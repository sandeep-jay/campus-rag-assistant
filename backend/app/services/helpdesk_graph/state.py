"""Internal state models for the helpdesk agent graph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.app.schemas.helpdesk import ConversationTurn, TicketDraft


class GitHubIssue(BaseModel):
    """Small, sanitized representation of a GitHub issue search hit."""

    number: int
    title: str
    state: str = 'open'
    url: str
    body: str | None = None


class ProposedSolution(BaseModel):
    """Future Phase-C shape for proposed fixes from KB/web evidence."""

    title: str
    summary: str
    source_url: str | None = None


class AwaitingUserPayload(BaseModel):
    """Future Phase-B payload for clarifying questions."""

    question_id: str
    question: str
    choices: list[str] = Field(default_factory=list)


class HelpdeskState(TypedDict, total=False):
    state_version: int
    session_id: str
    user_id: int | str
    original_question: str
    conversation: list[ConversationTurn]
    turns_taken: int
    questions_asked: list[str]
    user_replies: list[str]
    duplicate_candidates: list[GitHubIssue]
    kb_retry_results: list[Any]
    web_search_results: list[Any]
    tool_cache: dict[str, Any]
    proposed_solutions: list[ProposedSolution]
    rejected_solutions: list[str]
    facts: dict[str, str]
    draft: TicketDraft | None
    next_action: Literal[
        'retry_kb',
        'web_search',
        'search_duplicates',
        'ask_user',
        'propose_solution',
        'write_draft',
        'await_user_confirm',
        'file_new',
        'link_existing',
        'resolved_by_agent',
        'abort',
    ]
    awaiting_user: AwaitingUserPayload | None
    outcome: Literal['filed', 'linked', 'resolved_by_agent', 'aborted'] | None
