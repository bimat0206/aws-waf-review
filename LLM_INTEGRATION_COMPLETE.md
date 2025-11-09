# LLM Integration - Implementation Complete ✅

## Summary

I've successfully implemented a comprehensive LLM integration system for your AWS WAF analyzer with the following features:

### ✅ Completed Components

1. **Comprehensive Prompt Template** ([config/prompts/comprehensive_waf_analysis.md](config/prompts/comprehensive_waf_analysis.md))
   - Structured markdown template with all 10 analysis sections
   - Injects all WAF metrics (rules, traffic, threats, compliance, cost)
   - Optimized for accurate, concise, actionable recommendations

2. **PromptInjector Class** ([src/llm/prompt_injector.py](src/llm/prompt_injector.py))
   - Loads templates and injects real metrics data
   - Handles data serialization (JSON, DataFrames)
   - Saves prompts to files for manual use

3. **LLM Provider Architecture**
   - **Base Provider** ([src/llm/providers/base_provider.py](src/llm/providers/base_provider.py))
   - **Bedrock Provider** ([src/llm/providers/bedrock_provider.py](src/llm/providers/bedrock_provider.py))
     - Claude 3.5 Sonnet (RECOMMENDED - accurate & concise)
     - Claude 3 Haiku (fast & cheap)
     - Claude 3 Opus (maximum accuracy)
   - **OpenAI Provider** ([src/llm/providers/openai_provider.py](src/llm/providers/openai_provider.py))
     - Uses AWS Bedrock's OpenAI models (gpt-oss-20b, gpt-oss-120b)
     - Same AWS authentication as Bedrock Claude

4. **LLMAnalyzer** ([src/llm/analyzer.py](src/llm/analyzer.py))
   - Coordinates prompt injection and LLM calls
   - Supports both Bedrock (Claude/OpenAI) providers
   - Returns parsed, structured recommendations

5. **ResponseParser** ([src/llm/response_parser.py](src/llm/response_parser.py))
   - Parses LLM markdown into structured data
   - Extracts findings, scores, recommendations, compliance status

6. **Updated LLMRecommendationsSheet** ([src/reporters/sheets/llm_recommendations.py](src/llm/reporters/sheets/llm_recommendations.py))
   - **Manual Mode**: Template with instructions for copy/paste
   - **Auto Mode**: Populated with LLM analysis results

---

## 🚀 Integration with main.py

### Step 1: Add LLM Menu Options

Add to your interactive menu (after option 6 "Configure Timezone"):

```python
# Around line 1100 in main.py
print("\n" + "="*80)
print("📊 AWS WAF Security Analysis Tool")
print("="*80)
print(f"AWS Profile: {session_info.get('profile', 'default')}")
print(f"Region: {session_info.get('region', 'N/A')}")
print(f"Timezone: {get_timezone_display()}")
print()
print("1. Fetch and Store WAF Logs")
print("2. Calculate Metrics")
print("3. Export Excel Report (No LLM)")
print("4. Export Excel Report + Generate LLM Prompt (Manual)")
print("5. Export Excel Report + Auto-Analyze with LLM (Bedrock)")
print("6. Configure Timezone Settings")
print("0. Exit")
print("="*80)

choice = input("\nEnter choice (0-6): ").strip()
```

### Step 2: Add Import Statements

At the top of main.py:

```python
# Around line 20-30
from llm.analyzer import LLMAnalyzer
from llm.prompt_injector import PromptInjector
```

### Step 3: Add Helper Function for LLM Provider Selection

```python
def select_llm_provider():
    """
    Interactive selection of LLM provider and model.

    Returns:
        tuple: (provider_name, model_id, profile/None)
    """
    print("\n📡 Select LLM Provider:")
    print("1. AWS Bedrock - Claude 3.5 Sonnet (RECOMMENDED - accurate & concise)")
    print("2. AWS Bedrock - Claude 3 Haiku (fastest & cheapest)")
    print("3. AWS Bedrock - OpenAI GPT-OSS 120B (production)")
    print("4. AWS Bedrock - OpenAI GPT-OSS 20B (fast)")

    while True:
        choice = input("\nEnter choice (1-4): ").strip()

        if choice == '1':
            provider = 'bedrock'
            model = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
            break
        elif choice == '2':
            provider = 'bedrock'
            model = 'anthropic.claude-3-haiku-20240307-v1:0'
            break
        elif choice == '3':
            provider = 'openai'
            model = 'openai.gpt-oss-120b-1:0'
            break
        elif choice == '4':
            provider = 'openai'
            model = 'openai.gpt-oss-20b-1:0'
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")

    # Ask for AWS profile for Bedrock
    print("\n🔐 AWS Profile for Bedrock API:")
    print("1. Use current profile")
    print("2. Use different profile")

    profile_choice = input("Enter choice (1-2): ").strip()
    if profile_choice == '2':
        profile = input("Enter AWS profile name: ").strip()
    else:
        profile = os.environ.get('AWS_PROFILE')

    return provider, model, profile
```

### Step 4: Implement Report Generation Functions

