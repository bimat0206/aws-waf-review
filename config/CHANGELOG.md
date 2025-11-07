# Changelog - Configuration

All notable changes to the configuration files and templates will be documented in this file.

## [1.0.0] - 2025-11-07

### Added

#### WAF Schema (`waf_schema.json`)
- Complete AWS WAF log schema definition based on official AWS documentation
- **Required Fields** (8 fields):
  - `timestamp` - Request timestamp
  - `action` - WAF action taken (ALLOW, BLOCK, COUNT, CAPTCHA, CHALLENGE)
  - `clientIp` - Client IP address
  - `country` - Country code from geo-detection
  - `uri` - Requested URI
  - `httpMethod` - HTTP method (GET, POST, etc.)
  - `httpVersion` - HTTP version (HTTP/1.1, HTTP/2)
  - `httpStatus` - HTTP status code

- **Security Fields** (6 fields):
  - `terminatingRuleId` - Rule that terminated evaluation
  - `terminatingRuleType` - Type of terminating rule
  - `ruleGroupList` - List of rule groups evaluated
  - `labels` - Labels applied to request
  - `ja3Fingerprint` - JA3 TLS fingerprint
  - `ja4Fingerprint` - JA4 TLS fingerprint

- **Request Fields** (3 fields):
  - `requestHeaders` - HTTP request headers
  - `requestUri` - Full request URI
  - `httpRequest` - Complete HTTP request object

- **Optional Fields** (8 fields):
  - `webaclId` - Web ACL identifier
  - `terminatingRuleMatchDetails` - Match details
  - `httpSourceName` - Source name (ALB, API Gateway, etc.)
  - `httpSourceId` - Source resource ID
  - `rateBasedRuleList` - Rate-based rules evaluated
  - `nonTerminatingMatchingRules` - Non-terminating matches
  - `requestHeadersInserted` - Headers inserted by WAF
  - `responseCodeSent` - Response code sent to client

- **Action Values** (5 values):
  - ALLOW - Request allowed
  - BLOCK - Request blocked
  - COUNT - Request counted (not blocked)
  - CAPTCHA - CAPTCHA challenge issued
  - CHALLENGE - Challenge issued

- **Resource Types** (3 types):
  - ALB - Application Load Balancer
  - API_GATEWAY - API Gateway REST/HTTP API
  - CLOUDFRONT - CloudFront distribution

#### LLM Prompt Templates

##### Security Effectiveness Analysis (`prompts/security_effectiveness.md`)
- **Purpose**: Analyze WAF rule effectiveness and identify security gaps
- **Input Placeholders**:
  - `{web_acl_config}` - Web ACL configuration JSON
  - `{rule_metrics}` - Rule performance metrics JSON
  - `{top_blocked_requests}` - Most blocked request patterns
  - `{geo_distribution}` - Geographic threat data

- **Analysis Requirements** (5 areas):
  1. Identify rules with 0% hit rate (potentially redundant)
  2. Flag rules with high false positive rates (>10%)
  3. Recommend rule prioritization based on threat severity
  4. Identify gaps in attack pattern coverage
  5. Suggest managed rule groups to add

- **Output Structure**:
  - Critical Findings (immediate action)
  - High Priority Recommendations (30 days)
  - Medium Priority Optimizations (90 days)
  - Low Priority Suggestions (nice to have)

- **Security Context**: Production environment with mixed traffic

##### False Positive Analysis (`prompts/false_positive_analysis.md`)
- **Purpose**: Identify and reduce false positives
- **Input Placeholders**:
  - `{blocked_patterns}` - Patterns in blocked requests
  - `{legitimate_traffic_baseline}` - Normal traffic patterns
  - `{rule_block_analysis}` - Rule-specific block data
  - `{client_patterns}` - User-agent and IP patterns

- **Analysis Requirements** (5 areas):
  1. Identify false positive patterns
  2. Rule-specific false positive analysis
  3. Geographic false positives
  4. Rate-based rule threshold review
  5. Managed rule group issue identification

- **Output Structure**:
  - Executive summary with false positive rate
  - Detailed findings by rule
  - Whitelisting recommendations
  - Monitoring and validation steps
  - Risk assessment matrix

