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

from unittest.mock import patch

from fastapi import status
from starlette.testclient import TestClient


def test_delete_chat_session(client: TestClient, test_user_token: str) -> None:
    """Test deleting a chat session."""
    # First create a session
    response = client.post(
        '/api/chat/sessions',
        json={'title': 'Test Chat for Deletion'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_200_OK
    session_id = response.json()['id']

    # Now delete the session
    response = client.delete(
        f'/api/chat/sessions/{session_id}',
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['message'] == 'Chat session deleted successfully'

    # Try to get the deleted session
    response = client.get(
        f'/api/chat/sessions/{session_id}',
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_nonexistent_chat_session(
    client: TestClient,
    test_user_token: str,
) -> None:
    """Test deleting a chat session that doesn't exist."""
    response = client.delete(
        '/api/chat/sessions/999',
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_chat_endpoint(client: TestClient, test_user_token: str) -> None:
    """Test the standalone chat endpoint."""
    response = client.post(
        '/api/chat/chat',
        json={'content': 'Hello, this is a test message'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert 'user_message' in data
    assert 'assistant_message' in data
    assert data['user_message']['content'] == 'Hello, this is a test message'
    assert data['assistant_message']['role'] == 'assistant'


@patch('backend.app.api.chat.get_rag_service')
def test_chat_with_mock_rag(mock_get_rag_service, client: TestClient, test_user_token: str) -> None:
    """Test the chat endpoint with a mocked RAG service."""
    # Set up the mock response
    mock_rag_service = mock_get_rag_service.return_value
    mock_rag_service.process_query.return_value = {
        'message': 'This is a mock response',
        'metadata': {'sources': [], 'document_contents': []},
    }

    # Test the endpoint
    response = client.post(
        '/api/chat/chat',
        json={'content': 'Hello, this is a test message'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify the mock was called
    mock_rag_service.process_query.assert_called_once()

    # Check the response
    assert data['assistant_message']['content'] == 'This is a mock response'


def test_submit_feedback(client: TestClient, test_user_token: str) -> None:
    """Test submitting feedback for a message."""
    # First create a session and send a message
    response = client.post(
        '/api/chat/sessions',
        json={'title': 'Test Chat for Feedback'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    session_id = response.json()['id']

    # Send a message
    response = client.post(
        f'/api/chat/sessions/{session_id}/messages',
        json={'content': 'This is a message for feedback'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_200_OK
    message_id = response.json()['assistant_message']['id']

    # Submit feedback
    response = client.post(
        '/api/chat/feedback',
        json={
            'message_id': message_id,
            'feedback_type': 'thumbs_up',
            'rating': 5,
            'comment': 'Great response!',
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['feedback_type'] == 'thumbs_up'
    assert response.json()['rating'] == 5
    assert response.json()['comment'] == 'Great response!'


def test_get_message_sources(client: TestClient, test_user_token: str) -> None:
    """Test getting sources for a message."""
    # First create a session and send a message
    response = client.post(
        '/api/chat/sessions',
        json={'title': 'Test Chat for Sources'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    session_id = response.json()['id']

    # Send a message
    response = client.post(
        f'/api/chat/sessions/{session_id}/messages',
        json={'content': 'This is a message to get sources for'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_200_OK
    message_id = response.json()['assistant_message']['id']

    # Get sources
    response = client.get(
        f'/api/chat/messages/{message_id}/sources',
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == status.HTTP_200_OK
    assert 'sources' in response.json()
    assert 'document_contents' in response.json()
