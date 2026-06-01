"""Tests for the campus agent capability registry.

The seam test (``test_echo_agent_registers_without_router_changes``) is
the headline acceptance criterion for Phase 5 PR 8: adding a no-op
``echo`` agent must require only a registry call -- the router code
must not need to change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from backend.app.services.agents import registry as agent_registry
from backend.app.services.agents.registry import AgentSpec
from backend.app.services.agents.router import (
    RouterDecision,
    classify_domain,
    helpdesk_should_escalate,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _restore_registry() -> Iterator[None]:
    """Snapshot the registry before each test so registrations do not leak."""
    snapshot = tuple(agent_registry.iter_specs())
    yield
    for spec in agent_registry.iter_specs():
        if spec not in snapshot:
            agent_registry.unregister_agent(spec.domain)
    for spec in snapshot:
        agent_registry.register_agent(spec)


def _patch_settings(**kwargs):
    return patch.multiple('backend.app.core.config_manager.settings', **kwargs)


def test_helpdesk_is_registered_by_default() -> None:
    spec = agent_registry.get_agent('helpdesk')
    assert spec is not None
    assert spec.name == 'Helpdesk Agent'
    assert spec.enabled_flag == 'HELPDESK_AGENT_ENABLED'
    assert 'file_ticket' in spec.tools
    # The subgraph factory must be a zero-arg callable; we do not invoke
    # it here because that would import the helpdesk graph at test time.
    assert callable(spec.subgraph_factory)


def test_available_domains_includes_helpdesk() -> None:
    domains = agent_registry.available_domains()
    assert 'helpdesk' in domains


def test_enabled_domains_respects_feature_flag() -> None:
    with _patch_settings(HELPDESK_AGENT_ENABLED=True):
        assert 'helpdesk' in agent_registry.enabled_domains()
    with _patch_settings(HELPDESK_AGENT_ENABLED=False):
        assert 'helpdesk' not in agent_registry.enabled_domains()


def test_get_unknown_domain_returns_none() -> None:
    assert agent_registry.get_agent('not-a-real-domain') is None


def test_echo_agent_registers_without_router_changes() -> None:
    """Adding a third-party agent must not require touching the router.

    This is the Phase 5 seam test. We register a no-op ``echo`` agent,
    confirm it appears in the registry, and confirm the router still
    classifies turns into the existing domain set (``helpdesk`` /
    ``kb_answer``) without crashing or learning about ``echo``. A future
    PR can teach the router about additional domains without changing
    the registration contract.
    """

    def _echo_factory() -> str:
        return 'echo-subgraph'

    echo = AgentSpec(
        name='Echo Agent',
        domain='echo',
        subgraph_factory=_echo_factory,
        tools=('echo',),
        enabled_flag='',  # always-on for the test seam
        description='Test-only no-op agent that proves the registry is the only seam.',
    )
    agent_registry.register_agent(echo)
    try:
        assert 'echo' in agent_registry.available_domains()
        assert agent_registry.get_agent('echo') is echo

        with _patch_settings(
            CAMPUS_ROUTER_ENABLED=True,
            ROUTER_HELPDESK_FLOOR=0.6,
            HELPDESK_AGENT_ENABLED=True,
        ):
            decision = classify_domain('how do I submit an assignment in canvas?')
            assert isinstance(decision, RouterDecision)
            # Router contract: still only ``helpdesk`` / ``kb_answer``.
            assert decision.domain in ('helpdesk', 'kb_answer')
    finally:
        agent_registry.unregister_agent('echo')


def test_helpdesk_should_escalate_respects_kb_resolved() -> None:
    with _patch_settings(HELPDESK_AGENT_ENABLED=True, ROUTER_HELPDESK_FLOOR=0.6):
        assert helpdesk_should_escalate(None, kb_resolved=False) is True
        assert helpdesk_should_escalate(None, kb_resolved=True) is False
        assert helpdesk_should_escalate(None, kb_resolved=None) is False


def test_helpdesk_should_escalate_respects_router_floor() -> None:
    above = RouterDecision(domain='helpdesk', confidence=0.85, reason='strong')
    below = RouterDecision(domain='helpdesk', confidence=0.4, reason='weak')
    kb = RouterDecision(domain='kb_answer', confidence=0.95, reason='kb')
    with _patch_settings(HELPDESK_AGENT_ENABLED=True, ROUTER_HELPDESK_FLOOR=0.6):
        assert helpdesk_should_escalate(above, kb_resolved=True) is True
        assert helpdesk_should_escalate(below, kb_resolved=True) is False
        assert helpdesk_should_escalate(kb, kb_resolved=True) is False


def test_helpdesk_should_escalate_returns_false_when_agent_disabled() -> None:
    above = RouterDecision(domain='helpdesk', confidence=0.95, reason='strong')
    with _patch_settings(HELPDESK_AGENT_ENABLED=False, ROUTER_HELPDESK_FLOOR=0.6):
        assert helpdesk_should_escalate(above, kb_resolved=False) is False
        assert helpdesk_should_escalate(above, kb_resolved=True) is False


def test_helpdesk_should_escalate_returns_false_when_agent_unregistered() -> None:
    above = RouterDecision(domain='helpdesk', confidence=0.95, reason='strong')
    agent_registry.unregister_agent('helpdesk')
    assert helpdesk_should_escalate(above, kb_resolved=False) is False
