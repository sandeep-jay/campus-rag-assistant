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

import streamlit as st

from app.api import get_api_client
from app.logger import logger

"""Chat service module for handling messages and chat sessions."""


def _extract_session_id_from_response(response: dict[str, Any], api_client: Any) -> int | None:
    # Extract session ID from API response.
    if 'user_message' in response and isinstance(response['user_message'], dict):
        user_message = response['user_message']
        if 'session_id' in user_message:
            return user_message['session_id']

    if 'assistant_message' in response and isinstance(response['assistant_message'], dict):
        assistant_message = response['assistant_message']
        if 'session_id' in assistant_message:
            return assistant_message['session_id']

    # If we can't find it explicitly, get the session_id from the message id lookup
    if 'user_message' in response and 'id' in response['user_message']:
        logger.info('Getting session_id from message lookup')
        sessions = api_client.get_chat_sessions()
        if sessions:
            # The most recent session should be the one just created
            newest_session_id = sessions[0]['id'] if sessions else None
            if newest_session_id:
                # Update the response with the session_id for future reference
                if 'user_message' in response:
                    response['user_message']['session_id'] = newest_session_id
                if 'assistant_message' in response:
                    response['assistant_message']['session_id'] = newest_session_id
                return newest_session_id

    logger.warning('Could not extract session_id from response')
    return None


def send_message(message: str, session_id: int | None = None) -> dict[str, Any]:
    # Send a message to the chat API.
    try:
        logger.info(f'Sending message to session ID: {session_id}')
        api_client = get_api_client()
        response = api_client.send_message(message, session_id)

        if 'error' in response:
            logger.warning(f"Message failed: {response['error']}")
            return response

        # If we're starting a new session (session_id is None), extract the new session_id
        if session_id is None:
            new_session_id = _extract_session_id_from_response(response, api_client)
            if new_session_id:
                st.session_state.current_session_id = new_session_id
                logger.info(f'New session created with ID: {new_session_id}')

        logger.info(f'Message sent successfully to session ID: {session_id}')
        return response
    except Exception as e:
        logger.error(f'Error sending message: {e!s}')
        return {'error': str(e)}


def get_chat_sessions() -> list[dict[str, Any]]:
    # Get all chat sessions for the current user.
    try:
        api_client = get_api_client()
        return api_client.get_chat_sessions()
    except Exception as e:
        logger.error(f'Failed to fetch chat sessions: {e!s}')
        return []


def get_session_messages(session_id: int) -> list[dict[str, Any]]:
    # Get messages from a specific chat session.
    try:
        logger.info(f'Fetching messages for session ID: {session_id}')
        api_client = get_api_client()
        messages = api_client.get_session_messages(session_id)
        logger.info(f'Successfully fetched messages for session ID: {session_id}')
        return messages
    except Exception as e:
        logger.error(f'Error fetching messages for session ID {session_id}: {e!s}')
        return []


def delete_chat_session(session_id: int) -> bool:
    # Delete a chat session.
    try:
        api_client = get_api_client()
        return api_client.delete_chat_session(session_id)
    except Exception as e:
        logger.error(f'Failed to delete chat session: {e!s}')
        return False


def clear_all_chat_history() -> bool:
    # Clear all chat history for the current user.
    try:
        # Get all sessions and delete them one by one
        sessions = get_chat_sessions()
        success = True
        for session in sessions:
            if not delete_chat_session(session['id']):
                success = False
        return success
    except Exception as e:
        logger.error(f'Failed to clear all chat history: {e!s}')
        return False


def submit_message_feedback(
    message_id: int,
    feedback_type: str,
    rating: int | None = None,
    feedback_text: str | None = None,
) -> bool:
    # Submit feedback for a message.

    try:
        # Validate message_id
        if not message_id or not isinstance(message_id, int):
            logger.error(f'Invalid message ID: {message_id}')
            return False

        # Validate feedback_type
        valid_types = ['thumbs_up', 'thumbs_down', 'rating', 'comment']
        if feedback_type not in valid_types:
            logger.error(f'Invalid feedback type: {feedback_type}')
            return False

        logger.info(
            f'Submitting feedback for message ID: {message_id}, type: {feedback_type}',
        )

        # Only set default ratings if none is provided and we need to
        # This allows the caller to explicitly pass rating=None
        if rating is None and feedback_type == 'rating':
            # For rating type, a rating is required
            logger.error('Rating is required for feedback_type="rating"')
            return False

        logger.debug(
            f'Making API call with params: message_id={message_id}, '
            f'feedback_type={feedback_type}, rating={rating}, '
            f'has_comment={feedback_text is not None}',
        )

        api_client = get_api_client()

        # Submit feedback using cookie authentication
        response = api_client.submit_feedback(
            message_id,
            feedback_type,
            rating,
            feedback_text,
        )

        if 'error' in response:
            logger.error(f'Feedback submission failed: {response["error"]}')
            st.error(f'Failed to save feedback: {response["error"]}')
            return False

        logger.info(f'Feedback submitted successfully for message ID: {message_id}')
        return True
    except Exception as e:
        logger.error(f'Error submitting feedback: {e!s}')
        st.error(f'Failed to save feedback: {e!s}')
        return False
