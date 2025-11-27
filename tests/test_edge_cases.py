"""
Tests for edge cases and validation.
"""

import pytest
from agent.orchestrator import create_orchestrator, TicketTriageOrchestrator
from config.settings import Settings


class TestValidation:
    """Tests for input validation."""
    
    def test_empty_description(self, test_settings):
        """Test empty description validation."""
        orchestrator = create_orchestrator(test_settings)
        response, meta = orchestrator.triage("")
        
        assert response.meta.get("error") == "VALIDATION_FAILED"
    
    def test_very_long_description(self, test_settings):
        """Test description truncation."""
        orchestrator = create_orchestrator(test_settings)
        long_description = "x" * 15000
        response, meta = orchestrator.triage(long_description)
        
        # Should truncate without error
        assert response is not None
    
    def test_description_at_min_length(self, test_settings):
        """Test description at minimum length."""
        orchestrator = create_orchestrator(test_settings)
        response, meta = orchestrator.triage("a")
        
        # Should process successfully (may have other errors, but not validation)
        assert response is not None
    
    def test_description_at_max_length(self, test_settings):
        """Test description at maximum length."""
        orchestrator = create_orchestrator(test_settings)
        description = "x" * test_settings.description_max_length
        response, meta = orchestrator.triage(description)
        
        # Should process without truncation errors
        assert response is not None
    
    def test_description_unicode(self, test_settings):
        """Test description with unicode characters."""
        orchestrator = create_orchestrator(test_settings)
        description = "Users report 错误 😊 エラー on mobile checkout"
        response, meta = orchestrator.triage(description)
        
        # Should handle unicode
        assert response is not None


class TestTriageResponse:
    """Tests for triage response structure."""
    
    def test_response_structure(self, test_settings):
        """Test response has all required fields."""
        orchestrator = create_orchestrator(test_settings)
        response, meta = orchestrator.triage("Test ticket")
        
        assert hasattr(response, 'summary')
        assert hasattr(response, 'category')
        assert hasattr(response, 'severity')
        assert hasattr(response, 'kb_matches')
        assert hasattr(response, 'known_issue')
        assert hasattr(response, 'suggested_action')
        assert hasattr(response, 'meta')
    
    def test_response_to_dict(self, test_settings):
        """Test response can be serialized to dict."""
        orchestrator = create_orchestrator(test_settings)
        response, meta = orchestrator.triage("Test ticket")
        
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert "summary" in response_dict
        assert "meta" in response_dict
    
    def test_valid_category(self, test_settings):
        """Test response has valid category."""
        orchestrator = create_orchestrator(test_settings)
        response, meta = orchestrator.triage("Test bug")
        
        valid_categories = ["Bug", "Billing", "Login", "Performance", "Question", "Other"]
        assert response.category in valid_categories
    
    def test_valid_severity(self, test_settings):
        """Test response has valid severity."""
        orchestrator = create_orchestrator(test_settings)
        response, meta = orchestrator.triage("Test issue")
        
        valid_severities = ["Low", "Medium", "High", "Critical"]
        assert response.severity in valid_severities
    
    def test_meta_includes_latency(self, test_settings):
        """Test meta includes latency measurement."""
        orchestrator = create_orchestrator(test_settings)
        response, meta = orchestrator.triage("Test")
        
        assert "latency_ms" in response.meta
        assert response.meta["latency_ms"] >= 0
    
    def test_meta_includes_provider(self, test_settings):
        """Test meta includes provider info."""
        orchestrator = create_orchestrator(test_settings)
        response, meta = orchestrator.triage("Test")
        
        assert "provider" in response.meta
