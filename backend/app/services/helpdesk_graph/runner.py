"""Runner for the helpdesk agent."""

from __future__ import annotations

import logging
import re
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status
from langgraph.types import Command

from backend.app.core.config_manager import settings
from backend.app.core.metrics import (
    HELPDESK_AGENT_ERROR_TOTAL,
    HELPDESK_AGENT_FUNNEL_TOTAL,
    HELPDESK_AGENT_OUTCOME_TOTAL,
    HELPDESK_AGENT_STARTED_TOTAL,
    HELPDESK_AGENT_TOKENS_TOTAL,
    HELPDESK_AGENT_TOOL_TOTAL,
    HELPDESK_AGENT_TURNS_TAKEN,
)
from backend.app.schemas.helpdesk import (
    AgentDocContent,
    AgentSource,
    AgentStep,
    AgentTurn,
    Category,
    ConversationTurn,
    Impact,
    Severity,
    TicketDraft,
)
from backend.app.services.helpdesk.agent import draft_ticket
from backend.app.services.helpdesk.github import create_github_issue
from backend.app.services.helpdesk.persist import TERMINAL_KINDS, upsert_agent_summary
from backend.app.services.helpdesk_graph import tools
from backend.app.services.helpdesk_graph.checkpoint import (
    load_checkpoint,
    maybe_gc_langgraph_checkpoints,
    save_checkpoint,
    use_langgraph_checkpoint,
)
from backend.app.services.helpdesk_graph.graph import (
    HELPDESK_GRAPH,
    helpdesk_graph_for_request,
)
from backend.app.services.helpdesk_graph.nodes import _should_clarify_classification
from backend.app.services.helpdesk_graph.prompts import SOLUTION_PROMPT
from backend.app.services.helpdesk_graph.state import (
    AwaitingUserPayload,
    GitHubIssue,
    HelpdeskState,
    ProposedSolution,
)
from backend.app.services.helpdesk_graph.tracing import (
    trace_agent_run,
    trace_agent_tool,
)
from backend.app.services.providers import get_llm_provider

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from langchain.schema import Document
    from langchain_core.runnables import RunnableConfig
    from langgraph.graph.state import CompiledStateGraph
    from sqlalchemy.orm import Session

STATE_VERSION = 1
IMPACT_QUESTION = 'Is this affecting only you, your team, or the whole campus?'
IMPACT_CHOICES = ['Only me', 'My team', 'Campus-wide', 'Not sure']
SOLUTION_CHOICES = ['Yes, that solved it', "No, doesn't apply", "Tried it, didn't work"]
WEB_CONSENT_QUESTION = 'The knowledge base did not have a likely fix. ' 'Search the public web for troubleshooting ideas?'
WEB_CONSENT_CHOICES = ['Search the web', 'Skip and draft a ticket']
WEB_SEARCH_DISCLAIMER = 'This answer used public web search results. ' 'Verify information against official institutional sources.'

logger = logging.getLogger(__name__)


@dataclass
class _IdempotencyEntry:
    turn: AgentTurn
    expires_at: float


class _ConfirmIdempotencyCache:
    def __init__(self) -> None:
        self._store: dict[str, _IdempotencyEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> AgentTurn | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.time():
                self._store.pop(key, None)
                return None
            return entry.turn

    def put(self, key: str, turn: AgentTurn) -> None:
        expires_at = time.time() + max(0, int(settings.HELPDESK_DEDUP_WINDOW_SECONDS))
        with self._lock:
            self._store[key] = _IdempotencyEntry(turn=turn, expires_at=expires_at)
            now = time.time()
            stale = [cache_key for cache_key, entry in self._store.items() if entry.expires_at < now]
            for cache_key in stale:
                self._store.pop(cache_key, None)


_confirm_idempotency_cache = _ConfirmIdempotencyCache()


def _confirm_idempotency_key(user_id: int | str, idempotency_key: str | None) -> str | None:
    key = (idempotency_key or '').strip()
    if not key:
        return None
    return f'{user_id}:{key}'


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


def _record_turn_metrics(turn: AgentTurn, state: HelpdeskState | None) -> None:
    if state is None:
        return
    HELPDESK_AGENT_TOKENS_TOTAL.labels(node='turn').inc(_token_estimate(state))
    HELPDESK_AGENT_TURNS_TAKEN.labels(outcome=turn.kind).observe(float(state.get('turns_taken', 0) or 0))


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Helpdesk agent is not enabled.',
        )
    if settings.HELPDESK_AGENT_KILL_SWITCH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Helpdesk agent is temporarily disabled.',
        )


def _positive_int_setting(name: str, default: int) -> int:
    value = int(getattr(settings, name, default) or default)
    return max(1, value)


