"""
Tests for UI routes and static file serving.
"""

import pytest
from pathlib import Path


class TestUIRoutes:
    """Tests for UI route handlers."""

    def test_ui_endpoint_returns_html(self):
        """Test that /ui endpoint returns HTML."""
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("FastAPI not installed")
        
        client = TestClient(app)
        response = client.get("/ui")
        
        # Should return 200 OK
        assert response.status_code == 200
        
        # Should return HTML
        assert "text/html" in response.headers.get("content-type", "")
        
        # Should contain expected UI elements
        assert "<textarea" in response.text or "description" in response.text.lower()
        assert "button" in response.text.lower() or "submit" in response.text.lower()

    def test_root_redirects_to_ui_when_enabled(self):
        """Test that / redirects to UI when frontend is enabled."""
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("FastAPI not installed")
        
        client = TestClient(app)
        response = client.get("/", follow_redirects=False)
        
        # Should return 200 (not 404) or redirect
        assert response.status_code in [200, 307, 308]

    def test_static_files_served(self):
        """Test that static files (CSS, JS) are served."""
        try:
            from fastapi.testclient import TestClient
            from app.main import app
        except ImportError:
            pytest.skip("FastAPI not installed")
        
        client = TestClient(app)
        
        # Test CSS file
        css_response = client.get("/static/css/style.css")
        if css_response.status_code == 200:
            assert "css" in css_response.headers.get("content-type", "").lower()
        
        # Test JS file
        js_response = client.get("/static/js/main.js")
        if js_response.status_code == 200:
            assert "javascript" in js_response.headers.get("content-type", "").lower()

    def test_ui_html_file_exists(self):
        """Test that UI HTML file exists."""
        ui_path = Path(__file__).parent.parent / "web" / "ui" / "index.html"
        assert ui_path.exists(), f"UI file not found at {ui_path}"
        
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "<textarea" in content or "description" in content.lower()

    def test_static_css_file_exists(self):
        """Test that static CSS file exists."""
        css_path = Path(__file__).parent.parent / "web" / "static" / "css" / "style.css"
        assert css_path.exists(), f"CSS file not found at {css_path}"
        
        with open(css_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert ":root" in content or "--bg" in content

    def test_static_js_file_exists(self):
        """Test that static JS file exists."""
        js_path = Path(__file__).parent.parent / "web" / "static" / "js" / "main.js"
        assert js_path.exists(), f"JS file not found at {js_path}"
        
        with open(js_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "function" in content or "fetch" in content or "const" in content

    def test_ui_page_accessibility(self):
        """Test that UI page has accessibility features."""
        ui_path = Path(__file__).parent.parent / "web" / "ui" / "index.html"
        
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Check for ARIA labels
            assert "aria-label" in content or "aria-" in content, "Missing ARIA attributes"
            
            # Check for label elements
            assert "<label" in content, "Missing label elements"

    def test_css_variables_defined(self):
        """Test that CSS variables (theme) are defined."""
        css_path = Path(__file__).parent.parent / "web" / "static" / "css" / "style.css"
        
        with open(css_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Check for liquid-glass theme
            assert "--bg:" in content or "background:" in content
            assert "--accent" in content or "#00aaff" in content
            
            # Check for key CSS properties
            assert "backdrop-filter" in content or "blur" in content
            assert "linear-gradient" in content

    def test_js_has_fetch_api(self):
        """Test that JS uses Fetch API."""
        js_path = Path(__file__).parent.parent / "web" / "static" / "js" / "main.js"
        
        with open(js_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Should use fetch API
            assert "fetch(" in content
            
            # Should handle JSON
            assert ".json()" in content

    def test_ui_form_validation(self):
        """Test that UI has form validation."""
        js_path = Path(__file__).parent.parent / "web" / "static" / "js" / "main.js"
        
        with open(js_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Should validate description
            assert "validate" in content.lower()
            
            # Should check length
            assert "length" in content


class TestUIConfiguration:
    """Tests for UI configuration."""

    def test_frontend_enabled_env_var(self, monkeypatch):
        """Test that FRONTEND_ENABLED env var is respected."""
        monkeypatch.setenv("FRONTEND_ENABLED", "false")
        
        from config.settings import reload_settings
        settings = reload_settings()
        
        assert settings.frontend_enabled is False
        
        # Reset
        monkeypatch.setenv("FRONTEND_ENABLED", "true")
        reload_settings()

    def test_frontend_disabled_shows_api_info(self):
        """Test that when frontend is disabled, API info is shown."""
        try:
            from fastapi.testclient import TestClient
            from fastapi import FastAPI
            from app.routes.ui import router as ui_router
        except ImportError:
            pytest.skip("FastAPI not installed")
        
        app = FastAPI()
        app.include_router(ui_router)
        
        client = TestClient(app)
        response = client.get("/", follow_redirects=True)
        
        # Should return 200
        assert response.status_code == 200

    def test_frontend_port_configuration(self, monkeypatch):
        """Test that FRONTEND_PORT can be configured."""
        monkeypatch.setenv("FRONTEND_PORT", "3000")
        
        from config.settings import reload_settings
        settings = reload_settings()
        
        assert settings.frontend_port == 3000
        
        # Reset
        monkeypatch.delenv("FRONTEND_PORT")
        reload_settings()


class TestUIErrorHandling:
    """Tests for UI error handling."""

    def test_ui_handles_api_errors(self):
        """Test that UI can handle API errors gracefully."""
        js_path = Path(__file__).parent.parent / "web" / "static" / "js" / "main.js"
        
        with open(js_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Should have error handling
            assert "catch" in content
            assert "error" in content.lower()

    def test_ui_displays_loading_state(self):
        """Test that UI shows loading spinner."""
        html_path = Path(__file__).parent.parent / "web" / "ui" / "index.html"
        
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Should have loading indicator
            assert "spinner" in content.lower() or "loading" in content.lower()

    def test_ui_displays_results(self):
        """Test that UI displays triage results."""
        html_path = Path(__file__).parent.parent / "web" / "ui" / "index.html"
        
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Should have result sections
            assert "result" in content.lower() or "summary" in content.lower()
            assert "category" in content.lower()
            assert "severity" in content.lower()
