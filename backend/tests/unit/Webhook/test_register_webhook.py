import pytest
from unittest.mock import patch, MagicMock

from scripts import register_webhook

def test_main_creates_new_subscription(monkeypatch):
    # Mock settings
    monkeypatch.setattr(register_webhook.settings, "WEBHOOK_CALLBACK_URL", "http://test-url")
    # Mock SharePointService and its methods
    mock_service = MagicMock()
    mock_service.list_drives.return_value = [{"id": "drive1"}]
    mock_service.get_webhook_subscriptions.return_value = []
    monkeypatch.setattr(register_webhook, "SharePointService", lambda: mock_service)

    register_webhook.main()
    mock_service.create_webhook_subscription.assert_called_once_with(
        "drives/drive1/root", "http://test-url"
    )

def test_main_renews_existing_subscription(monkeypatch):
    monkeypatch.setattr(register_webhook.settings, "WEBHOOK_CALLBACK_URL", "http://test-url")
    mock_service = MagicMock()
    mock_service.list_drives.return_value = [{"id": "drive1"}]
    mock_service.get_webhook_subscriptions.return_value = [
        {"id": "sub1", "resource": "drives/drive1/root"}
    ]
    monkeypatch.setattr(register_webhook, "SharePointService", lambda: mock_service)

    register_webhook.main()
    mock_service.renew_webhook_subscription.assert_called_once_with("sub1")

def test_main_deletes_subscription_on_renew_failure(monkeypatch, capsys):
    monkeypatch.setattr(register_webhook.settings, "WEBHOOK_CALLBACK_URL", "http://test-url")
    mock_service = MagicMock()
    mock_service.list_drives.return_value = [{"id": "drive1"}]
    mock_service.get_webhook_subscriptions.return_value = [
        {"id": "sub1", "resource": "drives/drive1/root"}
    ]
    # Simulate renew_webhook_subscription raising an exception
    mock_service.renew_webhook_subscription.side_effect = Exception("renew failed")
    monkeypatch.setattr(register_webhook, "SharePointService", lambda: mock_service)

    register_webhook.main()

    mock_service.renew_webhook_subscription.assert_called_once_with("sub1")
    mock_service.delete_webhook_subscription.assert_called_once_with("sub1")
    captured = capsys.readouterr()
    assert "Failed to renew subscription sub1: renew failed" in captured.out
    assert "Deleting the failed subscription..." in captured.out
    assert "Subscription sub1 deleted successfully." in captured.out or "Failed to delete subscription sub1:" in captured.out

def test_main_delete_subscription_failure(monkeypatch, capsys):
    monkeypatch.setattr(register_webhook.settings, "WEBHOOK_CALLBACK_URL", "http://test-url")
    mock_service = MagicMock()
    mock_service.list_drives.return_value = [{"id": "drive1"}]
    mock_service.get_webhook_subscriptions.return_value = [
        {"id": "sub1", "resource": "drives/drive1/root"}
    ]
    # Simulate renew_webhook_subscription raising an exception
    mock_service.renew_webhook_subscription.side_effect = Exception("renew failed")
    # Simulate delete_webhook_subscription also raising an exception
    mock_service.delete_webhook_subscription.side_effect = Exception("delete failed")
    monkeypatch.setattr(register_webhook, "SharePointService", lambda: mock_service)

    register_webhook.main()

    mock_service.renew_webhook_subscription.assert_called_once_with("sub1")
    mock_service.delete_webhook_subscription.assert_called_once_with("sub1")
    captured = capsys.readouterr()
    assert "Failed to renew subscription sub1: renew failed" in captured.out
    assert "Deleting the failed subscription..." in captured.out
    assert "Failed to delete subscription sub1: delete failed" in captured.out

def test_main_error_ensuring_webhook(monkeypatch, capsys):
    # Patch SharePointService to raise an exception on instantiation
    with patch("scripts.register_webhook.SharePointService", side_effect=Exception("Test error")):
        from scripts import register_webhook
        register_webhook.main()
        captured = capsys.readouterr()
        assert "Error ensuring webhook subscription: Test error" in captured.out

def test_main_handles_no_drives(monkeypatch, capsys):
    monkeypatch.setattr(register_webhook.settings, "WEBHOOK_CALLBACK_URL", "http://test-url")
    mock_service = MagicMock()
    mock_service.list_drives.return_value = []
    monkeypatch.setattr(register_webhook, "SharePointService", lambda: mock_service)

    register_webhook.main()
    captured = capsys.readouterr()
    assert "No drives found in the SharePoint site." in captured.out