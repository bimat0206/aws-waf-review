//Start of aws.go
// Package aws provides AWS service interactions for WAF log retrieval
package aws

import (
    "context"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "os"
    "path/filepath"
	"strconv"
    "strings"
    "time"

    "github.com/aws/aws-sdk-go-v2/aws"
    "github.com/aws/aws-sdk-go-v2/service/cloudwatchlogs"
    cwTypes "github.com/aws/aws-sdk-go-v2/service/cloudwatchlogs/types"
    "github.com/aws/aws-sdk-go-v2/service/s3"
    "github.com/aws/aws-sdk-go-v2/service/sts"
    "github.com/aws/aws-sdk-go-v2/service/wafv2"
    wafTypes "github.com/aws/aws-sdk-go-v2/service/wafv2/types"
    awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/schollz/progressbar/v3"
    smithylogging "github.com/aws/smithy-go/logging"
    "waf-log-retriever/config"
    "waf-log-retriever/logging"                      
)

// WAFv2Manager handles WAFv2 service interactions
type WAFv2Manager struct {
    Session aws.Config
}

// WAFLogSource represents a WAF logging configuration
type WAFLogSource struct {
    ProfileName     string
    Region         string
    WebACLName     string
    WebACLID       string
    LogSourceType  string // "s3" or "cloudwatchlogs"
    DestinationARN string
    S3BucketName   string
    CWLogsGroupName string
    Scope           string // "Regional" or "CloudFront"
}

// SessionManager manages AWS session configuration and validation
type SessionManager struct {
    Config  *config.Config
    Session aws.Config
    Logger  logging.Logger
}

// S3Manager handles S3 operations for log retrieval
type S3Manager struct {
    Session aws.Config
}

// CWLogsManager handles CloudWatch Logs operations
type CWLogsManager struct {
    Session aws.Config
}
// awsLoggerWrapper wraps your app logger and implements aws.Logger.
// awsLoggerWrapper wraps your app logger and implements smithy-go/logging.Logger.
type awsLoggerWrapper struct {
    logger logging.Logger
}


// Logf implements the smithy-go/logging.Logger interface.
// It filters out the "Response has no supported checksum" messages and writes them only to the log file.
func (w awsLoggerWrapper) Logf(classification smithylogging.Classification, format string, args ...interface{}) {
	msg := fmt.Sprintf(format, args...)

	// If the message contains the unwanted checksum warning...
	if strings.Contains(msg, "Response has no supported checksum") {
		// If our logger is a *defaultLogger, write directly to its file (not stdout).
        if dl, ok := w.logger.(*logging.DefaultLogger); ok {
			// Write to file only.
			// You can adjust the log level/tag as desired.
            dl.Debugf("[DEBUG] %s: %s\n", classification, msg)
		}
		return
	}

	// Otherwise, log as usual (this will go to both console and file).
	w.logger.Debugf("%s: %s", classification, msg)
}

// NewWAFv2Manager creates a new WAFv2 manager instance
func NewWAFv2Manager(session aws.Config) *WAFv2Manager {
    return &WAFv2Manager{Session: session}
}

// NewS3Manager creates a new S3 manager instance
func NewS3Manager(session aws.Config) *S3Manager {
    return &S3Manager{Session: session}
}

// NewCWLogsManager creates a new CloudWatch Logs manager instance
func NewCWLogsManager(session aws.Config) *CWLogsManager {
    return &CWLogsManager{Session: session}
}


// deriveBasePrefix splits a key by "/" and returns the prefix up to (but not including) the first part that is a 4-digit year.
func deriveBasePrefix(key string) string {
    parts := strings.Split(key, "/")
    for i, p := range parts {
        if len(p) == 4 {
            if _, err := strconv.Atoi(p); err == nil {
                return strings.Join(parts[:i], "/") + "/"
            }
        }
    }
    return ""
}

// commonPrefix returns the longest common prefix among a slice of strings.
func commonPrefix(strs []string) string {
    if len(strs) == 0 {
        return ""
    }
    prefix := strs[0]
    for _, s := range strs[1:] {
        for !strings.HasPrefix(s, prefix) {
            if prefix == "" {
                return ""
            }
            prefix = prefix[:len(prefix)-1]
        }
    }
    return prefix
}

