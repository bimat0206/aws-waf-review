

# WAF Log Retriever

The **WAF Log Retriever** is a command-line tool designed to retrieve AWS Web Application Firewall (WAF) logs from Amazon S3 or CloudWatch Logs, process them, and store them locally. It supports both interactive and non-interactive modes, allowing users to dynamically discover WAF log sources or specify them via configuration files.

## Features

- **Log Retrieval**: Fetch WAF logs from S3 buckets or CloudWatch Logs based on a specified time range.
- **Interactive Mode**: Discover and select WAF log sources interactively.
- **Non-Interactive Mode**: Specify WAF log sources via configuration for automated workflows.
- **Progress Tracking**: Displays a progress bar for S3 downloads with total size estimation.
- **Flexible Configuration**: Uses JSON configuration files for AWS profiles and WAF sources.
- **Logging**: Comprehensive logging with configurable levels (DEBUG, INFO, WARNING, ERROR) to both console and file.
- **Storage Management**: Organizes logs in a structured directory with optional gzip compression and retention policies.
- **Concurrent Retrieval**: Supports batch retrieval of logs from multiple sources with configurable concurrency.

## Prerequisites

- **Go**: Version 1.18 or higher.
- **AWS Credentials**: Configured via AWS CLI or `~/.aws/credentials` with appropriate permissions for WAF, S3, and CloudWatch Logs.
- **Dependencies**: Install required Go packages:
  ```bash
  go get github.com/aws/aws-sdk-go-v2
  go get github.com/schollz/progressbar/v3
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd waf-log-retriever
   ```

2. Build the application:
   ```bash
   go build -o waf-log-retriever
   ```

## Configuration

### `config.json`
Defines AWS profiles for authentication:
```json
{
  "aws_profiles": [
    {
      "profileName": "default",
      "region_name": "us-east-1"
    }
  ]
}
```

### `waf-config.json` (Optional)
Predefines WAF log sources for non-interactive mode:
```json
{
  "waf_log_sources": [
    {
      "profileName": "default",
      "region": "us-east-1",
      "webACLName": "my-web-acl",
      "webACLID": "123e4567-e89b-12d3-a456-426614174000",
      "logSourceName": "my-logs",
      "logSourceType": "s3",
      "destinationARN": "arn:aws:s3:::my-waf-logs-bucket",
      "s3BucketName": "my-waf-logs-bucket",
      "cwLogsGroupName": ""
    }
  ]
}
```

## Folder Structure

The project is organized as follows:

```
waf-log-retriever/
├── cli/              # Command-line interface utilities
│   └── cli.go        # Functions for user interaction (e.g., WAF source selection)
├── aws/              # AWS service interactions
│   └── aws.go        # Logic for WAF, S3, and CloudWatch Logs operations
├── config/           # Configuration parsing and management
│   └── config.go     # Loads and validates config.json and waf-config.json
├── logging/          # Logging functionality
│   └── logging.go    # Logger setup and leveled logging implementation
├── storage/          # File storage and management
│   └── storage.go    # Handles log file writing, compression, and cleanup
├── main.go           # Application entry point and core logic
├── config.json       # Default AWS profile configuration (required)
├── waf-config.json   # Optional WAF log source configuration
└── logs/             # Default directory for application logs
    └── app/          # Structured logging directory (YYYY-MM-DD/)
```

- **Source Code**: Organized into packages for modularity and maintainability.
- **Configuration Files**: Placed in the root directory for easy access.
- **Logs**: Generated logs are stored in a nested structure under `logs/app/` by date.

## Usage

### Command-Line Flags
- `-config`: Path to `config.json` (default: `"config.json"`).
- `-waf-config`: Path to `waf-config.json` (default: `"waf-config.json"`).
- `-profile`: AWS profile name from `config.json`.
- `-waf-source`: WAF log source name from `waf-config.json` (non-interactive mode).
- `-start-date`: Start date (e.g., `2025-02-01` or `2025-02-01T12:00:00Z`).
- `-end-date`: End date (e.g., `2025-02-22` or `2025-02-22T23:59:59Z`).
- `-output-dir`: Directory for storing logs (default: `"../logs/raw"`).
- `-log-level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) (default: `"INFO"`).
- `-interactive`: Enable interactive mode (default: `false`).

### Examples

#### Interactive Mode
Discover and select WAF sources:
```bash
./waf-log-retriever -config config.json -interactive
```
- Lists discovered WAF log sources.
- Prompts for selection and time range if not provided.

#### Non-Interactive Mode
Retrieve logs for a specific WAF source:
```bash
./waf-log-retriever -config config.json -waf-config waf-config.json -profile default -waf-source my-logs -start-date 2025-02-01 -end-date 2025-02-22
```

#### Specify Output Directory and Log Level
```bash
./waf-log-retriever -config config.json -interactive -output-dir ./logs -log-level DEBUG
```

## Output

- Logs are stored in `<output-dir>/<profile>/<webACLName>/<YYYY>/<MM>/<DD>/<HH>/`.
- S3 logs maintain their original filenames (e.g., `waf_log_20250201_120000.log`).
- CloudWatch Logs are saved as JSON files (e.g., `waf_logs_20250201_120405.json`).
- Log files are optionally compressed with gzip.

## Logging

Logs are written to both console and a file in `logs/app/YYYY-MM-DD/waf-retriever_YYYYMMDD_HHMMSS.log`.

## Error Handling

- Invalid configurations or permissions result in detailed error messages.
- The tool exits with a non-zero status code on failure.

## Development

### Project Structure
- `cli/`: Command-line interface utilities.
- `aws/`: AWS service interactions (WAF, S3, CloudWatch Logs).
- `config/`: Configuration parsing and management.
- `logging/`: Logging functionality.
- `storage/`: File storage and management.
- `main.go`: Entry point and application logic.

### Adding Features
- Extend `aws.go` for new AWS services or log formats.
- Update `cli.go` for additional user prompts.
- Modify `storage.go` for custom storage options.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bugs or feature requests.

