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

from pathlib import Path

from dotenv import load_dotenv

# Load env before any backend import (settings reads os.environ at import time)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / '.env.test')
load_dotenv(_PROJECT_ROOT / '.env', override=True)

import os

# Developer .env may set RAG_ENGINE=langgraph; API tests mock the chain stream path.
_ragas_eval = os.environ.get('RAGAS_EVAL', '').lower() in ('1', 'true', 'yes')
if not _ragas_eval:
    os.environ['RAG_ENGINE'] = 'chain'
elif not os.environ.get('RAG_ENGINE', '').strip():
    os.environ['RAG_ENGINE'] = 'langgraph'

# API tests exercise graph control flow, not durable Postgres checkpointing,
# unless a test opts into the Postgres integration path explicitly.
os.environ.setdefault('HELPDESK_AGENT_CHECKPOINT_BACKEND', 'memory')

# tox -e eval sets RAGAS_EVAL=1 — avoid LangSmith + Bedrock stream teardown noise
if _ragas_eval:
    os.environ['LANGCHAIN_TRACING_V2'] = 'false'
    os.environ['LANGSMITH_TRACING'] = 'false'
    os.environ['LANGCHAIN_API_KEY'] = ''  # skip LangSmith HTTP during eval


import subprocess
import uuid
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.services.db import DatabaseService
from backend.app.services.rag import RAGService


@pytest.fixture(scope='session')
def engine():
    # Get PostgreSQL connection details from environment
    postgres_host = os.environ.get('POSTGRES_HOST', 'localhost')
    postgres_port = os.environ.get('POSTGRES_PORT', '5432')
    postgres_user = os.environ.get('POSTGRES_USER', 'chatbot')
    postgres_password = os.environ.get('POSTGRES_PASSWORD', 'chatbot')
    postgres_db = os.environ.get('POSTGRES_DB', 'chatbot_test')

    # Use PostgreSQL for tests with 'chatbot_test' database
    test_db_url = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'

    # Create test database if it doesn't exist
    try:
        # Check if database exists
        result = subprocess.run(
            [
                'psql',
                '-U',
                postgres_user,
                '-h',
                postgres_host,
                '-p',
                postgres_port,
                '-lqt',
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        existing_dbs = result.stdout.strip()
        if f' {postgres_db} ' not in existing_dbs:
            # Create the database
            subprocess.run(
                [
                    'createdb',
                    '-U',
                    postgres_user,
                    '-h',
                    postgres_host,
                    '-p',
                    postgres_port,
                    postgres_db,
                ],
                check=True,
            )
            print(f'Created test database: {postgres_db}')
    except Exception as e:
        print(f'Warning: Failed to check/create database: {e}')

    # Now connect to the test database
    db_url = test_db_url

    # Create engine
    engine = create_engine(db_url)

    # Drop all tables if they exist and recreate them
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield engine

    # Clean up after all tests are done
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope='session')
def testing_session_local(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db(testing_session_local) -> Generator:
    session = testing_session_local()
    try:
        yield session
    finally:
        # Clean up the database after each test
        # Make sure we rollback any pending transactions first
        session.rollback()
        # Then clear all data
        for table in reversed(Base.metadata.sorted_tables):
            try:
                session.execute(table.delete())
                session.commit()
            except Exception:
                session.rollback()
                # Try again with a fresh transaction
                session.execute(table.delete())
                session.commit()
        session.close()


@pytest.fixture()
def client(db) -> TestClient:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture()
def db_test_user(db) -> User:
    unique_id = str(uuid.uuid4())[:8]
    db_service = DatabaseService(db)
    return db_service.create_user(
        username=f'testuser_{unique_id}',
        email=f'test_{unique_id}@example.com',
        password='testpassword123',
    )


@pytest.fixture()
def test_user() -> dict[str, str]:
    unique_id = str(uuid.uuid4())[:8]
    return {
        'username': f'testuser_{unique_id}',
        'email': f'test_{unique_id}@example.com',
        'password': 'testpassword123',
    }


@pytest.fixture()
def test_user_token(client: TestClient, db_test_user: User) -> str:
    # Login and get token
    response = client.post(
        '/api/auth/token',
        data={'username': db_test_user.username, 'password': 'testpassword123'},
    )
    return response.json()['access_token']


@pytest.fixture(autouse=True)
def mock_rag_service():
    """Mock the RAG service for all tests."""
    with patch('backend.app.api.chat.get_rag_service') as mock_get_rag_service:
        # Create a mock RAG service
        mock_rag = MagicMock(spec=RAGService)
        mock_rag.is_mock = True
        mock_rag.process_query.return_value = {
            'message': 'This is a mock response',
            'metadata': {
                'sources': [
                    {
                        'source': 'Test Source',
                        'kb_url': 'https://example.com/test',
                        'kb_number': 'KB-001',
                        'kb_category': 'Test',
                        'short_description': 'Test description',
                        'project': 'Test Project',
                        'ingestion_date': '2024-01-01',
                        'score': 0.95,
                    }
                ],
                'document_contents': [
                    {
                        'content': 'Test content',
                        'metadata': {
                            'source': 'Test Source',
                            'kb_url': 'https://example.com/test',
                            'kb_number': 'KB-001',
                            'kb_category': 'Test',
                            'short_description': 'Test description',
                            'project': 'Test Project',
                            'ingestion_date': '2024-01-01',
                            'score': 0.95,
                        },
                    }
                ],
            },
        }

        def _default_stream(query, chat_history=None, tenant_config=None):
            yield {'type': 'token', 'token': mock_rag.process_query.return_value['message']}
            yield {'type': 'done', 'metadata': mock_rag.process_query.return_value['metadata']}

        mock_rag.stream_query.side_effect = _default_stream
        mock_rag._normalize_answer_formatting.side_effect = lambda text, _sources=None: text
        mock_get_rag_service.return_value = mock_rag
        yield mock_rag
