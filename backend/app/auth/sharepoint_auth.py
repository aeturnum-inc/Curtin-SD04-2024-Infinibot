# app/auth/sharepoint_auth.py
from fastapi import Request, HTTPException, Depends, Header
from typing import Optional
import logging
from app.models.database import User
from app.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

async def get_current_user_from_sharepoint(
    request: Request,
    x_sharepoint_user: Optional[str] = Header(None, alias="X-SharePoint-User"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_dev_mode: Optional[str] = Header(None, alias="X-Dev-Mode"),
    db: Session = Depends(get_db)
) -> User:
    """
    Authentication with SharePoint headers and development fallback.
    """
    try:
        # Log headers for debugging
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # First try SharePoint headers
        if x_sharepoint_user:
            email = x_sharepoint_user.split('|')[-1] if '|' in x_sharepoint_user else x_sharepoint_user
            logger.info(f"Using SharePoint user identity: {email}")
        # Then try custom email header with dev mode
        elif x_user_email and x_dev_mode == "true":
            email = x_user_email
            logger.info(f"Using development mode with email: {email}")
        else:
            # Print all received headers for debugging
            for header_name, header_value in request.headers.items():
                logger.info(f"Header - {header_name}: {header_value}")
            
            logger.error("No user identity headers found")
            raise HTTPException(status_code=401, detail="Authentication failed: No user identity provided")
        
        # Get or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.info(f"Creating new user for email: {email}")
            user = User(email=email)
            db.add(user)
            db.commit()
        
        logger.info(f"Authentication successful for user: {email}")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected authentication error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )