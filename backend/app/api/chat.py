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

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config_manager import settings
from backend.app.core.logger import logger
from backend.app.core.security import get_current_user
from backend.app.db.database import get_db
from backend.app.models.user import User
from backend.app.schemas.chat import ChatMessageCreate, ChatSessionCreate
from backend.app.schemas.feedback import Feedback, FeedbackCreate
from backend.app.services.db import DatabaseService
from backend.app.services.rag import RAGService
from backend.app.utils.simple_tracer import trace_rag

router = APIRouter()
# Removed module-level instance to avoid initialization issues


# Create a function to get a properly initialized RAG service
def get_rag_service():
    """Get a properly initialized RAG service instance."""
    try:
        service = RAGService()
        logger.info('RAG service initialized successfully')
        return service
    except Exception as e:
        logger.exception(f'Failed to initialize RAG service: {e}')
        # Return a mock instance that will handle the error gracefully
        service = RAGService()
        service.is_mock = True
        return service


@router.post('/sessions')
async def create_chat_session(
    session: ChatSessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    logger.info(f'Creating chat session for user {current_user.username}')
    db_service = DatabaseService(db)
    chat_session = db_service.create_chat_session(
        user_id=current_user.id,
        title=session.title,
    )
    logger.info(f'Chat session created with ID: {chat_session.id}')
    return {
        'id': chat_session.id,
        'title': chat_session.title,
        'created_at': chat_session.created_at,
    }


@router.get('/sessions')
async def get_chat_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    logger.info(f'Getting chat sessions for user {current_user.username}')
    db_service = DatabaseService(db)
    sessions = db_service.get_user_chat_sessions(current_user.id)
    logger.info(
        f'Retrieved {len(sessions)} chat sessions for user {current_user.username}',
    )
    return [
        {
            'id': session.id,
            'title': session.title,
            'created_at': session.created_at,
        }
        for session in sessions
    ]


@router.get('/sessions/{session_id}')
async def get_chat_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    logger.info(f'Getting chat session {session_id} for user {current_user.username}')
    db_service = DatabaseService(db)
    session = db_service.get_chat_session(session_id)

    if not session:
        logger.warning(f'Chat session {session_id} not found')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Chat session not found',
        )

    if session.user_id != current_user.id:
        logger.warning(
            f'User {current_user.username} not authorized to access session {session_id}',
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not authorized to access this chat session',
        )

    messages = [
        {
            'id': msg.id,
            'content': msg.content,
            'role': msg.role,
            'metadata': msg.message_meta,
            'created_at': msg.created_at,
        }
        for msg in session.messages
    ]

    logger.info(f'Retrieved session {session_id} with {len(messages)} messages')
    return {
        'id': session.id,
        'title': session.title,
        'created_at': session.created_at,
        'messages': messages,
    }


@router.post('/sessions/{session_id}/messages')
async def create_chat_message(
    session_id: int,
    message: ChatMessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    logger.info(
        f'Creating message in session {session_id} for user {current_user.username}',
    )
    db_service = DatabaseService(db)
    session = db_service.get_chat_session(session_id)

    if not session:
        logger.warning(f'Chat session {session_id} not found')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Chat session not found',
        )

    if session.user_id != current_user.id:
        logger.warning(
            f'User {current_user.username} not authorized to access session {session_id}',
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not authorized to access this chat session',
        )

    # Create user message
    user_msg = db_service.create_chat_message(
        session_id=session_id,
        content=message.content,
        role='user',
    )

    # Initialize the RAG service for this request
    rag_service = get_rag_service()

    @trace_rag
    def process_message(content):
        return rag_service.process_query(content)

    rag_response = process_message(message.content)
    logger.debug('RAG processing complete, storing assistant message')

    # Create assistant message
    assistant_msg = db_service.create_chat_message(
        session_id=session_id,
        content=rag_response['message'],
        role='assistant',
        metadata=rag_response.get('metadata', {}),
    )

    return {
        'user_message': {
            'id': user_msg.id,
            'content': user_msg.content,
            'role': user_msg.role,
            'created_at': user_msg.created_at,
        },
        'assistant_message': {
            'id': assistant_msg.id,
            'content': assistant_msg.content,
            'role': assistant_msg.role,
            'metadata': assistant_msg.message_meta,
            'created_at': assistant_msg.created_at,
        },
    }


