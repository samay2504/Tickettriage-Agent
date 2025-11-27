"""
Rate limiting middleware for API endpoints.
Supports both Redis-based and in-memory token bucket algorithms.
Configurable per-IP and optional per-API-key rate limiting.
"""

import logging
import time
from typing import Optional, Dict, Any, Set, List
from collections import defaultdict
import os

logger = logging.getLogger(__name__)

try:
    from redis import Redis as RedisClient
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RateLimitConfig:
    """Configuration for rate limiting."""

    def __init__(
        self,
        enabled: bool = True,
        requests_per_period: int = 60,
        period_seconds: int = 60,
        storage: str = "redis",  # "redis" or "inmemory"
        bypass_keys: Optional[Set[str]] = None,
    ):
        """
        Args:
            enabled: Whether rate limiting is enabled
            requests_per_period: Max requests allowed in period
            period_seconds: Time period in seconds
            storage: Backend storage ("redis" or "inmemory")
            bypass_keys: Set of admin keys that bypass rate limiting
        """
        self.enabled = enabled
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.storage = storage
        self.bypass_keys = bypass_keys or set()

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Load rate limit config from environment variables."""
        enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        requests_per_period = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
        period_seconds = int(os.getenv("RATE_LIMIT_PERIOD_SECONDS", "60"))
        storage = os.getenv("RATE_LIMIT_STORAGE", "redis")
        
        bypass_keys_str = os.getenv("RATE_LIMIT_BYPASS_KEYS", "")
        bypass_keys = set(k.strip() for k in bypass_keys_str.split(",") if k.strip())

        return cls(
            enabled=enabled,
            requests_per_period=requests_per_period,
            period_seconds=period_seconds,
            storage=storage,
            bypass_keys=bypass_keys,
        )


class RateLimiter:
    """Base rate limiter interface."""

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for key."""
        raise NotImplementedError

    def get_retry_after(self, key: str) -> int:
        """Get seconds to wait before next allowed request."""
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    """
    In-memory rate limiter using sliding window counter algorithm.
    Note: Per-process only; not suitable for multi-process/distributed deployments.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.windows: Dict[str, List[float]] = {}  # key -> list of request timestamps

    def is_allowed(self, key: str) -> bool:
        """Check and update sliding window for key."""
        current_time = time.time()
        
        if key not in self.windows:
            self.windows[key] = []
        
        window = self.windows[key]
        
        # Remove old requests outside the window
        cutoff_time = current_time - self.config.period_seconds
        self.windows[key] = [t for t in window if t > cutoff_time]
        
        # Check if we can add a new request
        if len(self.windows[key]) < self.config.requests_per_period:
            self.windows[key].append(current_time)
            return True
        
        return False

    def get_retry_after(self, key: str) -> int:
        """Get seconds to wait before next request is allowed."""
        if key not in self.windows or not self.windows[key]:
            return 0
        
        current_time = time.time()
        oldest_request = self.windows[key][0]
        window_expiry = oldest_request + self.config.period_seconds
        
        retry_after = max(1, int(window_expiry - current_time) + 1)
        return retry_after


class RedisRateLimiter(RateLimiter):
    """Rate limiter using Redis INCR and EXPIRE."""

    def __init__(self, config: RateLimitConfig, redis_client: RedisClient):
        self.config = config
        self.redis_client = redis_client

    def is_allowed(self, key: str) -> bool:
        """Use Redis INCR to implement sliding window."""
        try:
            rate_key = f"rate_limit:{key}"
            current_count = self.redis_client.incr(rate_key)

            # Set expiry on first request in window
            if current_count == 1:
                self.redis_client.expire(rate_key, self.config.period_seconds)

            return current_count <= self.config.requests_per_period
        except Exception as e:
            logger.warning(f"Redis rate limiter error: {e}. Allowing request.")
            return True  # Graceful failure: allow request

    def get_retry_after(self, key: str) -> int:
        """Get TTL of the current rate limit window."""
        try:
            rate_key = f"rate_limit:{key}"
            ttl = self.redis_client.ttl(rate_key)
            return max(1, ttl) if ttl > 0 else self.config.period_seconds
        except Exception:
            return self.config.period_seconds


def create_rate_limiter(config: RateLimitConfig, redis_url: Optional[str] = None) -> RateLimiter:
    """
    Factory function to create appropriate rate limiter.
    
    Args:
        config: RateLimitConfig instance
        redis_url: Redis connection URL (required if storage='redis')
    
    Returns:
        RateLimiter instance
    """
    if not config.enabled:
        logger.info("Rate limiting disabled")
        return NoOpRateLimiter()

    if config.storage == "redis" and redis_url and REDIS_AVAILABLE:
        try:
            from redis import from_url
            redis_client = from_url(redis_url, decode_responses=True)
            redis_client.ping()  # Test connection
            logger.info("Redis rate limiter initialized")
            return RedisRateLimiter(config, redis_client)
        except Exception as e:
            logger.warning(f"Failed to initialize Redis rate limiter: {e}. Falling back to in-memory.")

    logger.info("Using in-memory rate limiter (per-process only)")
    return InMemoryRateLimiter(config)


class NoOpRateLimiter(RateLimiter):
    """No-op rate limiter that always allows requests."""

    def is_allowed(self, key: str) -> bool:
        return True

    def get_retry_after(self, key: str) -> int:
        return 0
