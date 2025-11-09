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
