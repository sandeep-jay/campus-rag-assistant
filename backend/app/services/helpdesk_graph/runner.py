"""Runner for the helpdesk agent."""

from __future__ import annotations

import logging
import re
import uuid
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status

from backend.app.core.config_manager import settings
from backend.app.core.metrics import (
    HELPDESK_AGENT_ERROR_TOTAL,
    HELPDESK_AGENT_FUNNEL_TOTAL,
    HELPDESK_AGENT_OUTCOME_TOTAL,
    HELPDESK_AGENT_STARTED_TOTAL,
    HELPDESK_AGENT_TOOL_TOTAL,
)
from backend.app.schemas.helpdesk import AgentStep, AgentTurn, Category, ConversationTurn, Impact, Severity, TicketDraft
from backend.app.services.helpdesk.agent import draft_ticket
from backend.app.services.helpdesk.github import create_github_issue
from backend.app.services.helpdesk.persist import TERMINAL_KINDS, upsert_agent_summary
from backend.app.services.helpdesk_graph import tools
from backend.app.services.helpdesk_graph.checkpoint import load_checkpoint, save_checkpoint
from backend.app.services.helpdesk_graph.nodes import classify_ticket_facts, supervisor_next_action
from backend.app.services.helpdesk_graph.prompts import SOLUTION_PROMPT
from backend.app.services.helpdesk_graph.state import AwaitingUserPayload, GitHubIssue, HelpdeskState, ProposedSolution
from backend.app.services.helpdesk_graph.tracing import trace_agent_run, trace_agent_tool
from backend.app.services.providers import get_llm_provider

if TYPE_CHECKING:
    from langchain.schema import Document
    from sqlalchemy.orm import Session

STATE_VERSION = 1
IMPACT_QUESTION = 'Is this affecting only you, your team, or the whole campus?'
IMPACT_CHOICES = ['Only me', 'My team', 'Campus-wide', 'Not sure']
SOLUTION_CHOICES = ['Yes, that solved it', "No, doesn't apply", "Tried it, didn't work"]

logger = logging.getLogger(__name__)


_PREAMBLE_LINE_RE = re.compile(
    r'^\s*(title|url|category|short description|source|full text)\s*:\s*',
    re.IGNORECASE,
)


def _strip_ingestion_preamble(text: str) -> str:
    """Drop the KB ingestion preamble from chunk text.

    The KB pipeline prepends ``Title: ... URL: ... Category: ... Full Text:``
    to each chunk. The user-facing answer should read like prose, not a
    metadata dump, so we strip those labels before handing text to the LLM
    or to the fallback path.
    """
    if not text:
        return ''
    lower = text.lower()
    idx = lower.find('full text:')
    if idx >= 0:
        return text[idx + len('full text:') :].strip()
    cleaned: list[str] = []
    for line in text.splitlines():
        if _PREAMBLE_LINE_RE.match(line):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned).strip() or text.strip()


def _doc_text_block(doc: Document, *, max_chars: int = 1500) -> str:
    body = _strip_ingestion_preamble(doc.page_content or '')[:max_chars]
    return body.strip()


def _flatten_content_blocks(blocks: list[Any]) -> str:
    parts: list[str] = []
    for item in blocks:
        if isinstance(item, dict) and isinstance(item.get('text'), str):
            parts.append(item['text'])
        elif isinstance(item, str):
            parts.append(item)
    return '\n'.join(parts)