@router.delete('/sessions/{session_id}')
async def delete_chat_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    logger.info(f'Deleting chat session {session_id} for user {current_user.username}')
    db_service = DatabaseService(db)
    session = db_service.get_chat_session(session_id)

    if not session:
        logger.warning(f'Chat session {session_id} not found')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Chat session not found',
        )

    if session.user_id != current_user.id:
        logger.warning(
            f'User {current_user.username} not authorized to delete session {session_id}',
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not authorized to delete this chat session',
        )

    db_service.delete_chat_session(session_id)
    logger.info(f'Successfully deleted chat session {session_id}')
    return {'message': 'Chat session deleted successfully'}


@router.post('/chat')
async def chat(
    message: ChatMessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    # Handle chat messages with optional session creation.
    logger.info(f'Processing chat message from user {current_user.username}')
    db_service = DatabaseService(db)

    # If session_id is provided, use it, otherwise create a new session
    session_id = message.session_id
    if not session_id:
        # Create a new chat session with the first few words as title
        title = f'Chat: {message.content[:20]}...' if len(message.content) > 20 else message.content
        session = db_service.create_chat_session(
            user_id=current_user.id,
            title=title,
        )
        session_id = session.id
    else:
        # Verify the session exists and belongs to the user
        session = db_service.get_chat_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Chat session not found',
            )
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Not authorized to access this chat session',
            )

    # Create user message
    user_msg = db_service.create_chat_message(
        session_id=session_id,
        content=message.content,
        role='user',
    )

    # Get chat history for context
    chat_history = []
    session_messages = db_service.get_session_messages(session_id)
    # Format messages for LangChain
    for msg in session_messages:
        chat_history.append(
            (msg.content, '') if msg.role == 'user' else ('', msg.content),
        )

    # Initialize the RAG service for this request
    rag_service = get_rag_service()

    @trace_rag
    def process_chat(content, history):
        return rag_service.process_query(content, history)

    try:
        rag_response = process_chat(message.content, chat_history)

        # Create assistant message
        assistant_msg = db_service.create_chat_message(
            session_id=session_id,
            content=rag_response['message'],
            role='assistant',
            metadata=rag_response.get('metadata', {}),
        )

        # Return the response
        return {
            'user_message': {
                'id': user_msg.id,
                'content': user_msg.content,
                'role': user_msg.role,
                'created_at': user_msg.created_at,
            },
            'assistant_message': {
                'id': assistant_msg.id,
                'content': assistant_msg.content,
                'role': assistant_msg.role,
                'metadata': assistant_msg.message_meta,
                'created_at': assistant_msg.created_at,
            },
        }
    except Exception as e:
        logger.exception(f'Error generating response: {e!s}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error generating response: {e!s}',
        )


