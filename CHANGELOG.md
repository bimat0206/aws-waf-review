# Changelog

All notable changes to the AWS WAF Security Analysis Tool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.0] - 2025-11-09

### Added

#### Sheet-Specific LLM-Generated Findings
- **NEW FEATURE**: Auto-populated LLM findings on all 5 analysis sheets
- **Comprehensive Analysis**: Each analysis sheet now receives AI-powered insights specific to its data type
- **Sheet Coverage**:
  - **Traffic Analysis**: Traffic patterns, geographic distribution, DDoS indicators
  - **Rule Effectiveness**: Unused rules, false positives, optimization opportunities
  - **Geographic Blocked Traffic**: High-risk countries, geo-blocking recommendations
  - **Rule Action Distribution**: ALLOW/BLOCK/COUNT balance, security posture evaluation
  - **Client Analysis**: Suspicious IP detection, bot traffic, rate limiting recommendations
- **LLM Integration Methods**:
  - `analyze_sheet_findings()` - Generates sheet-specific findings from metrics
  - `parse_sheet_findings()` - Extracts structured findings from LLM responses
  - 5 specialized prompt generators for each analysis type
- **Dual Display Modes**:
  - **Template Mode**: Shows instructions + empty rows (when LLM analysis not run)
  - **Populated Mode**: Displays actual AI-generated findings with color-coded severity