def _extract_response_text(response: Any) -> str:
    if response is None:
        return ''
    if isinstance(response, str):
        return response
    content = getattr(response, 'content', None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        flattened = _flatten_content_blocks(content)
        if flattened:
            return flattened
    if isinstance(response, dict):
        text = response.get('content') or response.get('text')
        if isinstance(text, str):
            return text
    return str(response)


async def _ainvoke_llm(llm: Any, prompt: list[dict[str, str]]) -> Any:
    if hasattr(llm, 'ainvoke'):
        return await llm.ainvoke(prompt)
    return llm.invoke(prompt)


@trace_agent_tool('helpdesk_agent.generate_solution_summary', run_type='llm')
async def _generate_solution_summary(
    question: str,
    documents: list[Document],
) -> str:
    """Produce a clean, user-readable answer from retrieved docs.

    Real provider: call the configured LLM with ``SOLUTION_PROMPT`` so the
    helpdesk "Get help" reply reads the same shape as a normal RAG answer
    (markdown, numbered steps, no metadata preamble).

    Mock provider or any failure: fall back to the cleaned chunk body so the
    UI still renders a sensible suggestion instead of a raw dump.
    """
    if not documents:
        return ''
    fallback = _doc_text_block(documents[0], max_chars=600)

    provider = get_llm_provider()
    if provider.is_mock:
        return fallback

    context_parts = [_doc_text_block(doc) for doc in documents[:3] if doc]
    context = '\n\n---\n\n'.join(part for part in context_parts if part)
    if not context:
        return fallback

    prompt = [
        {'role': 'system', 'content': SOLUTION_PROMPT},
        {
            'role': 'user',
            'content': f'Question:\n{question}\n\nKnowledge base context:\n{context}',
        },
    ]
    try:
        llm = provider.get_llm()
        response = await _ainvoke_llm(llm, prompt)
    except Exception as exc:  # - solution generation is best-effort
        logger.warning('Helpdesk solution generation failed: %s', exc)
        return fallback

    text = _extract_response_text(response).strip()
    return text or fallback


def _record_funnel(stage: str, outcome: str = 'success') -> None:
    HELPDESK_AGENT_FUNNEL_TOTAL.labels(stage=stage, outcome=outcome).inc()


def _record_agent_error(operation: str, exc: Exception) -> None:
    reason = exc.__class__.__name__
    if isinstance(exc, HTTPException):
        reason = f'http_{exc.status_code}'
    HELPDESK_AGENT_ERROR_TOTAL.labels(operation=operation, reason=reason).inc()


def _last_user_text(conversation: list[ConversationTurn]) -> str:
    for turn in reversed(conversation):
        if turn.role.lower() == 'user':
            return turn.content.strip()
    return ''


def _mock_duplicate_candidates(question: str) -> list[GitHubIssue]:
    text = question.lower()
    if not any(marker in text for marker in ('duplicate', 'existing ticket', 'known issue', '#42')):
        return []
    return [
        GitHubIssue(
            number=42,
            title='Known duplicate helpdesk issue',
            state='open',
            url='https://github.com/demo-org/demo-repo/issues/42',
            body='Mock duplicate returned by the Phase-A helpdesk agent.',
        )
    ]


def _trace(step: str, action: str, outcome: str, message: str | None = None) -> AgentStep:
    return AgentStep(step=step, action=action, outcome=outcome, message=message)


def _require_agent_enabled() -> None:
    if not settings.HELPDESK_AGENT_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Helpdesk agent is not enabled.')
    if settings.HELPDESK_AGENT_KILL_SWITCH:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Helpdesk agent is temporarily disabled.')


def _new_state(session_id: str, user_id: int | str, question: str, conversation: list[ConversationTurn]) -> HelpdeskState:
    return {
        'state_version': STATE_VERSION,
        'session_id': session_id,
        'user_id': user_id,
        'original_question': question,
        'conversation': conversation,
        'turns_taken': 0,
        'questions_asked': [],
        'user_replies': [],
        'kb_retry_results': [],
        'web_search_results': [],
        'tool_cache': {},
        'proposed_solutions': [],
        'rejected_solutions': [],
        'facts': {},
    }


def _pause_for_impact(state: HelpdeskState) -> AgentTurn:
    question_id = f"impact-{state['session_id']}"
    awaiting = AwaitingUserPayload(question_id=question_id, question=IMPACT_QUESTION, choices=IMPACT_CHOICES)
    state['awaiting_user'] = awaiting
    state['next_action'] = 'ask_user'
    state['questions_asked'] = [*state.get('questions_asked', []), IMPACT_QUESTION]
    state['turns_taken'] = int(state.get('turns_taken', 0)) + 1
    save_checkpoint(state)
    HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='question').inc()
    _record_funnel('clarification_requested')
    return AgentTurn(
        session_id=state['session_id'],
        kind='question',
        message=IMPACT_QUESTION,
        choices=IMPACT_CHOICES,
        input='radio',
        debug_trace=[_trace('clarifier', 'ask_user', 'waiting', question_id)],
    )


