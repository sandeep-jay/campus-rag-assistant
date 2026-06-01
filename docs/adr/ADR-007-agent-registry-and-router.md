# ADR-007: Agent capability registry and live campus router

**Status:** Proposed
**Date:** 2026-06-01
**Companion:** [ADR-006 — Live LLM supervisor migration](./ADR-006-live-llm-supervisor-migration.md)
**Plan:** [docs/roadmap/AGENTIC_HELPDESK_REBUILD.md §Phase 5](../roadmap/AGENTIC_HELPDESK_REBUILD.md)

## Context

The agentic helpdesk rebuild (ADR-006) lands a real `StateGraph`, an LLM supervisor, specialist nodes, an `AsyncPostgresSaver` checkpointer, and a trajectory-eval gate. With those pieces in place the next step is to **promote the helpdesk agent from "the only thing that runs after RAG" to "one of several campus agents the router can dispatch to"**.

Concretely:

- Today, the Vue UI gates the escalation chip on `kb_resolved == false`. The signal is binary and reactive: the chip appears only after the KB path fails to answer.
- Future agents (research, syllabus, accessibility, ...) cannot be added without surgery in the chat path. Every new agent would mean another flag, another chip, another reactive trigger.
- There is no single place where "which agent owns this turn?" is decided. The chat path implicitly assumes one of "RAG answer" or "RAG failure → helpdesk".

This ADR introduces the seam that lets the codebase grow into multi-agent collaboration without rewriting the chat path each time.

## Decision

Introduce two coupled pieces in Phase 5 (PR 8):

1. **Capability registry** at `backend/app/services/agents/registry.py`. The registry maps `domain` (a stable string key) to an `AgentSpec`:

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

    The registry exposes `register_agent(spec)`, `get_agent(domain)`, `enabled_domains()`, and `unregister_agent(domain)`. The helpdesk agent registers itself at import time. Tests register a no-op `echo` agent to prove the seam (see `backend/tests/services/agents/test_registry.py::test_echo_agent_registers_without_router_changes`). Adding a new agent in a later phase is one line of `register_agent(...)` plus a feature flag — no router changes.

2. **Live campus router** at `backend/app/services/agents/router.py`. The router exposes `classify_domain(query) -> RouterDecision{domain, confidence, reason}`:

    - Returns the deterministic default `kb_answer` when `CAMPUS_ROUTER_ENABLED=false` (the production default).
    - Uses a mock-mode classifier when the LLM provider is mock — sentinel queries (`Oracle Financials 403`, `VPN`, `password reset`, ...) route to `helpdesk`, everything else to `kb_answer`. This keeps PR CI free of LLM calls and gives the trajectory eval a stable storyline.
    - Uses `llm.with_structured_output(RouterDecision)` against the configured provider when the router is enabled. Any parse or HTTP failure falls back to a low-confidence `kb_answer` decision so the chat path is never blocked.

    The decision is published on chat metadata (`metadata.router_decision`) for both the JSON and SSE paths. The Vue UI promotes the escalation chip when **either**:

    - `kb_resolved == false` (the legacy signal stays as-is), or
    - `router_decision.domain == 'helpdesk' AND router_decision.confidence >= ROUTER_HELPDESK_FLOOR` (default `0.6`).

    The backend enforces the same combined gate in `helpdesk_should_escalate(...)` so the UI and any future server-driven escalation agree.

3. **ADR-007 (this file)** is the decision; [`docs/roadmap/AGENT_REGISTRY.md`](../roadmap/AGENT_REGISTRY.md) is the engineering contract a future syllabus / accessibility / research agent follows. The pairing mirrors ADR-006 + `docs/roadmap/AGENTIC_HELPDESK_REBUILD.md`.

## Invariants

The router and registry never break the existing chat flow:

