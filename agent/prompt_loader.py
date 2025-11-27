"""
Prompt template loader for triage prompt from disk.
Loads templates from prompts/ directory (YAML or text format) and creates LangChain PromptTemplate.
Supports YAML with edge case handlers and production-grade validation.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class PromptLoader:
    """Load and manage prompt templates with edge case handling."""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.prompts: Dict[str, str] = {}
        self.config: Dict[str, Any] = {}
        self._load_yaml_config()
    
    def _load_yaml_config(self) -> None:
        """Load YAML configuration if available."""
        if not YAML_AVAILABLE:
            logger.warning("PyYAML not available, using text templates only")
            return
        
        yaml_path = self.prompts_dir / "triage_prompt.yaml"
        if not yaml_path.exists():
            logger.warning(f"YAML config not found: {yaml_path}")
            return
        
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
            logger.info(f"Loaded YAML configuration from {yaml_path}")
        except Exception as e:
            logger.error(f"Failed to load YAML config: {e}")
            self.config = {}
    
    def load_prompt(self, filename: str) -> Optional[str]:
        """Load a prompt template from file."""
        filepath = self.prompts_dir / filename
        
        if not filepath.exists():
            logger.error(f"Prompt file not found: {filepath}")
            return None
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.prompts[filename] = content
            logger.info(f"Loaded prompt template: {filename}")
            return content
        except Exception as e:
            logger.error(f"Failed to load prompt {filename}: {e}")
            return None
    
    def get_triage_prompt_template(self):
        """Load triage prompt and create LangChain PromptTemplate."""
        try:
            from langchain_core.prompts import PromptTemplate
            has_langchain = True
        except ImportError:
            logger.warning("LangChain not available, using string-based templates")
            has_langchain = False
        
        # Try loading from YAML file first
        template_text = self._get_triage_template_from_yaml()
        
        if not template_text:
            # Fallback to text file
            template_text = self.load_prompt("triage_prompt.txt")
        
        if not template_text:
            # Use default fallback
            template_text = self._get_default_triage_template()
            logger.info("Using default triage template")
        
        if not has_langchain:
            return template_text
        
        # Create PromptTemplate with expected variables
        try:
            prompt_template = PromptTemplate(
                input_variables=["description", "kb_matches", "config_summary"],
                template=template_text
            )
            return prompt_template
        except Exception as e:
            logger.error(f"Failed to create PromptTemplate: {e}")
            return template_text  # Return raw template as fallback
    
    @staticmethod
    def _get_default_triage_template() -> str:
        """Get default triage prompt template."""
        return """You are a Support Triage assistant for a customer support team.
Your role is to classify and route customer support tickets efficiently and accurately.

CRITICAL INSTRUCTIONS:
1. Output ONLY valid JSON. Do not include markdown, code blocks, or explanations.
2. Handle edge cases gracefully.
3. If uncertain about classification, use "Other" category and "Medium" severity.
4. Always provide actionable suggested_action for support team.
5. Reference KB articles only if confidence > 0.3.

INPUT ANALYSIS:

Customer Description:
{description}

Matching Knowledge Base Articles (top results):
{kb_matches}

System Configuration:
{config_summary}

CLASSIFICATION GUIDELINES:

Category Selection:
- Bug: System malfunction, error, crash, or failure
- Billing: Payment, subscription, invoice, or refund issues
- Login: Authentication, access, or credential problems
- Performance: Speed, latency, timeout, or responsiveness issues
- Question: Inquiry, how-to, or information request
- Other: Miscellaneous or unclear issues

Severity Determination:
- Critical: System down, urgent, blocking production, multiple users affected
- High: Significant feature broken, major functionality impaired, business impact
- Medium: Feature partially working, workaround available, single user affected
- Low: Minor issue, cosmetic, question, no functional impact

EDGE CASE HANDLING:

Empty/Short Description: Reject if < 10 characters, set category="Other", severity="Low"
Multiple Issues: Detect if 3+ different issues, suggest splitting, boost severity to "Medium"
Urgent Keywords: Override severity to "Critical"
Extremely Long: Summarize to key points
PII Detected: Flag for review
Spam/Gibberish: Route to spam detection
Language Mismatch: Route to multilingual team

FALLBACK STRATEGY:
- Unable to determine category → Use "Other"
- Unable to determine severity → Use "Medium"
- No KB matches → Use empty kb_ids array
- Return valid JSON structure always

OUTPUT REQUIREMENTS (ONLY valid JSON):

{
  "summary": "<1-2 sentence summary of ticket>",
  "category": "<one of: Bug, Billing, Login, Performance, Question, Other>",
  "severity": "<one of: Low, Medium, High, Critical>",
  "known_issue": <true or false>,
  "kb_ids": ["<id1>", "<id2>"],
  "suggested_action": "<clear next action for support team>"
}

