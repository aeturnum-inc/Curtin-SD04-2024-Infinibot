import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.api.routes.webhook import router

app = FastAPI()
app.include_router(router)

def test_webhook_validation_token():
    with TestClient(app) as client:
        resp = client.post("/webhook?validationToken=abc123")
        assert resp.status_code == 200
        assert resp.text == "abc123"

def test_webhook_notification_success():
    notification = {"value": [{"resource": "drives/drive-id/items/item-id"}]}
    with patch("app.services.sharepoint_service.SharePointService.process_webhook_notification") as mock_proc:
        mock_proc.return_value = None
        with TestClient(app) as client:
            resp = client.post("/webhook", json=notification)
            assert resp.status_code == 200
            assert resp.json() == {"status": "success"}
        mock_proc.assert_called_once_with(notification)

def test_webhook_notification_error():
    notification = {"value": [{"resource": "drives/drive-id/items/item-id"}]}
    with patch("app.services.sharepoint_service.SharePointService.process_webhook_notification", side_effect=Exception("fail")):
        with TestClient(app) as client:
            resp = client.post("/webhook", json=notification)
            assert resp.status_code == 400
            assert "Error processing webhook" in resp.json()["detail"]