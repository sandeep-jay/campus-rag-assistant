# Documentation index

See the root [README](../README.md) for setup and feature overview.

## Screenshots and demos

| Resource | Description |
|----------|-------------|
| [assets/README.md](./assets/README.md) | Product, auth, and LangSmith screenshots + demo script |
| [README#screenshots](../README.md#screenshots) | Gallery embedded in repo README |

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
| [roadmap/PORTFOLIO_PHASED_ROADMAP.md](./roadmap/PORTFOLIO_PHASED_ROADMAP.md) | **Primary roadmap** — phases, priorities, dev commands |
| [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) | LangGraph design, flags, latency |
| [roadmap/WEB_RESEARCH.md](./roadmap/WEB_RESEARCH.md) | Opt-in web research |
| [roadmap/archive/](./roadmap/archive/) | Completed sprint + campus scale track |
| [eval_baseline_2026-05-19.md](./eval_baseline_2026-05-19.md) | RAGAS bootstrap baseline |
| [EVALUATION.md](./EVALUATION.md) | RAGAS vs LangSmith |
| [../changelog/CHANGELOG.md](../changelog/CHANGELOG.md) | Release history |

## Architecture and operations

| Doc | Description |
|-----|-------------|
| [CI.md](./CI.md) | GitHub Actions CI/CD, secrets, branch gates |
| [RELEASE.md](./RELEASE.md) | `main` → `qa` → `release` promotion, tags, CI/CD branches |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, chat/SSE flow, API surface |
| [OPERATIONS.md](./OPERATIONS.md) | Runbooks, metrics, migrations |
| [PRODUCTION_TLS.md](./PRODUCTION_TLS.md) | HTTPS, OAuth (API-port + handoff), local dev checklist |
| [LOAD_TESTING.md](./LOAD_TESTING.md) | k6 load tests |
| [TENANT_CONFIG.md](./TENANT_CONFIG.md) | Per-tenant RAG prompts (`tenant.rag_config`, env defaults) |
| [SECURITY.md](./SECURITY.md) | Dependency audit, bandit, production hardening |
| [PERFORMANCE.md](./PERFORMANCE.md) | Campus perf track (Phase 0 shipped; checklists for cache/scale) |
| [E2E.md](./E2E.md) | Playwright E2E |
| [../frontend-vue/README.md](../frontend-vue/README.md) | Vue app setup |

Attribution and license: [README](../README.md#license).
