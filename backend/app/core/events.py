from app.core.database import connect_to_mongodb, close_mongodb_connection


def startup_event():
    """
    Function that runs when the application starts.
    """
    print("Starting application...")
    connect_to_mongodb()


def shutdown_event():
    """
    Function that runs when the application shuts down.
    """
    print("Shutting down application...")
    close_mongodb_connection()