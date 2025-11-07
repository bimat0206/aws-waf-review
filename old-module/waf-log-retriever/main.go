//start of main.go 
package main

import (
    "compress/gzip"
    "flag"
    "fmt"
    "os"
    "path/filepath"
    "time"

    "waf-log-retriever/aws"
    "waf-log-retriever/cli"
    "waf-log-retriever/config"
    "waf-log-retriever/logging"
    "waf-log-retriever/storage"
)

// Command line flags
var (
	configFile     = flag.String("config", "config.json", "Path to configuration file")
	wafConfigFile  = flag.String("waf-config", "waf-config.json", "Path to WAF configuration file")
	profileFlag    = flag.String("profile", "", "AWS profile name from config.json")
	wafSourceFlag  = flag.String("waf-source", "", "WAF Log Source Name from waf-config.json for non-interactive mode")
	startDateFlag  = flag.String("start-date", "", "Start date for log retrieval (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ssZ)")
	endDateFlag    = flag.String("end-date", "", "End date for log retrieval (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ssZ)")
    outputDirFlag = flag.String("output-dir", "../logs/raw", "Output directory for raw logs")
	logLevelFlag   = flag.String("log-level", "INFO", "Logging level (DEBUG, INFO, WARNING, ERROR)")
	interactiveFlag = flag.Bool("interactive", false, "Run in interactive mode")
)

// AppContext holds all the initialized components and configuration
// AppContext holds application-wide context
type AppContext struct {
    Config         *config.Config
    WAFConfig      *config.WAFConfig
    Logger         logging.Logger
    StorageManager *storage.StorageManager
    AWSSession     *aws.SessionManager
    StartTime      time.Time
    EndTime        time.Time
}

// main.go

func main() {
    // Parse command line flags
    flag.Parse()

    // Initialize application context
    appCtx, err := initializeApp()
    if err != nil {
        fmt.Printf("Failed to initialize application: %v\n", err)
        os.Exit(1)
    }
    // Ensure logger is closed properly
    defer appCtx.Logger.Close()

    // Log application start with configuration details
    appCtx.Logger.Info("Starting AWS WAF Log Retrieval Script")
    appCtx.Logger.Infof("Configuration loaded from: %s", *configFile)
    appCtx.Logger.Infof("Output directory: %s", *outputDirFlag)
    appCtx.Logger.Infof("Log level: %s", *logLevelFlag)
    if *wafSourceFlag != "" {
        appCtx.Logger.Infof("Running in non-interactive mode for WAF source: %s", *wafSourceFlag)
    } else {
        appCtx.Logger.Info("Running in interactive mode")
    }

    // Initialize AWS managers
    appCtx.Logger.Info("Initializing AWS service managers...")
    s3Mgr := aws.NewS3Manager(appCtx.AWSSession.Session)
    cwLogsMgr := aws.NewCWLogsManager(appCtx.AWSSession.Session)
    wafv2Mgr := aws.NewWAFv2Manager(appCtx.AWSSession.Session)
    appCtx.Logger.Info("AWS service managers initialized successfully")

    // Select WAF source based on mode
    var selectedWAFSource *aws.WAFLogSource
    if *wafSourceFlag != "" {
        selectedWAFSource, err = handleNonInteractiveMode(appCtx, *wafSourceFlag)
    } else {
        selectedWAFSource, err = handleInteractiveMode(appCtx, wafv2Mgr)
    }

    if err != nil {
        appCtx.Logger.Errorf("Failed to select WAF source: %v", err)
        os.Exit(1)
    }

    if selectedWAFSource == nil {
        appCtx.Logger.Error("No WAF Log Source selected or configured. Exiting.")
        os.Exit(1)
    }

    // Log the selected WAF source details
    appCtx.Logger.Infof("Selected WAF Source Details:")
    appCtx.Logger.Infof("  - Name: %s", selectedWAFSource.WebACLName)
    appCtx.Logger.Infof("  - ID: %s", selectedWAFSource.WebACLID)
    appCtx.Logger.Infof("  - Type: %s", selectedWAFSource.LogSourceType)
    appCtx.Logger.Infof("  - Region: %s", selectedWAFSource.Region)

    // Process the selected WAF source
    if err := processWAFSource(appCtx, selectedWAFSource, s3Mgr, cwLogsMgr); err != nil {
        appCtx.Logger.Errorf("Failed to process WAF source: %v", err)
        os.Exit(1)
    }

    // Log completion status and summary
    appCtx.Logger.Info("AWS WAF Log Retrieval Script completed successfully")
    appCtx.Logger.Infof("Log retrieval time range: %s to %s",
        appCtx.StartTime.Format("2006-01-02 15:04:05"),
        appCtx.EndTime.Format("2006-01-02 15:04:05"))
}

