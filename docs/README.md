# Documentation index

See the root [README](../README.md) for setup, features, screenshots, and stack overview.

## Start here

| Audience | Start with |
|----------|------------|
| **New to the codebase** | [DESIGN.md](./DESIGN.md) → [ARCHITECTURE.md](./ARCHITECTURE.md) → [README#quick-start](../README.md#quick-start-mock-rag-no-cloud) |
| **RAG / LangGraph** | [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) → [EVALUATION.md](./EVALUATION.md) |
| **Ops / release** | [OPERATIONS.md](./OPERATIONS.md) → [CI.md](./CI.md) → [RELEASE.md](./RELEASE.md) |

## Design and architecture

| Doc | Description |
|-----|-------------|
| [DESIGN.md](./DESIGN.md) | **Design goals and decisions** — why chain vs LangGraph, retrieval stack, eval, OAuth, web mode |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Diagrams, request flows, API and frontend layout |
| [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) | Graph nodes, configuration, streaming behavior |
| [roadmap/WEB_RESEARCH.md](./roadmap/WEB_RESEARCH.md) | Opt-in `research_mode=web` |

## Screenshots and demos

| Resource | Description |
|----------|-------------|
| [assets/README.md](./assets/README.md) | Product, auth, and LangSmith screenshots + demo script |
| [README#overview](../README.md#overview) | Architecture, design, screenshots, and LangSmith (collapsible panels) |

## Architecture diagrams

| File | Where it appears |
|------|------------------|
| [architecture_v2.png](./assets/architecture_v2.png) | **Overview** — [README](../README.md#architecture) |
| [architecture_detailed_v2.png](./assets/architecture_detailed_v2.png) | **Detailed** — [ARCHITECTURE.md](./ARCHITECTURE.md#detailed-v2) |
| [architecture_v1.png](./assets/architecture_v1.png) | Upstream reference — [ARCHITECTURE.md](./ARCHITECTURE.md#upstream-reference-v1) |

## Quality and delivery

| Doc | Description |
|-----|-------------|
| [EVALUATION.md](./EVALUATION.md) | RAGAS vs LangSmith, bootstrap, CI gates |
| [eval_baseline_2026-05-19.md](./eval_baseline_2026-05-19.md) | RAGAS baseline scores (live AWS) |
| [roadmap/PRODUCT_ROADMAP.md](./roadmap/PRODUCT_ROADMAP.md) | Product phases — shipped vs optional |
| [../changelog/CHANGELOG.md](../changelog/CHANGELOG.md) | Release history |

## Operations and engineering

| Doc | Description |
|-----|-------------|
| [CI.md](./CI.md) | GitHub Actions CI/CD, secrets, branch gates |
| [RELEASE.md](./RELEASE.md) | `main` → `qa` → `release` promotion |
| [OPERATIONS.md](./OPERATIONS.md) | Runbooks, metrics, migrations |
| [PRODUCTION_TLS.md](./PRODUCTION_TLS.md) | HTTPS, OAuth (API-port + handoff) |
| [SECURITY.md](./SECURITY.md) | Dependency audit, production hardening |
| [PERFORMANCE.md](./PERFORMANCE.md) | Chat history caps and latency metrics |
| [LOAD_TESTING.md](./LOAD_TESTING.md) | k6 load tests |
| [TENANT_CONFIG.md](./TENANT_CONFIG.md) | Per-tenant `tenant.rag_config` |
| [E2E.md](./E2E.md) | Playwright E2E |
| [../frontend-vue/README.md](../frontend-vue/README.md) | Vue app setup |

## Archive

| Doc | Description |
|-----|-------------|
| [roadmap/archive/SPRINT_2026-05-18_LANGGRAPH.md](./roadmap/archive/SPRINT_2026-05-18_LANGGRAPH.md) | LangGraph live-validation sprint log |
| [roadmap/archive/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/archive/PHASED_IMPROVEMENT_ROADMAP.md) | Campus / production scale (optional track) |

Attribution and license: [README](../README.md#license).
