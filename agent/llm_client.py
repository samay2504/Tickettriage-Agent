"""
LLM client wrapper around llm_provider.create_llm_provider.
Implements retries, backoff, and standardized invoke interface.
Supports configurable retry behavior via environment variables.
"""

import logging
import json
import time
from typing import Optional, Dict, Any

from agent.retry import retry_on_transient, RetryConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper around LLM provider with configurable retry and error handling."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = None
        self.retry_config = RetryConfig.from_env()
        logger.info(f"Retry config: enabled={self.retry_config.enabled}, max_retries={self.retry_config.max_retries}")
        self.initialize_provider()
    
    def initialize_provider(self):
        """Initialize the LLM provider."""
        try:
            # Import the llm_provider module from same package
            # This handles all provider setup including fallbacks
            from .llm_provider import create_llm_provider
            
            # Build provider config
            provider_config = {
                "provider_preference": self.config.get("provider_preference", [
                    "google_genai", "groq", "huggingface", "openai", "fallback"
                ]),
                "temperature": self.config.get("temperature", 0.1),
            }
            
            self.provider = create_llm_provider(provider_config)
            logger.info(f"LLM provider initialized: {self.provider.current_provider}")
        except ImportError as e:
            logger.error(f"Failed to import llm_provider: {e}. Using fallback mode.")
            self.provider = self._create_fallback_provider()
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}. Using fallback mode.")
            self.provider = self._create_fallback_provider()
    
    def _create_fallback_provider(self):
        """Create a fallback provider."""
        class FallbackProvider:
            current_provider = "fallback"
            model_name = "fallback"
            
            def invoke(self, prompt):
                return None
            
            def get_provider_info(self):
                return {"provider": "fallback", "available": False, "fallback_mode": True}
        
        return FallbackProvider()
    
    @retry_on_transient()
    def _invoke_with_retry(self, prompt: str) -> Optional[str]:
        """
        Internal invoke method with retry logic.
        
        Args:
            prompt: The prompt to send to LLM
        
        Returns:
            LLM response as string or None if failed
        """
        if not self.provider:
            return None
        
        response = self.provider.invoke(prompt)
        
        # Handle different response formats
        if response is None:
            logger.warning("LLM returned None")
            return None
        
        if isinstance(response, dict):
            if 'content' in response:
                return response['content']
            elif 'text' in response:
                return response['text']
            else:
                return json.dumps(response)
        elif isinstance(response, str):
            return response
        else:
            # Try to get content attribute
            if hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'text'):
                return response.text
            else:
                return str(response)

    def invoke(self, prompt: str, **kwargs) -> Optional[str]:
        """
        Invoke the LLM with configurable retry logic.
        
        Args:
            prompt: The prompt to send to LLM
            **kwargs: Additional parameters
        
        Returns:
            LLM response as string or None if failed
        
        Raises:
            Exception: If all retry attempts fail and retries are enabled
        """
        try:
            result = self._invoke_with_retry(prompt)
            return result
        except Exception as e:
            logger.error(
                f"LLM invocation failed after {self.retry_config.max_retries} retries: {type(e).__name__}: {str(e)}"
            )
            # Re-raise to let orchestrator handle fallback
            raise
    
    def get_provider_name(self) -> str:
        """Get the current provider name."""
        if not self.provider:
            return "unknown"
        return getattr(self.provider, 'current_provider', 'unknown')
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information."""
        if not self.provider:
            return {"provider": "unknown", "available": False}
        
        if hasattr(self.provider, 'get_provider_info'):
            return self.provider.get_provider_info()
        else:
            return {
                "provider": self.get_provider_name(),
                "available": True,
                "fallback_mode": False
            }
    
    def is_fallback_mode(self) -> bool:
        """Check if using fallback mode."""
        info = self.get_provider_info()
        return info.get('fallback_mode', False)


def create_llm_client(config: Dict[str, Any]) -> LLMClient:
    """Factory function to create LLM client."""
    return LLMClient(config)
