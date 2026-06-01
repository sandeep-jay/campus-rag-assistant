"""Campus agent capability registry (Phase 5).

This package introduces a small, side-effect-free registry that pairs a
``domain`` (e.g. ``helpdesk``, ``syllabus``, ``accessibility``) with the
factory that builds its compiled LangGraph subgraph, the tools the agent
exposes, and the settings flag that enables it. The router
(``classify_domain``) consumes the registry to decide which agent should
handle a given chat turn.

Only the ``helpdesk`` agent is registered in Phase 5; ADR-007 and
``docs/roadmap/AGENT_REGISTRY.md`` describe the contract third-party
agents follow.
"""

from backend.app.services.agents.registry import (
    AgentSpec,
    available_domains,
    enabled_domains,
    get_agent,
    register_agent,
    unregister_agent,
)
from backend.app.services.agents.router import (
    RouterDecision,
    classify_domain,
    helpdesk_should_escalate,
    is_router_enabled,
)

__all__ = [
    'AgentSpec',
    'RouterDecision',
    'available_domains',
    'classify_domain',
    'enabled_domains',
    'get_agent',
    'helpdesk_should_escalate',
    'is_router_enabled',
    'register_agent',
    'unregister_agent',
]
