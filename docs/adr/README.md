# Architecture Decision Records (ADRs)

Compact records of significant design choices. Full rationale lives in [DESIGN.md](../DESIGN.md); each ADR captures the decision, consequences, and references.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](./ADR-001-provider-registry.md) | Provider registry (AWS / Azure / mock) | Accepted |
| [ADR-002](./ADR-002-langgraph-vs-chain.md) | Dual RAG engines: `chain` vs `langgraph` | Accepted |
| [ADR-003](./ADR-003-opt-in-web-research.md) | Opt-in web research | Accepted |
| [ADR-004](./ADR-004-eval-gating-policy.md) | RAGAS eval gating policy | Accepted |
| [ADR-005](./ADR-005-bounded-helpdesk-agent.md) | Bounded helpdesk agent (LangGraph) | Accepted (mixed implementation — see ADR-006) |
| [ADR-006](./ADR-006-live-llm-supervisor-migration.md) | Live LLM supervisor migration (supersedes unbuilt portions of ADR-005) | Proposed |

## Template

New ADRs should follow this shape:

```markdown
# ADR-NNN: Title

**Status:** Proposed | Accepted | Superseded
**Date:** YYYY-MM-DD

## Context
What problem or constraint drove the decision?

## Decision
What we chose.

## Consequences
Positive and negative outcomes.

## Alternatives considered
What we did not choose and why.

## References
Links to code and docs.
```