// queryS3BasePrefix lists objects under "AWSLogs/" and returns a common base prefix containing the Web ACL name.
func queryS3BasePrefix(ctx context.Context, s3Client *s3.Client, bucket string, webACLName string, logger logging.Logger) (string, error) {
    input := &s3.ListObjectsV2Input{
        Bucket:  aws.String(bucket),
        Prefix:  aws.String("AWSLogs/"),
        MaxKeys: aws.Int32(100),
    }
    var candidateKeys []string
    paginator := s3.NewListObjectsV2Paginator(s3Client, input)
    for paginator.HasMorePages() {
        page, err := paginator.NextPage(ctx)
        if err != nil {
            return "", fmt.Errorf("failed to list S3 objects: %w", err)
        }
        for _, obj := range page.Contents {
            if strings.Contains(*obj.Key, webACLName) {
                candidateKeys = append(candidateKeys, *obj.Key)
            }
        }
        if len(candidateKeys) > 0 {
            break
        }
    }
    if len(candidateKeys) == 0 {
        return "", fmt.Errorf("no objects found containing Web ACL name %s", webACLName)
    }
    // Try to derive a base prefix from the first candidate.
    base := deriveBasePrefix(candidateKeys[0])
    if base == "" {
        // Fallback: compute the common prefix from all candidate keys.
        base = commonPrefix(candidateKeys)
    }
    if base != "" && !strings.HasSuffix(base, "/") {
        base += "/"
    }
    logger.Debugf("Queried base prefix: %s", base)
    return base, nil
}
// extractTimestampFromKey extracts the timestamp from the log file name.
// For example, given:
// "430096642635_waflogs_ap-southeast-1_vfbs-prod-dominos-v2_20241202T0105Z_d15273e2.log.gz"
// it will extract "20241202T0105Z" and parse it using layout "20060102T1504Z".
func extractTimestampFromKey(key string) (time.Time, error) {
    parts := strings.Split(key, "/")
    if len(parts) == 0 {
        return time.Time{}, errors.New("invalid key structure")
    }
    filename := parts[len(parts)-1]
    segments := strings.Split(filename, "_")
    var tsStr string
    for _, seg := range segments {
        if len(seg) == 13 && seg[8] == 'T' && seg[len(seg)-1] == 'Z' {
            // Optionally, you can add further checks here (e.g., ensuring the first 8 characters are digits)
            tsStr = seg
            break
        }
    }
    if tsStr == "" {
        return time.Time{}, fmt.Errorf("timestamp segment not found in filename %s", filename)
    }
    return time.Parse("20060102T1504Z", tsStr)
}
// NewSessionManager creates and validates an AWS session
func NewSessionManager(cfg *config.Config, logger logging.Logger) (*SessionManager, error) {
    if cfg == nil {
        return nil, fmt.Errorf("config cannot be nil")
    }
    
    if len(cfg.AWSProfiles) == 0 {
        return nil, fmt.Errorf("no AWS profiles found in config. Please add at least one profile to config.json")
    }

    logger.Infof("Attempting to connect to AWS using profile: %s", cfg.AWSProfiles[0].ProfileName)

    // Load AWS configuration with specified profile and region
    awsCfg, err := awsconfig.LoadDefaultConfig(context.TODO(),
    awsconfig.WithRegion(cfg.AWSProfiles[0].RegionName),
    awsconfig.WithSharedConfigProfile(cfg.AWSProfiles[0].ProfileName),
    awsconfig.WithLogger(awsLoggerWrapper{logger: logger}),
    // awsconfig.WithLogMode(0), // Disable AWS SDK logging if you don't want any
    )

    if err != nil {
        return nil, fmt.Errorf("unable to load SDK config: %w", err)
    }

    sm := &SessionManager{
        Config:  cfg,
        Session: awsCfg,
        Logger:  logger,
    }

    // Validate the session by making a test API call
    if err := sm.validateSession(); err != nil {
        return nil, fmt.Errorf("failed to validate AWS session: %w", err)
    }

    return sm, nil
}