def _token_estimate(state: HelpdeskState) -> int:
    """Cheap deterministic guardrail; exact provider token counts arrive in Phase 3."""
    text_parts = [state.get('original_question', '')]
    text_parts.extend(turn.content for turn in state.get('conversation', []))
    text_parts.extend(state.get('user_replies', []))
    text_parts.extend(solution.summary for solution in state.get('proposed_solutions', []))
    draft = state.get('draft')
    if draft is not None:
        text_parts.extend([draft.title, draft.description, draft.steps_to_reproduce or ''])
    return sum(max(1, len(part) // 4) for part in text_parts if part)


def _budget_exhausted(state: HelpdeskState) -> bool:
    max_turns = _positive_int_setting('HELPDESK_AGENT_MAX_TURNS', 8)
    max_questions = _positive_int_setting('HELPDESK_AGENT_MAX_QUESTIONS', 2)
    max_tokens = _positive_int_setting('HELPDESK_AGENT_MAX_TOKENS_PER_SESSION', 20000)
    deadline_at = float(state.get('deadline_at') or 0)
    return (
        int(state.get('turns_taken', 0)) > max_turns
        or len(state.get('questions_asked', [])) > max_questions
        or _token_estimate(state) > max_tokens
        or (deadline_at > 0 and time.time() >= deadline_at)
    )


def _tool_budget_exhausted(state: HelpdeskState) -> bool:
    max_tool_retries = _positive_int_setting('HELPDESK_AGENT_MAX_TOOL_RETRIES', 2)
    return int(state.get('tool_attempts', 0)) >= max_tool_retries


async def _budget_exhausted_turn(state: HelpdeskState, trace: list[AgentStep] | None = None) -> AgentTurn:
    return await _draft_from_state(
        state,
        message='I reached the helpdesk agent safety budget, so I prepared a ticket draft for your review.',
        trace=[*(trace or []), _trace('budget', 'budget_exhausted', 'forced_draft')],
    )


def _new_state(
    session_id: str,
    user_id: int | str,
    question: str,
    conversation: list[ConversationTurn],
) -> HelpdeskState:
    now = time.time()
    deadline_seconds = max(0.1, float(getattr(settings, 'HELPDESK_AGENT_DEADLINE_SECONDS', 60.0) or 60.0))
    return {
        'state_version': STATE_VERSION,
        'session_id': session_id,
        'user_id': user_id,
        'created_at': now,
        'deadline_at': now + deadline_seconds,
        'original_question': question,
        'conversation': conversation,
        'turns_taken': 0,
        'questions_asked': [],
        'user_replies': [],
        'tool_attempts': 0,
        'kb_retry_results': [],
        'web_search_results': [],
        'web_search_consent': None,
        'solution_source_kind': None,
        'tool_cache': {},
        'proposed_solutions': [],
        'rejected_solutions': [],
        'facts': {},
    }


async def _pause_for_impact(state: HelpdeskState) -> AgentTurn:
    from backend.app.services.helpdesk_graph.llm import clarify

    awaiting = await clarify(state)
    question_id = awaiting.question_id
    state['awaiting_user'] = awaiting
    state['next_action'] = 'ask_user'
    state['questions_asked'] = [*state.get('questions_asked', []), awaiting.question]
    state['turns_taken'] = int(state.get('turns_taken', 0)) + 1
    if _budget_exhausted(state):
        return await _budget_exhausted_turn(state, [_trace('clarifier', 'ask_user', 'blocked', question_id)])
    save_checkpoint(state)
    HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='question').inc()
    _record_funnel('clarification_requested')
    return AgentTurn(
        session_id=state['session_id'],
        kind='question',
        message=awaiting.question,
        choices=awaiting.choices,
        input='radio',
        debug_trace=[_trace('clarifier', 'ask_user', 'waiting', question_id)],
    )


def _source_url(doc: Document) -> str | None:
    meta = doc.metadata or {}
    nested = meta.get('source_metadata') if isinstance(meta.get('source_metadata'), dict) else {}
    url = nested.get('kb_url') or meta.get('source') or nested.get('source')
    return str(url) if url else None


def _requires_live_web_consent() -> bool:
    """True when web search would call a live provider (Tavily) off-campus."""
    if not settings.HELPDESK_AGENT_TOOL_WEB_SEARCH:
        return False
    provider = (getattr(settings, 'WEB_SEARCH_PROVIDER', None) or 'mock').strip().lower()
    if provider != 'tavily':
        return False
    api_key = getattr(settings, 'TAVILY_API_KEY', None)
    if api_key is None:
        return False
    secret = api_key.get_secret_value() if hasattr(api_key, 'get_secret_value') else str(api_key)
    return bool(secret.strip())


def _is_web_consent_acceptance(answer: str) -> bool:
    normalized = answer.strip().lower()
    return normalized.startswith('search the web')


def _is_web_consent_denial(answer: str) -> bool:
    normalized = answer.strip().lower()
    return 'skip' in normalized or 'draft' in normalized


def _kb_confidence_floor() -> float:
    raw = getattr(settings, 'HELPDESK_AGENT_KB_CONFIDENCE_FLOOR', 0.55)
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 0.4


def _evidence_top_n() -> int:
    raw = getattr(settings, 'HELPDESK_AGENT_EVIDENCE_TOP_N', 3)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 3
    return max(1, value)


def _top_kb_score(documents: list[Document]) -> float | None:
    """Return the highest similarity score across retrieved KB documents.

    Bedrock and Azure providers stash ``score`` on Document metadata. Mock /
    test providers may omit it, in which case we return ``None`` and the
    caller treats the retrieval as "score unknown" (which we accept rather
    than penalising mock-mode tests).
    """
    best: float | None = None
    for doc in documents:
        meta = doc.metadata or {}
        raw = meta.get('score')
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if best is None or value > best:
            best = value
    return best


def _kb_solution_has_confidence(documents: list[Document]) -> bool:
    """Return True when the KB retry's top hit clears the confidence floor.

    No-score retrievals (mock providers, tests) are treated as confident so
    deterministic mock flows keep their current behavior.
    """
    if not documents:
        return False
    top = _top_kb_score(documents)
    if top is None:
        return True
    return top >= _kb_confidence_floor()


def _format_agent_evidence(
    documents: list[Document],
) -> tuple[list[AgentSource], list[AgentDocContent]]:
    """Map retrieved LangChain docs to the chat-compatible sources shape.

    The agent retries the KB with a wider ``numberOfResults`` than the chat
    pipeline; surfacing all of them clutters the bubble. We keep only the
    top ``HELPDESK_AGENT_EVIDENCE_TOP_N`` documents (already ranked by the
    retriever).
    """
    top_n = _evidence_top_n()
    trimmed = list(documents)[:top_n]
    metadata_list: list[dict[str, Any]] = []
    document_contents: list[dict[str, Any]] = []
    for doc in trimmed:
        source_meta = doc.metadata.get('source_metadata', {})
        doc_metadata = {
            'source': source_meta.get('source', doc.metadata.get('source', 'unknown')),
            'kb_url': source_meta.get('kb_url', doc.metadata.get('kb_url', '#')),
            'kb_number': source_meta.get('kb_number', doc.metadata.get('kb_number', 'N/A')),
            'kb_category': source_meta.get('kb_category', doc.metadata.get('kb_category', '')),
            'short_description': source_meta.get('short_description', doc.metadata.get('short_description', '')),
            'project': source_meta.get('project', doc.metadata.get('project', '')),
            'ingestion_date': source_meta.get('ingestion_date', doc.metadata.get('ingestion_date', '')),
            'score': doc.metadata.get('score', None),
        }
        metadata_list.append(doc_metadata)
        document_contents.append({'content': doc.page_content, 'metadata': doc_metadata})
    sources = [AgentSource(**item) for item in metadata_list]
    doc_contents = [AgentDocContent(content=item['content'], metadata=AgentSource(**item['metadata'])) for item in document_contents]
    return sources, doc_contents


async def _pause_for_web_consent(state: HelpdeskState, trace: list[AgentStep]) -> AgentTurn:
    question_id = f"web-consent-{state['session_id']}"
    state['awaiting_user'] = AwaitingUserPayload(
        question_id=question_id,
        question=WEB_CONSENT_QUESTION,
        choices=WEB_CONSENT_CHOICES,
    )
    state['web_search_consent'] = 'pending'
    state['next_action'] = 'ask_user'
    state['turns_taken'] = int(state.get('turns_taken', 0)) + 1
    if _budget_exhausted(state):
        return await _budget_exhausted_turn(
            state,
            [*trace, _trace('supervisor', 'web_search_consent', 'blocked', question_id)],
        )
    save_checkpoint(state)
    HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='question').inc()
    _record_funnel('web_search_consent_requested')
    return AgentTurn(
        session_id=state['session_id'],
        kind='question',
        message=WEB_CONSENT_QUESTION,
        choices=WEB_CONSENT_CHOICES,
        input='radio',
        debug_trace=[*trace, _trace('supervisor', 'web_search_consent', 'waiting', question_id)],
    )


