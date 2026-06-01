# ADR-002: Dual RAG engines (`chain` vs `langgraph`)

**Status:** Accepted  
**Date:** 2026-05-19

## Context

Production chat needs low-latency **token streaming** (SSE). Engineering and evaluation need **observable RAG stages** (condense, multi-query, retrieve, rerank) and flag-gated retrieval tuning without growing a monolithic chain class.

## Decision

Support two engines behind `RAG_ENGINE`:

| | `chain` | `langgraph` |
|---|---------|-------------|
| **Implementation** | LangChain `ConversationalRetrievalChain` | Compiled graph in `backend/app/services/graph/` |
| **Streaming** | True token streaming via `astream_events` | Status event + paced chunks after `graph.invoke()` |
| **Observability** | Chain-level LangSmith runs | Per-node spans |
| **Default in CI** | **Yes** (`conftest` forces `chain`) | Local/live when configured |

Both paths share the provider registry and the same API response contract.

## Consequences

**Positive**

- Operators can choose streaming vs observability per environment.
- Retrieval tuning (multi-query, rerank) is explicit graph nodes, not buried in chain config.
- Eval can compare engines on the same golden set when `RAGAS_EVAL=1` preserves `RAG_ENGINE` from env.

**Negative**

- Two code paths to maintain and test.
- LangGraph path trades time-to-first-token for span clarity until Phase 6a (native SSE).
- Interviewers may ask about complexity—frame as explicit migration tradeoff, not accidental duplication.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| LangGraph only | Loses true Bedrock token streaming on chain path |
| Chain only | Harder to add multi-query/rerank as testable stages |
| Open-ended multi-agent | Cost, flakiness, poor observability for production RAG |

## References

- [ADR-001 — Provider registry](./ADR-001-provider-registry.md)
- [DESIGN.md — Dual RAG engines](../DESIGN.md#dual-rag-engines-chain-vs-langgraph)
- [DESIGN.md — LangGraph KB path](../DESIGN.md#langgraph-kb-path-multi-query--retrieve--rerank)
- `backend/app/services/rag.py`, `backend/app/services/graph/`