// validateSession verifies the AWS session by making a test API call
func (sm *SessionManager) validateSession() error {
    ctx := context.TODO()
    stsClient := sts.NewFromConfig(sm.Session)

    sm.Logger.Info("Validating AWS credentials...")
    
    result, err := stsClient.GetCallerIdentity(ctx, &sts.GetCallerIdentityInput{})
    if err != nil {
        return fmt.Errorf("failed to validate credentials: %w", err)
    }

    sm.Logger.Infof("Successfully connected to AWS as: %s (Account: %s)", *result.Arn, *result.Account)
    return nil
}


// DiscoverWAFLogSources discovers WAF ACLs and their logging configurations
func DiscoverWAFLogSources(wafv2Mgr *WAFv2Manager, cfg *config.Config, logger logging.Logger) ([]*WAFLogSource, error) {
    ctx := context.TODO()
    client := wafv2.NewFromConfig(wafv2Mgr.Session)

    logger.Info("Discovering WAF Web ACLs...")

    var discoveredSources []*WAFLogSource

    // Helper function to list Web ACLs for a given scope
    listWebACLs := func(scope wafTypes.Scope) error {
        var nextMarker *string

        for {
            input := &wafv2.ListWebACLsInput{
                Scope:      scope,
                Limit:      aws.Int32(100),
                NextMarker: nextMarker,
            }

            result, err := client.ListWebACLs(ctx, input)
            if err != nil {
                return fmt.Errorf("failed to list Web ACLs for scope %s: %w", scope, err)
            }

            logger.Infof("Found %d Web ACLs for scope %s", len(result.WebACLs), scope)

            // Process each Web ACL
            for _, acl := range result.WebACLs {
                aclName := aws.ToString(acl.Name)
                aclID := aws.ToString(acl.Id)
                aclArn := aws.ToString(acl.ARN)

                logCfgInput := &wafv2.GetLoggingConfigurationInput{
                    ResourceArn: aws.String(aclArn),
                }

                logCfg, err := client.GetLoggingConfiguration(ctx, logCfgInput)
                var notFoundErr *wafTypes.WAFNonexistentItemException
                if err != nil {
                    if errors.As(err, &notFoundErr) {
                        logger.Debugf("No logging configuration found for Web ACL: %s", aclName)
                        continue
                    }
                    return fmt.Errorf("failed to get logging configuration for %s: %w", aclName, err)
                }

                if logCfg.LoggingConfiguration == nil || len(logCfg.LoggingConfiguration.LogDestinationConfigs) == 0 {
                    logger.Debugf("No log destination configured for Web ACL: %s", aclName)
                    continue
                }

                destArn := logCfg.LoggingConfiguration.LogDestinationConfigs[0]

                source := &WAFLogSource{
                    ProfileName:    cfg.AWSProfiles[0].ProfileName,
                    Region:         cfg.AWSProfiles[0].RegionName,
                    WebACLName:     aclName,
                    WebACLID:       aclID,
                    DestinationARN: destArn,
                    Scope:          string(scope), // Add the scope (Regional or CloudFront)
                }

                if isS3Destination(destArn) {
                    source.LogSourceType = "s3"
                    source.S3BucketName = extractS3BucketName(destArn)
                    logger.Debugf("Found S3 destination: %s", source.S3BucketName)
                } else if isCloudWatchDestination(destArn) {
                    source.LogSourceType = "cloudwatchlogs"
                    source.CWLogsGroupName = extractLogGroupName(destArn)
                    logger.Debugf("Found CloudWatch Logs destination: %s", source.CWLogsGroupName)
                }

                discoveredSources = append(discoveredSources, source)
                logger.Infof("Found WAF Web ACL: %s with logging enabled to %s", aclName, source.LogSourceType)
            }

            if result.NextMarker == nil {
                break
            }
            nextMarker = result.NextMarker
        }
        return nil
    }

    // List Web ACLs for both Regional and CloudFront scopes
    if err := listWebACLs(wafTypes.ScopeRegional); err != nil {
        return nil, fmt.Errorf("error discovering Regional Web ACLs: %w", err)
    }
    if err := listWebACLs(wafTypes.ScopeCloudfront); err != nil {
        return nil, fmt.Errorf("error discovering CloudFront Web ACLs: %w", err)
    }

    // Log the total discovered sources
    if len(discoveredSources) == 0 {
        logger.Warning("No WAF Web ACLs with logging enabled were found")
    } else {
        logger.Infof("Total WAF Web ACLs with logging enabled: %d", len(discoveredSources))
    }

    return discoveredSources, nil
}



