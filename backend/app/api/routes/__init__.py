"""Routes module for API endpoints."""
from fastapi import APIRouter

from app.api.routes import chat
from app.api.routes import permissions

router = APIRouter()
router.include_router(chat.router)
router.include_router(permissions.router)