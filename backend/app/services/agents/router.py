"""Live LLM campus router (Phase 5).

The router classifies each chat turn into one of the domains registered
in :mod:`backend.app.services.agents.registry`. Today the only enabled
agent is ``helpdesk``; everything else falls back to ``kb_answer`` (the
existing RAG path). The decision is published on chat metadata so the
Vue escalation chip can fire when the router is confident the turn is a
helpdesk issue, in addition to the existing ``kb_resolved=False``
signal.

Design notes
------------
- The router is **off by default** (``CAMPUS_ROUTER_ENABLED=False``); it
  is intended as a demo-mode toggle until trajectory eval has data on
  the LLM router's false-positive rate.
- Mock-mode parity: when the LLM provider is mock, the router uses
  deterministic sentinel matching tied to the existing helpdesk demo
  queries. This keeps PR CI free of model calls and gives the demo a
  repeatable storyline.
- The router never raises: any LLM/parse failure falls back to
  ``kb_answer`` with low confidence so the chat path is never blocked.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.core.config_manager import settings
from backend.app.core.metrics import HELPDESK_AGENT_STARTED_TOTAL
from backend.app.services.agents import registry as agent_registry
from backend.app.services.providers import get_llm_provider

logger = logging.getLogger(__name__)

RouterDomain = Literal['helpdesk', 'kb_answer']

_HELPDESK_SENTINEL_PHRASES: tuple[str, ...] = (
    'oracle financials',
    '[helpdesk-demo]',
    'oracle financials 403',
    'vpn',
    "can't log in",
    'cannot log in',
    'wifi down',
    'campus-wide outage',
    'campus wide outage',
)

_HELPDESK_KEYWORDS: tuple[str, ...] = (
    'outage',
    'ticket',
    'helpdesk',
    'reset my password',
    'password reset',
    'access denied',
    '403',
    'forbidden',
)


class RouterDecision(BaseModel):
    """Structured router output bound to the registered domains."""

    domain: RouterDomain = Field(
        description='Registered agent domain that should handle this turn.',
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description='Calibrated confidence in [0, 1] for the chosen domain.',
    )
    reason: str = Field(
        default='',
        description='One-sentence explanation; safe to surface in traces and tests.',
    )


_DEFAULT_KB_DECISION = RouterDecision(
    domain='kb_answer',
    confidence=0.55,
    reason='default kb_answer (router disabled or no helpdesk signal)',
)


def is_router_enabled() -> bool:
    """Return True when the campus router should run for chat turns."""
    return bool(getattr(settings, 'CAMPUS_ROUTER_ENABLED', False))


def helpdesk_should_escalate(
    decision: RouterDecision | None,
    *,
    kb_resolved: bool | None,
) -> bool:
    """Combine router + ``kb_resolved`` to gate the escalation chip.

    The chip fires when **either**:

    - the KB path could not answer (``kb_resolved is False``), OR
    - the router classified the turn as ``helpdesk`` with confidence at
      or above ``ROUTER_HELPDESK_FLOOR``.

    Returns ``False`` if the helpdesk agent is unregistered/disabled so
    the UI does not promote an action the backend would refuse.
    """
    helpdesk_spec = agent_registry.get_agent('helpdesk')
    if helpdesk_spec is None:
        return False
    if helpdesk_spec.enabled_flag and not getattr(settings, helpdesk_spec.enabled_flag, False):
        return False

    if kb_resolved is False:
        return True

    if decision is None:
        return False

    if decision.domain != 'helpdesk':
        return False
    floor = float(getattr(settings, 'ROUTER_HELPDESK_FLOOR', 0.6) or 0.6)
    return decision.confidence >= floor


def _mock_router(query: str) -> RouterDecision:
    """Deterministic mock router for PR CI and demo mode.

    Returns ``helpdesk`` when the query matches any sentinel phrase used
    by the helpdesk demo, otherwise ``kb_answer``. This mirrors the
    existing helpdesk demo sentinels in ``RAGService._create_mock_response``
    so the mock router and mock RAG path agree.
    """
    text = (query or '').lower()
    if any(phrase in text for phrase in _HELPDESK_SENTINEL_PHRASES):
        return RouterDecision(
            domain='helpdesk',
            confidence=0.9,
            reason='mock router matched helpdesk sentinel phrase',
        )
    if any(re.search(rf'\b{re.escape(kw)}\b', text) for kw in _HELPDESK_KEYWORDS):
        return RouterDecision(
            domain='helpdesk',
            confidence=0.7,
            reason='mock router matched helpdesk keyword',
        )
    return RouterDecision(
        domain='kb_answer',
        confidence=0.6,
        reason='mock router default (no helpdesk signal)',
    )


def _safe_validate(value: Any) -> RouterDecision | None:
    """Validate a model response into a :class:`RouterDecision`.

    Accepts a Pydantic instance or a dict; clamps confidence into
    ``[0, 1]``; rejects unknown domains.
    """
    try:
        if isinstance(value, RouterDecision):
            decision = value
        elif isinstance(value, dict):
            decision = RouterDecision.model_validate(value)
        else:
            decision = RouterDecision.model_validate(value)
    except Exception as exc:
        logger.warning('Campus router validation failed: %s', exc)
        return None
    if decision.domain not in ('helpdesk', 'kb_answer'):
        return None
    return decision


_ROUTER_SYSTEM_PROMPT = (
    'You are the campus chat router. Choose which downstream agent should handle '
    'this turn: "helpdesk" for IT/support issues that should result in a ticket '
    '(account access, outages, hardware, application errors, password resets), or '
    '"kb_answer" for knowledge-base questions about the learning platform, course '
    'tools, integrations, or documentation. Return a structured RouterDecision; '
    'confidence must reflect how clearly the turn is a helpdesk issue.'
)


def classify_domain(query: str, *, allow_live_llm: bool | None = None) -> RouterDecision:
    """Return the router's decision for ``query``.

    ``query`` is the user's most recent message text. ``allow_live_llm``
    forces the deterministic mock router when ``False``; when ``None``,
    falls back to the live LLM only if the configured provider is not
    mock. The function never raises -- LLM failures are logged and
    surfaced as a low-confidence ``kb_answer`` decision.
    """
    if not is_router_enabled():
        return _DEFAULT_KB_DECISION.model_copy(update={'reason': 'router disabled'})

    provider = get_llm_provider()
    use_live = bool(allow_live_llm) if allow_live_llm is not None else (not provider.is_mock)

    if not use_live:
        decision = _mock_router(query)
        _record_started_metric(decision)
        return decision

    try:
        llm = provider.get_llm()
        if not hasattr(llm, 'with_structured_output'):
            logger.warning('Campus router provider %s lacks structured output; using mock fallback', provider.name)
            return _mock_router(query)
        structured = llm.with_structured_output(RouterDecision)
        raw = structured.invoke(
            [
                {'role': 'system', 'content': _ROUTER_SYSTEM_PROMPT},
                {'role': 'user', 'content': query or ''},
            ]
        )
        decision = _safe_validate(raw)
        if decision is None:
            decision = _DEFAULT_KB_DECISION.model_copy(update={'reason': 'invalid LLM router output'})
    except Exception as exc:
        logger.warning('Campus router LLM failed; falling back to kb_answer: %s', exc)
        decision = _DEFAULT_KB_DECISION.model_copy(update={'reason': f'router LLM error: {exc.__class__.__name__}'})
    _record_started_metric(decision)
    return decision


def _record_started_metric(decision: RouterDecision) -> None:
    """Increment the ``llm_router`` trigger counter for helpdesk picks.

    Only ``helpdesk`` classifications are counted -- ``kb_answer`` stays
    in the RAG funnel. The counter shares the existing
    ``HELPDESK_AGENT_STARTED_TOTAL`` series; the label set already
    reserves ``llm_router`` (see ``backend/app/core/metrics.py``).
    """
    if decision.domain != 'helpdesk':
        return
    helpdesk_spec = agent_registry.get_agent('helpdesk')
    if helpdesk_spec is None:
        return
    try:
        HELPDESK_AGENT_STARTED_TOTAL.labels(trigger='llm_router').inc()
    except Exception:
        # Never let metric bookkeeping fail the chat path.
        logger.debug('Failed to record llm_router metric', exc_info=True)


__all__ = [
    'RouterDecision',
    'RouterDomain',
    'classify_domain',
    'helpdesk_should_escalate',
    'is_router_enabled',
]
