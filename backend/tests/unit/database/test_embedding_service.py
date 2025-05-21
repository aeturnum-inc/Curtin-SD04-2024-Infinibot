import pytest
from unittest.mock import patch, MagicMock

from app.services.embedding_service import get_embedding_model

@patch("app.services.embedding_service.OpenAIEmbeddings")
@patch("app.services.embedding_service.settings")
def test_get_embedding_model_openai(mock_settings, mock_openai):
    mock_settings.LLM_PROVIDER = "openai"
    model = MagicMock()
    mock_openai.return_value = model

    result = get_embedding_model()
    mock_openai.assert_called_once()
    assert result == model

@patch("app.services.embedding_service.AzureOpenAIEmbeddings")
@patch("app.services.embedding_service.settings")
def test_get_embedding_model_azure(mock_settings, mock_azure):
    mock_settings.LLM_PROVIDER = "azure"
    mock_settings.AZURE_API_KEY = "key"
    mock_settings.AZURE_EMBEDDING_DEPLOYMENT_NAME = "deployment"
    mock_settings.AZURE_API_BASE = "base"
    mock_settings.AZURE_API_VERSION = "version"
    model = MagicMock()
    mock_azure.return_value = model

    result = get_embedding_model()
    mock_azure.assert_called_once_with(
        azure_deployment="deployment",
        azure_endpoint="base",
        api_key="key",
        api_version="version",
    )
    assert result == model

@patch("app.services.embedding_service.OpenAIEmbeddings")
@patch("app.services.embedding_service.settings")
def test_get_embedding_model_azure_missing_settings_fallbacks_to_openai(mock_settings, mock_openai):
    mock_settings.LLM_PROVIDER = "azure"
    mock_settings.AZURE_API_KEY = None
    mock_settings.AZURE_EMBEDDING_DEPLOYMENT_NAME = None
    model = MagicMock()
    mock_openai.return_value = model

    result = get_embedding_model()
    mock_openai.assert_called_once()
    assert result == model