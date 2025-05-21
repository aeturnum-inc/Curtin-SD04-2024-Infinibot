from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.core.auth import get_current_user
from app.models.schemas import PermissionCheckRequest, PermissionCheckResponse
from app.services.sharepoint_service import SharePointService
from app.core.config import settings

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.post("/check", response_model=PermissionCheckResponse)
async def check_document_permission(
    request: PermissionCheckRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Check if a user has permission to access a document.
    
    Args:
        request: PermissionCheckRequest containing user_email and document_id
        current_user: Authenticated user information
        
    Returns:
        PermissionCheckResponse: The result of the permission check
    """
    # Ensure the requesting user has admin rights or is checking their own permissions
    if not current_user.get("dev_mode", False) and request.user_email.lower() != current_user.get("email", "").lower():
        raise HTTPException(
            status_code=403,
            detail="You can only check permissions for your own account"
        )
    
    try:
        # Initialize SharePoint service
        sharepoint_service = SharePointService()
        
        # Get drives
        token = sharepoint_service.get_access_token()
        drives_endpoint = f"https://graph.microsoft.com/v1.0/sites/{settings.SITE_ID}/drives"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get drive ID
        drives_response = requests.get(drives_endpoint, headers=headers)
        drives_response.raise_for_status()
        drives = drives_response.json().get("value", [])
        
        if not drives:
            return PermissionCheckResponse(
                has_access=False,
                reason="No document libraries found in SharePoint site"
            )
        
        drive_id = drives[0]["id"]
        
        # Check permission
        has_permission = sharepoint_service.check_user_permission(
            document_id=request.document_id,
            user_email=request.user_email,
            drive_id=drive_id
        )
        
        if has_permission:
            return PermissionCheckResponse(
                has_access=True
            )
        else:
            return PermissionCheckResponse(
                has_access=False,
                reason="User does not have permissions to access this document"
            )
            
    except Exception as e:
        print(f"Error checking document permission: {e}")
        return PermissionCheckResponse(
            has_access=False,
            reason=f"Error checking permissions: {str(e)}"
        )