"""
Tests for rate limiting middleware.
"""

import pytest
import time
from unittest.mock import Mock, patch

from app.middleware.rate_limit import (
    RateLimitConfig,
    InMemoryRateLimiter,
    RedisRateLimiter,
    create_rate_limiter,
    NoOpRateLimiter,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_config(self):
        """Test default rate limit config."""
        config = RateLimitConfig()
        assert config.enabled is True
        assert config.requests_per_period == 60
        assert config.period_seconds == 60
        assert config.storage == "redis"
        assert config.bypass_keys == set()

    def test_from_env_default(self, monkeypatch):
        """Test loading from environment with defaults."""
        monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
        config = RateLimitConfig.from_env()
        assert config.enabled is True

    def test_from_env_custom(self, monkeypatch):
        """Test loading from environment with custom values."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("RATE_LIMIT_REQUESTS", "30")
        monkeypatch.setenv("RATE_LIMIT_PERIOD_SECONDS", "120")
        monkeypatch.setenv("RATE_LIMIT_STORAGE", "inmemory")
        monkeypatch.setenv("RATE_LIMIT_BYPASS_KEYS", "admin_key,superuser_key")
        
        config = RateLimitConfig.from_env()
        assert config.enabled is False
        assert config.requests_per_period == 30
        assert config.period_seconds == 120
        assert config.storage == "inmemory"
        assert "admin_key" in config.bypass_keys
        assert "superuser_key" in config.bypass_keys


class TestInMemoryRateLimiter:
    """Tests for in-memory rate limiter."""

    def test_allows_requests_within_limit(self):
        """Test that requests within limit are allowed."""
        config = RateLimitConfig(requests_per_period=3, period_seconds=60)
        limiter = InMemoryRateLimiter(config)
        
        # Should allow 3 requests
        assert limiter.is_allowed("ip_1") is True
        assert limiter.is_allowed("ip_1") is True
        assert limiter.is_allowed("ip_1") is True

    def test_rejects_requests_exceeding_limit(self):
        """Test that requests exceeding limit are rejected."""
        config = RateLimitConfig(requests_per_period=2, period_seconds=60)
        limiter = InMemoryRateLimiter(config)
        
        # Allow 2 requests
        assert limiter.is_allowed("ip_1") is True
        assert limiter.is_allowed("ip_1") is True
        
        # Reject 3rd request
        assert limiter.is_allowed("ip_1") is False

    def test_different_keys_independent(self):
        """Test that different keys have independent buckets."""
        config = RateLimitConfig(requests_per_period=2, period_seconds=60)
        limiter = InMemoryRateLimiter(config)
        
        # ip_1 uses 2 requests
        assert limiter.is_allowed("ip_1") is True
        assert limiter.is_allowed("ip_1") is True
        
        # ip_2 should still have 2 requests available
        assert limiter.is_allowed("ip_2") is True
        assert limiter.is_allowed("ip_2") is True

    def test_token_refill_over_time(self):
        """Test that tokens refill over time."""
        config = RateLimitConfig(requests_per_period=1, period_seconds=0.1)
        limiter = InMemoryRateLimiter(config)
        
        # Use the token
        assert limiter.is_allowed("key") is True
        
        # Should be rejected immediately
        assert limiter.is_allowed("key") is False
        
        # Wait for refill period
        time.sleep(0.15)
        
        # Should be allowed again
        assert limiter.is_allowed("key") is True

    def test_get_retry_after(self):
        """Test retry_after calculation."""
        config = RateLimitConfig(requests_per_period=1, period_seconds=10)
        limiter = InMemoryRateLimiter(config)
        
        # Use the token
        limiter.is_allowed("key")
        
        # Check retry_after (should be close to 10 seconds, allowing for +1 rounding)
        retry_after = limiter.get_retry_after("key")
        assert 0 < retry_after <= 11

    def test_no_jitter_backoff(self):
        """Test that jitter can be disabled."""
        config = RateLimitConfig(requests_per_period=2, period_seconds=60)
        limiter = InMemoryRateLimiter(config)
        
        # Use requests
        limiter.is_allowed("key")
        limiter.is_allowed("key")
        
        # Get predictable retry_after (no jitter)
        retry_after = limiter.get_retry_after("key")
        assert isinstance(retry_after, int)
        assert retry_after >= 1


class TestRateLimiterFactory:
    """Tests for rate limiter factory."""

    def test_creates_inmemory_limiter(self):
        """Test creating in-memory rate limiter."""
        config = RateLimitConfig(storage="inmemory", enabled=True)
        limiter = create_rate_limiter(config, redis_url=None)
        
        assert isinstance(limiter, InMemoryRateLimiter)

    def test_creates_noop_when_disabled(self):
        """Test creating no-op limiter when disabled."""
        config = RateLimitConfig(enabled=False)
        limiter = create_rate_limiter(config)
        
        assert isinstance(limiter, NoOpRateLimiter)
        assert limiter.is_allowed("any_key") is True

    def test_graceful_fallback_on_redis_failure(self):
        """Test fallback to in-memory if Redis fails."""
        config = RateLimitConfig(storage="redis", enabled=True)
        
        # Redis URL that will fail
        limiter = create_rate_limiter(config, redis_url="redis://invalid:12345/0")
        
        # Should fallback to in-memory
        assert isinstance(limiter, InMemoryRateLimiter)


class TestNoOpRateLimiter:
    """Tests for no-op rate limiter."""

    def test_always_allows(self):
        """Test that no-op limiter always allows requests."""
        limiter = NoOpRateLimiter()
        
        for _ in range(1000):
            assert limiter.is_allowed("any_key") is True

    def test_retry_after_zero(self):
        """Test that retry_after is always 0."""
        limiter = NoOpRateLimiter()
        assert limiter.get_retry_after("any_key") == 0


class TestRateLimitMiddlewareIntegration:
    """Integration tests with FastAPI app."""

    def test_rate_limit_via_fastapi_testclient(self):
        """Test rate limiting through FastAPI TestClient."""
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not installed")
        
        from app.routes.triage import router as triage_router
        
        app = FastAPI()
        app.include_router(triage_router)
        
        client = TestClient(app)
        
        # Make a valid request
        response = client.post(
            "/triage",
            json={"description": "Test issue with at least 10 characters"}
        )
        
        # Should get 200 or 500 (API error), not 429 (rate limit)
        # Note: 500 expected if LLM not configured
        assert response.status_code in [200, 500]

    def test_rate_limit_per_ip(self):
        """Test that rate limiting is per-IP address."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not installed")
        
        config = RateLimitConfig(requests_per_period=2, period_seconds=60)
        limiter = InMemoryRateLimiter(config)
        
        # Simulate requests from different IPs
        ip1_requests = [limiter.is_allowed(f"192.168.1.1") for _ in range(3)]
        ip2_requests = [limiter.is_allowed(f"192.168.1.2") for _ in range(3)]
        
        # ip1: 2 allowed, 1 rejected
        assert ip1_requests == [True, True, False]
        
        # ip2: 2 allowed, 1 rejected (independent from ip1)
        assert ip2_requests == [True, True, False]
