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

from typing import Any

import requests
from requests.exceptions import RequestException

from app.config import settings
from app.logger import logger

"""Client for interacting with the backend API."""


class APIError(Exception):
    """Exception raised for API-related errors."""


class APIClient:
    """Client for interacting with the backend API."""

    def __init__(self, base_url: str | None = None):
        # Initialize the API client.
        self.base_url = base_url or settings.API_URL
        self.session = requests.Session()
        self.token: str | None = None
        logger.debug(f'APIClient initialized with base URL: {self.base_url}')

    def set_token(self, token: str) -> None:
        # Set the authentication token.
        self.token = token
        self.session.headers['Authorization'] = f'Bearer {token}'

    def clear_token(self) -> None:
        # Clear the authentication token.
        self.token = None
        self.session.headers.pop('Authorization', None)

    def _prepare_request(self, **kwargs: Any) -> dict[str, Any]:
        # Prepare the request parameters.
        # Set default timeout
        timeout = kwargs.get('timeout', 30)  # Default timeout of 30 seconds
        logger.debug(f'Request timeout: {timeout} seconds')
        kwargs['timeout'] = timeout

        # Ensure authorization header is set if token is available
        if self.token and 'Authorization' not in self.session.headers:
            logger.warning('Token present but Authorization header missing, setting it now')
            self.session.headers['Authorization'] = f'Bearer {self.token}'

        # Always send cookies with the request (important for cookie-based auth)
        kwargs['cookies'] = kwargs.get('cookies', None)

        return kwargs

    def _log_request_info(self, method: str, url: str) -> None:
        # Log information about the request.
        logger.debug(f'Making {method} request to {url}')

        # Log authentication status
        if self.token:
            logger.debug(f'Request includes authentication token (truncated): {self.token[:10]}...')
        else:
            logger.debug('Request does not include authentication token')

        # Log authorization header status
        if 'Authorization' in self.session.headers:
            logger.debug('Authorization header is set in session')
        else:
            logger.debug('No Authorization header (using cookies or unauthenticated request)')

    def _handle_error_response(self, response) -> dict[str, Any]:
        # Handle error responses from the API.
        logger.warning(f'API request failed with status {response.status_code}: {response.text}')
        try:
            error_data = response.json()
            return {'error': error_data.get('detail', 'Unknown error')}
        except ValueError:
            return {'error': f'HTTP {response.status_code}: {response.text}'}

    def _process_json_response(self, response) -> dict[str, Any]:
        # Process a successful JSON response.
        try:
            data = response.json()
            # Make sure data is a dictionary before returning
            if isinstance(data, dict):
                return data
            if isinstance(data, list):
                return {'items': data}  # Wrap lists in a dictionary
            return {'data': data}  # Wrap other values in a dictionary
        except ValueError:
            logger.warning(f'Response is not valid JSON: {response.text[:100]}...')
            # Return empty dict if not JSON
            return {}

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # Make an HTTP request to the API.
        url = f'{self.base_url}{endpoint}'
        try:
            self._log_request_info(method, url)
            kwargs = self._prepare_request(**kwargs)

            # Important for cookie-based auth
            kwargs['allow_redirects'] = kwargs.get('allow_redirects', True)

            response = self.session.request(method, url, **kwargs)
            logger.debug(f'Response status code: {response.status_code}')

            if response.status_code >= 400:
                return self._handle_error_response(response)

            response.raise_for_status()
            return self._process_json_response(response)

        except RequestException as e:
            logger.error(f'API request failed: {e!s}')
            msg = f'API request failed: {e!s}'
            raise APIError(msg)
        except Exception as e:
            logger.error(f'Error in API request: {e!s}')
            msg = f'Error in API request: {e!s}'
            raise APIError(msg)

    def login(self, username: str, password: str) -> dict[str, Any]:
        # Login to the API and get an authentication token.
        try:
            logger.info(f'Attempting login for user: {username}')
            response = self._make_request(
                'POST',
                '/api/auth/token',
                data={'username': username, 'password': password},
            )

            if 'access_token' in response:
                self.set_token(response['access_token'])
                logger.info(f'Login successful for user: {username}')

            return response
        except APIError as e:
            logger.warning(f'Login failed for user: {username}: {e!s}')
            raise

    def login_with_cookie(self, username: str, password: str) -> dict[str, Any]:
        # Login using HTTP-only cookie authentication.
        try:
            logger.info(f'Attempting cookie-based login for user: {username}')

            # Reminder about cookie naming best practices
            logger.debug('IMPORTANT: Ensure backend generates uniquely prefixed cookies to prevent cross-app leakage')

            response = self._make_request(
                'POST',
                '/api/auth/login',
                data={'username': username, 'password': password},
            )

            logger.info(f'Cookie-based login successful for user: {username}')
            return response
        except APIError as e:
            logger.warning(f'Cookie-based login failed for user: {username}: {e!s}')
            raise

    def logout(self) -> dict[str, Any]:
        # Logout and clear the authentication cookie.
        try:
            logger.info('Logging out user')
            response = self._make_request(
                'POST',
                '/api/auth/logout',
            )
            # Clear any token-based auth too
            self.clear_token()
            logger.info('Logout successful')
            return response
        except APIError as e:
            logger.warning(f'Logout failed: {e!s}')
            raise

    def register(self, username: str, email: str, password: str) -> dict[str, Any]:
        # Register a new user.
        try:
            logger.info(f'Attempting to register user: {username}')
            response = self._make_request(
                'POST',
                '/api/auth/register',
                json={'username': username, 'email': email, 'password': password},
            )
            logger.info(f'Registration successful for user: {username}')
            return response
        except APIError as e:
            logger.warning(f'Registration failed for user: {username}: {e!s}')
            raise

    def get_user_info(self) -> dict[str, Any]:
        # Get information about the current user.
        try:
            return self._make_request('GET', '/api/auth/me')
        except APIError:
            return {'username': 'User'}  # Default if we can't get the user info
