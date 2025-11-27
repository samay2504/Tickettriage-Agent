"""
Ticket Triage Orchestrator - core orchestration logic.
Orchestrates KB search, LLM classification, and decision making.
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from kb.kb_loader import KBLoader
from kb.search import KBSearch
from cache.redis_client import RedisClient
from agent.llm_client import create_llm_client
from agent.prompt_loader import PromptLoader
from config.settings import Settings

logger = logging.getLogger(__name__)


class TriageResponse:
    """Structured triage response."""
    
    def __init__(
        self,
        summary: str = "",
        category: str = "Other",
        severity: str = "Low",
        kb_matches: List[Dict[str, Any]] = None,
        known_issue: bool = False,
        suggested_action: str = "",
        meta: Dict[str, Any] = None,
    ):
        self.summary = summary
        self.category = category
        self.severity = severity
        self.kb_matches = kb_matches or []
        self.known_issue = known_issue
        self.suggested_action = suggested_action
        self.meta = meta or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "summary": self.summary,
            "category": self.category,
            "severity": self.severity,
            "kb_matches": self.kb_matches,
            "known_issue": self.known_issue,
            "suggested_action": self.suggested_action,
            "meta": self.meta,
        }


class TicketTriageOrchestrator:
    """Main orchestrator for ticket triage with production-grade edge case handling."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.kb_loader = KBLoader(settings.kb_path)
        self.kb_search = KBSearch(self.kb_loader.get_entries(), settings.kb_embedding_model)
        self.redis_client = RedisClient(settings.redis_url, settings.cache_enabled)
        self.llm_client = create_llm_client({
            "temperature": settings.llm_temperature,
            "provider_preference": settings.provider_preference,
        })
        self.prompt_loader = PromptLoader(settings.prompts_dir)
    
    def triage(self, description: str) -> tuple[TriageResponse, Dict[str, Any]]:
        """
        Triage a support ticket with edge case handling.
        
        Args:
            description: Ticket description text
        
        Returns:
            Tuple of (TriageResponse, metadata dict)
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        cache_hit = False
        edge_cases_detected = []
        
        try:
            # Validate description with edge case detection
            if not description or len(description) < self.settings.description_min_length:
                logger.warning(f"[{request_id}] Description too short or empty")
                return (
                    TriageResponse(
                        summary="Invalid request",
                        category="Other",
                        severity="Low",
                        suggested_action="Please provide a detailed description (minimum 10 characters)",
                        meta={
                            "error": "VALIDATION_FAILED",
                            "error_code": "EMPTY_OR_SHORT",
                            "provider": None,
                            "latency_ms": int((time.time() - start_time) * 1000),
                            "cache_hit": False,
                            "edge_cases": ["empty_or_short"],
                        }
                    ),
                    {"request_id": request_id, "error": "EMPTY_OR_SHORT"}
                )
            
            # Detect edge cases early
            edge_case_analysis = self.prompt_loader.validate_edge_case(description)
            for key, value in edge_case_analysis.items():
                if key != "recommendations" and value:
                    edge_cases_detected.append(key)
            
            if edge_cases_detected:
                logger.info(f"[{request_id}] Edge cases detected: {edge_cases_detected}")
            
            # Handle extremely long descriptions
            if len(description) > self.settings.description_max_length:
                logger.warning(f"[{request_id}] Description truncated from {len(description)} chars")
                description = description[:self.settings.description_max_length]
            
            # Try cache first
            cache_key = RedisClient.compute_key(description)
            cached_response = self.redis_client.get(cache_key)
            
            if cached_response:
                cache_hit = True
                logger.info(f"[{request_id}] Cache hit for key {cache_key}")
                
                response_dict = cached_response.get("response", {})
                response = TriageResponse(
                    summary=response_dict.get("summary"),
                    category=response_dict.get("category"),
                    severity=response_dict.get("severity"),
                    kb_matches=response_dict.get("kb_matches", []),
                    known_issue=response_dict.get("known_issue", False),
                    suggested_action=response_dict.get("suggested_action"),
                    meta={
                        "provider": cached_response.get("provider"),
                        "latency_ms": int((time.time() - start_time) * 1000),
                        "cache_hit": True,
                        "cached_at": cached_response.get("created_at"),
                        "edge_cases": edge_cases_detected,
                    }
                )
                return response, {"request_id": request_id, "cache_hit": True}
            
            # KB search
            kb_results = self.kb_search.search(description, self.settings.kb_search_top_k)
            kb_matches = [result.to_dict() for result in kb_results]
            
            # Format for prompt
            kb_matches_str = self.prompt_loader.format_kb_matches(kb_matches)
            config_summary = self.prompt_loader.format_config_summary({
                "temperature": self.settings.llm_temperature,
                "top_k": self.settings.kb_search_top_k,
                "provider": self.llm_client.get_provider_name(),
            })
            
            # Build prompt
            prompt_text = self._build_prompt(description, kb_matches_str, config_summary)
            
            # Call LLM
            llm_response = self.llm_client.invoke(prompt_text)
            provider_name = self.llm_client.get_provider_name()
            is_fallback = self.llm_client.is_fallback_mode()
            
            # Parse response
            response = self._parse_llm_response(llm_response, kb_matches, is_fallback)
            
            # Add metadata
            response.meta = {
                "provider": provider_name,
                "latency_ms": int((time.time() - start_time) * 1000),
                "cache_hit": False,
                "fallback_mode": is_fallback,
            }
            
            # Cache the response
            cache_payload = {
                "response": {
                    "summary": response.summary,
                    "category": response.category,
                    "severity": response.severity,
                    "kb_matches": response.kb_matches,
                    "known_issue": response.known_issue,
                    "suggested_action": response.suggested_action,
                },
                "provider": provider_name,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            self.redis_client.set(cache_key, cache_payload, self.settings.cache_ttl_seconds)
            
            logger.info(
                f"[{request_id}] Triage completed - "
                f"category={response.category}, severity={response.severity}, "
                f"provider={provider_name}, latency={response.meta['latency_ms']}ms"
            )
            
            return response, {"request_id": request_id, "cache_hit": False}
        
        except Exception as e:
            logger.exception(f"[{request_id}] Triage failed: {e}")
            return (
                TriageResponse(
                    summary="Error processing ticket",
                    category="Other",
                    severity="High",
                    meta={
                        "error": "PROCESSING_FAILED",
                        "provider": None,
                        "latency_ms": int((time.time() - start_time) * 1000),
                        "cache_hit": False,
                    }
                ),
                {"request_id": request_id, "error": str(e)}
            )
    
    def _build_prompt(self, description: str, kb_matches: str, config_summary: str) -> str:
        """Build prompt for LLM."""
        prompt_loader = PromptLoader(self.settings.prompts_dir)
        template_text = prompt_loader.load_prompt("triage_prompt.txt")
        
        if not template_text:
            template_text = prompt_loader._get_default_triage_template()
        
        # Simple string formatting
        prompt = template_text.format(
            description=description,
            kb_matches=kb_matches,
            config_summary=config_summary
        )
        
        return prompt
    
    def _parse_llm_response(
        self,
        llm_response: Optional[str],
        kb_matches: List[Dict[str, Any]],
        is_fallback: bool
    ) -> TriageResponse:
        """Parse LLM response into structured format."""
        
        if not llm_response:
            logger.warning("LLM returned None, using fallback response")
            return self._create_fallback_response(kb_matches, is_fallback)
        
        try:
            # Try to extract JSON from response
            # Remove markdown code blocks if present
            json_text = llm_response
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]
            
            parsed = json.loads(json_text.strip())
            
            # Validate and normalize fields
            response = TriageResponse(
                summary=parsed.get("summary", ""),
                category=self._normalize_category(parsed.get("category", "Other")),
                severity=self._normalize_severity(parsed.get("severity", "Low")),
                kb_matches=kb_matches,
                known_issue=parsed.get("known_issue", False),
                suggested_action=parsed.get("suggested_action", ""),
            )
            
            # Extract KB IDs if mentioned
            kb_ids = parsed.get("kb_ids", [])
            if kb_ids and isinstance(kb_ids, str):
                kb_ids = [bid.strip() for bid in kb_ids.split(",")]
            
            # Filter KB matches to only those mentioned
            if kb_ids:
                response.kb_matches = [
                    m for m in kb_matches
                    if any(bid in m.get("id", "") for bid in kb_ids)
                ]
            
            return response
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}. Raw response: {llm_response[:200]}")
            return self._create_fallback_response(kb_matches, is_fallback)
        
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return self._create_fallback_response(kb_matches, is_fallback)
    
    def _create_fallback_response(
        self,
        kb_matches: List[Dict[str, Any]],
        is_fallback: bool
    ) -> TriageResponse:
        """Create a fallback response when LLM parsing fails."""
        category = "Bug" if kb_matches else "Other"
        severity = "Medium"
        known_issue = len(kb_matches) > 0
        
        response = TriageResponse(
            summary="Ticket submitted for review",
            category=category,
            severity=severity,
            kb_matches=kb_matches[:1] if kb_matches else [],
            known_issue=known_issue,
            suggested_action="Escalate to support team for manual review",
        )
        
        if is_fallback:
            response.meta["parse_error"] = True
            response.meta["fallback_response"] = True
        
        return response
    
    @staticmethod
    def _normalize_category(category: str) -> str:
        """Normalize category to valid values."""
        valid_categories = ["Bug", "Billing", "Login", "Performance", "Question", "Other"]
        normalized = category.strip().title()
        
        for valid_cat in valid_categories:
            if valid_cat.lower() in normalized.lower():
                return valid_cat
        
        return "Other"
    
    @staticmethod
    def _normalize_severity(severity: str) -> str:
        """Normalize severity to valid values."""
        valid_severities = ["Low", "Medium", "High", "Critical"]
        normalized = severity.strip().title()
        
        for valid_sev in valid_severities:
            if valid_sev.lower() in normalized.lower():
                return valid_sev
        
        return "Low"
    
    def purge_cache(self, key: Optional[str] = None) -> bool:
        """Purge cache."""
        if key:
            return self.redis_client.delete(key)
        else:
            return self.redis_client.delete_pattern("triage:*")


def create_orchestrator(settings: Settings) -> TicketTriageOrchestrator:
    """Factory function to create orchestrator."""
    return TicketTriageOrchestrator(settings)
