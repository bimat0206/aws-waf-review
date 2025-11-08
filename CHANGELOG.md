# Changelog

All notable changes to the AWS WAF Security Analysis Tool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] - 2025-11-08

### Added

- **Sheet Descriptions**: Added comprehensive descriptions to all Excel report sheets explaining their purpose and metrics
  - Executive Summary: Added AWS account information section and detailed metric explanations
  - Traffic Analysis: Added description explaining daily trends and geographic distribution
  - Rule Effectiveness: Added detailed explanations of hit rates, block rates, and color coding
  - Client Analysis: Added descriptions for IP tracking, bot detection, and user agent analysis
  - Geographic Blocked Traffic: Added threat level criteria and risk assessment explanations
- **AWS Account Information**: Executive Summary now displays AWS Account ID, Account Name (alias), Region, and Profile at the top of the report
- **Timezone Configuration**: Added interactive timezone configuration option in main menu
  - Users can select from preset timezones (UTC, UTC+7, UTC+8, UTC+9, UTC-5, UTC-8) or enter custom timezone
  - Default timezone is UTC+7 (Bangkok/Jakarta/Ho Chi Minh)
  - Timezone information is displayed in Executive Summary sheet for report clarity
  - Current timezone shown in interactive menu header
- **Enhanced Empty Data Handling**: Traffic Analysis sheet now shows helpful messages when daily trend data is unavailable

### Changed

- **Chart Positioning**: Repositioned all visualization charts to the right side of data tables for improved readability and professional layout
  - Executive Summary: Removed action distribution chart to keep focus on summary data
  - Traffic Analysis: Daily trends and geographic charts now positioned on the right (column G)
  - Rule Effectiveness: Rule and attack type charts positioned on the right (column I)
  - Geographic Blocked Traffic: Geographic threat chart positioned on the right (column H)
  - Client Analysis: Hourly pattern chart positioned on the right (column H)
  - Rule Action Distribution: Action distribution chart positioned on the right (column I)
- **Chart Sizing**: Optimized chart dimensions for side-by-side layout (650-700px width, 350-450px height)

### Fixed

- **Excel Report Generation**: Fixed `NameError: name 'PatternFill' is not defined` in Geographic Blocked Traffic sheet by adding missing import
- **Metrics Calculator Web ACL Filtering**: Added missing Web ACL ID filtering to `get_attack_type_distribution()` and `get_bot_traffic_analysis()` methods to ensure accurate metrics when analyzing specific Web ACLs

## [1.3.0] - 2025-11-07

### Added

- **Data-Rich Prompt Exports**: Prompt exporter now injects real metrics, rule inventories, cost summaries, and attack trends into every template, eliminating manual placeholder replacement before sharing with LLMs.

### Changed

- **Prompt Export API**: `PromptExporter.export_all_prompts()` now accepts logging configuration metadata so each compliance prompt includes accurate destination details.
- **Optional Colored Logging**: The tool now falls back to Python's standard logging formatter when `coloredlogs` is not installed, making quick runs on new environments smoother.

## [1.2.0] - 2025-11-07

### Added

#### Account Name/Alias Support
- **AWS Account Alias Fetching**: Automatically fetches AWS account alias (friendly name) if configured
- **Enhanced Naming**: Directory and file names use format `{alias}_{account_id}` when alias exists
  - Database files: `data/{alias}_{account_id}/{alias}_{account_id}_waf_analysis.duckdb`
  - Excel reports: `output/{alias}_{account_id}/{alias}_{account_id}_{timestamp}_waf_report.xlsx`
  - Application logs: `logs/{alias}_{account_id}/`
  - Exported prompts: `exported-prompt/{alias}_{account_id}/`
- **Graceful Fallback**: If no alias set, uses account ID only: `{account_id}`
- **IAM Permission**: Requires `iam:ListAccountAliases` permission (gracefully handles denial)

### Changed