// ConvertWAFLogSource converts a WAF config source to a WAFLogSource structure
func ConvertWAFLogSource(cfg *config.WAFLogSourceConfig) *WAFLogSource {
    if cfg == nil {
        return nil
    }
    
    return &WAFLogSource{
        ProfileName:     cfg.ProfileName,
        Region:         cfg.Region,
        WebACLName:     cfg.WebACLName,
        WebACLID:       cfg.WebACLID,
        LogSourceType:  cfg.LogSourceType,
        DestinationARN: cfg.DestinationARN,
        S3BucketName:   cfg.S3BucketName,
        CWLogsGroupName: cfg.CWLogsGroupName,
    }
}

// RetrieveLogsFromS3 retrieves WAF logs from an S3 bucket


// extractS3Prefix extracts the S3 prefix from a destination ARN.
// For an ARN like "arn:aws:s3:::aws-waf-logs-acfc-24/AWSLogs/WAFLogs/ACFC_LB_WAF",
// it returns "AWSLogs/WAFLogs/ACFC_LB_WAF".
func extractS3Prefix(arn string) string {
    parts := strings.SplitN(arn, ":::", 2)
    if len(parts) != 2 {
        return ""
    }
    bucketAndPrefix := parts[1] // "bucket-name/prefix/..."
    idx := strings.Index(bucketAndPrefix, "/")
    if idx == -1 {
        return ""
    }
    return bucketAndPrefix[idx+1:]
}

// generatePrefixesForTimeRangeCustom builds prefixes using the provided base prefix.
func generatePrefixesForTimeRangeCustom(startTime, endTime time.Time, basePrefix string) []string {
    var prefixes []string
    currentTime := startTime
    for !currentTime.After(endTime) {
        for hour := 0; hour < 24; hour++ {
            prefix := fmt.Sprintf("%s%d/%02d/%02d/%02d/",
                basePrefix,
                currentTime.Year(),
                currentTime.Month(),
                currentTime.Day(),
                hour,
            )
            prefixes = append(prefixes, prefix)
        }
        currentTime = currentTime.AddDate(0, 0, 1)
    }
    return prefixes
}


