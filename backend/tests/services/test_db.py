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

import pytest
from sqlalchemy.orm import Session

from backend.app.services.db import DatabaseService

# Define constants to avoid magic numbers
NUM_TEST_USERS = 2
NUM_TEST_MESSAGES = 2

"""Tests for the database service module."""


@pytest.fixture()
def db_service(db: Session) -> DatabaseService:
    """Create and return a DatabaseService instance for testing."""
    return DatabaseService(db)


def test_get_user(db: Session) -> None:
    """Test getting a user from the database."""
    db_service = DatabaseService(db)
    user = db_service.create_user(
        username='test_get',
        email='test_get@example.com',
        password='password',
    )
    assert user.id is not None
    assert user.username == 'test_get'
    assert user.email == 'test_get@example.com'


def test_get_user_by_email(db: Session) -> None:
    """Test getting a user by email from the database."""
    db_service = DatabaseService(db)
    db_service.create_user(
        username='test_email',
        email='test_email@example.com',
        password='password',
    )
    db_user = db_service.get_user_by_email('test_email@example.com')
    assert db_user is not None
    assert db_user.username == 'test_email'
    assert db_user.email == 'test_email@example.com'


def test_get_user_by_username(db: Session) -> None:
    """Test getting a user by username from the database."""
    db_service = DatabaseService(db)
    db_service.create_user(
        username='test_username',
        email='test_username@example.com',
        password='password',
    )
    db_user = db_service.get_user_by_username('test_username')
    assert db_user is not None
    assert db_user.username == 'test_username'
    assert db_user.email == 'test_username@example.com'


def test_create_user(db: Session) -> None:
    """Test creating a user in the database."""
    db_service = DatabaseService(db)
    user = db_service.create_user(
        username='test_create',
        email='test_create@example.com',
        password='password',
    )
    assert user.id is not None
    assert user.username == 'test_create'
    assert user.email == 'test_create@example.com'
    assert user.verify_password('password')
    assert not user.verify_password('wrong_password')


def test_get_users(db: Session) -> None:
    """Test getting all users from the database."""
    db_service = DatabaseService(db)
    db_service.create_user(
        username='test1',
        email='test1_list@example.com',
        password='password',
    )
    db_service.create_user(
        username='test2',
        email='test2_list@example.com',
        password='password',
    )
    users = db_service.get_users()
    assert len(users) == NUM_TEST_USERS


def test_authenticate_user(db: Session) -> None:
    """Test authenticating a user."""
    db_service = DatabaseService(db)
    db_service.create_user(
        username='test_auth',
        email='test_auth@example.com',
        password='password',
    )
    user = db_service.authenticate_user('test_auth', 'password')
    assert user is not None
    assert user.username == 'test_auth'
    assert user.email == 'test_auth@example.com'

    # Test with wrong password
    user = db_service.authenticate_user('test_auth', 'wrong_password')
    assert user is None

    # Test with non-existent user
    user = db_service.authenticate_user('nonexistent', 'password')
    assert user is None


def test_create_chat_session(db: Session) -> None:
    """Test creating a chat session."""
    db_service = DatabaseService(db)
    user = db_service.create_user(
        username='test_chat',
        email='test_chat@example.com',
        password='password',
    )
    session = db_service.create_chat_session(user_id=user.id, title='Test Session')
    assert session.id is not None
    assert session.user_id == user.id
    assert session.title == 'Test Session'


def test_get_user_chat_sessions(db: Session) -> None:
    """Test getting chat sessions for a user."""
    db_service = DatabaseService(db)
    user = db_service.create_user(
        username='test_sessions',
        email='test_sessions@example.com',
        password='password',
    )
    db_service.create_chat_session(user_id=user.id, title='Test Session 1')
    db_service.create_chat_session(user_id=user.id, title='Test Session 2')
    sessions = db_service.get_user_chat_sessions(user.id)
    assert len(sessions) == NUM_TEST_USERS
    assert sessions[0].title in ['Test Session 1', 'Test Session 2']
    assert sessions[1].title in ['Test Session 1', 'Test Session 2']


def test_create_chat_message(db: Session) -> None:
    """Test creating chat messages with and without metadata."""
    db_service = DatabaseService(db)
    user = db_service.create_user(
        username='test_message',
        email='test_message@example.com',
        password='password',
    )
    session = db_service.create_chat_session(user_id=user.id, title='Test Session')

    # Test creating message without metadata
    message1 = db_service.create_chat_message(
        session_id=session.id,
        content='Hello',
        role='user',
    )
    assert message1.id is not None
    assert message1.session_id == session.id
    assert message1.content == 'Hello'
    assert message1.role == 'user'
    assert message1.message_meta is None

    # Test creating message with metadata
    message2 = db_service.create_chat_message(
        session_id=session.id,
        content='Response',
        role='assistant',
        metadata=[{'source': 'test', 'relevance': 0.9}],
    )
    assert message2.id is not None
    assert message2.session_id == session.id
    assert message2.content == 'Response'
    assert message2.role == 'assistant'
    assert message2.message_meta == [{'source': 'test', 'relevance': 0.9}]


def test_get_session_messages(db: Session) -> None:
    """Test getting messages for a chat session."""
    db_service = DatabaseService(db)
    user = db_service.create_user(
        username='test_get_messages',
        email='test_get_messages@example.com',
        password='password',
    )
    session = db_service.create_chat_session(user_id=user.id, title='Test Session')
    db_service.create_chat_message(session_id=session.id, content='Hello', role='user')
    db_service.create_chat_message(
        session_id=session.id,
        content='Response',
        role='assistant',
    )

    messages = db_service.get_session_messages(session.id)
    assert len(messages) == NUM_TEST_MESSAGES
    assert messages[0].content == 'Hello'
    assert messages[0].role == 'user'
    assert messages[1].content == 'Response'
    assert messages[1].role == 'assistant'


def test_delete_chat_session(db: Session) -> None:
    """Test deleting a chat session and its messages."""
    db_service = DatabaseService(db)
    user = db_service.create_user(
        username='test_delete',
        email='test_delete@example.com',
        password='password',
    )
    session = db_service.create_chat_session(user_id=user.id, title='Test Session')

    # Add some messages
    db_service.create_chat_message(session_id=session.id, content='Hello', role='user')
    db_service.create_chat_message(
        session_id=session.id,
        content='Response',
        role='assistant',
    )

    # Verify session exists
    assert db_service.get_chat_session(session.id) is not None

    # Delete session
    result = db_service.delete_chat_session(session.id)
    assert result is True

    # Verify session and messages are deleted
    assert db_service.get_chat_session(session.id) is None
    assert len(db_service.get_session_messages(session.id)) == 0