#### Directory and File Naming
- Updated naming convention from `{account_id}` to `{alias}_{account_id}` format
- Makes multi-account analysis more user-friendly with recognizable names
- Backward compatible: Falls back to account ID if alias not available

## [1.1.0] - 2025-11-07

### Added

#### Multi-Account Support
- **Account-Specific Directories**: Organized data by AWS Account ID
  - Database files: `data/{account_id}/{account_id}_waf_analysis.duckdb`
  - Excel reports: `output/{account_id}/{account_id}_{timestamp}_waf_report.xlsx`
  - Application logs: `logs/{account_id}/`
  - Exported prompts: `exported-prompt/{account_id}/`
- **Automatic Account Detection**: Uses AWS STS to get current account ID
- **Timestamp in Reports**: All generated reports include timestamp in filename for versioning
- **Directory Auto-Creation**: Automatically creates account-specific subdirectories on first run

#### Enhanced Time Window Selection
- **Today Analysis**: Analyze WAF logs from midnight UTC to current time
- **Yesterday Analysis**: Analyze full 24-hour period for previous day
- **Past Week Analysis**: Analyze last 7 days of WAF logs
- **Custom Date Range**: User-specified start and end dates with flexible parsing
- **Interactive Menu**: Six time window options in interactive mode:
  1. Today (since midnight UTC)
  2. Yesterday (full 24 hours)
  3. Past week (last 7 days)
  4. Past 3 months (~90 days)
  5. Past 6 months (~180 days)
  6. Custom date range (user input)
- **Flexible Date Parsing**: Supports `YYYY-MM-DD` and `YYYY-MM-DD HH:MM:SS` formats
- **Date Validation**: Ensures end date is after start date with clear error messages

#### Auto-Detect CloudWatch Log Groups
- **Database-Driven Discovery**: Automatically extract log groups from Web ACL logging configurations
- **Region-Aware Fetching**: Parse region from CloudWatch log ARN for correct API calls
- **Interactive Display**: Show log groups with associated Web ACL names and regions
- **ARN Parsing**: Extract log group name and region from CloudWatch destination ARNs
- **Fallback Support**: Option to use CloudWatch API if no log groups in database

#### Prompt Template System
- **Template Directory**: `config/prompts/` for version-controlled prompt templates
- **Export Directory**: `exported-prompt/{account_id}/` for filled prompts with WAF data (gitignored)
- **Account Separation**: Each AWS account has separate directory for exported prompts

### Changed

#### Directory Structure
- Updated from flat structure to account-organized hierarchy
- Changed database naming from `waf_analysis.duckdb` to `{account_id}_waf_analysis.duckdb`
- Changed report naming from `waf_report_{timestamp}.xlsx` to `{account_id}_{timestamp}_waf_report.xlsx`
- Separated prompt templates (version controlled) from exports (gitignored)

#### Time Window Selection
- Changed `interactive_time_window()` return type from `int` to `Tuple[datetime, datetime]`
- Expanded time window options from 2 to 6 in interactive mode
- All time window functions return consistent `(start_time, end_time)` tuples

#### CloudWatch Log Fetching
- CloudWatch fetcher now accepts region parameter for multi-region support
- Log fetching uses region from log group ARN instead of current AWS CLI region
- Fixed bug where CloudFront WAF logs failed when user region differed from us-east-1

### Fixed

#### CRITICAL: CloudWatch Region Mismatch (Commit 2f239a8)
- **Issue**: CloudWatch log fetching failed with `ResourceNotFoundException` when current AWS region differed from log group's region
- **Root Cause**: CloudFront WAF logs are typically in us-east-1, but tool used user's current region
- **Fix**: Parse region from CloudWatch log group ARN and use region-specific client
- **Impact**: CloudFront WAF log analysis now works from any AWS region

#### CRITICAL: JSON Serialization Error (Commit b12f0d6)
- **Issue**: `TypeError: Object of type datetime is not JSON serializable` when storing WAF logs
- **Root Cause**: Log parser converts timestamps to datetime objects, but `json.dumps()` couldn't serialize them
- **Fix**: Created custom `DateTimeEncoder` class to convert datetime to ISO 8601 strings
- **Impact**: All WAF logs now store correctly without serialization errors

