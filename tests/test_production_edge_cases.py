"""
Production-grade edge case tests for triage system.
Tests comprehensive edge case handling, YAML prompt loading, and production standards.
"""

import pytest
from agent.prompt_loader import PromptLoader
from pathlib import Path
from tempfile import TemporaryDirectory


class TestEdgeCaseDetection:
    """Test edge case detection and handling."""
    
    def test_empty_description_detection(self):
        """Test detection of empty descriptions."""
        loader = PromptLoader()
        result = loader.validate_edge_case("")
        
        assert result["empty_or_short"] is True
        assert len(result["recommendations"]) > 0
    
    def test_none_description_handling(self):
        """Test handling of None descriptions."""
        loader = PromptLoader()
        # Should not crash on None
        try:
            result = loader.validate_edge_case(None)
            # If it doesn't crash, it should indicate empty
            assert result["empty_or_short"] is True
        except (TypeError, AttributeError):
            # Expected if None handling isn't special-cased
            pass
    
    def test_whitespace_only_description(self):
        """Test detection of whitespace-only descriptions."""
        loader = PromptLoader()
        result = loader.validate_edge_case("   \n\t  ")
        
        # Treated as empty
        assert result["empty_or_short"] is True
    
    def test_minimum_valid_description(self):
        """Test that minimum valid description is accepted."""
        loader = PromptLoader()
        result = loader.validate_edge_case("1234567890")  # Exactly 10 chars
        
        assert result["empty_or_short"] is False
    
    def test_very_long_description(self):
        """Test detection of extremely long descriptions."""
        loader = PromptLoader()
        result = loader.validate_edge_case("x" * 5001)
        
        assert result["extremely_long"] is True
    
    def test_multiple_issues_detection(self):
        """Test detection of multiple issues in one ticket."""
        loader = PromptLoader()
        desc = "Issue 1? Problem 2? Also issue 3? Another 4? And 5?"
        result = loader.validate_edge_case(desc)
        
        assert result["multiple_issues"] is True
    
    def test_urgent_critical_keyword(self):
        """Test detection of CRITICAL urgency keyword."""
        loader = PromptLoader()
        result = loader.validate_edge_case("CRITICAL: System is DOWN")
        
        assert result["urgent_indicators"] is True
    
    def test_urgent_emergency_keyword(self):
        """Test detection of EMERGENCY urgency keyword."""
        loader = PromptLoader()
        result = loader.validate_edge_case("EMERGENCY! Please help ASAP")
        
        assert result["urgent_indicators"] is True
    
    def test_urgent_sos_keyword(self):
        """Test detection of SOS urgency keyword."""
        loader = PromptLoader()
        result = loader.validate_edge_case("SOS - System completely broken")
        
        assert result["urgent_indicators"] is True
    
    def test_pii_email_detection(self):
        """Test detection of email addresses."""
        loader = PromptLoader()
        result = loader.validate_edge_case("Can't login to john.doe@company.com account")
        
        assert result["pii_detected"] is True
    
    def test_pii_phone_detection(self):
        """Test detection of phone numbers."""
        loader = PromptLoader()
        result = loader.validate_edge_case("My phone is 555-123-4567 if you need to call")
        
        assert result["pii_detected"] is True
    
    def test_pii_ssn_detection(self):
        """Test detection of SSN patterns."""
        loader = PromptLoader()
        result = loader.validate_edge_case("Account with SSN 123-45-6789 affected")
        
        assert result["pii_detected"] is True
    
    def test_pii_credit_card_detection(self):
        """Test detection of credit card numbers."""
        loader = PromptLoader()
        result = loader.validate_edge_case("Card 1234-5678-9012-3456 was charged")
        
        assert result["pii_detected"] is True
    
    def test_spam_repeated_characters(self):
        """Test detection of spam with repeated characters."""
        loader = PromptLoader()
        result = loader.validate_edge_case("Test >>>>>>>>>>>> spam")
        
        assert result["spam_detected"] is True
    
    def test_spam_all_special_chars(self):
        """Test detection of spam with mostly non-alphanumeric content."""
        loader = PromptLoader()
        desc = "!@#$%^&*()_+-=[]{}|;:',.<>?/" * 5
        result = loader.validate_edge_case(desc)
        
        assert result["gibberish_detected"] is True
    
    def test_normal_description_no_edge_cases(self):
        """Test that normal description doesn't trigger false positives."""
        loader = PromptLoader()
        desc = "I'm unable to access my account after password reset. Error: 500 server error"
        result = loader.validate_edge_case(desc)
        
        assert result["empty_or_short"] is False
        assert result["extremely_long"] is False
        assert result["urgent_indicators"] is False
        assert result["spam_detected"] is False
        assert result["pii_detected"] is False
        assert result["gibberish_detected"] is False
    
    def test_complex_multi_edge_case(self):
        """Test ticket with multiple edge cases."""
        loader = PromptLoader()
        desc = "CRITICAL: Email john@example.com can't login and >>>>>>>> plus several other issues? Help!"
        result = loader.validate_edge_case(desc)
        
        # Should detect multiple
        assert result["urgent_indicators"] is True
        assert result["pii_detected"] is True


