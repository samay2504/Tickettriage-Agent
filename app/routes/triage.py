"""
API routes for ticket triage.
Implements POST /triage, GET /health, POST /cache/purge endpoints.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request
from app.schemas import TriageRequest, TriageResponse, CachePurgeResponse, KBMatch, TriageMeta
from agent.orchestrator import create_orchestrator
from config.settings import get_settings
from cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

router = APIRouter()

# Global orchestrator instance
_orchestrator = None


def get_orchestrator():
    """Get or create orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        settings = get_settings()
        _orchestrator = create_orchestrator(settings)
    return _orchestrator


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    settings = get_settings()
    orchestrator = get_orchestrator()
    
    redis_status = "connected" if orchestrator.redis_client.is_available() else "disconnected"
    llm_info = orchestrator.llm_client.get_provider_info()
    
    return {
        "status": "healthy",
        "redis": redis_status,
        "llm_provider": llm_info.get("provider", "unknown"),
        "llm_available": llm_info.get("available", False),
    }


@router.post("/triage")
async def triage(request: TriageRequest, req: Request) -> TriageResponse:
    """
    Triage a support ticket.
    
    Request:
        description: str (1-10000 characters)
    
    Response:
        summary: str
        category: Bug|Billing|Login|Performance|Question|Other
        severity: Low|Medium|High|Critical
        kb_matches: [{id, title, snippet, score}]
        known_issue: bool
        suggested_action: str
        meta: {provider, latency_ms, cache_hit}
    """
    settings = get_settings()
    orchestrator = get_orchestrator()
    
    # Validate input
    if not request.description or len(request.description) < settings.description_min_length:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "VALIDATION_FAILED",
                "details": f"Description must be at least {settings.description_min_length} characters"
            }
        )
    
    if len(request.description) > settings.description_max_length:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "VALIDATION_FAILED",
                "details": f"Description must be at most {settings.description_max_length} characters"
            }
        )
    
    try:
        # Run triage
        triage_response, meta_info = orchestrator.triage(request.description)
        
        # Convert to API response format
        kb_matches_list = [
            KBMatch(
                id=m["id"],
                title=m["title"],
                snippet=m["snippet"],
                score=m["score"],
                category=m.get("category")
            )
            for m in triage_response.kb_matches
        ]
        
        api_response = TriageResponse(
            summary=triage_response.summary,
            category=triage_response.category,
            severity=triage_response.severity,
            kb_matches=kb_matches_list,
            known_issue=triage_response.known_issue,
            suggested_action=triage_response.suggested_action,
            meta=TriageMeta(**triage_response.meta)
        )
        
        logger.info(f"Triage processed: {meta_info.get('request_id')}")
        return api_response
    
    except Exception as e:
        logger.exception(f"Triage endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "details": "An error occurred while processing the ticket"
            }
        )


@router.post("/cache/purge")
async def purge_cache(request: CachePurgeResponse = None) -> CachePurgeResponse:
    """
    Purge cache entries (admin only).
    
    Request:
        key: Optional[str] - specific cache key to delete
        token: Optional[str] - admin token
    
    Response:
        success: bool
        message: str
        keys_deleted: int
    """
    settings = get_settings()
    orchestrator = get_orchestrator()
    
    # Validate admin token
    if settings.admin_token:
        if not request or not request.token or request.token != settings.admin_token:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "UNAUTHORIZED",
                    "details": "Invalid or missing admin token"
                }
            )
    
    try:
        if request and request.key:
            # Delete specific key
            success = orchestrator.redis_client.delete(request.key)
            return CachePurgeResponse(
                success=success,
                message=f"Deleted cache key: {request.key}",
                keys_deleted=1 if success else 0
            )
        else:
            # Purge all triage cache
            keys_deleted = orchestrator.redis_client.delete_pattern("triage:*")
            return CachePurgeResponse(
                success=True,
                message=f"Purged {keys_deleted} cache entries",
                keys_deleted=keys_deleted
            )
    
    except Exception as e:
        logger.exception(f"Cache purge error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "details": "An error occurred while purging cache"
            }
        )
