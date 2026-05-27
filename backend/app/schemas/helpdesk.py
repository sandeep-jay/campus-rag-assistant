"""Pydantic schemas for the post-RAG helpdesk escalation flow.

Layout note: this lives under ``backend/app/schemas/`` because the project
reserves ``backend/app/models/`` for SQLAlchemy ORM models. Pydantic request
and response shapes belong in ``schemas``.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'
    critical = 'critical'


class Category(str, Enum):
    network = 'network'
    access = 'access'
    application = 'application'
    hardware = 'hardware'
    account = 'account'
    other = 'other'


class Impact(str, Enum):
    single_user = 'Single user'
    team = 'Team'
    campus_wide = 'Campus-wide'


class ConversationTurn(BaseModel):
    role: str = Field(description="'user' or 'assistant'")
    content: str


class ConversationSummary(BaseModel):
    """Plain-text narrative recap of a conversation."""

    summary: str = Field(min_length=1)


class TicketDraft(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    severity: Severity
    category: Category
    steps_to_reproduce: str | None = None
    impact: Impact


class SummarizeRequest(BaseModel):
    """Shared input shape for both recap and draft-ticket endpoints."""

    conversation: list[ConversationTurn]


class SummarizeResponse(BaseModel):
    """Response shape for ``/api/helpdesk/summarize`` (narrative recap)."""

    summary: ConversationSummary


class DraftTicketResponse(BaseModel):
    """Response shape for ``/api/helpdesk/draft-ticket`` (structured draft)."""

    draft: TicketDraft


class CreateIssueRequest(BaseModel):
    draft: TicketDraft


class CreateIssueResponse(BaseModel):
    issue_url: str
    issue_number: int
    deduplicated: bool = False
