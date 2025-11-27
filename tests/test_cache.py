"""
Tests for cache functionality.
"""

import pytest
from unittest.mock import Mock, patch
from cache.redis_client import RedisClient


class TestRedisClient:
    """Tests for Redis client."""
    
    def test_compute_key(self):
        """Test cache key computation."""
        description1 = "Test issue"
        description2 = "TEST ISSUE"
        
        key1 = RedisClient.compute_key(description1)
        key2 = RedisClient.compute_key(description2)
        
        # Same normalized content should produce same key
        assert key1 == key2
        assert "triage:v1:" in key1
    
    def test_compute_key_different(self):
        """Test different keys for different input."""
        key1 = RedisClient.compute_key("Issue A")
        key2 = RedisClient.compute_key("Issue B")
        
        assert key1 != key2
    
    def test_compute_key_with_namespace(self):
        """Test key computation with custom namespace."""
        key = RedisClient.compute_key("test", namespace="custom")
        assert "custom:v1:" in key
    
    def test_redis_not_available(self):
        """Test behavior when Redis is not available."""
        # Create client with bad connection string
        client = RedisClient("redis://invalid-host:99999/0", enabled=True)
        
        # Should handle connection failure gracefully
        assert not client.is_available()
    
    def test_redis_client_disabled(self):
        """Test Redis client when disabled."""
        client = RedisClient(enabled=False)
        
        assert not client.is_available()
        assert not client.set("test", {"key": "value"})
        assert client.get("test") is None


class TestCacheBehavior:
    """Tests for cache behavior."""
    
    def test_cache_key_format(self):
        """Test cache key format is consistent."""
        key = RedisClient.compute_key("test description")
        
        # Should follow pattern: namespace:version:hash
        parts = key.split(":")
        assert len(parts) == 3
        assert parts[0] == "triage"
        assert parts[1] == "v1"
        assert len(parts[2]) == 64  # SHA256 hash is 64 chars
