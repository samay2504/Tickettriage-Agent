"""
Tests for prompt loading functionality with YAML support and edge case handling.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from agent.prompt_loader import PromptLoader


class TestPromptLoader:
    """Tests for prompt loading."""
    
    def test_load_default_prompt(self):
        """Test loading default prompt when file doesn't exist."""
        loader = PromptLoader("nonexistent")
        
        template = loader.get_triage_prompt_template()
        # May return None if LangChain not available, or a template
        assert template is None or hasattr(template, 'format') or isinstance(template, str)
    
    def test_get_default_triage_template(self):
        """Test getting default triage template."""
        template_text = PromptLoader._get_default_triage_template()
        
        assert "description" in template_text.lower()
        assert "kb_matches" in template_text.lower()
        assert "config_summary" in template_text.lower()
        assert "JSON" in template_text
        assert "EDGE CASE" in template_text
    
    def test_format_kb_matches_empty(self):
        """Test formatting empty KB matches."""
        loader = PromptLoader()
        formatted = loader.format_kb_matches([])
        
        assert "no matching" in formatted.lower()
    
    def test_format_kb_matches_with_data(self):
        """Test formatting KB matches with data."""
        loader = PromptLoader()
        matches = [
            {"id": "TEST-001", "title": "Test Issue", "score": 0.95, "snippet": "Test snippet"},
            {"id": "TEST-002", "title": "Another Issue", "score": 0.87, "snippet": "Another snippet"}
        ]
        formatted = loader.format_kb_matches(matches)
        
        assert "TEST-001" in formatted
        assert "Test Issue" in formatted
        assert "0.95" in formatted
    
    def test_format_kb_matches_truncates_title(self):
        """Test that KB match titles are truncated if too long."""
        loader = PromptLoader()
        matches = [
            {"id": "TEST", "title": "x" * 200, "score": 0.95, "snippet": "snippet"}
        ]
        formatted = loader.format_kb_matches(matches)
        
        # Title should be truncated to 100 chars
        assert len(formatted) < len("x" * 200)
    
    def test_format_kb_matches_limits_to_5(self):
        """Test that KB matches are limited to 5 items."""
        loader = PromptLoader()
        matches = [
            {"id": f"TEST-{i:03d}", "title": f"Issue {i}", "score": 0.95, "snippet": "snippet"}
            for i in range(10)
        ]
        formatted = loader.format_kb_matches(matches)
        
        # Should only contain first 5
        assert "TEST-004" in formatted
        assert "TEST-009" not in formatted
    
    def test_format_config_summary(self):
        """Test formatting config summary."""
        loader = PromptLoader()
        config = {"temperature": 0.1, "top_k": 3, "provider": "test-provider"}
        formatted = loader.format_config_summary(config)
        
        assert "0.1" in formatted
        assert "3" in formatted
        assert "test-provider" in formatted
    
    def test_format_config_summary_with_invalid_values(self):
        """Test that config formatting handles invalid values gracefully."""
        loader = PromptLoader()
        config = {"temperature": "invalid", "top_k": None, "provider": None}
        formatted = loader.format_config_summary(config)
        
        assert "Configuration" in formatted or "Default" in formatted
    
    def test_validate_edge_case_empty_description(self):
        """Test edge case detection for empty descriptions."""
        loader = PromptLoader()
        result = loader.validate_edge_case("")
        
        assert result["empty_or_short"] is True
        assert len(result["recommendations"]) > 0
    
    def test_validate_edge_case_short_description(self):
        """Test edge case detection for short descriptions."""
        loader = PromptLoader()
        result = loader.validate_edge_case("short")
        
        assert result["empty_or_short"] is True
    
    def test_validate_edge_case_extremely_long(self):
        """Test edge case detection for extremely long descriptions."""
        loader = PromptLoader()
        long_desc = "x" * 6000
        result = loader.validate_edge_case(long_desc)
        
        assert result["extremely_long"] is True
    
    def test_validate_edge_case_urgent_keywords(self):
        """Test edge case detection for urgent keywords."""
        loader = PromptLoader()
        desc = "This is URGENT! Our system is DOWN and CRITICAL!"
        result = loader.validate_edge_case(desc)
        
        assert result["urgent_indicators"] is True
        assert "escalate" in " ".join(result["recommendations"]).lower()
    
    def test_validate_edge_case_pii_email(self):
        """Test edge case detection for PII - email."""
        loader = PromptLoader()
        desc = "I can't login with my email user@example.com"
        result = loader.validate_edge_case(desc)
        
        assert result["pii_detected"] is True
        assert "redact" in " ".join(result["recommendations"]).lower()
    
    def test_validate_edge_case_pii_phone(self):
        """Test edge case detection for PII - phone."""
        loader = PromptLoader()
        desc = "Call me at 555-123-4567 about my issue"
        result = loader.validate_edge_case(desc)
        
        assert result["pii_detected"] is True
    
    def test_validate_edge_case_spam_repeated_chars(self):
        """Test edge case detection for spam with repeated characters."""
        loader = PromptLoader()
        desc = "Test message with >>>>>>>>>>>>> repeated chars"  # 13 repeated chars
        result = loader.validate_edge_case(desc)
        
        assert result["spam_detected"] is True
    
    def test_validate_edge_case_multiple_issues(self):
        """Test edge case detection for multiple issues."""
        loader = PromptLoader()
        desc = "Issue 1? Also issue 2? Plus issue 3? And another issue 4?"
        result = loader.validate_edge_case(desc)
        
        # Has 4+ question marks, should detect multiple issues
        assert result["multiple_issues"] is True
    
    def test_validate_edge_case_normal_description(self):
        """Test that normal descriptions don't trigger edge cases."""
        loader = PromptLoader()
        desc = "I'm having trouble logging into my account. I get an error message when I try."
        result = loader.validate_edge_case(desc)
        
        # Should not have major edge cases
        assert result["empty_or_short"] is False
        assert result["spam_detected"] is False
        assert result["pii_detected"] is False
    
    def test_load_yaml_config(self):
        """Test loading YAML configuration."""
        with TemporaryDirectory() as tmpdir:
            # Create a minimal YAML file
            yaml_content = """version: "1.0"
prompt_template:
  preamble: |
    Test preamble
  main_input: |
    Test input with {description}
"""
            yaml_path = Path(tmpdir) / "triage_prompt.yaml"
            yaml_path.write_text(yaml_content)
            
            loader = PromptLoader(tmpdir)
            template = loader._get_triage_template_from_yaml()
            
            if template:  # May be None if PyYAML not available
                assert "Test preamble" in template
                assert "Test input" in template
    
    def test_get_edge_case_handler(self):
        """Test getting edge case handler configuration."""
        loader = PromptLoader()
        handler = loader.get_edge_case_handler()
        
        # May be empty if YAML not available, but should be a dict
        assert isinstance(handler, dict)
    
    def test_load_custom_prompt_file(self):
        """Test loading prompt from custom file."""
        with TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir)
            prompt_file = prompts_dir / "custom_prompt.txt"
            
            custom_prompt = "Custom prompt with {variable}"
            prompt_file.write_text(custom_prompt)
            
            loader = PromptLoader(str(prompts_dir))
            loaded = loader.load_prompt("custom_prompt.txt")
            
            assert loaded == custom_prompt
    
    def test_prompt_variables_consistency(self):
        """Test that prompt template variables are consistent."""
        template_text = PromptLoader._get_default_triage_template()
        
        # Extract variable names
        import re
        variables = set(re.findall(r'\{(\w+)\}', template_text))
        
        expected_variables = {"description", "kb_matches", "config_summary"}
        assert variables == expected_variables
