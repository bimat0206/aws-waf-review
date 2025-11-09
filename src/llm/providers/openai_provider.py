"""
OpenAI Provider via AWS Bedrock

Implementation for OpenAI models hosted on AWS Bedrock (gpt-oss-20b, gpt-oss-120b).
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider using AWS Bedrock (gpt-oss models)."""

    # Pricing per 1M tokens (AWS Bedrock pricing for OpenAI models)
    # Note: Update these based on actual Bedrock pricing
    PRICING = {
        'openai.gpt-oss-20b-1:0': {'input': 0.50, 'output': 1.50},  # Estimated
        'openai.gpt-oss-120b-1:0': {'input': 3.00, 'output': 9.00},  # Estimated
    }

    @classmethod
    def _load_supported_regions(cls) -> List[str]:
        """
        Load supported regions from bedrock_inference_profiles.json config.

        Returns:
            List of AWS regions that support OpenAI models on Bedrock
        """
        try:
            config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'bedrock_inference_profiles.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Extract all regions from regional_prefix_mapping
            regions = list(config.get('regional_prefix_mapping', {}).keys())

            if not regions:
                # Fallback to default regions from AWS docs
                logger.warning("No regions found in config, using defaults")
                return [
                    'us-east-1', 'us-east-2', 'us-west-2',
                    'ap-northeast-1', 'ap-south-1', 'ap-southeast-3',
                    'eu-central-1', 'eu-north-1', 'eu-south-1', 'eu-west-1', 'eu-west-2',
                    'sa-east-1'
                ]

            logger.debug(f"Loaded {len(regions)} supported regions from config")
            return regions

        except Exception as e:
            logger.warning(f"Error loading config, using default regions: {e}")
            # Fallback to default regions
            return [
                'us-east-1', 'us-east-2', 'us-west-2',
                'ap-northeast-1', 'ap-south-1', 'ap-southeast-3',
                'eu-central-1', 'eu-north-1', 'eu-south-1', 'eu-west-1', 'eu-west-2',
                'sa-east-1'
            ]

    def __init__(
        self,
        model: str = 'openai.gpt-oss-120b-1:0',
        region: str = 'us-east-1',
        profile: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize OpenAI provider via Bedrock.

        Args:
            model: Bedrock OpenAI model ID (default: gpt-oss-120b)
            region: AWS region for Bedrock (default: us-east-1)
            profile: AWS profile name (optional)
            **kwargs: Additional configuration
        """
        super().__init__(model, **kwargs)
        self.region = region
        self.profile = profile

        # Load supported regions dynamically from config
        supported_regions = self._load_supported_regions()

        # Validate region supports OpenAI models
        if region not in supported_regions:
            logger.warning(
                f"Region '{region}' may not support OpenAI models. "
                f"Supported regions: {', '.join(supported_regions[:5])}..."
            )
            logger.warning(f"Full list: {', '.join(supported_regions)}")

        # Validate model ID
        if model not in self.PRICING:
            logger.error(f"Invalid OpenAI model ID: {model}")
            logger.error(f"Valid model IDs: {list(self.PRICING.keys())}")
            raise ValueError(
                f"Invalid model ID '{model}'. "
                f"Valid OpenAI models: {list(self.PRICING.keys())}"
            )

        # Initialize boto3 session
        try:
            if profile:
                session = boto3.Session(profile_name=profile, region_name=region)
                logger.info(f"Using AWS profile: {profile}")
            else:
                session = boto3.Session(region_name=region)
                logger.info(f"Using default AWS credentials")

            self.client = session.client('bedrock-runtime')
            logger.info(f"Bedrock client initialized for OpenAI models in region: {region}")
            logger.info(f"Model: {model}")

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
        Send prompt to Bedrock OpenAI model and get analysis.

        Args:
            prompt: Complete prompt with injected data
            temperature: Sampling temperature (0.0-2.0, lower = more focused)
            max_tokens: Maximum tokens in response
            **kwargs: Additional Bedrock parameters

        Returns:
            Dict containing response, model, tokens, cost, duration
        """
        logger.info(f"Sending request to Bedrock OpenAI: {self.model}")
        logger.info(f"Prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)")

        start_time = time.time()

        try:
            # Prepare request body for OpenAI models on Bedrock
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_completion_tokens": max_tokens,
                "temperature": temperature,
            }

            # Add optional parameters
            if 'top_p' in kwargs:
                body['top_p'] = kwargs['top_p']
            if 'stop' in kwargs:
                body['stop'] = kwargs['stop']
            if 'frequency_penalty' in kwargs:
                body['frequency_penalty'] = kwargs['frequency_penalty']
            if 'presence_penalty' in kwargs:
                body['presence_penalty'] = kwargs['presence_penalty']

            # Add system message if provided
            if 'system_message' in kwargs:
                body['messages'].insert(0, {
                    "role": "system",
                    "content": kwargs['system_message']
                })

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

            # Extract text from OpenAI-format response
            response_text = response_body.get('choices', [{}])[0].get('message', {}).get('content', '')

            # Extract token usage
            usage = response_body.get('usage', {})
            input_tokens = usage.get('prompt_tokens', self._calculate_tokens(prompt))
            output_tokens = usage.get('completion_tokens', self._calculate_tokens(response_text))

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
                'finish_reason': response_body.get('choices', [{}])[0].get('finish_reason'),
                'raw_response': response_body
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"Bedrock API error [{error_code}]: {error_msg}")

            if error_code == 'ThrottlingException':
                logger.error("Request throttled - consider reducing request rate")
            elif error_code == 'ModelNotReadyException':
                logger.error(f"Model {self.model} not available in {self.region}")
                logger.error(f"Check model access at: https://console.aws.amazon.com/bedrock/home?region={self.region}#/modelaccess")
            elif error_code == 'ValidationException':
                supported_regions = self._load_supported_regions()
                logger.error("Invalid request - possible causes:")
                logger.error(f"  1. Model '{self.model}' not available in region '{self.region}'")
                logger.error(f"  2. Model access not enabled - visit AWS Bedrock console to request access")
                logger.error(f"  3. Supported regions: {', '.join(supported_regions)}")
                logger.error(f"  4. Valid models: {list(self.PRICING.keys())}")
                logger.error(f"\nTo enable model access, visit:")
                logger.error(f"https://console.aws.amazon.com/bedrock/home?region={self.region}#/modelaccess")
            elif error_code == 'AccessDeniedException':
                logger.error("Access denied - check IAM permissions for bedrock:InvokeModel")
                logger.error(f"Also verify model access is enabled in region {self.region}")

            return self._format_error(e)

        except Exception as e:
            logger.error(f"Unexpected error calling Bedrock OpenAI: {e}")
            return self._format_error(e)

    def test_connection(self) -> bool:
        """
        Test connection to Bedrock OpenAI models.

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

            logger.info("Bedrock OpenAI connection test successful")
            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost in USD.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            float: Estimated cost in USD
        """
        pricing = self.PRICING.get(self.model, {'input': 1.00, 'output': 3.00})

        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']

        return input_cost + output_cost

    @classmethod
    def list_available_models(cls) -> Dict[str, Dict[str, Any]]:
        """
        List available Bedrock OpenAI models with pricing.

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
        if 'gpt-oss-20b' in model_id:
            return 'GPT-OSS 20B (Fast)'
        elif 'gpt-oss-120b' in model_id:
            return 'GPT-OSS 120B (Production)'
        return model_id

    @staticmethod
    def _get_recommendation(model_id: str) -> str:
        """Get use case recommendation."""
        if '20b' in model_id:
            return 'Fast & cost-effective for straightforward analysis'
        elif '120b' in model_id:
            return 'Production use, higher reasoning capability (RECOMMENDED)'
        return 'General purpose'
