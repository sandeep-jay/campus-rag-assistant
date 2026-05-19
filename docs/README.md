# Documentation index

See the root [README](../README.md) for setup and feature overview.

## Architecture diagrams

| File | Where it appears |
|------|------------------|
| [architecture_v2.png](./assets/architecture_v2.png) | **Overview** — [README](../README.md#architecture) |
| [architecture_detailed_v2.png](./assets/architecture_detailed_v2.png) | **Detailed** — [ARCHITECTURE.md](./ARCHITECTURE.md#detailed-v2) |
| [architecture_v1.png](./assets/architecture_v1.png) | Upstream reference — [ARCHITECTURE.md](./ARCHITECTURE.md#upstream-reference-v1) |

Narrative, chat/SSE flow, and API surface: [ARCHITECTURE.md](./ARCHITECTURE.md).

## Roadmap and quality

| Doc | Description |
|-----|-------------|
| [roadmap/TODAY_SPRINT.md](./roadmap/TODAY_SPRINT.md) | **Active sprint** — LangGraph + web research (same day) |
| [roadmap/PORTFOLIO_PHASED_ROADMAP.md](./roadmap/PORTFOLIO_PHASED_ROADMAP.md) | **Primary roadmap** — phases and deferrals |
| [EVALUATION.md](./EVALUATION.md) | RAGAS vs LangSmith; quality scorecard |
| [../changelog/CHANGELOG.md](../changelog/CHANGELOG.md) | Release history |
| [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) | LangGraph design |
| [roadmap/WEB_RESEARCH.md](./roadmap/WEB_RESEARCH.md) | Opt-in web research tool |

## Architecture and operations

| Doc | Description |
|-----|-------------|
| [RELEASE.md](./RELEASE.md) | `main` → `qa` → `release` promotion, tags, CI/CD branches |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, chat/SSE flow, API surface |
| [OPERATIONS.md](./OPERATIONS.md) | Runbooks, metrics, migrations |
| [PRODUCTION_TLS.md](./PRODUCTION_TLS.md) | HTTPS, OAuth callbacks, local `127.0.0.1` dev checklist |
| [LOAD_TESTING.md](./LOAD_TESTING.md) | k6 load tests |
| [TENANT_CONFIG.md](./TENANT_CONFIG.md) | Per-tenant RAG prompts (`tenant.rag_config`, env defaults) |
| [PERFORMANCE.md](./PERFORMANCE.md) | Phase 0 tuning + Phase 1–3 doc checklists |
| [E2E.md](./E2E.md) | Playwright E2E |

## Optional (campus / scale track)

| Doc | Description |
|-----|-------------|
| [roadmap/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/PHASED_IMPROVEMENT_ROADMAP.md) | Production scale — Redis HA, tenant budgets, EB |

Attribution and license: [README](../README.md#license).
