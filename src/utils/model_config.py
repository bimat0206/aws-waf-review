"""
Model Configuration Loader

This module provides functions to load model configurations from the
bedrock_inference_profiles.json configuration file.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def load_bedrock_config() -> Dict[str, Any]:
    """
    Load Bedrock inference profile configuration from JSON file.

    Returns:
        Dict[str, Any]: Configuration dictionary with regional mappings, models, and pricing
    """
    config_path = Path(__file__).parent.parent.parent / 'config' / 'bedrock_inference_profiles.json'

    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load Bedrock config from {config_path}: {e}")
        # Return minimal fallback config
        return {
            'available_models': {
                'default_model': 'anthropic.claude-sonnet-4-20250514-v1:0',
                'models': []
            }
        }


def get_available_models(region_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get list of available models, optionally filtered by region.

    Args:
        region_prefix: Regional prefix to filter models (us, eu, apac, global)
                      If None, returns all models

    Returns:
        List[Dict[str, Any]]: List of model dictionaries with id, name, description, pricing
    """
    config = load_bedrock_config()
    all_models = config.get('available_models', {}).get('models', [])

    if region_prefix:
        # Filter models available in the specified region
        filtered_models = [
            model for model in all_models
            if region_prefix in model.get('available_in', [])
        ]
        return filtered_models
    else:
        return all_models


def get_default_model() -> str:
    """
    Get the default model ID from configuration.

    Returns:
        str: Default model ID
    """
    config = load_bedrock_config()
    return config.get('available_models', {}).get('default_model', 'anthropic.claude-sonnet-4-20250514-v1:0')


def get_regional_prefix(region: str) -> str:
    """
    Get the regional prefix for a given AWS region.

    Args:
        region: AWS region code (e.g., 'ap-southeast-1', 'us-east-1')

    Returns:
        str: Regional prefix (us, eu, apac, global)
    """
    config = load_bedrock_config()
    mapping = config.get('regional_prefix_mapping', {})

    # Return the mapped prefix or default to 'us'
    return mapping.get(region, 'us')