// --- In the RetrieveLogsFromS3 function ---
func RetrieveLogsFromS3(s3Mgr *S3Manager, source *WAFLogSource, startTime, endTime time.Time, outputDir string, logger logging.Logger) (int, error) {
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
    defer cancel()

    s3Client := s3.NewFromConfig(s3Mgr.Session)
    var logCount int

    // 1) Determine the base prefix for listing objects.
    basePrefix, err := queryS3BasePrefix(ctx, s3Client, source.S3BucketName, source.WebACLName, logger)
    if err != nil {
        logger.Warningf("Failed to query S3 for base prefix: %v. Falling back to extracting from DestinationARN.", err)
        basePrefix = extractS3Prefix(source.DestinationARN)
    }
    logger.Debugf("Using base prefix: %s", basePrefix)

    // 2) Generate all possible prefixes for the time range.
    prefixes := generatePrefixesForTimeRangeCustom(startTime, endTime, basePrefix)
    logger.Debugf("Generated %d prefixes to check for logs", len(prefixes))

    // 3) Collect all matching objects first (to calculate total compressed size).
    type s3LogObject struct {
        Key       string
        Timestamp time.Time
        Size      int64
    }
    var logObjects []s3LogObject
    var totalSize int64

    for _, prefix := range prefixes {
        logger.Debugf("Checking prefix: %s", prefix)
        paginator := s3.NewListObjectsV2Paginator(s3Client, &s3.ListObjectsV2Input{
            Bucket: aws.String(source.S3BucketName),
            Prefix: aws.String(prefix),
        })

        for paginator.HasMorePages() {
            page, err := paginator.NextPage(ctx)
            if err != nil {
                return 0, fmt.Errorf("failed to list S3 objects for prefix %s: %w", prefix, err)
            }
            for _, obj := range page.Contents {
                logger.Debugf("Found log file: %s", *obj.Key)
                timestamp, err := extractTimestampFromPath(*obj.Key)
                if err != nil {
                    logger.Debugf("Skipping file due to timestamp parsing error: %s - %v", *obj.Key, err)
                    continue
                }
                if timestamp.Before(startTime) || timestamp.After(endTime) {
                    continue
                }
                logObjects = append(logObjects, s3LogObject{
                    Key:       *obj.Key,
                    Timestamp: timestamp,
                    Size:      *obj.Size,
                })
                totalSize += *obj.Size
            }
        }
    }

    if len(logObjects) == 0 {
        logger.Warning("No log files found in the specified time range")
        return 0, nil
    }

    // 4) Prompt user with total size & object count.
    sizeInMB := float64(totalSize) / (1024 * 1024)
    fmt.Printf("\nFound %d log files (%.2f MB total). Proceed with download? (y/n): ", len(logObjects), sizeInMB)
    var userResp string
    _, _ = fmt.Scanln(&userResp)
    if strings.ToLower(userResp) != "y" {
        logger.Info("User chose to cancel the download.")
        return 0, nil
    }

    // 5) Create one overall progress bar using the total compressed size.
    overallBar := progressbar.NewOptions64(
        totalSize,
        progressbar.OptionSetDescription("Overall Download Progress"),
        progressbar.OptionSetWidth(40),
        progressbar.OptionSetTheme(progressbar.Theme{
            Saucer:        "█",
            SaucerHead:    "█",
            SaucerPadding: "░",
            BarStart:      "[",
            BarEnd:        "]",
        }),
        progressbar.OptionClearOnFinish(),
    )

    // 6) Download each object, updating the overall progress bar.
    for _, logObj := range logObjects {
        outPath := generateOutputPath(outputDir, source, logObj.Timestamp, logObj.Key)
        if err := os.MkdirAll(filepath.Dir(outPath), 0755); err != nil {
            return logCount, fmt.Errorf("failed to create output directory: %w", err)
        }
        logger.Debugf("Downloading %s to %s", logObj.Key, outPath)
        if err := downloadS3Object(ctx, s3Client, source.S3BucketName, logObj.Key, outPath, overallBar); err != nil {
            return logCount, fmt.Errorf("failed to download object %s: %w", logObj.Key, err)
        }
        logCount++
    }

    logger.Infof("Successfully downloaded %d log files", logCount)
    return logCount, nil
}






// generatePrefixesForTimeRange generates a list of S3 prefixes to check based on the time range
func generatePrefixesForTimeRange(startTime, endTime time.Time, source *WAFLogSource) []string {
    var prefixes []string
    basePrefix := fmt.Sprintf("AWSLogs/WAFLogs/%s/%s", source.Region, source.WebACLName)

    // Iterate through each day in the time range
    currentTime := startTime
    for currentTime.Before(endTime) || currentTime.Equal(endTime) {
        // Generate prefix for each hour of the day
        for hour := 0; hour < 24; hour++ {
            prefix := fmt.Sprintf("%s/%d/%02d/%02d/%02d/",
                basePrefix,
                currentTime.Year(),
                currentTime.Month(),
                currentTime.Day(),
                hour,
            )
            prefixes = append(prefixes, prefix)
        }
        currentTime = currentTime.AddDate(0, 0, 1) // Move to next day
    }

    return prefixes
}

