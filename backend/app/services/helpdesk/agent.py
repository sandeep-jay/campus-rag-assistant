r"""Helpdesk LLM tasks (post-RAG escalation).

This module exposes two independent LLM tasks that operate on the tail of a
chat conversation where the RAG assistant could not resolve the question:

- :func:`recap_conversation` — narrative summary the user sees inline.
  Returns a :class:`ConversationSummary` (free-form markdown).
- :func:`draft_ticket` — structured ticket extraction. Returns a
  :class:`TicketDraft` the user reviews in a modal before filing on GitHub.

The two are deliberately decoupled so:

* the inline summary is human-friendly prose, not a ticket schema preview;
* the ticket draft can change shape without disturbing what the user reads
  in chat;
* either action can be performed without the other (Summarize without
  filing, or Create ticket without first viewing a recap).

Shared concerns (mock-mode short-circuit, redaction, trimming to the last N
turns, defensive parsing) are factored into private helpers so both tasks
behave consistently.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from backend.app.core.config_manager import settings
from backend.app.core.metrics import (
    HELPDESK_DRAFT_TICKET_LATENCY_SECONDS,
    HELPDESK_DRAFT_TICKET_TOTAL,
    HELPDESK_RECAP_LATENCY_SECONDS,
    HELPDESK_RECAP_TOTAL,
)
from backend.app.schemas.helpdesk import (
    Category,
    ConversationSummary,
    ConversationTurn,
    Impact,
    Severity,
    TicketDraft,
)
from backend.app.services.helpdesk.redaction import redact_conversation
from backend.app.services.providers import get_llm_provider

logger = logging.getLogger(__name__)


DRAFT_TICKET_SYSTEM_PROMPT = """You are an IT helpdesk assistant. Given a short conversation
between a user and a knowledge-base assistant that could not resolve the issue,
extract a structured support ticket.

Return ONLY a valid JSON object matching this schema exactly:
{
  "title": "<short descriptive title, 80 chars or fewer>",
  "description": "<2-3 sentence restatement of the user problem>",
  "severity": "low|medium|high|critical",
  "category": "network|access|application|hardware|account|other",
  "steps_to_reproduce": "<if inferable from conversation, else null>",
  "impact": "Single user|Team|Campus-wide"
}

Severity guidance:
- critical: system down, many users affected
- high: major feature broken, work blocked
- medium: degraded functionality, workaround exists
- low: minor issue, cosmetic

Rules:
- Output exactly one JSON object.
- Do NOT wrap the JSON in Markdown fences.
- Do NOT include any explanatory text before or after the JSON.
- If a field is unknown, choose the most conservative value (severity=medium,
  category=other, impact="Single user").
"""


RECAP_SYSTEM_PROMPT = """You are an IT helpdesk assistant. Given a short conversation
between a user and a knowledge-base assistant that could not resolve the issue,
produce a concise narrative recap of the conversation for the user to review.

Return plain GitHub-flavored Markdown (no JSON, no code fences) that contains:
- 1-2 short sentences describing what the user asked about, and
- a short bulleted list (3-6 items) of the relevant context, what was tried
  or discussed, and what remains unresolved.

Rules:
- Do NOT propose severity, category, impact, or any ticket-style fields.
- Do NOT invent facts that are not present in the conversation.
- Keep the recap under ~150 words.
- Do not address the user in the second person; describe the conversation
  in the third person (e.g. "The user reported ...").
