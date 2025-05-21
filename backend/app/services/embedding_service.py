"""
Service for text embeddings from different providers.
"""
from typing import List

from langchain_openai import OpenAIEmbeddings
from langchain_openai.embeddings import AzureOpenAIEmbeddings

from app.core.config import settings


def get_embedding_model():
    """
    Get the appropriate embedding model based on configuration.
    
    Returns:
        An embedding model instance
    """
    if settings.LLM_PROVIDER == "azure" and settings.AZURE_API_KEY and settings.AZURE_EMBEDDING_DEPLOYMENT_NAME:
        print("Using Azure OpenAI Embeddings")
        return AzureOpenAIEmbeddings(
            azure_deployment=settings.AZURE_EMBEDDING_DEPLOYMENT_NAME,
            azure_endpoint=settings.AZURE_API_BASE,
            api_key=settings.AZURE_API_KEY,
            api_version=settings.AZURE_API_VERSION,
        )
    else:
        print("Using OpenAI Embeddings")
        return OpenAIEmbeddings()