import pytest
from unittest.mock import patch, MagicMock
import requests

from app.services.document_permission import (
    get_org_domains,
    check_user_group_membership,
    is_user_in_organization,
    get_document_permissions,
    process_permission_entry,
    process_granted_entity,
    get_group_details
)


class TestGetOrgDomains:
    """Test cases for get_org_domains function"""

    @patch('app.services.document_permission.settings')
    def test_get_org_domains_from_settings(self, mock_settings):
        """Test getting organization domains from settings"""
        mock_settings.ORG_DOMAINS = "domain1.com,domain2.com, domain3.com"
        
        result = get_org_domains()
        
        assert result == ["domain1.com", "domain2.com", "domain3.com"]

    @patch('app.services.document_permission.settings')
    def test_get_org_domains_default(self, mock_settings):
        """Test getting default organization domains"""
        mock_settings.ORG_DOMAINS = None
        # Should use default from getattr
        with patch('app.services.document_permission.getattr') as mock_getattr:
            mock_getattr.return_value = "microweb.global,microwebglobal.onmicrosoft.com"
            
            result = get_org_domains()
            
            assert result == ["microweb.global", "microwebglobal.onmicrosoft.com"]

    @patch('app.services.document_permission.settings')
    def test_get_org_domains_empty_string(self, mock_settings):
        """Test handling empty domain strings"""
        mock_settings.ORG_DOMAINS = "domain1.com, , domain2.com"
        
        result = get_org_domains()
        
        assert result == ["domain1.com", "domain2.com"]


class TestCheckUserGroupMembership:
    """Test cases for check_user_group_membership function"""

    @pytest.fixture
    def mock_sharepoint_service(self):
        """Create mock SharePoint service"""
        service = MagicMock()
        service.get_access_token.return_value = "mock_token"
        return service

    @patch('app.services.document_permission.get_org_domains')
    def test_user_in_sharepoint_group(self, mock_get_domains, mock_sharepoint_service):
        """Test user membership in SharePoint site groups"""
        mock_get_domains.return_value = ["microweb.global"]
        user_email = "user@microweb.global"
        groups = ["demo Owners", "demo Members"]
        
        result = check_user_group_membership(user_email, groups, mock_sharepoint_service)
        
        assert result is True

    @patch('app.services.document_permission.get_org_domains')
    def test_user_not_in_org_domain(self, mock_get_domains, mock_sharepoint_service):
        """Test user not in organization domain"""
        mock_get_domains.return_value = ["microweb.global"]
        user_email = "user@external.com"
        groups = ["demo Owners"]
        
        result = check_user_group_membership(user_email, groups, mock_sharepoint_service)
        
        assert result is False

    @patch('app.services.document_permission.get_org_domains')
    @patch('requests.get')
    def test_user_in_azure_ad_group(self, mock_get, mock_get_domains, mock_sharepoint_service):
        """Test user membership in Azure AD groups"""
        mock_get_domains.return_value = ["microweb.global"]
        user_email = "user@microweb.global"
        groups = ["azure-group@microweb.global"]
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"displayName": "azure-group", "mail": "azure-group@microweb.global"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = check_user_group_membership(user_email, groups, mock_sharepoint_service)
        
        assert result is True
        mock_get.assert_called_once()

    @patch('app.services.document_permission.get_org_domains')
    @patch('requests.get')
    def test_api_error_returns_false(self, mock_get, mock_get_domains, mock_sharepoint_service):
        """Test API error handling"""
        mock_get_domains.return_value = ["microweb.global"]
        user_email = "user@microweb.global"
        groups = ["some-group@microweb.global"]
        
        # Mock API error
        mock_get.return_value.status_code = 404
        
        result = check_user_group_membership(user_email, groups, mock_sharepoint_service)
        
        assert result is False

    def test_invalid_email_format(self, mock_sharepoint_service):
        """Test handling invalid email format"""
        user_email = "invalid-email"
        groups = ["some-group"]
        
        result = check_user_group_membership(user_email, groups, mock_sharepoint_service)
        
        assert result is False

    @patch('app.services.document_permission.get_org_domains')
    def test_no_azure_ad_groups(self, mock_get_domains, mock_sharepoint_service):
        """Test when no Azure AD groups are present"""
        mock_get_domains.return_value = ["microweb.global"]
        user_email = "user@external.com"
        groups = ["demo Owners"]  # Only SharePoint groups
        
        result = check_user_group_membership(user_email, groups, mock_sharepoint_service)
        
        # Should return False since user is not in org domain
        assert result is False


