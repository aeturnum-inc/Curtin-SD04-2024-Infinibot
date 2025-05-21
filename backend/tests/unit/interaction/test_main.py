import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from app.main import app

client = TestClient(app)

def test_root_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "LangGraph Agent Server"
    assert data["status"] == "healthy"
    assert "version" in data

def test_get_me_authenticated():
    async def mock_user():
        return {
            "email": "test@example.com",
            "name": "Test User",
            "is_authenticated": True,
            "dev_mode": True,
        }
    app.dependency_overrides = {}
    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = mock_user
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert data["authenticated"] is True
    assert data["dev_mode"] is True
    app.dependency_overrides = {}

def test_get_me_unauthenticated():
    async def mock_user():
        return {
            "email": None,
            "name": None,
            "is_authenticated": False,
            "dev_mode": False,
        }
    app.dependency_overrides = {}
    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = mock_user
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] is None
    assert data["name"] is None
    assert data["authenticated"] is False
    assert data["dev_mode"] is False
    app.dependency_overrides = {}

def test_cors_headers_present():
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert "access-control-allow-origin" in response.headers

def test_log_requests_middleware_logs(monkeypatch):
    logs = []
    monkeypatch.setattr("builtins.print", lambda msg: logs.append(msg))
    response = client.get("/", headers={"authorization": "Bearer test", "x-dev-mode": "true"})
    assert response.status_code == 200
    assert any("Request: GET /, Auth: Present, DevMode: True" in log for log in logs)
    assert any("Response: GET /, Status: 200" in log for log in logs)