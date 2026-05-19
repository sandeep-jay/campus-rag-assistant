# Sprint record — LangGraph live validation (2026-05-18)

> **Archived.** Active design: [LANGGRAPH.md](../LANGGRAPH.md). Roadmap: [PRODUCT_ROADMAP.md](../PRODUCT_ROADMAP.md).

## Goal

Prove LangGraph **KB path** on **live AWS** (Bedrock + Knowledge Base) with real `sources`, then add opt-in web research.

## Outcome

| Delivered | Notes |
|-----------|--------|
| `RAG_ENGINE=langgraph` on live AWS | KB answers with real corpus sources (LMS / policy articles) |
| Linear graph | condense → retrieve → generate → format (rerank/multi-query added in Phase 5 (retrieval)) |
| Web branch | `research_mode=web`; mock + optional Tavily |
| Vue toggle | `VITE_WEB_RESEARCH_ENABLED` + disclaimer UI (Phase 6b) |
| CI | `tox -e lint,backend` green with mock RAG (`RAG_ENGINE=chain` in conftest) |

**Deferred from this sprint:** LangGraph-native SSE (Phase 6 (agentic)a); strict RAGAS ±0.02 gate (Phase 3 lite completed separately).

## Acceptance (manual, live AWS)

1. Set `RAG_ENGINE=langgraph`, AWS credentials, `RAG_FORCE_MOCK=false`.
2. Ask a Canvas LMS or policy question in Vue; confirm `metadata.sources` with KB URLs.
3. Optional: compare same prompt on `RAG_ENGINE=chain`.
4. LangSmith: run name `chat-session-<id>` with condense / retrieve / generate spans.

## Related

- [LANGGRAPH.md](../LANGGRAPH.md) — current graph design
- [WEB_RESEARCH.md](../WEB_RESEARCH.md)
- [EVALUATION.md](../../EVALUATION.md)
