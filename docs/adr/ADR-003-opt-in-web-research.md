# ADR-003: Opt-in web research

**Status:** Accepted  
**Date:** 2026-05-19

## Context

Campus KB answers must default to **governed corpus** content. Many RAG demos silently fall back to open-web search when retrieval is weak—eroding trust and auditability.

## Decision

Web search is **per message**, not automatic:

- Client sends `research_mode=web` on the chat request (Vue toggle).
- Server gates on `WEB_RESEARCH_ENABLED` and provider (`mock` | `tavily`).
- UI shows a **disclaimer banner** on web answers; sources use `source_kind=web`.
- LangGraph web path: `condense → web_search → generate → format` (skips KB rerank).

KB path always retrieves first; web is never a silent fallback when retrieval scores are low.

## Consequences

**Positive**

- Clear trust model for institutional deployments.
- Operators can disable web entirely via config.
- Demo-friendly mock web provider without Tavily API keys.

**Negative**

- Users must explicitly opt in—extra UI step vs “always augmented” assistants.
- Web answers are not grounded in the campus KB; disclaimer is required.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Always-on web augmentation | Conflicts with KB governance story |
| Silent fallback when retrieval fails | Hides weak retrieval; hard to debug |
| Separate web-only product | Duplicates auth, sessions, and UI |

## References

- [DESIGN.md — Opt-in web research](../DESIGN.md#opt-in-web-research)
- [roadmap/WEB_RESEARCH.md](../roadmap/WEB_RESEARCH.md)
- `backend/app/services/tools/web_search.py`
- `backend/app/services/graph/nodes.py`