### Technical Details

#### New Functions (utils/time_helpers.py)
- `get_today_window()` - Time window for today (midnight UTC to now)
- `get_yesterday_window()` - Full 24-hour period for yesterday
- `get_past_week_window()` - Last 7 days from current time
- `get_custom_window(start_date_str, end_date_str)` - Parse custom date range

#### New Functions (main.py)
- `get_cloudwatch_log_groups_from_db(db_manager)` - Extract log groups from database
- Updated `setup_directories(account_id)` - Create account-specific directories

#### Database Changes (storage/duckdb_manager.py)
- Added `DateTimeEncoder` class for JSON serialization
- All `json.dumps()` calls now use `cls=DateTimeEncoder` parameter

### Documentation

#### Updated CHANGELOGs
- `src/CHANGELOG.md` - Version 1.3.0 with multi-account support
- `src/utils/CHANGELOG.md` - Version 1.1.0 with time window enhancements
- `src/storage/CHANGELOG.md` - Version 1.0.3 with DateTimeEncoder fix
- `src/fetchers/CHANGELOG.md` - Version 1.0.1 with region-aware fetching

### Security

#### Data Isolation
- Each AWS account's data stored in separate directories
- Prevents data mixing when analyzing multiple accounts
- Exported prompts (may contain sensitive data) are gitignored per account

## [1.0.0] - 2025-11-07

### Added

#### Core Features
- Complete AWS WAF security analysis solution with modular architecture
- Zero persistent connection model - all data fetched once and stored locally
- DuckDB-based local storage for efficient analytics
- Multi-sheet Excel report generation with embedded visualizations
- LLM prompt templates for AI-powered security analysis
- Command-line interface with comprehensive options
- Progress tracking with tqdm for all long-running operations
- Color-coded logging with coloredlogs for better visibility

#### Data Collection
- CloudWatch Logs fetcher with automatic pagination
- S3 log fetcher with compressed file support (gzip)
- AWS WAF configuration fetcher (Web ACLs, rules, associations)
- Support for both REGIONAL and CLOUDFRONT scopes
- Configurable time windows (3 or 6 months)
- Automatic rate limiting and retry logic
- Volume estimation before fetching logs

#### Data Processing
- WAF log parser supporting official AWS log schema
- Normalization of logs from multiple sources (CloudWatch, S3)
- Configuration processor for Web ACLs and rule analysis
- Metrics calculator with 15+ security analytics functions
- Attack type classification (SQLi, XSS, scanners, bots, etc.)
- Geographic threat scoring
- Rule effectiveness analysis
- Security posture scoring (0-100)

#### Storage
- DuckDB database with 5 tables and 8 indexes
- Bulk insert operations with chunking for large datasets
- Support for querying with SQL
- Export capabilities to Parquet format
- Database optimization with VACUUM
- Automatic schema initialization

#### Reporting
- Multi-sheet Excel workbook generation (6 sheets)
- Executive Summary with KPIs and charts
- Inventory of Web ACLs and protected resources
- Traffic Analysis with geographic distribution
- Rule Effectiveness with performance metrics
- Client Analysis with top IPs and bot detection
- LLM Recommendations template sheet
- Embedded matplotlib charts (pie, bar, line, horizontal bar)
- Professional styling with conditional formatting
- Color-coded warnings for security gaps

#### LLM Integration
- Security effectiveness analysis prompt template
- False positive analysis prompt template
- Rule optimization prompt template
- Compliance gap analysis prompt template (OWASP, PCI-DSS, etc.)
- Structured output format for prioritized recommendations

#### Configuration
- WAF log schema definition (JSON)
- Support for all official WAF log fields
- Action validation (ALLOW, BLOCK, COUNT, CAPTCHA, CHALLENGE)
- Resource type detection (ALB, API Gateway, CloudFront)

