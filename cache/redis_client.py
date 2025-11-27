"""
Redis cache client with connection pooling and caching utilities.
"""

import json
import logging
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis cache client."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", enabled: bool = True):
        self.redis_url = redis_url
        self.enabled = enabled
        self.client = None
        
        if enabled:
            self._connect()
    
    def _connect(self):
        """Connect to Redis."""
        try:
            import redis
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis: {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
            self.enabled = False
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache."""
        if not self.is_available():
            return None
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """Set value in cache with TTL."""
        if not self.is_available():
            return False
        
        try:
            json_value = json.dumps(value)
            self.client.setex(key, ttl_seconds, json_value)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.is_available():
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self.is_available():
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern failed for {pattern}: {e}")
            return 0
    
    def flush(self) -> bool:
        """Flush all cache."""
        if not self.is_available():
            return False
        
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            logger.warning(f"Cache flush failed: {e}")
            return False
    
    @staticmethod
    def compute_key(description: str, namespace: str = "triage") -> str:
        """Compute cache key from description."""
        # Normalize description
        normalized = description.strip().lower()
        # Hash with SHA256
        hash_value = hashlib.sha256(normalized.encode()).hexdigest()
        return f"{namespace}:v1:{hash_value}"


# Global Redis client singleton
_redis_client: Optional[RedisClient] = None


def get_redis_client(redis_url: str = "redis://localhost:6379/0", enabled: bool = True) -> RedisClient:
    """Get or create Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient(redis_url, enabled)
    return _redis_client


def close_redis_client():
    """Close Redis client connection."""
    global _redis_client
    if _redis_client and _redis_client.client:
        try:
            _redis_client.client.close()
            logger.info("Closed Redis connection")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")
    _redis_client = None