// extractTimestampFromPath extracts the timestamp from a WAF log file path
func extractTimestampFromPath(path string) (time.Time, error) {
    // Split the path and get components
    parts := strings.Split(path, "/")
    if len(parts) < 7 {
        return time.Time{}, fmt.Errorf("invalid path structure")
    }

    // Find the year, month, day, and hour in the path
    var year, month, day, hour string
    for i, part := range parts {
        if i > 0 && i < len(parts)-4 {
            // Try to parse each part as a year (4 digits)
            if len(part) == 4 && part[0] == '2' {
                year = part
                if i+3 < len(parts) {
                    month = parts[i+1]
                    day = parts[i+2]
                    hour = parts[i+3]
                    break
                }
            }
        }
    }

    if year == "" || month == "" || day == "" || hour == "" {
        return time.Time{}, fmt.Errorf("could not find date components in path")
    }

    // Parse the timestamp
    timeStr := fmt.Sprintf("%s-%s-%sT%s:00:00Z", year, month, day, hour)
    return time.Parse(time.RFC3339, timeStr)
}

// generateOutputPath creates the output file path maintaining the same structure
// generateOutputPath creates the output file path maintaining the same structure
func generateOutputPath(baseDir string, source *WAFLogSource, timestamp time.Time, originalKey string) string {
    // Create directory structure: baseDir/profile/waf-name/year/month/day/hour/
    datePath := filepath.Join(
        timestamp.Format("2006"),
        timestamp.Format("01"),
        timestamp.Format("02"),
        timestamp.Format("15"),
    )
    
    // Use the original filename as-is, including .gz
    baseName := filepath.Base(originalKey)
    
    return filepath.Join(
        baseDir,
        source.ProfileName,
        source.WebACLName,
        datePath,
        baseName,
    )
}

// downloadS3Object downloads a compressed object from S3 and writes it to outputPath as-is,
// preserving its compressed .gz format, while displaying a progress bar.
func downloadS3Object(ctx context.Context, client *s3.Client, bucket, key, outputPath string, overallBar *progressbar.ProgressBar) error {
    // Get the object from S3.
    result, err := client.GetObject(ctx, &s3.GetObjectInput{
        Bucket: aws.String(bucket),
        Key:    aws.String(key),
    })
    if err != nil {
        return fmt.Errorf("failed to get object: %w", err)
    }
    defer result.Body.Close()

    // Create the output file.
    outFile, err := os.Create(outputPath)
    if err != nil {
        return fmt.Errorf("failed to create output file: %w", err)
    }
    defer outFile.Close()

    // Create a TeeReader to update the overall progress bar as compressed bytes are read.
    tee := io.TeeReader(result.Body, overallBar)

    // Copy the compressed data directly to the output file without decompression.
    if _, err := io.Copy(outFile, tee); err != nil {
        return fmt.Errorf("failed to copy compressed data: %w", err)
    }
    return nil
}


