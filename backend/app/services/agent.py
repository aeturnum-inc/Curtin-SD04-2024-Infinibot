import json
from datetime import datetime
from typing import Annotated, List, TypedDict, Any, Dict, Optional

from pydantic import BaseModel, Field
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_openai.chat_models import AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.prebuilt import ToolNode
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient

from langgraph.graph.message import add_messages

from app.core.config import settings
from app.services.embedding_service import get_embedding_model
from app.services.document_permission import get_org_domains


# Define Pydantic models for source structure
class DocumentSource(BaseModel):
    """Source information for a document referenced in the response."""
    source: str = Field(description="The name of the document")
    webUrl: str = Field(description="The web URL of the document")
    docId: str = Field(description="The document ID of the document")

class DocumentSources(BaseModel):
    """Collection of document sources referenced in the response."""
    sources: List[DocumentSource] = Field(
        default_factory=list,
        description="List of document sources referenced in the response"
    )


def get_llm_model():
    """
    Get the appropriate LLM model based on configuration.
    """
    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        return ChatAnthropic(
            model=settings.LLM_MODEL_NAME, 
            temperature=settings.LLM_TEMPERATURE
        )
    elif settings.LLM_PROVIDER == "azure" and settings.AZURE_API_KEY:
        return AzureChatOpenAI(
            azure_deployment=settings.AZURE_DEPLOYMENT_NAME,
            azure_endpoint=settings.AZURE_API_BASE, 
            api_key=settings.AZURE_API_KEY,
            api_version=settings.AZURE_API_VERSION,
            temperature=settings.LLM_TEMPERATURE
        )
    else:
        return ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE
        )


