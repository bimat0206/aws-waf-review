# WAF Logs Parser

A robust tool for extracting and processing AWS WAF logs from CloudWatch Log exports.

## Overview

WAF Logs Parser is a Go application designed to extract the inner JSON data from the `@message` field in AWS WAF logs. It handles multi-line JSON objects, validates the data integrity, and provides detailed processing metrics.

## Features

- Extracts and processes nested JSON from AWS WAF logs
- Handles multi-line JSON objects correctly
- Validates JSON data integrity
- Supports pretty-printing of extracted JSON
- Provides detailed processing metrics and debug information
- Robust error handling and recovery

## Installation

### Prerequisites

- Go 1.16 or later

### Build from Source

```bash
# Clone the repository (if applicable)
git clone https://github.com/yourusername/waf-logs-parser.git
cd waf-logs-parser

# Build the application
go build -o waf_logs_parser main.go
```

Alternatively, you can download the pre-built binary from the releases page.

## Usage

### Basic Usage

```bash
./waf_logs_parser -input your_waf_logs.json -output extracted_data.json
```

### Command Line Options

| Flag | Description | Default |
|------|-------------|---------|
| `-input` | Input file path (required) | - |
| `-output` | Output file path | stdout |
| `-pretty` | Pretty-print JSON output | false |
| `-debug` | Enable debug output | false |
| `-validate` | Validate inner JSON before processing | true |

### Examples

**Basic extraction:**
```bash
./waf_logs_parser -input waf_logs.json -output extracted.json
```

**Pretty-print the output:**
```bash
./waf_logs_parser -input waf_logs.json -output extracted.json -pretty
```

**Enable debug information:**
```bash
./waf_logs_parser -input waf_logs.json -output extracted.json -debug
```

**Skip validation for better performance:**
```bash
./waf_logs_parser -input waf_logs.json -output extracted.json -validate=false
```

**Output to console instead of file:**
```bash
./waf_logs_parser -input waf_logs.json
```

## Input Format

The tool expects CloudWatch log exports containing AWS WAF logs. Each log entry should be a JSON object with an `@message` field that contains the actual WAF log data as a JSON string.

Example input format:
```json
{
    "@message": "{\"timestamp\":1740095950321,\"formatVersion\":1,\"webaclId\":\"arn:aws:wafv2:us-east-1:123456789012:global/webacl/example-acl/abc123\",\"terminatingRuleId\":\"example-rule\",\"terminatingRuleType\":\"REGULAR\",\"action\":\"ALLOW\",\"httpRequest\":{\"clientIp\":\"203.0.113.1\",\"country\":\"US\",\"headers\":[{\"name\":\"User-Agent\",\"value\":\"Mozilla/5.0\"}]}}",
    "@ptr": "abcdefghijklmnopqrstuvwxyz",
    "@timestamp": "2025-02-20 23:59:10.321"
}
```

## Output Format

The tool extracts the JSON data from the `@message` field and outputs it as individual JSON objects, one per line.

Example output:
```json
{"timestamp":1740095950321,"formatVersion":1,"webaclId":"arn:aws:wafv2:us-east-1:123456789012:global/webacl/example-acl/abc123","terminatingRuleId":"example-rule","terminatingRuleType":"REGULAR","action":"ALLOW","httpRequest":{"clientIp":"203.0.113.1","country":"US","headers":[{"name":"User-Agent","value":"Mozilla/5.0"}]}}
```

With the `-pretty` option, the output will be formatted with proper indentation.

## Processing Summary

After processing, the tool outputs a summary to stderr:

```
Processing summary:
- Total JSON objects found: 123
- Successfully processed: 120 records
- Valid @message fields: 118
- Invalid @message fields: 2
- Skipped records: 3
```

This summary helps you verify that all expected records were processed correctly.

## Error Handling

The tool is designed to continue processing even if individual records have errors. When using the `-debug` flag, detailed information about problematic records will be output to stderr.

## Troubleshooting

If you encounter issues:

1. Use the `-debug` flag to see detailed information about the processing.
2. Check for any JSON syntax errors in your input file.
3. Ensure your input file contains valid WAF log entries with the expected structure.
4. Check file permissions for reading the input and writing to the output.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- AWS WAF and CloudWatch documentation for the log format specifications