def _source_url(doc: Document) -> str | None:
    meta = doc.metadata or {}
    nested = meta.get('source_metadata') if isinstance(meta.get('source_metadata'), dict) else {}
    url = nested.get('kb_url') or meta.get('source') or nested.get('source')
    return str(url) if url else None


async def _solution_from_documents(
    documents: list[Document],
    *,
    source: str,
    question: str,
) -> ProposedSolution | None:
    """Build a ProposedSolution from retrieved docs.

    The body is generated by ``_generate_solution_summary`` (LLM in real
    mode, cleaned-chunk fallback in mock / on error). The title and source
    URL still come from the top hit's metadata so the user sees a stable
    reference back to the underlying KB article.
    """
    if not documents:
        return None
    doc = documents[0]
    meta = doc.metadata or {}
    nested = meta.get('source_metadata') if isinstance(meta.get('source_metadata'), dict) else {}
    title = nested.get('short_description') or meta.get('title') or f'{source.upper()} suggested fix'

    summary = (await _generate_solution_summary(question, documents)).strip()
    if not summary:
        return None
    return ProposedSolution(title=str(title)[:120], summary=summary, source_url=_source_url(doc))


def _solution_message(solution: ProposedSolution) -> str:
    if solution.source_url:
        match = re.search(r'KB\d+', solution.source_url)
        label = match.group(0) if match else 'View source'
        source = f'\n\n— [{label}]({solution.source_url})'
    else:
        source = ''
    return f'### {solution.title}\n\n{solution.summary}{source}'


def _is_solution_acceptance(answer: str) -> bool:
    normalized = answer.strip().lower()
    return normalized.startswith('yes') or 'solved' in normalized or 'fixed' in normalized


def _is_solution_rejection(answer: str) -> bool:
    normalized = answer.strip().lower()
    return any(token in normalized for token in ("doesn't", 'does not', 'tried', "didn't", 'did not', 'no'))


def _append_user_reply(state: HelpdeskState, answer: str, *, label: str) -> list[ConversationTurn]:
    conversation = [*state.get('conversation', []), ConversationTurn(role='user', content=f'{label}: {answer}')]
    state['conversation'] = conversation
    state['user_replies'] = [*state.get('user_replies', []), answer]
    return conversation


async def _draft_from_state(state: HelpdeskState, *, message: str, trace: list[AgentStep]) -> AgentTurn:
    conversation = state.get('conversation', [])
    classification = classify_ticket_facts(state)
    state['facts'] = {**state.get('facts', {}), **classification}
    draft = await draft_ticket(conversation)
    draft = draft.model_copy(
        update={
            'severity': Severity(classification['severity']),
            'category': Category(classification['category']),
            'impact': Impact(classification['impact']),
        }
    )
    state['draft'] = draft
    state['awaiting_user'] = None
    state['next_action'] = 'await_user_confirm'
    save_checkpoint(state)
    HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='draft_ready').inc()
    _record_funnel('draft_ready')
    classification_summary = '/'.join((classification['severity'], classification['category'], classification['impact']))
    return AgentTurn(
        session_id=state['session_id'],
        kind='draft_ready',
        message=message,
        draft=draft,
        debug_trace=[
            *trace,
            _trace('classifier', 'classify_ticket', 'success', classification_summary),
            _trace('writer', 'write_draft', 'success', draft.title),
        ],
    )


