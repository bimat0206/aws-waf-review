"""
AWS Bedrock LLM Provider

Implementation for AWS Bedrock (Claude 3.x models).
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


def load_inference_profile_config() -> Dict[str, Any]:
    """Load inference profile configuration from config file."""
    config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'bedrock_inference_profiles.json'

    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load inference profile config: {e}. Using defaults.")
        return {
            'regional_prefix_mapping': {
                'us-east-1': 'us',
                'us-west-2': 'us',
                'eu-west-1': 'eu',
                'eu-central-1': 'eu',
                'ap-southeast-1': 'apac',
                'ap-southeast-2': 'apac',
                'ap-northeast-1': 'apac',
                'ap-south-1': 'apac'
            }
        }


class BedrockProvider(BaseLLMProvider):
    """AWS Bedrock provider for Claude models."""

    # Load configuration from file
    _CONFIG = load_inference_profile_config()

    # Regional prefix mapping for inference profiles (loaded from config)
    REGION_PREFIX_MAP = _CONFIG.get('regional_prefix_mapping', {})

    # Build pricing table from config
    _pricing_dict = {}
    for region, models in _CONFIG.get('model_pricing', {}).items():
        if region != 'description':
            _pricing_dict.update(models)

    PRICING = _pricing_dict if _pricing_dict else {
        # Fallback pricing if config fails to load
        'anthropic.claude-sonnet-4-5-20250929-v1:0': {'input': 3.00, 'output': 15.00},
        'anthropic.claude-3-haiku-20240307-v1:0': {'input': 0.25, 'output': 1.25},
    }

    def __init__(
        self,
        model: str = 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        region: str = 'us-east-1',
        profile: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Bedrock provider.

        Args:
            model: Bedrock model ID (can be with or without regional prefix)
            region: AWS region for Bedrock (default: us-east-1)
            profile: AWS profile name (optional)
            **kwargs: Additional configuration
        """
        # Apply regional prefix to model ID if needed
        model = self._apply_regional_prefix(model, region)

        super().__init__(model, **kwargs)
        self.region = region
        self.profile = profile

        # Initialize boto3 session
        try:
            if profile:
                session = boto3.Session(profile_name=profile, region_name=region)
                logger.info(f"Using AWS profile: {profile}")
            else:
                session = boto3.Session(region_name=region)
                logger.info(f"Using default AWS credentials")

            self.client = session.client('bedrock-runtime')
            logger.info(f"Bedrock client initialized in region: {region}")
            logger.info(f"Using model: {self.model}")

        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise ValueError("AWS credentials not configured. Set AWS_PROFILE or configure credentials.")
        except Exception as e:
            logger.error(f"Error initializing Bedrock client: {e}")
            raise

    def analyze(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 16000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send prompt to Bedrock Claude and get analysis.

        Args:
            prompt: Complete prompt with injected data
            temperature: Sampling temperature (0.0-1.0, lower = more focused)
            max_tokens: Maximum tokens in response
            **kwargs: Additional Bedrock parameters

        Returns:
            Dict containing response, model, tokens, cost, duration
        """
        logger.info(f"Sending request to Bedrock: {self.model}")
        logger.info(f"Prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)")

        start_time = time.time()

        try:
            # Prepare request body for Claude models
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            # Add optional parameters
            if 'top_p' in kwargs:
                body['top_p'] = kwargs['top_p']
            if 'top_k' in kwargs:
                body['top_k'] = kwargs['top_k']
            if 'stop_sequences' in kwargs:
                body['stop_sequences'] = kwargs['stop_sequences']

            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model,
                body=json.dumps(body),
                contentType='application/json',
                accept='application/json'
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            duration = time.time() - start_time

            # Extract text from response
            response_text = response_body.get('content', [{}])[0].get('text', '')

            # Extract token usage
            usage = response_body.get('usage', {})
            input_tokens = usage.get('input_tokens', self._calculate_tokens(prompt))
            output_tokens = usage.get('output_tokens', self._calculate_tokens(response_text))

            # Calculate cost
            cost = self._calculate_cost(input_tokens, output_tokens)

            logger.info(f"Response received in {duration:.2f}s")
            logger.info(f"Tokens: {input_tokens:,} input + {output_tokens:,} output = {input_tokens + output_tokens:,} total")
            logger.info(f"Estimated cost: ${cost:.4f}")

            return {
                'response': response_text,
                'model': self.model,
                'tokens_used': {
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': input_tokens + output_tokens
                },
                'cost_estimate': cost,
                'duration': duration,
                'stop_reason': response_body.get('stop_reason'),
                'raw_response': response_body
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"Bedrock API error [{error_code}]: {error_msg}")

            # Check if it's a channel program account error and try global profile fallback
            if error_code == 'ValidationException' and 'channel program' in error_msg.lower():
                logger.warning("Channel program account detected - trying global inference profile...")
                return self._try_global_fallback(prompt, temperature, max_tokens, **kwargs)

            if error_code == 'ThrottlingException':
                logger.error("Request throttled - consider reducing request rate")
            elif error_code == 'ModelNotReadyException':
                logger.error(f"Model {self.model} not available in {self.region}")
            elif error_code == 'ValidationException':
                logger.error("Invalid request parameters")

            return self._format_error(e)

        except Exception as e:
            logger.error(f"Unexpected error calling Bedrock: {e}")
            return self._format_error(e)

    def test_connection(self) -> bool:
        """
        Test connection to Bedrock.

        Returns:
            bool: True if connection successful
        """
        try:
            # Simple test with minimal tokens
            test_prompt = "Respond with: OK"
            result = self.analyze(test_prompt, max_tokens=10)

            if result.get('error'):
                logger.error(f"Connection test failed: {result['error']}")
                return False

            logger.info("Bedrock connection test successful")
            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def _try_global_fallback(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Try to use global inference profile as fallback for channel program accounts.

        Args:
            prompt: Complete prompt with injected data
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional Bedrock parameters

        Returns:
            Dict containing response or error
        """
        # Convert region-specific profile to global profile
        global_model = self._to_global_profile(self.model)

        if global_model == self.model:
            logger.error("No global fallback available for this model")
            return self._format_error(Exception("Channel program account restriction - no global profile available"))

        logger.info(f"Attempting with global inference profile: {global_model}")

        # Temporarily switch model
        original_model = self.model
        self.model = global_model

        try:
            # Prepare request body for Claude models
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            # Add optional parameters
            if 'top_p' in kwargs:
                body['top_p'] = kwargs['top_p']
            if 'top_k' in kwargs:
                body['top_k'] = kwargs['top_k']
            if 'stop_sequences' in kwargs:
                body['stop_sequences'] = kwargs['stop_sequences']

            # Invoke model with global profile
            start_time = time.time()
            response = self.client.invoke_model(
                modelId=global_model,
                body=json.dumps(body),
                contentType='application/json',
                accept='application/json'
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            duration = time.time() - start_time

            # Extract text from response
            response_text = response_body.get('content', [{}])[0].get('text', '')

            # Extract token usage
            usage = response_body.get('usage', {})
            input_tokens = usage.get('input_tokens', self._calculate_tokens(prompt))
            output_tokens = usage.get('output_tokens', self._calculate_tokens(response_text))

            # Calculate cost
            cost = self._calculate_cost(input_tokens, output_tokens)

            logger.info(f"✅ Global profile succeeded! Response received in {duration:.2f}s")
            logger.info(f"Tokens: {input_tokens:,} input + {output_tokens:,} output = {input_tokens + output_tokens:,} total")
            logger.info(f"Estimated cost: ${cost:.4f}")

            return {
                'response': response_text,
                'model': global_model,
                'tokens_used': {
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': input_tokens + output_tokens
                },
                'cost_estimate': cost,
                'duration': duration,
                'stop_reason': response_body.get('stop_reason'),
                'raw_response': response_body
            }

        except Exception as e:
            logger.error(f"Global profile fallback also failed: {e}")
            return self._format_error(e)
        finally:
            # Restore original model
            self.model = original_model

    @classmethod
    def _apply_regional_prefix(cls, model_id: str, region: str) -> str:
        """
        Apply the correct regional prefix to a model ID based on the AWS region.

        Args:
            model_id: Model ID (can be with or without regional prefix)
            region: AWS region (e.g., us-east-1, ap-southeast-1)

        Returns:
            str: Model ID with correct regional prefix
        """
        # If already has a regional prefix (us., eu., apac., global.), return as is
        if any(model_id.startswith(prefix + '.') for prefix in ['us', 'eu', 'apac', 'global']):
            return model_id

        # If it's a direct model ID (anthropic.claude-*), add regional prefix
        if model_id.startswith('anthropic.'):
            # Get regional prefix from mapping (default to 'us' if region not in map)
            regional_prefix = cls.REGION_PREFIX_MAP.get(region, 'us')

            # Extract the model portion after 'anthropic.'
            model_portion = model_id.replace('anthropic.', '', 1)

            # Construct regional inference profile ID
            regional_model_id = f"{regional_prefix}.anthropic.{model_portion}"

            logger.info(f"Converting {model_id} to regional inference profile: {regional_model_id}")
            return regional_model_id

        # Return as is (might be a custom ID format)
        return model_id

    def _to_global_profile(self, model_id: str) -> str:
        """
        Convert region-specific inference profile to global profile.

        Args:
            model_id: Model ID (e.g., us.anthropic.claude-sonnet-4-5-20250929-v1:0)

        Returns:
            str: Global profile ID (e.g., global.anthropic.claude-sonnet-4-5-20250929-v1:0)
        """
        if model_id.startswith('us.'):
            return model_id.replace('us.', 'global.', 1)
        elif model_id.startswith('eu.'):
            return model_id.replace('eu.', 'global.', 1)
        elif model_id.startswith('apac.'):
            return model_id.replace('apac.', 'global.', 1)
        else:
            # Already global or direct model ID
            return model_id

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost in USD.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            float: Estimated cost in USD
        """
        pricing = self.PRICING.get(self.model, {'input': 3.00, 'output': 15.00})

        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']

        return input_cost + output_cost

    @classmethod
    def list_available_models(cls) -> Dict[str, Dict[str, Any]]:
        """
        List available Bedrock Claude models with pricing.

        Returns:
            Dict: Model information including pricing
        """
        return {
            model_id: {
                'name': cls._get_model_name(model_id),
                'pricing': pricing,
                'recommended_for': cls._get_recommendation(model_id)
            }
            for model_id, pricing in cls.PRICING.items()
        }

    @staticmethod
    def _get_model_name(model_id: str) -> str:
        """Get friendly model name."""
        if 'claude-3-5-sonnet' in model_id:
            return 'Claude 3.5 Sonnet'
        elif 'claude-3-sonnet' in model_id:
            return 'Claude 3 Sonnet'
        elif 'claude-3-haiku' in model_id:
            return 'Claude 3 Haiku'
        elif 'claude-3-opus' in model_id:
            return 'Claude 3 Opus'
        return model_id

    @staticmethod
    def _get_recommendation(model_id: str) -> str:
        """Get use case recommendation."""
        if 'haiku' in model_id:
            return 'Fast & cost-effective for straightforward analysis'
        elif 'sonnet' in model_id:
            return 'Balanced performance & cost (RECOMMENDED)'
        elif 'opus' in model_id:
            return 'Maximum accuracy for complex analysis'
        return 'General purpose'
