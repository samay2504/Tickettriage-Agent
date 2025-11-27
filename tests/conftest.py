"""
Conftest for pytest - fixtures and configuration.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from tempfile import TemporaryDirectory

# Mock FastAPI imports if not available
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:
    FastAPI = None
    TestClient = None

from config.settings import Settings, get_settings
from kb.kb_loader import KBLoader
from kb.search import KBSearch


@pytest.fixture
def temp_kb_path():
    """Create temporary KB file for testing."""
    with TemporaryDirectory() as tmpdir:
        kb_path = Path(tmpdir) / "test_kb.json"
        test_kb = [
            {
                "id": "TEST-001",
                "title": "Test Bug",
                "category": "Bug",
                "symptoms": ["error", "crash"],
                "snippet": "This is a test bug entry",
                "full_text": "Test full text",
                "recommended_action": "Restart service"
            },
            {
                "id": "TEST-002",
                "title": "Test Login Issue",
                "category": "Login",
                "symptoms": ["login", "cannot"],
                "snippet": "Login test entry",
                "full_text": "Test login issue",
                "recommended_action": "Reset password"
            }
        ]
        with open(kb_path, "w") as f:
            json.dump(test_kb, f)
        yield str(kb_path)


@pytest.fixture
def test_settings(temp_kb_path):
    """Create test settings."""
    return Settings(
        api_host="localhost",
        api_port=8000,
        api_debug=False,
        llm_temperature=0.1,
        redis_url="redis://localhost:6379/0",
        cache_enabled=False,  # Disable for tests
        kb_path=temp_kb_path,
        kb_search_top_k=3,
        admin_token="test-token",
        description_min_length=1,
        description_max_length=10000,
    )


@pytest.fixture
def kb_loader(temp_kb_path):
    """Create KB loader."""
    return KBLoader(temp_kb_path)


@pytest.fixture
def kb_search(kb_loader):
    """Create KB search instance."""
    return KBSearch(kb_loader.get_entries())


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    mock_client = Mock()
    mock_client.invoke.return_value = json.dumps({
        "summary": "Test summary",
        "category": "Bug",
        "severity": "Low",
        "known_issue": False,
        "kb_ids": [],
        "suggested_action": "Escalate"
    })
    mock_client.get_provider_name.return_value = "test"
    mock_client.get_provider_info.return_value = {
        "provider": "test",
        "available": True,
        "fallback_mode": False
    }
    mock_client.is_fallback_mode.return_value = False
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    mock_redis = Mock()
    mock_redis.is_available.return_value = False
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.delete_pattern.return_value = 5
    return mock_redis


@pytest.fixture
def mock_orchestrator(mock_llm_client, mock_redis_client):
    """Create mock orchestrator."""
    from agent.orchestrator import TicketTriageOrchestrator
    
    mock_orch = Mock(spec=TicketTriageOrchestrator)
    mock_orch.llm_client = mock_llm_client
    mock_orch.redis_client = mock_redis_client
    
    return mock_orch


@pytest.fixture
def fastapi_test_client():
    """Create FastAPI test client."""
    if not FastAPI or not TestClient:
        pytest.skip("FastAPI not installed")
    
    from app.main import app
    return TestClient(app)
