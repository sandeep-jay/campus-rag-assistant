# ADR-006: Live LLM supervisor migration

**Status:** Proposed
**Date:** 2026-05-31
**Supersedes (partially):** [ADR-005 — Bounded helpdesk agent](./ADR-005-bounded-helpdesk-agent.md) — the unbuilt portions only

## Context

[ADR-005](./ADR-005-bounded-helpdesk-agent.md) committed to a bounded, observable, HITL-gated helpdesk agent on LangGraph. The first slice shipped in `v3.0.0` (PRs #37–#43): topology, tools, redaction, HITL gate, four-outcome termination, multi-turn pause/resume, and mock-mode parity. What did **not** ship as committed:

- The supervisor that picks `next_action` is a **deterministic 3-branch routine** (`supervisor_next_action`), not an LLM with `with_structured_output(SupervisorDecision)`.
- There is **no compiled `StateGraph`** — orchestration is hand-coded in `services/helpdesk_graph/runner.py`. LangSmith therefore sees one flat span per session instead of a graph tree.
- The checkpointer is a **custom JSON-on-SQLite implementation**, not LangGraph's `AsyncPostgresSaver` or `SqliteSaver`. Budgets (`turns_taken`, retries, tokens) are tracked but never read, so the bounded-loop invariant ADR-005 relies on is not actually enforced in code.
- The Clarifier / Classifier / Writer / Solution **specialists** are hand-coded helpers, not LLM nodes with focused prompts.
- The trajectory eval rig (`test_helpdesk_agent_scenarios.py`) ADR-005 references **does not exist** in `backend/tests/eval/`.
- Redaction is applied at LLM input and at GitHub-issue-body filing, but **not on tool inputs** before GitHub Search / Tavily calls — a small but real gap.

These gaps are real but not catastrophic for the shipped product (mock-mode demo, KB / web / dups / file flow, HITL, four outcomes all work end-to-end). They are catastrophic for the claim ADR-005 makes to a senior reviewer reading the doc set — that the agent is "real" in the LLM-supervisor sense.

## Decision

Treat the unbuilt portions of ADR-005 as **superseded by this ADR and by [docs/roadmap/AGENTIC_HELPDESK_REBUILD.md](../roadmap/AGENTIC_HELPDESK_REBUILD.md)**, which delivers them in six phased PRs (one infrastructure PR plus Phases 0–5):

| Phase | What it ships | Reference |
|---|---|---|
| **−1** | `docker-compose.yml` Postgres 14 as the default local dev path; Homebrew Postgres kept as fallback for one release | [rebuild plan §Phase −1](../roadmap/AGENTIC_HELPDESK_REBUILD.md) |
| **0** | Budgets enforced in code; redaction extended to all tool inputs; this ADR-006 lands; HELPDESK_AGENT.md target-state sections moved under a "Target state (in progress)" heading | rebuild §Phase 0 |
| **1a** | Compile a real `StateGraph` mirroring `services/graph/graph.py`; behavior unchanged (supervisor still deterministic) | rebuild §Phase 1a |
| **1b** | `AsyncPostgresSaver` checkpointer with Alembic-owned schema; LangGraph `interrupt()` swap; SQLite + memory fallbacks | rebuild §Phase 1b |
| **2** | Tools wrapped as `@tool` with Pydantic args; LLM supervisor returning `SupervisorDecision`; LLM classifier; conditional clarification; writer specialist; idempotency on `/agent/confirm` | rebuild §Phase 2 |
| **3** | Real `astream_events` SSE; UI activity timeline; node/tool latency + tokens + decision metrics | rebuild §Phase 3 |
| **4** | Trajectory eval split: mock-CI gate (every PR) + live-nightly comparison | rebuild §Phase 4 |
| **5** | Live LLM campus router with capability registry; ADR-007 pairs with this for a future syllabus / accessibility / research agent | rebuild §Phase 5 |

This ADR is the **decision** to migrate; the rebuild roadmap is the **plan**.

## Invariants preserved from ADR-005

The rebuild does not relax any ADR-005 commitment:

- **Closed action enum + allow-list** — supervisor cannot return out-of-enum actions; Pydantic validation rejects invalid outputs.
- **HITL gate** — `file_ticket` remains reachable only via `/agent/confirm`.
- **Four terminal outcomes** — `resolved_by_agent`, `linked`, `filed`, `aborted`.
- **Mock-mode parity** — deterministic scripted plan tied to the sentinel query for demos without AWS / GitHub.
- **Kill switch** — `HELPDESK_AGENT_KILL_SWITCH=true` aborts all in-flight sessions.
- **Reversibility** — `HELPDESK_AGENT_LLM_SUPERVISOR=false` falls back to the deterministic supervisor; the original `/summarize`, `/draft-ticket`, `/create-issue` endpoints stay mounted as cheap fallbacks.

## Consequences

**Positive**

- The repo finally matches its own documentation. Senior reviewers reading ADR-005 + HELPDESK_AGENT.md no longer have to reverse-engineer the code to see what is target vs shipped.
- LangSmith run trees become useful — one tree per session with supervisor, tool, and specialist spans, instead of one flat span.
- Budgets actually bound the loop in code; the "wrong tool budgets" failure mode becomes detectable in trajectory eval.
- The rebuild's Phase 4 eval rig gives a real signal that the LLM supervisor beats the retained deterministic routine on over-ask and false-escalation — the metric ADR-005 implicitly promised.

**Negative**

- Six phased PRs and one infrastructure PR (Phase −1) before the migration is complete. The interim state (after Phase 1a, before Phase 2) is "real `StateGraph`, still deterministic supervisor" — useful for LangSmith but not yet the headline.
- A real LLM supervisor adds latency and per-turn cost vs. the deterministic routine. Mitigated by the LangSmith `astream_events` SSE in Phase 3 (the UI can show "agent is searching existing tickets…" live), and by the eval rig validating that the latency / cost is buying measurable quality.

## Alternatives considered

| Option | Why not |
|---|---|
| **Edit ADR-005 in place** | ADRs are append-only by convention. Editing `Status: Accepted` to "partially implemented" rewrites history. Adding ADR-006 + an `Implementation status` note on ADR-005 is the cleaner pattern. |
| **Ship the LLM supervisor in a single PR** | Too much surface area at once. Phase 1a (`StateGraph`, behavior unchanged) and 1b (`AsyncPostgresSaver`) are mechanical; Phase 2 (LLM supervisor + specialists) is the risky part. Splitting them lets each PR be reverted in isolation behind a flag. |
| **Skip the rebuild — call the current state v3 and move on** | The doc-vs-code gap is the worst signal-to-noise issue in the portfolio set. A senior reviewer who reads ADR-005 and then the code will not give the project the benefit of the doubt. |

## References

- [ADR-005 — Bounded helpdesk agent](./ADR-005-bounded-helpdesk-agent.md)
- [docs/roadmap/AGENTIC_HELPDESK_REBUILD.md](../roadmap/AGENTIC_HELPDESK_REBUILD.md) — phased delivery plan
- [docs/roadmap/HELPDESK_AGENT.md](../roadmap/HELPDESK_AGENT.md) — engineering reference (mixed shipped / target)
- [docs/helpdesk/index.md](../helpdesk/index.md#today-vs-target-state) — shipped-vs-target row table
- Implementation (shipped slice): PRs #37, #41, #42, #43 on `main` (`v3.0.0`)