#### Documentation
- Comprehensive README with installation instructions
- Usage examples and command-line options
- Troubleshooting guide
- Advanced usage examples (SQL queries, programmatic access)
- Database schema documentation
- Performance considerations and best practices

#### Developer Experience
- Modular architecture with clear separation of concerns
- Type hints throughout the codebase
- Comprehensive docstrings for all functions and classes
- Proper error handling and logging
- PEP 8 compliant code formatting
- Context managers for resource management

### Technical Details

#### Dependencies
- boto3==1.34.0 - AWS SDK
- duckdb==0.10.0 - Local database
- pandas==2.2.0 - Data processing
- openpyxl==3.1.2 - Excel generation
- matplotlib==3.8.0 - Visualizations
- tqdm==4.66.0 - Progress bars
- coloredlogs==15.0.1 - Colored logging

#### Database Schema
- `web_acls` - Web ACL configurations
- `rules` - Individual WAF rules
- `resource_associations` - Protected resources
- `logging_configurations` - Logging settings
- `waf_logs` - Parsed log entries with full metadata

#### Supported AWS Services
- AWS WAFv2 (Regional and CloudFront)
- CloudWatch Logs
- Amazon S3
- AWS STS (for credential verification)

#### Metrics Calculated
- Total requests and action distribution
- Block rate and security posture score
- Rule hit rates and effectiveness
- Geographic threat distribution
- Attack type classification
- Hourly and daily traffic patterns
- Bot traffic analysis (JA3/JA4)
- Top blocked IPs and user agents
- Resource protection coverage

### Security Features
- No credential storage - uses AWS CLI profiles
- Local-only data storage
- No cloud uploads
- Data sanitization in logs
- Graceful handling of missing permissions
- Validation of all AWS responses

### Known Limitations
- CloudWatch Logs rate limited to 5 TPS per region
- Large datasets (millions of logs) may require significant memory
- Excel chart generation may be slow for very large datasets
- WAF v1 (Classic) not supported
- Requires Python 3.9 or higher

### Platform Support
- macOS (primary target)
- Linux (tested)
- Windows (should work, but not primary target)

## [1.3.4] - 2025-11-08

### Fixed
- **Excel Report Issue**: Resolved empty reports by fixing Web ACL ID extraction in log parser and adding database migration. The logs contain full ARNs in the `webaclId` field (e.g., "arn:aws:wafv2:...:webacl/name/id") but the database stores only the ID part. The log parser now extracts just the ID portion from the ARN to ensure proper table joins between log data and Web ACL configuration data. Added automatic migration for existing databases to convert old ARN format log entries to ID format.

## [1.3.3] - 2025-11-08

### Changed
- **Performance Improvements**: 
  - Added composite indexes to DuckDB manager for improved query performance
  - Optimized bulk log insertion in DuckDB manager to reduce JSON processing and database round trips
  - Reduced database round trips in metrics calculator by fetching total requests in a single query
  - Improved user-agent extraction efficiency in log parser
  - Enhanced batch parsing performance in log parser
  - Added parallel processing for S3 log downloads using ThreadPoolExecutor
  - Optimized bucket generation functions in time helpers to use list comprehensions
  - Implemented bulk data insertion method for Excel report generation

---

[1.0.0]: https://github.com/bimat0206/aws-waf-review/releases/tag/v1.0.0
## [1.3.1] - 2025-11-07

### Fixed

- **DuckDB log ingestion**: Resolved a `Constraint Error: Duplicate key "log_id: 0"` when importing multiple CloudWatch batches. `insert_log_entries()` now seeds each batch with `MAX(log_id)+1`, preventing primary-key collisions during repeated log fetches.
## [1.3.2] - 2025-11-07

### Added

- **Raw Log Archives**: Every CloudWatch or S3 fetch now exports the untouched log events as JSONL under `raw-logs/{alias}_{account_id}/<source>/...`, mirroring the `data/` directory structure for each account. This makes it easier to diff, replay, or troubleshoot parsing issues when Excel outputs look empty.
