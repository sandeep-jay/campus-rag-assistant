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
from pathlib import Path

import streamlit as st

# This must be the first Streamlit command
st.set_page_config(page_title='RTL Services Support Chatbot', layout='wide')

# Add the parent directory to sys.path to enable absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# Change from relative to absolute imports
from app.auth.auth_service import check_auth, login, register
from app.config import initialize_config
from app.logger import initialize_logger, logger
from app.ui.components.profile import display_auth_user_profile
from app.ui.styles.main import load_main_styles
from app.utils.session_state import (
    initialize_session_state,
)

"""Streamlit application for the RTL Services Support Chatbot."""


def display_auth_sidebar():
    # Display authentication sidebar with login and register tabs.
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


def display_authenticated_sidebar():
    # Display sidebar content for authenticated users.
    # Display user profile at the top
    display_auth_user_profile()

    st.title('Chat History')
    if st.button('New Chat'):
        st.session_state.current_session_id = None
        st.session_state.messages = []
        st.rerun()


def display_chat_interface():
    # Display the main chat interface.
    st.title('RTL Services Support Chatbot')
    st.write(
        'RAG Chatbot that uses Bedrock to answer questions on tools like bCourses, Ally, Kaltura etc.',
    )

    # Initialize chat history in session state if it doesn't exist
    if 'messages' not in st.session_state:
        st.session_state.messages = [{'role': 'assistant', 'content': 'Hello! How can I help you today?'}]

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.write(message['content'])

    # Chat input
    if prompt := st.chat_input("What's on your mind?"):
        # Add user message to chat history
        st.session_state.messages.append({'role': 'user', 'content': prompt})

        # Display user message
        with st.chat_message('user'):
            st.write(prompt)

        # Simulate assistant response
        response = f'This is a dummy response to: {prompt}'
        st.session_state.messages.append({'role': 'assistant', 'content': response})

        # Display assistant response
        with st.chat_message('assistant'):
            st.write(response)


def main():
    # Initialize configuration first
    initialize_config()

    # Initialize enhanced logger
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
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'Not set')}")

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
