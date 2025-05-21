import pytest
from unittest import mock

import app.services.seed_service as seed_service

@pytest.fixture
def mock_settings():
    with mock.patch("app.services.seed_service.settings") as m:
        m.MONGODB_ATLAS_URI = "mongodb://fake"
        m.DB_NAME = "testdb"
        m.COLLECTION_NAME = "testcol"
        m.SITE_ID = "siteid"
        yield m

@pytest.fixture
def mock_mongo_client():
    with mock.patch("app.services.seed_service.MongoClient") as m:
        yield m

@pytest.fixture
def mock_sharepoint_service():
    with mock.patch("app.services.seed_service.SharePointService") as m:
        yield m

@pytest.fixture
def mock_get_document_permissions():
    with mock.patch("app.services.seed_service.get_document_permissions") as m:
        yield m

@pytest.fixture
def mock_get_embedding_model():
    with mock.patch("app.services.seed_service.get_embedding_model") as m:
        m.return_value = mock.Mock()
        yield m

@pytest.fixture
def mock_vector_search():
    with mock.patch("app.services.seed_service.MongoDBAtlasVectorSearch") as m:
        yield m

def make_fake_doc(id="1", name="Doc", webUrl="url", lastModified="now"):
    return {"id": id, "name": name, "webUrl": webUrl, "lastModified": lastModified}

def test_seed_database_success(
    mock_settings, mock_mongo_client, mock_sharepoint_service,
    mock_get_document_permissions, mock_get_embedding_model, mock_vector_search
):
    fake_client = mock.MagicMock()
    fake_collection = mock.MagicMock()
    fake_db = {mock_settings.COLLECTION_NAME: fake_collection}
    fake_client.__getitem__.side_effect = lambda name: fake_db if name == mock_settings.DB_NAME else fake_collection
    mock_mongo_client.return_value = fake_client
    fake_sharepoint = mock_sharepoint_service.return_value
    fake_sharepoint.list_documents.return_value = [make_fake_doc()]
    fake_sharepoint.get_document_content.return_value = "content"
    with mock.patch("app.services.seed_service.RecursiveCharacterTextSplitter") as mock_splitter:
        mock_splitter.return_value.split_text.return_value = ["chunk1", "chunk2"]
        result = seed_service.seed_database(client=None, admin_email=None)
    assert result == 2
    fake_collection.delete_many.assert_called_once()
    mock_vector_search.from_documents.assert_called_once()
    fake_client.close.assert_called_once()

def test_seed_database_no_documents(
    mock_settings, mock_mongo_client, mock_sharepoint_service,
    mock_get_document_permissions, mock_get_embedding_model, mock_vector_search
):
    fake_client = mock.MagicMock()
    fake_collection = mock.MagicMock()
    fake_db = {mock_settings.COLLECTION_NAME: fake_collection}
    fake_client.__getitem__.side_effect = lambda name: fake_db if name == mock_settings.DB_NAME else fake_collection
    mock_mongo_client.return_value = fake_client
    fake_sharepoint = mock_sharepoint_service.return_value
    fake_sharepoint.list_documents.return_value = []
    with pytest.raises(Exception, match="No documents to upload to database"):
        seed_service.seed_database(client=None, admin_email=None)
    fake_client.close.assert_called_once()

def test_seed_database_permission_mapping_error(
    mock_settings, mock_mongo_client, mock_sharepoint_service,
    mock_get_document_permissions, mock_get_embedding_model, mock_vector_search
):
    fake_client = mock.MagicMock()
    fake_collection = mock.MagicMock()
    fake_db = {mock_settings.COLLECTION_NAME: fake_collection}
    fake_client.__getitem__.side_effect = lambda name: fake_db if name == mock_settings.DB_NAME else fake_collection
    mock_mongo_client.return_value = fake_client
    fake_sharepoint = mock_sharepoint_service.return_value
    fake_sharepoint.list_documents.return_value = [make_fake_doc()]
    fake_sharepoint.get_access_token.side_effect = Exception("token error")
    with mock.patch("app.services.seed_service.RecursiveCharacterTextSplitter") as mock_splitter:
        mock_splitter.return_value.split_text.return_value = ["chunk"]
        result = seed_service.seed_database(client=None, admin_email="admin@example.com")
    assert result == 1
    fake_client.close.assert_called_once()

def test_seed_database_document_processing_error(
    mock_settings, mock_mongo_client, mock_sharepoint_service,
    mock_get_document_permissions, mock_get_embedding_model, mock_vector_search
):
    fake_client = mock.MagicMock()
    fake_collection = mock.MagicMock()
    fake_db = {mock_settings.COLLECTION_NAME: fake_collection}
    fake_client.__getitem__.side_effect = lambda name: fake_db if name == mock_settings.DB_NAME else fake_collection
    mock_mongo_client.return_value = fake_client
    fake_sharepoint = mock_sharepoint_service.return_value
    fake_sharepoint.list_documents.return_value = [make_fake_doc()]
    fake_sharepoint.get_document_content.side_effect = Exception("content error")
    with mock.patch("app.services.seed_service.RecursiveCharacterTextSplitter") as mock_splitter:
        mock_splitter.return_value.split_text.return_value = ["chunk"]
        with pytest.raises(Exception, match="No documents to upload to database"):
            seed_service.seed_database(client=None, admin_email=None)
    fake_client.close.assert_called_once()