def _build_solution_turn(
    state: HelpdeskState,
    solution: ProposedSolution,
    documents: list[Document],
    *,
    source_kind: str,
    trace: list[AgentStep],
) -> AgentTurn:
    sources, document_contents = _format_agent_evidence(documents) if documents else (None, None)
    disclaimer = WEB_SEARCH_DISCLAIMER if source_kind == 'web' else None
    state['solution_source_kind'] = source_kind  # type: ignore[typeddict-item]
    question_id = f"solution-{state['session_id']}"
    state['proposed_solutions'] = [*state.get('proposed_solutions', []), solution]
    state['awaiting_user'] = AwaitingUserPayload(
        question_id=question_id,
        question='Did this solve the issue?',
        choices=SOLUTION_CHOICES,
    )
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
        sources=sources,
        document_contents=document_contents,
        source_kind=source_kind,  # type: ignore[arg-type]
        disclaimer=disclaimer,
        debug_trace=[
            *trace,
            _trace('supervisor', 'propose_solution', 'waiting', question_id),
        ],
    )


async def _propose_solution_after_web_consent(
    state: HelpdeskState,
    trace: list[AgentStep],
) -> AgentTurn | None:
    """Run web search after the user granted live-web consent."""
    query = state.get('original_question', '')
    if _tool_budget_exhausted(state):
        return await _budget_exhausted_turn(state, trace)
    state['tool_attempts'] = int(state.get('tool_attempts', 0)) + 1
    web_docs = await tools.web_search(query, state=state)
    state['web_search_results'] = web_docs
    trace.append(_trace('tool', 'web_search', 'success', f'{len(web_docs)} document(s)'))
    solution = await _solution_from_documents(web_docs, source='web', question=query)
    if solution is None:
        state['_trace_seed'] = trace
        state['_next'] = 'write_draft'
        return None
    if _budget_exhausted(state):
        return await _budget_exhausted_turn(
            state,
            [*trace, _trace('supervisor', 'propose_solution', 'blocked', f"solution-{state['session_id']}")],
        )
    return _build_solution_turn(state, solution, web_docs, source_kind='web', trace=trace)


async def _propose_web_solution_or_draft(
    state: HelpdeskState,
    trace: list[AgentStep],
    *,
    query: str,
) -> AgentTurn | None:
    consent = state.get('web_search_consent')
    if consent == 'denied':
        state['_trace_seed'] = trace
        state['_next'] = 'write_draft'
        return None

    if _requires_live_web_consent() and consent != 'granted':
        return await _pause_for_web_consent(state, trace)

    if _tool_budget_exhausted(state):
        return await _budget_exhausted_turn(state, trace)
    state['tool_attempts'] = int(state.get('tool_attempts', 0)) + 1
    web_docs = await tools.web_search(query, state=state)
    state['web_search_results'] = web_docs
    trace.append(_trace('tool', 'web_search', 'success', f'{len(web_docs)} document(s)'))
    solution = await _solution_from_documents(web_docs, source='web', question=query)

    if solution is None:
        state['_trace_seed'] = trace
        state['_next'] = 'write_draft'
        return None

    if _budget_exhausted(state):
        return await _budget_exhausted_turn(
            state,
            [*trace, _trace('supervisor', 'propose_solution', 'blocked', f"solution-{state['session_id']}")],
        )
    return _build_solution_turn(state, solution, web_docs, source_kind='web', trace=trace)


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
    conversation = [
        *state.get('conversation', []),
        ConversationTurn(role='user', content=f'{label}: {answer}'),
    ]
    state['conversation'] = conversation
    state['user_replies'] = [*state.get('user_replies', []), answer]
    return conversation


async def _classify_state(state: HelpdeskState):
    from backend.app.services.helpdesk_graph.llm import classify

    classification = await classify(state)
    state['facts'] = {
        **state.get('facts', {}),
        'severity': classification.severity,
        'category': classification.category,
        'impact': classification.impact,
    }
    state['classification_confidence'] = classification.confidence
    return classification


async def _draft_from_state(state: HelpdeskState, *, message: str, trace: list[AgentStep]) -> AgentTurn:
    conversation = state.get('conversation', [])
    facts = state.get('facts', {})
    if {'severity', 'category', 'impact'} <= set(facts):
        classification = {
            'severity': facts['severity'],
            'category': facts['category'],
            'impact': facts['impact'],
            'confidence': float(state.get('classification_confidence', 0.0)),
        }
    else:
        classified = await _classify_state(state)
        classification = classified.model_dump()
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
    classification_summary = '/'.join(
        (
            classification['severity'],
            classification['category'],
            classification['impact'],
            f"confidence={classification['confidence']:.2f}",
        )
    )
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


