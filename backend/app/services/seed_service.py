import requests
from pymongo import MongoClient
from langchain_experimental.text_splitter import SemanticChunker
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.documents import Document

from app.core.config import settings
from app.services.sharepoint_service import SharePointService
from app.services.document_permission import get_document_permissions
from app.services.embedding_service import get_embedding_model


def seed_database(client: MongoClient = None, admin_email: str = None) -> int:
    """
    Seed the MongoDB database with SharePoint documents.
    
    Args:
        client: Optional MongoClient to use
        admin_email: Email of admin user for permission tracking
        
    Returns:
        int: Number of chunks inserted
    """
    if client is None:
        client = MongoClient(settings.MONGODB_ATLAS_URI)
    
    try:
        # Verify connection
        client.admin.command("ping")
        print("Successfully connected to MongoDB!")
        
        # Get database and collection
        db = client[settings.DB_NAME]
        collection = db[settings.COLLECTION_NAME]
        
        # Clear existing documents
        collection.delete_many({})
        print("Cleared existing documents")

        # Initialize SharePoint service
        sharepoint_service = SharePointService()
        
        # Get all documents from SharePoint (as admin)
        documents = sharepoint_service.list_documents()
        print(f"Found {len(documents)} documents in SharePoint")

        # Get the embedding model for semantic chunking and later vector search
        embedding_model = get_embedding_model()
        
        # Initialize semantic text splitter with the latest API
        text_splitter = SemanticChunker(
            embeddings=embedding_model,
            buffer_size=5,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=0.7,
            number_of_chunks=None,  # Let the algorithm decide based on content
            min_chunk_size=800
        )
        all_documents = []

        # If admin_email is provided, create a permission map for documents
        permission_map = {}
        print(f"Admin email provided: {admin_email}")
        if admin_email:
            print(f"Getting permission data using admin email: {admin_email}")
            try:
                token = sharepoint_service.get_access_token()
                print(f"Got SharePoint access token: {token[:10]}...")
                headers = {"Authorization": f"Bearer {token}"}
                
                # Get drives
                drives_endpoint = f"https://graph.microsoft.com/v1.0/sites/{settings.SITE_ID}/drives"
                print(f"Getting drives using endpoint: {drives_endpoint}")
                drives_response = requests.get(drives_endpoint, headers=headers)
                drives_response.raise_for_status()
                drives = drives_response.json().get("value", [])
                print(f"Found {len(drives)} drives")
                
                if drives:
                    drive_id = drives[0]["id"]
                    print(f"Using drive ID: {drive_id}")
                    
                    # For each document, get users with access
                    for doc in documents:
                        doc_id = doc["id"]
                        print(f"Getting permissions for document {doc['name']} (ID: {doc_id})")
                        try:
                            permission_data = get_document_permissions(
                                sharepoint_service, doc_id, drive_id
                            )
                            permission_map[doc_id] = permission_data
                            print(f"Got permissions for document {doc['name']}: {permission_data}")
                        except Exception as e:
                            print(f"Error getting permissions for document {doc['name']}: {e}")
                else:
                    print("No drives found, cannot get permissions")
            except Exception as e:
                print(f"Error in permission mapping: {e}")

        # Process each document
        for doc in documents:
            print(f"Processing: {doc['name']}")
            try:
                content = sharepoint_service.get_document_content(doc["id"])
                
                # Using semantic chunker with the updated API
                chunks = text_splitter.split_text(content)
                
                for index, chunk in enumerate(chunks):
                    metadata = {
                        "documentId": doc["id"],
                        "documentName": doc["name"],
                        "webUrl": doc["webUrl"],
                        "lastModified": doc["lastModified"],
                        "chunkIndex": index,
                    }
                    
                    # Add access control information if permission map exists
                    if doc["id"] in permission_map:
                        print(f"Adding permission metadata for document {doc['name']}")
                        metadata["authorized_users"] = permission_map[doc["id"]]["users"]
                        metadata["authorized_groups"] = permission_map[doc["id"]]["groups"]
                        metadata["access_level"] = permission_map[doc["id"]]["access_level"]
                    else:
                        print(f"No permission data found for document {doc['name']}")
                    
                    all_documents.append(Document(page_content=chunk, metadata=metadata))
                
                print(f"Processed: {doc['name']}")
            except Exception as e:
                print(f"Error processing document {doc['name']}: {e}")
                continue

        if not all_documents:
            raise Exception("No documents to upload to database")
            
        # Print sample metadata to verify permissions are included
        print("\nSample document metadata before embedding:")
        for i in range(min(3, len(all_documents))):
            print(f"Document {i+1} metadata: {all_documents[i].metadata}")

        # Store documents with embeddings
        MongoDBAtlasVectorSearch.from_documents(
            documents=all_documents,
            embedding=embedding_model,
            collection=collection,
            index_name="vector_index",
            text_key="embedding_text",
            embedding_key="embedding",
        )
        
        print(f"Successfully inserted {len(all_documents)} chunks into MongoDB")
        print("Database seeding completed")
        
        return len(all_documents)
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        raise
    finally:
        if client:
            client.close()