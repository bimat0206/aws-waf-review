# Changelog - Fetchers Module

All notable changes to the fetchers module will be documented in this file.

## [1.0.1] - 2025-11-07

### Fixed

#### Region-Aware CloudWatch Fetching
- **Issue**: CloudWatch log fetching failed when user's current AWS region differed from log group's region
- **Impact**: CloudFront WAF logs (typically in us-east-1) failed when user was in other regions
- **Fix**: Added optional `region` parameter to `CloudWatchFetcher.__init__()`
- **Usage**: Can now instantiate fetcher with specific region: `CloudWatchFetcher(region='us-east-1')`
- **Backward Compatibility**: Region parameter is optional; defaults to current AWS CLI region if not provided

### Changed

#### CloudWatchFetcher Constructor
- Added optional `region` parameter to `__init__()` method
- Fetcher now creates region-specific CloudWatch Logs client when region is provided
- Enables cross-region log fetching without changing AWS CLI configuration

### Technical Details

#### Before (v1.0.0)
```python
class CloudWatchFetcher:
    def __init__(self):
        self.logs_client = get_logs_client()  # Uses current region
```

#### After (v1.0.1)
```python
class CloudWatchFetcher:
    def __init__(self, region: str = None):
        if region:
            self.logs_client = get_logs_client(region=region)
        else:
            self.logs_client = get_logs_client()
```

### Integration

#### Used By
- `main.py` - `get_cloudwatch_log_groups_from_db()` extracts region from log group ARN
- Log fetching now uses: `CloudWatchFetcher(region=log_group_region)`

## [1.0.0] - 2025-11-07

### Added

#### CloudWatch Fetcher (`cloudwatch_fetcher.py`)
- `CloudWatchFetcher` class for retrieving WAF logs from CloudWatch Logs
- `list_log_groups()` - List all WAF-related log groups with prefix filtering
- `get_log_events()` - Fetch log events with time range filtering and pagination
- `get_log_streams()` - List log streams in a log group with time filtering
- `get_log_events_by_stream()` - Fetch events from specific log stream
- `estimate_log_volume()` - Estimate total log volume before fetching
- `fetch_logs_chunked()` - Fetch logs in time-based chunks for large volumes
- Automatic pagination handling with `nextToken`
- Rate limiting (5 TPS) to comply with CloudWatch Logs API limits
- Progress bars with tqdm for long-running fetches
- Support for CloudWatch Logs filter patterns
- Configurable maximum results limit
- Error handling with proper AWS error messages

#### S3 Fetcher (`s3_fetcher.py`)
- `S3Fetcher` class for retrieving WAF logs from S3 buckets
- `list_objects()` - List S3 objects with prefix and time filtering
- `download_object()` - Download individual log files with temp file support
- `read_log_file()` - Read and parse log files (gzip or plain text)
- `fetch_logs()` - Fetch all logs for a time range with progress tracking
- `fetch_logs_streaming()` - Memory-efficient streaming iterator for large datasets
- `estimate_log_volume()` - Estimate log volume and file count
- `get_bucket_info()` - Validate bucket access and get region info
- `parse_waf_bucket_arn()` - Parse S3 ARN from WAF logging configuration
- Automatic gzip decompression for compressed log files
- Date-based prefix generation (YYYY/MM/DD format)
- Temporary file management with automatic cleanup
- Support for newline-delimited JSON log format
- Progress bars for both prefix scanning and file reading
- Error handling for missing files and access denied errors

### Features

#### CloudWatch Fetcher
- **Pagination**: Automatic handling of large result sets
- **Rate Limiting**: Built-in 1-second delay every 5 requests
- **Time Filtering**: Millisecond-precision timestamp conversion
- **Progress Tracking**: Visual progress bars for user feedback
- **Volume Estimation**: Sample-based estimation before full fetch
- **Chunked Fetching**: Break large queries into manageable time windows
- **Stream-Level Access**: Ability to fetch from specific log streams
- **Filter Patterns**: Support for CloudWatch Logs filter syntax

#### S3 Fetcher
- **Compression Support**: Automatic gzip decompression
- **Date-Based Prefixes**: Efficient scanning using date hierarchy
- **Streaming Mode**: Memory-efficient iterator for large datasets
- **Temporary Files**: Automatic temp file creation and cleanup
- **Bucket Validation**: Pre-flight checks for bucket access
- **ARN Parsing**: Extract bucket and prefix from WAF logging ARNs
- **Progress Tracking**: Two-level progress (prefixes and files)
- **Error Recovery**: Graceful handling of missing or corrupted files

### Technical Details

#### CloudWatch Fetcher
- Uses `boto3.client('logs')`
- API calls: `filter_log_events`, `describe_log_groups`, `describe_log_streams`, `get_log_events`
- Rate limit: 5 TPS per region
- Default limit: 10,000 events per request
- Timestamp format: Milliseconds since epoch

#### S3 Fetcher
- Uses `boto3.client('s3')`
- API calls: `list_objects_v2`, `download_file`, `head_bucket`, `get_bucket_location`
- Supported formats: `.gz`, `.json`
- Log format: Newline-delimited JSON
- Prefix format: `YYYY/MM/DD/`

### Dependencies
- `boto3` - AWS SDK for Python
- `botocore.exceptions` - AWS error handling
- `tqdm` - Progress bars
- `gzip` - Compressed file handling
- `json` - JSON parsing
- `tempfile` - Temporary file management
- `pathlib` - Path operations

### Error Handling
- `ClientError` - AWS API errors with detailed messages
- `AccessDeniedException` - Insufficient permissions
- `ResourceNotFoundException` - Missing log groups or buckets
- `ThrottlingException` - Rate limit exceeded
- JSON parsing errors for corrupted log lines
- File I/O errors with automatic cleanup

### Performance
- CloudWatch: ~200-500 events/second (limited by API)
- S3: ~1000-5000 events/second (depends on file size)
- Memory usage: Chunked processing keeps memory bounded
- Network: Efficient batch operations with pagination

### Known Limitations
- CloudWatch rate limit of 5 TPS may slow large queries
- S3 requires scanning all date prefixes in range
- Very large log files (>100MB) may cause memory spikes
- No built-in caching of downloaded S3 files

### Future Enhancements
- [ ] Parallel S3 file downloads
- [ ] Local caching layer for S3 files
- [ ] CloudWatch Insights query support
- [ ] Support for Kinesis Data Firehose logs
- [ ] Incremental fetch from last checkpoint
- [ ] Compression ratio analysis for S3
