"""
Request/response schemas for API endpoints.
Uses pydantic v2 with safe fallback to dataclass.
"""

from typing import List, Dict, Any, Optional

try:
    from pydantic import BaseModel, Field, field_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

if PYDANTIC_AVAILABLE:
    class TriageRequest(BaseModel):
        """Triage request schema."""
        description: str = Field(..., min_length=1, max_length=10000)
    
    class KBMatch(BaseModel):
        """KB match in response."""
        id: str
        title: str
        snippet: str
        score: float
        category: Optional[str] = None
    
    class TriageMeta(BaseModel):
        """Metadata in response."""
        provider: Optional[str] = None
        latency_ms: int
        cache_hit: bool
        fallback_mode: Optional[bool] = False
        error: Optional[str] = None
        parse_error: Optional[bool] = False
        cached_at: Optional[str] = None
    
    class TriageResponse(BaseModel):
        """Triage response schema."""
        summary: str
        category: str  # Bug|Billing|Login|Performance|Question|Other
        severity: str  # Low|Medium|High|Critical
        kb_matches: List[KBMatch]
        known_issue: bool
        suggested_action: str
        meta: TriageMeta
    
    class CachePurgeRequest(BaseModel):
        """Cache purge request."""
        key: Optional[str] = None
        token: Optional[str] = None
    
    class CachePurgeResponse(BaseModel):
        """Cache purge response."""
        success: bool
        message: str
        keys_deleted: int = 0

else:
    # Fallback to simple dataclasses
    from dataclasses import dataclass, field
    
    @dataclass
    class TriageRequest:
        description: str
    
    @dataclass
    class KBMatch:
        id: str
        title: str
        snippet: str
        score: float
        category: Optional[str] = None
    
    @dataclass
    class TriageMeta:
        provider: Optional[str] = None
        latency_ms: int = 0
        cache_hit: bool = False
        fallback_mode: Optional[bool] = False
        error: Optional[str] = None
        parse_error: Optional[bool] = False
        cached_at: Optional[str] = None
    
    @dataclass
    class TriageResponse:
        summary: str
        category: str
        severity: str
        kb_matches: List[KBMatch] = field(default_factory=list)
        known_issue: bool = False
        suggested_action: str = ""
        meta: TriageMeta = field(default_factory=TriageMeta)
    
    @dataclass
    class CachePurgeRequest:
        key: Optional[str] = None
        token: Optional[str] = None
    
    @dataclass
    class CachePurgeResponse:
        success: bool
        message: str
        keys_deleted: int = 0


class ErrorResponse:
    """Error response."""
    
    def __init__(self, error: str, details: Optional[str] = None):
        self.error = error
        self.details = details
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.error}
        if self.details:
            result["details"] = self.details
        return result