func RetrieveLogsFromCWLogs(cwLogsMgr *CWLogsManager, source *WAFLogSource, startTime, endTime time.Time, outputDir string, logger logging.Logger) (int, error) {
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
    defer cancel()

    cwlogsClient := cloudwatchlogs.NewFromConfig(cwLogsMgr.Session)

    outputPath := filepath.Join(outputDir, source.ProfileName, source.WebACLName)
    if err := os.MkdirAll(outputPath, 0755); err != nil {
        return 0, fmt.Errorf("failed to create output directory: %w", err)
    }

    // ✅ Set Time Chunk Interval (Adjust if Needed)
    timeChunk := 6 * time.Hour // Splitting logs into 6-hour chunks
    totalChunks := int(endTime.Sub(startTime) / timeChunk) // Total number of queries to execute
    if totalChunks == 0 {
        totalChunks = 1 // Ensure at least one chunk
    }

    // ✅ Initialize Progress Bar
    progress := progressbar.Default(int64(totalChunks), "Retrieving logs...")

    currentStart := startTime
    totalLogCount := 0

    // ✅ Loop Over Time Chunks
    for currentStart.Before(endTime) {
        currentEnd := currentStart.Add(timeChunk)
        if currentEnd.After(endTime) {
            currentEnd = endTime
        }

        logger.Infof("Querying logs from %s to %s", currentStart.Format(time.RFC3339), currentEnd.Format(time.RFC3339))

        // ✅ Query CloudWatch Logs
        queryInput := &cloudwatchlogs.StartQueryInput{
            LogGroupName: aws.String(source.CWLogsGroupName),
            StartTime:    aws.Int64(currentStart.UnixNano() / int64(time.Millisecond)),
            EndTime:      aws.Int64(currentEnd.UnixNano() / int64(time.Millisecond)),
            QueryString:  aws.String("fields @timestamp, @message"),
        }

        startQueryOutput, err := cwlogsClient.StartQuery(ctx, queryInput)
        if err != nil {
            return totalLogCount, fmt.Errorf("failed to start CloudWatch Logs query: %w", err)
        }

        logger.Infof("Started log retrieval query with ID: %s", *startQueryOutput.QueryId)

        // ✅ Process Query Results
        for {
            queryResults, err := cwlogsClient.GetQueryResults(ctx, &cloudwatchlogs.GetQueryResultsInput{
                QueryId: startQueryOutput.QueryId,
            })

            if err != nil {
                return totalLogCount, fmt.Errorf("failed to get query results: %w", err)
            }

            if len(queryResults.Results) > 0 {
                // ✅ Generate a unique filename per chunk
                outputFile := filepath.Join(outputPath, fmt.Sprintf("waf_logs_%s_to_%s.json", 
                    currentStart.Format("20060102_150405"), currentEnd.Format("20060102_150405")))

                if err := writeLogsToFile(outputFile, queryResults.Results); err != nil {
                    return totalLogCount, fmt.Errorf("failed to write logs to file: %w", err)
                }

                totalLogCount += len(queryResults.Results)

                firstLogTime := queryResults.Results[0][0].Value
                lastLogTime := queryResults.Results[len(queryResults.Results)-1][0].Value
                logger.Infof("Retrieved logs from %s to %s", firstLogTime, lastLogTime)
            }

            if queryResults.Status == cwTypes.QueryStatusComplete {
                break
            }

            time.Sleep(5 * time.Second)
        }

        // ✅ Update Progress Bar
        _ = progress.Add(1)

        // ✅ Move to Next Time Chunk
        currentStart = currentEnd
    }

    logger.Infof("Successfully retrieved a total of %d logs", totalLogCount)
    return totalLogCount, nil
}




// Helper functions for ARN parsing and validation

func isS3Destination(arn string) bool {
    return strings.Contains(arn, ":s3:")
}

func isCloudWatchDestination(arn string) bool {
    return strings.Contains(arn, ":logs:")
}

func extractS3BucketName(arn string) string {
    parts := strings.Split(arn, ":")
    if len(parts) < 6 {
        return ""
    }
	bucketAndPrefix := strings.Split(parts[5], "/")
    return bucketAndPrefix[0]
}

func extractLogGroupName(arn string) string {
    parts := strings.Split(arn, ":")
    if len(parts) < 7 {
        return ""
    }
    return parts[6]
}

// writeLogsToFile writes CloudWatch Logs query results to a JSON file
func writeLogsToFile(filename string, results [][]cwTypes.ResultField) error {
    file, err := os.Create(filename)
    if err != nil {
        return fmt.Errorf("failed to create output file: %w", err)
    }
    defer file.Close()

    encoder := json.NewEncoder(file)
    encoder.SetIndent("", "  ") // Add indentation for better readability

    for _, result := range results {
        // Convert the ResultField slice to a map for better JSON structure
        logEntry := make(map[string]interface{})
        for _, field := range result {
            if field.Field != nil && field.Value != nil {
                // Handle different field types appropriately
                logEntry[*field.Field] = *field.Value
            }
        }

        // Only write non-empty log entries
        if len(logEntry) > 0 {
            if err := encoder.Encode(logEntry); err != nil {
                return fmt.Errorf("failed to encode log entry: %w", err)
            }
        }
    }

    return nil
}

