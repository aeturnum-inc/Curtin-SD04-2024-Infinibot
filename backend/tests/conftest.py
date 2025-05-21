"""
Pytest configuration and shared fixtures for testing.
"""
import pytest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session")
def test_settings():
    """Test settings fixture that provides consistent test configuration"""
    with patch('app.core.config.settings') as mock_settings:
        # Set common test values
        mock_settings.DEV_MODE = False
        mock_settings.AUTH_REQUIRED = True
        mock_settings.DB_NAME = "test_knowledge_base"
        mock_settings.COLLECTION_NAME = "test_documents"
        mock_settings.TENANT_ID = "test-tenant-id"
        mock_settings.CLIENT_ID = "test-client-id"
        mock_settings.CLIENT_SECRET = "test-client-secret"
        mock_settings.SITE_ID = "test-site-id"
        mock_settings.LLM_PROVIDER = "anthropic"
        mock_settings.LLM_MODEL_NAME = "claude-3-sonnet"
        mock_settings.LLM_TEMPERATURE = 0.0
        mock_settings.MONGODB_ATLAS_URI = "mongodb://test-uri"
        yield mock_settings


@pytest.fixture
def mock_mongodb_client():
    """Mock MongoDB client for testing"""
    client = MagicMock()
    db = MagicMock()
    collection = MagicMock()
    
    client.__getitem__.return_value = db
    db.__getitem__.return_value = collection
    
    return client


@pytest.fixture
def mock_request():
    """Mock FastAPI request object"""
    from fastapi import Request
    
    request = MagicMock(spec=Request)
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.url = MagicMock()
    request.url.path = "/test-path"
    return request


@pytest.fixture
def mock_user_context():
    """Standard user context for testing"""
    return {
        "email": "test@company.com",
        "name": "Test User",
        "is_authenticated": True,
        "dev_mode": False
    }


@pytest.fixture
def mock_dev_user_context():
    """Dev mode user context for testing"""
    return {
        "email": "dev@example.com",
        "name": "Developer",
        "is_authenticated": True,
        "dev_mode": True
    }


@pytest.fixture
def mock_sharepoint_service():
    """Mock SharePoint service for testing"""
    service = MagicMock()
    service.get_access_token.return_value = "mock_access_token"
    return service


@pytest.fixture
def sample_document_permissions():
    """Sample document permissions for testing"""
    return {
        "users": ["user1@company.com", "user2@company.com"],
        "groups": ["admin-group@company.com"],
        "access_level": "private"
    }


@pytest.fixture
def sample_sharepoint_documents():
    """Sample SharePoint documents for testing"""
    return [
        {
            "id": "doc1",
            "name": "Document1.pdf",
            "webUrl": "https://sharepoint.com/doc1",
            "lastModifiedDateTime": "2024-01-01T00:00:00Z"
        },
        {
            "id": "doc2", 
            "name": "Document2.docx",
            "webUrl": "https://sharepoint.com/doc2",
            "lastModifiedDateTime": "2024-01-02T00:00:00Z"
        }
    ]


# Pytest configuration
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as auth-related"
    )
    config.addinivalue_line(
        "markers", "rbac: mark test as RBAC-related"
    )


# Global test setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment for each test"""
    # Mock environment variables for testing
    test_env_vars = {
        'DEV_MODE': 'false',
        'AUTH_REQUIRED': 'true',
        'TENANT_ID': 'test-tenant',
        'CLIENT_ID': 'test-client',
        'CLIENT_SECRET': 'test-secret',
        'SITE_ID': 'test-site',
        'MONGODB_ATLAS_URI': 'mongodb://test',
        'LLM_PROVIDER': 'anthropic',
        'ANTHROPIC_API_KEY': 'test-key'
    }
    
    with patch.dict(os.environ, test_env_vars):
        yield


# Helper functions for test data
def create_mock_document(doc_id: str, access_level: str = "private", 
                        authorized_users: list = None, authorized_groups: list = None):
    """Helper function to create mock documents with permissions"""
    doc = MagicMock()
    doc.page_content = f"Content for document {doc_id}"
    doc.metadata = {
        "documentId": doc_id,
        "documentName": f"{doc_id}.pdf",
        "access_level": access_level,
        "authorized_users": authorized_users or [],
        "authorized_groups": authorized_groups or []
    }
    return doc


def create_mock_jwt_token(email: str, name: str = None, exp: int = None):
    """Helper function to create mock JWT tokens for testing"""
    import json
    import base64
    import time
    
    if exp is None:
        exp = int(time.time()) + 3600  # 1 hour from now
    
    payload = {
        "email": email,
        "name": name or email.split("@")[0],
        "exp": exp,
        "aud": "test-audience",
        "iss": "test-issuer"
    }
    
    # Create a mock JWT (not cryptographically valid, just for testing)
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature_b64 = "test_signature"
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"