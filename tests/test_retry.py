"""
Tests for retry mechanism with transient error handling.
"""

import pytest
from unittest.mock import Mock, patch, call
import time

from agent.retry import retry_on_transient, RetryConfig


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_config(self):
        """Test default retry config values."""
        config = RetryConfig()
        assert config.enabled is True
        assert config.max_retries == 3
        assert config.initial_delay_sec == 0.5
        assert config.max_delay_sec == 8.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True

    def test_from_env_default(self, monkeypatch):
        """Test loading config from env with defaults."""
        monkeypatch.delenv("LLM_RETRY_ENABLED", raising=False)
        monkeypatch.delenv("LLM_RETRY_MAX_RETRIES", raising=False)
        
        config = RetryConfig.from_env()
        assert config.enabled is True
        assert config.max_retries == 3

    def test_from_env_custom(self, monkeypatch):
        """Test loading config from env with custom values."""
        monkeypatch.setenv("LLM_RETRY_ENABLED", "false")
        monkeypatch.setenv("LLM_RETRY_MAX_RETRIES", "5")
        monkeypatch.setenv("LLM_RETRY_INITIAL_DELAY_SEC", "1.0")
        monkeypatch.setenv("LLM_RETRY_MAX_DELAY_SEC", "16.0")
        monkeypatch.setenv("LLM_RETRY_BACKOFF_MULTIPLIER", "3.0")
        
        config = RetryConfig.from_env()
        assert config.enabled is False
        assert config.max_retries == 5
        assert config.initial_delay_sec == 1.0
        assert config.max_delay_sec == 16.0
        assert config.backoff_multiplier == 3.0


