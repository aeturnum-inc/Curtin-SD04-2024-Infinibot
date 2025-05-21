#!/usr/bin/env python
"""
Script to verify that permissions are correctly stored in MongoDB documents.
"""
import os
import sys
from pymongo import MongoClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings

def main():
    """Verify permissions are correctly stored in MongoDB documents."""
    print(f"Verifying permissions in database: {settings.DB_NAME}")
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGODB_ATLAS_URI)
    
    try:
        # Get database and collection
        db = client[settings.DB_NAME]
        collection = db[settings.COLLECTION_NAME]
        
        # Count total documents
        total_docs = collection.count_documents({})
        print(f"Total documents in collection: {total_docs}")
        
        # Count documents with permission fields
        docs_with_authorized_users = collection.count_documents({"metadata.authorized_users": {"$exists": True}})
        docs_with_authorized_groups = collection.count_documents({"metadata.authorized_groups": {"$exists": True}})
        docs_with_access_level = collection.count_documents({"metadata.access_level": {"$exists": True}})
        
        print(f"Documents with authorized_users: {docs_with_authorized_users}")
        print(f"Documents with authorized_groups: {docs_with_authorized_groups}")
        print(f"Documents with access_level: {docs_with_access_level}")
        
        # Sample a few documents to inspect
        sample_docs = collection.find().limit(5)
        
        print("\nSample document metadata:")
        for i, doc in enumerate(sample_docs):
            print(f"\nDocument {i+1}:")
            metadata = doc.get("metadata", {})
            print(f"  Document ID: {metadata.get('documentId', 'N/A')}")
            print(f"  Document Name: {metadata.get('documentName', 'N/A')}")
            print(f"  Authorized Users: {metadata.get('authorized_users', [])}")
            print(f"  Authorized Groups: {metadata.get('authorized_groups', [])}")
            print(f"  Access Level: {metadata.get('access_level', 'N/A')}")
            
    except Exception as e:
        print(f"ERROR: Failed to verify permissions: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()