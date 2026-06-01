# Portfolio Case Study: Campus RAG Assistant

## One-line summary

A production-style RAG platform for governed institutional knowledge, built to demonstrate AI product engineering and platform architecture.

## Problem

Campus knowledge is scattered across LMS guides, ServiceNow articles, and policy documents. Staff and students need fast answers they can verify—not another generic chatbot that guesses from the open web.

## What changed in v3 (2026-05-31)

`v3.0.0` adds the **bounded helpdesk agent** end-to-end (backend LangGraph + Vue Ask/Agent mode + HITL ticket filing to a private GitHub demo repo), versioned architecture diagrams and product screenshots (`docs/assets/{architecture,product,auth}/{v1,v2,v3}/`), and the [Agentic Helpdesk Rebuild](./roadmap/AGENTIC_HELPDESK_REBUILD.md) roadmap that migrates the deterministic supervisor to a real LLM supervisor with structured-output specialists, `AsyncPostgresSaver`, enforced budgets, real-event SSE, trajectory eval, and a live campus router. Row-by-row shipped-vs-target reference: [helpdesk/index.md](./helpdesk/index.md#today-vs-target-state). Decision records: [ADR-005](./adr/ADR-005-bounded-helpdesk-agent.md) (original commitment) and [ADR-006](./adr/ADR-006-live-llm-supervisor-migration.md) (LLM supervisor migration). Full release-by-release summary: [release-notes/](./release-notes/index.md).

## My role

I owned the platform transformation work represented in this repository: the Vue product UI, provider registry, AWS / Azure / mock execution modes, LangGraph orchestration, RAGAS evaluation harness, LangSmith observability, CI/CD, load testing, and operational documentation.

The project builds from the public [`ets-berkeley-edu/chabot`](https://github.com/ets-berkeley-edu/chabot) codebase, which established the campus chatbot domain. This repository extends that base into a source-reviewable AI platform architecture artifact for portfolio and educational review. It is not an official UC Berkeley or UC product.

## Architecture

![High-level architecture](assets/architecture/v3/overview.png)

| Layer | Components |
|-------|------------|
| **UI** | Vue 3 SPA (primary); optional Streamlit on the same API |
| **API** | FastAPI — SSE streaming, sessions, feedback, JWT/OAuth |
| **RAG** | LangGraph (`condense` → `multi_query` → `retrieve` → `rerank` → `generate`) or LangChain chain (true token streaming) |
| **Providers** | AWS Bedrock KB, Azure AI Search + OpenAI, mock (CI/local) |
| **Data** | PostgreSQL + Alembic; per-tenant `rag_config` |
| **Quality** | RAGAS golden set, LangSmith traces, Prometheus, k6 |
| **Helpdesk agent** | LangGraph supervisor + tools (KB retry, web search, GitHub-issue search), SQLite checkpoint, HITL ticket filing to a private demo repo |

Detailed diagrams and request flows: [ARCHITECTURE.md](./ARCHITECTURE.md).

## Key decisions

| Decision | Rationale | ADR |
|----------|-----------|-----|
| **Provider registry** (AWS / Azure / mock) | Same API and UI across environments; CI runs without cloud credentials | [ADR-001](./adr/ADR-001-provider-registry.md) |
| **Dual RAG engines** (`chain` vs `langgraph`) | Chain preserves true SSE; LangGraph adds observable stages and retrieval tuning | [ADR-002](./adr/ADR-002-langgraph-vs-chain.md) |
| **Opt-in web research** | Governed KB-first; open web is explicit per message with disclaimer | [ADR-003](./adr/ADR-003-opt-in-web-research.md) |
| **RAGAS gates as release controls** | Honest baselines on PR CI; strict gates on release milestones only | [ADR-004](./adr/ADR-004-eval-gating-policy.md) |
| **Bedrock KB API** (not direct OpenSearch) | Managed sync, retrieve, and citation metadata; simpler ops | [DESIGN.md](./DESIGN.md#bedrock-knowledge-base-with-opensearch-aws) |
| **Bounded helpdesk agent** | Real agentic loop (LLM-chosen tools, multi-turn checkpointing, HITL gate) without unbounded autonomy; original one-shot endpoints kept as fallbacks | [ADR-005](./adr/ADR-005-bounded-helpdesk-agent.md) + [ADR-006](./adr/ADR-006-live-llm-supervisor-migration.md), [HELPDESK_AGENT.md](./roadmap/HELPDESK_AGENT.md) |

## Measured outcomes

| Signal | Evidence |
|--------|----------|
| **Test breadth** | ~48 backend, frontend, e2e, and eval test files; `tox (lint, backend, frontends)` on every PR |
| **RAGAS baseline** | 10-question golden set; AWS Phase 5 tuned profile: **context_recall 0.80** (passes gate) |
| **CI without cloud** | Mock providers; `RAG_FORCE_MOCK=true`; no AWS credentials in GitHub Actions |
| **Load profile** | k6 validates auth, session CRUD, and chat under load — [LOAD_TESTING.md](./LOAD_TESTING.md) |
| **Observability** | LangSmith per-node spans on LangGraph path; Prometheus `/api/metrics` |
| **Helpdesk agent eval** | Scenario rig (`backend/tests/eval/test_helpdesk_agent_scenarios.py`) asserts mock-conversation -> expected `next_action`; `chatbot_helpdesk_agent_*` Prometheus metrics surface outcome distribution and tool usage |

Full score tables: [eval_baseline_2026-05-19.md](./eval_baseline_2026-05-19.md).

## Known limits

- **Eval set is small** (10 rows) and corpus-specific—good for regression baseline, not production quality claims.
- **Context precision** (~0.50) is the main quality bottleneck; next levers are ingestion/chunking and rerank tuning.
- **LangGraph path** buffers output into paced SSE chunks rather than true token streaming (Phase 6a optional).
- **UC license** limits commercial reuse; treat as portfolio/educational fork, not a drop-in commercial product.

## What this demonstrates

- **Lead AI engineering** — retrieval tuning, orchestration, citations, eval discipline, failure-mode thinking
- **AI platform architecture** — multicloud abstraction, tenant config, mock/live environments, CI/CD
- **Product judgment** — opt-in web research, topic scoping, source transparency, feedback loop
- **Evaluation discipline** — RAGAS + LangSmith as complementary tools; honest baselines
- **Production-readiness thinking** — metrics, rate limits, migrations, security notes, hardening backlog

## Related

- [README](../README.md) — quick start and portfolio highlights
- [release-notes/](./release-notes/index.md) — what shipped in v1.0 / v2.0 / v3.0.0
- [DESIGN.md](./DESIGN.md) — goals, boundaries, tradeoffs
- [PRODUCTION_HARDENING.md](./PRODUCTION_HARDENING.md) — scale and ops backlog
- [docs/adr/](./adr/) — architecture decision records (incl. ADR-006 for the agentic rebuild)