async def _propose_solution_or_draft(state: HelpdeskState, trace: list[AgentStep]) -> AgentTurn:
    from backend.app.services.rag import RAGService

    query = state.get('original_question', '')
    rag_service = RAGService()
    kb_docs = await tools.retry_kb(query, rag_service=rag_service, state=state)
    state['kb_retry_results'] = kb_docs
    trace.append(_trace('tool', 'retry_kb', 'success', f'{len(kb_docs)} document(s)'))

    solution = await _solution_from_documents(kb_docs, source='kb', question=query)
    if solution is None:
        web_docs = await tools.web_search(query, state=state)
        state['web_search_results'] = web_docs
        trace.append(_trace('tool', 'web_search', 'success', f'{len(web_docs)} document(s)'))
        solution = await _solution_from_documents(web_docs, source='web', question=query)

    if solution is None:
        return await _draft_from_state(
            state,
            message='I could not find a likely fix, so I prepared a ticket draft. Review it before filing.',
            trace=trace,
        )

    question_id = f"solution-{state['session_id']}"
    state['proposed_solutions'] = [*state.get('proposed_solutions', []), solution]
    state['awaiting_user'] = AwaitingUserPayload(question_id=question_id, question='Did this solve the issue?', choices=SOLUTION_CHOICES)
    state['next_action'] = 'propose_solution'
    state['turns_taken'] = int(state.get('turns_taken', 0)) + 1
    save_checkpoint(state)
    HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='solution_proposed').inc()
    _record_funnel('solution_proposed')
    return AgentTurn(
        session_id=state['session_id'],
        kind='info',
        message=_solution_message(solution),
        choices=SOLUTION_CHOICES,
        debug_trace=[*trace, _trace('supervisor', 'propose_solution', 'waiting', question_id)],
    )


def _persist_and_stamp(
    turn: AgentTurn,
    *,
    db: Session | None,
    chat_session_id: int | None,
    user_id: int | str,
    state: HelpdeskState | None = None,
) -> AgentTurn:
    """Upsert the agent-journey row in ``chat_messages`` and stamp the turn.

    No-op when ``chat_session_id`` or ``db`` is missing (e.g. direct
    runner calls from tests or scripts). The agent's API layer is the
    primary caller that supplies both.

    Behaviour by turn kind:

    - **Terminal** (``filed``/``linked``/``resolved``/``aborted``) —
      upsert the row and promote its rich Markdown body onto
      ``AgentTurn.message`` so the live in-memory bubble matches the
      persisted row exactly (heading, impact, activity, outcome with
      inline ticket link).
    - **Non-terminal** (``question``/``info``/``draft_ready``) — upsert
      the row so refresh shows the current state, but **leave the live
      ``AgentTurn.message`` untouched**. The frontend renders the
      question prompt / solution body / draft summary directly from
      ``AgentTurn.message`` (radio choices, feedback pills, ticket draft
      preview); rewriting it to the recap heading would break those
      live affordances. The persisted recap text is read-only history.
    """
    if db is None or chat_session_id is None:
        return turn
    try:
        row = upsert_agent_summary(
            db,
            chat_session_id=chat_session_id,
            user_id=int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id,  # type: ignore[arg-type]
            turn=turn,
            state=state,
            agent_run_id=turn.session_id,
        )
    except Exception:  # persistence must never break agent UX
        logger.exception('failed to persist agent summary for kind=%s', turn.kind)
        return turn
    if row is None:
        return turn
    updates: dict[str, Any] = {'chat_message_id': row.id}
    if turn.kind in TERMINAL_KINDS:
        updates['message'] = row.content
    return turn.model_copy(update=updates)