// Utility function to validate the WAF log source configuration
func validateWAFLogSource(source *WAFLogSource) error {
    if source == nil {
        return fmt.Errorf("WAF log source cannot be nil")
    }

    if source.WebACLName == "" {
        return fmt.Errorf("WebACL name cannot be empty")
    }

    if source.WebACLID == "" {
        return fmt.Errorf("WebACL ID cannot be empty")
    }

    if source.LogSourceType != "s3" && source.LogSourceType != "cloudwatchlogs" {
        return fmt.Errorf("invalid log source type: %s (must be 's3' or 'cloudwatchlogs')", source.LogSourceType)
    }

    if source.LogSourceType == "s3" && source.S3BucketName == "" {
        return fmt.Errorf("S3 bucket name cannot be empty for S3 log source")
    }

    if source.LogSourceType == "cloudwatchlogs" && source.CWLogsGroupName == "" {
        return fmt.Errorf("CloudWatch Logs group name cannot be empty for CloudWatch Logs source")
    }

    return nil
}

// BatchRetrieveLogs retrieves logs from multiple WAF sources in parallel
func BatchRetrieveLogs(sources []*WAFLogSource, s3Mgr *S3Manager, cwLogsMgr *CWLogsManager, 
    startTime, endTime time.Time, outputDir string, logger logging.Logger, maxConcurrent int) []error {
    
    if maxConcurrent <= 0 {
        maxConcurrent = 4 // Default concurrent retrievals
    }

    type retrievalResult struct {
        source *WAFLogSource
        err    error
    }

    // Create a channel to receive results
    results := make(chan retrievalResult, len(sources))
    semaphore := make(chan struct{}, maxConcurrent)

    // Start retrieval for each source
    for _, source := range sources {
        go func(src *WAFLogSource) {
            semaphore <- struct{}{} // Acquire semaphore
            defer func() { <-semaphore }() // Release semaphore

            var err error
            if err = validateWAFLogSource(src); err != nil {
                results <- retrievalResult{src, fmt.Errorf("validation failed: %w", err)}
                return
            }

            logger.Infof("Starting log retrieval for WAF WebACL: %s", src.WebACLName)

            switch src.LogSourceType {
            case "s3":
                _, err = RetrieveLogsFromS3(s3Mgr, src, startTime, endTime, outputDir, logger)
            case "cloudwatchlogs":
                _, err = RetrieveLogsFromCWLogs(cwLogsMgr, src, startTime, endTime, outputDir, logger)
            default:
                err = fmt.Errorf("unsupported log source type: %s", src.LogSourceType)
            }

            if err != nil {
                err = fmt.Errorf("failed to retrieve logs for %s: %w", src.WebACLName, err)
            }

            results <- retrievalResult{src, err}
        }(source)
    }

    // Collect results
    var errors []error
    for range sources {
        result := <-results
        if result.err != nil {
            errors = append(errors, result.err)
            logger.Errorf("Error retrieving logs for %s: %v", result.source.WebACLName, result.err)
        } else {
            logger.Infof("Successfully retrieved logs for %s", result.source.WebACLName)
        }
    }

    return errors
}

// GetWAFLogMetrics retrieves basic metrics about WAF logs
func GetWAFLogMetrics(source *WAFLogSource, startTime, endTime time.Time, logger logging.Logger) (map[string]interface{}, error) {
    metrics := make(map[string]interface{})
    
    // Set basic metrics
    metrics["webACL"] = source.WebACLName
    metrics["logSourceType"] = source.LogSourceType
    metrics["timeRange"] = map[string]string{
        "start": startTime.Format(time.RFC3339),
        "end":   endTime.Format(time.RFC3339),
    }

    // Additional metrics based on source type
    switch source.LogSourceType {
    case "s3":
        // Add S3-specific metrics
        metrics["bucketName"] = source.S3BucketName
        // You could add more S3 metrics here (e.g., storage size, object count)
        
    case "cloudwatchlogs":
        // Add CloudWatch Logs specific metrics
        metrics["logGroupName"] = source.CWLogsGroupName
        // You could add more CloudWatch metrics here (e.g., log volume, query stats)
    }

    return metrics, nil
}

//end of aws.go