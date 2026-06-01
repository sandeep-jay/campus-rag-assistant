# Releases

Campus RAG Assistant follows a `main` → `qa` → `release` promotion ladder with annotated tags and GitHub Releases on the `release` branch tip. See [RELEASE.md](../operations-manual/release.md) for the promotion process; [CHANGELOG.md](../../changelog/CHANGELOG.md) for fine-grained per-PR detail.

| Tag | Date | Highlights |
|---|---|---|
| [`v3.0.0`](#v300--helpdesk-agent--docs-refresh) | 2026-05-31 | Bounded helpdesk agent (backend + Vue), v3 architecture refresh, versioned assets |
| [`v2.0`](#v20--rag-platform-transformation) | 2026-05-19 | Vue SPA, multicloud providers, LangGraph RAG, RAGAS baseline, GitHub Actions CI/CD |
| [`v1.0`](#v10--upstream-chabot-baseline) | 2024 (upstream fork point) | Initial fork of UC Berkeley ETS chabot — Streamlit + FastAPI + LangChain |

GitHub Releases (with attached release notes and tagged commit): [`v1.0`](https://github.com/sandeep-jay/campus-rag-assistant/releases/tag/v1.0) · [`v2.0`](https://github.com/sandeep-jay/campus-rag-assistant/releases/tag/v2.0) · [`v3.0.0`](https://github.com/sandeep-jay/campus-rag-assistant/releases/tag/v3.0.0)

---

## v3.0.0 — Helpdesk agent + docs refresh

**Tag:** `v3.0.0` · **Date:** 2026-05-31

Ships the **bounded helpdesk agent** end-to-end (backend LangGraph + Vue Ask/Agent mode + HITL ticket filing) and refreshes all documentation with v3 architecture diagrams, agent UI screenshots, and versioned asset layout.

### Helpdesk agent (backend)

- **LangGraph agent endpoints** — `/api/helpdesk/agent/{start,resume,confirm,abort}` + SSE streams
- **Supervisor + specialists** — clarifier, classifier, writer, solution nodes with bounded tool budgets *(supervisor routing is deterministic in this release; LLM supervisor is the target — see [AGENTIC_HELPDESK_REBUILD.md](../roadmap/AGENTIC_HELPDESK_REBUILD.md))*
- **Agent tools** — KB retry, web search, GitHub-issue search, HITL-gated file-ticket
- **SQLite checkpointing** — multi-turn session persistence across clarifying questions
- **Durable chat persistence** — one assistant bubble per agent journey with activity trace
- **Observability** — `chatbot_helpdesk_agent_*` Prometheus metrics + LangSmith tracing

### Helpdesk agent (frontend)

- **Ask / Agent mode toggle** — independent chat modes with mode-specific input placeholders
- **Activity timeline** — multi-step agent trace rendered in a single assistant bubble
- **HITL flows** — radio/pill clarifying questions, outcome chips, ticket review modal with redaction warning
- **Design tokens v2** — rebuilt light/dark palettes, sidebar recency grouping, always-visible copy button

### Documentation & assets

- **v3 architecture diagrams** — overview, detailed, and full topology (RAG + agent subgraphs)
- **v3 product screenshots** — agent mode, HITL questions, ticket draft, GitHub Issues
- **Versioned asset layout** — `docs/assets/{architecture,product,auth}/{v1,v2,v3}/`
- **Agentic rebuild roadmap** — [AGENTIC_HELPDESK_REBUILD.md](../roadmap/AGENTIC_HELPDESK_REBUILD.md) for LLM-driven supervisor migration
- **Release notes** — high-level summaries for v1.0, v2.0, and v3.0.0 (this page)

### Security & hygiene

- Tool attribution guard workflow (PR #44)
- Frontend dev-tool CVE remediation (vite, esbuild, vitest upgrades)
- Python dependency bumps (authlib, langchain, streamlit)
- Pydantic settings tightening + env template CI guard
- CD workflow startup fix on `qa` / `release` (PR #49) — explicit permissions, `secrets: inherit` for reusable CI, locked Linux `lightningcss` optional natives

### Architecture

See [architecture/v3/overview.png](../assets/architecture/v3/overview.png), [detailed.png](../assets/architecture/v3/detailed.png), and [topology.png](../assets/architecture/v3/topology.png).

### Known limits

- Supervisor routing is **deterministic** (hand-coded), not yet LLM-driven — see [AGENTIC_HELPDESK_REBUILD.md](../roadmap/AGENTIC_HELPDESK_REBUILD.md)
- SQLite checkpointing (Postgres migration planned in Phase 1b of the rebuild)
- RAGAS context precision (~0.50) remains the main quality bottleneck

### What's next

[Agentic Helpdesk Rebuild](../roadmap/AGENTIC_HELPDESK_REBUILD.md) — phased migration to LLM supervisor + specialists, Postgres checkpointing, real-event SSE, trajectory eval, and live campus router.

---

## v2.0 — RAG platform transformation

**Tag:** `v2.0` · **Date:** 2026-05-19

Major platform evolution from the upstream chabot fork into **Campus RAG Assistant** — a production-style enterprise RAG platform with Vue product UI, multicloud provider boundaries, LangGraph orchestration, RAGAS evaluation, and GitHub Actions CI/CD.

### Product & UI

- **Vue 3 SPA** — streaming chat, session sidebar, source panels (Sources + Content tabs), feedback, OAuth handoff
- **Opt-in web research** — per-message toggle with visible disclaimer banner
- **GitHub OAuth** — dev OAuth on API port with one-time handoff to Vue

### RAG engineering

- **LangGraph pipeline** — condense → multi-query → retrieve → rerank → generate → format
- **Dual RAG engines** — `RAG_ENGINE=chain` (true SSE) and `langgraph` (observable stages)
- **Provider registry** — AWS Bedrock KB, Azure AI Search + OpenAI, mock mode for CI/local
- **Multi-query + RRF fusion** — improved retrieval coverage

### Platform & ops

- **Alembic migrations** — schema versioning for PostgreSQL
- **Prometheus metrics** — `/api/metrics`, request IDs, structured logging
- **GitHub Actions CI/CD** — tox (lint, backend, frontends) + gitleaks on every PR
- **MkDocs site** — GitHub Pages documentation

### Evaluation & quality

- **RAGAS golden-set harness** — 10-question regression baseline
- **Phase 5 retrieval tuning** — AWS context_recall improved to **0.80** (passes gate)
- **LangSmith traces** — per-node spans on LangGraph path; waterfall screenshots in README

### Documentation

- Architecture diagrams (v1/v2), screenshot gallery, ADRs (001–004), portfolio case study, reviewer guide

### Architecture

See [architecture/v2/overview.png](../assets/architecture/v2/overview.png) and [detailed.png](../assets/architecture/v2/detailed.png).

---

## v1.0 — Upstream chabot baseline

**Tags:** `v1.0` (release ladder), `v0.1` (historical fork tag — same commit) · **Date:** 2024 (upstream fork point)

Initial fork of the UC Berkeley ETS **chabot** campus chatbot — a Streamlit + FastAPI + LangChain stack querying OpenSearch and Bedrock directly. Kept as the baseline reference for v2's platform transformation.

### Highlights

- **Streamlit UI** — single-page chat against a campus knowledge base
- **FastAPI backend** — chat endpoints, PostgreSQL sessions
- **LangChain retrieval** — direct OpenSearch vector search + Bedrock LLM
- **AWS deployment** — Elastic Beanstalk + Nginx configs for co-hosting API and Streamlit
- **LangSmith** — basic trace integration

### Architecture

See [architecture/v1/architecture.png](../assets/architecture/v1/architecture.png) for the upstream diagram.
