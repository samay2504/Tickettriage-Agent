"""
Tests for fallback and error handling.
"""

import pytest
import json
from unittest.mock import Mock, patch
from agent.orchestrator import create_orchestrator
from agent.llm_client import LLMClient


class TestFallbackBehavior:
    """Tests for fallback behavior when LLM fails."""
    
    def test_fallback_on_none_response(self, test_settings):
        """Test fallback when LLM returns None."""
        orchestrator = create_orchestrator(test_settings)
        
        # Mock LLM to return None
        orchestrator.llm_client.invoke = Mock(return_value=None)
        
        response, meta = orchestrator.triage("Test ticket")
        
        # Should still return a valid response
        assert response is not None
        assert response.summary is not None
    
    def test_fallback_on_invalid_json(self, test_settings):
        """Test fallback when LLM returns invalid JSON."""
        orchestrator = create_orchestrator(test_settings)
        
        # Mock LLM to return invalid JSON
        orchestrator.llm_client.invoke = Mock(return_value="This is not JSON")
        
        response, meta = orchestrator.triage("Test ticket")
        
        # Should still return a valid response
        assert response is not None
        assert response.summary is not None
    
    def test_fallback_response_structure(self, test_settings):
        """Test fallback response has correct structure."""
        orchestrator = create_orchestrator(test_settings)
        orchestrator.llm_client.invoke = Mock(return_value=None)
        
        response, meta = orchestrator.triage("Test ticket")
        
        # Fallback response should have all fields
        assert response.category in ["Bug", "Billing", "Login", "Performance", "Question", "Other"]
        assert response.severity in ["Low", "Medium", "High", "Critical"]


class TestLLMClientFallback:
    """Tests for LLM client fallback modes."""
    
    def test_llm_client_import_failure(self):
        """Test LLM client handles missing provider module gracefully."""
        # Test that LLMClient can be instantiated even if provider init fails
        client = LLMClient({"temperature": 0.1})
        
        # Should have a fallback provider
        assert client.provider is not None
        
        config = {"temperature": 0.1, "provider_preference": ["openai"]}
        client = LLMClient(config)
        
        # Should have fallback provider
        assert client.provider is not None
    
    def test_llm_client_invoke_returns_none(self):
        """Test LLM client handles None response."""
        client = LLMClient({"temperature": 0.1})
        client.provider = Mock()
        client.provider.invoke = Mock(return_value=None)
        
        response = client.invoke("test prompt")
        
        assert response is None
    
    def test_llm_client_invoke_with_dict_response(self):
        """Test LLM client handles dict response."""
        client = LLMClient({"temperature": 0.1})
        client.provider = Mock()
        client.provider.invoke = Mock(return_value={"content": "test content"})
        
        response = client.invoke("test prompt")
        
        assert response == "test content"
    
    def test_llm_client_invoke_with_string_response(self):
        """Test LLM client handles string response."""
        client = LLMClient({"temperature": 0.1})
        client.provider = Mock()
        client.provider.invoke = Mock(return_value="test string")
        
        response = client.invoke("test prompt")
        
        assert response == "test string"


class TestErrorRecovery:
    """Tests for error recovery."""
    
    def test_malformed_kb_matches(self, test_settings):
        """Test handling of malformed KB matches."""
        orchestrator = create_orchestrator(test_settings)
        
        # LLM returns response referencing non-existent KB IDs
        llm_response = json.dumps({
            "summary": "Test",
            "category": "Bug",
            "severity": "Low",
            "known_issue": True,
            "kb_ids": ["NONEXISTENT-1", "NONEXISTENT-2"],
            "suggested_action": "Check KB"
        })
        
        orchestrator.llm_client.invoke = Mock(return_value=llm_response)
        response, meta = orchestrator.triage("Test")
        
        # Should handle gracefully
        assert response is not None
        assert isinstance(response.kb_matches, list)
    
    def test_parse_json_with_markdown(self, test_settings):
        """Test parsing JSON wrapped in markdown."""
        orchestrator = create_orchestrator(test_settings)
        
        # LLM returns JSON wrapped in markdown
        llm_response = """```json
{
    "summary": "Test summary",
    "category": "Bug",
    "severity": "High",
    "known_issue": false,
    "kb_ids": [],
    "suggested_action": "Test action"
}
```"""
        
        orchestrator.llm_client.invoke = Mock(return_value=llm_response)
        response, meta = orchestrator.triage("Test")
        
        assert response.summary == "Test summary"
        assert response.category == "Bug"
