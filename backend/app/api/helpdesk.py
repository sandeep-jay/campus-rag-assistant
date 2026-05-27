"""Helpdesk escalation endpoints.

Three endpoints under ``/api/helpdesk``:

- ``POST /summarize`` — narrative conversation recap (the Summarize button).
- ``POST /draft-ticket`` — structured ticket extraction for the review modal.
- ``POST /create-issue`` — file a reviewed ticket draft as a GitHub issue.

All endpoints require auth and inherit chat rate limiting. The router 404s
when ``HELPDESK_ENABLED`` is false, so the feature stays dark in environments
without a configured demo repo / PAT.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.config_manager import settings
from backend.app.core.rate_limit import limit_chat
from backend.app.core.security import get_current_user
from backend.app.models.user import User
from backend.app.schemas.helpdesk import (
    CreateIssueRequest,
    CreateIssueResponse,
    DraftTicketResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from backend.app.services.helpdesk.agent import draft_ticket, recap_conversation
from backend.app.services.helpdesk.github import create_github_issue


def _require_enabled() -> None:
    if not settings.HELPDESK_ENABLED:
        raise HTTPException(status_code=404, detail='Helpdesk is not enabled.')


router = APIRouter(
    prefix='/api/helpdesk',
    tags=['helpdesk'],
    dependencies=[Depends(_require_enabled)],
)


@router.post('/summarize', response_model=SummarizeResponse, dependencies=[Depends(limit_chat)])
async def summarize(
    request: SummarizeRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> SummarizeResponse:
    """Produce a narrative recap of the conversation for inline display."""
    summary = await recap_conversation(request.conversation)
    return SummarizeResponse(summary=summary)


@router.post('/draft-ticket', response_model=DraftTicketResponse, dependencies=[Depends(limit_chat)])
async def draft_ticket_endpoint(
    request: SummarizeRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> DraftTicketResponse:
    """Extract a structured ticket draft from conversation history."""
    draft = await draft_ticket(request.conversation)
    return DraftTicketResponse(draft=draft)


@router.post('/create-issue', response_model=CreateIssueResponse, dependencies=[Depends(limit_chat)])
async def create_issue(
    request: CreateIssueRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CreateIssueResponse:
    return await create_github_issue(request.draft, user_id=current_user.id)