Validation:
- summary: 10-200 characters, no empty strings
- category: Must match enum exactly
- severity: Must match enum exactly
- known_issue: true or false only
- kb_ids: Array of strings (can be empty)
- suggested_action: 10-300 characters, actionable
"""
    
    def _get_triage_template_from_yaml(self) -> Optional[str]:
        """Extract triage template from loaded YAML config."""
        if not self.config or not YAML_AVAILABLE:
            return None
        
        try:
            prompt_template = self.config.get("prompt_template", {})
            if not prompt_template:
                return None
            
            # Build complete template from YAML sections
            sections = []
            
            if "preamble" in prompt_template:
                sections.append(prompt_template["preamble"])
            
            if "main_input" in prompt_template:
                sections.append(prompt_template["main_input"])
            
            if "classification_guidelines" in prompt_template:
                sections.append(prompt_template["classification_guidelines"])
            
            if "edge_case_guidelines" in prompt_template:
                sections.append(prompt_template["edge_case_guidelines"])
            
            if "fallback_strategy" in prompt_template:
                sections.append(prompt_template["fallback_strategy"])
            
            if "output_format" in prompt_template:
                sections.append(prompt_template["output_format"])
            
            if not sections:
                return None
            
            complete_template = "\n\n".join(sections)
            logger.info("Successfully built template from YAML configuration")
            return complete_template
        
        except Exception as e:
            logger.error(f"Failed to extract template from YAML: {e}")
            return None
    
    def format_kb_matches(self, matches: list) -> str:
        """Format KB matches for prompt with edge case handling."""
        if not matches:
            return "No matching KB articles found."
        
        formatted = []
        try:
            for i, match in enumerate(matches[:5], 1):  # Limit to 5 items
                match_id = match.get("id", "unknown")
                title = match.get("title", "Unknown")
                score = match.get("score", 0)
                snippet = match.get("snippet", "")
                
                # Sanitize values
                title = title.strip()[:100] if title else "Unknown"
                snippet = snippet.strip()[:150] if snippet else ""
                
                formatted.append(
                    f"[{i}] ({match_id}) {title} - Score: {score:.2f}\n"
                    f"    Snippet: {snippet}"
                )
        except Exception as e:
            logger.error(f"Error formatting KB matches: {e}")
            return "Error formatting KB articles."
        
        return "\n".join(formatted) if formatted else "No valid KB articles."
    
    def format_config_summary(self, config: Dict[str, Any]) -> str:
        """Format config for prompt with validation."""
        try:
            temperature = config.get("temperature", 0.1)
            top_k = config.get("top_k", 3)
            provider = config.get("provider", "unknown")
            
            # Validate values
            temperature = float(temperature) if temperature else 0.1
            top_k = int(top_k) if top_k else 3
            
            summary = (
                f"LLM Provider: {provider} | "
                f"Temperature: {temperature:.1f} | "
                f"Top-K: {top_k}"
            )
            return summary
        except Exception as e:
            logger.error(f"Error formatting config: {e}")
            return "Configuration: Default settings"
    
    def validate_edge_case(self, description: str) -> Dict[str, Any]:
        """Validate and detect edge cases in input description."""
        edge_cases = {
            "empty_or_short": False,
            "extremely_long": False,
            "multiple_issues": False,
            "urgent_indicators": False,
            "spam_detected": False,
            "pii_detected": False,
            "gibberish_detected": False,
            "recommendations": []
        }
        
        try:
            if not description:
                edge_cases["empty_or_short"] = True
                edge_cases["recommendations"].append("Request more detailed description")
                return edge_cases
            
            desc_len = len(description)
            
            # Check for empty or short
            if desc_len < 10:
                edge_cases["empty_or_short"] = True
                edge_cases["recommendations"].append("Description too short, request details")
            
            # Check for extremely long
            if desc_len > 5000:
                edge_cases["extremely_long"] = True
                edge_cases["recommendations"].append("Summarize to key points")
            
            # Check for multiple issues
            issue_keywords = ["also", "plus", "another", "also have", "and another", "additional"]
            if description.lower().count("?") > 3 or description.lower().count("!") > 5:
                edge_cases["multiple_issues"] = True
                edge_cases["recommendations"].append("Consider splitting into separate tickets")
            
            # Check for urgent indicators
            urgent_keywords = ["URGENT", "CRITICAL", "DOWN", "EMERGENCY", "SOS", "ASAP"]
            if any(keyword in description.upper() for keyword in urgent_keywords):
                edge_cases["urgent_indicators"] = True
                edge_cases["recommendations"].append("Escalate immediately")
            
            # Check for PII
            pii_patterns = {
                "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
                "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
                "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"
            }
            
            for pii_type, pattern in pii_patterns.items():
                if re.search(pattern, description):
                    edge_cases["pii_detected"] = True
                    edge_cases["recommendations"].append(f"Review and redact {pii_type}")
                    break
            
            # Check for spam/gibberish
            repeated_chars = re.findall(r"(.)\1{10,}", description)
            if repeated_chars:
                edge_cases["spam_detected"] = True
                edge_cases["recommendations"].append("Route to spam detection")
            
            # Check for gibberish (high entropy, mostly non-alphanumeric)
            alpha_numeric = sum(1 for c in description if c.isalnum() or c.isspace())
            alpha_ratio = alpha_numeric / len(description) if description else 0
            if alpha_ratio < 0.3:
                edge_cases["gibberish_detected"] = True
                edge_cases["recommendations"].append("Request resubmission with clear description")
            
        except Exception as e:
            logger.error(f"Error validating edge cases: {e}")
        
        return edge_cases
    
    def get_edge_case_handler(self) -> Dict[str, Any]:
        """Get edge case configuration from YAML."""
        if self.config and "edge_cases" in self.config:
            return self.config["edge_cases"]
        return {}
