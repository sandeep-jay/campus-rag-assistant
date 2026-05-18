# Performance and scale

Operational tuning for latency, throughput, and cost. Roadmap phases align with [roadmap/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/PHASED_IMPROVEMENT_ROADMAP.md).

## Phase 0 — Shipped on `main`

| Change | Config / code | Docs |
|--------|----------------|------|
| Chat history window | `CHAT_HISTORY_MAX_MESSAGES` | [.env.example](../.env.example), [LOAD_TESTING.md](./LOAD_TESTING.md) |
| Optional stream demo delay | `STREAM_ARTIFICIAL_DELAY_MS` (default `0`) | `.env.example` |
| SQLAlchemy pool | `SQLALCHEMY_POOL_SIZE`, `SQLALCHEMY_MAX_OVERFLOW` | `.env.example`, [OPERATIONS.md](./OPERATIONS.md), [LOAD_TESTING.md](./LOAD_TESTING.md) |
| Multi-worker API (EB) | `API_WORKERS` / `UVICORN_WORKERS` in [run_services.sh](../run_services.sh) | [OPERATIONS.md](./OPERATIONS.md) |
| SSE first-token metric | `chatbot_chat_first_token_latency_seconds` | [OPERATIONS.md](./OPERATIONS.md) alerts |
| No fixed `sleep` on SSE tokens | — | This doc |

Runbooks: [OPERATIONS.md](./OPERATIONS.md) (SLOs split: auth/session vs live RAG). Load validation: [LOAD_TESTING.md](./LOAD_TESTING.md).

---

## Documentation checklist — Phase 1 (not yet implemented)

**Goal:** exact Redis response cache, deeper observability, realistic k6 mix.

| Doc | Update when Phase 1 lands |
|-----|---------------------------|
| [.env.example](../.env.example) | `RESPONSE_CACHE_ENABLED`, `RESPONSE_CACHE_TTL_SECONDS`, `CACHE_BYPASS_HEADER` (or equivalent) |
| [OPERATIONS.md](./OPERATIONS.md) | Cache hit rate metric, invalidation on KB deploy, bypass for support |
| [LOAD_TESTING.md](./LOAD_TESTING.md) | Mixed scenario (sessions + stream + feedback); note cache warm vs cold |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Optional cache layer in chat sequence / diagram notes |
| [roadmap/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/PHASED_IMPROVEMENT_ROADMAP.md) | Mark 1a–1c complete; link env names |
| [EVALUATION.md](./EVALUATION.md) | Whether cached answers are excluded from RAGAS runs |
| [changelog/CHANGELOG.md](../changelog/CHANGELOG.md) | Release notes |

**Code (for implementers):** `backend/app/services/response_cache.py` (or similar), wire in `chat.py` / `rag.py`, Prometheus `cache_hit` / `cache_miss` counters.

---

## Documentation checklist — Phase 2 (not yet implemented)

**Goal:** retrieval quality (multi-query, metadata filters, optional rerank) without regressing eval.

| Doc | Update when Phase 2 lands |
|-----|---------------------------|
| [.env.example](../.env.example) | `RERANK_ENABLED`, `RERANK_*`, multi-query / filter flags |
| [EVALUATION.md](./EVALUATION.md) | RAGAS gates with rerank on/off; baseline comparison |
| [roadmap/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/PHASED_IMPROVEMENT_ROADMAP.md) | 2a–2d status; **note:** FlashRank is roadmap-only until wired in `rag.py` |
| [roadmap/PORTFOLIO_PHASED_ROADMAP.md](./roadmap/PORTFOLIO_PHASED_ROADMAP.md) | Portfolio eval / LangGraph alignment |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Retrieval subgraph (expand, filter, rerank) |
| [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) | If nodes move to graph runner |
| [changelog/CHANGELOG.md](../changelog/CHANGELOG.md) | Release notes |

**Code:** `backend/app/services/rag.py`, retriever providers, `backend/tests/eval/`.

---

## Documentation checklist — Phase 3 (not yet implemented)

**Goal:** multi-instance reliability, idempotency, cost governance.

| Doc | Update when Phase 3 lands |
|-----|---------------------------|
| [.env.example](../.env.example) | Production `REDIS_URL` (TLS), idempotency TTL, budget caps |
| [OPERATIONS.md](./OPERATIONS.md) | ElastiCache / Redis HA, idempotent chat retries, connection budget math |
| [RELEASE.md](./RELEASE.md) | Promote + cache flush / migration notes |
| [LOAD_TESTING.md](./LOAD_TESTING.md) | Retry / duplicate POST scenarios |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Redis HA, horizontal workers, optional read path |
| [roadmap/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/PHASED_IMPROVEMENT_ROADMAP.md) | Phase 3–4 items |
| [docs/RELEASE.md](./RELEASE.md) | Deploy order if schema adds `client_message_id` |
| [changelog/CHANGELOG.md](../changelog/CHANGELOG.md) | Release notes |

**Code:** rate limit shared Redis (already), chat API schema, Alembic migration if idempotency keys are stored.

---

## Related

- [OPERATIONS.md](./OPERATIONS.md) — metrics, pools, alerts
- [LOAD_TESTING.md](./LOAD_TESTING.md) — k6 profiles
- [RELEASE.md](./RELEASE.md) — branch promotion
