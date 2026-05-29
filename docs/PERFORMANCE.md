# Performance and scale

Operational tuning for latency, throughput, and cost.

!!! info "Status — backlog tracker"
    This page is a **forward-looking backlog** for the **campus production-scale track**. Phase 0 items are shipped on `main`; Phases 1-3 are planned scope, not implementation status. For shipped retrieval and observability work, see [LANGGRAPH.md](./roadmap/LANGGRAPH.md), [OPERATIONS.md](./OPERATIONS.md), and the [product roadmap](./roadmap/PRODUCT_ROADMAP.md).

> **Phase numbering:** [PRODUCT_ROADMAP.md](./roadmap/PRODUCT_ROADMAP.md) tracks **product delivery** (RAG features on `main`). This doc and [archive/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/archive/PHASED_IMPROVEMENT_ROADMAP.md) describe a separate **campus production scale** track (Redis HA, caching, EB hardening). **Phase 5 (retrieval stack)** — multi-query, rerank — is **shipped** on `main`; see [LANGGRAPH.md](./roadmap/LANGGRAPH.md).

## Campus track Phase 0 — Shipped on `main`

| Change | Config / code | Docs |
|--------|----------------|------|
| Chat history window | `CHAT_HISTORY_MAX_MESSAGES` | [.env.example](../.env.example), [LOAD_TESTING.md](./LOAD_TESTING.md) |
| Optional stream demo delay | `STREAM_ARTIFICIAL_DELAY_MS` (default `0`) | `.env.example` |
| SQLAlchemy pool | `SQLALCHEMY_POOL_SIZE`, `SQLALCHEMY_MAX_OVERFLOW` | `.env.example`, [OPERATIONS.md](./OPERATIONS.md) |
| Multi-worker API (EB) | `API_WORKERS` in [run_services.sh](../run_services.sh) | [OPERATIONS.md](./OPERATIONS.md) |
| SSE first-token metric | `chatbot_chat_first_token_latency_seconds` | [OPERATIONS.md](./OPERATIONS.md) |

Runbooks: [OPERATIONS.md](./OPERATIONS.md). Load validation: [LOAD_TESTING.md](./LOAD_TESTING.md).

---

## Documentation checklist — Campus Phase 1 (not implemented)

**Goal:** exact Redis response cache, deeper observability, realistic k6 mix.

| Doc | Update when Phase 1 lands |
|-----|---------------------------|
| [.env.example](../.env.example) | `RESPONSE_CACHE_ENABLED`, `RESPONSE_CACHE_TTL_SECONDS`, `CACHE_BYPASS_HEADER` |
| [OPERATIONS.md](./OPERATIONS.md) | Cache hit rate metric, invalidation on KB deploy |
| [LOAD_TESTING.md](./LOAD_TESTING.md) | Mixed scenario; cache warm vs cold |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Optional cache layer in chat flow |
| [roadmap/archive/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/archive/PHASED_IMPROVEMENT_ROADMAP.md) | Mark 1a–1c complete |
| [EVALUATION.md](./EVALUATION.md) | Whether cached answers are excluded from RAGAS |

---

## Documentation checklist — Campus Phase 2 (partially superseded)

**Goal (campus track):** retrieval quality at scale.

**Phase 5** already shipped multi-query, metadata filters, and LangGraph **rerank** (FlashRank + keyword) on `main`. When implementing **remaining** campus Phase 2 items (e.g. semantic cache, ingestion pipeline), update:

| Doc | Update |
|-----|--------|
| [.env.example](../.env.example) | Any new cache / ingestion flags |
| [EVALUATION.md](./EVALUATION.md) | RAGAS comparison after changes |
| [roadmap/archive/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/archive/PHASED_IMPROVEMENT_ROADMAP.md) | Mark completed slices |
| [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) | New graph nodes if any |

---

## Documentation checklist — Campus Phase 3 (not implemented)

**Goal:** multi-instance reliability, idempotency, cost governance.

| Doc | Update when Phase 3 lands |
|-----|---------------------------|
| [.env.example](../.env.example) | Production `REDIS_URL`, idempotency TTL, budget caps |
| [OPERATIONS.md](./OPERATIONS.md) | Redis HA, idempotent chat retries |
| [RELEASE.md](./RELEASE.md) | Promote + cache flush notes |
| [LOAD_TESTING.md](./LOAD_TESTING.md) | Retry / duplicate POST scenarios |

---

## Related

- [OPERATIONS.md](./OPERATIONS.md)
- [LOAD_TESTING.md](./LOAD_TESTING.md)
- [RELEASE.md](./RELEASE.md)