- **Off-by-default.** `CAMPUS_ROUTER_ENABLED=false` ships in `default.py`. PR CI never invokes the live LLM router. Mock-mode demos can opt in.
- **No raised exceptions.** `classify_domain` is wrapped so any provider error falls back to `kb_answer` with a `reason` field that explains why.
- **HITL preserved.** The router never causes a `file_ticket` to fire. It only promotes the escalation chip; the user still confirms in the review modal as in ADR-005.
- **Tool attribution guard preserved.** Router decisions log `reason` strings; none mention vendor or tool brands.
- **Metrics parity.** Helpdesk classifications above the floor increment the existing `chatbot_helpdesk_agent_started_total{trigger="llm_router"}` series. The label was reserved in Phase 6d so no new metric series ships in this PR.

## Consequences

**Positive**

- The chat path has a single seam (the registry) for adding agents. The router code does not change as new domains are added; only the registry call and a feature flag do.
- The Vue UI gains a proactive signal — the escalation chip can fire on confidently helpdesk turns even when the KB answers something generic. This is the "infer, don't ask" UX from `AGENTIC_HELPDESK_REBUILD.md §Demo`.
- ADR-007 + `AGENT_REGISTRY.md` give the next contributor a clear template. The Phase 5 PR ships the helpdesk registration as the worked example.
- Backend and frontend gate the chip the same way, so server-side automation built on top of `helpdesk_should_escalate` (future ChatOps integration, audit reports) cannot drift from the UI.

**Negative**

- The router adds one LLM call per chat turn when enabled. Mitigated by the off-by-default flag and the mock fallback. Cost / latency will be quantified during the live trajectory eval once Phase 5 is live behind the flag in demos.
- Without a calibration set, the default `ROUTER_HELPDESK_FLOOR=0.6` is a judgement call. The trajectory eval (Phase 4) gives us false-positive / false-negative signals to retune the floor before flipping the flag on by default.

## Alternatives considered

| Option | Why not |
|---|---|
| **Skip the registry; keep adding `if/elif` branches in the chat path** | Each new agent then needs a chat-path PR; the chat module would grow into a switchboard that hides the agent contract. The registry pattern makes the contract a single import. |
| **Make the router pick a node directly (no domain key)** | Tight coupling: the router would need to know the helpdesk subgraph object. The `domain -> AgentSpec` indirection lets the router stay a thin classifier and the registry stay the only thing that knows about subgraphs. |
| **Ship the router enabled-by-default in PR 8** | We have no live-LLM false-positive data yet (trajectory eval lives in Phase 4 mock mode). Defaulting to off keeps PR CI behaviour byte-identical, and the flag lets demos opt in immediately. |
| **Combine the router into the supervisor** | Conflates "which agent handles this?" with "what does the helpdesk agent do next?" The two questions have different prompts, different evals (`agent-eval` for the helpdesk supervisor, future router eval for the classifier), and different reversibility properties. |

## References

- Code: [`backend/app/services/agents/registry.py`](../../backend/app/services/agents/registry.py), [`backend/app/services/agents/router.py`](../../backend/app/services/agents/router.py)
- Wiring: [`backend/app/api/chat.py`](../../backend/app/api/chat.py) (router merged into chat metadata for both JSON and SSE paths)
- UI: [`frontend-vue/src/components/chat/MessageBubble.vue`](../../frontend-vue/src/components/chat/MessageBubble.vue) (router-aware escalation chip)
- Tests: [`backend/tests/services/agents/test_registry.py`](../../backend/tests/services/agents/test_registry.py) (seam test), [`backend/tests/services/agents/test_router.py`](../../backend/tests/services/agents/test_router.py) (router contract)
- Plan: [`docs/roadmap/AGENTIC_HELPDESK_REBUILD.md`](../roadmap/AGENTIC_HELPDESK_REBUILD.md) §Phase 5
- Contract: [`docs/roadmap/AGENT_REGISTRY.md`](../roadmap/AGENT_REGISTRY.md)
- Companion: [ADR-006 — Live LLM supervisor migration](./ADR-006-live-llm-supervisor-migration.md)