async def _propose_solution_or_draft(state: HelpdeskState, trace: list[AgentStep]) -> AgentTurn | None:
    from backend.app.services.rag import RAGService

    query = state.get('original_question', '')
    rag_service = RAGService()
    if _tool_budget_exhausted(state):
        return await _budget_exhausted_turn(state, trace)
    state['tool_attempts'] = int(state.get('tool_attempts', 0)) + 1
    kb_docs = await tools.retry_kb(query, rag_service=rag_service, state=state)
    state['kb_retry_results'] = kb_docs

    top_score = _top_kb_score(kb_docs)
    floor = _kb_confidence_floor()
    if top_score is None:
        score_note = f'{len(kb_docs)} document(s)'
    else:
        score_note = f'{len(kb_docs)} document(s); top_score={top_score:.2f} (floor={floor:.2f})'
    trace.append(_trace('tool', 'retry_kb', 'success', score_note))
    logger.info(
        'helpdesk_agent.retry_kb session=%s docs=%d top_score=%s floor=%.2f',
        state.get('session_id'),
        len(kb_docs),
        f'{top_score:.3f}' if top_score is not None else 'n/a',
        floor,
    )

    if _kb_solution_has_confidence(kb_docs):
        solution = await _solution_from_documents(kb_docs, source='kb', question=query)
        if solution is not None:
            if _budget_exhausted(state):
                return await _budget_exhausted_turn(
                    state,
                    [*trace, _trace('supervisor', 'propose_solution', 'blocked', f"solution-{state['session_id']}")],
                )
            return _build_solution_turn(state, solution, kb_docs, source_kind='kb', trace=trace)
    elif kb_docs:
        # KB returned hits but none cleared the confidence floor — say so in the
        # trace so the user can see why we're escalating to web/draft instead of
        # quietly dropping the retrieval.
        trace.append(
            _trace(
                'supervisor',
                'kb_low_confidence',
                'skipped',
                f'top_score={top_score:.2f} < floor={floor:.2f}' if top_score is not None else 'score_unavailable',
            )
        )

    return await _propose_web_solution_or_draft(state, trace, query=query)


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
        _record_turn_metrics(turn, state)
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
        _record_turn_metrics(turn, state)
        return turn
    if row is None:
        _record_turn_metrics(turn, state)
        return turn
    updates: dict[str, Any] = {'chat_message_id': row.id}
    if turn.kind in TERMINAL_KINDS:
        updates['message'] = row.content
    stamped = turn.model_copy(update=updates)
    _record_turn_metrics(stamped, state)
    return stamped


async def graph_tool_search_duplicates(state: HelpdeskState) -> list[GitHubIssue]:
    """Run the duplicate-issue tool, picking mock vs. real per provider.

    Called by the compiled graph's ``tools`` node (the spec's
    ``ToolNode`` slot in Phase 2). Mock provider returns a sentinel
    list keyed on the question wording so the demo scenarios stay
    deterministic.
    """
    question = state.get('original_question', '')
    provider = get_llm_provider()
    if provider.is_mock:
        duplicates = _mock_duplicate_candidates(question)
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool='search_existing_issues', outcome='mock', reason='provider_mock').inc()
    else:
        duplicates = await tools.search_existing_issues(question)
    return duplicates


async def graph_clarifier_step(state: HelpdeskState) -> dict[str, Any]:
    """Graph-node wrapper around :func:`_pause_for_impact`.

    Preserves the original ``start_session`` invariant that
    ``facts['duplicate_search']`` is set only when the duplicate search
    actually ran and returned an empty list — the empty-question path
    (no search at all) leaves the fact unset.
    """
    if 'duplicate_candidates' in state and not state['duplicate_candidates']:
        state['facts'] = {
            **state.get('facts', {}),
            'duplicate_search': 'no matching issue found',
        }
    turn = await _pause_for_impact(state)
    state['_graph_turn'] = turn
    return state


async def graph_solution_step(state: HelpdeskState) -> dict[str, Any]:
    """Graph-node wrapper around :func:`_propose_solution_or_draft`.

    Only runs on the resume path where the user just answered the
    impact question or granted live-web search consent. Mirrors the
    legacy ``resume_session`` branch that appended the user reply,
    recorded the impact fact, cleared ``awaiting_user``, then handed
    control to the propose-solution helper with the ``append_user_reply``
    trace seed.
    """
    awaiting = state.get('awaiting_user')
    answer = state.get('resume_answer') or ''
    question_id = awaiting.question_id if awaiting is not None else ''
    trace_seed: list[AgentStep] = []
    if awaiting is not None and awaiting.question_id.startswith('web-consent-'):
        _append_user_reply(state, answer, label='Web search consent')
        state['awaiting_user'] = None
        outcome = 'granted' if _is_web_consent_acceptance(answer) else 'denied'
        trace_seed.append(_trace('resume', 'web_search_consent', outcome, question_id))
        if _is_web_consent_acceptance(answer):
            state['web_search_consent'] = 'granted'
            turn = await _propose_solution_after_web_consent(state, trace_seed)
        else:
            state['web_search_consent'] = 'denied'
            turn = await _draft_from_state(
                state,
                message='Understood — I prepared a ticket draft instead of searching the public web.',
                trace=trace_seed,
            )
        if turn is None:
            state['_graph_turn'] = None
            return state
        state['_graph_turn'] = turn
        return state
    if awaiting is not None:
        _append_user_reply(state, answer, label='Impact clarification')
        state['facts'] = {**state.get('facts', {}), 'impact': answer}
        state['awaiting_user'] = None
        trace_seed.append(_trace('resume', 'append_user_reply', 'success', question_id))
    turn = await _propose_solution_or_draft(state, trace_seed)
    if turn is None:
        state['_graph_turn'] = None
        return state
    state['_graph_turn'] = turn
    return state


async def graph_classifier_step(state: HelpdeskState) -> dict[str, Any]:
    """Run the classifier specialist before ticket writing or clarification."""
    await _classify_state(state)
    if _should_clarify_classification(state):
        state['_next'] = 'ask_user'
    else:
        state['_next'] = 'write_draft'
    return state