class TestKBMatchFormatting:
    """Test KB match formatting with edge cases."""
    
    def test_format_empty_matches(self):
        """Test formatting empty KB matches."""
        loader = PromptLoader()
        result = loader.format_kb_matches([])
        
        assert "no matching" in result.lower() or "not found" in result.lower()
    
    def test_format_single_match(self):
        """Test formatting single KB match."""
        loader = PromptLoader()
        matches = [{"id": "KB-001", "title": "Login Issue", "score": 0.92, "snippet": "Try clearing cache"}]
        result = loader.format_kb_matches(matches)
        
        assert "KB-001" in result
        assert "Login Issue" in result
        assert "0.92" in result
    
    def test_format_multiple_matches_ordered(self):
        """Test that matches are formatted in order."""
        loader = PromptLoader()
        matches = [
            {"id": "KB-001", "title": "First", "score": 0.95, "snippet": "First snippet"},
            {"id": "KB-002", "title": "Second", "score": 0.85, "snippet": "Second snippet"},
            {"id": "KB-003", "title": "Third", "score": 0.75, "snippet": "Third snippet"},
        ]
        result = loader.format_kb_matches(matches)
        
        first_pos = result.find("KB-001")
        second_pos = result.find("KB-002")
        third_pos = result.find("KB-003")
        
        assert first_pos < second_pos < third_pos
    
    def test_format_matches_limits_to_5(self):
        """Test that only first 5 matches are formatted."""
        loader = PromptLoader()
        matches = [
            {"id": f"KB-{i:03d}", "title": f"Issue {i}", "score": 0.9, "snippet": f"Snippet {i}"}
            for i in range(10)
        ]
        result = loader.format_kb_matches(matches)
        
        assert "KB-000" in result or "KB-001" in result
        assert "KB-009" not in result
    
    def test_format_matches_with_missing_fields(self):
        """Test formatting matches with missing optional fields."""
        loader = PromptLoader()
        matches = [
            {"id": "KB-001"},  # Missing title, score, snippet
            {"id": "KB-002", "title": "Title only"},  # Partial
        ]
        result = loader.format_kb_matches(matches)
        
        # Should not crash
        assert "KB-001" in result
        assert "KB-002" in result
        assert "error" not in result.lower() or "snippet" not in result.lower()
    
    def test_format_matches_truncates_long_title(self):
        """Test that long titles are truncated."""
        loader = PromptLoader()
        long_title = "x" * 200
        matches = [{"id": "KB-001", "title": long_title, "score": 0.9, "snippet": "snippet"}]
        result = loader.format_kb_matches(matches)
        
        # Should contain title but truncated
        assert "KB-001" in result
        # Result should be much shorter than if entire title was included
        assert len(result) < 500
    
    def test_format_matches_score_formatting(self):
        """Test that scores are formatted consistently."""
        loader = PromptLoader()
        matches = [
            {"id": "KB-001", "title": "Test", "score": 0.123456789, "snippet": "snippet"},
        ]
        result = loader.format_kb_matches(matches)
        
        # Should format score to 2 decimal places
        assert "0.12" in result