class TestIsUserInOrganization:
    """Test cases for is_user_in_organization function"""

    @patch('app.services.document_permission.get_org_domains')
    def test_user_in_organization(self, mock_get_domains):
        """Test user in organization domain"""
        mock_get_domains.return_value = ["microweb.global", "company.com"]
        
        result = is_user_in_organization("user@microweb.global")
        
        assert result is True

    @patch('app.services.document_permission.get_org_domains')
    def test_user_not_in_organization(self, mock_get_domains):
        """Test user not in organization domain"""
        mock_get_domains.return_value = ["microweb.global"]
        
        result = is_user_in_organization("user@external.com")
        
        assert result is False

    @patch('app.services.document_permission.get_org_domains')
    def test_invalid_email_format(self, mock_get_domains):
        """Test invalid email format"""
        mock_get_domains.return_value = ["microweb.global"]
        
        result = is_user_in_organization("invalid-email")
        
        assert result is False


class TestGetDocumentPermissions:
    """Test cases for get_document_permissions function"""

    @pytest.fixture
    def mock_sharepoint_service(self):
        """Create mock SharePoint service"""
        service = MagicMock()
        service.get_access_token.return_value = "mock_token"
        return service

    @patch('requests.get')
    def test_successful_permissions_retrieval(self, mock_get, mock_sharepoint_service):
        """Test successful retrieval of document permissions"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "value": [
                {
                    "link": {
                        "scope": "organization",
                        "type": "view",
                        "webUrl": "https://example.com/link"
                    },
                    "grantedToV2": {
                        "user": {"email": "user1@company.com"}
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_document_permissions(mock_sharepoint_service, "doc123", "drive123")
        
        assert result["access_level"] == "organization"
        assert "user1@company.com" in result["users"]
        assert len(result["sharing_links"]) == 1

    @patch('requests.get')
    def test_api_error_handling(self, mock_get, mock_sharepoint_service):
        """Test API error handling"""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        result = get_document_permissions(mock_sharepoint_service, "doc123", "drive123")
        
        assert result["access_level"] == "private"
        assert result["users"] == []
        assert result["groups"] == []
        assert "error" in result

    @patch('requests.get')
    def test_public_access_level(self, mock_get, mock_sharepoint_service):
        """Test detection of public access level"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "value": [
                {
                    "link": {
                        "scope": "anonymous",
                        "type": "view"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_document_permissions(mock_sharepoint_service, "doc123", "drive123")
        
        assert result["access_level"] == "public"

    @patch('requests.get')
    def test_restricted_access_level(self, mock_get, mock_sharepoint_service):
        """Test detection of restricted access level"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "value": [
                {
                    "grantedToV2": {
                        "user": {"email": "user1@company.com"}
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_document_permissions(mock_sharepoint_service, "doc123", "drive123")
        
        assert result["access_level"] == "restricted"


class TestProcessPermissionEntry:
    """Test cases for process_permission_entry function"""

    @pytest.fixture
    def result_dict(self):
        """Create a result dictionary for testing"""
        return {
            "users": set(),
            "groups": set(),
            "access_level": "private",
            "inheritance": False,
            "sharing_links": []
        }

    def test_process_link_permission(self, result_dict):
        """Test processing link-based permission"""
        permission = {
            "link": {
                "scope": "organization",
                "type": "edit",
                "webUrl": "https://example.com/link"
            }
        }
        
        process_permission_entry(permission, result_dict, None, "token")
        
        assert result_dict["access_level"] == "organization"
        assert len(result_dict["sharing_links"]) == 1
        assert result_dict["sharing_links"][0]["scope"] == "organization"

    def test_process_user_permission(self, result_dict):
        """Test processing user-based permission"""
        permission = {
            "grantedToV2": {
                "user": {"email": "user@company.com"}
            }
        }
        
        process_permission_entry(permission, result_dict, None, "token")
        
        assert "user@company.com" in result_dict["users"]

    def test_process_inherited_permission(self, result_dict):
        """Test processing inherited permission"""
        permission = {
            "inheritedFrom": {"id": "parent-folder"}
        }
        
        process_permission_entry(permission, result_dict, None, "token")
        
        assert result_dict["inheritance"] is True

    def test_process_multiple_identities(self, result_dict):
        """Test processing multiple granted identities"""
        permission = {
            "grantedToIdentities": [
                {"user": {"email": "user1@company.com"}},
                {"group": {"email": "group1@company.com"}}
            ]
        }
        
        process_permission_entry(permission, result_dict, None, "token")
        
        assert "user1@company.com" in result_dict["users"]
        assert "group1@company.com" in result_dict["groups"]


class TestProcessGrantedEntity:
    """Test cases for process_granted_entity function"""

    @pytest.fixture
    def result_dict(self):
        """Create a result dictionary for testing"""
        return {
            "users": set(),
            "groups": set()
        }

    def test_process_user_entity(self, result_dict):
        """Test processing user entity"""
        entity = {
            "user": {"email": "user@company.com"}
        }
        
        process_granted_entity(entity, result_dict, None, "token")
        
        assert "user@company.com" in result_dict["users"]

    def test_process_site_group_entity(self, result_dict):
        """Test processing site group entity"""
        entity = {
            "siteGroup": {
                "displayName": "Site Owners",
                "id": "group123"
            }
        }
        
        process_granted_entity(entity, result_dict, None, "token")
        
        assert "Site Owners" in result_dict["groups"]

    @patch('app.services.document_permission.get_group_details')
    def test_process_group_entity_with_details(self, mock_get_details, result_dict):
        """Test processing group entity with additional details"""
        entity = {
            "group": {
                "id": "group123",
                "displayName": "Test Group"
            }
        }
        
        mock_get_details.return_value = {
            "mail": "testgroup@company.com"
        }
        
        process_granted_entity(entity, result_dict, None, "token")
        
        assert "testgroup@company.com" in result_dict["groups"]
        mock_get_details.assert_called_once_with("group123", "token")

    def test_process_group_entity_with_email(self, result_dict):
        """Test processing group entity with direct email"""
        entity = {
            "group": {
                "email": "group@company.com",
                "displayName": "Test Group"
            }
        }
        
        process_granted_entity(entity, result_dict, None, "token")
        
        assert "group@company.com" in result_dict["groups"]

    def test_process_application_entity(self, result_dict):
        """Test processing application entity (should not add to users/groups)"""
        entity = {
            "application": {
                "id": "app123",
                "displayName": "Test App"
            }
        }
        
        process_granted_entity(entity, result_dict, None, "token")
        
        # Applications should not be added to users or groups
        assert len(result_dict["users"]) == 0
        assert len(result_dict["groups"]) == 0

    def test_process_empty_entity(self, result_dict):
        """Test processing empty entity"""
        entity = {}
        
        process_granted_entity(entity, result_dict, None, "token")
        
        assert len(result_dict["users"]) == 0
        assert len(result_dict["groups"]) == 0


class TestGetGroupDetails:
    """Test cases for get_group_details function"""

    @patch('requests.get')
    def test_successful_group_details(self, mock_get):
        """Test successful retrieval of group details"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "id": "group123",
            "displayName": "Test Group",
            "mail": "testgroup@company.com"
        }
        mock_get.return_value = mock_response
        
        result = get_group_details("group123", "token")
        
        assert result["mail"] == "testgroup@company.com"
        assert result["displayName"] == "Test Group"

    @patch('requests.get')
    def test_group_details_api_error(self, mock_get):
        """Test API error handling in group details"""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        result = get_group_details("group123", "token")
        
        assert result == {}

    @patch('requests.get')
    def test_group_details_http_error(self, mock_get):
        """Test HTTP error handling in group details"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        result = get_group_details("group123", "token")
        
        assert result == {}