async def graph_writer_step(state: HelpdeskState) -> dict[str, Any]:
    """Graph-node wrapper around :func:`_draft_from_state`.

    Currently reachable from the resume path on a rejected solution or
    when the user declines live-web search consent. The trace seed keeps
    the pre-graph byte-shape that existing tests assert.
    """
    awaiting = state.get('awaiting_user')
    answer = state.get('resume_answer') or ''
    question_id = awaiting.question_id if awaiting is not None else ''
    trace_seed = [*state.get('_trace_seed', [])]
    if awaiting is not None and awaiting.question_id.startswith('web-consent-'):
        _append_user_reply(state, answer, label='Web search consent')
        state['web_search_consent'] = 'denied'
        trace_seed.append(_trace('resume', 'web_search_consent', 'denied', question_id))
    elif awaiting is not None and awaiting.question_id.startswith('solution-'):
        _append_user_reply(state, answer, label='Solution feedback')
        if _is_solution_rejection(answer):
            state['rejected_solutions'] = [*state.get('rejected_solutions', []), answer]
        trace_seed.append(_trace('resume', 'solution_feedback', 'rejected', question_id))
    turn = await _draft_from_state(
        state,
        message=(
            'Thanks — I prepared a ticket draft instead. Review it before filing.'
            if awaiting is not None and awaiting.question_id.startswith('solution-')
            else (
                'Understood — I prepared a ticket draft instead of searching the public web.'
                if awaiting is not None and awaiting.question_id.startswith('web-consent-')
                else (
                    'Thanks — I prepared a ticket draft instead. Review it before filing.'
                    if awaiting is not None
                    else 'I could not find a likely fix, so I prepared a ticket draft. Review it before filing.'
                )
            )
        ),
        trace=trace_seed,
    )
    state['_graph_turn'] = turn
    return state


async def graph_resolved_step(state: HelpdeskState) -> dict[str, Any]:
    """Graph-node wrapper for the ``resolved_by_agent`` terminal."""
    awaiting = state.get('awaiting_user')
    answer = state.get('resume_answer') or ''
    question_id = awaiting.question_id if awaiting is not None else ''
    session_id = state['session_id']
    _append_user_reply(state, answer, label='Solution feedback')
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
        debug_trace=[_trace('resume', 'solution_feedback', 'accepted', question_id)],
    )
    state['_graph_turn'] = turn
    return state


async def graph_link_existing_step(state: HelpdeskState) -> dict[str, Any]:
    """Graph-node wrapper for the ``link_existing`` terminal."""
    candidates = state.get('duplicate_candidates') or []
    candidate = candidates[0]
    state['outcome'] = 'linked'
    HELPDESK_AGENT_OUTCOME_TOTAL.labels(outcome='linked').inc()
    _record_funnel('linked')
    turn = AgentTurn(
        session_id=state['session_id'],
        kind='linked',
        message=(
            f'This looks like an existing report ({candidate.title}). '
            'Following the linked issue should get you status updates without filing a duplicate.'
        ),
        linked_issue_url=candidate.url,
        debug_trace=[
            _trace('supervisor', 'search_duplicates', 'selected'),
            _trace(
                'tool',
                'search_existing_issues',
                'success',
                f'{len(candidates)} candidate(s)',
            ),
            _trace('supervisor', 'link_existing', 'selected'),
        ],
    )
    state['_graph_turn'] = turn
    return state


async def graph_file_ticket_step(state: HelpdeskState) -> dict[str, Any]:
    """Graph-node wrapper for the ``file_new`` (HITL-confirmed) terminal."""
    session_id = state['session_id']
    draft = state.get('confirm_draft')
    if draft is None:
        # Defensive fallback; the runner's confirm entry point validates
        # the draft before reaching the graph.
        exc = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Helpdesk agent confirm draft missing.',
        )
        _record_agent_error('confirm', exc)
        raise exc
    user_id = state['user_id']
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
        debug_trace=[
            _trace(
                'tool',
                'file_ticket',
                'deduplicated' if issue.deduplicated else 'success',
                str(issue.issue_number),
            )
        ],
    )
    state['_graph_turn'] = turn
    return state


async def graph_aborted_step(state: HelpdeskState) -> dict[str, Any]:
    """Graph-node wrapper for the ``abort`` terminal."""
    session_id = state['session_id']
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
    state['_graph_turn'] = turn
    return state


def _graph_config(session_id: str) -> RunnableConfig:
    return {'configurable': {'thread_id': session_id}}


def _state_not_found_exc(operation: str) -> HTTPException:
    exc = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='Helpdesk agent session was not found.',
    )
    _record_agent_error(operation, exc)
    return exc


async def _load_langgraph_state(
    graph: CompiledStateGraph,
    session_id: str,
    *,
    user_id: int | str,
    operation: str,
) -> HelpdeskState:
    snapshot = await graph.aget_state(_graph_config(session_id))
    snapshot_values = getattr(snapshot, 'values', None) or {}
    state = dict(snapshot_values)
    if not state or str(state.get('user_id')) != str(user_id):
        raise _state_not_found_exc(operation)
    return state


async def _run_graph(
    state_or_command: HelpdeskState | Command,
    *,
    operation: str,
    graph: CompiledStateGraph | None = None,
    config: RunnableConfig | None = None,
) -> tuple[AgentTurn, HelpdeskState]:
    """Invoke the compiled helpdesk graph and unpack the final turn.

    Returns ``(turn, final_state)`` so the entry point can hand the
    state to ``_persist_and_stamp``. Falls back to a defensive
    budget-exhausted draft if a node forgot to populate
    ``_graph_turn`` — that should never happen in Phase 1a but keeps
    the API contract intact if a future refactor adds a node without
    setting the turn.
    """
    active_graph = graph or HELPDESK_GRAPH
    result = await active_graph.ainvoke(state_or_command, config=config)
    turn = result.get('_graph_turn')
    if turn is None:
        logger.warning('helpdesk graph completed without _graph_turn for operation=%s', operation)
        turn = await _budget_exhausted_turn(dict(result))
    return turn, result


_VISIBLE_CHAIN_NODES = {
    'supervisor',
    'clarifier',
    'classifier',
    'writer',
    'solution',
    'tools',
    'link_existing',
    'file_ticket',
    'resolved',
    'aborted',
}
_VISIBLE_TOOL_NAMES = {
    'retry_kb',
    'web_search',
    'search_existing_issues',
    'file_ticket',
}
_NODE_ACTIONS = {
    'supervisor': 'route',
    'clarifier': 'ask_user',
    'classifier': 'classify_ticket',
    'writer': 'write_draft',
    'solution': 'propose_solution',
    'tools': 'search_existing_issues',
    'link_existing': 'link_existing',
    'file_ticket': 'file_ticket',
    'resolved': 'resolved_by_agent',
    'aborted': 'abort',
}


def _event_output(event: dict[str, Any]) -> Any:
    data = event.get('data')
    if isinstance(data, dict):
        return data.get('output')
    return None


