# Changelog - LLM Module

All notable changes to the LLM analysis module will be documented in this file.

## [1.1.0] - 2025-11-08

### Changed

#### Response Parser - Major Format Update
- **BREAKING CHANGE**: Complete redesign of response parsing to support new table-based format
- **Executive Summary Parser** ([response_parser.py:66-138](../response_parser.py#L66-L138)):
  - Changed from numeric score (0-100) to categorical assessment (High/Medium/Low)
  - Added parsing for assessment breakdown (5 metrics: Rule Coverage, Threat Detection, Logging & Monitoring, Configuration Security, Response Readiness)
  - Updated field names: `security_score` → `security_posture`, added `assessment_breakdown`
  - Updated counts: `critical_count`, `mid_long_term_count`, `low_priority_count`
- **Findings Parser** ([response_parser.py:140-216](../response_parser.py#L140-L216)):
  - Changed from list-based format to table-based format (5 columns)
  - New columns: No | Finding | Expected Impact | Action Items | Rationale
  - Updated priority mappings: "High Priority" → "Mid/Long-Term Recommendations", "Medium" → merged into Mid/Long-Term
  - Added `_parse_action_items()` method to extract bullet lists from table cells
  - Support for both `<br>` and newline-separated action items
  - Field aliases for backward compatibility (title/finding, impact/expected_impact, action/actions, rationale/reason)
- **Parse Response Method** ([response_parser.py:45-58](../response_parser.py#L45-L58)):
  - Added `low_priority` field to parsed output
  - Set `medium_priority` to empty list (now merged into `high_priority`)
  - Updated comments to reflect new mapping

#### Prompt Template - Security Assessment Update
- **Analysis Requirements** ([comprehensive_waf_analysis.md:84-90](../../config/prompts/comprehensive_waf_analysis.md#L84-L90)):
  - Changed from "Calculate overall security posture score (0-100)" to "Assess overall security posture (High/Medium/Low)"
  - Added requirement for assessment breakdown with 5 key areas
  - Updated to align with new categorical assessment approach
- **Output Format** ([comprehensive_waf_analysis.md:141-176](../../config/prompts/comprehensive_waf_analysis.md#L141-L176)):
  - Changed from numeric scoring to categorical assessment (High/Medium/Low)
  - Added assessment breakdown section with justifications for each area
  - Changed from list-based findings to table-based format
  - Updated table columns: No | Finding | Expected Impact | Action Items | Rationale
  - Removed all Timeline references
- **Critical Requirements** ([comprehensive_waf_analysis.md:462-486](../../config/prompts/comprehensive_waf_analysis.md#L462-L486)):
  - Added specific requirement for 3-5 detailed, concise bullet points in Action Items
  - Added clear definitions for High/Medium/Low security posture levels
  - Added example Action Items format with specific implementation details
  - Prohibited Timeline information and generic recommendations

### Added

#### New Helper Method
- **`_parse_action_items()`** ([response_parser.py:195-216](../response_parser.py#L195-L216)):
  - Extracts bullet lists from table cells
  - Handles both `<br>` and newline-separated items
  - Removes bullet point characters (•, -, *)
  - Returns list of cleaned action items
  - Fallback to original text if parsing fails

### Backward Compatibility

- Maintained field aliases in findings parser for existing code:
  - `title` / `finding`
  - `impact` / `expected_impact`
  - `action` (raw text) / `actions` (parsed list)
  - `rationale` / `reason`
- Excel sheet generator can handle both old numeric scores and new categorical assessments
- Graceful handling of missing fields with default values

## [1.0.0] - 2025-11-08

### Added

#### LLM-Powered Security Analysis Module
- **Comprehensive Prompt Template**: Created single master prompt template covering all security analysis areas
- **Modular Architecture**:
  - `prompt_injector.py`: Handles loading templates and injecting WAF metrics data
  - `analyzer.py`: Main coordinator orchestrating prompt generation and LLM analysis
  - `response_parser.py`: Parses LLM markdown responses into structured data
  - `providers/base_provider.py`: Abstract base class for LLM providers
  - `providers/bedrock_provider.py`: AWS Bedrock implementation for Claude models
  - `providers/openai_provider.py`: AWS Bedrock implementation for OpenAI models

#### AWS Bedrock Provider Support
- **Claude Models** (Recommended):
  - `anthropic.claude-3-5-sonnet-20241022-v2:0` - Production use ($3/$15 per 1M tokens)
  - `anthropic.claude-3-haiku-20240307-v1:0` - Fast/cheap ($0.25/$1.25 per 1M tokens)
  - `anthropic.claude-3-opus-20240229-v1:0` - Maximum accuracy ($15/$75 per 1M tokens)
- **OpenAI Models** (via Bedrock):
  - `openai.gpt-oss-120b-1:0` - Production use (~$3/$9 per 1M tokens)
  - `openai.gpt-oss-20b-1:0` - Fast/cheap (~$0.50/$1.50 per 1M tokens)

#### Data Injection System
- Automatically injects comprehensive WAF metrics into prompt templates
- Supports JSON serialization of complex data structures
- Handles DataFrames, lists, and nested dictionaries
- Limits large datasets for token efficiency

#### LLM Response Parser
- Extracts structured recommendations from LLM markdown output
- Parses executive summary with security score
- Extracts Critical/High/Medium priority findings
- Parses markdown tables for rule analysis
- Extracts threat intelligence insights
- Parses compliance assessment data
- Extracts cost optimization opportunities
- Parses implementation roadmap

#### Integration Features
- Interactive menu option in main.py for LLM analysis
- Provider and model selection workflow
- AWS profile selection for Bedrock API calls
- Web ACL selection for targeted analysis
- Connection testing before analysis
- Cost tracking with token usage and estimates
- Error handling with graceful fallback
- Auto-generation of Excel report with populated recommendations

### Technical Details

#### Module Structure
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

### Dependencies
- boto3: AWS SDK for Bedrock API calls
- All existing WAF analyzer dependencies

### Known Limitations
- Only supports AWS Bedrock (no direct OpenAI API)
- Requires Bedrock model access in AWS account
- Token limits may affect very large WAF configurations
- Response parsing based on expected markdown format
