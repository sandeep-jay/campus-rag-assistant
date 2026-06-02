"""Pydantic schemas for the helpdesk agent (post-RAG escalation flow).

Layout note: this lives under ``backend/app/schemas/`` because the project
reserves ``backend/app/models/`` for SQLAlchemy ORM models. Pydantic request
and response shapes belong in ``schemas``.

Two independent agent tasks share these schemas:

- **Recap** (``/api/helpdesk/summarize``) — narrative ``ConversationSummary``
  the user can glance at inline.
- **Draft ticket** (``/api/helpdesk/draft-ticket``) — structured ``TicketDraft``
  the user reviews and files as a GitHub issue.

Both endpoints accept the same ``SummarizeRequest`` payload (a list of
``ConversationTurn``s).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

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
    """Plain-text narrative recap of a conversation.

    Independent of ``TicketDraft`` — this is what Summarize emits inline,
    not a ticket-shaped structure.
    """

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


class AgentStartRequest(BaseModel):
    """Start a helpdesk-agent session from chat history."""

    conversation: list[ConversationTurn]
    # Chat session that this agent run belongs to. When provided, the
    # agent's terminal summary will be persisted to chat_messages so the
    # full conversation has a durable record even after refresh.
    chat_session_id: int | None = None


class AgentResumeRequest(BaseModel):
    """Resume a paused helpdesk-agent session with the user's answer."""

    session_id: str
    reply: str | None = None
    choice: str | None = None
    pending_question_id: str | None = None
    chat_session_id: int | None = None


class AgentAbortRequest(BaseModel):
    """Abort an active helpdesk-agent session."""

    session_id: str
    chat_session_id: int | None = None


class AgentConfirmRequest(BaseModel):
    """Confirm and file a reviewed agent ticket draft."""

    session_id: str
    draft: TicketDraft
    chat_session_id: int | None = None


class AgentStep(BaseModel):
    """A compact, safe trace item for the agent's visible debug trail."""

    step: str
    action: str
    outcome: str
    message: str | None = None


class AgentSource(BaseModel):
    """Structured citation metadata aligned with chat ``metadata.sources``."""

    source: str = 'unknown'
    kb_url: str = '#'
    kb_number: str = 'N/A'
    kb_category: str = ''
    short_description: str = ''
    project: str = ''
    ingestion_date: str = ''
    score: float | None = None


class AgentDocContent(BaseModel):
    """Retrieved chunk body plus metadata for the sources panel Content tab."""

    content: str
    metadata: AgentSource


class AgentTurn(BaseModel):
    """Single response turn from the helpdesk agent."""

    session_id: str
    # Server-issued chat_messages row id for the durable summary, populated
    # only on terminal turns (filed / linked / resolved / aborted) when a
    # chat_session_id was supplied. The frontend uses this so the in-memory
    # bubble carries the same identity as the persisted record.
    chat_message_id: int | None = None
    kind: Literal['question', 'info', 'draft_ready', 'linked', 'filed', 'resolved', 'aborted']
    message: str
    choices: list[str] | None = None
    # UI hint for how ``choices`` should be rendered. ``None`` preserves the
    # legacy pill behavior (auto-submit on click) so one-tap questions like
    # solution feedback are unchanged. ``radio`` asks the frontend to render
    # a confirm-before-submit radio group; ``checkbox`` and ``text`` are
    # reserved for future multi-select and free-form clarifications.
    input: Literal['pills', 'radio', 'checkbox', 'text'] | None = None
    draft: TicketDraft | None = None
    linked_issue_url: str | None = None
    debug_trace: list[AgentStep] | None = None
    # Evidence backing a proposed solution — mirrors chat ``metadata.sources``.
    sources: list[AgentSource] | None = None
    document_contents: list[AgentDocContent] | None = None
    source_kind: Literal['kb', 'web'] | None = None
    disclaimer: str | None = None


class CreateIssueRequest(BaseModel):
    draft: TicketDraft


class CreateIssueResponse(BaseModel):
    issue_url: str
    issue_number: int
    deduplicated: bool = False
