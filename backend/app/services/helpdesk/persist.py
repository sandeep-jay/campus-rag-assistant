"""Persist the helpdesk agent's journey to ``chat_messages`` via upsert.

Background — the helpdesk agent runs on its own LangGraph state and
checkpoint store. Its intermediate turns (clarifications, draft review,
solution proposal) are valuable while the user is interacting; if we
only persisted terminal turns, refreshing mid-flow would leave holes in
the chat history (a pending question would vanish until the agent
reached ``filed``/``linked``/``resolved``/``aborted``).

To make every step of the journey durable without exploding the chat
log into one row per turn, this module upserts **one** ``role='assistant'``
row per ``agent_session_id``. The first turn inserts the row; every
subsequent turn updates the same row's content + metadata so the chat
view always reflects the agent's latest state. The persisted recap is
multi-line Markdown — heading, issue, impact, activity so far,
status/outcome — so the row reads on its own after a reload without
depending on the live ``AgentTurnBadge`` chrome.

Determinism note: the recap text is built from the ``AgentTurn`` plus
the ``HelpdeskState`` passed in from the runner. We deliberately do
*not* call an LLM here so that:

- persistence never fails because of a model timeout, and
- LangSmith traces remain clean (the agent's user-facing recap LLM
  call belongs to ``recap_conversation``, not to this side-effect).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.chat import ChatMessage, ChatSession

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from backend.app.schemas.helpdesk import AgentTurn
    from backend.app.services.helpdesk_graph.state import HelpdeskState

logger = logging.getLogger(__name__)

TERMINAL_KINDS: frozenset[str] = frozenset({'filed', 'linked', 'resolved', 'aborted'})

_KIND_HEADINGS: dict[str, str] = {
    'filed': 'Helpdesk ticket filed',
    'linked': 'Linked to an existing ticket',
    'resolved': 'Resolved without a ticket',
    'aborted': 'Helpdesk session canceled',
    'question': 'Helpdesk agent is asking a question',
    'info': 'Helpdesk agent proposed a solution',
    'draft_ready': 'Helpdesk agent drafted a ticket',
}


def _summarize_activity(state: HelpdeskState | None) -> list[str]:
    """Return bullet phrases describing what the agent did, in order.

    Inspecting the persisted state instead of the live ``debug_trace`` so
    the recap survives even if ``trace`` was trimmed for size.
    """
    if state is None:
        return []
    activity: list[str] = []
    if state.get('duplicate_candidates'):
        count = len(state['duplicate_candidates'])
        activity.append(f'Searched existing helpdesk tickets ({count} candidate(s) reviewed).')
    if state.get('kb_retry_results') is not None:
        count = len(state['kb_retry_results']) if state.get('kb_retry_results') else 0
        activity.append(f'Re-checked the knowledge base ({count} document(s)).')
    if state.get('web_search_results') is not None:
        count = len(state['web_search_results']) if state.get('web_search_results') else 0
        activity.append(f'Ran a web search ({count} result(s)).')
    proposed = state.get('proposed_solutions') or []
    rejected = state.get('rejected_solutions') or []
    if proposed:
        if rejected:
            activity.append(f'Proposed {len(proposed)} solution(s); user reported they did not solve the issue.')
        else:
            activity.append(f'Proposed {len(proposed)} solution(s).')
    return activity


_STATUS_LINES: dict[str, str] = {
    'resolved': '**Outcome:** Resolved without filing — the proposed solution worked.',
    'aborted': '**Outcome:** Canceled without filing a ticket.',
    'question': '**Status:** Waiting on your reply.',
    'info': '**Status:** Solution proposed — waiting on your feedback.',
    'draft_ready': '**Status:** Draft ready for your review.',
}


def _summarize_outcome(turn: AgentTurn, state: HelpdeskState | None) -> str:
    """Return the closing line for the turn, with inline link or live status."""
    if turn.kind == 'filed' and turn.linked_issue_url:
        label = _issue_label_from_url(turn.linked_issue_url) or 'View ticket'
        return f'**Outcome:** Filed [{label}]({turn.linked_issue_url}). The helpdesk team will follow up there.'
    if turn.kind == 'linked' and turn.linked_issue_url:
        label = _issue_label_from_url(turn.linked_issue_url) or 'View ticket'
        return f'**Outcome:** Linked to existing ticket [{label}]({turn.linked_issue_url}).'
    if turn.kind in _STATUS_LINES:
        return _STATUS_LINES[turn.kind]
    return f'**Outcome:** {turn.kind}.'


def _issue_label_from_url(url: str) -> str | None:
    """``https://github.com/org/repo/issues/77`` -> ``#77``."""
    if not url:
        return None
    tail = url.rstrip('/').rsplit('/', 1)[-1]
    return f'#{tail}' if tail.isdigit() else None


