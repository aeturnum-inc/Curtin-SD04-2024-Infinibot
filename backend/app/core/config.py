import os
from typing import List
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # Project info
    PROJECT_NAME: str = "LangGraph Agent API"
    PROJECT_DESCRIPTION: str = "FastAPI backend for document search and AI assistance using LangGraph"
    PROJECT_VERSION: str = "0.1.0"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Authentication
    DEV_MODE: bool = os.getenv("DEV_MODE", "false").lower() == "true"
    AUTH_REQUIRED: bool = os.getenv("AUTH_REQUIRED", "true").lower() == "true"
    SHAREPOINT_TENANT_URL: str = os.getenv("SHAREPOINT_TENANT_URL", "")
    
    # MongoDB
    MONGODB_ATLAS_URI: str = os.getenv("MONGODB_ATLAS_URI", "")
    
    # API keys for LLM services
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Azure/SharePoint config
    TENANT_ID: str = os.getenv("TENANT_ID", "")
    CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")
    SITE_ID: str = os.getenv("SITE_ID", "")
    
    # Webhook
    WEBHOOK_CALLBACK_URL: str = os.getenv("WEBHOOK_CALLBACK_URL", "")

    # Organization domains for permission checking

    ORG_DOMAINS: str = os.getenv("ORG_DOMAINS", "microweb.global,microwebglobal.onmicrosoft.com")

    
    # Database
    DB_NAME: str = "knowledge_base"
    COLLECTION_NAME: str = "documents"
    
    # Model config
    LLM_MODEL_NAME: str = "claude-3-5-sonnet-20241022"
    LLM_TEMPERATURE: float = 0.0
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "azure")  # Options: openai, anthropic, azure
    
    # Azure OpenAI specific config (if using Azure)
    AZURE_API_KEY: str = os.getenv("AZURE_API_KEY", "")
    AZURE_API_BASE: str = os.getenv("AZURE_API_BASE", "")
    AZURE_API_VERSION: str = os.getenv("AZURE_API_VERSION", "2023-05-15")
    AZURE_DEPLOYMENT_NAME: str = os.getenv("AZURE_DEPLOYMENT_NAME", "")
    AZURE_EMBEDDING_DEPLOYMENT_NAME: str = os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME", "")
    
    model_config = ConfigDict(env_file=".env", case_sensitive=True)


# Create settings instance
settings = Settings()

# Log critical settings availability at module level
for key, value in {
    "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    "ANTHROPIC_API_KEY": settings.ANTHROPIC_API_KEY,
    "MONGODB_ATLAS_URI": settings.MONGODB_ATLAS_URI,
    "DEV_MODE": settings.DEV_MODE,
}.items():
    print(f"{key} set: {'YES' if value else 'NO'}")