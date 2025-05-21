import traceback
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.database import get_mongodb_client
from app.core.auth import get_current_user
from app.models.schemas import ChatRequest, ChatResponse, NewChatResponse, DocumentSource
from app.services.agent import call_agent
from pymongo import MongoClient
from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/", response_model=NewChatResponse)
def start_chat(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    client: MongoClient = Depends(get_mongodb_client)
):
    """
    Start a new chat conversation.
    
    Args:
        request: The chat request
        current_user: Authenticated user information
        client: MongoDB client instance
        
    Returns:
        NewChatResponse: The response with thread ID and sources
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Generate a unique thread ID based on timestamp
    thread_id = str(int(datetime.now().timestamp()))
    
    try:
        # Log user information for auditing
        user_email = current_user.get("email", "anonymous")
        print(f"Starting new chat for user: {user_email}")
        
        # Store user permissions for this thread in MongoDB
        if not current_user.get("dev_mode", False):
            try:
                # Store user info in the threads collection for future reference
                db = client[settings.DB_NAME]
                threads_collection = db["threads"]
                
                threads_collection.insert_one({
                    "thread_id": thread_id,
                    "user_email": user_email,
                    "user_name": current_user.get("name", ""),
                    "created_at": datetime.now(),
                    "last_activity": datetime.now()
                })
                
                print(f"Stored user context for thread {thread_id}")
            except Exception as e:
                print(f"Error storing user context: {e}")
        
        # Call the agent to get a response
        response_data = call_agent(
            client,
            request.message,
            thread_id,
            user_context=current_user
        )
        
        # Extract content and sources
        if isinstance(response_data, dict):
            content = response_data.get("content", "")
            sources = response_data.get("sources", [])
            return NewChatResponse(threadId=thread_id, response=content, sources=sources)
        else:
            # Handle legacy format (string response)
            return NewChatResponse(threadId=thread_id, response=response_data)
            
    except Exception as e:
        error_detail = f"Error starting conversation: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}", response_model=ChatResponse)
def continue_chat(
    thread_id: str,
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    client: MongoClient = Depends(get_mongodb_client)
):
    """
    Continue an existing chat conversation.
    
    Args:
        thread_id: The thread ID
        request: The chat request
        current_user: Authenticated user information
        client: MongoDB client instance
        
    Returns:
        ChatResponse: The agent's response with sources
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    try:
        # Log user information for auditing
        user_email = current_user.get("email", "anonymous")
        print(f"Continuing chat {thread_id} for user: {user_email}")
        
        # Verify this user has permission to access this thread
        if not current_user.get("dev_mode", False):
            try:
                # Check thread ownership in the threads collection
                db = client[settings.DB_NAME]
                threads_collection = db["threads"]
                
                thread_info = threads_collection.find_one({"thread_id": thread_id})
                if thread_info:
                    thread_owner = thread_info.get("user_email", "")
                    # If thread owner doesn't match current user
                    if thread_owner and thread_owner.lower() != user_email.lower():
                        print(f"User {user_email} attempted to access thread {thread_id} owned by {thread_owner}")
                        raise HTTPException(
                            status_code=403, 
                            detail="You don't have permission to access this conversation thread"
                        )
                    
                    # Update last activity timestamp
                    threads_collection.update_one(
                        {"thread_id": thread_id},
                        {"$set": {"last_activity": datetime.now()}}
                    )
                else:
                    # If thread doesn't exist in our DB, create it now
                    threads_collection.insert_one({
                        "thread_id": thread_id,
                        "user_email": user_email,
                        "user_name": current_user.get("name", ""),
                        "created_at": datetime.now(),
                        "last_activity": datetime.now()
                    })
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                print(f"Error verifying thread access: {e}")
        
        # Call the agent to get a response, passing user context for permission checks
        response_data = call_agent(
            client,
            request.message,
            thread_id,
            user_context=current_user
        )
        
        # Extract content and sources
        if isinstance(response_data, dict):
            content = response_data.get("content", "")
            sources = response_data.get("sources", [])
            return ChatResponse(response=content, sources=sources)
        else:
            # Handle legacy format (string response)
            return ChatResponse(response=response_data)
            
    except Exception as e:
        print(f"Error in chat: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Internal server error")