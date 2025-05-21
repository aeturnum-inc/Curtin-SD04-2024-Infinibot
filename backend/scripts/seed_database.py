#!/usr/bin/env python
"""
Script to seed the database with documents from SharePoint.
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.services.seed_service import seed_database
from pymongo import MongoClient

def main():
    """
    Main function to seed the database.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Seed the MongoDB database with SharePoint documents')
    parser.add_argument('--admin-email', help='Email of admin user for permission tracking')
    args = parser.parse_args()
    
    admin_email = args.admin_email or os.getenv("ADMIN_EMAIL")
    
    print(f"Seeding database: {settings.DB_NAME}")
    print(f"MongoDB URI: {'*' * 10}...{'*' * 5}")  # Hide the actual URI for security
    
    # Check if environment variables are set
    required_vars = [
        "MONGODB_ATLAS_URI", 
        "TENANT_ID", 
        "CLIENT_ID", 
        "CLIENT_SECRET", 
        "SITE_ID"
    ]
    
    # Add required API key based on provider
    if settings.LLM_PROVIDER == "anthropic":
        required_vars.append("ANTHROPIC_API_KEY")
    elif settings.LLM_PROVIDER == "azure":
        required_vars.append("AZURE_API_KEY") 
    else:
        required_vars.append("OPENAI_API_KEY")
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file or environment.")
        sys.exit(1)
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGODB_ATLAS_URI)
    
    try:
        # Seed the database
        num_chunks = seed_database(client, admin_email)
        print(f"Successfully seeded database with {num_chunks} document chunks")
    except Exception as e:
        print(f"ERROR: Failed to seed database: {e}")
        sys.exit(1)
    finally:
        client.close()
        
    print("Database seeding completed successfully")

if __name__ == "__main__":
    main()