"""


_FENCE_RE = re.compile(r'^```(?:json)?\s*|\s*```$', re.MULTILINE)


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith('```'):
        text = _FENCE_RE.sub('', text).strip()
    return text


def _extract_text(response: Any) -> str:
    """Extract plain text from a LangChain BaseMessage/AIMessage or raw string."""
    if response is None:
        return ''
    content = getattr(response, 'content', None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get('text') or block.get('content') or '')
            else:
                parts.append(getattr(block, 'text', None) or str(block))
        return ''.join(parts)
    if content is not None:
        return str(content)
    return str(response)


def _format_conversation(turns: list[dict[str, str]]) -> str:
    return '\n'.join(f"{turn.get('role', '').upper()}: {turn.get('content', '')}" for turn in turns)


def _trim_turns(turns: list[dict[str, str]], max_turns: int) -> list[dict[str, str]]:
    if max_turns <= 0 or len(turns) <= max_turns:
        return turns
    return turns[-max_turns:]


def _prepare_turns(turns: list[ConversationTurn]) -> list[dict[str, str]]:
    """Apply the shared trim + redact pipeline before any LLM call."""
    raw = [{'role': t.role, 'content': t.content} for t in turns]
    raw = _trim_turns(raw, settings.HELPDESK_SUMMARIZE_MAX_TURNS)
    return redact_conversation(raw)


async def _ainvoke(llm: Any, prompt: list[dict[str, str]]) -> Any:
    if hasattr(llm, 'ainvoke'):
        return await llm.ainvoke(prompt)
    return llm.invoke(prompt)


# ---------------------------------------------------------------------------
# Conversation recap (Summarize button)
# ---------------------------------------------------------------------------


def _build_mock_recap(turns: list[dict[str, str]]) -> ConversationSummary:
    last_user = next(
        (t.get('content', '') for t in reversed(turns) if (t.get('role') or '').lower() == 'user'),
        '',
    )
    headline = (last_user.strip().splitlines() or ['an unspecified issue'])[0]
    body = (
        f'The user reported: {headline}.\n'
        '\n'
        '- The knowledge base did not return a confident answer.\n'
        '- No remediation steps were proposed in the conversation.\n'
        '- The user has not yet escalated this to a human helpdesk owner.'
    )
    return ConversationSummary(summary=body)


async def recap_conversation(turns: list[ConversationTurn]) -> ConversationSummary:
    """Produce a narrative recap of the conversation for inline display.

    Returns plain markdown wrapped in :class:`ConversationSummary`. Raises
    ``HTTPException(502)`` if the underlying LLM call fails.
    """
    safe_turns = _prepare_turns(turns)
    provider = get_llm_provider()
    started = time.perf_counter()

    if provider.is_mock:
        HELPDESK_RECAP_TOTAL.labels(outcome='mock').inc()
        HELPDESK_RECAP_LATENCY_SECONDS.observe(time.perf_counter() - started)
        return _build_mock_recap(safe_turns)

    llm = provider.get_llm()
    prompt = [
        {'role': 'system', 'content': RECAP_SYSTEM_PROMPT},
        {'role': 'user', 'content': f'Conversation:\n{_format_conversation(safe_turns)}'},
    ]

    try:
        response = await _ainvoke(llm, prompt)
    except Exception as exc:
        HELPDESK_RECAP_TOTAL.labels(outcome='llm_error').inc()
        HELPDESK_RECAP_LATENCY_SECONDS.observe(time.perf_counter() - started)
        logger.exception('Helpdesk recap LLM call failed: %s', exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Helpdesk summarizer is unavailable. Please try again later.',
        ) from exc

    text = _extract_text(response).strip()
    if not text:
        HELPDESK_RECAP_TOTAL.labels(outcome='llm_error').inc()
        HELPDESK_RECAP_LATENCY_SECONDS.observe(time.perf_counter() - started)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Helpdesk summarizer returned an empty recap. Please try again.',
        )

    HELPDESK_RECAP_TOTAL.labels(outcome='success').inc()
    HELPDESK_RECAP_LATENCY_SECONDS.observe(time.perf_counter() - started)
    return ConversationSummary(summary=text)


# ---------------------------------------------------------------------------
# Structured ticket draft (Create ticket button)
# ---------------------------------------------------------------------------


def _build_mock_draft(turns: list[dict[str, str]]) -> TicketDraft:
    last_user = next(
        (t.get('content', '') for t in reversed(turns) if (t.get('role') or '').lower() == 'user'),
        '',
    )
    base_title = (last_user or 'User reported issue').strip().splitlines()[0]
    title = (base_title[:80] or 'User reported issue').strip()
    description = f"User reported: {last_user.strip() or 'an unspecified issue'}. " 'The knowledge base could not resolve this request.'
    return TicketDraft(
        title=title,
        description=description,
        severity=Severity.medium,
        category=Category.other,
        steps_to_reproduce=None,
        impact=Impact.single_user,
    )


def _parse_draft(raw: str) -> TicketDraft:
    text = _strip_fences(raw)
    data = json.loads(text)
    return TicketDraft(**data)


async def draft_ticket(turns: list[ConversationTurn]) -> TicketDraft:
    """Extract a structured support-ticket draft from conversation history.

    Returns a :class:`TicketDraft`. Raises ``HTTPException(502)`` on
    unrecoverable LLM or parse failures.
    """
    safe_turns = _prepare_turns(turns)
    provider = get_llm_provider()
    started = time.perf_counter()

    if provider.is_mock:
        HELPDESK_DRAFT_TICKET_TOTAL.labels(outcome='mock').inc()
        HELPDESK_DRAFT_TICKET_LATENCY_SECONDS.observe(time.perf_counter() - started)
        return _build_mock_draft(safe_turns)

    llm = provider.get_llm()
    prompt = [
        {'role': 'system', 'content': DRAFT_TICKET_SYSTEM_PROMPT},
        {'role': 'user', 'content': f'Conversation:\n{_format_conversation(safe_turns)}'},
    ]

    try:
        response = await _ainvoke(llm, prompt)
    except Exception as exc:
        HELPDESK_DRAFT_TICKET_TOTAL.labels(outcome='llm_error').inc()
        HELPDESK_DRAFT_TICKET_LATENCY_SECONDS.observe(time.perf_counter() - started)
        logger.exception('Helpdesk draft-ticket LLM call failed: %s', exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Helpdesk summarizer is unavailable. Please try again later.',
        ) from exc

    raw_text = _extract_text(response)
    try:
        draft = _parse_draft(raw_text)
    except (json.JSONDecodeError, ValidationError) as exc:
        retry_prompt = [
            *prompt,
            {'role': 'assistant', 'content': raw_text},
            {
                'role': 'user',
                'content': 'That was not valid JSON. Respond again with ONLY the JSON object, no fences, no prose.',
            },
        ]
        try:
            retry_response = await _ainvoke(llm, retry_prompt)
            draft = _parse_draft(_extract_text(retry_response))
        except Exception:
            HELPDESK_DRAFT_TICKET_TOTAL.labels(outcome='parse_error').inc()
            HELPDESK_DRAFT_TICKET_LATENCY_SECONDS.observe(time.perf_counter() - started)
            logger.exception('Helpdesk draft-ticket returned unparseable JSON: %s', exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Could not parse a ticket draft from the assistant. Please try again.',
            ) from exc

    HELPDESK_DRAFT_TICKET_TOTAL.labels(outcome='success').inc()
    HELPDESK_DRAFT_TICKET_LATENCY_SECONDS.observe(time.perf_counter() - started)
    return draft
