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
        
        # Security & Rate Limiting
        admin_token: Optional[str] = None
        rate_limit_enabled: bool = True
        rate_limit_requests: int = 60
        rate_limit_period_seconds: int = 60
        rate_limit_storage: str = "redis"
        rate_limit_bypass_keys: str = ""
        
        # LLM Retry Configuration
        llm_retry_enabled: bool = True
        llm_retry_initial_delay_sec: float = 0.5
        llm_retry_max_delay_sec: float = 8.0
        llm_retry_backoff_multiplier: float = 2.0
        
        # Frontend
        frontend_enabled: bool = True
        frontend_port: Optional[int] = None
        
        # Logging
        log_level: str = "INFO"
        log_format: str = "json"
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
                rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "60")),
                rate_limit_period_seconds=int(os.getenv("RATE_LIMIT_PERIOD_SECONDS", "60")),
                rate_limit_storage=os.getenv("RATE_LIMIT_STORAGE", "redis"),
                rate_limit_bypass_keys=os.getenv("RATE_LIMIT_BYPASS_KEYS", ""),
                llm_retry_enabled=os.getenv("LLM_RETRY_ENABLED", "true").lower() == "true",
                llm_retry_initial_delay_sec=float(os.getenv("LLM_RETRY_INITIAL_DELAY_SEC", "0.5")),
                llm_retry_max_delay_sec=float(os.getenv("LLM_RETRY_MAX_DELAY_SEC", "8.0")),
                llm_retry_backoff_multiplier=float(os.getenv("LLM_RETRY_BACKOFF_MULTIPLIER", "2.0")),
                frontend_enabled=os.getenv("FRONTEND_ENABLED", "true").lower() == "true",
                frontend_port=int(os.getenv("FRONTEND_PORT")) if os.getenv("FRONTEND_PORT") else None,
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                log_format=os.getenv("LOG_FORMAT", "json"),
                sentry_dsn=os.getenv("SENTRY_DSN"),
                description_min_length=int(os.getenv("DESCRIPTION_MIN_LENGTH", "1")),
                description_max_length=int(os.getenv("DESCRIPTION_MAX_LENGTH", "10000")),
            )

else:
    # Use pydantic BaseSettings
    from pydantic import field_validator
    
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
        provider_preference: str = "google_genai,groq,huggingface,openai,fallback"
        
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
        
        # Security & Rate Limiting
        admin_token: Optional[str] = None
        rate_limit_enabled: bool = True
        rate_limit_requests: int = 60
        rate_limit_period_seconds: int = 60
        rate_limit_storage: str = "redis"
        rate_limit_bypass_keys: str = ""
        
        # LLM Retry Configuration
        llm_retry_enabled: bool = True
        llm_retry_initial_delay_sec: float = 0.5
        llm_retry_max_delay_sec: float = 8.0
        llm_retry_backoff_multiplier: float = 2.0
        
        # Frontend
        frontend_enabled: bool = True
        frontend_port: Optional[int] = None
        
        # Logging
        log_level: str = "INFO"
        log_format: str = "json"
        sentry_dsn: Optional[str] = None
        
        # Validation
        description_min_length: int = 1
        description_max_length: int = 10000
        
        if PYDANTIC_AVAILABLE:
            model_config = ConfigDict(env_file=".env", extra="ignore")
        
        def get_provider_preference_list(self) -> List[str]:
            """Get provider preference as a list."""
            if isinstance(self.provider_preference, list):
                return self.provider_preference
            return [p.strip() for p in self.provider_preference.split(",")]


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
