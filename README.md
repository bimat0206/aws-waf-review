# AWS WAF Security Analysis Tool

A comprehensive Python application for analyzing AWS WAF (Web Application Firewall) configurations and logs. This tool helps security teams identify security gaps, optimize rules, reduce false positives, and improve their overall security posture.

## Features

- **Zero Persistent Connections**: Fetches all data once and stores it locally in DuckDB
- **Multi-Source Log Collection**: Supports both CloudWatch Logs and S3 as log sources
- **Comprehensive Analysis**: Analyzes WAF configurations, rules, traffic patterns, and attack types
- **Rich Excel Reports**: Generates multi-sheet Excel workbooks with visualizations
- **LLM-Ready**: Includes prompt templates for AI-powered security analysis
- **Modular Architecture**: Clean separation of concerns for easy maintenance and extension

## Architecture

```
aws-waf-analyzer/
├── config/                  # Configuration files
│   ├── prompts/            # LLM prompt templates
│   │   ├── security_effectiveness.md
│   │   ├── false_positive_analysis.md
│   │   ├── rule_optimization.md
│   │   └── compliance_gap_analysis.md
│   └── waf_schema.json     # WAF log schema definition
├── src/                    # Source code
│   ├── fetchers/          # Data fetching modules
│   ├── processors/        # Data processing modules
│   ├── storage/           # Database management
│   ├── reporters/         # Report generation
│   ├── utils/             # Utility functions
│   └── main.py           # Main orchestration script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Prerequisites

- **Python 3.9 or higher**
- **AWS CLI** configured with appropriate credentials
- **IAM Permissions**: The AWS profile must have permissions for:
  - `wafv2:ListWebACLs`
  - `wafv2:GetWebACL`
  - `wafv2:ListResourcesForWebACL`
  - `wafv2:GetLoggingConfiguration`
  - `logs:DescribeLogGroups`
  - `logs:FilterLogEvents`
  - `s3:ListBucket`
  - `s3:GetObject`

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd aws-waf-review
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # OR
   .\venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### AWS Credentials

Configure AWS CLI with your profile:

```bash
aws configure --profile <profile-name>
```

Or export AWS credentials:

```bash
export AWS_PROFILE=<profile-name>
export AWS_DEFAULT_REGION=<region>
```

### Verify Access

Test your AWS access:

```bash
aws wafv2 list-web-acls --scope REGIONAL
aws logs describe-log-groups --log-group-name-prefix aws-waf-logs
```

## Usage

### Basic Usage

Run the analyzer with default settings (3 months of logs, REGIONAL scope):

```bash
python src/main.py
```

The tool will:
1. Verify AWS credentials
2. Fetch WAF configurations
3. Prompt you to select a log source (CloudWatch or S3)
4. Fetch and parse logs
5. Calculate security metrics
6. Generate an Excel report

### Command-Line Options

```bash
python src/main.py [OPTIONS]

Options:
  --db-path PATH          Path to DuckDB database file (default: waf_analysis.duckdb)
  --months {3,6}          Number of months of logs to analyze (default: 3)
  --scope {REGIONAL,CLOUDFRONT}  WAF scope to analyze (default: REGIONAL)
  --skip-config           Skip fetching WAF configurations
  --skip-logs            Skip fetching logs
  --log-source {cloudwatch,s3}  Log source
  --log-group NAME       CloudWatch log group name
  --s3-bucket NAME       S3 bucket name
  --s3-prefix PREFIX     S3 key prefix
  --output PATH          Output Excel report filename
```

### Example Usage Scenarios

**Analyze 6 months of CloudWatch logs**:
```bash
python src/main.py --months 6 --log-source cloudwatch --log-group aws-waf-logs-myapp
```

**Analyze S3 logs for CloudFront WAF**:
```bash
python src/main.py --scope CLOUDFRONT --log-source s3 \
  --s3-bucket my-waf-logs --s3-prefix cloudfront/waf/