def _turn_from_output(output: Any) -> AgentTurn | None:
    if not isinstance(output, dict):
        return None
    turn = output.get('_graph_turn')
    if isinstance(turn, AgentTurn):
        return turn
    if isinstance(turn, dict):
        return AgentTurn(**turn)
    return None


def _event_step_summary(name: str, output: Any, status_value: str) -> str:
    if status_value == 'running':
        return f'Started {name.replace("_", " ")}'
    if isinstance(output, dict):
        if name == 'supervisor' and output.get('_next'):
            return f"Selected {output['_next']}"
        turn = _turn_from_output(output)
        if turn is not None:
            return f'Produced {turn.kind} turn'
    if isinstance(output, list):
        return f'{len(output)} result(s)'
    return f'Finished {name.replace("_", " ")}'


def _step_event_from_graph_event(
    event: dict[str, Any],
    *,
    started_at: dict[str, float],
) -> dict[str, Any] | None:
    event_kind = str(event.get('event') or '')
    name = str(event.get('name') or '')
    run_id = str(event.get('run_id') or f'{name}:{event_kind}')
    is_tool = event_kind.startswith('on_tool_')
    is_chain = event_kind.startswith('on_chain_')
    if is_tool:
        if name not in _VISIBLE_TOOL_NAMES:
            return None
        node = name
        action = name
    elif is_chain:
        if name not in _VISIBLE_CHAIN_NODES:
            return None
        node = name
        action = _NODE_ACTIONS.get(name, name)
    else:
        return None

    if event_kind.endswith('_start'):
        started_at[run_id] = time.perf_counter()
        status_value = 'running'
        latency_ms = None
        output = None
    elif event_kind.endswith('_end'):
        started = started_at.pop(run_id, None)
        status_value = 'success'
        latency_ms = round((time.perf_counter() - started) * 1000, 2) if started is not None else None
        output = _event_output(event)
    elif event_kind.endswith('_error'):
        started = started_at.pop(run_id, None)
        status_value = 'error'
        latency_ms = round((time.perf_counter() - started) * 1000, 2) if started is not None else None
        output = _event_output(event)
    else:
        return None

    return {
        'type': 'step',
        'node': node,
        'action': action,
        'status': status_value,
        'latency_ms': latency_ms,
        'summary': _event_step_summary(name, output, status_value),
    }


async def _stream_graph(  # noqa: C901 - event parsing keeps stream state in one place
    state_or_command: HelpdeskState | Command,
    *,
    operation: str,
    graph: CompiledStateGraph,
    config: RunnableConfig | None,
) -> AsyncIterator[dict[str, Any]]:
    started_at: dict[str, float] = {}
    final_state: HelpdeskState | None = None
    final_turn: AgentTurn | None = None
    async for event in graph.astream_events(state_or_command, config=config, version='v2'):
        output = _event_output(event)
        if isinstance(output, dict):
            turn = _turn_from_output(output)
            if turn is not None:
                final_turn = turn
                final_state = dict(output)
        step_event = _step_event_from_graph_event(event, started_at=started_at)
        if step_event is not None:
            yield step_event
        if final_turn is not None:
            break

    if final_state is None and config is not None:
        with suppress(Exception):
            snapshot = await graph.aget_state(config)
            values = getattr(snapshot, 'values', None) or {}
            if values:
                final_state = dict(values)
                final_turn = _turn_from_output(final_state)

    if final_state is None or final_turn is None:
        logger.warning(
            'helpdesk graph stream completed without _graph_turn for operation=%s',
            operation,
        )
        state = final_state or {}
        final_turn = await _budget_exhausted_turn(dict(state))
        final_state = dict(state)

    if config is not None:
        producer_node = None
        if final_turn.kind == 'draft_ready':
            producer_node = 'writer'
        elif final_turn.kind == 'question':
            producer_node = 'clarifier'
        elif final_turn.kind == 'info':
            producer_node = 'solution'
        if producer_node is not None:
            with suppress(Exception):
                await graph.aupdate_state(config, final_state, as_node=producer_node)

    yield {'type': '_internal_done', 'turn': final_turn, 'state': final_state}


@trace_agent_run('start')
async def start_session(
    conversation: list[ConversationTurn],
    *,
    user_id: int | str,
    trigger: str = 'api',
    chat_session_id: int | None = None,
    db: Session | None = None,
) -> AgentTurn:
    """Start a helpdesk-agent session and pause for clarification when needed.

    Phase 1a wires this entry point through the compiled LangGraph
    StateGraph in :mod:`backend.app.services.helpdesk_graph.graph`; the
    runner still owns budget guards, metrics counters, and the
    chat-history upsert at the persistence layer, but every routing
    decision now flows through the supervisor → specialist tree.
    """
    _require_agent_enabled()
    await maybe_gc_langgraph_checkpoints()
    HELPDESK_AGENT_STARTED_TOTAL.labels(trigger=trigger).inc()
    _record_funnel('started', trigger)

    session_id = str(uuid.uuid4())
    question = _last_user_text(conversation)
    state = _new_state(session_id, user_id, question, conversation)
    if _budget_exhausted(state):
        return _persist_and_stamp(
            await _budget_exhausted_turn(state),
            db=db,
            chat_session_id=chat_session_id,
            user_id=user_id,
            state=state,
        )

    state['entry'] = 'start'
    if use_langgraph_checkpoint():
        async with helpdesk_graph_for_request() as graph:
            turn, final_state = await _run_graph(
                state,
                operation='start',
                graph=graph,
                config=_graph_config(session_id),
            )
    else:
        turn, final_state = await _run_graph(state, operation='start')
    return _persist_and_stamp(
        turn,
        db=db,
        chat_session_id=chat_session_id,
        user_id=user_id,
        state=final_state,
    )


