"""
Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# Add the parent directory to sys.path to enable absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# """Streamlit application for the RTL Services Support Chatbot."""

# Change from relative to absolute imports
from app.auth.auth_service import check_auth, login, register
from app.chat.chat_service import (
    delete_chat_session,
    get_chat_sessions,
    get_session_messages,
    send_message,
)
from app.logger import initialize_logger, logger
from app.ui.components import display_message
from app.ui.components.profile import display_auth_user_profile
from app.ui.styles.main import load_main_styles
from app.utils.session_state import (
    initialize_session_state,
)


def display_auth_sidebar():
    """Display authentication sidebar with login and register tabs."""
    logger.debug('User not logged in, displaying login/register tabs')
    tab_options = ['Login', 'Register']
    current_tab = st.radio(
        'Authentication Options',
        tab_options,
        label_visibility='collapsed',  # Hide the label but keep it for accessibility
    )

    if current_tab == 'Login':
        logger.debug('Login tab selected')
        st.title('Login')
        username = st.text_input('Username', key='login_username')
        password = st.text_input('Password', type='password', key='login_password')
        if st.button('Login', key='login_button'):
            success, error = login(username, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            elif error:
                st.error(error.get('error', 'Login failed'))
    else:  # Register tab
        st.title('Register')
        reg_username = st.text_input('New Username', key='reg_username')
        reg_email = st.text_input('New Email', key='reg_email')
        reg_password = st.text_input(
            'New Password',
            type='password',
            key='reg_password',
        )
        if st.button('Register', key='register_button'):
            success, error = register(reg_username, reg_email, reg_password)
            if success:
                st.success('Registration successful! Please login.')
                st.rerun()
            elif error:
                st.error(error.get('error', 'Registration failed'))


def display_chat_history_sessions(sessions):
    """Display chat history sessions grouped by date."""
    # Sort sessions by date in descending order (newest first)
    sorted_sessions = (
        sorted(
            sessions,
            key=lambda x: datetime.fromisoformat(
                x.get('created_at', '').replace('Z', '+00:00'),
            ),
            reverse=True,
        )
        if sessions
        else []
    )

    # Group sessions by date
    sessions_by_date = {}
    for session in sorted_sessions:
        created_at = datetime.fromisoformat(
            session.get('created_at', '').replace('Z', '+00:00'),
        )
        date_str = created_at.strftime('%Y-%m-%d')
        if date_str not in sessions_by_date:
            sessions_by_date[date_str] = []
        sessions_by_date[date_str].append(session)

    # Display sessions grouped by date
    for date_str, date_sessions in sessions_by_date.items():
        with st.expander(f'📅 {date_str}', expanded=False):
            for session in date_sessions:
                display_session_item(session)


def display_session_item(session):
    """Display an individual session with its delete button."""
    col1, col2 = st.columns([4, 1])
    with col1:
        if st.button(f"{session['title']}", key=f"session_{session['id']}"):
            st.session_state.current_session_id = session['id']
            st.session_state.messages = get_session_messages(session['id'])
            st.rerun()
    with col2:
        if st.button(
            '🗑️',
            key=f"delete_{session['id']}",
        ) and delete_chat_session(
            session['id'],
        ):
            if st.session_state.current_session_id == session['id']:
                st.session_state.current_session_id = None
                st.session_state.messages = []
            st.success('Chat session deleted')
            st.rerun()


def display_authenticated_sidebar():
    """Display sidebar content for authenticated users."""
    # Display user profile at the top
    display_auth_user_profile()

    st.title('Chat History')
    sessions = get_chat_sessions()
    if st.button('New Chat'):
        st.session_state.current_session_id = None
        st.session_state.messages = []
        st.rerun()

    # Display chat sessions
    display_chat_history_sessions(sessions)


def display_chat_interface():
    """Display the main chat interface."""
    st.title('RTL Services Support Chatbot')
    st.write(
        'RAG Chatbot that uses Bedrock to answer questions on tools like bCourses, Ally, Kaltura etc.',
    )

    # Display chat messages
    for message in st.session_state.messages:
        display_message(message)

    # Chat input - this should be outside the message loop
    prompt = st.chat_input('What would you like to know?')
    if prompt:
        # Add user message to chat history
        st.session_state.messages.append({'role': 'user', 'content': prompt})
        display_message({'role': 'user', 'content': prompt})

        # Get response from API
        response = send_message(prompt, st.session_state.current_session_id)
        if response:
            # Add assistant message to chat history
            if 'error' in response:
                error_message = response.get('error', 'Unknown error')
                logger.error(f'Error in response: {error_message}')
                st.error(f'API Error: {error_message}')
            # Handle the nested response structure where message is inside assistant_message
            elif 'assistant_message' in response:
                assistant_message = {
                    'role': 'assistant',
                    'content': response['assistant_message']['content'],
                    'metadata': response['assistant_message'].get('metadata', {}),
                    'id': response['assistant_message'].get('id'),
                }
                st.session_state.messages.append(assistant_message)
                display_message(assistant_message)

                # Update current session ID if it was a new session
                if st.session_state.current_session_id is None and 'user_message' in response:
                    # Extract session_id from the first message
                    user_msg = response.get('user_message', {})
                    if 'session_id' in user_msg:
                        st.session_state.current_session_id = user_msg['session_id']
            elif 'message' in response:
                assistant_message = {
                    'role': 'assistant',
                    'content': response['message'],
                    'metadata': response.get('metadata'),
                    'id': response.get('id'),
                }
                st.session_state.messages.append(assistant_message)
                display_message(assistant_message)
            else:
                # Log the actual response structure for debugging
                logger.error(f'Unexpected response structure: {response}')
                st.error('Received unexpected response format from API')


def main():
    """Run the Streamlit application."""
    # Initialize enhanced logger first thing in the application
    initialize_logger()

    # Log startup information to help with debugging environment variable issues
    logger.info(
        'Starting the Streamlit application with enhanced logging configuration',
    )
    logger.info('Environment variables affecting logging:')
    for var in [
        'LOGGING_LEVEL',
        'DEBUG',
        'LOGGING_LOCATION',
        'LOGGING_PROPAGATION_LEVEL',
        'LOG_TO_FILE',
    ]:
        logger.info(f"  {var}: {os.environ.get(var, 'Not set')}")
    logger.info(f'Current directory: {os.getcwd()}')
    logger.info(f"Environment: {os.environ.get('APP_ENV', 'Not set')}")

    st.set_page_config(page_title='RTL Services Support Chatbot', layout='wide')

    # Load all styles
    load_main_styles()

    # Initialize session state
    initialize_session_state()
    logger.debug('Session state initialized')

    # Check for cookie-based authentication on page load/refresh
    if not st.session_state.get('logged_in', False):
        # Try to authenticate using HTTP-only cookie
        logger.debug('Checking for cookie-based authentication')
        if check_auth():
            logger.info('User authenticated via cookie')
            # No need to rerun as session state is updated by check_auth()
        else:
            logger.debug('No cookie-based authentication found')

    # Sidebar for authentication and session management
    with st.sidebar:
        if not st.session_state.logged_in:
            display_auth_sidebar()
        else:
            display_authenticated_sidebar()

    # Main chat interface
    if st.session_state.logged_in:
        display_chat_interface()
    else:
        st.title('RTL Services Support Chatbot')
        st.write(
            'RAG Chatbot that uses Bedrock to answer questions on tools like bCourses, Ally, Kaltura etc.',
        )
        st.write('Please login or register to start chatting!')


if __name__ == '__main__':
    main()
