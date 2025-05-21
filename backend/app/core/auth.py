"""
Authentication middleware and utilities for validating SharePoint requests.
"""
import base64
import json
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

# Initialize security scheme
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Authenticate user from SharePoint context or development headers.
    
    Args:
        request: FastAPI request object
        credentials: Optional HTTP Bearer token
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If authentication fails
    """
    # Log all relevant headers for debugging
    logger.info(f"Authentication attempt with headers: {dict(request.headers)}")
    
    # CRITICAL: Dev mode can only be enabled if BOTH:
    # 1. The environment variable DEV_MODE is True
    # 2. The X-Dev-Mode header is True
    dev_mode_header = request.headers.get("X-Dev-Mode", "").lower() == "true"
    dev_mode_enabled = settings.DEV_MODE and dev_mode_header
    
    logger.info(f"Dev mode check: DEV_MODE={settings.DEV_MODE}, X-Dev-Mode header={dev_mode_header}, Final dev_mode={dev_mode_enabled}")
    
    # If in dev mode, use user info from headers
    if dev_mode_enabled:
        logger.info("Using development authentication mode")
        user_email = request.headers.get("X-User-Email", "dev@example.com")
        
        # Validate dev email format
        if not user_email or "@" not in user_email:
            logger.error(f"Invalid dev mode email: {user_email}")
            raise HTTPException(status_code=401, detail="Invalid dev mode email format")
        
        logger.info(f"Dev mode authentication successful for: {user_email}")
        return {
            "email": user_email,
            "name": request.headers.get("X-SharePoint-User", "Developer"),
            "is_authenticated": True,
            "dev_mode": True
        }
    
    # In production mode, get user from SharePoint context
    # Check various SharePoint headers that might contain user info
    user_email = None
    user_name = None
    
    # Check X-SharePoint-User header (common in SPFx applications)
    sharepoint_user = request.headers.get("X-SharePoint-User")
    if sharepoint_user:
        # Extract email from SharePoint user string (format might be "i:0#.f|membership|user@domain.com")
        if "|" in sharepoint_user:
            user_email = sharepoint_user.split("|")[-1]
        else:
            user_email = sharepoint_user
        logger.info(f"Found SharePoint user header: {user_email}")
    
    # Check for direct email headers
    if not user_email:
        user_email = request.headers.get("X-User-Email")
        logger.info(f"Found X-User-Email header: {user_email}")
    
    # Check for user name
    user_name = request.headers.get("X-User-Name") or request.headers.get("X-SharePoint-DisplayName")
    
    # If no headers, try to extract from JWT token
    if not user_email and credentials:
        try:
            logger.info("No user headers found, attempting JWT validation")
            # Validate the SharePoint JWT token
            payload = validate_sharepoint_token(credentials.credentials)
            
            # Extract user info from JWT claims
            user_email = (
                payload.get("email") or 
                payload.get("upn") or 
                payload.get("unique_name") or
                payload.get("preferred_username")
            )
            user_name = (
                payload.get("name") or 
                payload.get("given_name") or
                payload.get("family_name")
            )
            
            logger.info(f"JWT validation successful for: {user_email}")
            
        except Exception as e:
            logger.error(f"JWT validation failed: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Invalid authentication token: {str(e)}")
    
    # If still no user email, reject the request
    if not user_email:
        logger.error("No valid user authentication found")
        raise HTTPException(
            status_code=401,
            detail="Authentication required. No valid SharePoint context or token found."
        )
    
    # Clean up email format
    user_email = user_email.strip().lower()
    
    # Return user info with dev_mode=False for production users
    user_info = {
        "email": user_email,
        "name": user_name or user_email.split("@")[0],
        "is_authenticated": True,
        "dev_mode": False  # Always False in production
    }
    
    logger.info(f"Production authentication successful for: {user_email}")
    return user_info


def validate_sharepoint_token(token: str) -> Dict[str, Any]:
    """
    Validate SharePoint JWT token.
    
    This is a basic implementation. In a production scenario, you should:
    1. Verify the token signature using Azure AD public keys
    2. Validate the claims (aud, iss, exp, etc.)
    3. Check token expiration
    
    Args:
        token: JWT token from SharePoint
        
    Returns:
        Dict with token claims
    """
    try:
        # Split token into parts
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format - expected 3 parts")
        
        # Decode the payload (middle part)
        payload_base64 = parts[1]
        
        # Add padding if necessary
        payload_base64 += "=" * ((4 - len(payload_base64) % 4) % 4)
        
        # Decode base64
        payload_bytes = base64.b64decode(payload_base64)
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        # Basic validation - check if token has required claims
        required_claims = ["aud", "iss", "exp"]
        missing_claims = [claim for claim in required_claims if claim not in payload]
        
        if missing_claims:
            logger.warning(f"JWT missing required claims: {missing_claims}")
        
        # Check expiration
        import time
        current_time = int(time.time())
        exp = payload.get("exp", 0)
        
        if exp and current_time > exp:
            raise ValueError("JWT token has expired")
        
        logger.info(f"JWT validation successful. Subject: {payload.get('sub', 'unknown')}")
        return payload
        
    except Exception as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise ValueError(f"Invalid JWT token: {str(e)}")


# Additional helper functions for enhanced authentication

def extract_user_from_claim(token_payload: Dict[str, Any]) -> tuple[str, str]:
    """
    Extract user email and name from JWT claims.
    
    Args:
        token_payload: Decoded JWT payload
        
    Returns:
        Tuple of (email, name)
    """
    email = (
        token_payload.get("email") or
        token_payload.get("upn") or
        token_payload.get("unique_name") or
        token_payload.get("preferred_username")
    )
    
    name = (
        token_payload.get("name") or
        token_payload.get("given_name") or
        token_payload.get("family_name")
    )
    
    return email, name


def is_valid_email(email: str) -> bool:
    """
    Basic email validation.
    
    Args:
        email: Email string to validate
        
    Returns:
        bool: True if valid email format
    """
    if not email:
        return False
    
    # Basic email regex
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def check_user_permissions(user_context: Dict[str, Any], required_permissions: list = None) -> bool:
    """
    Check if user has required permissions.
    
    Args:
        user_context: User context from authentication
        required_permissions: List of required permissions
        
    Returns:
        bool: True if user has required permissions
    """
    if not user_context.get("is_authenticated", False):
        return False
    
    # In dev mode, allow everything
    if user_context.get("dev_mode", False):
        return True
    
    # Add your permission checking logic here
    # For now, all authenticated users have access
    return True


# Middleware for request logging
async def log_authentication_attempt(request: Request):
    """
    Log authentication attempts for security monitoring.
    
    Args:
        request: FastAPI request object
    """
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    path = request.url.path
    
    logger.info(f"Auth attempt: IP={client_ip}, Path={path}, UserAgent={user_agent}")


# Error handling for authentication failures
class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def handle_auth_error(error: AuthenticationError) -> HTTPException:
    """
    Convert authentication error to HTTP exception.
    
    Args:
        error: AuthenticationError instance
        
    Returns:
        HTTPException: Formatted HTTP exception
    """
    logger.error(f"Authentication error: {error.message}")
    return HTTPException(status_code=error.status_code, detail=error.message)



def is_user_in_organization_domain(user_email: str) -> bool:
    """
    Check if user email belongs to organization domain.
    Uses configurable organization domains from environment.
    
    Args:
        user_email: User's email address
        
    Returns:
        bool: True if user is in organization domain
    """
    if not user_email or "@" not in user_email:
        return False
    
    user_domain = user_email.split("@")[1].lower()
    
    org_domains = get_org_domains()
    
    return user_domain in org_domains

def validate_user_permissions(user_context: Dict[str, Any], required_permission: str = None) -> bool:
    """
    Validate user permissions for accessing resources.
    
    Args:
        user_context: User context from authentication
        required_permission: Optional specific permission required
        
    Returns:
        bool: True if user has required permissions
    """
    if not user_context.get("is_authenticated", False):
        return False
    
    if user_context.get("dev_mode", False):
        logger.info("Dev mode enabled - allowing all permissions")
        return True
    
    user_email = user_context.get("email", "")
    if not is_user_in_organization_domain(user_email):
        logger.warning(f"User {user_email} not in organization domain")
        return False
    
   
    
    return True