import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.api.routes import chat

# Globally override authentication
def override_get_current_user():
    return {"email": "test@user.com", "dev_mode": True, "name": "Test User"}

from app.core.auth import get_current_user
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def test_start_chat_success(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hello!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].insert_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 200
        assert "threadId" in response.json()
        assert response.json()["response"] == "Hello!"

def test_start_chat_no_message(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hello!", "sources": []})
    with patch("app.api.routes.chat.MongoClient"):
        payload = {"message": ""}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 400

def test_start_chat_agent_exception(monkeypatch):
    from app.api.routes import chat
    def raise_exc(*a, **kw): raise Exception("Agent error")
    monkeypatch.setattr(chat, "call_agent", raise_exc)
    with patch("app.api.routes.chat.MongoClient"):
        payload = {"message": "Hi"}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 500

def test_start_chat_legacy_format(monkeypatch):
    from app.api.routes import chat
    # Simulate legacy string response from call_agent
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: "Legacy response")
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].insert_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == "Legacy response"

def test_start_chat_db_exception(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hello!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        # Simulate DB insert error
        db["threads"].insert_one.side_effect = Exception("DB error")
        payload = {"message": "Hi"}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 200  # Should still succeed because dev_mode is True

def test_start_chat_missing_email(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hi!", "sources": []})
    with patch("app.api.routes.chat.MongoClient"):
        def override_user():
            return {"dev_mode": True, "name": "Test User"}
        chat.get_current_user = override_user
        payload = {"message": "Hello"}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 200

def test_start_chat_missing_name(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hi!", "sources": []})
    with patch("app.api.routes.chat.MongoClient"):
        def override_user():
            return {"email": "test@user.com", "dev_mode": True}
        chat.get_current_user = override_user
        payload = {"message": "Hello"}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 200

def test_start_chat_missing_dev_mode(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hi!", "sources": []})
    with patch("app.api.routes.chat.MongoClient"):
        def override_user():
            return {"email": "test@user.com", "name": "Test User"}
        chat.get_current_user = override_user
        payload = {"message": "Hello"}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 200

def test_start_chat_agent_returns_empty_dict(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {})
    with patch("app.api.routes.chat.MongoClient"):
        payload = {"message": "Hi"}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == ""
        assert response.json()["sources"] == []

def test_continue_chat_success(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Follow-up!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = {"thread_id": "thread123", "user_email": "test@user.com"}
        db["threads"].update_one.return_value = None
        payload = {"message": "Continue"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == "Follow-up!"

def test_continue_chat_no_message(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hello!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = {"thread_id": "thread123", "user_email": "test@user.com"}
        db["threads"].update_one.return_value = None
        payload = {"message": ""}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 400

def test_continue_chat_creates_thread_if_not_exists(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Created!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = None  # Simulate thread not found
        db["threads"].insert_one.return_value = None
        payload = {"message": "Start new"}
        response = client.post("/api/chat/thread999", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == "Created!"

def test_continue_chat_agent_exception(monkeypatch):
    from app.api.routes import chat
    def raise_exc(*a, **kw): raise Exception("Agent error")
    monkeypatch.setattr(chat, "call_agent", raise_exc)
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = {"thread_id": "thread123", "user_email": "test@user.com"}
        db["threads"].update_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 500

def test_continue_chat_db_exception(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hello!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.side_effect = Exception("DB error")
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200  # dev_mode True

def test_continue_chat_thread_owner_is_none(monkeypatch):
    from app.api.routes import chat
    # Simulate thread_info with no user_email
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "No owner!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        threads_collection = MagicMock()
        db.__getitem__.return_value = threads_collection
        db.threads = threads_collection
        threads_collection.find_one.return_value = {"thread_id": "thread123"}  # No user_email
        threads_collection.update_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == "No owner!"

def test_continue_chat_db_update_exception(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "DB update error!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        threads_collection = MagicMock()
        db.__getitem__.return_value = threads_collection
        db.threads = threads_collection
        threads_collection.find_one.return_value = {"thread_id": "thread123", "user_email": "test@user.com"}
        threads_collection.update_one.side_effect = Exception("DB update failed")
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == "DB update error!"

def test_continue_chat_db_insert_exception(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "DB insert error!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        threads_collection = MagicMock()
        db.__getitem__.return_value = threads_collection
        db.threads = threads_collection
        threads_collection.find_one.return_value = None
        threads_collection.insert_one.side_effect = Exception("DB insert failed")
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == "DB insert error!"

def test_continue_chat_permission_check_exception(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Should not reach", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        threads_collection = MagicMock()
        db.__getitem__.return_value = threads_collection
        db.threads = threads_collection
        # Simulate exception in find_one (e.g., DB error)
        threads_collection.find_one.side_effect = Exception("DB error")
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200  # dev_mode True, so error is swallowed

def test_continue_chat_missing_email(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hi!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = {"thread_id": "thread123", "user_email": None}
        db["threads"].update_one.return_value = None
        def override_user():
            return {"dev_mode": True, "name": "Test User"}
        chat.get_current_user = override_user
        payload = {"message": "Hello"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200

def test_continue_chat_missing_name(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hi!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = None
        db["threads"].insert_one.return_value = None
        def override_user():
            return {"email": "test@user.com", "dev_mode": True}
        chat.get_current_user = override_user
        payload = {"message": "Hello"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200

def test_continue_chat_missing_dev_mode(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hi!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = None
        db["threads"].insert_one.return_value = None
        def override_user():
            return {"email": "test@user.com", "name": "Test User"}
        chat.get_current_user = override_user
        payload = {"message": "Hello"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200

def test_continue_chat_agent_returns_empty_dict(monkeypatch):
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = {"thread_id": "thread123", "user_email": "test@user.com"}
        db["threads"].update_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == ""
        assert response.json()["sources"] == []

def test_continue_chat_owner_case_insensitive(monkeypatch):
    """Should allow access if emails match case-insensitively."""
    from app.api.routes import chat
    from app.core.auth import get_current_user
    def fake_get_current_user():
        return {"email": "OWNER@USER.COM", "dev_mode": False, "name": "Owner"}
    app.dependency_overrides[get_current_user] = fake_get_current_user
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Allowed!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        threads_collection = MagicMock()
        db.__getitem__.return_value = threads_collection
        db.threads = threads_collection
        threads_collection.find_one.return_value = {"thread_id": "thread123", "user_email": "owner@user.com"}
        threads_collection.update_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == "Allowed!"
    app.dependency_overrides[get_current_user] = override_get_current_user

def test_continue_chat_thread_not_found_and_db_insert_fails(monkeypatch):
    """Should still return 200 if thread not found and insert_one fails (dev_mode True)."""
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Created!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        threads_collection = MagicMock()
        db.__getitem__.return_value = threads_collection
        db.threads = threads_collection
        threads_collection.find_one.return_value = None
        threads_collection.insert_one.side_effect = Exception("Insert failed")
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread999", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == "Created!"

def test_continue_chat_agent_returns_dict_missing_content_sources(monkeypatch):
    """Should default to empty string and list if agent dict missing keys."""
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"foo": "bar"})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = {"thread_id": "thread123", "user_email": "test@user.com"}
        db["threads"].update_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == ""
        assert response.json()["sources"] == []
        

def test_start_chat_stores_user_exception(monkeypatch):
    """Covers exception when storing user context in MongoDB (not dev_mode)."""
    from app.api.routes import chat
    from app.core.auth import get_current_user
    def override_user():
        return {"email": "test@user.com", "dev_mode": False, "name": "Test User"}
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Hello!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        threads_collection = MagicMock()
        db.__getitem__.return_value = threads_collection
        db.threads = threads_collection
        threads_collection.insert_one.side_effect = Exception("DB error")
        payload = {"message": "Hi"}
        response = client.post("/api/chat/", json=payload)
        assert response.status_code == 200
    app.dependency_overrides[get_current_user] = override_get_current_user

def test_continue_chat_permission_check_exception(monkeypatch):
    """Covers exception in permission check block (not dev_mode)."""
    from app.api.routes import chat
    from app.core.auth import get_current_user
    def override_user():
        return {"email": "test@user.com", "dev_mode": False, "name": "Test User"}
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Should not reach", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        threads_collection = MagicMock()
        db.__getitem__.return_value = threads_collection
        db.threads = threads_collection
        threads_collection.find_one.side_effect = Exception("DB error")
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200
    app.dependency_overrides[get_current_user] = override_get_current_user

def test_continue_chat_thread_not_found_and_db_insert_fails_not_dev(monkeypatch):
    """Covers thread not found and insert_one fails (not dev_mode)."""
    from app.api.routes import chat
    from app.core.auth import get_current_user
    def override_user():
        return {"email": "test@user.com", "dev_mode": False, "name": "Test User"}
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: {"content": "Created!", "sources": []})
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        threads_collection = MagicMock()
        db.__getitem__.return_value = threads_collection
        db.threads = threads_collection
        threads_collection.find_one.return_value = None
        threads_collection.insert_one.side_effect = Exception("Insert failed")
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread999", json=payload)
        assert response.status_code == 200
    app.dependency_overrides[get_current_user] = override_get_current_user

def test_continue_chat_legacy_format(monkeypatch):
    """Covers legacy string response in continue_chat."""
    from app.api.routes import chat
    monkeypatch.setattr(chat, "call_agent", lambda *a, **kw: "Legacy response")
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = {"thread_id": "thread123", "user_email": "test@user.com"}
        db["threads"].update_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 200
        assert response.json()["response"] == "Legacy response"

def test_continue_chat_final_exception(monkeypatch):
    """Covers the final except Exception block in continue_chat."""
    from app.api.routes import chat
    # Simulate call_agent raising an unexpected error
    def raise_exc(*a, **kw): raise Exception("Unexpected error")
    monkeypatch.setattr(chat, "call_agent", raise_exc)
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = {"thread_id": "thread123", "user_email": "test@user.com"}
        db["threads"].update_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 500
        assert "Internal server error" in response.text

def test_continue_chat_raises_http_exception(monkeypatch):
    """Should re-raise HTTPException in the outer except block."""
    from app.api.routes import chat
    from fastapi import HTTPException
    def raise_http_exc(*a, **kw): raise HTTPException(status_code=418, detail="I'm a teapot")
    monkeypatch.setattr(chat, "call_agent", raise_http_exc)
    with patch("app.api.routes.chat.MongoClient") as mock_client:
        db = mock_client.return_value[chat.settings.DB_NAME]
        db["threads"].find_one.return_value = {"thread_id": "thread123", "user_email": "test@user.com"}
        db["threads"].update_one.return_value = None
        payload = {"message": "Hi"}
        response = client.post("/api/chat/thread123", json=payload)
        assert response.status_code == 418
        assert "teapot" in response.text