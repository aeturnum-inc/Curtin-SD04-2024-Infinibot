# tests/unit/core/test_auth.py
import pytest
import json
import base64
import asyncio
from unittest.mock import patch, MagicMock
from fastapi import Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import (
    get_current_user,
    validate_sharepoint_token,
    extract_user_from_claim,
    is_valid_email,
    check_user_permissions,
    AuthenticationError,
    handle_auth_error
)
from app.core.config import settings


class TestGetCurrentUser:
    """Test cases for get_current_user function"""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object"""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.url = MagicMock()
        request.url.path = "/test"
        return request

    @pytest.fixture
    def mock_credentials(self):
        """Create mock HTTP credentials"""
        return HTTPAuthorizationCredentials(
            scheme="bearer",
            credentials="mock_token"
        )

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', True)
    async def test_dev_mode_with_valid_headers(self, mock_request):
        """Test authentication in dev mode with valid headers"""
        mock_request.headers = {
            "X-Dev-Mode": "true",
            "X-User-Email": "test@example.com",
            "X-SharePoint-User": "Test User"
        }
        
        result = await get_current_user(mock_request, None)
        
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["is_authenticated"] is True
        assert result["dev_mode"] is True

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', True)
    async def test_dev_mode_with_default_email(self, mock_request):
        """Test dev mode with default email when header is missing"""
        mock_request.headers = {"X-Dev-Mode": "true"}
        
        result = await get_current_user(mock_request, None)
        
        assert result["email"] == "dev@example.com"
        assert result["dev_mode"] is True

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', True)
    async def test_dev_mode_with_invalid_email(self, mock_request):
        """Test dev mode with invalid email format"""
        mock_request.headers = {
            "X-Dev-Mode": "true",
            "X-User-Email": "invalid-email"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, None)
        
        assert exc_info.value.status_code == 401
        assert "Invalid dev mode email format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', False)
    async def test_dev_mode_disabled_ignores_header(self, mock_request):
        """Test that dev mode header is ignored when DEV_MODE is False"""
        mock_request.headers = {
            "X-Dev-Mode": "true",
            "X-User-Email": "test@example.com"
        }
        
        # When DEV_MODE is False, the X-Dev-Mode header should be ignored
        # but X-User-Email header is still processed as a regular email header
        result = await get_current_user(mock_request, None)
        
        # Should authenticate using the email header, but NOT in dev mode
        assert result["email"] == "test@example.com"
        assert result["is_authenticated"] is True
        assert result["dev_mode"] is False  

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', False)
    async def test_production_with_sharepoint_user_header(self, mock_request):
        """Test production mode with SharePoint user header"""
        mock_request.headers = {
            "X-SharePoint-User": "i:0#.f|membership|test@example.com"
        }
        
        result = await get_current_user(mock_request, None)
        
        assert result["email"] == "test@example.com"
        assert result["is_authenticated"] is True
        assert result["dev_mode"] is False

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', False)
    async def test_production_with_simple_user_header(self, mock_request):
        """Test production mode with simple user header (no pipes)"""
        mock_request.headers = {
            "X-SharePoint-User": "test@example.com"
        }
        
        result = await get_current_user(mock_request, None)
        
        assert result["email"] == "test@example.com"
        assert result["dev_mode"] is False

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', False)
    async def test_production_with_email_header(self, mock_request):
        """Test production mode with direct email header"""
        mock_request.headers = {
            "X-User-Email": "test@example.com",
            "X-User-Name": "Test User"
        }
        
        result = await get_current_user(mock_request, None)
        
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["dev_mode"] is False

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', False)
    @patch('app.core.auth.validate_sharepoint_token')
    async def test_production_with_jwt_token(self, mock_validate, mock_request, mock_credentials):
        """Test production mode with JWT token"""
        mock_request.headers = {}
        mock_validate.return_value = {
            "email": "test@jwt.com",
            "name": "JWT User"
        }
        
        result = await get_current_user(mock_request, mock_credentials)
        
        assert result["email"] == "test@jwt.com"
        assert result["name"] == "JWT User"
        assert result["dev_mode"] is False
        mock_validate.assert_called_once_with("mock_token")

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', False)
    @patch('app.core.auth.validate_sharepoint_token')
    async def test_production_with_invalid_jwt(self, mock_validate, mock_request, mock_credentials):
        """Test production mode with invalid JWT token"""
        mock_request.headers = {}
        mock_validate.side_effect = ValueError("Invalid token")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "Invalid authentication token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch.object(settings, 'DEV_MODE', False)
    async def test_production_no_auth_provided(self, mock_request):
        """Test production mode when no authentication is provided"""
        mock_request.headers = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, None)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in str(exc_info.value.detail)


class TestValidateSharepointToken:
    """Test cases for JWT token validation"""

    def create_mock_jwt(self, payload):
        """Create a mock JWT token with given payload"""
        header = {"alg": "HS256", "typ": "JWT"}
        
        # Encode header and payload
        header_b64 = base64.b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature_b64 = "mock_signature"
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def test_validate_valid_token(self):
        """Test validation of a valid JWT token"""
        payload = {
            "aud": "test-audience",
            "iss": "test-issuer",
            "exp": 9999999999,  # Far future
            "email": "test@example.com",
            "name": "Test User"
        }
        token = self.create_mock_jwt(payload)
        
        result = validate_sharepoint_token(token)
        
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"

    def test_validate_expired_token(self):
        """Test validation of an expired JWT token"""
        payload = {
            "aud": "test-audience",
            "iss": "test-issuer",
            "exp": 1000000000,  # Past timestamp
            "email": "test@example.com"
        }
        token = self.create_mock_jwt(payload)
        
        with pytest.raises(ValueError) as exc_info:
            validate_sharepoint_token(token)
        
        assert "expired" in str(exc_info.value)

    def test_validate_malformed_token(self):
        """Test validation of a malformed JWT token"""
        malformed_token = "not.a.valid.jwt.token"
        
        with pytest.raises(ValueError) as exc_info:
            validate_sharepoint_token(malformed_token)
        
        assert "Invalid JWT format" in str(exc_info.value)

    def test_validate_token_missing_claims(self):
        """Test validation of token missing required claims"""
        payload = {
            "email": "test@example.com"
            # Missing aud, iss, exp
        }
        token = self.create_mock_jwt(payload)
        
        # Should not raise an error, but should log warnings
        result = validate_sharepoint_token(token)
        assert result["email"] == "test@example.com"

    def test_validate_token_invalid_base64(self):
        """Test validation of token with invalid base64 encoding"""
        invalid_token = "invalid.base64!@#.signature"
        
        with pytest.raises(ValueError):
            validate_sharepoint_token(invalid_token)


class TestExtractUserFromClaim:
    """Test cases for extracting user information from JWT claims"""

    def test_extract_with_email_claim(self):
        """Test extraction when email claim is present"""
        payload = {
            "email": "test@example.com",
            "name": "Test User"
        }
        
        email, name = extract_user_from_claim(payload)
        
        assert email == "test@example.com"
        assert name == "Test User"

    def test_extract_with_upn_claim(self):
        """Test extraction when UPN claim is present"""
        payload = {
            "upn": "test@upn.com",
            "given_name": "Test",
            "family_name": "User"
        }
        
        email, name = extract_user_from_claim(payload)
        
        assert email == "test@upn.com"
        assert name == "Test"

    def test_extract_with_fallback_claims(self):
        """Test extraction with fallback to unique_name and preferred_username"""
        payload = {
            "unique_name": "test@unique.com",
            "preferred_username": "test@preferred.com"
        }
        
        email, name = extract_user_from_claim(payload)
        
        # Should prefer unique_name over preferred_username
        assert email == "test@unique.com"
        assert name is None

    def test_extract_with_no_claims(self):
        """Test extraction when no relevant claims are present"""
        payload = {
            "sub": "some-subject-id"
        }
        
        email, name = extract_user_from_claim(payload)
        
        assert email is None
        assert name is None


class TestIsValidEmail:
    """Test cases for email validation"""

    def test_valid_emails(self):
        """Test various valid email formats"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@domain.com",
            "user123@domain123.com"
        ]
        
        for email in valid_emails:
            assert is_valid_email(email) is True

    def test_invalid_emails(self):
        """Test various invalid email formats"""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "",
            None
        ]
        
        for email in invalid_emails:
            assert is_valid_email(email) is False


