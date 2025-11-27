"""
Routes for serving the UI.
"""

import logging
from pathlib import Path

try:
    from fastapi import APIRouter
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def is_frontend_enabled() -> bool:
    """Check if frontend is enabled."""
    settings = get_settings()
    return getattr(settings, "frontend_enabled", True)


@router.get("/ui")
async def serve_ui() -> HTMLResponse:
    """
    Serve the main UI page.
    
    Returns:
        HTML response with the triage UI
    """
    if not is_frontend_enabled():
        return HTMLResponse(status_code=403, content="Frontend is disabled")
    
    ui_path = Path(__file__).parent.parent.parent / "web" / "ui" / "index.html"
    
    if not ui_path.exists():
        logger.error(f"UI file not found at {ui_path}")
        return HTMLResponse(
            status_code=404,
            content="<h1>UI Not Found</h1><p>The user interface is not available.</p>"
        )
    
    try:
        with open(ui_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.exception(f"Error reading UI file: {e}")
        return HTMLResponse(
            status_code=500,
            content="<h1>Error</h1><p>Failed to load the user interface.</p>"
        )


@router.get("/")
async def serve_root() -> HTMLResponse:
    """
    Serve the UI from root if frontend enabled.
    Otherwise, show API documentation.
    """
    if is_frontend_enabled():
        return await serve_ui()
    
    # Show API info
    return HTMLResponse(
        content="""
        <html>
            <head>
                <title>Support Ticket Triage API</title>
                <style>
                    body {
                        font-family: system-ui, -apple-system, sans-serif;
                        margin: 40px;
                        color: #333;
                    }
                    code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
                </style>
            </head>
            <body>
                <h1>Support Ticket Triage API</h1>
                <p>This is the REST API server. To use the web UI, enable frontend:</p>
                <code>FRONTEND_ENABLED=true</code>
                <p>API Documentation: <a href="/docs">/docs</a></p>
                <p>OpenAPI Schema: <a href="/openapi.json">/openapi.json</a></p>
            </body>
        </html>
        """
    )
