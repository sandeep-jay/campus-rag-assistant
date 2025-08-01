# Import the error class directly
from .client import APIError

# Import models directly
from .models import ChatSession, Feedback, Message, User

# Don't import api_client here to avoid circular imports
# Instead, use get_api_client() function

__all__ = [
    'APIError',
    'ChatSession',
    'Feedback',
    'Message',
    'User',
    'get_api_client',
]


def get_api_client():
    """Get the API client for the current session.

    Instead of using a singleton pattern that shares the same client
    across different user sessions, this creates a session-specific client
    to prevent auth tokens from leaking between users.
    """
    import streamlit as st

    from .client import APIClient

    # Create a client instance specific to this session
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()

    return st.session_state.api_client