class TestCheckUserPermissions:
    """Test cases for user permission checking"""

    def test_unauthenticated_user(self):
        """Test permission check for unauthenticated user"""
        user_context = {"is_authenticated": False}
        
        result = check_user_permissions(user_context)
        
        assert result is False

    def test_dev_mode_user(self):
        """Test permission check for user in dev mode"""
        user_context = {
            "is_authenticated": True,
            "dev_mode": True
        }
        
        result = check_user_permissions(user_context)
        
        assert result is True

    def test_authenticated_production_user(self):
        """Test permission check for authenticated production user"""
        user_context = {
            "is_authenticated": True,
            "dev_mode": False
        }
        
        result = check_user_permissions(user_context)
        
        # Currently allows all authenticated users
        assert result is True

    def test_missing_context(self):
        """Test permission check with missing context"""
        result = check_user_permissions({})
        
        assert result is False


class TestAuthenticationError:
    """Test cases for AuthenticationError and error handling"""

    def test_create_auth_error(self):
        """Test creating AuthenticationError"""
        error = AuthenticationError("Test error", 403)
        
        assert error.message == "Test error"
        assert error.status_code == 403
        assert str(error) == "Test error"

    def test_default_status_code(self):
        """Test AuthenticationError with default status code"""
        error = AuthenticationError("Test error")
        
        assert error.status_code == 401

    def test_handle_auth_error(self):
        """Test converting AuthenticationError to HTTPException"""
        error = AuthenticationError("Test error", 403)
        
        http_exception = handle_auth_error(error)
        
        assert http_exception.status_code == 403
        assert http_exception.detail == "Test error"