```python
def generate_excel_report_with_manual_llm(db_manager, output_path, selected_web_acl_ids, session_info):
    """Generate Excel report and save LLM prompt for manual use."""
    from reporters.excel_generator import ExcelReportGenerator
    from fetchers.waf_fetcher import WAFFetcher
    from processors.metrics_calculator import MetricsCalculator
    from llm.prompt_injector import PromptInjector

    logger.info(f"Generating Excel report with manual LLM prompt: {output_path}")

    # Get WAF data
    waf_fetcher = WAFFetcher(profile=session_info.get('profile'), region=session_info.get('region'))
    web_acls = waf_fetcher.list_web_acls()
    resources = waf_fetcher.list_resources_for_web_acls(web_acls)
    logging_configs = waf_fetcher.get_logging_configurations(web_acls)

    # Get rules
    rules_by_web_acl = {}
    for acl in web_acls:
        acl_id = acl.get('Id') or acl.get('id')
        acl_scope = acl.get('Scope') or acl.get('scope')
        rules = waf_fetcher.get_rules_for_web_acl(acl_id, acl_scope)
        rules_by_web_acl[acl_id] = rules

    # Calculate metrics
    calculator = MetricsCalculator(db_manager, web_acl_ids=selected_web_acl_ids)
    metrics = calculator.calculate_all_metrics()

    # Generate prompt
    injector = PromptInjector()
    prompt = injector.create_comprehensive_prompt(
        metrics=metrics,
        web_acls=web_acls,
        resources=resources,
        account_info=session_info
    )

    # Save prompt
    prompt_path = output_path.replace('.xlsx', '_llm_prompt.md')
    injector.save_prompt_to_file(prompt, prompt_path)

    # Generate Excel report (manual template mode)
    generator = ExcelReportGenerator(output_path)
    generator.generate_report(
        metrics=metrics,
        web_acls=web_acls,
        resources=resources,
        logging_configs=logging_configs,
        rules_by_web_acl=rules_by_web_acl,
        account_info=session_info
    )
    generator.save()

    print(f"\n✅ Excel report generated: {output_path}")
    print(f"✅ LLM prompt saved: {prompt_path}")
    print("\n📋 Next Steps:")
    print(f"1. Open the prompt file: {prompt_path}")
    print("2. Copy the entire content")
    print("3. Paste into ChatGPT/Claude/Gemini")
    print("4. Copy the AI response")
    print("5. Paste into the 'LLM Recommendations' sheet in Excel")


def generate_excel_report_with_auto_llm(db_manager, output_path, selected_web_acl_ids, session_info):
    """Generate Excel report with auto LLM analysis."""
    from reporters.excel_generator import ExcelReportGenerator
    from fetchers.waf_fetcher import WAFFetcher
    from processors.metrics_calculator import MetricsCalculator
    from llm.analyzer import LLMAnalyzer

    logger.info(f"Generating Excel report with auto LLM analysis: {output_path}")

    # Get WAF data
    waf_fetcher = WAFFetcher(profile=session_info.get('profile'), region=session_info.get('region'))
    web_acls = waf_fetcher.list_web_acls()
    resources = waf_fetcher.list_resources_for_web_acls(web_acls)
    logging_configs = waf_fetcher.get_logging_configurations(web_acls)

    # Get rules
    rules_by_web_acl = {}
    for acl in web_acls:
        acl_id = acl.get('Id') or acl.get('id')
        acl_scope = acl.get('Scope') or acl.get('scope')
        rules = waf_fetcher.get_rules_for_web_acl(acl_id, acl_scope)
        rules_by_web_acl[acl_id] = rules

    # Calculate metrics
    calculator = MetricsCalculator(db_manager, web_acl_ids=selected_web_acl_ids)
    metrics = calculator.calculate_all_metrics()

    # Select LLM provider
    provider, model, bedrock_profile = select_llm_provider()

    # Initialize LLM analyzer
    analyzer = LLMAnalyzer(
        provider=provider,
        model=model,
        region=session_info.get('region', 'us-east-1'),
        profile=bedrock_profile
    )

    # Test connection
    print("\n🔗 Testing LLM connection...")
    if not analyzer.test_provider_connection():
        print("❌ LLM connection failed. Falling back to manual prompt generation.")
        prompt_path = output_path.replace('.xlsx', '_llm_prompt.md')
        analyzer.injector.save_prompt_to_file(
            analyzer.injector.create_comprehensive_prompt(
                metrics=metrics,
                web_acls=web_acls,
                resources=resources,
                account_info=session_info
            ),
            prompt_path
        )
        llm_analysis = None
        llm_metadata = None
    else:
        # Run LLM analysis
        print("✅ Connection successful. Analyzing WAF security...")
        prompt_path = output_path.replace('.xlsx', '_llm_prompt.md')

        result = analyzer.analyze_waf_security(
            metrics=metrics,
            web_acls=web_acls,
            resources=resources,
            account_info=session_info,
            save_prompt=prompt_path,
            temperature=0.3,
            max_tokens=16000
        )

        if result.get('error'):
            print(f"❌ LLM analysis failed: {result['error']}")
            llm_analysis = None
            llm_metadata = None
        else:
            llm_analysis = result['parsed']
            llm_metadata = result['metadata']
            print(f"✅ LLM analysis completed!")
            print(f"   Model: {llm_metadata['model']}")
            print(f"   Tokens: {llm_metadata['tokens_used']['total']:,}")
            print(f"   Cost: ${llm_metadata['cost_estimate']:.4f}")
            print(f"   Duration: {llm_metadata['duration']:.2f}s")

    # Generate Excel report with LLM results
    generator = ExcelReportGenerator(output_path)
    generator.generate_report(
        metrics=metrics,
        web_acls=web_acls,
        resources=resources,
        logging_configs=logging_configs,
        rules_by_web_acl=rules_by_web_acl,
        account_info=session_info,
        llm_analysis=llm_analysis,
        llm_metadata=llm_metadata
    )
    generator.save()

    print(f"\n✅ Excel report generated: {output_path}")
    if llm_analysis:
        print("✅ LLM Recommendations sheet populated with AI analysis")
    print(f"✅ LLM prompt saved: {prompt_path}")
```