// initializeApp initializes all components and returns an AppContext
func initializeApp() (*AppContext, error) {
    // Create application context
    appCtx := &AppContext{}

    // Initialize logger first for error reporting
    logger, err := logging.SetupLogger(*logLevelFlag)
    if err != nil {
        return nil, fmt.Errorf("failed to setup logger: %w", err)
    }
    appCtx.Logger = logger

    // Load configuration files
    logger.Info("Loading configuration files...")
    cfg, err := config.LoadConfig(*configFile)
    if err != nil {
        return nil, fmt.Errorf("failed to load config file: %w", err)
    }
    logger.Info("Successfully loaded config.json")

    wafCfg, err := config.LoadWAFConfig(*wafConfigFile)
    if err != nil {
        logger.Warning("Failed to load WAF config. Dynamic discovery will be used.")
    } else {
        logger.Info("Successfully loaded waf-config.json")
    }
    appCtx.Config = cfg
    appCtx.WAFConfig = wafCfg

    // Initialize AWS session
    logger.Info("Initializing AWS session...")
    awsSession, err := aws.NewSessionManager(cfg, logger)
    if err != nil {
        return nil, fmt.Errorf("failed to create AWS session manager: %w", err)
    }
    appCtx.AWSSession = awsSession

    // Parse time range
    startTime, endTime, err := parseTimeRange(*startDateFlag, *endDateFlag)
    if err != nil {
        return nil, fmt.Errorf("failed to parse time range: %w", err)
    }
    appCtx.StartTime = startTime
    appCtx.EndTime = endTime

    // Initialize storage manager
    storageConfig := storage.StorageConfig{
        BaseDirectory:      *outputDirFlag,
        RetentionDays:     30,
        CompressionEnabled: true,
        CompressionLevel:   gzip.BestCompression,
    }
    
    storageManager, err := storage.NewStorageManager(storageConfig)
    if err != nil {
        return nil, fmt.Errorf("failed to create storage manager: %w", err)
    }
    appCtx.StorageManager = storageManager

    return appCtx, nil
}

// handleNonInteractiveMode processes WAF source selection in non-interactive mode
func handleNonInteractiveMode(appCtx *AppContext, wafSourceName string) (*aws.WAFLogSource, error) {
	appCtx.Logger.Infof("Running in non-interactive mode with pre-defined WAF Source: %s", wafSourceName)

	wafSourceConfig, err := config.FindWAFLogSource(appCtx.WAFConfig, *profileFlag, wafSourceName)
	if err != nil {
		return nil, fmt.Errorf("error finding WAF Log Source '%s' in waf-config.json: %w", wafSourceName, err)
	}

	return aws.ConvertWAFLogSource(wafSourceConfig), nil
}

// handleInteractiveMode processes WAF source selection in interactive mode
func handleInteractiveMode(appCtx *AppContext, wafv2Mgr *aws.WAFv2Manager) (*aws.WAFLogSource, error) {
    appCtx.Logger.Info("Starting WAF Web ACL discovery...")

    discoveredSources, err := aws.DiscoverWAFLogSources(wafv2Mgr, appCtx.Config, appCtx.Logger)
    if err != nil {
        return nil, fmt.Errorf("error during WAF Log Source Discovery: %w", err)
    }

    if len(discoveredSources) == 0 {
        return nil, fmt.Errorf("no WAF Web ACLs with logging enabled were found. Please check your WAF configuration")
    }

    appCtx.Logger.Info("Please select a WAF Web ACL from the list below:")
    selected, err := cli.PromptUserForWAFSourceSelection(discoveredSources)
    if err != nil {
        return nil, fmt.Errorf("error during WAF source selection: %w", err)
    }

    appCtx.Logger.Infof("Selected WAF Web ACL: %s", selected.WebACLName)
    return selected, nil
}