async def stream_start_session(
    conversation: list[ConversationTurn],
    *,
    user_id: int | str,
    trigger: str = 'stream',
    chat_session_id: int | None = None,
    db: Session | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream graph step events for a new helpdesk-agent session."""
    _require_agent_enabled()
    await maybe_gc_langgraph_checkpoints()
    HELPDESK_AGENT_STARTED_TOTAL.labels(trigger=trigger).inc()
    _record_funnel('started', trigger)

    session_id = str(uuid.uuid4())
    question = _last_user_text(conversation)
    state = _new_state(session_id, user_id, question, conversation)
    if _budget_exhausted(state):
        turn = _persist_and_stamp(
            await _budget_exhausted_turn(state),
            db=db,
            chat_session_id=chat_session_id,
            user_id=user_id,
            state=state,
        )
        yield {'type': 'done', 'turn': turn.model_dump(mode='json')}
        return

    state['entry'] = 'start'
    if use_langgraph_checkpoint():
        async with helpdesk_graph_for_request() as graph:
            async for event in _stream_graph(
                state,
                operation='start',
                graph=graph,
                config=_graph_config(session_id),
            ):
                if event.get('type') != '_internal_done':
                    yield event
                    continue
                turn = _persist_and_stamp(
                    event['turn'],
                    db=db,
                    chat_session_id=chat_session_id,
                    user_id=user_id,
                    state=event['state'],
                )
                yield {'type': 'done', 'turn': turn.model_dump(mode='json')}
    else:
        async for event in _stream_graph(state, operation='start', graph=HELPDESK_GRAPH, config=None):
            if event.get('type') != '_internal_done':
                yield event
                continue
            turn = _persist_and_stamp(
                event['turn'],
                db=db,
                chat_session_id=chat_session_id,
                user_id=user_id,
                state=event['state'],
            )
            yield {'type': 'done', 'turn': turn.model_dump(mode='json')}


@trace_agent_run('resume')
async def resume_session(  # noqa: C901 - mirrors legacy and LangGraph checkpoint resume paths during rollback window
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
    if use_langgraph_checkpoint():
        async with helpdesk_graph_for_request() as graph:
            state = await _load_langgraph_state(graph, session_id, user_id=user_id, operation='resume')
            if _budget_exhausted(state):
                return _persist_and_stamp(
                    await _budget_exhausted_turn(state),
                    db=db,
                    chat_session_id=chat_session_id,
                    user_id=user_id,
                    state=state,
                )

            awaiting = state.get('awaiting_user')
            if awaiting is None:
                exc = HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Helpdesk agent is not waiting for user input.',
                )
                _record_agent_error('resume', exc)
                raise exc
            if pending_question_id and pending_question_id != awaiting.question_id:
                exc = HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Helpdesk agent question is stale.',
                )
                _record_agent_error('resume', exc)
                raise exc

            answer = (choice or reply or '').strip()
            if not answer:
                exc = HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail='A reply or choice is required.',
                )
                _record_agent_error('resume', exc)
                raise exc

            state['turns_taken'] = int(state.get('turns_taken', 0)) + 1
            if _budget_exhausted(state):
                _append_user_reply(state, answer, label='Budget-stop reply')
                draft_turn = await _budget_exhausted_turn(
                    state,
                    [
                        _trace(
                            'resume',
                            'append_user_reply',
                            'success',
                            awaiting.question_id,
                        )
                    ],
                )
                return _persist_and_stamp(
                    draft_turn,
                    db=db,
                    chat_session_id=chat_session_id,
                    user_id=user_id,
                    state=state,
                )

            turn, final_state = await _run_graph(
                Command(
                    resume=answer,
                    update={'entry': 'resume', 'turns_taken': state['turns_taken']},
                ),
                operation='resume',
                graph=graph,
                config=_graph_config(session_id),
            )
            return _persist_and_stamp(
                turn,
                db=db,
                chat_session_id=chat_session_id,
                user_id=user_id,
                state=final_state,
            )

    state = load_checkpoint(session_id, user_id=user_id)
    if state is None:
        raise _state_not_found_exc('resume')
    if _budget_exhausted(state):
        return _persist_and_stamp(
            await _budget_exhausted_turn(state),
            db=db,
            chat_session_id=chat_session_id,
            user_id=user_id,
            state=state,
        )

    awaiting = state.get('awaiting_user')
    if awaiting is None:
        exc = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Helpdesk agent is not waiting for user input.',
        )
        _record_agent_error('resume', exc)
        raise exc
    if pending_question_id and pending_question_id != awaiting.question_id:
        exc = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Helpdesk agent question is stale.',
        )
        _record_agent_error('resume', exc)
        raise exc

    answer = (choice or reply or '').strip()
    if not answer:
        exc = HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='A reply or choice is required.',
        )
        _record_agent_error('resume', exc)
        raise exc

    state['turns_taken'] = int(state.get('turns_taken', 0)) + 1
    if _budget_exhausted(state):
        _append_user_reply(state, answer, label='Budget-stop reply')
        draft_turn = await _budget_exhausted_turn(
            state,
            [_trace('resume', 'append_user_reply', 'success', awaiting.question_id)],
        )
        return _persist_and_stamp(
            draft_turn,
            db=db,
            chat_session_id=chat_session_id,
            user_id=user_id,
            state=state,
        )

    state['entry'] = 'resume'
    state['resume_answer'] = answer
    turn, final_state = await _run_graph(state, operation='resume')
    return _persist_and_stamp(
        turn,
        db=db,
        chat_session_id=chat_session_id,
        user_id=user_id,
        state=final_state,
    )


async def stream_resume_session(  # noqa: C901, PLR0912, PLR0915 - mirrors resume_session during checkpoint rollback window
    session_id: str,
    *,
    user_id: int | str,
    reply: str | None = None,
    choice: str | None = None,
    pending_question_id: str | None = None,
    chat_session_id: int | None = None,
    db: Session | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream graph step events while resuming a paused helpdesk-agent session."""
    _require_agent_enabled()
    if use_langgraph_checkpoint():
        async with helpdesk_graph_for_request() as graph:
            state = await _load_langgraph_state(graph, session_id, user_id=user_id, operation='resume')
            if _budget_exhausted(state):
                turn = _persist_and_stamp(
                    await _budget_exhausted_turn(state),
                    db=db,
                    chat_session_id=chat_session_id,
                    user_id=user_id,
                    state=state,
                )
                yield {'type': 'done', 'turn': turn.model_dump(mode='json')}
                return

            awaiting = state.get('awaiting_user')
            if awaiting is None:
                exc = HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Helpdesk agent is not waiting for user input.',
                )
                _record_agent_error('resume', exc)
                raise exc
            if pending_question_id and pending_question_id != awaiting.question_id:
                exc = HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Helpdesk agent question is stale.',
                )
                _record_agent_error('resume', exc)
                raise exc

            answer = (choice or reply or '').strip()
            if not answer:
                exc = HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail='A reply or choice is required.',
                )
                _record_agent_error('resume', exc)
                raise exc

            state['turns_taken'] = int(state.get('turns_taken', 0)) + 1
            if _budget_exhausted(state):
                _append_user_reply(state, answer, label='Budget-stop reply')
                draft_turn = await _budget_exhausted_turn(
                    state,
                    [
                        _trace(
                            'resume',
                            'append_user_reply',
                            'success',
                            awaiting.question_id,
                        )
                    ],
                )
                turn = _persist_and_stamp(
                    draft_turn,
                    db=db,
                    chat_session_id=chat_session_id,
                    user_id=user_id,
                    state=state,
                )
                yield {'type': 'done', 'turn': turn.model_dump(mode='json')}
                return

            async for event in _stream_graph(
                Command(
                    resume=answer,
                    update={'entry': 'resume', 'turns_taken': state['turns_taken']},
                ),
                operation='resume',
                graph=graph,
                config=_graph_config(session_id),
            ):
                if event.get('type') != '_internal_done':
                    yield event
                    continue
                turn = _persist_and_stamp(
                    event['turn'],
                    db=db,
                    chat_session_id=chat_session_id,
                    user_id=user_id,
                    state=event['state'],
                )
                yield {'type': 'done', 'turn': turn.model_dump(mode='json')}
            return

    state = load_checkpoint(session_id, user_id=user_id)
    if state is None:
        raise _state_not_found_exc('resume')
    if _budget_exhausted(state):
        turn = _persist_and_stamp(
            await _budget_exhausted_turn(state),
            db=db,
            chat_session_id=chat_session_id,
            user_id=user_id,
            state=state,
        )
        yield {'type': 'done', 'turn': turn.model_dump(mode='json')}
        return

    awaiting = state.get('awaiting_user')
    if awaiting is None:
        exc = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Helpdesk agent is not waiting for user input.',
        )
        _record_agent_error('resume', exc)
        raise exc
    if pending_question_id and pending_question_id != awaiting.question_id:
        exc = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Helpdesk agent question is stale.',
        )
        _record_agent_error('resume', exc)
        raise exc

    answer = (choice or reply or '').strip()
    if not answer:
        exc = HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='A reply or choice is required.',
        )
        _record_agent_error('resume', exc)
        raise exc

    state['turns_taken'] = int(state.get('turns_taken', 0)) + 1
    if _budget_exhausted(state):
        _append_user_reply(state, answer, label='Budget-stop reply')
        draft_turn = await _budget_exhausted_turn(
            state,
            [_trace('resume', 'append_user_reply', 'success', awaiting.question_id)],
        )
        turn = _persist_and_stamp(
            draft_turn,
            db=db,
            chat_session_id=chat_session_id,
            user_id=user_id,
            state=state,
        )
        yield {'type': 'done', 'turn': turn.model_dump(mode='json')}
        return

    state['entry'] = 'resume'
    state['resume_answer'] = answer
    async for event in _stream_graph(state, operation='resume', graph=HELPDESK_GRAPH, config=None):
        if event.get('type') != '_internal_done':
            yield event
            continue
        turn = _persist_and_stamp(
            event['turn'],
            db=db,
            chat_session_id=chat_session_id,
            user_id=user_id,
            state=event['state'],
        )
        yield {'type': 'done', 'turn': turn.model_dump(mode='json')}


