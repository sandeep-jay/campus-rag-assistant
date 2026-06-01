"""Helpdesk agent endpoints.

Three endpoints under ``/api/helpdesk``:

- ``POST /summarize`` — narrative conversation recap (the **Summarize**
  button). Returns a :class:`ConversationSummary` the user can glance at
  inline; never produces a ticket-shaped object.
- ``POST /draft-ticket`` — structured ticket extraction (the **Create
  ticket** button). Returns a :class:`TicketDraft` that the frontend opens
  in a review modal before filing.
- ``POST /create-issue`` — file a reviewed :class:`TicketDraft` as a GitHub
  issue.

All endpoints require auth and inherit chat rate limiting. The router 404s
when ``HELPDESK_ENABLED`` is false, so the feature stays dark in
environments without a configured demo repo / PAT.
"""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.config_manager import settings
from backend.app.core.rate_limit import limit_chat
from backend.app.core.security import get_current_user
from backend.app.db.database import get_db
from backend.app.models.user import User
from backend.app.schemas.helpdesk import (
    AgentAbortRequest,
    AgentConfirmRequest,
    AgentResumeRequest,
    AgentStartRequest,
    AgentTurn,
    CreateIssueRequest,
    CreateIssueResponse,
    DraftTicketResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from backend.app.services.helpdesk.agent import draft_ticket, recap_conversation
from backend.app.services.helpdesk.github import create_github_issue
from backend.app.services.helpdesk_graph.runner import (
    abort_session,
    confirm_session,
    resume_session,
    start_session,
    stream_resume_session,
    stream_start_session,
)


def _require_enabled() -> None:
    if not settings.HELPDESK_ENABLED:
        raise HTTPException(status_code=404, detail='Helpdesk is not enabled.')


router = APIRouter(
    prefix='/api/helpdesk',
    tags=['helpdesk'],
    dependencies=[Depends(_require_enabled)],
)


def _sse_payload(event: dict) -> str:
    return f'data: {json.dumps(event)}\n\n'


def _agent_turn_event(turn: AgentTurn) -> dict:
    return {'type': 'done', 'turn': turn.model_dump(mode='json')}


@router.post(
    '/summarize', response_model=SummarizeResponse, dependencies=[Depends(limit_chat)]
)
async def summarize(
    request: SummarizeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> SummarizeResponse:
    """Produce a narrative recap of the conversation for inline display."""
    summary = await recap_conversation(request.conversation)
    return SummarizeResponse(summary=summary)


@router.post(
    '/draft-ticket',
    response_model=DraftTicketResponse,
    dependencies=[Depends(limit_chat)],
)
async def draft_ticket_endpoint(
    request: SummarizeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> DraftTicketResponse:
    """Extract a structured ticket draft from conversation history."""
    draft = await draft_ticket(request.conversation)
    return DraftTicketResponse(draft=draft)


@router.post(
    '/agent/start', response_model=AgentTurn, dependencies=[Depends(limit_chat)]
)
async def start_agent(
    request: AgentStartRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> AgentTurn:
    """Start the helpdesk agent flow."""
    return await start_session(
        request.conversation,
        user_id=current_user.id,
        trigger='api',
        chat_session_id=request.chat_session_id,
        db=db,
    )


@router.post('/agent/start/stream', dependencies=[Depends(limit_chat)])
async def start_agent_stream(
    request: AgentStartRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> StreamingResponse:
    """Stream visible helpdesk-agent start progress and final turn."""

    async def _events():
        try:
            async for event in stream_start_session(
                request.conversation,
                user_id=current_user.id,
                trigger='stream',
                chat_session_id=request.chat_session_id,
                db=db,
            ):
                yield _sse_payload(event)
        except HTTPException as exc:
            yield _sse_payload({'type': 'error', 'message': str(exc.detail)})

    return StreamingResponse(_events(), media_type='text/event-stream')


@router.post(
    '/agent/resume', response_model=AgentTurn, dependencies=[Depends(limit_chat)]
)
async def resume_agent(
    request: AgentResumeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AgentTurn:
    """Resume a paused helpdesk-agent session with user clarification."""
    return await resume_session(
        request.session_id,
        user_id=current_user.id,
        reply=request.reply,
        choice=request.choice,
        pending_question_id=request.pending_question_id,
        chat_session_id=request.chat_session_id,
        db=db,
    )


@router.post('/agent/resume/stream', dependencies=[Depends(limit_chat)])
async def resume_agent_stream(
    request: AgentResumeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Stream visible helpdesk-agent resume progress and final turn."""

    async def _events():
        try:
            async for event in stream_resume_session(
                request.session_id,
                user_id=current_user.id,
                reply=request.reply,
                choice=request.choice,
                pending_question_id=request.pending_question_id,
                chat_session_id=request.chat_session_id,
                db=db,
            ):
                yield _sse_payload(event)
        except HTTPException as exc:
            yield _sse_payload({'type': 'error', 'message': str(exc.detail)})

    return StreamingResponse(_events(), media_type='text/event-stream')


@router.post(
    '/agent/confirm', response_model=AgentTurn, dependencies=[Depends(limit_chat)]
)
async def confirm_agent(
    request: AgentConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> AgentTurn:
    """File a reviewed ticket draft for an active helpdesk-agent session."""
    return await confirm_session(
        request.session_id,
        user_id=current_user.id,
        draft=request.draft,
        idempotency_key=idempotency_key,
        chat_session_id=request.chat_session_id,
        db=db,
    )


@router.post(
    '/agent/abort', response_model=AgentTurn, dependencies=[Depends(limit_chat)]
)
async def abort_agent(
    request: AgentAbortRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AgentTurn:
    """Abort an active helpdesk-agent session without filing a ticket."""
    return await abort_session(
        request.session_id,
        user_id=current_user.id,
        chat_session_id=request.chat_session_id,
        db=db,
    )


@router.post(
    '/create-issue',
    response_model=CreateIssueResponse,
    dependencies=[Depends(limit_chat)],
)
async def create_issue(
    request: CreateIssueRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CreateIssueResponse:
    return await create_github_issue(request.draft, user_id=current_user.id)