```

**Generate report from existing database**:
```bash
python src/main.py --skip-config --skip-logs --output custom_report.xlsx
```

**Fetch configs only (no logs)**:
```bash
python src/main.py --skip-logs
```

## Excel Report Structure

The generated Excel report contains the following sheets:

### 1. Executive Summary
- High-level metrics and KPIs
- Security posture score
- Action distribution charts
- Time range and coverage information

### 2. Inventory
- List of all Web ACLs with configurations
- Protected resources (ALB, API Gateway, CloudFront)
- Logging status and destinations
- Color-coded warnings for missing logging

### 3. Traffic Analysis
- Daily traffic trends (line charts)
- Geographic distribution of traffic and threats
- Top countries by blocked requests
- Threat scores by geography

### 4. Rule Effectiveness
- Rule performance metrics (hit count, block rate)
- Rules with 0% hit rate (potentially redundant)
- Attack type distribution
- Top blocking rules with visualizations

### 5. Client Analysis
- Top blocked IP addresses
- Bot traffic analysis (JA3/JA4 fingerprints)
- User-Agent patterns
- Hourly traffic patterns

### 6. LLM Recommendations
- Template for AI-generated security findings
- Structured format for prioritized recommendations
- Action items organized by priority level

## LLM Prompt Templates

The `config/prompts/` directory contains markdown templates for AI-powered analysis:

### security_effectiveness.md
Analyzes rule effectiveness, identifies gaps, and recommends improvements.

**Usage**:
1. Open the template
2. Replace placeholders with data from the Excel report
3. Submit to your preferred LLM (Claude, GPT-4, etc.)
4. Review and validate recommendations
5. Populate the "LLM Recommendations" sheet in Excel

### false_positive_analysis.md
Identifies patterns in false positives and suggests tuning.

### rule_optimization.md
Recommends rule ordering, consolidation, and performance improvements.

### compliance_gap_analysis.md
Evaluates compliance with OWASP Top 10, PCI-DSS, and other frameworks.

## Database Schema

The tool uses DuckDB with the following tables:

- **web_acls**: Web ACL configurations
- **rules**: Individual WAF rules
- **resource_associations**: Resources protected by each Web ACL
- **logging_configurations**: Logging destinations and settings
- **waf_logs**: Parsed WAF log entries with full metadata

You can query the database directly:

```bash
duckdb waf_analysis.duckdb
```

```sql
-- Example queries
SELECT COUNT(*) FROM waf_logs WHERE action = 'BLOCK';
SELECT country, COUNT(*) as requests FROM waf_logs GROUP BY country ORDER BY requests DESC;
SELECT terminating_rule_id, COUNT(*) as hits FROM waf_logs GROUP BY terminating_rule_id ORDER BY hits DESC LIMIT 10;
```

## Security Metrics Calculated

- **Summary Metrics**: Total requests, block rate, unique IPs, countries
- **Action Distribution**: Breakdown of ALLOW, BLOCK, COUNT, CAPTCHA, CHALLENGE actions
- **Rule Effectiveness**: Hit rate, block rate, and effectiveness score per rule
- **Geographic Distribution**: Traffic and threat patterns by country
- **Attack Type Classification**: SQL injection, XSS, scanners, bots, etc.
- **Temporal Patterns**: Hourly and daily traffic trends
- **Bot Analysis**: JA3/JA4 fingerprint analysis, user-agent patterns
- **Security Posture Score**: 0-100 score based on coverage, effectiveness, and configuration

## Troubleshooting

### No Web ACLs Found

**Issue**: "No Web ACLs found in REGIONAL scope"

**Solutions**:
- Verify you're using the correct AWS profile and region
- Try `--scope CLOUDFRONT` if analyzing CloudFront WAFs
- Check IAM permissions for `wafv2:ListWebACLs`

### No Logs Found

**Issue**: "No log events found in CloudWatch"

**Solutions**:
- Verify logging is enabled for your Web ACL
- Check the log group name (should start with `aws-waf-logs-`)
- Adjust the time window with `--months 6`
- Verify IAM permissions for CloudWatch Logs

### Access Denied Errors

**Issue**: "Access denied" when fetching data

**Solutions**:
- Run `aws sts get-caller-identity` to verify credentials
- Check IAM permissions listed in Prerequisites
- Ensure you have access to the specific resources (log groups, S3 buckets)

### Memory Issues with Large Datasets

**Issue**: Out of memory when processing millions of logs

**Solutions**:
- The tool uses chunked processing for large S3 datasets
- For CloudWatch, consider breaking into smaller time windows
- Increase available RAM or use a machine with more memory

### Import Errors

**Issue**: "ModuleNotFoundError" when running

**Solutions**:
- Ensure you're in the virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`
- Verify Python version: `python --version` (must be 3.9+)

## Performance Considerations

- **CloudWatch Logs**: Rate limited to 5 TPS per region. Large queries may take time.
- **S3 Logs**: Faster than CloudWatch but requires scanning date-based prefixes
- **Database Size**: Expect ~100-200 bytes per log entry in DuckDB
- **Excel Generation**: Charts are generated as embedded images; large datasets may take several minutes

## Best Practices

1. **Start Small**: Begin with 3 months of logs to understand data volume
2. **Regular Analysis**: Run monthly to track security posture trends
3. **Validate AI Recommendations**: Always review LLM suggestions before implementing
4. **Backup Databases**: The DuckDB file contains all your analysis data
5. **Version Control Configs**: Keep snapshots of WAF configurations over time
6. **Incremental Updates**: Use `--skip-config` when only updating logs

## Advanced Usage

### Custom SQL Queries

```python
from src.storage.duckdb_manager import DuckDBManager

db = DuckDBManager('waf_analysis.duckdb')
conn = db.get_connection()

# Custom analysis
result = conn.execute("""
    SELECT
        DATE(timestamp) as date,
        terminating_rule_id,
        COUNT(*) as blocks
    FROM waf_logs
    WHERE action = 'BLOCK'
    GROUP BY date, terminating_rule_id
    ORDER BY date, blocks DESC
""").df()

print(result)
```

### Export to Parquet

```bash
duckdb waf_analysis.duckdb -c "COPY waf_logs TO 'waf_logs.parquet' (FORMAT PARQUET)"
```

### Programmatic Access

```python
from src.processors.metrics_calculator import MetricsCalculator
from src.storage.duckdb_manager import DuckDBManager

db = DuckDBManager('waf_analysis.duckdb')
calculator = MetricsCalculator(db)

# Get specific metrics
summary = calculator.get_summary_metrics()
rules = calculator.get_rule_effectiveness()
geo = calculator.get_geographic_distribution()

print(f"Total requests: {summary['total_requests']}")
print(f"Block rate: {summary['block_rate_percent']}%")
```

## Contributing

Contributions are welcome! Areas for improvement:

- Additional visualization types
- Support for WAF v1 (Classic)
- Integration with SIEM platforms
- Real-time monitoring mode
- Automated remediation suggestions
- Custom rule development assistance

## License

MIT License - See LICENSE file for details

## Changelog

### Version 1.0.0 (Initial Release)
- Complete WAF configuration analysis
- CloudWatch and S3 log fetching
- Multi-sheet Excel reports with visualizations
- LLM prompt templates for AI-powered analysis
- DuckDB local storage
- Comprehensive metrics calculation

## Acknowledgments

- AWS WAF documentation and best practices
- OWASP Top 10 security framework
- DuckDB for efficient local analytics
- OpenPyXL for Excel report generation
