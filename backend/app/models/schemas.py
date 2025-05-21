from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Request model for chat endpoints.
    """
    message: str = Field(..., description="The user message")

class DocumentSource(BaseModel):
    """
    Source information for a document referenced in the response.
    """
    source: str = Field(..., description="The name of the document")
    webUrl: str = Field(..., description="The web URL of the document")
    docId: str = Field(..., description="The document ID")


class ChatResponse(BaseModel):
    """
    Response model for chat endpoints.
    """
    response: str = Field(..., description="The assistant's response")
    sources: Optional[List[DocumentSource]] = Field(default=None, description="Document sources referenced in the response")


class NewChatResponse(ChatResponse):
    """
    Response model for starting a new chat.
    """
    threadId: str = Field(..., description="The thread ID for continuing the conversation")



class DocumentPermissions(BaseModel):
    """
    Model for document permissions.
    """
    authorized_users: List[str] = Field(default_factory=list, description="List of users who can access this document")
    authorized_groups: List[str] = Field(default_factory=list, description="List of groups who can access this document")
    access_level: str = Field(default="private", description="Access level: private, organization, or public")


class DocumentMetadata(BaseModel):
    """
    Metadata for documents returned from SharePoint.
    """
    id: str
    name: str
    webUrl: str
    lastModified: str
    permissions: Optional[DocumentPermissions] = None


class Document(BaseModel):
    """
    Document model.
    """
    id: str
    name: str
    webUrl: str
    lastModified: str
    content: Optional[str] = None
    permissions: Optional[DocumentPermissions] = None


class SearchResult(BaseModel):
    """
    Search result model.
    """
    page_content: str
    metadata: Dict[str, Any]
    score: float


class SearchResults(BaseModel):
    """
    Multiple search results model.
    """
    results: List[SearchResult]


class ThreadInfo(BaseModel):
    """
    Model for conversation thread information.
    """
    thread_id: str
    user_email: str
    user_name: Optional[str] = None
    created_at: str
    last_activity: str


class PermissionCheckRequest(BaseModel):
    """
    Request model for permission check endpoint.
    """
    user_email: str
    document_id: str


class PermissionCheckResponse(BaseModel):
    """
    Response model for permission check endpoint.
    """
    has_access: bool
    reason: Optional[str] = None