@trace_agent_run('start')
async def start_session(
    conversation: list[ConversationTurn],
    *,
    user_id: int | str,
    trigger: str = 'api',
    chat_session_id: int | None = None,
    db: Session | None = None,
) -> AgentTurn:
    """Start a helpdesk-agent session and pause for clarification when needed."""
    _require_agent_enabled()
    HELPDESK_AGENT_STARTED_TOTAL.labels(trigger=trigger).inc()
    _record_funnel('started', trigger)

    session_id = str(uuid.uuid4())
    question = _last_user_text(conversation)
    state = _new_state(session_id, user_id, question, conversation)
    debug_trace: list[AgentStep] = []

    if not question:
        return _persist_and_stamp(
            _pause_for_impact(state),
            db=db,
            chat_session_id=chat_session_id,
            user_id=user_id,
            state=state,
        )

    action = supervisor_next_action(state)
    debug_trace.append(_trace('supervisor', action, 'selected'))

    provider = get_llm_provider()
    if provider.is_mock:
        duplicate_candidates = _mock_duplicate_candidates(question)
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool='search_existing_issues', outcome='mock', reason='provider_mock').inc()
    else:
        duplicate_candidates = await tools.search_existing_issues(question)
    state['duplicate_candidates'] = duplicate_candidates
    debug_trace.append(_trace('tool', 'search_existing_issues', 'success', f'{len(duplicate_candidates)} candidate(s)'))

    action = supervisor_next_action(state)
    debug_trace.append(_trace('supervisor', action, 'selected'))

    if action == 'link_existing' and duplicate_candidates:
        candidate = duplicate_candidates[0]
        state['outcome'] = 'linked'
        HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='linked').inc()
        _record_funnel('linked')
        turn = AgentTurn(
            session_id=session_id,
            kind='linked',
            message=(
                f'This looks like an existing report ({candidate.title}). '
                'Following the linked issue should get you status updates without filing a duplicate.'
            ),
            linked_issue_url=candidate.url,
            debug_trace=debug_trace,
        )
        return _persist_and_stamp(turn, db=db, chat_session_id=chat_session_id, user_id=user_id, state=state)

    state['facts']['duplicate_search'] = 'no matching issue found'
    return _persist_and_stamp(
        _pause_for_impact(state),
        db=db,
        chat_session_id=chat_session_id,
        user_id=user_id,
        state=state,
    )


@trace_agent_run('resume')
async def resume_session(
    session_id: str,
    *,
    user_id: int | str,
    reply: str | None = None,
    choice: str | None = None,
    pending_question_id: str | None = None,
    chat_session_id: int | None = None,
    db: Session | None = None,
) -> AgentTurn:
    """Resume a paused helpdesk-agent session after a clarifying answer."""
    _require_agent_enabled()
    state = load_checkpoint(session_id, user_id=user_id)
    if state is None:
        exc = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Helpdesk agent session was not found.')
        _record_agent_error('resume', exc)
        raise exc

    awaiting = state.get('awaiting_user')
    if awaiting is None:
        exc = HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Helpdesk agent is not waiting for user input.')
        _record_agent_error('resume', exc)
        raise exc
    if pending_question_id and pending_question_id != awaiting.question_id:
        exc = HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Helpdesk agent question is stale.')
        _record_agent_error('resume', exc)
        raise exc

    answer = (choice or reply or '').strip()
    if not answer:
        exc = HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='A reply or choice is required.')
        _record_agent_error('resume', exc)
        raise exc

    state['turns_taken'] = int(state.get('turns_taken', 0)) + 1

    if awaiting.question_id.startswith('solution-'):
        _append_user_reply(state, answer, label='Solution feedback')
        if _is_solution_acceptance(answer):
            state['awaiting_user'] = None
            state['outcome'] = 'resolved_by_agent'
            state['next_action'] = 'resolved_by_agent'
            save_checkpoint(state)
            HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='resolved_by_agent').inc()
            _record_funnel('resolved_by_agent')
            turn = AgentTurn(
                session_id=session_id,
                kind='resolved',
                message='Glad that worked. No ticket needed — reach out again any time if something else comes up.',
                debug_trace=[_trace('resume', 'solution_feedback', 'accepted', awaiting.question_id)],
            )
            return _persist_and_stamp(turn, db=db, chat_session_id=chat_session_id, user_id=user_id, state=state)

        if _is_solution_rejection(answer):
            state['rejected_solutions'] = [*state.get('rejected_solutions', []), answer]
        draft_turn = await _draft_from_state(
            state,
            message='Thanks — I prepared a ticket draft instead. Review it before filing.',
            trace=[_trace('resume', 'solution_feedback', 'rejected', awaiting.question_id)],
        )
        return _persist_and_stamp(
            draft_turn,
            db=db,
            chat_session_id=chat_session_id,
            user_id=user_id,
            state=state,
        )

    _append_user_reply(state, answer, label='Impact clarification')
    state['facts'] = {**state.get('facts', {}), 'impact': answer}
    state['awaiting_user'] = None

    next_turn = await _propose_solution_or_draft(
        state,
        [_trace('resume', 'append_user_reply', 'success', awaiting.question_id)],
    )
    return _persist_and_stamp(
        next_turn,
        db=db,
        chat_session_id=chat_session_id,
        user_id=user_id,
        state=state,
    )


