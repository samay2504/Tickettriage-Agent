"""
FastAPI application main entry point.
Initializes app, logging, middleware, and routes.
"""

import logging
import json
import sys
from pathlib import Path
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from config.settings import get_settings
from app.routes import triage as triage_routes
from cache.redis_client import close_redis_client

# Configure logging
def setup_logging():
    """Setup structured logging."""
    settings = get_settings()
    
    log_level = getattr(logging, settings.log_level, logging.INFO)
    
    if settings.log_format == "json":
        # JSON logging format
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_obj = {
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "timestamp": self.formatTime(record),
                }
                if record.exc_info:
                    log_obj["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_obj)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
    else:
        # Plain text logging
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
    
    # Set specific loggers
    logging.getLogger("triage").setLevel(log_level)
    logging.getLogger("app").setLevel(log_level)
    logging.getLogger("agent").setLevel(log_level)
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)


# Optional Sentry integration
def setup_sentry():
    """Setup Sentry error tracking if configured."""
    settings = get_settings()
    
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=settings.sentry_dsn)
            logging.getLogger("app").info("Sentry initialized")
        except ImportError:
            logging.getLogger("app").warning("sentry-sdk not installed, skipping Sentry setup")
        except Exception as e:
            logging.getLogger("app").warning(f"Failed to initialize Sentry: {e}")


# Setup logging first
setup_logging()
setup_sentry()

logger = logging.getLogger("app")


if not FASTAPI_AVAILABLE:
    logger.error("FastAPI not installed. Cannot start application.")
    sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup/shutdown."""
    logger.info("Starting Ticket Triage Agent")
    yield
    logger.info("Shutting down Ticket Triage Agent")
    close_redis_client()


# Create FastAPI app
app = FastAPI(
    title="Support Ticket Triage Agent",
    description="Intelligent support ticket classification and routing",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routes
app.include_router(triage_routes.router, prefix="", tags=["triage"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Support Ticket Triage Agent",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "triage": "/triage",
            "cache": "/cache/purge"
        }
    }


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "details": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    settings = get_settings()
    
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_debug,
        )
    except ImportError:
        logger.error("uvicorn not installed. Install with: pip install uvicorn")
        sys.exit(1)