// processWAFSource handles the log retrieval for a selected WAF source
func processWAFSource(appCtx *AppContext, source *aws.WAFLogSource, s3Mgr *aws.S3Manager, cwLogsMgr *aws.CWLogsManager) error {
    appCtx.Logger.Infof("Processing logs for WAF Web ACL: %s", source.WebACLName)
    appCtx.Logger.Infof("Log destination type: %s", source.LogSourceType)

    var logCount int
    var err error

    switch source.LogSourceType {
    case "s3":
        appCtx.Logger.Infof("Retrieving logs from S3 bucket: %s", source.S3BucketName)
        logCount, err = aws.RetrieveLogsFromS3(s3Mgr, source, appCtx.StartTime, appCtx.EndTime, *outputDirFlag, appCtx.Logger)
    case "cloudwatchlogs":
        appCtx.Logger.Infof("Retrieving logs from CloudWatch Logs group: %s", source.CWLogsGroupName)
        logCount, err = aws.RetrieveLogsFromCWLogs(cwLogsMgr, source, appCtx.StartTime, appCtx.EndTime, *outputDirFlag, appCtx.Logger)
    default:
        return fmt.Errorf("unsupported log source type: %s", source.LogSourceType)
    }

    if err != nil {
        return fmt.Errorf("failed to retrieve logs: %w", err)
    }

    appCtx.Logger.Infof("Successfully retrieved %d log files for WAF Web ACL: %s", logCount, source.WebACLName)
    appCtx.Logger.Infof("Logs stored in: %s", filepath.Join(*outputDirFlag, source.ProfileName, source.WebACLName))
    return nil
}

// parseTimeRange parses and validates the time range for log retrieval
func parseTimeRange(startDateStr, endDateStr string) (startTime, endTime time.Time, err error) {
    // If both start and end dates are empty, prompt the user for custom dates.
    if startDateStr == "" && endDateStr == "" {
        var startInput, endInput string
        fmt.Print("Enter start date (YYYY-MM-DD): ")
        if _, err := fmt.Scanln(&startInput); err != nil {
            return time.Time{}, time.Time{}, fmt.Errorf("failed to read start date: %w", err)
        }
        fmt.Print("Enter end date (YYYY-MM-DD): ")
        if _, err := fmt.Scanln(&endInput); err != nil {
            return time.Time{}, time.Time{}, fmt.Errorf("failed to read end date: %w", err)
        }
        startTime, err = time.Parse("2006-01-02", startInput)
        if err != nil {
            return time.Time{}, time.Time{}, fmt.Errorf("invalid start date format: %w", err)
        }
        endTime, err = time.Parse("2006-01-02", endInput)
        if err != nil {
            return time.Time{}, time.Time{}, fmt.Errorf("invalid end date format: %w", err)
        }
        if startTime.After(endTime) {
            return time.Time{}, time.Time{}, fmt.Errorf("start date cannot be after end date")
        }
        return startTime, endTime, nil
    }

    // If either flag is provided, try to parse using multiple layouts.
    layoutFormats := []string{
        "2006-01-02T15:04:05Z",
        "2006-01-02T15:04Z",
        "2006-01-02",
    }

    if startDateStr != "" {
        var parseErr error
        for _, layout := range layoutFormats {
            startTime, parseErr = time.Parse(layout, startDateStr)
            if parseErr == nil {
                break
            }
        }
        if parseErr != nil {
            return time.Time{}, time.Time{}, fmt.Errorf("invalid start date format: %w", parseErr)
        }
    } else {
        // Fallback: default to 24 hours before now.
        startTime = time.Now().Add(-24 * time.Hour)
    }

    if endDateStr != "" {
        var parseErr error
        for _, layout := range layoutFormats {
            endTime, parseErr = time.Parse(layout, endDateStr)
            if parseErr == nil {
                break
            }
        }
        if parseErr != nil {
            return time.Time{}, time.Time{}, fmt.Errorf("invalid end date format: %w", parseErr)
        }
    } else {
        // Fallback: default to current time.
        endTime = time.Now()
    }

    if startTime.After(endTime) {
        return time.Time{}, time.Time{}, fmt.Errorf("start date cannot be after end date")
    }

    return startTime, endTime, nil
}



// parseTime parses a time string in various formats
func parseTime(timeStr string) (time.Time, error) {
	layouts := []string{
		"2006-01-02T15:04:05Z",
		"2006-01-02T15:04Z",
		"2006-01-02",
	}

	for _, layout := range layouts {
		t, err := time.Parse(layout, timeStr)
		if err == nil {
			return t, nil
		}
	}
	
	return time.Time{}, fmt.Errorf("could not parse time string: %s, supported formats: YYYY-MM-DD, YYYY-MM-DDTHH:mm, YYYY-MM-DDTHH:mm:ssZ", timeStr)
}

// end of main.go