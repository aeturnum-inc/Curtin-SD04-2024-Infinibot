from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from app.core.config import settings

# Global database connections
mongodb_client: MongoClient = None


def get_mongodb_client() -> MongoClient:
    """
    Get the MongoDB client instance.
    """
    return mongodb_client


def connect_to_mongodb():
    """
    Create database connections.
    """
    global mongodb_client
    
    # sync client
    mongodb_client = MongoClient(settings.MONGODB_ATLAS_URI)
    try:
        # Verify connection
        mongodb_client.admin.command("ping")
        print("Connected to MongoDB (synchronous)")
    except ConnectionFailure:
        print("Failed to connect to MongoDB (sync)")
        raise


def close_mongodb_connection():
    """
    Close database connections.
    """
    global mongodb_client
    
    if mongodb_client:
        mongodb_client.close()
        print("Closed MongoDB connection (sync)")