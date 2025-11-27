"""
Retry wrapper with configurable exponential backoff for LLM calls.
Integrates with config to support transient error recovery and graceful fallback.
"""

import logging
import time
from typing import Callable, Any, Optional, TypeVar, cast
from functools import wraps

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        Retrying,
        RetryError,
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Transient exceptions that warrant retry
TRANSIENT_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

# Map of provider names to their transient exception types
PROVIDER_TRANSIENT_EXCEPTIONS = {
    "google_genai": (
        Exception,  # google.api_core.exceptions.* would be ideal but hard to import
    ),
    "groq": (
        Exception,
    ),
    "openai": (
        Exception,
    ),
    "huggingface": (
        Exception,
    ),
}


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        enabled: bool = True,
        max_retries: int = 3,
        initial_delay_sec: float = 0.5,
        max_delay_sec: float = 8.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
    ):
        """
        Args:
            enabled: Whether retries are enabled
            max_retries: Maximum number of retry attempts
            initial_delay_sec: Initial delay between retries
            max_delay_sec: Maximum delay between retries
            backoff_multiplier: Multiplier for exponential backoff
            jitter: Add random jitter to delays
        """
        self.enabled = enabled
        self.max_retries = max_retries
        self.initial_delay_sec = initial_delay_sec
        self.max_delay_sec = max_delay_sec
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter

    @classmethod
    def from_env(cls, env_prefix: str = "LLM_RETRY") -> "RetryConfig":
        """Load retry config from environment variables."""
        import os

        enabled = os.getenv(f"{env_prefix}_ENABLED", "true").lower() == "true"
        max_retries = int(os.getenv(f"{env_prefix}_MAX_RETRIES", "3"))
        initial_delay_sec = float(os.getenv(f"{env_prefix}_INITIAL_DELAY_SEC", "0.5"))
        max_delay_sec = float(os.getenv(f"{env_prefix}_MAX_DELAY_SEC", "8.0"))
        backoff_multiplier = float(os.getenv(f"{env_prefix}_BACKOFF_MULTIPLIER", "2"))
        jitter = os.getenv(f"{env_prefix}_JITTER", "true").lower() == "true"

        return cls(
            enabled=enabled,
            max_retries=max_retries,
            initial_delay_sec=initial_delay_sec,
            max_delay_sec=max_delay_sec,
            backoff_multiplier=backoff_multiplier,
            jitter=jitter,
        )


def retry_on_transient(config: Optional[RetryConfig] = None) -> Callable[[F], F]:
    """
    Decorator to retry a function on transient errors.

    Args:
        config: RetryConfig instance; if None, loads from environment

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_transient()
        def call_llm(prompt):
            return provider.invoke(prompt)
    """
    if config is None:
        config = RetryConfig.from_env()

    def decorator(func: F) -> F:
        if not config.enabled or not TENACITY_AVAILABLE:
            # If retries disabled or tenacity unavailable, return function as-is
            return func

        def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None
            func_name = getattr(func, '__name__', 'function')

            while attempt < config.max_retries + 1:
                try:
                    attempt += 1
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(
                            f"[{func_name}] Success on attempt {attempt}/{config.max_retries + 1}"
                        )
                    return result
                except TRANSIENT_EXCEPTIONS as e:
                    last_exception = e
                    if attempt > config.max_retries:
                        logger.error(
                            f"[{func_name}] Failed after {attempt} attempts. "
                            f"Final error: {type(e).__name__}: {str(e)}"
                        )
                        raise
                    else:
                        delay = min(
                            config.initial_delay_sec * (config.backoff_multiplier ** (attempt - 1)),
                            config.max_delay_sec,
                        )
                        if config.jitter:
                            import random
                            delay *= (0.5 + random.random())
                        logger.warning(
                            f"[{func_name}] Attempt {attempt} failed with {type(e).__name__}: {str(e)}. "
                            f"Retrying in {delay:.2f}s ({attempt}/{config.max_retries} retries)..."
                        )
                        time.sleep(delay)
                except Exception as e:
                    # Non-transient exceptions should not be retried
                    logger.error(
                        f"[{func_name}] Non-transient error on attempt {attempt}: {type(e).__name__}: {str(e)}"
                    )
                    raise

            # Fallback (should not reach here due to raise above)
            if last_exception:
                raise last_exception
            raise RuntimeError(f"[{func_name}] Unexpected failure after {attempt} attempts")

        return cast(F, wrapper)

    return decorator