def _build_summary_text(turn: AgentTurn, state: HelpdeskState | None) -> str:
    """Compose a multi-line Markdown recap of the agent's current state.

    Stands on its own after a reload — does not depend on the live
    ``AgentTurnBadge`` chrome. For non-terminal turns the recap shows
    activity so far and the live message body (question / solution /
    draft summary) so the row is useful while the journey is in flight.
    """
    heading = _KIND_HEADINGS.get(turn.kind, 'Helpdesk session')
    lines: list[str] = [f'### {heading}']

    question = (state.get('original_question') if state else None) or ''
    if question:
        trimmed = question.strip().split('\n', 1)[0]
        if len(trimmed) > 200:
            trimmed = trimmed[:197].rstrip() + '…'
        lines.append(f'**Issue:** {trimmed}')

    impact = ((state or {}).get('facts') or {}).get('impact') if state else None
    if impact:
        lines.append(f'**Impact:** {impact}')

    activity = _summarize_activity(state)
    if activity:
        lines.append('**Agent activity:**\n' + '\n'.join(f'- {item}' for item in activity))

    lines.append(_summarize_outcome(turn, state))

    # For non-terminal turns the agent's live message (question text,
    # proposed solution, draft summary) is the most useful piece of
    # content for the reader. Quote it so the body reads naturally.
    if turn.kind not in TERMINAL_KINDS and turn.message:
        snippet = turn.message.strip()
        if snippet:
            lines.append(snippet)

    return '\n\n'.join(lines)


def _trim_trace(turn: AgentTurn) -> list[dict[str, Any]] | None:
    """Return a JSON-safe copy of the agent's last ~20 trace steps."""
    if not turn.debug_trace:
        return None
    trimmed = list(turn.debug_trace)[-20:]
    return [
        {
            'step': step.step,
            'action': step.action,
            'outcome': step.outcome,
            'message': step.message,
        }
        for step in trimmed
    ]


def upsert_agent_summary(
    db: Session,
    *,
    chat_session_id: int,
    user_id: int,
    turn: AgentTurn,
    state: HelpdeskState | None = None,
    agent_run_id: str | None = None,
) -> ChatMessage | None:
    """Upsert the ``chat_messages`` row representing one agent journey.

    The first call for a given ``agent_session_id`` inserts a new row;
    subsequent calls update the same row's content + metadata so the
    chat history always reflects the agent's latest state. The caller
    is expected to propagate the returned ``row.id`` onto
    ``AgentTurn.chat_message_id`` so the frontend can reconcile its
    optimistic in-memory bubble with the persisted record.
    """
    session: ChatSession | None = db.execute(
        select(ChatSession).where(ChatSession.id == chat_session_id, ChatSession.user_id == user_id)
    ).scalar_one_or_none()
    if session is None:
        logger.warning(
            'upsert_agent_summary: chat_session_id=%s not found for user_id=%s; skipping',
            chat_session_id,
            user_id,
        )
        return None

    summary_text = _build_summary_text(turn, state)
    meta: dict[str, Any] = {
        'agent_summary': {
            'kind': turn.kind,
            'agent_session_id': turn.session_id,
            'agent_run_id': agent_run_id,
            'linked_issue_url': turn.linked_issue_url,
            'impact': ((state or {}).get('facts') or {}).get('impact') if state else None,
            'trace': _trim_trace(turn),
        },
    }

    # Look up an existing row for this agent_session_id. Scanning the
    # session's assistant rows in Python keeps the query dialect-agnostic
    # (SQLite in tests, Postgres in prod) — agent journeys produce at most
    # one row per session, so the scan is bounded and cheap.
    existing_rows = (
        db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.session_id == chat_session_id,
                ChatMessage.role == 'assistant',
            )
            .order_by(ChatMessage.id.desc())
        )
        .scalars()
        .all()
    )
    target: ChatMessage | None = None
    for row in existing_rows:
        existing_meta = row.message_meta or {}
        summary_existing = existing_meta.get('agent_summary') if isinstance(existing_meta, dict) else None
        if isinstance(summary_existing, dict) and summary_existing.get('agent_session_id') == turn.session_id:
            target = row
            break

    try:
        if target is None:
            target = ChatMessage(
                session_id=chat_session_id,
                role='assistant',
                content=summary_text,
                message_meta=meta,
            )
            db.add(target)
        else:
            target.content = summary_text
            target.message_meta = meta
            # JSON-typed columns aren't auto-tracked for mutations in
            # every SQLAlchemy dialect; flag explicitly so the UPDATE
            # actually fires.
            flag_modified(target, 'message_meta')
        db.commit()
    except Exception:  # persistence must never break agent UX
        logger.exception('upsert_agent_summary: commit failed; rolling back')
        db.rollback()
        return None
    db.refresh(target)
    return target


# Back-compat alias for callers that still import the old name. Behaviour
# is identical to ``upsert_agent_summary`` — the upsert subsumes the
# original "append-on-terminal" semantics.
persist_agent_summary = upsert_agent_summary