- **Priority Matrix**: Impact vs Risk vs Effort

##### Rule Optimization (`prompts/rule_optimization.md`)
- **Purpose**: Optimize WAF rules for performance and cost
- **Input Placeholders**:
  - `{current_rules}` - Current rule configuration
  - `{rule_performance}` - Performance metrics
  - `{traffic_distribution}` - Traffic patterns
  - `{cost_metrics}` - WCU usage and costs
  - `{attack_patterns}` - Attack type distribution

- **Analysis Requirements** (5 areas):
  1. Rule ordering optimization
  2. Rule consolidation opportunities
  3. Performance optimization
  4. Cost optimization
  5. Security effectiveness enhancement

- **Output Structure**:
  - Executive summary with optimization potential
  - Rule ordering recommendations
  - Consolidation plan
  - Performance optimizations
  - Cost reduction strategies
  - Implementation roadmap (4 phases)
  - Testing and validation plan

- **Phases**: Quick wins (1-2 weeks), Performance (3-4 weeks), Security (5-8 weeks), Cost (ongoing)

##### Compliance Gap Analysis (`prompts/compliance_gap_analysis.md`)
- **Purpose**: Evaluate compliance with security frameworks
- **Input Placeholders**:
  - `{waf_config}` - Complete WAF configuration
  - `{logging_config}` - Logging status
  - `{protected_resources}` - Resource inventory
  - `{rule_coverage}` - Rule coverage analysis
  - `{incident_history}` - Historical incidents (optional)

- **Compliance Frameworks** (5 frameworks):
  1. PCI-DSS Requirements (6.6, 10, 11)
  2. OWASP Top 10 (2021 edition)
  3. AWS Well-Architected Framework (Security Pillar)
  4. CIS AWS Foundations Benchmark
  5. NIST Cybersecurity Framework

- **Analysis Requirements** (5 areas):
  1. Rule coverage assessment
  2. Logging and monitoring compliance
  3. Resource protection coverage
  4. Configuration security review
  5. Incident response readiness

- **Output Structure**:
  - Executive summary with overall compliance score
  - OWASP Top 10 coverage analysis (all 10 categories)
  - PCI-DSS compliance assessment
  - AWS Well-Architected Framework assessment
  - Unprotected resources list
  - Logging and monitoring gaps
  - Configuration best practices review
  - Remediation roadmap (immediate, short, medium, long-term)
  - Compliance maintenance recommendations
  - Risk register
  - Audit evidence checklist

- **Compliance Score**: 0-100 based on coverage across all frameworks

### Features

#### WAF Schema
- **Comprehensive Coverage**: All official AWS WAF log fields
- **Field Classification**: Required vs optional fields
- **Type Definitions**: Clear data types for validation
- **Action Enumeration**: All valid WAF actions
- **Resource Types**: Common AWS resources
- **Version Tracking**: Based on latest AWS documentation

#### LLM Prompt Templates
- **Markdown Format**: Easy to read and edit
- **Structured Sections**: Consistent format across templates
- **Placeholder System**: Clear variable substitution
- **Priority Levels**: Standardized priority classification
- **Actionable Output**: Specific recommendations, not just analysis
- **Context Aware**: Production environment considerations
- **Framework Aligned**: Industry-standard compliance frameworks
- **Evidence Based**: Requires supporting data for findings

### Template Structure

Each prompt template follows this structure:
1. **Title and Purpose**: Clear objective statement
2. **Context**: Background and use case
3. **Data Provided**: Input placeholders with descriptions
4. **Analysis Requirements**: Specific areas to analyze (numbered list)
5. **Output Format**: Structured sections with clear headers
6. **Security/Risk Context**: Environmental considerations
7. **References** (compliance template): Links to frameworks

### Usage Workflow

1. **Generate Excel Report**: Run the analysis tool
2. **Extract Metrics**: Copy relevant data from Excel sheets
3. **Populate Template**: Replace `{placeholders}` with actual data
4. **Submit to LLM**: Use Claude, GPT-4, or other LLM
5. **Review Output**: Validate AI recommendations
6. **Update Excel**: Populate "LLM Recommendations" sheet
7. **Implement Actions**: Execute validated recommendations

