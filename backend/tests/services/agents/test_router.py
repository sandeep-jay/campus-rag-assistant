"""Tests for the campus router (``classify_domain``).

The router contract under PR CI is:

- Disabled by default -> deterministic ``kb_answer`` decision with a
  ``reason`` that calls out the disabled state.
- Enabled + mock provider -> sentinel-driven decision; helpdesk demo
  queries route to ``helpdesk``, everything else to ``kb_answer``.
- Enabled + live provider -> structured LLM output; on parse/HTTP
  failure the router never raises and falls back to ``kb_answer``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.app.services.agents import registry as agent_registry
from backend.app.services.agents.router import (
    RouterDecision,
    classify_domain,
    is_router_enabled,
)
from backend.app.services.providers.base import BaseLlmProvider


def _patch_settings(**kwargs):
    return patch.multiple('backend.app.core.config_manager.settings', **kwargs)


def test_router_disabled_returns_kb_answer_with_disabled_reason() -> None:
    with _patch_settings(CAMPUS_ROUTER_ENABLED=False):
        assert is_router_enabled() is False
        decision = classify_domain('Canvas is down for everyone in the dorms')
        assert decision.domain == 'kb_answer'
        assert 'disabled' in decision.reason


def test_router_enabled_mock_provider_routes_helpdesk_sentinel() -> None:
    with _patch_settings(CAMPUS_ROUTER_ENABLED=True, LLM_PROVIDER='mock', RAG_FORCE_MOCK=True):
        decision = classify_domain('My Oracle Financials login is throwing 403')
        assert decision.domain == 'helpdesk'
        assert decision.confidence >= 0.6


def test_router_enabled_mock_provider_keyword_matches_helpdesk() -> None:
    with _patch_settings(CAMPUS_ROUTER_ENABLED=True, LLM_PROVIDER='mock', RAG_FORCE_MOCK=True):
        decision = classify_domain('Please reset my password, I cannot log in')
        assert decision.domain == 'helpdesk'


def test_router_enabled_mock_provider_routes_kb_for_general_query() -> None:
    with _patch_settings(CAMPUS_ROUTER_ENABLED=True, LLM_PROVIDER='mock', RAG_FORCE_MOCK=True):
        decision = classify_domain('How do I submit an assignment in Canvas?')
        assert decision.domain == 'kb_answer'


def test_router_live_provider_uses_structured_output() -> None:
    fake_llm = MagicMock()
    structured = MagicMock()
    structured.invoke.return_value = RouterDecision(
        domain='helpdesk',
        confidence=0.92,
        reason='LLM said so',
    )
    fake_llm.with_structured_output.return_value = structured

    class _StubProvider(BaseLlmProvider):
        name = 'stub'
        is_mock = False

        def get_llm(self):
            return fake_llm

    with (
        _patch_settings(CAMPUS_ROUTER_ENABLED=True),
        patch(
            'backend.app.services.agents.router.get_llm_provider',
            return_value=_StubProvider(),
        ),
    ):
        decision = classify_domain("VPN won't connect, can you help?")
    assert decision.domain == 'helpdesk'
    assert decision.confidence == pytest.approx(0.92)
    fake_llm.with_structured_output.assert_called_once()


def test_router_live_provider_failure_falls_back_to_kb_answer() -> None:
    fake_llm = MagicMock()
    fake_llm.with_structured_output.side_effect = RuntimeError('boom')

    class _StubProvider(BaseLlmProvider):
        name = 'stub'
        is_mock = False

        def get_llm(self):
            return fake_llm

    with (
        _patch_settings(CAMPUS_ROUTER_ENABLED=True),
        patch(
            'backend.app.services.agents.router.get_llm_provider',
            return_value=_StubProvider(),
        ),
    ):
        decision = classify_domain('Anything')
    assert decision.domain == 'kb_answer'
    assert 'router LLM error' in decision.reason


def test_router_records_metric_for_helpdesk_classification() -> None:
    with (
        _patch_settings(CAMPUS_ROUTER_ENABLED=True, LLM_PROVIDER='mock', RAG_FORCE_MOCK=True),
        patch('backend.app.services.agents.router.HELPDESK_AGENT_STARTED_TOTAL') as metric,
    ):
        classify_domain('Oracle Financials 403 error')
    # The mock router classifies sentinel queries as helpdesk, which
    # should increment the ``llm_router`` trigger counter exactly once.
    metric.labels.assert_called_with(trigger='llm_router')
    metric.labels.return_value.inc.assert_called_once()


def test_router_does_not_record_metric_for_kb_classification() -> None:
    with (
        _patch_settings(CAMPUS_ROUTER_ENABLED=True, LLM_PROVIDER='mock', RAG_FORCE_MOCK=True),
        patch('backend.app.services.agents.router.HELPDESK_AGENT_STARTED_TOTAL') as metric,
    ):
        classify_domain('What is the syllabus for CS101?')
    metric.labels.assert_not_called()


def test_router_decision_validates_domain_field() -> None:
    with pytest.raises(ValidationError):
        RouterDecision(domain='other', confidence=0.5)  # type: ignore[arg-type]


def test_router_decision_clamps_confidence_at_validation() -> None:
    with pytest.raises(ValidationError):
        RouterDecision(domain='helpdesk', confidence=1.5)
    with pytest.raises(ValidationError):
        RouterDecision(domain='helpdesk', confidence=-0.1)


def test_helpdesk_agent_registration_unaffected_by_router_module() -> None:
    """Importing the router must not de-register the default helpdesk agent."""
    assert agent_registry.get_agent('helpdesk') is not None
