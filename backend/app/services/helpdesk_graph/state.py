"""Internal state models for the helpdesk agent graph."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field

# Imported at runtime (not under ``TYPE_CHECKING``) because LangGraph's
# ``StateGraph`` resolves the TypedDict's annotations via
# ``typing.get_type_hints`` when compiling the channel schema; deferred
# annotations break that resolution.
from backend.app.schemas.helpdesk import AgentStep, AgentTurn, ConversationTurn, TicketDraft  # noqa: TCH001


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
    created_at: float
    deadline_at: float
    original_question: str
    conversation: list[ConversationTurn]
    turns_taken: int
    questions_asked: list[str]
    user_replies: list[str]
    tool_attempts: int
    duplicate_candidates: list[GitHubIssue]
    kb_retry_results: list[Any]
    web_search_results: list[Any]
    web_search_consent: Literal['pending', 'granted', 'denied'] | None
    solution_source_kind: Literal['kb', 'web'] | None
    tool_cache: dict[str, Any]
    proposed_solutions: list[ProposedSolution]
    rejected_solutions: list[str]
    facts: dict[str, str]
    classification_confidence: float
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
    # --- Phase 1a transient graph plumbing (stripped before checkpoint save). ---
    # ``entry`` tells the supervisor which entry point invoked the graph this
    # turn (start/resume/confirm/abort); ``_next`` is the supervisor's chosen
    # next node and is read by the routing function; ``_graph_turn`` carries
    # the final ``AgentTurn`` that the runner returns to the API layer.
    entry: Literal['start', 'resume', 'confirm', 'abort']
    resume_answer: str | None
    confirm_draft: TicketDraft | None
    _trace_seed: list[AgentStep]
    _next: str | None
    _graph_turn: AgentTurn | None