class TestRetryOnTransient:
    """Tests for @retry_on_transient decorator."""

    def test_success_on_first_attempt(self):
        """Test function succeeds on first attempt."""
        mock_func = Mock(return_value="success")
        config = RetryConfig(max_retries=2)
        
        decorated = retry_on_transient(config)(mock_func)
        result = decorated("arg1", kwarg1="value1")
        
        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_with("arg1", kwarg1="value1")

    def test_retry_on_transient_then_success(self):
        """Test retrying after transient error and then succeeding."""
        mock_func = Mock(side_effect=[
            ConnectionError("Connection failed"),
            ConnectionError("Connection failed again"),
            "success"
        ])
        config = RetryConfig(max_retries=3, initial_delay_sec=0.01, jitter=False)
        
        decorated = retry_on_transient(config)(mock_func)
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 3

    def test_all_retries_fail(self):
        """Test that all retries fail and exception is raised."""
        mock_func = Mock(side_effect=ConnectionError("Network error"))
        config = RetryConfig(max_retries=2, initial_delay_sec=0.01, jitter=False)
        
        decorated = retry_on_transient(config)(mock_func)
        
        with pytest.raises(ConnectionError):
            decorated()
        
        # Should try: initial attempt + 2 retries = 3 total
        assert mock_func.call_count == 3

    def test_non_transient_exception_not_retried(self):
        """Test that non-transient exceptions are not retried."""
        mock_func = Mock(side_effect=ValueError("Invalid value"))
        config = RetryConfig(max_retries=2)
        
        decorated = retry_on_transient(config)(mock_func)
        
        with pytest.raises(ValueError):
            decorated()
        
        # Should only try once (no retries for non-transient)
        assert mock_func.call_count == 1

    def test_timeout_error_is_retried(self):
        """Test that TimeoutError is retried."""
        mock_func = Mock(side_effect=[
            TimeoutError("Request timeout"),
            "success"
        ])
        config = RetryConfig(max_retries=2, initial_delay_sec=0.01, jitter=False)
        
        decorated = retry_on_transient(config)(mock_func)
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 2

    def test_exponential_backoff(self):
        """Test that backoff delays increase exponentially."""
        mock_func = Mock(side_effect=ConnectionError("Network error"))
        config = RetryConfig(
            max_retries=3,
            initial_delay_sec=0.05,
            max_delay_sec=1.0,
            backoff_multiplier=2.0,
            jitter=False
        )
        
        decorated = retry_on_transient(config)(mock_func)
        
        start_time = time.time()
        with pytest.raises(ConnectionError):
            decorated()
        elapsed = time.time() - start_time
        
        # Should have delays: 0.05 + 0.10 + 0.20 = 0.35 seconds minimum
        # (retries with exponential backoff: initial_delay * (multiplier ^ (attempt-1)))
        assert elapsed >= 0.25  # Allow some tolerance for timing variations
        # Should try 4 times (initial + 3 retries)
        assert mock_func.call_count == 4

    def test_retries_disabled(self):
        """Test that retries are disabled when config.enabled=False."""
        mock_func = Mock(side_effect=ConnectionError("Network error"))
        config = RetryConfig(enabled=False, max_retries=3)
        
        decorated = retry_on_transient(config)(mock_func)
        
        with pytest.raises(ConnectionError):
            decorated()
        
        # Should only try once (retries disabled)
        assert mock_func.call_count == 1

    def test_preserves_function_behavior(self):
        """Test that decorator doesn't break function behavior."""
        def sample_func(x, y):
            """This is a sample function."""
            return x + y
        
        config = RetryConfig()
        decorated = retry_on_transient(config)(sample_func)
        
        # Function should still work correctly
        assert decorated(5, 10) == 15

    def test_with_multiple_arguments(self):
        """Test decorator works with multiple arguments."""
        mock_func = Mock(side_effect=[
            ConnectionError("Error"),
            "success"
        ])
        config = RetryConfig(max_retries=1, initial_delay_sec=0.01, jitter=False)
        
        decorated = retry_on_transient(config)(mock_func)
        result = decorated("arg1", "arg2", kwarg1="val1", kwarg2="val2")
        
        assert result == "success"
        mock_func.assert_called_with("arg1", "arg2", kwarg1="val1", kwarg2="val2")

    def test_max_delay_cap(self):
        """Test that backoff delay is capped at max_delay."""
        config = RetryConfig(
            max_retries=5,
            initial_delay_sec=1.0,
            max_delay_sec=2.0,
            backoff_multiplier=2.0,
            jitter=False
        )
        
        # Calculate delays: 1, 2, 2, 2 (capped)
        expected_delays = [1.0, 2.0, 2.0, 2.0]
        total_expected = sum(expected_delays)
        
        mock_func = Mock(side_effect=ConnectionError("Error"))
        decorated = retry_on_transient(config)(mock_func)
        
        start_time = time.time()
        with pytest.raises(ConnectionError):
            decorated()
        elapsed = time.time() - start_time
        
        # Allow 20% tolerance
        assert elapsed >= total_expected * 0.8


class TestLLMClientRetryIntegration:
    """Integration tests with LLMClient."""

    def test_llm_client_uses_configurable_retry(self):
        """Test that LLMClient uses configurable retry settings."""
        from agent.llm_client import LLMClient
        
        config = {
            "provider_preference": ["fallback"],
            "temperature": 0.1,
        }
        
        client = LLMClient(config)
        
        # Should have loaded retry config
        assert client.retry_config is not None
        assert hasattr(client.retry_config, "enabled")
        assert hasattr(client.retry_config, "max_retries")

    def test_llm_client_retry_on_connection_error(self, monkeypatch):
        """Test that LLMClient retries on connection errors."""
        monkeypatch.setenv("LLM_RETRY_ENABLED", "true")
        monkeypatch.setenv("LLM_RETRY_MAX_RETRIES", "2")
        monkeypatch.setenv("LLM_RETRY_INITIAL_DELAY_SEC", "0.01")
        
        from agent.llm_client import LLMClient
        
        config = {"provider_preference": ["fallback"]}
        client = LLMClient(config)
        
        # Mock provider to fail then succeed
        mock_provider = Mock()
        mock_provider.invoke = Mock(side_effect=[
            ConnectionError("Network error"),
            "LLM response"
        ])
        client.provider = mock_provider
        
        result = client._invoke_with_retry("test prompt")
        
        # Should have retried and succeeded
        assert result == "LLM response"
        assert mock_provider.invoke.call_count == 2
