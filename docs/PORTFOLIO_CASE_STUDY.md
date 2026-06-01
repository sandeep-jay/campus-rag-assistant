# Portfolio Case Study: Campus RAG Assistant

## One-line summary

A source-reviewable AI platform case study: governed campus knowledge becomes cited answers, measurable retrieval quality, and a bounded helpdesk escalation flow.

## Problem

Campus support knowledge is fragmented across LMS guides, service desk articles, policy pages, and tribal memory. Users need answers they can verify, while platform owners need evidence that the system is observable, testable, and safe to run without turning every question into an open-web chatbot.

## My role

I owned the platform transformation represented in this repository: Vue product UI, FastAPI API, provider boundaries, LangGraph RAG orchestration, evaluation harness, LangSmith/Prometheus observability, CI/CD, and the bounded helpdesk escalation path.

The project builds from the public [`ets-berkeley-edu/chabot`](https://github.com/ets-berkeley-edu/chabot) codebase, which established the campus chatbot domain. This repository extends that base into a portfolio and educational architecture artifact. It is not an official UC Berkeley or UC product.

## Architecture

![High-level architecture](assets/architecture/v3/overview.png)

| Layer | What matters |
|-------|--------------|
| **Product UI** | Vue 3 SPA with sessions, streaming chat, cited source panels, feedback, OAuth handoff, Ask/Agent mode |
| **API** | FastAPI with SSE, JWT cookies, Alembic migrations, request IDs, Prometheus metrics |
| **RAG** | LangGraph KB path (`condense → multi_query → retrieve → rerank → generate → format`) plus chain path for true token streaming |
| **Providers** | AWS Bedrock KB, Azure AI Search/OpenAI, and mock mode behind the same interface |
| **Quality** | RAGAS golden set, release-oriented gates, LangSmith traces, k6 load profiles |
| **Helpdesk escalation** | Bounded workflow with KB retry, web search, duplicate issue search, HITL ticket filing, and four explicit outcomes |

Detailed diagrams and request flows: [ARCHITECTURE.md](./ARCHITECTURE.md). Design rationale: [DESIGN.md](./DESIGN.md).

## Measured outcomes

| Signal | Evidence |
|--------|----------|
| **Runs without cloud** | Mock providers and `RAG_FORCE_MOCK=true` let CI/local exercise the app without AWS or Azure credentials |
| **Retrieval work is measured** | 10-question RAGAS baseline; tuned AWS profile reaches **context_recall 0.80** |
| **Quality claims stay bounded** | RAGAS gates are release controls, not marketing claims; context precision remains explicitly named as the quality bottleneck |
| **Operational shape is visible** | GitHub Actions, gitleaks, dependency review, no tool attribution, Prometheus metrics, request IDs, k6 profiles |
| **Agentic scope is constrained** | Helpdesk escalation is HITL-gated; current supervisor is deterministic; LLM supervisor migration is documented separately |

Full score tables: [eval_baseline_v2.md](./eval_baseline_v2.md). Operations detail: [operations-manual/](./operations-manual/index.md).

## Key decisions

| Decision | Why it matters | Reference |
|----------|----------------|-----------|
| **Provider registry** | Keeps AWS, Azure, and mock execution modes behind the same app contract | [ADR-001](./adr/ADR-001-provider-registry.md) |
| **Dual RAG engines** | Preserves true streaming on the chain path while using LangGraph for staged retrieval tuning and traces | [ADR-002](./adr/ADR-002-langgraph-vs-chain.md) |
| **Opt-in web research** | Makes open-web answers a deliberate user choice, not a hidden fallback when KB retrieval is weak | [ADR-003](./adr/ADR-003-opt-in-web-research.md) |
| **RAGAS gates as release controls** | Keeps PR CI fast and cloud-free while preserving stricter milestone checks | [ADR-004](./adr/ADR-004-eval-gating-policy.md) |
| **Bedrock KB API over direct OpenSearch calls** | Lets AWS own ingestion, sync, and vector index lifecycle while the app owns retrieval contracts | [DESIGN.md](./DESIGN.md#bedrock-knowledge-base-with-opensearch-aws) |
| **Bounded helpdesk escalation** | Shows agentic product thinking without unbounded autonomy; side effects require human confirmation | [helpdesk/index.md](./helpdesk/index.md), [ADR-005](./adr/ADR-005-bounded-helpdesk-agent.md), [ADR-006](./adr/ADR-006-live-llm-supervisor-migration.md) |

## Known limits

- **Evaluation set is intentionally small** — useful as a regression baseline, not production proof.
- **Context precision is still the main RAG quality gap** — next levers are ingestion, chunking, and rerank tuning.
- **Graph path buffers output** — chain path has true token streaming; LangGraph-native SSE is a planned optional improvement.
- **Helpdesk supervisor is deterministic today** — the LLM supervisor, Postgres checkpointing, and trajectory eval are the [Agentic Helpdesk Rebuild](./roadmap/AGENTIC_HELPDESK_REBUILD.md) track.
- **License and deployment scope are bounded** — UC license retained; this is a portfolio/educational fork, not a commercial product claim.

## What this demonstrates

- **AI platform architecture:** provider boundaries, tenant configuration, mock/live parity, CI-safe local mode.
- **RAG engineering judgment:** explicit retrieval stages, citation contracts, eval baselines, and named quality gaps.
- **Product judgment:** KB-first UX, source transparency, opt-in web research, feedback loop, bounded escalation.
- **Production-readiness thinking:** runbooks, metrics, security review, load profiles, release process, hardening backlog.

## Related

- [README](../README.md) — repo landing page and quick review paths
- [Reviewer Guide](./REVIEWER_GUIDE.md) — 90-second signal map
- [Architecture](./ARCHITECTURE.md) and [Design Notes](./DESIGN.md) — system shape and tradeoffs
- [Operations Manual](./operations-manual/index.md) — runbooks, CI/CD, release, security, load testing
- [Release notes](./release-notes/index.md) — version-by-version history
