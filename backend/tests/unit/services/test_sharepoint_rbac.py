import pytest
from unittest.mock import patch, MagicMock
import requests

from app.services.sharepoint_service import SharePointService


class TestSharePointServiceRBAC:
    """Test cases for SharePoint service RBAC functionality"""

    @pytest.fixture
    def sharepoint_service(self):
        """Create SharePoint service instance with mocked dependencies"""
        with patch('app.services.sharepoint_service.MongoClient'):
            service = SharePointService()
            service.access_token = "mock_token"
            return service

    @pytest.fixture
    def mock_drives_response(self):
        """Mock response for drives API"""
        return {
            "value": [
                {
                    "id": "drive123",
                    "name": "Documents"
                }
            ]
        }

    @pytest.fixture
    def mock_documents_response(self):
        """Mock response for documents API"""
        return {
            "value": [
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
        }

    @patch('requests.get')
    @patch.object(SharePointService, 'check_user_permission')
    def test_list_documents_with_user_permissions(
        self, mock_check_permission, mock_get, sharepoint_service, 
        mock_drives_response, mock_documents_response
    ):
        """Test listing documents filtered by user permissions"""
        # Setup mocks
        mock_get.side_effect = [
            MagicMock(raise_for_status=lambda: None, json=lambda: mock_drives_response),
            MagicMock(raise_for_status=lambda: None, json=lambda: mock_documents_response)
        ]
        
        # Mock permission checks - user has access to doc1 but not doc2
        mock_check_permission.side_effect = lambda doc_id, email, drive_id: doc_id == "doc1"
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"):
            result = sharepoint_service.list_documents(user_email="user@company.com")
        
        # Should only return doc1
        assert len(result) == 1
        assert result[0]["id"] == "doc1"
        assert result[0]["name"] == "Document1.pdf"
        
        # Verify permission checks were called
        assert mock_check_permission.call_count == 2

    @patch('requests.get')
    def test_list_documents_dev_mode_no_filter(
        self, mock_get, sharepoint_service, mock_drives_response, mock_documents_response
    ):
        """Test listing documents in dev mode returns all documents"""
        mock_get.side_effect = [
            MagicMock(raise_for_status=lambda: None, json=lambda: mock_drives_response),
            MagicMock(raise_for_status=lambda: None, json=lambda: mock_documents_response)
        ]
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"), \
             patch('app.services.sharepoint_service.settings.DEV_MODE', True):
            result = sharepoint_service.list_documents(user_email="user@company.com")
        
        # Should return all documents in dev mode
        assert len(result) == 2
        assert result[0]["id"] == "doc1"
        assert result[1]["id"] == "doc2"

    @patch('requests.get')
    def test_list_documents_no_user_email(
        self, mock_get, sharepoint_service, mock_drives_response, mock_documents_response
    ):
        """Test listing documents without user email returns all documents"""
        mock_get.side_effect = [
            MagicMock(raise_for_status=lambda: None, json=lambda: mock_drives_response),
            MagicMock(raise_for_status=lambda: None, json=lambda: mock_documents_response)
        ]
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"):
            result = sharepoint_service.list_documents()
        
        # Should return all documents when no user email provided
        assert len(result) == 2

    @patch('requests.get')
    def test_list_documents_api_error(self, mock_get, sharepoint_service):
        """Test handling API errors when listing documents"""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"):
            with pytest.raises(requests.exceptions.RequestException):
                sharepoint_service.list_documents()

    @patch('app.services.sharepoint_service.get_document_permissions')
    def test_check_user_permission_public_access(
        self, mock_get_permissions, sharepoint_service
    ):
        """Test user permission check for public access document"""
        mock_get_permissions.return_value = {
            "access_level": "public",
            "users": [],
            "groups": []
        }
        
        result = sharepoint_service.check_user_permission("doc1", "user@company.com", "drive1")
        
        assert result is True
        mock_get_permissions.assert_called_once_with(sharepoint_service, "doc1", "drive1")

    @patch('app.services.sharepoint_service.get_document_permissions')
    @patch('app.services.document_permission.is_user_in_organization')
    def test_check_user_permission_organization_access(
        self, mock_is_in_org, mock_get_permissions, sharepoint_service
    ):
        """Test user permission check for organization access document"""
        mock_get_permissions.return_value = {
            "access_level": "organization",
            "users": [],
            "groups": []
        }
        mock_is_in_org.return_value = True
        
        result = sharepoint_service.check_user_permission("doc1", "user@company.com", "drive1")
        
        assert result is True
        mock_is_in_org.assert_called_once_with("user@company.com", sharepoint_service)

    @patch('app.services.sharepoint_service.get_document_permissions')
    @patch('app.services.document_permission.is_user_in_organization')
    def test_check_user_permission_organization_access_denied(
        self, mock_is_in_org, mock_get_permissions, sharepoint_service
    ):
        """Test user permission check denied for organization access when not in org"""
        mock_get_permissions.return_value = {
            "access_level": "organization",
            "users": [],
            "groups": []
        }
        mock_is_in_org.return_value = False
        
        result = sharepoint_service.check_user_permission("doc1", "external@other.com", "drive1")
        
        assert result is False

    @patch('app.services.sharepoint_service.get_document_permissions')
    def test_check_user_permission_direct_user_access(
        self, mock_get_permissions, sharepoint_service
    ):
        """Test user permission check for direct user access"""
        mock_get_permissions.return_value = {
            "access_level": "private",
            "users": ["user@company.com", "other@company.com"],
            "groups": []
        }
        
        result = sharepoint_service.check_user_permission("doc1", "user@company.com", "drive1")
        
        assert result is True

    @patch('app.services.sharepoint_service.get_document_permissions')
    @patch('app.services.document_permission.check_user_group_membership')
    def test_check_user_permission_group_access(
        self, mock_check_group, mock_get_permissions, sharepoint_service
    ):
        """Test user permission check for group access"""
        mock_get_permissions.return_value = {
            "access_level": "private",
            "users": [],
            "groups": ["admin-group@company.com"]
        }
        mock_check_group.return_value = True
        
        result = sharepoint_service.check_user_permission("doc1", "user@company.com", "drive1")
        
        assert result is True
        mock_check_group.assert_called_once_with(
            "user@company.com", 
            ["admin-group@company.com"], 
            sharepoint_service
        )

    @patch('app.services.sharepoint_service.get_document_permissions')
    def test_check_user_permission_access_denied(
        self, mock_get_permissions, sharepoint_service
    ):
        """Test user permission check when access is denied"""
        mock_get_permissions.return_value = {
            "access_level": "private",
            "users": ["other@company.com"],
            "groups": []
        }
        
        result = sharepoint_service.check_user_permission("doc1", "user@company.com", "drive1")
        
        assert result is False

    @patch('app.services.sharepoint_service.get_document_permissions')
    def test_check_user_permission_error_handling(
        self, mock_get_permissions, sharepoint_service
    ):
        """Test error handling in permission check"""
        mock_get_permissions.side_effect = Exception("Permission check failed")
        
        result = sharepoint_service.check_user_permission("doc1", "user@company.com", "drive1")
        
        # Should default to deny access on error
        assert result is False

    @patch('requests.get')
    @patch.object(SharePointService, 'check_user_permission')
    def test_get_document_content_with_permission_check(
        self, mock_check_permission, mock_get, sharepoint_service
    ):
        """Test getting document content with permission check"""
        # Mock drives response
        mock_drives = MagicMock()
        mock_drives.raise_for_status = lambda: None
        mock_drives.json.return_value = {"value": [{"id": "drive123"}]}
        
        # Mock document content response
        mock_content = MagicMock()
        mock_content.raise_for_status = lambda: None
        mock_content.headers = {"Content-Type": "text/plain"}
        mock_content.content = b"Document content"
        mock_content.text = "Document content"
        
        mock_get.side_effect = [mock_drives, mock_content]
        mock_check_permission.return_value = True
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"), \
             patch('app.services.sharepoint_service.settings.DEV_MODE', False):
            result = sharepoint_service.get_document_content("doc1", "user@company.com")
        
        assert result == "Document content"
        mock_check_permission.assert_called_once_with("doc1", "user@company.com", "drive123")

    @patch('requests.get')
    @patch.object(SharePointService, 'check_user_permission')
    def test_get_document_content_permission_denied(
        self, mock_check_permission, mock_get, sharepoint_service
    ):
        """Test getting document content when permission is denied"""
        mock_drives = MagicMock()
        mock_drives.raise_for_status = lambda: None
        mock_drives.json.return_value = {"value": [{"id": "drive123"}]}
        
        mock_get.return_value = mock_drives
        mock_check_permission.return_value = False
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"), \
             patch('app.services.sharepoint_service.settings.DEV_MODE', False):
            with pytest.raises(Exception) as exc_info:
                sharepoint_service.get_document_content("doc1", "user@company.com")
        
        assert "does not have permission" in str(exc_info.value)

    @patch('requests.get')
    def test_get_document_content_dev_mode_no_check(
        self, mock_get, sharepoint_service
    ):
        """Test getting document content in dev mode skips permission check"""
        mock_drives = MagicMock()
        mock_drives.raise_for_status = lambda: None
        mock_drives.json.return_value = {"value": [{"id": "drive123"}]}
        
        mock_content = MagicMock()
        mock_content.raise_for_status = lambda: None
        mock_content.headers = {"Content-Type": "text/plain"}
        mock_content.content = b"Document content"
        mock_content.text = "Document content"
        
        mock_get.side_effect = [mock_drives, mock_content]
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"), \
             patch('app.services.sharepoint_service.settings.DEV_MODE', True):
            result = sharepoint_service.get_document_content("doc1", "user@company.com")
        
        assert result == "Document content"
        # Verify permission check was not called
        assert not any(call.args[0].endswith('permissions') for call in mock_get.call_args_list)

    @patch('requests.get')
    def test_get_document_content_no_user_email(
        self, mock_get, sharepoint_service
    ):
        """Test getting document content without user email skips permission check"""
        mock_drives = MagicMock()
        mock_drives.raise_for_status = lambda: None
        mock_drives.json.return_value = {"value": [{"id": "drive123"}]}
        
        mock_content = MagicMock()
        mock_content.raise_for_status = lambda: None
        mock_content.headers = {"Content-Type": "text/plain"}
        # Fix: Set the actual content attribute
        mock_content.content = b"Document content"
        mock_content.text = "Document content"
        
        mock_get.side_effect = [mock_drives, mock_content]
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"):
            result = sharepoint_service.get_document_content("doc1")
        
        assert result == "Document content"


class TestSharePointContentParsing:
    """Test cases for different content type parsing in SharePoint service"""

    @pytest.fixture
    def sharepoint_service(self):
        """Create SharePoint service instance"""
        with patch('app.services.sharepoint_service.MongoClient'):
            service = SharePointService()
            service.access_token = "mock_token"
            return service

    @patch('requests.get')
    @patch('app.services.sharepoint_service.pdfplumber')
    def test_get_pdf_content(self, mock_pdfplumber, mock_get, sharepoint_service):
        """Test getting PDF document content"""
        # Mock PDF content
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF page content"
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        # Mock API responses
        mock_drives = MagicMock()
        mock_drives.raise_for_status = lambda: None
        mock_drives.json.return_value = {"value": [{"id": "drive123"}]}
        
        mock_content = MagicMock()
        mock_content.raise_for_status = lambda: None
        mock_content.headers = {"Content-Type": "application/pdf"}
        mock_content.content = b"mock pdf content"
        
        mock_get.side_effect = [mock_drives, mock_content]
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"):
            result = sharepoint_service.get_document_content("doc1")
        
        assert result == "PDF page content"

    @patch('requests.get')
    @patch('app.services.sharepoint_service.docx2txt')
    def test_get_docx_content(self, mock_docx2txt, mock_get, sharepoint_service):
        """Test getting DOCX document content"""
        mock_docx2txt.process.return_value = "DOCX content"
        
        # Mock API responses
        mock_drives = MagicMock()
        mock_drives.raise_for_status = lambda: None
        mock_drives.json.return_value = {"value": [{"id": "drive123"}]}
        
        mock_content = MagicMock()
        mock_content.raise_for_status = lambda: None
        mock_content.headers = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        mock_content.content = b"mock docx content"
        
        mock_get.side_effect = [mock_drives, mock_content]
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"):
            result = sharepoint_service.get_document_content("doc1")
        
        assert result == "DOCX content"

    @patch('requests.get')
    def test_get_text_content(self, mock_get, sharepoint_service):
        """Test getting plain text document content"""
        # Mock API responses
        mock_drives = MagicMock()
        mock_drives.raise_for_status = lambda: None
        mock_drives.json.return_value = {"value": [{"id": "drive123"}]}
        
        mock_content = MagicMock()
        mock_content.raise_for_status = lambda: None
        mock_content.headers = {"Content-Type": "text/plain"}
        mock_content.content = b"Plain text content"
        
        mock_get.side_effect = [mock_drives, mock_content]
        
        with patch.object(sharepoint_service, 'get_access_token', return_value="token"):
            result = sharepoint_service.get_document_content("doc1")
        
        assert result == "Plain text content"