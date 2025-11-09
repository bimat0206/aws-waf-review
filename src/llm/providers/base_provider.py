"""
Base LLM Provider

Abstract base class for LLM provider implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, **kwargs):
        """
        Initialize the LLM provider.

        Args:
            model: Model identifier (e.g., 'claude-3-5-sonnet-20241022', 'gpt-4')
            **kwargs: Provider-specific configuration
        """
        self.model = model
        self.config = kwargs
        logger.info(f"Initialized {self.__class__.__name__} with model: {model}")

    @abstractmethod
    def analyze(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Send prompt to LLM and get analysis.

        Args:
            prompt: Complete prompt with injected data
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Dict containing:
                - 'response': Raw LLM response text
                - 'model': Model used
                - 'tokens_used': Token usage statistics
                - 'cost_estimate': Estimated cost in USD
                - 'duration': Response time in seconds

        Raises:
            Exception: If API call fails
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to LLM provider.

        Returns:
            bool: True if connection successful
        """
        pass

    def _calculate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Input text

        Returns:
            int: Estimated token count (rough estimate: chars/4)
        """
        return len(text) // 4

    def _format_error(self, error: Exception) -> Dict[str, Any]:
        """
        Format error response.

        Args:
            error: Exception that occurred

        Returns:
            Dict: Error information
        """
        return {
            'error': str(error),
            'error_type': type(error).__name__,
            'response': None,
            'model': self.model,
            'tokens_used': 0,
            'cost_estimate': 0.0,
            'duration': 0.0
        }
