"""
Configuration module with pydantic-safe BaseSettings.
Loads from .env file and config.yaml with safe fallback to dataclasses.
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

# Try pydantic v2 first
try:
    from pydantic_settings import BaseSettings as PydanticSettings
    from pydantic import Field, ConfigDict
    PYDANTIC_AVAILABLE = True
except ImportError:
    try:
        from pydantic import BaseSettings as PydanticSettings
        from pydantic import Field
        PYDANTIC_AVAILABLE = True
    except ImportError:
        PYDANTIC_AVAILABLE = False

# Try yaml support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Fallback to dataclass
if not PYDANTIC_AVAILABLE:
    from dataclasses import dataclass, field
    
    @dataclass
    class Settings:
        """Settings dataclass (pydantic fallback)."""
        # FastAPI
        api_host: str = "0.0.0.0"
        api_port: int = 8000
        api_debug: bool = False
        
        # LLM Configuration
        llm_temperature: float = 0.1
        llm_max_tokens: int = 1024
        llm_timeout_seconds: int = 30
        llm_max_retries: int = 3
        llm_retry_backoff_factor: float = 2.0
        provider_preference: List[str] = field(
            default_factory=lambda: ["google_genai", "groq", "huggingface", "openai", "fallback"]
        )
        
        # API Keys (all optional)
        openai_api_key: Optional[str] = None
        google_api_key: Optional[str] = None
        groq_api_key: Optional[str] = None
        huggingface_api_key: Optional[str] = None
        
        # Redis
        redis_url: str = "redis://localhost:6379/0"
        cache_ttl_seconds: int = 3600
        cache_enabled: bool = True
        
        # KB & Search
        kb_path: str = "kb/sample_kb.json"
        kb_search_top_k: int = 3
        kb_embedding_model: Optional[str] = None
        
        # Prompts
        prompts_dir: str = "prompts"
        triage_prompt_file: str = "prompts/triage_prompt.txt"
        
        # Security
        admin_token: Optional[str] = None
        rate_limit_enabled: bool = True
        rate_limit_requests_per_minute: int = 60
        
        # Logging
        log_level: str = "INFO"
        log_format: str = "json"  # json or plain
        sentry_dsn: Optional[str] = None
        
        # Validation
        description_min_length: int = 1
        description_max_length: int = 10000
        
        @classmethod
        def from_env(cls) -> "Settings":
            """Load settings from environment variables."""
            return cls(
                api_host=os.getenv("API_HOST", "0.0.0.0"),
                api_port=int(os.getenv("API_PORT", "8000")),
                api_debug=os.getenv("API_DEBUG", "false").lower() == "true",
                llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
                llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
                llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
                llm_max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
                llm_retry_backoff_factor=float(os.getenv("LLM_RETRY_BACKOFF_FACTOR", "2.0")),
                provider_preference=os.getenv("PROVIDER_PREFERENCE", "google_genai,groq,huggingface,openai,fallback").split(","),
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                groq_api_key=os.getenv("GROQ_API_KEY"),
                huggingface_api_key=os.getenv("HUGGINGFACE_API_KEY"),
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
                cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
                kb_path=os.getenv("KB_PATH", "kb/sample_kb.json"),
                kb_search_top_k=int(os.getenv("KB_SEARCH_TOP_K", "3")),
                kb_embedding_model=os.getenv("KB_EMBEDDING_MODEL"),
                prompts_dir=os.getenv("PROMPTS_DIR", "prompts"),
                triage_prompt_file=os.getenv("TRIAGE_PROMPT_FILE", "prompts/triage_prompt.txt"),
                admin_token=os.getenv("ADMIN_TOKEN"),
                rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
                rate_limit_requests_per_minute=int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60")),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                log_format=os.getenv("LOG_FORMAT", "json"),
                sentry_dsn=os.getenv("SENTRY_DSN"),
                description_min_length=int(os.getenv("DESCRIPTION_MIN_LENGTH", "1")),
                description_max_length=int(os.getenv("DESCRIPTION_MAX_LENGTH", "10000")),
            )

else:
    # Use pydantic BaseSettings
    class Settings(PydanticSettings):
        """Settings using Pydantic BaseSettings."""
        # FastAPI
        api_host: str = "0.0.0.0"
        api_port: int = 8000
        api_debug: bool = False
        
        # LLM Configuration
        llm_temperature: float = 0.1
        llm_max_tokens: int = 1024
        llm_timeout_seconds: int = 30
        llm_max_retries: int = 3
        llm_retry_backoff_factor: float = 2.0
        provider_preference: List[str] = [
            "google_genai", "groq", "huggingface", "openai", "fallback"
        ]
        
        # API Keys (all optional)
        openai_api_key: Optional[str] = None
        google_api_key: Optional[str] = None
        groq_api_key: Optional[str] = None
        huggingface_api_key: Optional[str] = None
        
        # Redis
        redis_url: str = "redis://localhost:6379/0"
        cache_ttl_seconds: int = 3600
        cache_enabled: bool = True
        
        # KB & Search
        kb_path: str = "kb/sample_kb.json"
        kb_search_top_k: int = 3
        kb_embedding_model: Optional[str] = None
        
        # Prompts
        prompts_dir: str = "prompts"
        triage_prompt_file: str = "prompts/triage_prompt.txt"
        
        # Security
        admin_token: Optional[str] = None
        rate_limit_enabled: bool = True
        rate_limit_requests_per_minute: int = 60
        
        # Logging
        log_level: str = "INFO"
        log_format: str = "json"  # json or plain
        sentry_dsn: Optional[str] = None
        
        # Validation
        description_min_length: int = 1
        description_max_length: int = 10000
        
        if PYDANTIC_AVAILABLE:
            model_config = ConfigDict(env_file=".env", extra="ignore")


# Global settings singleton
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        if PYDANTIC_AVAILABLE:
            _settings = Settings()
        else:
            _settings = Settings.from_env()
    return _settings


def reload_settings() -> Settings:
    """Force reload of settings."""
    global _settings
    if PYDANTIC_AVAILABLE:
        _settings = Settings()
    else:
        _settings = Settings.from_env()
    return _settings