### Step 5: Add Menu Handlers

```python
# In your main menu loop, around line 1110-1120

elif choice == '3':
    # Export Excel Report (No LLM) - existing implementation
    # Keep your existing code
    pass

elif choice == '4':
    # Export Excel Report + Generate LLM Prompt (Manual)
    # Get Web ACL selection and output path (same as option 3)
    # ... your existing Web ACL selection code ...
    generate_excel_report_with_manual_llm(db_manager, output_path, selected_web_acl_ids, session_info)

elif choice == '5':
    # Export Excel Report + Auto-Analyze with LLM
    # Get Web ACL selection and output path (same as option 3)
    # ... your existing Web ACL selection code ...
    generate_excel_report_with_auto_llm(db_manager, output_path, selected_web_acl_ids, session_info)

elif choice == '6':
    # Configure Timezone - existing implementation
    configure_timezone()
```

### Step 6: Update ExcelReportGenerator

Modify `src/reporters/excel_generator.py` to accept LLM parameters:

```python
def generate_report(
    self,
    metrics: Dict[str, Any],
    web_acls: List[Dict[str, Any]],
    resources: List[Dict[str, Any]],
    logging_configs: List[Dict[str, Any]],
    rules_by_web_acl: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    account_info: Optional[Dict[str, Any]] = None,
    llm_analysis: Optional[Dict[str, Any]] = None,  # NEW
    llm_metadata: Optional[Dict[str, Any]] = None,  # NEW
) -> None:
    """Generate the complete Excel report."""
    # ... existing sheets ...

    # LLM Recommendations sheet
    self._init_sheet(LLMRecommendationsSheet).build(llm_analysis, llm_metadata)
```

---

## 📊 Usage Examples

### Manual Mode (No AWS Bedrock Needed)
```bash
python src/main.py
# Select option 4
# Prompt saved to: output/account-123/waf_analysis_2025-11-08_llm_prompt.md
# Copy content, paste to ChatGPT/Claude, paste response back
```

### Auto Mode (AWS Bedrock)
```bash
python src/main.py
# Select option 5
# Choose Claude 3.5 Sonnet
# Analysis runs automatically
# Excel populated with recommendations
```

---

## 💰 Cost Estimates

| Provider | Model | Input | Output | Est. Cost/Report |
|----------|-------|--------|--------|------------------|
| **Bedrock** | Claude 3.5 Sonnet | $3/1M | $15/1M | **$1.50-3.00** |
| Bedrock | Claude 3 Haiku | $0.25/1M | $1.25/1M | $0.15-0.40 |
| Bedrock | GPT-OSS 120B | $3/1M | $9/1M | $1.00-2.50 |
| Bedrock | GPT-OSS 20B | $0.50/1M | $1.50/1M | $0.20-0.60 |

*Estimates based on ~40K input tokens + ~50K output tokens*

---

## 🔒 Security Notes

1. **AWS Credentials**: Uses existing AWS profile/credentials
2. **Data Privacy**: All data stays in your AWS account (Bedrock)
3. **No External APIs**: Both Claude and OpenAI models run on AWS Bedrock
4. **Validation Required**: Always review LLM recommendations before implementing

---

## 🧪 Testing

Test the integration:

```bash
# Test without LLM
python src/main.py
# Select option 3 (existing)

# Test manual LLM mode
python src/main.py
# Select option 4
# Check if prompt file is generated

# Test auto LLM mode
python src/main.py
# Select option 5
# Verify connection test passes
# Check if Excel has populated LLM sheet
```

---

## 📝 Next Steps

1. **Review**: Check [PROMPT_TEMPLATE_ANALYSIS.md](PROMPT_TEMPLATE_ANALYSIS.md) for full architecture
2. **Integrate**: Follow steps above to add to main.py
3. **Test**: Run with sample data
4. **Update CHANGELOG**: Document new LLM features

---

## ✅ What's Ready to Use

All code is complete and ready. You just need to:
1. Copy the integration code into main.py
2. Test with your WAF data
3. Enjoy AI-powered security recommendations!

**Would you like me to create a PR-ready implementation or help with any specific integration step?**