def test_seed_database_finally_closes_client(
    mock_settings, mock_mongo_client, mock_sharepoint_service,
    mock_get_document_permissions, mock_get_embedding_model, mock_vector_search
):
    fake_client = mock.MagicMock()
    fake_collection = mock.MagicMock()
    fake_db = {mock_settings.COLLECTION_NAME: fake_collection}
    fake_client.__getitem__.side_effect = lambda name: fake_db if name == mock_settings.DB_NAME else fake_collection
    mock_mongo_client.return_value = fake_client
    fake_sharepoint = mock_sharepoint_service.return_value
    fake_sharepoint.list_documents.side_effect = Exception("fail")
    with pytest.raises(Exception):
        seed_service.seed_database(client=None, admin_email=None)
    fake_client.close.assert_called_once()
    
def test_seed_database_admin_permission_mapping_success(
    mock_settings, mock_mongo_client, mock_sharepoint_service,
    mock_get_document_permissions, mock_get_embedding_model, mock_vector_search
):
    """Covers admin_email branch, drives found, permissions fetched, permission metadata added."""
    fake_client = mock.MagicMock()
    fake_collection = mock.MagicMock()
    fake_db = {mock_settings.COLLECTION_NAME: fake_collection}
    fake_client.__getitem__.side_effect = lambda name: fake_db if name == mock_settings.DB_NAME else fake_collection
    mock_mongo_client.return_value = fake_client

    fake_sharepoint = mock_sharepoint_service.return_value
    fake_sharepoint.list_documents.return_value = [make_fake_doc()]
    fake_sharepoint.get_document_content.return_value = "content"
    fake_sharepoint.get_access_token.return_value = "tokentest"
    # Simulate drives returned from requests.get
    fake_response = mock.Mock()
    fake_response.json.return_value = {"value": [{"id": "driveid"}]}
    fake_response.raise_for_status = mock.Mock()
    with mock.patch("app.services.seed_service.requests.get", return_value=fake_response):
        with mock.patch("app.services.seed_service.RecursiveCharacterTextSplitter") as mock_splitter:
            mock_splitter.return_value.split_text.return_value = ["chunk"]
            # Simulate get_document_permissions returns permission data
            mock_get_document_permissions.return_value = {
                "users": ["user1"],
                "groups": ["group1"],
                "access_level": "read"
            }
            result = seed_service.seed_database(client=None, admin_email="admin@example.com")
    assert result == 1
    fake_collection.delete_many.assert_called_once()
    mock_vector_search.from_documents.assert_called_once()
    fake_client.close.assert_called_once()

def test_seed_database_admin_permission_mapping_no_drives(
    mock_settings, mock_mongo_client, mock_sharepoint_service,
    mock_get_document_permissions, mock_get_embedding_model, mock_vector_search
):
    """Covers admin_email branch, but no drives found."""
    fake_client = mock.MagicMock()
    fake_collection = mock.MagicMock()
    fake_db = {mock_settings.COLLECTION_NAME: fake_collection}
    fake_client.__getitem__.side_effect = lambda name: fake_db if name == mock_settings.DB_NAME else fake_collection
    mock_mongo_client.return_value = fake_client

    fake_sharepoint = mock_sharepoint_service.return_value
    fake_sharepoint.list_documents.return_value = [make_fake_doc()]
    fake_sharepoint.get_document_content.return_value = "content"
    fake_sharepoint.get_access_token.return_value = "tokentest"
    # Simulate no drives returned from requests.get
    fake_response = mock.Mock()
    fake_response.json.return_value = {"value": []}
    fake_response.raise_for_status = mock.Mock()
    with mock.patch("app.services.seed_service.requests.get", return_value=fake_response):
        with mock.patch("app.services.seed_service.RecursiveCharacterTextSplitter") as mock_splitter:
            mock_splitter.return_value.split_text.return_value = ["chunk"]
            result = seed_service.seed_database(client=None, admin_email="admin@example.com")
    assert result == 1
    fake_collection.delete_many.assert_called_once()
    mock_vector_search.from_documents.assert_called_once()
    fake_client.close.assert_called_once()

def test_seed_database_admin_permission_mapping_permission_error(
    mock_settings, mock_mongo_client, mock_sharepoint_service,
    mock_get_document_permissions, mock_get_embedding_model, mock_vector_search
):
    """Covers admin_email branch, drives found, but get_document_permissions raises error."""
    fake_client = mock.MagicMock()
    fake_collection = mock.MagicMock()
    fake_db = {mock_settings.COLLECTION_NAME: fake_collection}
    fake_client.__getitem__.side_effect = lambda name: fake_db if name == mock_settings.DB_NAME else fake_collection
    mock_mongo_client.return_value = fake_client

    fake_sharepoint = mock_sharepoint_service.return_value
    fake_sharepoint.list_documents.return_value = [make_fake_doc()]
    fake_sharepoint.get_document_content.return_value = "content"
    fake_sharepoint.get_access_token.return_value = "tokentest"
    # Simulate drives returned from requests.get
    fake_response = mock.Mock()
    fake_response.json.return_value = {"value": [{"id": "driveid"}]}
    fake_response.raise_for_status = mock.Mock()
    with mock.patch("app.services.seed_service.requests.get", return_value=fake_response):
        with mock.patch("app.services.seed_service.RecursiveCharacterTextSplitter") as mock_splitter:
            mock_splitter.return_value.split_text.return_value = ["chunk"]
            mock_get_document_permissions.side_effect = Exception("perm error")
            result = seed_service.seed_database(client=None, admin_email="admin@example.com")
    assert result == 1
    fake_collection.delete_many.assert_called_once()
    mock_vector_search.from_documents.assert_called_once()
    fake_client.close.assert_called_once()