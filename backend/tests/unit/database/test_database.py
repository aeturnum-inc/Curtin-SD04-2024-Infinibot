import pytest
from unittest.mock import patch, MagicMock
from pymongo.errors import ConnectionFailure
from app.core import database

@patch("app.core.database.settings")
@patch("app.core.database.MongoClient")
def test_connect_to_mongodb_success(mock_mongo_client, mock_settings, capsys):
    mock_settings.MONGODB_ATLAS_URI = "mongodb://fakeuri"
    mock_client_instance = MagicMock()
    mock_mongo_client.return_value = mock_client_instance

    database.connect_to_mongodb()

    mock_mongo_client.assert_called_once_with("mongodb://fakeuri")
    mock_client_instance.admin.command.assert_called_once_with("ping")
    captured = capsys.readouterr()
    assert "Connected to MongoDB (synchronous)" in captured.out
    assert database.mongodb_client == mock_client_instance

def test_get_mongodb_client_returns_client():
    mock_client = MagicMock()
    database.mongodb_client = mock_client

    result = database.get_mongodb_client()
    assert result == mock_client

@patch("app.core.database.settings")
@patch("app.core.database.MongoClient")
def test_connect_to_mongodb_failure(mock_mongo_client, mock_settings, capsys):
    mock_settings.MONGODB_ATLAS_URI = "mongodb://fakeuri"
    mock_client_instance = MagicMock()
    mock_client_instance.admin.command.side_effect = ConnectionFailure("fail")
    mock_mongo_client.return_value = mock_client_instance

    with pytest.raises(ConnectionFailure):
        database.connect_to_mongodb()

        mock_mongo_client.assert_called_once_with("mongodb://fakeuri")
        mock_client_instance.admin.command.assert_called_once_with("ping")
        captured = capsys.readouterr()
        assert "Failed to connect to MongoDB (sync)" in captured.out

def test_close_mongodb_connection_closes_and_prints(capsys):
    mock_client = MagicMock()
    database.mongodb_client = mock_client

    database.close_mongodb_connection()

    mock_client.close.assert_called_once()
    captured = capsys.readouterr()
    assert "Closed MongoDB connection (sync)" in captured.out
    # Optionally, check that mongodb_client is still set (the function does not set it to None)
    assert database.mongodb_client == mock_client

def test_close_mongodb_connection_noop_when_none(capsys):
    database.mongodb_client = None

    database.close_mongodb_connection()

    # Nothing should happen, no exception, no output
    captured = capsys.readouterr()
    assert "Closed MongoDB connection (sync)" not in captured.out