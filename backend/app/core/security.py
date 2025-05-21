"""
Security-related utilities.
"""
import secrets
from datetime import datetime, timedelta


def generate_thread_id():
    """
    Generate a unique thread ID for conversations.
    
    Returns:
        str: A unique thread ID
    """
    timestamp = int(datetime.now().timestamp())
    random_suffix = secrets.token_hex(4)
    return f"{timestamp}-{random_suffix}"