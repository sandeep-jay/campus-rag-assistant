# Design and architecture decisions

This document records **why** the system is shaped the way it is. For component diagrams and request flows, see [ARCHITECTURE.md](./ARCHITECTURE.md). For graph node detail, see [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md).

**Last updated:** 2026-05-19

---

## Product scope

Campus RAG Assistant is a **retrieval-augmented chat application** for **campus teaching, learning, and education IT knowledge** (for example Canvas LMS and LTI tooling, accessibility and inclusive teaching guidance, and ServiceNow IT knowledge articles). Users ask natural-language questions; the system retrieves grounded context, generates a structured answer with citations, and keeps per-user chat history.

It is an independent evolution of the upstream [chabot](https://github.com/ets-berkeley-edu/chabot) codebase: same problem domain (institutional knowledge), expanded platform surface (Vue SPA, provider registry, LangGraph pipeline, formal evaluation).

---


## Product boundaries

### In scope

- Q&A over **institutional knowledge** — Canvas LMS, LTI tools, accessibility, inclusive teaching and learning, ServiceNow IT articles, and institutional policies.
- **Cited answers** with expandable source excerpts in the UI.
- **Multi-turn chat** with session history and thumbs-up/down feedback.
- **Per-tenant** prompt and topic configuration (`tenant.rag_config`).
- **Operator controls**: feature flags for retrieval tuning, web research, and RAG engine selection.

### Out of scope (by design)

- **General-purpose chat** without retrieval grounding (KB path always retrieves first).
- **Silent open-web answers** — web mode requires an explicit user toggle and shows a disclaimer.
- **Unbounded agent tool loops** — orchestration is a **fixed LangGraph** with optional bounded rewrite (Phase 6), not open-ended multi-agent autonomy.
- **Clinical or HIPAA-regulated use** — this codebase targets **education IT knowledge**; do not deploy against PHI without a separate compliance program.

### Success signals

| Signal | Mechanism |
|--------|-----------|
| Answer usefulness | User feedback on messages; qualitative review of traces |
| Grounding | Source panel + RAGAS **faithfulness** on golden set |
| Retrieval coverage | RAGAS **context_recall** vs curated `ground_truth` |
| Operability | CI green on mock RAG; Prometheus metrics; LangSmith per-node spans on graph path |

---

## Design goals

| Goal | How we approach it |
|------|-------------------|
| **Grounded answers** | Retrieval before generation; sources returned to the client and shown in the UI |
| **Operable in dev and prod** | Mock providers for local/CI; AWS/Azure paths for live KB; health and metrics endpoints |
| **Observable RAG** | LangSmith traces (per-node with LangGraph); RAGAS golden-set regression; Prometheus on the API |
| **Safe extension** | Explicit graph nodes and feature flags; opt-in web research with disclaimer; topic scoping via config |
| **Deployable incrementally** | Alembic migrations; `main` → `qa` → `release` CD; optional strict eval gates on release |

---

## Major decisions

### Dual RAG engines (`chain` vs `langgraph`)

| | `RAG_ENGINE=chain` | `RAG_ENGINE=langgraph` |
|---|-------------------|------------------------|
| **Implementation** | LangChain `ConversationalRetrievalChain` | Compiled graph in `backend/app/services/graph/` |
| **Streaming** | True token streaming via `astream_events` | Status event + paced chunks after `graph.invoke()` |
| **Observability** | Chain-level LangSmith runs | **Per-node** spans (condense, multi_query, retrieve, rerank, …) |
| **Retrieval tuning** | Chain retriever settings | Multi-query, metadata filters, rerank as **explicit nodes** |
| **Default in tests** | **Yes** (`conftest` forces `chain` so CI needs no AWS) | Local/live when configured in `.env` |

**Rationale:** The chain path preserves low-latency SSE and a simple mental model. LangGraph adds a testable orchestration layer and room for retrieval stages without growing a monolithic chain class. Both paths share the same provider registry and response shape so the API and UI stay engine-agnostic.

**Code:** `backend/app/services/rag.py`, `backend/app/services/graph/`.

---

### Bedrock Knowledge Base with OpenSearch (AWS)

**AWS stack:** **Bedrock Knowledge Base** (retrieve API) + **OpenSearch Serverless** (typical vector store behind the KB). The app uses `AmazonKnowledgeBasesRetriever`—not direct OpenSearch client calls.

```text
retrieve node → Bedrock KB API → OpenSearch Serverless index
```

| Piece | Responsibility |
|-------|----------------|
| **OpenSearch Serverless** | Chunk embeddings, vector/hybrid search, index storage |
| **Bedrock Knowledge Base** | Connectors, sync, retrieve orchestration, result metadata for citations |
| **This application** | `RETRIEVER_PROVIDER=aws`, `BEDROCK_KNOWLEDGE_BASE_ID`, optional Bedrock metadata filters |

**Azure stack:** **Azure AI Search** fills the same role (no OpenSearch)—`RETRIEVER_PROVIDER=azure`.

**Rationale:** v1 (upstream chabot) coupled the app to OpenSearch queries. v2 keeps OpenSearch in the platform architecture but uses the KB API so ingestion, index policies, and retrieve semantics stay managed by AWS—one retriever interface in the provider registry for both clouds.

**Code:** `backend/app/services/providers/retriever/aws.py`, `backend/app/services/retrieval.py` (metadata filters).

**Code (registry):** `backend/app/services/providers/` (AWS/Azure/mock).

---

### Provider registry (LLM + retriever)

`LLM_PROVIDER` and `RETRIEVER_PROVIDER` select `aws`, `azure`, or `mock` implementations. `RAG_FORCE_MOCK=true` forces mock for demos and CI.

**Rationale:** Same API and UI across environments; tox and new contributors run without cloud credentials. Explicit env vars beat implicit “whatever is in .env” for support and docs.

**Code:** `backend/app/services/providers/`, `backend/app/config/default.py`, `.env.example`.

---

### LangGraph KB path: multi-query → retrieve → rerank

```text
condense → multi_query → retrieve → rerank → generate → format
```

| Stage | Purpose |
|-------|---------|
| **condense** | Turn follow-up questions into a standalone retrieval query |
| **multi_query** | Expand queries; fuse results (RRF) for better recall |
| **retrieve** | Bedrock KB / Azure Search; optional metadata filters; fetch `RERANK_CANDIDATE_K` docs when reranking |
| **rerank** | FlashRank or keyword backend to trim noise before generation |
| **generate** | LLM answer grounded on selected chunks |
| **format** | Normalize metadata (`sources`, `source_kind`, markdown shape) |

**Rationale:** Recall and precision are tuned in retrieval, not only in the prompt. Each stage is flag-gated (`MULTI_QUERY_*`, `RERANK_*`, `METADATA_FILTER_*`) so operators can compare profiles (see [eval_baseline_2026-05-19.md](./eval_baseline_2026-05-19.md) and `./scripts/run_eval_phase5.sh`).

**Code:** `backend/app/services/graph/nodes.py`, `backend/app/services/retrieval.py`, `backend/app/services/rerank.py`.

Web path intentionally **skips rerank**: `condense → web_search → generate → format` ([WEB_RESEARCH.md](./roadmap/WEB_RESEARCH.md)).

---

### Opt-in web research

Web search is **per message** (`research_mode=web`), gated by `WEB_RESEARCH_ENABLED`, with a **disclaimer** in the UI and `source_kind=web` in metadata.

**Rationale:** Campus KB answers should default to governed corpus content. Open web is a deliberate user choice, not silent fallback when retrieval is weak.

**Code:** `backend/app/services/tools/web_search.py`, graph routing in `nodes.py`, Vue `ChatInput` / stores.

---

### Two evaluation layers (RAGAS + LangSmith)

| Tool | Role |
|------|------|
| **RAGAS** | Offline **quality metrics** on a fixed golden dataset (`backend/tests/eval/`); optional strict gates via `RAGAS_QUALITY_GATE` |
| **LangSmith** | Online **trace inspection** per session and per graph node |

**Rationale:** RAGAS answers “did we regress on known questions?” LangSmith answers “what happened on this slow or wrong turn?” CI runs unit tests with mock RAG; full RAGAS is slow and AWS-dependent, so it is optional locally and on `release` when configured ([EVALUATION.md](./EVALUATION.md)).

---

### API-port OAuth with SPA handoff

GitHub OAuth callback runs on the **API origin** (`OAUTH_REDIRECT_BASE_URL`, typically `:8000`), then redirects to Vue `/oauth/handoff` with a one-time code.

**Rationale:** OAuth `state` and cookies stay on one origin during the provider round-trip; avoids `state_mismatch` when the browser hits both Vite (`:5173`) and the API during login.

**Code:** `backend/app/api/auth/oauth_handoff.py` (or equivalent), [PRODUCTION_TLS.md](./PRODUCTION_TLS.md).

---

### Tenant-hydrated prompts

Per-tenant `tenant.rag_config` in Postgres can override topics, prompts, and related RAG settings.

**Rationale:** One deployment serving multiple logical tenants or campuses without separate builds. See [TENANT_CONFIG.md](./TENANT_CONFIG.md).

---

### History and performance guardrails

Chat history is capped (`CHAT_HISTORY_MAX_MESSAGES`) to bound prompt size and cost. Prometheus exposes pool and first-token style metrics ([PERFORMANCE.md](./PERFORMANCE.md)).

**Rationale:** Long sessions should not silently blow context windows or latency SLOs.

---

## Capability map (where to read more)

| Capability | Primary doc | Implementation |
|------------|-------------|----------------|
| Chat + SSE | [ARCHITECTURE.md](./ARCHITECTURE.md) | `backend/app/api/chat.py`, `frontend-vue/src/stores/chat.ts` |
| LangGraph pipeline | [LANGGRAPH.md](./roadmap/LANGGRAPH.md) | `backend/app/services/graph/` |
| Web research | [WEB_RESEARCH.md](./roadmap/WEB_RESEARCH.md) | `backend/app/services/tools/web_search.py` |
| Auth / OAuth | [PRODUCTION_TLS.md](./PRODUCTION_TLS.md) | `backend/app/api/auth/` |
| Evaluation | [EVALUATION.md](./EVALUATION.md) | `backend/tests/eval/`, `scripts/run_eval_phase5.sh` |
| CI/CD | [CI.md](./CI.md), [RELEASE.md](./RELEASE.md) | `.github/workflows/` |
| Operations | [OPERATIONS.md](./OPERATIONS.md) | Alembic, metrics, run scripts |
| Delivery phases | [roadmap/PRODUCT_ROADMAP.md](./roadmap/PRODUCT_ROADMAP.md) | Shipped vs optional work |

---

## Alternatives considered (short)

| Topic | Alternative | Why not (for this codebase) |
|-------|-------------|-------------------------------|
| Orchestration | Open-ended multi-agent (CrewAI, etc.) | Harder to test and observe; prefer explicit graph for production RAG |
| Retrieval | App-managed chunking + direct OpenSearch only | Bedrock KB + OpenSearch Serverless: managed sync and retrieve API; app avoids index client ops |
| Streaming | Only buffered responses | Chain path keeps true SSE; graph path trades TTFT for span clarity until Phase 6a |
| Web | Always-on web augmentation | Conflicts with KB trust model; opt-in + disclaimer is clearer |
| DB schema | `create_all` in production | Alembic-only in prod for repeatable deploys |

---

## Extension points (planned or optional)

Documented in [roadmap/PRODUCT_ROADMAP.md](./roadmap/PRODUCT_ROADMAP.md):

- **LangGraph-native SSE** — stream from `astream_events` instead of post-invoke chunking
- **Bounded rewrite loop** — `RAG_AGENTIC_ENABLED` (quality retry without open agents)
- **Campus scale** — Redis rate limits, HA, EB hardening ([archive/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/archive/PHASED_IMPROVEMENT_ROADMAP.md))

---

## Related

- [ARCHITECTURE.md](./ARCHITECTURE.md) — diagrams, API summary, frontend layout
- [docs/README.md](./README.md) — documentation index
- [changelog/CHANGELOG.md](../changelog/CHANGELOG.md) — what shipped when
