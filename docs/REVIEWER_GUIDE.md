# Reviewer Guide

Campus RAG Assistant is a source-reviewable AI platform for governed campus knowledge. It combines a
cited-answer RAG path with LangGraph agentic helpdesk orchestration: when the knowledge base cannot
resolve a question, the agent can retry retrieval, use controlled web research, search GitHub issues
for duplicates, draft a ticket, and file to GitHub only after human confirmation. The system runs
behind one FastAPI backend and Vue 3 SPA with AWS / Azure / mock providers, RAGAS evaluation,
LangSmith and Prometheus observability, CI/security gates, redaction, and HITL guardrails for
responsible AI.

Review it as an engineering artifact: source code, architecture, screenshots, evaluation results,
observability, CI/CD, security posture, and release hygiene. It is not presented as a hosted public
product.

## What this shows

| Capability | What it shows | Evidence |
|---|---|---|
| **Cited RAG path** | LangGraph retrieval stages, KB-first answers, multi-query retrieval, rerank hooks, source contracts, and opt-in web research | [DESIGN.md](DESIGN.md) · [EVALUATION.md](EVALUATION.md) · [ADR-001](adr/ADR-001-provider-registry.md) · [ADR-003](adr/ADR-003-opt-in-web-research.md) |
| **Agentic helpdesk orchestration** | Bounded LangGraph escalation with KB retry, web research, GitHub duplicate search, GitHub ticket drafting/filing, clarifying turns, redaction, HITL confirmation, and four explicit outcomes | [Helpdesk overview](helpdesk/index.md) · [ADR-005](adr/ADR-005-bounded-helpdesk-agent.md) · [ADR-006](adr/ADR-006-live-llm-supervisor-migration.md) |
| **AI platform architecture** | One FastAPI + Vue product surface over AWS / Azure / mock providers, tenant configuration, feature flags, migrations, and CI-safe local mode | [ARCHITECTURE.md](ARCHITECTURE.md) · [ADR-001](adr/ADR-001-provider-registry.md) |
| **Evaluation, observability, and responsible AI** | RAGAS baseline, LangSmith traces, Prometheus metrics, k6 load profiles, gitleaks, protected branches, redaction, and human approval before side effects | [eval_baseline_v2.md](eval_baseline_v2.md) · [operations-manual/index.md](operations-manual/index.md) · [ADR-004](adr/ADR-004-eval-gating-policy.md) |

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