@pytest.mark.asyncio
class TestAuthMiddlewareIntegration:
    """Integration tests for auth middleware with different scenarios"""

    @pytest.fixture
    def mock_request_factory(self):
        """Factory for creating mock requests with different headers"""
        def _create_request(headers=None, client_host="127.0.0.1"):
            request = MagicMock(spec=Request)
            request.headers = headers or {}
            request.client = MagicMock()
            request.client.host = client_host
            request.url = MagicMock()
            request.url.path = "/test"
            return request
        return _create_request

    @patch.object(settings, 'DEV_MODE', True)
    async def test_complete_dev_flow(self, mock_request_factory):
        """Test complete authentication flow in dev mode"""
        request = mock_request_factory({
            "X-Dev-Mode": "true",
            "X-User-Email": "developer@test.com",
            "X-SharePoint-User": "Developer"
        })
        
        result = await get_current_user(request, None)
        
        assert result["email"] == "developer@test.com"
        assert result["name"] == "Developer"
        assert result["dev_mode"] is True
        assert result["is_authenticated"] is True

    @patch.object(settings, 'DEV_MODE', False)
    async def test_complete_production_flow_with_headers(self, mock_request_factory):
        """Test complete authentication flow in production with headers"""
        request = mock_request_factory({
            "X-SharePoint-User": "i:0#.f|membership|prod@company.com",
            "X-User-Name": "Production User"
        })
        
        result = await get_current_user(request, None)
        
        assert result["email"] == "prod@company.com"
        assert result["name"] == "Production User"
        assert result["dev_mode"] is False
        assert result["is_authenticated"] is True

    @patch.object(settings, 'DEV_MODE', False)
    @patch('app.core.auth.validate_sharepoint_token')
    async def test_complete_production_flow_with_jwt(
        self, mock_validate, mock_request_factory
    ):
        """Test complete authentication flow in production with JWT"""
        request = mock_request_factory({})
        credentials = HTTPAuthorizationCredentials(
            scheme="bearer",
            credentials="valid.jwt.token"
        )
        
        mock_validate.return_value = {
            "email": "jwt@company.com",
            "name": "JWT User",
            "upn": "jwt@company.com"
        }
        
        result = await get_current_user(request, credentials)
        
        assert result["email"] == "jwt@company.com"
        assert result["name"] == "JWT User"
        assert result["dev_mode"] is False
        assert result["is_authenticated"] is True