def call_agent(
    client: MongoClient, 
    query: str, 
    thread_id: str,
    user_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Optimized agent with fast permission checking
    """
    user_info = ""
    user_email = None
    
    if user_context:
        user_email = user_context.get("email", "")
        user_name = user_context.get("name", "")
        dev_mode = user_context.get("dev_mode", False)
        user_info = f"User: {user_name} ({user_email}), Dev Mode: {'Yes' if dev_mode else 'No'}"
    
    from app.services.sharepoint_service import SharePointService
    sharepoint_service = SharePointService()
    
    db_name = settings.DB_NAME
    db = client[db_name]
    collection = db[settings.COLLECTION_NAME]

    class GraphState(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
        sources: Optional[List[Dict[str, str]]]


    def extract_sources(state: GraphState) -> dict:
        """
        Extracts document sources using a Pydantic model for structured output.
        """
        final_message = state["messages"][-1]
        
        # Get a fresh model instance for extraction
        extraction_model = get_llm_model()
        
        # Bind the Pydantic model to the model
        model_with_structure = extraction_model.with_structured_output(DocumentSources)
        
        # Create a prompt for extraction
        extraction_prompt = f"""
        Review the following AI assistant response and extract all document sources mentioned in it.
        Only include sources that were actually used to answer the question.
        
        Important: You MUST include the source name, webUrl, and docId for each document. These are all required.
        
        AI RESPONSE:
        {final_message.content}
        """
        
        # Get structured output directly
        try:
            # This will return a DocumentSources object
            result = model_with_structure.invoke(extraction_prompt)
            # Convert to list of dictionaries
            sources = [source.model_dump() for source in result.sources]
        except Exception as e:
            print(f"Error extracting sources with structured output: {str(e)}")
            sources = []
        
        # Return both the original message and the extracted sources
        return {"messages": state["messages"], "sources": sources}

    @tool
    def document_search_tool(query: str, n: int = 10) -> str:
        """
        Searches through Microsoft SharePoint documents stored in MongoDB to find relevant information,
        filtering based on user permissions.

        Args:
            query (str): The search query.
            n (int): Number of results to return (default: 10).

        Returns:
            str: JSON string of search results with scores.
        """
        embedding_model = get_embedding_model()
        
        vector_store = MongoDBAtlasVectorSearch(
            collection=collection,
            embedding=embedding_model,
            index_name="vector_index",
            text_key="embedding_text",
            embedding_key="embedding"
        )

        try:
            results = vector_store.similarity_search_with_score(query, k=n*3)
            
            if user_email and not (user_context and user_context.get("dev_mode", False)):
                filtered_results = []
                for doc, score in results:
                    if has_document_access(doc, user_email, sharepoint_service):
                        filtered_results.append((doc, score))
                        if len(filtered_results) >= n:
                            break
                
                results = filtered_results
            else:
                results = results[:n]
                
        except Exception as e:
            return json.dumps([])
        
        serializable_results = []
        for doc, score in results:
            serializable_doc = {
                "page_content": str(doc.page_content),
                "metadata": {
                    k: str(v) for k, v in doc.metadata.items() 
                    if k not in ["authorized_users", "authorized_groups"]
                },
                "source": doc.metadata.get("documentName", "Unknown Document"),
                "webUrl": doc.metadata.get("webUrl", "Unknown URL"),
                "docId": doc.metadata.get("documentId", "Unknown ID"),
                "score": float(score)
            }
            serializable_results.append(serializable_doc)

        return json.dumps(serializable_results)

    def has_document_access(doc, user_email: str, sharepoint_service=None) -> bool:
        """
        Fast document access check with configurable organization domains
        """
        if not hasattr(doc, "metadata") or not user_email:
            return False
            
        metadata = doc.metadata
        
        if not any(field in metadata for field in ["authorized_users", "authorized_groups", "access_level"]):
            return False
        
        access_level = metadata.get("access_level", "private")
        
        if access_level == "public":
            return True
        
        if access_level == "organization":
            user_domain = user_email.split("@")[1].lower() if "@" in user_email else ""
            org_domains = get_org_domains()
            return user_domain in org_domains
        
        authorized_users = metadata.get("authorized_users", [])
        if isinstance(authorized_users, str):
            try:
                authorized_users = json.loads(authorized_users.replace("'", "\""))
            except:
                authorized_users = [authorized_users]
        
        authorized_users_lower = [u.lower() for u in authorized_users if isinstance(u, str)]
        if user_email.lower() in authorized_users_lower:
            return True
        
        authorized_groups = metadata.get("authorized_groups", [])
        if isinstance(authorized_groups, str):
            try:
                authorized_groups = json.loads(authorized_groups.replace("'", "\""))
            except:
                authorized_groups = [authorized_groups]
        
        if authorized_groups and sharepoint_service:
            from app.services.document_permission import check_user_group_membership
            return check_user_group_membership(user_email, authorized_groups, sharepoint_service)
        
        return False
    
    tools = [document_search_tool]
    tool_node = ToolNode(tools)

    model = get_llm_model().bind_tools(tools)

    user_context_str = ""
    if user_context:
        user_name = user_context.get("name", "")
        user_email = user_context.get("email", "")
        if user_name and user_email:
            user_context_str = f"You are helping {user_name} ({user_email}). "

    system = """You are a helpful AI assistant specialized in retrieving information ONLY from company documents.

IMPORTANT INSTRUCTIONS:
1. ALWAYS use the document_search_tool to find information from company documents first before responding.
2. ONLY answer based on information found in the document search results. If you don't find relevant information, say "I don't have information about that in the available documents."
3. Provide natural, conversational responses that integrate information from the documents.
4. When referencing information, mention the document by name (e.g., "According to the Annual Report...").
5. DO NOT include URLs or IDs within your main response text.
6. If the question is unrelated to document content (like coding or calculations), say: "I'm designed to provide information only from company documents."

CRITICAL - SOURCES SECTION:
After your main response, you MUST include a "## Sources Used" section with all referenced documents formatted exactly as follows:

## Sources Used
- [documentName] (URL: [webUrl], ID: [docId])

This exact format is essential for proper source extraction. Include ALL sources you referenced.

Use the provided document_search_tool to find relevant information from the documents. {user_context}

Current time: {time}."""

    if user_email and not (user_context and user_context.get("dev_mode", False)):
        system += """\n\nIMPORTANT: You can only access information from documents that the user has permission to view. If they ask about information they don't have access to, you should inform them that you don't have access to that information due to permission restrictions."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        MessagesPlaceholder(variable_name="messages"),
    ])

    def call_model(state: GraphState) -> dict:
        """
        Calls the model with formatted messages based on the current state.
        """
        formatted_messages = prompt.format_messages(
            tool_names=", ".join([tool.name for tool in tools]),
            time=datetime.now().isoformat(),
            user_context=user_context_str,
            messages=state["messages"]
        )
        result = model.invoke(formatted_messages)
        return {"messages": [result]}

    def should_continue(state: GraphState) -> str:
        """
        Determines the next step based on the last message.
        """
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        # If we're done with tool calls, go to source extraction instead of END
        return "source_extractor"

    workflow = StateGraph(GraphState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_node("source_extractor", extract_sources)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    workflow.add_edge("source_extractor", END)

    checkpointer = MongoDBSaver(client=client, db_name=db_name)

    app = workflow.compile(checkpointer=checkpointer)

    message_content = query
    if user_context and not user_context.get("dev_mode", False):
        user_name = user_context.get("name", "")
        if user_name:
            message_content = f"[Query from {user_name}] {query}"

    final_state = app.invoke(
        {"messages": [HumanMessage(content=message_content)], "sources": []},
        config={"recursion_limit": 15, "configurable": {"thread_id": thread_id}}
    )

    print(f"Final state sources: {final_state.get('sources', [])}")
    
    # Return both the final content and the extracted sources
    return {
        "content": final_state["messages"][-1].content,
        "sources": final_state.get("sources", [])
    }