### Placeholder Format

All placeholders use this format:
```markdown
{placeholder_name}
```

Examples:
- `{web_acl_config}` - JSON object
- `{rule_metrics}` - Table or JSON array
- `{geo_distribution}` - Table or JSON array

### Technical Details

#### WAF Schema
- Format: JSON
- Encoding: UTF-8
- Version: Based on WAFv2 (latest as of 2025)
- Size: ~1 KB
- Structure: Nested objects with arrays
- Validation: Used by log_parser.py

#### Prompt Templates
- Format: Markdown
- Encoding: UTF-8
- Total: 4 templates
- Size: 3-8 KB each
- Structure: Hierarchical with numbered sections
- Line length: Wrapped at ~80 characters

### Integration

#### Schema Integration
- Loaded by `processors.log_parser.WAFLogParser`
- Used for field validation
- Guides normalization process
- Ensures data quality

#### Template Integration
- Referenced in Excel "LLM Recommendations" sheet
- Instructions provided in README.md
- Standalone usage (copy to LLM interface)
- Can be automated with LLM APIs

### Maintenance

#### Schema Updates
- Monitor AWS WAF documentation for new fields
- Update when new actions are added (e.g., CHALLENGE)
- Add new resource types as AWS releases them
- Version control all changes

#### Template Updates
- Update frameworks as new versions release (e.g., OWASP Top 10 2025)
- Add new compliance frameworks as needed
- Incorporate user feedback and improvements
- Keep references current

### Known Limitations

#### WAF Schema
- Based on AWS documentation (may lag AWS releases)
- Doesn't include all possible fields (some are vendor-specific)
- No versioning within the file
- Assumes standard WAF log format (custom fields not supported)

#### Prompt Templates
- Placeholders must be manually replaced (no automation)
- Output format depends on LLM capability
- No validation of LLM responses
- Requires human review before implementation
- English only (no i18n)

### Future Enhancements

#### Schema
- [ ] Schema versioning
- [ ] Support for custom fields
- [ ] JSON Schema validation format
- [ ] Multiple schema versions (WAF Classic, WAFv2)
- [ ] Field deprecation tracking
- [ ] Automated schema updates from AWS docs

#### Templates
- [ ] Automated placeholder population
- [ ] Multi-language support (Spanish, French, etc.)
- [ ] Additional frameworks (SOC 2, HIPAA, etc.)
- [ ] Industry-specific templates (finance, healthcare, etc.)
- [ ] Integration with LLM APIs (automated processing)
- [ ] Template customization system
- [ ] Output validation schemas
- [ ] Example outputs for each template
- [ ] Video tutorials for usage

### Examples

#### Schema Usage
```python
import json

with open('config/waf_schema.json', 'r') as f:
    schema = json.load(f)

required_fields = schema['required_fields']
# ['timestamp', 'action', 'clientIp', ...]

valid_actions = schema['action_values']
# ['ALLOW', 'BLOCK', 'COUNT', 'CAPTCHA', 'CHALLENGE']
```

#### Template Usage
```markdown
# From security_effectiveness.md

## Data Provided

### Web ACL Configuration
```json
{web_acl_config}  # Replace with actual config
```

# Becomes:

## Data Provided

### Web ACL Configuration
```json
{
  "Name": "MyWebACL",
  "Id": "a1b2c3d4-...",
  "Rules": [...]
}
```
```

### Compatibility

#### Schema
- WAF Version: v2 (WAFv2)
- AWS Regions: All
- Log Sources: CloudWatch Logs, S3, Kinesis Firehose
- Log Format: JSON (newline-delimited)

#### Templates
- LLMs: Claude (all versions), GPT-4, GPT-3.5, other instruction-following models
- Format: Any markdown-compatible interface
- Integration: API-compatible (Claude API, OpenAI API)
- Output: Markdown or plain text

### References

#### WAF Schema
- [AWS WAF Logs Documentation](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html)
- [AWS WAF Log Fields Reference](https://docs.aws.amazon.com/waf/latest/developerguide/logging-fields.html)

#### Compliance Frameworks
- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [PCI DSS v4.0](https://www.pcisecuritystandards.org/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