@router.post('/feedback')
async def submit_feedback(
    feedback: FeedbackCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Feedback:
    # Submit feedback for a message.
    logger.info(
        f'Received feedback request: message_id={feedback.message_id}, type={feedback.feedback_type}, rating={feedback.rating}',
    )

    db_service = DatabaseService(db)

    # Verify the message exists and belongs to the user
    message = db_service.get_message(feedback.message_id)
    if not message:
        logger.warning(
            f'Feedback submission failed: Message ID {feedback.message_id} not found',
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Message not found',
        )

    # Verify the message belongs to a session owned by the user
    session = db_service.get_chat_session(message.session_id)
    if not session or session.user_id != current_user.id:
        logger.warning(
            f'Feedback submission failed: User {current_user.id} not authorized for message {feedback.message_id}',
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not authorized to provide feedback for this message',
        )

    try:
        # Create the feedback
        logger.info(
            f'Creating feedback record in database: user_id={current_user.id}, message_id={feedback.message_id}',
        )
        db_feedback = db_service.create_feedback(
            message_id=feedback.message_id,
            user_id=current_user.id,
            feedback_type=feedback.feedback_type,
            rating=feedback.rating,
            comment=feedback.comment,
        )

        logger.info(f'Feedback successfully created: id={db_feedback.id}')
        return db_feedback
    except Exception as e:
        logger.exception(f'Error creating feedback: {e!s}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to create feedback: {e!s}',
        )


@router.post('/test_langsmith')
async def test_langsmith() -> dict[str, Any]:
    # Test endpoint for LangSmith tracing with trace_rag.
    # Check if LangSmith tracing is enabled
    if not settings.LANGCHAIN_TRACING_V2 or not settings.LANGCHAIN_API_KEY:
        logger.warning('LangSmith tracing is not enabled')
        return {
            'success': False,
            'message': 'LangSmith tracing not enabled',
            'trace_enabled': settings.LANGCHAIN_TRACING_V2,
            'api_key_present': bool(settings.LANGCHAIN_API_KEY),
            'project': settings.LANGCHAIN_PROJECT,
            'status': 'DISABLED',
        }

    try:
        # Import the client getter directly to check status
        from backend.app.utils.simple_tracer import get_client

        # Force refresh client to ensure we have the latest settings
        langsmith_client = get_client()

        if not langsmith_client:
            return {
                'success': False,
                'message': 'LangSmith client not initialized in simple_tracer',
                'trace_enabled': settings.LANGCHAIN_TRACING_V2,
                'api_key_present': bool(settings.LANGCHAIN_API_KEY),
                'project': settings.LANGCHAIN_PROJECT,
                'status': 'CLIENT_INIT_FAILED',
            }

        logger.info(f'Testing LangSmith tracing with project: {settings.LANGCHAIN_PROJECT}')

        # Define a simple test function that we can trace
        @trace_rag
        def test_trace_function(text: str) -> str:
            logger.info(f'Traced function called with: {text}')
            return f'Echo: {text}'

        # Execute the test function with tracing
        try:
            test_content = 'Testing trace_rag decorator from simple_tracer'
            result = test_trace_function(test_content)

            # Test if we can list runs to verify connection works
            try:
                # Attempt to list a single run to verify API connection
                runs = list(langsmith_client.list_runs(project_name=settings.LANGCHAIN_PROJECT, limit=1))
                run_count = len(runs)

                return {
                    'success': True,
                    'message': 'Successfully traced test function to LangSmith',
                    'project': settings.LANGCHAIN_PROJECT,
                    'response': result,
                    'client_status': 'READY',
                    'runs_found': run_count,
                    'status': 'SUCCESS',
                }
            except Exception as api_e:
                # Connection issue with the API
                return {
                    'success': False,
                    'message': f'Client initialized but API connection failed: {api_e}',
                    'project': settings.LANGCHAIN_PROJECT,
                    'trace_result': result,
                    'status': 'API_CONNECTION_FAILED',
                }

        except Exception as e:
            logger.exception(f'Failed during trace execution: {e}')
            return {
                'success': False,
                'message': f'Trace execution failed: {e}',
                'trace_enabled': settings.LANGCHAIN_TRACING_V2,
                'project': settings.LANGCHAIN_PROJECT,
                'status': 'TRACE_FAILED',
            }

    except Exception as e:
        logger.exception(f'LangSmith test failed: {e!s}')
        return {
            'success': False,
            'message': f'LangSmith test failed: {e!s}',
            'trace_enabled': settings.LANGCHAIN_TRACING_V2,
            'project': settings.LANGCHAIN_PROJECT,
            'status': 'TEST_ERROR',
        }


@router.get('/messages/{message_id}/sources')
async def get_message_sources(
    message_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    # Get the source documents for a specific message.
    db_service = DatabaseService(db)
    message = db_service.get_message(message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Message not found',
        )

    # Verify the message belongs to a session owned by the user
    session = db_service.get_chat_session(message.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not authorized to access this message',
        )

    # Extract source documents from metadata
    metadata = message.message_meta or {}
    document_contents = metadata.get('document_contents', [])
    sources = metadata.get('sources', [])

    return {
        'message_id': message_id,
        'document_contents': document_contents,
        'sources': sources,
    }
