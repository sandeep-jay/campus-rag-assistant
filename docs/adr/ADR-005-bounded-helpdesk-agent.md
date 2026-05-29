# ADR-005: Bounded helpdesk agent (LangGraph) over open multi-agent autonomy

**Status:** Accepted
**Date:** 2026-05-27

## Context

When KB retrieval cannot resolve a question (`metadata.kb_resolved=false`), users are left with a dead-end answer. The product needs an escalation path that can:

- Retry retrieval with a different framing
- Search the open web when the KB does not have the answer
- Detect duplicates against existing tickets / issues
- Ask the user clarifying questions before filing
- File a ticket to the appropriate system

A single-shot LLM endpoint (the original `/summarize` + `/draft-ticket` + `/create-issue`) cannot do this — it never sees its own tool outputs and cannot ask follow-ups. A real agent can.

But the project is portfolio-shaped: it has to be **observable, testable, and bounded**. Open-ended multi-agent frameworks (e.g. CrewAI, AutoGen) optimize for autonomy at the cost of:

- **Loop control** — agents that decide their own termination criteria
- **Tool blast radius** — agents that file tickets, send email, or call paid APIs without HITL
- **Cost / latency variance** — many sub-agent calls per user turn
- **Trace clarity** — non-trivial to inspect "what did this agent do and why" for evals or audit

For an enterprise RAG platform that demonstrates production readiness, those defaults are wrong.

## Decision

Implement helpdesk as a **single-supervisor LangGraph** with explicit tool nodes, hard budgets, and a HITL gate on the only side-effecting action (`file_ticket`).

Concretely:

1. **One supervisor LLM** picks `next_action` each turn from a closed enum (`retry_kb`, `web_search`, `search_dups`, `clarify`, `classify`, `propose_solution`, `write_draft`, `await_user_confirm`, `abort`).
2. **Specialists** (clarifier, classifier, draft writer) are separate LLM nodes with focused prompts — easier to evaluate and to swap models per node.
3. **Tools** (`retry_kb`, `web_search`, `search_dups`, `file_ticket`) return structured observations that flow back to the supervisor.
4. **Budgets** are hard caps, not advisory: max supervisor steps, max clarifying questions, max KB/web/dup retries, max tokens per session, max sessions per user per day.
5. **HITL** — `file_ticket` is reachable only through `POST /api/helpdesk/agent/confirm` after the user reviews the rendered draft. The agent never auto-files.
6. **Termination** — every session ends in one of four explicit outcomes: `resolved_by_agent`, `linked`, `filed`, `aborted`.
7. **Persistence** — `SqliteSaver` checkpointer keyed by chat `session_id`, TTL'd at 24 h, so paused sessions can resume without losing state.
8. **Kill switch** — `HELPDESK_AGENT_KILL_SWITCH` disables all agent endpoints with one env flip; the original one-shot endpoints (`/summarize`, `/draft-ticket`, `/create-issue`) remain available as fallback.
9. **Mock-mode parity** — with `provider.is_mock`, the supervisor follows a deterministic scripted plan tied to a sentinel query, so the full flow is demo-able without AWS or GitHub.

## Consequences

**Positive**

- **Observable.** Every supervisor decision and every tool call is a LangGraph node, traced per-span in LangSmith and counted in Prometheus (`chatbot_helpdesk_agent_*`).
- **Testable.** A scenario-based eval rig (`backend/tests/eval/test_helpdesk_agent_scenarios.py`) asserts mock-conversation → expected `next_action` end-to-end without AWS or GitHub.
- **Bounded blast radius.** Tool budgets + HITL gate make it safe to ship behind a feature flag; the worst case is "agent gives up and asks the user to file the ticket manually."
- **Resumable.** Multi-turn pauses for clarifying questions are first-class; the user can close the tab and come back within the checkpoint TTL.
- **Reversible decision.** Because the original one-shot helpdesk endpoints are still mounted, falling back to non-agentic helpdesk is one feature-flag toggle (`HELPDESK_AGENT_ENABLED=false`).

**Negative**

- **More moving parts.** Supervisor + specialists + tools + checkpointer + redaction + budgets is more code than a single endpoint. Mitigated by tests and the eval rig.
- **Latency.** A multi-turn agent is slower than a one-shot endpoint by definition. Mitigated by streaming SSE status events on `/agent/start/stream` and `/agent/resume/stream` so the UI can render activity.
- **No emergent multi-agent behavior.** This is the explicit tradeoff: we sacrifice "agents debating among themselves" for production controls. Listed under "Alternatives considered" rather than treated as a defect.

## Alternatives considered

| Option | Why not |
|---|---|
| **CrewAI / AutoGen-style multi-agent** | Open-ended loops, no HITL by default, harder to bound budgets/termination, harder to trace in LangSmith on a per-node basis |
| **Single supervisor with no specialists** | Less prompt focus; clarifier and classifier benefit from separate prompts and can use smaller models |
| **No agent — keep one-shot endpoints only** | Cannot ask clarifying questions; cannot react to tool output; user has to restart the loop manually |
| **Agent without HITL on `file_ticket`** | Single-step away from auto-filing wrong tickets; not acceptable for a public portfolio piece that demonstrates production thinking |
| **In-memory state instead of SQLite checkpoint** | Loses sessions on API restart; cannot resume across tabs; harder to inspect during review |

## References

- Engineering spec: [docs/roadmap/HELPDESK_AGENT.md](../roadmap/HELPDESK_AGENT.md)
- Product / UX contract: [docs/roadmap/CONVERSATION_FLOW.md](../roadmap/CONVERSATION_FLOW.md)
- Live API surface: [docs/ARCHITECTURE.md](../ARCHITECTURE.md#helpdesk-capabilities-post-rag)
- Privacy / redaction / kill switch: [docs/SECURITY.md](../SECURITY.md)
- Scenario evaluation: [docs/EVALUATION.md](../EVALUATION.md#helpdesk-agent-evaluation)
- Implementation: PRs #37, #41, #42, #43 on `main`
