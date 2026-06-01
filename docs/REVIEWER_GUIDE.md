# Reviewer Guide

Campus RAG Assistant is a source-reviewable enterprise RAG platform for governed campus knowledge. Review it as an engineering artifact: code, architecture, screenshots, evaluation, operations, and release hygiene — not as a hosted public SaaS product.

## Senior signals

| Signal | Evidence |
|---|---|
| **AI platform architecture** | AWS Bedrock KB, Azure AI Search/OpenAI, and mock providers behind one registry — [ADR-001](adr/ADR-001-provider-registry.md) |
| **RAG engineering** | LangGraph retrieval stages, multi-query expansion, rerank hooks, explicit source metadata — [Design Notes](DESIGN.md#langgraph-kb-path-multi-query-retrieve-rerank) |
| **Evaluation discipline** | RAGAS golden set, documented baseline, release-oriented gates, named quality gaps — [Evaluation](EVALUATION.md), [Baseline](eval_baseline_v2.md) |
| **Product judgment** | KB-first answers, source panels, opt-in web research, visible disclaimer, feedback loop — [Opt-in web research](DESIGN.md#opt-in-web-research) |
| **Observability and operations** | LangSmith traces, Prometheus metrics, request IDs, k6 load profiles, runbooks — [Operations Manual](operations-manual/index.md) |
| **Security and release hygiene** | gitleaks, dependency review, no tool attribution, protected `main`, release ladder — [CI/CD](operations-manual/ci-cd.md), [Security](operations-manual/security.md) |
| **Bounded agentic work** | Helpdesk escalation with tools, HITL ticket filing, deterministic supervisor today, LLM supervisor migration documented — [Helpdesk overview](helpdesk/index.md), [ADR-006](adr/ADR-006-live-llm-supervisor-migration.md) |

## Suggested review paths

| Reviewer | Start here |
|---|---|
| Hiring manager | [Case Study](PORTFOLIO_CASE_STUDY.md) |
| Staff / principal engineer | [Architecture](ARCHITECTURE.md), [Design Notes](DESIGN.md), [ADRs](adr/README.md) |
| AI engineer | [Evaluation](EVALUATION.md), [LangGraph KB path](DESIGN.md#langgraph-kb-path-multi-query-retrieve-rerank), [Provider registry ADR](adr/ADR-001-provider-registry.md) |
| Platform / DevOps reviewer | [Operations Manual](operations-manual/index.md), [CI/CD](operations-manual/ci-cd.md), [Security](operations-manual/security.md) |
| Product reviewer | [Screenshots](assets/README.md), [Case Study](PORTFOLIO_CASE_STUDY.md), [Product Roadmap](roadmap/PRODUCT_ROADMAP.md) |
| Agent / orchestration reviewer | [Helpdesk overview](helpdesk/index.md), [Conversation Flow](roadmap/CONVERSATION_FLOW.md), [Engineering Spec](roadmap/HELPDESK_AGENT.md), [Agentic Rebuild plan](roadmap/AGENTIC_HELPDESK_REBUILD.md) |

## What this repository implements

- Vue 3 product UI with sessions, streaming chat, cited sources, feedback, OAuth handoff, Ask/Agent mode.
- FastAPI backend with JWT cookies, SSE endpoints, Alembic migrations, request IDs, Prometheus metrics.
- Provider registry for AWS, Azure, and mock execution modes.
- LangGraph RAG pipeline (`condense → multi_query → retrieve → rerank → generate → format`) plus chain path for true token streaming.
- Tenant-hydrated prompt and topic configuration in Postgres.
- RAGAS evaluation harness with a documented v2 retrieval baseline.
- LangSmith trace capture for KB and web-research paths.
- Opt-in web research with disclaimer UI and `source_kind=web` metadata.
- Helpdesk escalation: ASK-mode one-shot endpoints plus multi-turn AGENT-mode endpoints with HITL ticket filing.
- CI/CD, gitleaks, dependency review, no tool attribution guard, k6 load testing, release docs, and production hardening backlog.

## What this is not

- Not an official UC Berkeley or UC product.
- Not a public hosted SaaS product.
- Not a production deployment claim.
- Not a generic chatbot demo.
- Not a claim that the current evaluation set is production-sufficient.
- Not a claim that the current helpdesk supervisor is LLM-driven; that migration is tracked in [ADR-006](adr/ADR-006-live-llm-supervisor-migration.md).

See [Notice](notice.md) and [License](license.md) for attribution and licensing details.
