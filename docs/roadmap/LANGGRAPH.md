# LangGraph integration

Deterministic RAG orchestration behind `RAGService.process_query` — **not** multi-agent by default.

**Status:** KB graph shipped on live AWS; paced SSE. See [PORTFOLIO_PHASED_ROADMAP.md](./PORTFOLIO_PHASED_ROADMAP.md).

**Order:** Phase 4 (this doc) **before** Phase 3 RAGAS gates. Web branch: [WEB_RESEARCH.md](./WEB_RESEARCH.md).

---

## Why LangGraph here

| Benefit | Notes |
|---------|--------|
| Explicit steps | condense → retrieve → generate → format |
| Web branch | `research_mode=web` → web_search tool node |
| Testability | Unit test each node |
| LangSmith | Per-node spans |
| Extensibility | Phase 5 adds rerank / multi-query as nodes |

LangChain runs **inside each node** (`llm.invoke`, `retriever.invoke`).

---

## Architecture (KB + web)

```mermaid
flowchart TB
  API[chat.py] --> RAG[RAGService.process_query]
  RAG --> Engine{RAG_ENGINE}
  Engine -->|chain| Legacy[ConversationalRetrievalChain]
  Engine -->|langgraph| Graph[RagGraph]
  Graph --> Route{research_mode}
  Route -->|kb| Condense --> Retrieve --> Generate
  Route -->|web| CondenseW --> WebSearch --> Generate
  Generate --> Format[format_response]
```

**Contract:**

```json
{ "message": "...", "metadata": { "sources": [], "document_contents": [], "source_kind": "kb" } }
```

---

## Module layout

```
backend/app/services/graph/
  state.py
  nodes.py
  graph.py
  runner.py
backend/app/services/tools/
  web_search.py
```

---

## Configuration

```bash
RAG_ENGINE=chain              # chain | langgraph (default chain)
WEB_RESEARCH_ENABLED=false
WEB_SEARCH_PROVIDER=mock      # mock | tavily
RAG_AGENTIC_ENABLED=false     # rewrite loop — later
```

---

## Today MVP scope

| In scope | Out of scope |
|----------|----------------|
| Buffered `process_query` on graph | LangGraph SSE |
| KB linear path + web branch | RAGAS ±0.02 gate |
| Mock web search | Delete chain path |
| Unit tests (mock) | Auto web without user flag |

---

## Rollout

| Step | Action |
|------|--------|
| 1 | Graph module + `RAG_ENGINE` (default `chain`) |
| 2 | Wire `process_query`; tests green |
| 3 | Web tool + `research_mode` |
| 4 | Optional: flip default to `langgraph` after spot-check |

Full RAGAS parity: Phase 3 lite (deferred).

---

## Related

- [WEB_RESEARCH.md](./WEB_RESEARCH.md)
- [PORTFOLIO_PHASED_ROADMAP.md](./PORTFOLIO_PHASED_ROADMAP.md)
- [EVALUATION.md](../EVALUATION.md)


## Live validation

- **AWS KB parity (2026-05-18):** `RAG_ENGINE=langgraph` returns real `metadata.sources` on Bedrock + Knowledge Base; validated against `chain` on the same prompts.
- **Latency (LangSmith):** Typical run ~4–8s — `generate` (~6s) dominates; `condense` (~1.3s) on follow-ups only; `retrieve` ~0.5s. See [PORTFOLIO_PHASED_ROADMAP.md](./PORTFOLIO_PHASED_ROADMAP.md).
- **Streaming:** SSE uses status + paced chunks after `graph.invoke()`; native graph/Bedrock streaming is a follow-up.