- **Severity Color Coding**:
  - 🔴 **HIGH** - Red background (#FFC7CE) for critical issues
  - 🟡 **MEDIUM** - Yellow background (#FFEB9C) for moderate concerns
  - 🟢 **LOW** - Green background (#C6EFCE) for minor improvements
- **User Experience**:
  - Progress indicators during analysis: "Analyzing traffic patterns..."
  - Graceful error handling: continues with empty findings if generation fails
  - Shorter prompts (max 2000 tokens) for faster analysis
- **Workflow Integration**:
  - Automatically runs after comprehensive WAF analysis (Option 6)
  - Generates findings for all 5 sheets sequentially
  - Passes findings to Excel generator for population

**Files Added**:
- No new files - enhanced existing architecture

**Files Updated**:
- [src/llm/analyzer.py](src/llm/analyzer.py:177-450) - Added `analyze_sheet_findings()` and 5 prompt generators
- [src/llm/response_parser.py](src/llm/response_parser.py:383-432) - Added `parse_sheet_findings()` method
- [src/reporters/sheets/base_sheet.py](src/reporters/sheets/base_sheet.py:186-279) - Enhanced `_add_llm_findings_section()` with dual modes
- [src/reporters/sheets/traffic_analysis.py](src/reporters/sheets/traffic_analysis.py:20-39,152) - Added `llm_findings` parameter
- [src/reporters/sheets/rule_effectiveness.py](src/reporters/sheets/rule_effectiveness.py:20-43,142) - Added `llm_findings` parameter
- [src/reporters/sheets/geographic_blocked.py](src/reporters/sheets/geographic_blocked.py:20-44,193) - Added `llm_findings` parameter
- [src/reporters/sheets/rule_action_distribution.py](src/reporters/sheets/rule_action_distribution.py:20-28,208) - Added `llm_findings` parameter
- [src/reporters/sheets/client_analysis.py](src/reporters/sheets/client_analysis.py:20-41,172) - Added `llm_findings` parameter
- [src/reporters/excel_generator.py](src/reporters/excel_generator.py:46-96) - Added `llm_sheet_findings` parameter
- [src/main.py](src/main.py:865-925,996) - Integrated sheet findings generation into LLM workflow

**Prompt Structure**:
Each sheet-specific prompt follows a focused format:
```
FINDING 1:
Finding: [Description of issue or insight]
Severity: [HIGH/MEDIUM/LOW]
Recommendation: [Specific action to take]

FINDING 2:
...
```

**Example Output**:
```
No | Finding                              | Severity | Recommendation
1  | High traffic from blocked countries  | HIGH     | Implement geo-blocking for CN, RU
2  | Unusual spike in evening hours       | MEDIUM   | Review rate limiting rules
3  | Low threat score overall             | LOW      | Maintain current configuration
```

### Fixed

#### Bug Fixes in Analysis Sheets
- **Rule Action Distribution**: Fixed undefined variable `rule_data` → changed to `rule_effectiveness`
- **Client Analysis**: Fixed undefined variable `top_clients` → changed to `top_ips`

### Technical Details

**New Methods in LLMAnalyzer** ([src/llm/analyzer.py](src/llm/analyzer.py)):
- `analyze_sheet_findings(sheet_type, metrics, sheet_data)` - Main coordination method
- `_create_traffic_prompt(metrics, data)` - Traffic analysis prompt generation
- `_create_rule_effectiveness_prompt(metrics, data)` - Rule effectiveness prompt
- `_create_geographic_prompt(metrics, data)` - Geographic threat prompt
- `_create_rule_action_prompt(metrics, data)` - Rule action analysis prompt
- `_create_client_prompt(metrics, data)` - Client behavior prompt
- `_format_geo_data(data)`, `_format_rule_data(data)`, `_format_ip_data(data)` - Data formatters

**Response Parser Enhancement** ([src/llm/response_parser.py](src/llm/response_parser.py)):
```python
def parse_sheet_findings(self, response: str) -> List[Dict[str, Any]]:
    """
    Parse sheet-specific findings from LLM response.
    Returns: List of dicts with keys: finding, severity, recommendation
    """
```

**Base Sheet Helper Enhancement** ([src/reporters/sheets/base_sheet.py](src/reporters/sheets/base_sheet.py)):
```python
def _add_llm_findings_section(self, ws, start_row, section_title,
                               merge_cols='A:E', findings=None):
    """
    Supports both template mode (findings=None) and populated mode (findings=List[Dict])
    """
```

**Performance Characteristics**:
- Each sheet analysis takes ~5-10 seconds with Claude Sonnet 4
- Total additional time: ~30-50 seconds for all 5 sheets
- Token usage: ~1,500-2,000 tokens per sheet (input + output)
- Cost impact: ~$0.02-0.05 additional cost per complete analysis

### Benefits

**For Users**:
- Actionable insights directly on each analysis sheet
- No need to cross-reference LLM Recommendations sheet
- Context-specific recommendations based on actual data patterns
- Visual severity indicators make priorities clear

**For Security Teams**:
- Faster identification of critical issues
- Sheet-specific remediation steps
- Better understanding of WAF effectiveness per analysis area
- Clear prioritization with HIGH/MEDIUM/LOW severity levels

**For Reporting**:
- More comprehensive Excel reports
- Professional appearance with color-coded findings
- Self-contained sheets with embedded AI insights
- Suitable for executive presentations and compliance audits

## [1.6.0] - 2025-11-08

### Added

#### Dynamic Regional Inference Profile Support with Configuration File
- **NEW CONFIG FILE**: [config/bedrock_inference_profiles.json](config/bedrock_inference_profiles.json) - Centralized configuration for regional inference profiles
- **Automatic Regional Prefix Selection**: Based on AWS region, automatically selects correct inference profile prefix
- **Regional Prefixes**:
  - **US Regions** (us-east-1, us-west-2): `us.anthropic.*`
  - **EU Regions** (eu-west-1, eu-central-1): `eu.anthropic.*`
  - **APAC Regions** (ap-southeast-1, ap-southeast-2, ap-northeast-1, ap-south-1): `apac.anthropic.*`
  - **Global** (fallback): `global.anthropic.*`
- **Smart Conversion**: Automatically converts direct model IDs (`anthropic.claude-*`) to region-specific inference profiles
- **Configuration-Driven**: All regional mappings and pricing loaded from JSON config file
- **Backward Compatible**: Existing inference profile IDs (with regional prefix) work as before

**Configuration Structure** ([config/bedrock_inference_profiles.json](config/bedrock_inference_profiles.json)):
```json
{
  "regional_prefix_mapping": {
    "us-east-1": "us",
    "ap-southeast-1": "apac",
    "eu-west-1": "eu"
  },
  "model_pricing": {
    "us": { "us.anthropic.claude-sonnet-4-5-20250929-v1:0": {...} },
    "apac": { "apac.anthropic.claude-sonnet-4-5-20250929-v1:0": {...} },
    "eu": { "eu.anthropic.claude-sonnet-4-5-20250929-v1:0": {...} }
  }
}
```

**New Methods**:
- `load_inference_profile_config()` - Loads configuration from JSON file with fallback defaults
- `_apply_regional_prefix()` - Applies correct regional prefix based on AWS region
- Updated `_to_global_profile()` - Now supports APAC prefix conversion

**Example Usage**:
```python
# Singapore region (ap-southeast-1) automatically uses apac prefix
analyzer = LLMAnalyzer(
    provider='bedrock',
    model='anthropic.claude-sonnet-4-5-20250929-v1:0',  # Base model ID
    region='ap-southeast-1'
)
# Automatically converted to: apac.anthropic.claude-sonnet-4-5-20250929-v1:0
```

**Supported APAC Regions**:
- **Asia Pacific (Singapore)**: ap-southeast-1 → apac.anthropic.*
- **Asia Pacific (Sydney)**: ap-southeast-2 → apac.anthropic.*
- **Asia Pacific (Tokyo)**: ap-northeast-1 → apac.anthropic.*
- **Asia Pacific (Mumbai)**: ap-south-1 → apac.anthropic.*

**Files Added**:
- [config/bedrock_inference_profiles.json](config/bedrock_inference_profiles.json) - Regional inference profile configuration

**Files Updated**:
- [src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py:20-62) - Added config loader and dynamic pricing
- [src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py:351-382) - Added `_apply_regional_prefix()` method
- [src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py:384-402) - Updated `_to_global_profile()` for APAC
- [src/llm/analyzer.py](src/llm/analyzer.py:63-67) - Updated default model to use base ID
- [src/main.py](src/main.py:700-711) - Updated model selection to use base IDs
- [src/main.py](src/main.py:805-811) - **FIXED**: Dynamic region detection from AWS session (no longer hardcoded)

### Fixed

#### Region Detection for Bedrock LLM Provider
- **Bug**: LLM analyzer was hardcoded to use `us-east-1` region, causing model identifier errors for users in other regions
- **Impact**: Users in APAC, EU regions received "The provided model identifier is invalid" error
- **Root Cause**: Line 809 in main.py hardcoded `region='us-east-1'` instead of using detected AWS region
- **Fix**: Now dynamically detects AWS region from session info and uses correct regional inference profile
- **Example**: Users in ap-southeast-1 (Singapore) now correctly use `apac.anthropic.*` instead of `us.anthropic.*`
- **File**: [src/main.py](src/main.py:805-811)

#### Incorrect Model IDs in Configuration
- **Bug 1**: Wrong model ID format: `claude-sonnet-4-0-*` (with hyphen) instead of `claude-sonnet-4-*` (without hyphen)
- **Bug 2**: Claude Sonnet 4.5 (`claude-sonnet-4-5-*`) doesn't exist in APAC region
- **Bug 3**: Model IDs were hardcoded in Python files instead of being configuration-driven
- **Impact**: All model invocations failed with "The provided model identifier is invalid"
- **Root Cause**: Configuration file had incorrect/non-existent model IDs and hardcoded values in codebase
- **Fix**:
  - ✅ Corrected model IDs to use proper format (removed extra hyphen)
  - ✅ Removed non-existent Claude Sonnet 4.5 from APAC region
  - ✅ Added Claude 3.7 Sonnet as available alternative
  - ✅ **Made model selection fully configuration-driven** (no hardcoded model IDs in code)
  - ✅ Dynamic menu generation based on region availability
  - ✅ Automatic filtering of models by region
- **Files Added**:
  - [src/utils/model_config.py](src/utils/model_config.py) - NEW utility for loading model configuration
- **Files Updated**:
  - [config/bedrock_inference_profiles.json](config/bedrock_inference_profiles.json:15-60) - Added `available_models` section with metadata
  - [src/main.py](src/main.py:679-731) - Dynamic model menu from config, region-aware filtering
  - [src/llm/analyzer.py](src/llm/analyzer.py:16,67) - Load default model from config

**Configuration-Driven Model Selection**:
```json
{
  "available_models": {
    "models": [
      {
        "id": "anthropic.claude-sonnet-4-20250514-v1:0",
        "name": "Claude Sonnet 4",
        "description": "Latest",
        "input_price": 3.00,
        "output_price": 15.00,
        "available_in": ["us", "eu", "apac", "global"]
      }
    ],
    "default_model": "anthropic.claude-sonnet-4-20250514-v1:0"
  }
}
```

**Available Models by Region**:
- **APAC**: ✅ Sonnet 4, ✅ 3.7 Sonnet, ✅ 3.5 Sonnet v2, ✅ Haiku (❌ Sonnet 4.5 not available)
- **US/EU**: ✅ All models including Sonnet 4.5

### Changed

#### LLM Recommendations Sheet - Major Format Redesign
- **BREAKING CHANGE**: Complete redesign of LLM Recommendations sheet format
- **New 3-Section Structure**:
  1. **Critical Findings** (Immediate Action Required) - Red background
  2. **Mid/Long-Term Recommendations** (Strategic Approach) - Orange background
  3. **Low Priority Suggestions** (Nice to Have) - Green background
- **New Table Format**: Changed from 4 columns to 5 columns
  - **Old**: Priority | Finding/Recommendation | Impact | Action Items
  - **New**: No | Finding | Expected Impact | Action Items (bullet list) | Rationale
- **Action Items Enhancement**: Now displayed as bullet list (3-5 items) with detailed, concise steps
- **Security Posture Assessment**: Changed from numeric (0-100) to categorical (High/Medium/Low)
  - Large, bold display with color coding
  - Auto-conversion of legacy numeric scores (≥80→High, ≥60→Medium, <60→Low)
- **Assessment Breakdown** (NEW SECTION): Added detailed breakdown with 5 key metrics:
  - **Rule Coverage**: High/Medium/Low with justification
  - **Threat Detection**: High/Medium/Low with justification
  - **Logging & Monitoring**: High/Medium/Low with justification
  - **Configuration Security**: High/Medium/Low with justification
  - **Response Readiness**: High/Medium/Low with justification
  - Each metric individually color-coded for quick visual assessment
  - Bullet-list format with indentation for visual hierarchy
- **Color Coding**:
  - High = Green (#008000)
  - Medium = Orange (#FF8C00)
  - Low = Red (#C00000)

**Files Updated**:
- [src/reporters/sheets/llm_recommendations.py](src/reporters/sheets/llm_recommendations.py:167-259) - Complete redesign of sheet generation
- [config/prompts/comprehensive_waf_analysis.md](config/prompts/comprehensive_waf_analysis.md:84-89) - Updated analysis requirements
- [config/prompts/comprehensive_waf_analysis.md](config/prompts/comprehensive_waf_analysis.md:141-176) - New table-based output format
- [config/prompts/comprehensive_waf_analysis.md](config/prompts/comprehensive_waf_analysis.md:462-486) - Added critical requirements section
- [src/llm/response_parser.py](src/llm/response_parser.py:66-138) - Updated executive summary parser
- [src/llm/response_parser.py](src/llm/response_parser.py:140-216) - New table-based findings parser

#### Prompt Template Updates
- **REMOVED**: All **Timeline:** information from prompt template
- **ADDED**: Specific requirement for 3-5 detailed, concise bullet points in Action Items
- **ADDED**: Clear definitions for High/Medium/Low security posture levels
- **UPDATED**: Output format to use markdown tables for findings
- **ENHANCED**: Action Items example with specific, implementable steps

#### Response Parser Enhancements
- **NEW**: `_parse_action_items()` method to extract bullet lists from table cells
- **UPDATED**: Executive summary parser to extract High/Medium/Low assessments
- **UPDATED**: Findings parser to extract data from table format (5 columns)
- **IMPROVED**: Support for both `<br>` and newline-separated action items
- **BACKWARD COMPATIBLE**: Maintains field aliases for existing code

## [1.5.3] - 2025-11-08

### Added

#### Claude Sonnet 4.0 Model Support
- **NEW MODEL**: Added Claude Sonnet 4.0 to available model options
- **Menu Position**: Option 2 in Claude model selection menu
- **Model ID**: `us.anthropic.claude-sonnet-4-0-20250514-v1:0` (region-specific)
- **Global Profile**: `global.anthropic.claude-sonnet-4-0-20250514-v1:0` (fallback for channel program accounts)
- **Pricing**: $3 per 1M input tokens, $15 per 1M output tokens
- **Use Case**: Stable, reliable option between 4.5 (latest) and 3.5 (previous gen)
- **Files Updated**:
  - [src/main.py](src/main.py:689-714) - Added option 2 for Sonnet 4.0
  - [src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py:27) - Added to pricing table
  - [src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py:33) - Added global profile

**Updated Menu**:
```
🤖 Select Claude Model:
1. Claude Sonnet 4.5 (Latest & Best - $3/$15 per 1M tokens)
2. Claude Sonnet 4.0 (Stable - $3/$15 per 1M tokens)         ← NEW
3. Claude 3.5 Sonnet v2 (Previous Gen - $3/$15 per 1M tokens)
4. Claude 3 Haiku (Fast & Cheap - $0.25/$1.25 per 1M tokens)
0. Cancel
```

## [1.5.2] - 2025-11-08

### Fixed

#### Automatic Global Inference Profile Fallback for Channel Program Accounts
- **CRITICAL FIX**: Added automatic fallback from region-specific to global inference profiles
- **Root Cause**: AWS channel program accounts (reseller/distributor) don't have access to region-specific inference profiles
- **Solution**: Automatically detects channel program restriction and retries with global inference profile
- **Fallback Logic**:
  1. Try region-specific profile first (e.g., `us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
  2. If ValidationException with "channel program" error, automatically switch to global profile
  3. Retry with global profile (e.g., `global.anthropic.claude-sonnet-4-5-20250929-v1:0`)
- **New Methods**:
  - `_try_global_fallback()` - Attempts request with global inference profile
  - `_to_global_profile()` - Converts region-specific profile ID to global profile ID
- **Files Updated**:
  - [src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py:173-176) - Added fallback detection
  - [src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py:214-335) - Added fallback methods

**Error Fixed**:
```
ValidationException: Access to this model is not available for channel program accounts.
Reach out to your AWS Solution Provider or AWS Distributor for more information.
```

**User Experience**:
- Seamless fallback - no user intervention required
- Automatic detection and retry with global profile
- Informative logging shows when fallback is triggered
- Success message confirms global profile usage

## [1.5.1] - 2025-11-08

### Fixed

#### All Claude Models Now Use Inference Profiles
- **CRITICAL FIX**: Updated all Claude model references to use AWS Bedrock inference profiles
- **Root Cause**: AWS Bedrock now requires inference profiles for all Claude models with on-demand throughput
- **Models Updated**:
  - Claude Sonnet 4.5: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
  - Claude 3.5 Sonnet v2: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
  - Claude 3 Haiku: `us.anthropic.claude-3-haiku-20240307-v1:0`
- **Removed**: Claude 3 Opus option (not available via inference profiles)
- **Default Model**: Changed from Claude 3.5 Sonnet v2 to Claude Sonnet 4.5
- **Files Updated**:
  - [src/main.py](src/main.py:689-707) - Updated model selection menu (removed Opus, updated to 0-3 choices)
  - [src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py:22-40) - Added inference profile IDs to pricing table
  - [src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py:44) - Updated default model to Sonnet 4.5

**Error Fixed**:
```
ValidationException: Invocation of model ID anthropic.claude-3-5-sonnet-20241022-v2:0
with on-demand throughput isn't supported. Retry your request with the ID or ARN of an
inference profile that contains this model.
```

**Inference Profile Format**:
- Region-specific: `us.anthropic.{model-id}` or `arn:aws:bedrock:{region}:{account}:inference-profile/us.anthropic.{model-id}`
- Global: `global.anthropic.{model-id}` or `arn:aws:bedrock:{region}:{account}:inference-profile/global.anthropic.{model-id}`

## [1.5.0] - 2025-11-08

### Added

#### Raw LLM Response Export System
- **New `RawLLMExporter` class** (`src/reporters/raw_llm_exporter.py`) for exporting raw LLM analysis responses
- **Automatic Export**: Raw LLM responses now automatically saved to `raw-llm-response/{alias}_{account_id}/` directory
- **File Format**: Markdown (.md) files with metadata headers
- **Export Methods**:
  - `export_raw_response()` - Export raw LLM response text to markdown file
  - `export_full_analysis()` - Export complete analysis with metadata and parsed results
- **Metadata Tracking**: Includes generation timestamp, account info, model details, token usage, and cost
- **Safe Filenames**: Automatic sanitization of special characters in filenames
- **Organized Storage**: Same directory structure as raw-logs (`{account_identifier}/`)
- **Integration**: Seamlessly integrated into `generate_llm_analysis()` workflow in main.py

### Changed

#### LLM Recommendations Sheet - Professional Format Redesign
- **BREAKING CHANGE**: Complete redesign of recommendations table structure in Excel
- **New Priority Organization** (3 sections instead of 4):
  1. **Critical Findings (Immediate Action Required)** - Red header, no subtitle
  2. **Mid/Long-Term Recommendations** - Orange header with strategic approach subtitle
  3. **Low Priority Suggestions (Nice to Have)** - Green header with improvement context
- **New Professional Table Format**:
  - **Column 1**: `No` (6 width) - Sequential numbering, center-aligned
  - **Column 2**: `Finding` (35 width) - Issue description with wrap text
  - **Column 3**: `Expected Impact` (25 width) - Impact assessment with wrap text
  - **Column 4**: `Action Items` (40 width) - Bullet list format with `•` prefix, wrap text
  - **Column 5**: `Rationale` (30 width) - Reasoning behind recommendation, wrap text
- **Removed Features**:
  - Raw response display section from Excel sheet (now in separate file)
  - Timeline column (merged into action items)
  - Priority column (now shown in section headers only)
- **Enhanced Features**:
  - Automatic bullet list formatting for action items (handles both list and string inputs)
  - Dynamic row height based on content length (40-120px range)
  - Professional subtitle text for Mid/Long-Term section about strategic approach
  - Improved data extraction with fallback field names
- **User Experience Improvements**:
  - Cleaner, more professional appearance
  - Easier to read with numbered findings
  - Action items clearly formatted as bullet lists
  - Raw response available in separate file for detailed review

#### Main Workflow Integration
- **Updated `generate_llm_analysis()`** in main.py:
  - Added raw LLM response export before Excel generation
  - Displays raw response file path after analysis completes
  - Creates `raw-llm-response/{account_identifier}/` directory automatically
  - Includes Web ACL name in filename for targeted analyses
- **Import Added**: `RawLLMExporter` imported in main.py

### Impact

**Before This Update**:
- Raw LLM response shown at bottom of Excel sheet (unprofessional, hard to navigate)
- 4 priority sections with generic column structure
- Fixed row heights causing text truncation
- No separate archive of raw responses

**After This Update**:
- Professional, organized table format with clear priorities
- Raw responses exported to dedicated directory for archiving and review
- Dynamic row heights prevent text truncation
- Bullet-formatted action items for clarity
- Cleaner Excel reports focused on actionable recommendations
- Raw data preserved separately for external analysis

### Files Modified
- `src/reporters/raw_llm_exporter.py` - NEW FILE
- `src/reporters/llm_recommendations.py` - MAJOR REDESIGN
- `src/reporters/CHANGELOG.md` - UPDATED
- `src/main.py` - UPDATED (import and integration)
- `CHANGELOG.md` - UPDATED

## [1.4.0] - 2025-11-08

### Added

#### Interactive LLM Analysis Menu Option
- **Option 7 in Main Menu**: "Generate LLM Security Analysis (Auto-populate Recommendations)"
- **Provider Selection**: Choose between AWS Bedrock Claude or OpenAI models
- **Model Selection**:
  - Claude Sonnet 4.5 (Latest & Best - default, uses inference profile)
  - Claude 3.5 Sonnet v2 (Stable)
  - Claude 3 Haiku (Fast & Cheap)
  - Claude 3 Opus (Maximum Accuracy)
  - OpenAI GPT-OSS 120B/20B via Bedrock
- **AWS Profile Selection**: Optional profile for Bedrock API calls
- **Web ACL Selection**: Analyze specific Web ACL or all Web ACLs
- **Connection Testing**: Verifies Bedrock access before analysis
- **Progress Indicators**: Real-time status updates during analysis
- **Cost Tracking**: Displays tokens used, cost estimate, and duration

### Added

#### LLM-Powered Security Analysis Integration
- **Comprehensive Prompt Template**: Created single master prompt template (`config/prompts/comprehensive_waf_analysis.md`) covering all security analysis areas:
  - Executive Summary with security posture scoring
  - Rule Effectiveness Analysis
  - False Positive Detection
  - Threat Intelligence Assessment
  - Geographic Risk Analysis
  - Compliance Review (OWASP Top 10, PCI-DSS)
  - Cost Optimization Recommendations
  - Implementation Roadmap with actionable timeline
  - Advanced Threat Detection
  - Long-term Strategic Recommendations
- **Modular LLM Architecture** (`src/llm/`):
  - `prompt_injector.py`: Handles loading templates and injecting WAF metrics data
  - `analyzer.py`: Main coordinator orchestrating prompt generation and LLM analysis
  - `response_parser.py`: Parses LLM markdown responses into structured data
  - `providers/base_provider.py`: Abstract base class for LLM providers
  - `providers/bedrock_provider.py`: AWS Bedrock implementation for Claude models
  - `providers/openai_provider.py`: AWS Bedrock implementation for OpenAI models
- **AWS Bedrock Provider Support**:
  - **Claude Models** (Recommended):
    - `anthropic.claude-3-5-sonnet-20241022-v2:0` - Production use ($3/$15 per 1M tokens)
    - `anthropic.claude-3-haiku-20240307-v1:0` - Fast/cheap ($0.25/$1.25 per 1M tokens)
    - `anthropic.claude-3-opus-20240229-v1:0` - Maximum accuracy ($15/$75 per 1M tokens)
  - **OpenAI Models** (via Bedrock):
    - `openai.gpt-oss-120b-1:0` - Production use (~$3/$9 per 1M tokens)
    - `openai.gpt-oss-20b-1:0` - Fast/cheap (~$0.50/$1.50 per 1M tokens)
- **Dual Implementation Modes**:
  - **Manual Mode**: Generates Excel report with prompt file for copy/paste to ChatGPT/Claude/Gemini
  - **Auto Mode**: Auto-sends to AWS Bedrock API, parses response, and populates Excel sheet with recommendations
- **Data Injection System**: Automatically injects comprehensive WAF metrics into prompt templates:
  - Summary metrics (total requests, block rate, security score)
  - Rule effectiveness data (top 50 rules)
  - Attack type distribution
  - Geographic threat analysis
  - Top blocked IPs, user agents, URIs
  - Bot traffic analysis
  - Hourly/daily traffic patterns
  - Web ACL configurations
  - Protected resources inventory
- **LLM Response Parser**: Extracts structured recommendations from LLM markdown output:
  - Executive summary with security score
  - Critical/High/Medium priority findings
  - Rule analysis tables
  - Threat intelligence insights
  - Compliance assessment
  - Cost optimization opportunities
  - Implementation roadmap
- **Auto-Populated LLM Recommendations Sheet**: Enhanced `llm_recommendations.py` to support:
  - Template mode (instructions for manual workflow)
  - Auto-populated mode (structured recommendations from LLM)
  - Analysis metadata display (provider, model, tokens, cost, duration)
  - Color-coded security score (green ≥80, orange ≥60, red <60)
  - Organized findings sections with priority levels
  - Full raw response for reference
- **Cost Tracking**: Built-in token usage and cost estimation for all LLM API calls
- **Error Handling**: Graceful fallback if LLM connection fails, with detailed error messages

### Changed

- **Prompt Template Strategy**: Replaced 4 separate specialized prompts with single comprehensive template:
  - Removed: `security_effectiveness.md`, `false_positive_analysis.md`, `rule_optimization.md`, `compliance_gap_analysis.md`
  - Added: `comprehensive_waf_analysis.md` - Master prompt covering all analysis areas
  - Rationale: More cost-effective, provides holistic analysis, reduces API calls
- **LLM Recommendations Sheet**: Updated to support both manual template and auto-populated modes based on whether LLM analysis is provided
- **System Architecture**: Added LLM module to architecture diagram showing integration with main workflow
- **External Dependencies**: Added AWS Bedrock API to dependency list

### Technical Details

#### New Module Structure
```
src/llm/
├── __init__.py              # Module exports
├── prompt_injector.py       # Template loading and data injection
├── analyzer.py              # Main LLM coordinator
├── response_parser.py       # Response parsing to structured data
└── providers/
    ├── __init__.py
    ├── base_provider.py     # Abstract base class
    ├── bedrock_provider.py  # AWS Bedrock Claude implementation
    └── openai_provider.py   # AWS Bedrock OpenAI implementation
```

#### Key Features
- Template-based prompt injection with JSON data serialization
- Abstract provider pattern for easy addition of new LLM providers
- Comprehensive error handling and logging
- Token estimation and cost calculation
- Connection testing for all providers
- Support for custom temperature, max_tokens, and other LLM parameters
- Automatic saving of generated prompts for manual use
- Parsing of complex markdown responses with regex-based extraction

### Documentation

- Updated README.md with LLM integration section
- Added LLM module to directory structure
- Updated system architecture diagram
- Documented supported models and pricing
- Added usage examples for both manual and auto modes

### Fixed

- **MetricsCalculator Integration**: Fixed `TypeError` in LLM analysis workflow where `web_acl_ids` was incorrectly passed to `calculate_all_metrics()` method instead of the constructor
- **Claude Sonnet 4.5 Support**: Fixed `ValidationException` by using AWS Bedrock inference profile ID (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`) instead of direct model ID. Sonnet 4.5 requires inference profiles for on-demand throughput.
- **OpenAI Provider Selection**: Fixed `ValidationException` where OpenAI models were incorrectly routed to BedrockProvider (Claude API format) instead of OpenAIProvider. Changed provider type from 'bedrock' to 'openai' when selecting OpenAI models.

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
