# Agent capability registry — contract

The campus agent registry is the single seam every new agent plugs into. The router (`backend/app/services/agents/router.py`) reads only the registry, so adding a new domain is one line of `register_agent(...)` plus a feature flag. This doc is the engineering contract for that registration.

> Companion ADR: [ADR-007 — Agent registry and router](../adr/ADR-007-agent-registry-and-router.md). Plan: [`AGENTIC_HELPDESK_REBUILD.md`](./AGENTIC_HELPDESK_REBUILD.md) §Phase 5.

## What is registered

```python
@dataclass(frozen=True)
class AgentSpec:
    name: str
    domain: str
    subgraph_factory: Callable[[], Any]
    tools: tuple[str, ...] = ()
    enabled_flag: str = ''
    description: str = ''
```

| Field | Required | Purpose |
|---|---|---|
| `name` | yes | Human-readable name surfaced in LangSmith trace tags, logs, and registry docs. |
| `domain` | yes | Stable lookup key the router emits. Lower-snake-case; treat as a public API. |
| `subgraph_factory` | yes | Zero-arg callable that returns either a compiled `CompiledStateGraph` **or** an async context manager that yields one. The helpdesk registration shows the canonical async pattern. |
| `tools` | no | Names of tools the agent owns. Documentation today; future phases may use it for per-agent allow-lists. |
| `enabled_flag` | no | Name of the `settings` boolean that gates the agent. Empty string means "always on" (test-only). |
| `description` | no | One-line summary for ADR-007 / registry docs. |

## Registration pattern

A new agent registers itself at import time using `register_agent(...)`:

```python
# backend/app/services/agents/registry.py (excerpt — helpdesk is registered this way)
def _helpdesk_subgraph_factory():
    from backend.app.services.helpdesk_graph.graph import helpdesk_graph_for_request

    return helpdesk_graph_for_request()


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
```

The factory is imported lazily so app startup does not pay each agent's import cost when its `enabled_flag` is false.

### What the seam test guarantees

`backend/tests/services/agents/test_registry.py::test_echo_agent_registers_without_router_changes` adds a no-op `echo` agent and confirms:

- The registry exposes `echo` via `available_domains()` / `get_agent(...)`.
- The router still classifies turns into the existing `helpdesk` / `kb_answer` domain set without crashing.
- Removing the test agent restores the registry state.

If a contributor adds a new agent and this test breaks, the registration touched a constraint outside the registry — usually a hard-coded enum elsewhere. The fix is to widen the seam, not to widen the test.

## Router contract

The router translates a user turn into a `RouterDecision`:

```python
class RouterDecision(BaseModel):
    domain: Literal['helpdesk', 'kb_answer']
    confidence: float  # in [0, 1]
    reason: str = ''
```

- `CAMPUS_ROUTER_ENABLED=false` (default) → deterministic `kb_answer` decision with `reason="router disabled"`. PR CI defaults to this.
- Enabled + mock provider → sentinel-driven mock router (see `_mock_router` in `router.py`). Helpdesk demo queries return `helpdesk` with high confidence; everything else returns `kb_answer`.
- Enabled + live provider → structured output via `llm.with_structured_output(RouterDecision)`. Any parse/HTTP failure logs a warning and returns `kb_answer` with `reason="router LLM error: <ClassName>"`.

### Escalation gate

`helpdesk_should_escalate(decision, kb_resolved)` returns True when **either**:

- The KB path could not answer (`kb_resolved is False`), or
- The router returned `domain == 'helpdesk'` with `confidence >= ROUTER_HELPDESK_FLOOR` (default `0.6`).

If the helpdesk agent is unregistered or its `enabled_flag` is false, the gate returns False even when both signals fire — the UI must never promote a backend the server would refuse.

### Adding a new domain to the router

The router currently classifies into the closed set `{helpdesk, kb_answer}`. Adding a new domain (e.g. `syllabus`) is two PRs:

1. **Registration PR.** Register the new `AgentSpec`, add a feature flag (`SYLLABUS_AGENT_ENABLED`), wire the subgraph factory. The seam test still passes because the router contract is unchanged.
2. **Router PR.** Widen `RouterDomain` to include the new key, extend the LLM prompt and mock-mode sentinels, add trajectory-eval scenarios. The escalation-gate helper in `helpdesk_should_escalate` stays helpdesk-specific; new domains add their own gate helper.

Splitting the two lets the registration land behind a flag without touching the router, and lets the router land with calibration data already on hand.

## Operational notes

- The registry uses a process-local `RLock`. Re-registering the same domain replaces the prior spec; tests rely on this for fakes.
- `iter_specs()` returns a tuple snapshot — callers do not need to hold the lock.
- The helpdesk subgraph factory wraps an async context manager (it lazily compiles a graph with a per-request checkpointer). New agents that share the same shape should follow the helpdesk registration; agents that do not need request-scoped checkpoints can return a compiled graph directly.

## References

- ADR: [ADR-007 — Agent registry and router](../adr/ADR-007-agent-registry-and-router.md)
- Plan: [`AGENTIC_HELPDESK_REBUILD.md`](./AGENTIC_HELPDESK_REBUILD.md) §Phase 5
- Code: [`backend/app/services/agents/registry.py`](../../backend/app/services/agents/registry.py), [`backend/app/services/agents/router.py`](../../backend/app/services/agents/router.py)
- Tests: [`backend/tests/services/agents/test_registry.py`](../../backend/tests/services/agents/test_registry.py), [`backend/tests/services/agents/test_router.py`](../../backend/tests/services/agents/test_router.py)