@trace_agent_run('confirm')
async def confirm_session(
    session_id: str,
    *,
    user_id: int | str,
    draft: TicketDraft,
    chat_session_id: int | None = None,
    db: Session | None = None,
) -> AgentTurn:
    """File a reviewed agent ticket draft after explicit user confirmation."""
    _require_agent_enabled()
    state = load_checkpoint(session_id, user_id=user_id)
    if state is None:
        exc = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Helpdesk agent session was not found.')
        _record_agent_error('confirm', exc)
        raise exc
    if state.get('next_action') != 'await_user_confirm' or state.get('draft') is None:
        exc = HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Helpdesk agent is not waiting for ticket confirmation.')
        _record_agent_error('confirm', exc)
        raise exc

    issue = await create_github_issue(draft, user_id=user_id)
    state['draft'] = draft
    state['awaiting_user'] = None
    state['outcome'] = 'filed'
    state['next_action'] = 'file_new'
    save_checkpoint(state)
    HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='filed').inc()
    _record_funnel('filed', 'deduplicated' if issue.deduplicated else 'created')

    if issue.deduplicated:
        body = f'A matching ticket was already filed earlier and reused. You can follow #{issue.issue_number} for updates.'
    else:
        body = f'I filed your ticket as #{issue.issue_number}. The helpdesk team will follow up there; you can track progress via the link above.'
    turn = AgentTurn(
        session_id=session_id,
        kind='filed',
        message=body,
        linked_issue_url=issue.issue_url,
        debug_trace=[_trace('tool', 'file_ticket', 'deduplicated' if issue.deduplicated else 'success', str(issue.issue_number))],
    )
    return _persist_and_stamp(turn, db=db, chat_session_id=chat_session_id, user_id=user_id, state=state)


@trace_agent_run('abort')
async def abort_session(
    session_id: str,
    *,
    user_id: int | str,
    chat_session_id: int | None = None,
    db: Session | None = None,
) -> AgentTurn:
    """Abort a helpdesk-agent session without filing a ticket."""
    _require_agent_enabled()
    state = load_checkpoint(session_id, user_id=user_id)
    if state is None:
        exc = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Helpdesk agent session was not found.')
        _record_agent_error('abort', exc)
        raise exc

    state['awaiting_user'] = None
    state['outcome'] = 'aborted'
    state['next_action'] = 'abort'
    save_checkpoint(state)
    HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='aborted').inc()
    _record_funnel('aborted')
    turn = AgentTurn(
        session_id=session_id,
        kind='aborted',
        message='No problem — I closed this helpdesk session without filing. You can ask again any time.',
        debug_trace=[_trace('supervisor', 'abort', 'success')],
    )
    return _persist_and_stamp(turn, db=db, chat_session_id=chat_session_id, user_id=user_id, state=state)
