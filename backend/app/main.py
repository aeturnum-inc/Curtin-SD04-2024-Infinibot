from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.events import startup_event, shutdown_event
from app.api.routes import router as api_router , webhook
from app.core.auth import get_current_user

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event handlers
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)

#  middleware to log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    path = request.url.path
    user_agent = request.headers.get("user-agent", "Unknown")
    auth_header = "Present" if request.headers.get("authorization") else "None"
    dev_mode = request.headers.get("x-dev-mode", "false").lower() == "true"
    
    print(f"Request: {request.method} {path}, Auth: {auth_header}, DevMode: {dev_mode}")
    
    response = await call_next(request)
    
    print(f"Response: {request.method} {path}, Status: {response.status_code}")
    return response

# Include routers
app.include_router(api_router, prefix="/api")
app.include_router(webhook.router, prefix="/api")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "LangGraph Agent Server", "status": "healthy", "version": settings.PROJECT_VERSION}

@app.get("/auth/me")
async def get_me(current_user = Depends(get_current_user)):
    """Get authenticated user information"""
    return {
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "authenticated": current_user.get("is_authenticated", False),
        "dev_mode": current_user.get("dev_mode", False),
    }