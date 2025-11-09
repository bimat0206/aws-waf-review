"""
LLM Analyzer

Main analyzer class that coordinates prompt injection and LLM provider calls.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .prompt_injector import PromptInjector
from .providers.base_provider import BaseLLMProvider
from .providers.bedrock_provider import BedrockProvider
from .providers.openai_provider import OpenAIProvider
from .response_parser import ResponseParser
from utils.model_config import get_default_model

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """Main LLM analyzer coordinating prompt generation and analysis."""

    def __init__(
        self,
        provider: str = 'bedrock',
        model: Optional[str] = None,
        template_dir: str = 'config/prompts',
        **provider_kwargs
    ):
        """
        Initialize LLM analyzer.

        Args:
            provider: Provider name ('bedrock' or 'openai')
            model: Model identifier (provider-specific, uses default if None)
            template_dir: Directory containing prompt templates
            **provider_kwargs: Provider-specific parameters (region, profile, api_key, etc.)
        """
        self.provider_name = provider.lower()
        self.injector = PromptInjector(template_dir=template_dir)
        self.parser = ResponseParser()

        # Initialize provider
        self.provider = self._initialize_provider(model, **provider_kwargs)

        logger.info(f"LLMAnalyzer initialized with {self.provider_name} provider")

    def _initialize_provider(
        self,
        model: Optional[str],
        **kwargs
    ) -> BaseLLMProvider:
        """
        Initialize the appropriate LLM provider.

        Args:
            model: Model identifier
            **kwargs: Provider-specific parameters

        Returns:
            BaseLLMProvider: Initialized provider instance
        """
        if self.provider_name == 'bedrock':
            # Load default model from config if not specified
            # Regional prefix will be applied automatically based on the region parameter
            model = model or get_default_model()
            return BedrockProvider(model=model, **kwargs)

        elif self.provider_name == 'openai':
            # Default to GPT-4 Turbo if no model specified
            model = model or 'gpt-4-turbo'
            return OpenAIProvider(model=model, **kwargs)

        else:
            raise ValueError(
                f"Unsupported provider: {self.provider_name}. "
                f"Supported providers: 'bedrock', 'openai'"
            )

    def analyze_waf_security(
        self,
        metrics: Dict[str, Any],
        web_acls: List[Dict[str, Any]],
        resources: List[Dict[str, Any]],
        account_info: Dict[str, Any],
        save_prompt: Optional[str] = None,
        **llm_params
    ) -> Dict[str, Any]:
        """
        Perform comprehensive WAF security analysis using LLM.

        Args:
            metrics: Calculated metrics from MetricsCalculator
            web_acls: List of Web ACL configurations
            resources: List of protected resources
            account_info: AWS account information
            save_prompt: Optional path to save the generated prompt
            **llm_params: LLM-specific parameters (temperature, max_tokens, etc.)

        Returns:
            Dict containing:
                - 'prompt': Generated prompt
                - 'response': LLM response (raw markdown)
                - 'parsed': Parsed structured recommendations
                - 'metadata': Analysis metadata (model, tokens, cost, duration)
                - 'error': Error message if analysis failed
        """
        logger.info("Starting WAF security analysis...")

        try:
            # Generate prompt with data injection
            prompt = self.injector.create_comprehensive_prompt(
                metrics=metrics,
                web_acls=web_acls,
                resources=resources,
                account_info=account_info
            )

            # Save prompt if requested
            if save_prompt:
                self.injector.save_prompt_to_file(prompt, save_prompt)

            # Send to LLM
            logger.info(f"Sending prompt to {self.provider_name}...")
            result = self.provider.analyze(prompt, **llm_params)

            if result.get('error'):
                logger.error(f"LLM analysis failed: {result['error']}")
                return {
                    'prompt': prompt,
                    'response': None,
                    'parsed': None,
                    'metadata': result,
                    'error': result['error']
                }

            # Parse response
            logger.info("Parsing LLM response...")
            parsed_recommendations = self.parser.parse_response(result['response'])

            logger.info("Analysis completed successfully")
            return {
                'prompt': prompt,
                'response': result['response'],
                'parsed': parsed_recommendations,
                'metadata': {
                    'provider': self.provider_name,
                    'model': result['model'],
                    'tokens_used': result['tokens_used'],
                    'cost_estimate': result['cost_estimate'],
                    'duration': result['duration']
                },
                'error': None
            }

        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            return {
                'prompt': None,
                'response': None,
                'parsed': None,
                'metadata': {},
                'error': str(e)
            }

    def test_provider_connection(self) -> bool:
        """
        Test connection to LLM provider.

        Returns:
            bool: True if connection successful
        """
        logger.info(f"Testing connection to {self.provider_name}...")
        return self.provider.test_connection()

    def analyze_sheet_findings(
        self,
        sheet_type: str,
        metrics: Dict[str, Any],
        sheet_data: Dict[str, Any],
        **llm_params
    ) -> List[Dict[str, Any]]:
        """
        Generate sheet-specific findings using LLM.

        Args:
            sheet_type: Type of sheet ('traffic', 'rule_effectiveness', 'geographic', 'rule_action', 'client')
            metrics: Relevant metrics for this sheet
            sheet_data: Sheet-specific data
            **llm_params: LLM-specific parameters

        Returns:
            List of findings with structure:
                - finding: Description of the finding
                - severity: HIGH/MEDIUM/LOW
                - recommendation: What to do about it
        """
        logger.info(f"Generating {sheet_type} analysis findings...")

        try:
            # Create sheet-specific prompt
            prompt = self._create_sheet_prompt(sheet_type, metrics, sheet_data)

            # Send to LLM with shorter response parameters
            result = self.provider.analyze(
                prompt,
                max_tokens=llm_params.get('max_tokens', 2000),
                temperature=llm_params.get('temperature', 0.7)
            )

            if result.get('error'):
                logger.error(f"Sheet findings analysis failed: {result['error']}")
                return []

            # Parse findings from response
            findings = self.parser.parse_sheet_findings(result['response'])
            logger.info(f"Generated {len(findings)} findings for {sheet_type}")
            return findings

        except Exception as e:
            logger.error(f"Error generating sheet findings: {e}")
            return []

    def _create_sheet_prompt(
        self,
        sheet_type: str,
        metrics: Dict[str, Any],
        sheet_data: Dict[str, Any]
    ) -> str:
        """
        Create a focused prompt for sheet-specific analysis.

        Args:
            sheet_type: Type of analysis
            metrics: Metrics data
            sheet_data: Sheet-specific data

        Returns:
            str: Formatted prompt
        """
        prompts = {
            'traffic': self._create_traffic_prompt,
            'rule_effectiveness': self._create_rule_effectiveness_prompt,
            'geographic': self._create_geographic_prompt,
            'rule_action': self._create_rule_action_prompt,
            'client': self._create_client_prompt
        }

        creator = prompts.get(sheet_type)
        if not creator:
            raise ValueError(f"Unknown sheet type: {sheet_type}")

        return creator(metrics, sheet_data)

    def _create_traffic_prompt(self, metrics: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Create prompt for traffic analysis findings."""
        daily_trends = metrics.get('daily_trends')
        geo_data = metrics.get('geographic_distribution', [])[:10]

        return f"""Analyze the following WAF traffic patterns and provide 3-5 key findings.

## Traffic Data:
- Total Requests: {metrics.get('total_requests', 0):,}
- Blocked Requests: {metrics.get('blocked_requests', 0):,}
- Block Rate: {metrics.get('block_rate', 0):.1f}%

## Geographic Distribution (Top 10):
{self._format_geo_data(geo_data)}

## Instructions:
Provide 3-5 concise findings in this EXACT format:

FINDING 1:
Finding: [Brief description of traffic pattern or anomaly]
Severity: [HIGH/MEDIUM/LOW]
Rationale: [Evidence from data and reasoning for the finding]

FINDING 2:
...

Focus on:
- Unusual traffic patterns or spikes
- Geographic threat sources
- Block rate trends
- Potential DDoS indicators"""

    def _create_rule_effectiveness_prompt(self, metrics: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Create prompt for rule effectiveness findings."""
        rules = metrics.get('rule_effectiveness', [])[:10]

        return f"""Analyze the following WAF rule effectiveness and provide 3-5 key findings.

## Rule Performance (Top 10):
{self._format_rule_data(rules)}

## Instructions:
Provide 3-5 concise findings in this EXACT format:

FINDING 1:
Finding: [Brief description of rule performance issue or optimization opportunity]
Severity: [HIGH/MEDIUM/LOW]
Rationale: [Evidence from data and reasoning for the finding]

FINDING 2:
...

Focus on:
- Rules with 0% hit rate (unused rules)
- Rules with very high hit rates (potential false positives)
- Missing rule coverage
- Rule optimization opportunities"""

    def _create_geographic_prompt(self, metrics: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Create prompt for geographic threat analysis findings."""
        geo_data = metrics.get('blocked_by_country', [])[:15]

        return f"""Analyze the following geographic threat distribution and provide 3-5 key findings.

## Blocked Traffic by Country (Top 15):
{self._format_geo_blocked_data(geo_data)}

## Instructions:
Provide 3-5 concise findings in this EXACT format:

FINDING 1:
Finding: [Brief description of geographic threat pattern]
Severity: [HIGH/MEDIUM/LOW]
Rationale: [Evidence from data and reasoning for the finding]

FINDING 2:
...

Focus on:
- Countries with high block rates
- Emerging threat sources
- Geographic anomalies
- Geo-blocking recommendations"""

    def _create_rule_action_prompt(self, metrics: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Create prompt for rule action distribution findings."""
        action_dist = metrics.get('action_distribution', {})

        # Extract counts from potentially dict values
        def _extract_count(value):
            if isinstance(value, dict):
                return value.get('count', 0)
            return value or 0

        allow_count = _extract_count(action_dist.get('ALLOW', 0))
        block_count = _extract_count(action_dist.get('BLOCK', 0))
        count_count = _extract_count(action_dist.get('COUNT', 0))
        total = max(allow_count + block_count + count_count, 1)

        return f"""Analyze the following rule action distribution and provide 3-5 key findings.

## Action Distribution:
- ALLOW: {allow_count:,} ({allow_count / total * 100:.1f}%)
- BLOCK: {block_count:,} ({block_count / total * 100:.1f}%)
- COUNT: {count_count:,} ({count_count / total * 100:.1f}%)

## Instructions:
Provide 3-5 concise findings in this EXACT format:

FINDING 1:
Finding: [Brief description of action distribution insight]
Severity: [HIGH/MEDIUM/LOW]
Rationale: [Evidence from data and reasoning for the finding]

FINDING 2:
...

Focus on:
- Balance between ALLOW/BLOCK/COUNT
- Rules in COUNT mode that should be promoted to BLOCK
- Over-blocking risks
- Security posture based on actions"""

    def _create_client_prompt(self, metrics: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Create prompt for client behavior analysis findings."""
        top_clients = metrics.get('top_clients', [])[:10]

        return f"""Analyze the following client behavior patterns and provide 3-5 key findings.

## Top Clients by Activity:
{self._format_client_data(top_clients)}

## Instructions:
Provide 3-5 concise findings in this EXACT format:

FINDING 1:
Finding: [Brief description of client behavior pattern]
Severity: [HIGH/MEDIUM/LOW]
Rationale: [Evidence from data and reasoning for the finding]

FINDING 2:
...

Focus on:
- Suspicious client behavior (high block rates)
- Potential bot traffic
- Legitimate clients being blocked
- Rate limiting recommendations"""

    def _format_geo_data(self, data: List[Dict]) -> str:
        """Format geographic data for prompt."""
        if not data:
            return "No geographic data available"

        lines = []
        for item in data:
            lines.append(
                f"- {item.get('country', 'Unknown')}: "
                f"{item.get('total_requests', 0):,} requests, "
                f"{item.get('threat_score', 0):.1f}% blocked"
            )
        return '\n'.join(lines)

    def _format_geo_blocked_data(self, data: List[Dict]) -> str:
        """Format blocked geographic data for prompt."""
        if not data:
            return "No blocked traffic data available"

        lines = []
        for item in data:
            lines.append(
                f"- {item.get('country', 'Unknown')}: "
                f"{item.get('blocked_requests', 0):,} blocked, "
                f"{item.get('block_rate', 0):.1f}% block rate"
            )
        return '\n'.join(lines)

    def _format_rule_data(self, data: List[Dict]) -> str:
        """Format rule data for prompt."""
        if not data:
            return "No rule data available"

        lines = []
        for rule in data:
            lines.append(
                f"- {rule.get('rule_name', 'Unknown')}: "
                f"{rule.get('hit_count', 0):,} hits, "
                f"{rule.get('hit_rate_percent', 0):.1f}% hit rate, "
                f"{rule.get('block_rate_percent', 0):.1f}% block rate"
            )
        return '\n'.join(lines)

    def _format_client_data(self, data: List[Dict]) -> str:
        """Format client data for prompt."""
        if not data:
            return "No client data available"

        lines = []
        for client in data:
            lines.append(
                f"- {client.get('client_ip', 'Unknown')}: "
                f"{client.get('total_requests', 0):,} requests, "
                f"{client.get('blocked_requests', 0):,} blocked "
                f"({client.get('block_rate', 0):.1f}%)"
            )
        return '\n'.join(lines)

    @classmethod
    def list_available_providers(cls) -> Dict[str, Any]:
        """
        List available LLM providers and their models.

        Returns:
            Dict: Provider information
        """
        return {
            'bedrock': {
                'name': 'AWS Bedrock',
                'models': BedrockProvider.list_available_models(),
                'requires': 'AWS credentials (profile or default)',
                'regions': ['us-east-1', 'us-west-2', 'eu-central-1', 'ap-southeast-1']
            },
            'openai': {
                'name': 'OpenAI',
                'models': OpenAIProvider.list_available_models(),
                'requires': 'OPENAI_API_KEY environment variable',
                'regions': ['Global']
            }
        }
