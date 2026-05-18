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

from __future__ import annotations

import uuid
from typing import Any

import streamlit as st

from app.api import get_api_client
from app.logger import logger

"""Authentication service module for login and registration."""


def get_browser_fingerprint() -> str:
    # Generate a browser fingerprint to enhance session security.
    try:
        # In a real implementation, we would use JavaScript through a custom component
        # to gather more information. For now, this is a simple placeholder.
        browser_info = {'user_agent': st.session_state.get('_user_agent', 'unknown'), 'session_id': str(uuid.uuid4())}
        return f"{browser_info['user_agent']}:{browser_info['session_id']}"
    except Exception as e:
        logger.warning(f'Error generating browser fingerprint: {e}')
        return str(uuid.uuid4())  # Fallback to a random UUID


def login(username: str, password: str) -> tuple[bool, dict[str, Any] | None]:
    # Attempt to login with the provided credentials using HTTP-only cookies.

    try:
        logger.info(f'Attempting login for user: {username}')
        api_client = get_api_client()
        response = api_client.login_with_cookie(username, password)

        if response.get('status') == 'success':
            # Store username in session state but not the token (it's in HTTP-only cookie)
            st.session_state.logged_in = True
            st.session_state.username = response.get('username')

            # Store browser fingerprint for added security
            st.session_state.browser_fingerprint = get_browser_fingerprint()

            logger.info(f'Login successful for user: {username}')
            return True, None
        logger.warning(f'Login failed for user: {username}, invalid response')
        return False, {'error': 'Invalid response from server'}
    except Exception as e:
        logger.error(f'Login error: {e!s}')
        return False, {'error': f'Failed to login: {e!s}'}


def register(
    username: str,
    email: str,
    password: str,
) -> tuple[bool, dict[str, Any] | None]:
    # Register a new user with the provided details.
    try:
        logger.info(f'Attempting to register user: {username}')
        api_client = get_api_client()
        api_client.register(username, email, password)
        logger.info(f'Registration successful for user: {username}')
        return True, None
    except Exception as e:
        logger.error(f'Registration error: {e!s}')
        error_detail = str(e)
        return False, {'error': error_detail}


def logout() -> None:
    # Log the user out by clearing session state and API cookie.
    logger.info('User logged out')
    # Clear session state
    st.session_state.logged_in = False
    st.session_state.messages = []
    st.session_state.current_session_id = None
    st.session_state.username = None

    # Call logout endpoint to clear cookie
    api_client = get_api_client()
    api_client.logout()


def get_user_info() -> dict[str, Any]:
    # Get information about the current user.
    api_client = get_api_client()
    return api_client.get_user_info()


def check_auth() -> bool:
    # Check if user is authenticated via cookie.
    try:
        api_client = get_api_client()
        user_info = api_client.get_user_info()

        if user_info and 'username' in user_info and 'id' in user_info:
            # Check if we have a browser fingerprint from before
            current_fingerprint = get_browser_fingerprint()
            stored_fingerprint = st.session_state.get('browser_fingerprint')

            # For new users without a fingerprint, store it
            if not stored_fingerprint:
                st.session_state.browser_fingerprint = current_fingerprint

            # User is authenticated via cookie, update session state
            st.session_state.logged_in = True
            st.session_state.username = user_info['username']
            logger.info(f"User authenticated via cookie: {user_info['username']}")
            return True

        logger.debug('No valid authentication found in cookie')
        return False
    except Exception as e:
        logger.error(f'Error checking authentication: {e}')
        return False