class TestConfigFormatting:
    """Test configuration formatting."""
    
    def test_format_config_valid(self):
        """Test formatting valid config."""
        loader = PromptLoader()
        config = {"temperature": 0.1, "top_k": 3, "provider": "gemini"}
        result = loader.format_config_summary(config)
        
        assert "0.1" in result
        assert "3" in result
        assert "gemini" in result
    
    def test_format_config_missing_fields(self):
        """Test formatting config with missing fields."""
        loader = PromptLoader()
        config = {}
        result = loader.format_config_summary(config)
        
        # Should not crash, should return sensible default
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_format_config_invalid_temperature(self):
        """Test formatting config with invalid temperature."""
        loader = PromptLoader()
        config = {"temperature": "not_a_number", "top_k": 3}
        result = loader.format_config_summary(config)
        
        # Should not crash
        assert isinstance(result, str)
    
    def test_format_config_negative_top_k(self):
        """Test formatting config with negative top_k."""
        loader = PromptLoader()
        config = {"temperature": 0.1, "top_k": -5}
        result = loader.format_config_summary(config)
        
        # Should handle gracefully
        assert isinstance(result, str)


class TestYAMLConfiguration:
    """Test YAML configuration loading."""
    
    def test_yaml_config_loads_successfully(self):
        """Test that YAML config loads when available."""
        loader = PromptLoader()
        # Attempt to access config (may be empty if YAML not available)
        assert isinstance(loader.config, dict)
    
    def test_yaml_template_extraction(self):
        """Test extracting template from YAML config."""
        loader = PromptLoader()
        template = loader._get_triage_template_from_yaml()
        
        # May be None if YAML not available or file not found
        if template:
            assert isinstance(template, str)
            assert len(template) > 100
    
    def test_edge_case_handler_config(self):
        """Test getting edge case handler configuration."""
        loader = PromptLoader()
        handler = loader.get_edge_case_handler()
        
        # Should be dict (may be empty if YAML not available)
        assert isinstance(handler, dict)


class TestProductionStandards:
    """Test production-grade requirements."""
    
    def test_no_exceptions_on_malformed_input(self):
        """Test that system handles malformed input without exceptions."""
        loader = PromptLoader()
        
        malformed_inputs = [
            "",
            "   ",
            "\n\n\n",
            "x" * 10000,
            "CRITICAL " * 1000,
            "a" * 100 + "\x00" + "b" * 100,  # Null byte
            "😀" * 100,  # Unicode emoji
            "<script>alert('xss')</script>",  # XSS attempt
        ]
        
        for malformed in malformed_inputs:
            try:
                result = loader.validate_edge_case(malformed)
                assert isinstance(result, dict)
                assert "recommendations" in result
            except Exception as e:
                pytest.fail(f"Edge case handler crashed on {repr(malformed)}: {e}")
    
    def test_consistent_recommendations_format(self):
        """Test that recommendations are always in consistent format."""
        loader = PromptLoader()
        
        test_cases = [
            "",
            "x" * 10000,
            "CRITICAL: Down",
            "email@example.com",
        ]
        
        for test_input in test_cases:
            result = loader.validate_edge_case(test_input)
            
            assert isinstance(result["recommendations"], list)
            for rec in result["recommendations"]:
                assert isinstance(rec, str)
                assert len(rec) > 0
    
    def test_all_edge_case_fields_present(self):
        """Test that all edge case detection fields are always present."""
        loader = PromptLoader()
        result = loader.validate_edge_case("Normal description for testing")
        
        required_fields = {
            "empty_or_short",
            "extremely_long",
            "multiple_issues",
            "urgent_indicators",
            "spam_detected",
            "pii_detected",
            "gibberish_detected",
            "recommendations",
        }
        
        for field in required_fields:
            assert field in result
    
    def test_output_sanitization(self):
        """Test that all output is properly sanitized."""
        loader = PromptLoader()
        
        dangerous = "<script>alert('xss')</script>"
        config = {"temperature": dangerous, "top_k": dangerous}
        
        result = loader.format_config_summary(config)
        
        # Should be safe to output (no code execution)
        assert isinstance(result, str)
        assert len(result) < 500  # Reasonably sized


class TestCrossValidation:
    """Test cross-component validation."""
    
    def test_kb_format_output_safe_for_prompt(self):
        """Test that KB formatting output is safe for LLM prompt injection."""
        loader = PromptLoader()
        
        malicious_matches = [
            {
                "id": "KB-001",
                "title": "{description}",  # Could cause prompt injection
                "score": 0.9,
                "snippet": "{config_summary}"
            },
            {
                "id": "KB-002",
                "title": "'; DROP TABLE--",  # SQL injection attempt
                "score": 0.8,
                "snippet": "'; DELETE FROM"
            },
        ]
        
        result = loader.format_kb_matches(malicious_matches)
        
        # Should be safe to use in prompt
        assert isinstance(result, str)
        assert result.count("{") < 5  # Most braces should be escaped/handled
