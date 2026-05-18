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

    def get_chat_sessions(self) -> list[dict[str, Any]]:
        # Get all chat sessions for the current user.
        try:
            response = self._make_request('GET', '/api/chat/sessions')
            # Extract items if wrapped in a dict, otherwise return empty list
            if 'items' in response and isinstance(response['items'], list):
                return response['items']
            return []
        except APIError:
            return []

    def get_session_messages(self, session_id: int) -> list[dict[str, Any]]:
        # Get messages from a specific chat session.
        try:
            logger.info(f'Fetching messages for session ID: {session_id}')
            response = self._make_request('GET', f'/api/chat/sessions/{session_id}')

            if isinstance(response, dict) and 'messages' in response:
                logger.info(
                    f'Successfully fetched messages for session ID: {session_id}',
                )
                return response.get('messages', [])

            return []
        except APIError as e:
            logger.error(f'Error fetching messages for session ID {session_id}: {e!s}')
            return []

    def send_message(
        self,
        message: str,
        session_id: int | None = None,
    ) -> dict[str, Any]:
        # Send a message to the chat.
        try:
            logger.info(f'Sending message to session ID: {session_id}')
            response = self._make_request(
                'POST',
                '/api/chat/chat',
                json={'content': message, 'session_id': session_id},
            )
            logger.info(f'Message sent successfully to session ID: {session_id}')
            return response
        except APIError as e:
            logger.error(f'Error sending message: {e!s}')
            return {'error': str(e)}

    def submit_feedback(
        self,
        message_id: int,
        feedback_type: str,
        rating: int | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        # Submit feedback for a message.
        try:
            logger.info(
                f'Submitting feedback for message ID: {message_id}, type: {feedback_type}',
            )

            feedback_data = {
                'message_id': message_id,
                'feedback_type': feedback_type,
            }

            if rating is not None:
                feedback_data['rating'] = rating

            if comment:
                feedback_data['comment'] = comment

            logger.debug(f'Sending feedback data to API: {feedback_data}')

            # Use the standard _make_request function instead of direct request
            # This ensures proper handling of cookies and tokens
            response = self._make_request(
                'POST',
                '/api/chat/feedback',
                json=feedback_data,
            )

            logger.debug(f'Feedback API response: {response}')
            return response

        except APIError as e:
            logger.exception(f'API Error submitting feedback: {e!s}')
            return {'error': str(e)}
        except Exception as e:
            logger.exception(f'Unexpected error submitting feedback: {e!s}')
            return {'error': str(e)}

    def delete_chat_session(self, session_id: int) -> bool:
        # Delete a chat session.
        try:
            self._make_request('DELETE', f'/api/chat/sessions/{session_id}')
            return True
        except APIError:
            return False

    def test_connection(self) -> dict[str, Any]:
        # Test the API connection by calling the health endpoint.
        try:
            logger.info('Testing API connection')
            result = {'status': 'initialized'}
            result['api_url'] = self.base_url

            # Test health endpoint
            try:
                health_data = self._make_request('GET', '/api/health', timeout=5)
                result['health_check'] = health_data
                result['health_status'] = 'success'
            except Exception as e:
                logger.error(f'Health check failed: {e}')
                result['health_status'] = 'failed'
                result['health_error'] = str(e)

            # Test authentication status
            try:
                user_info = self.get_user_info()
                # If we get valid user info, the user is authenticated (via token or cookie)
                is_authenticated = 'id' in user_info and 'username' in user_info
                result['has_auth'] = is_authenticated
                result['auth_type'] = 'token' if self.token else 'cookie' if is_authenticated else 'none'

                if is_authenticated:
                    result['user_info'] = user_info
                    result['user_info_status'] = 'success'
                else:
                    result['user_info_status'] = 'not_authenticated'
            except Exception as e:
                logger.error(f'Authentication check failed: {e}')
                result['has_auth'] = False
                result['auth_type'] = 'none'
                result['user_info_status'] = 'failed'
                result['user_info_error'] = str(e)

            # Test if the server accepts POST requests to the feedback endpoint
            try:
                # Don't actually submit feedback, just check if the endpoint exists and accepts POST
                # Use a HEAD request which should return 405 Method Not Allowed if endpoint exists
                response = self.session.head(f'{self.base_url}/api/chat/feedback', timeout=5)
                result['feedback_endpoint_status'] = response.status_code
                # 405 means Method Not Allowed which is normal for HEAD on a POST-only endpoint
                # This shows the endpoint exists
                result['feedback_endpoint_check'] = 'success'
            except Exception as e:
                logger.error(f'Feedback endpoint check failed: {e}')
                result['feedback_endpoint_check'] = 'failed'
                result['feedback_endpoint_error'] = str(e)

            result['status'] = 'completed'
            return result
        except Exception as e:
            logger.exception(f'API connection test failed: {e}')
            return {'status': 'error', 'error': str(e)}