@trace_agent_run('confirm')
async def confirm_session(
    session_id: str,
    *,
    user_id: int | str,
    draft: TicketDraft,
    idempotency_key: str | None = None,
    chat_session_id: int | None = None,
    db: Session | None = None,
) -> AgentTurn:
    """File a reviewed agent ticket draft after explicit user confirmation."""
    _require_agent_enabled()
    cache_key = _confirm_idempotency_key(user_id, idempotency_key)
    if cache_key is not None:
        cached = _confirm_idempotency_cache.get(cache_key)
        if cached is not None:
            return cached

    if use_langgraph_checkpoint():
        async with helpdesk_graph_for_request() as graph:
            state = await _load_langgraph_state(graph, session_id, user_id=user_id, operation='confirm')
            if state.get('next_action') != 'await_user_confirm' or state.get('draft') is None:
                exc = HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Helpdesk agent is not waiting for ticket confirmation.',
                )
                _record_agent_error('confirm', exc)
                raise exc

            turn, final_state = await _run_graph(
                Command(resume=draft.model_dump(), update={'entry': 'confirm'}),
                operation='confirm',
                graph=graph,
                config=_graph_config(session_id),
            )
            turn = _persist_and_stamp(
                turn,
                db=db,
                chat_session_id=chat_session_id,
                user_id=user_id,
                state=final_state,
            )
            if cache_key is not None:
                _confirm_idempotency_cache.put(cache_key, turn)
            return turn

    state = load_checkpoint(session_id, user_id=user_id)
    if state is None:
        raise _state_not_found_exc('confirm')
    if state.get('next_action') != 'await_user_confirm' or state.get('draft') is None:
        exc = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Helpdesk agent is not waiting for ticket confirmation.',
        )
        _record_agent_error('confirm', exc)
        raise exc

    state['entry'] = 'confirm'
    state['confirm_draft'] = draft
    turn, final_state = await _run_graph(state, operation='confirm')
    turn = _persist_and_stamp(
        turn,
        db=db,
        chat_session_id=chat_session_id,
        user_id=user_id,
        state=final_state,
    )
    if cache_key is not None:
        _confirm_idempotency_cache.put(cache_key, turn)
    return turn


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
    if use_langgraph_checkpoint():
        async with helpdesk_graph_for_request() as graph:
            await _load_langgraph_state(graph, session_id, user_id=user_id, operation='abort')
            turn, final_state = await _run_graph(
                Command(resume={'action': 'abort'}, update={'entry': 'abort'}),
                operation='abort',
                graph=graph,
                config=_graph_config(session_id),
            )
            return _persist_and_stamp(
                turn,
                db=db,
                chat_session_id=chat_session_id,
                user_id=user_id,
                state=final_state,
            )

    state = load_checkpoint(session_id, user_id=user_id)
    if state is None:
        raise _state_not_found_exc('abort')

    state['entry'] = 'abort'
    turn, final_state = await _run_graph(state, operation='abort')
    return _persist_and_stamp(
        turn,
        db=db,
        chat_session_id=chat_session_id,
        user_id=user_id,
        state=final_state,
    )
