"""Capability registry mapping campus ``domain`` -> ``AgentSpec``.

The registry is the single seam every new agent (syllabus, accessibility,
research, ...) plugs into. The router (``classify_domain``) reads only
the registry, so adding a new domain is a one-line registration plus an
``enabled_flag`` -- no router changes required. ADR-007 documents the
contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import TYPE_CHECKING, Any

from backend.app.core.config_manager import settings

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


@dataclass(frozen=True)
class AgentSpec:
    """Static description of a campus agent.

    Fields
    ------
    ``name``: Human-readable name shown in traces and logs (``"Helpdesk Agent"``).
    ``domain``: Registry key the router emits (``"helpdesk"``).
    ``subgraph_factory``: Zero-arg callable that returns either a compiled
    LangGraph object **or** an async context manager that yields one. The
    runner picks the right invocation pattern; see the ``helpdesk``
    registration below for the canonical example.
    ``tools``: Names of tools the agent owns. Treated as documentation today
    (used in registry tests and ADR-007); future phases may wire it into
    per-agent allow-lists.
    ``enabled_flag``: Name of the ``settings`` boolean that gates the agent.
    The router skips agents whose flag is falsy.
    ``description``: One-line summary for ADR-007 / registry docs.
    """

    name: str
    domain: str
    subgraph_factory: Callable[[], Any]
    tools: tuple[str, ...] = ()
    enabled_flag: str = ''
    description: str = ''


_REGISTRY: dict[str, AgentSpec] = {}
_LOCK = RLock()


def register_agent(spec: AgentSpec) -> None:
    """Register an :class:`AgentSpec`. Re-registering the same domain replaces it.

    Re-registration is intentional: tests use it to swap in fake specs and
    later phases may want to hot-reload registry entries from config.
    """
    with _LOCK:
        _REGISTRY[spec.domain] = spec


def unregister_agent(domain: str) -> None:
    """Remove ``domain`` from the registry (test/cleanup helper)."""
    with _LOCK:
        _REGISTRY.pop(domain, None)


def get_agent(domain: str) -> AgentSpec | None:
    """Return the :class:`AgentSpec` for ``domain``, or ``None`` if unknown."""
    with _LOCK:
        return _REGISTRY.get(domain)


def available_domains() -> tuple[str, ...]:
    """Return every registered domain, regardless of feature-flag state."""
    with _LOCK:
        return tuple(sorted(_REGISTRY))


def enabled_domains() -> tuple[str, ...]:
    """Return the subset of registered domains whose ``enabled_flag`` is true."""
    with _LOCK:
        return tuple(sorted(domain for domain, spec in _REGISTRY.items() if _flag_enabled(spec)))


def _flag_enabled(spec: AgentSpec) -> bool:
    if not spec.enabled_flag:
        return True
    return bool(getattr(settings, spec.enabled_flag, False))


def iter_specs() -> Iterable[AgentSpec]:
    """Iterate over a snapshot of the current registry (lock-free for callers)."""
    with _LOCK:
        return tuple(_REGISTRY.values())


def _helpdesk_subgraph_factory() -> Any:
    """Return the helpdesk agent's compiled LangGraph context manager.

    Imported lazily so app startup does not pay the helpdesk-graph import
    cost when the helpdesk agent is disabled. The router never invokes
    the factory unless ``HELPDESK_AGENT_ENABLED`` is true.
    """
    from backend.app.services.helpdesk_graph.graph import helpdesk_graph_for_request

    return helpdesk_graph_for_request()


def _bootstrap_default_registry() -> None:
    register_agent(
        AgentSpec(
            name='Helpdesk Agent',
            domain='helpdesk',
            subgraph_factory=_helpdesk_subgraph_factory,
            tools=('retry_kb', 'web_search', 'search_existing_issues', 'file_ticket'),
            enabled_flag='HELPDESK_AGENT_ENABLED',
            description='Bounded multi-turn IT helpdesk loop with HITL ticket filing.',
        )
    )


_bootstrap_default_registry()


__all__ = [
    'AgentSpec',
    'available_domains',
    'enabled_domains',
    'get_agent',
    'iter_specs',
    'register_agent',
    'unregister_agent',
]
