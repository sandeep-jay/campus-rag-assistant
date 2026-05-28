# Reviewer Guide

Campus RAG Assistant is a production-style enterprise RAG platform for governed campus knowledge. It is intended to be reviewed through source code, architecture, screenshots, evaluation results, and operational artifacts — not as a hosted public product.

## 90-second read

- Full-stack RAG platform built around governed institutional knowledge.
- Multicloud provider boundaries across **AWS Bedrock KB**, **Azure AI Search / OpenAI**, and mock CI/local providers.
- **Vue 3** product UI with sessions, streaming chat, cited sources, feedback, OAuth handoff, and opt-in web research.
- **LangGraph** orchestration, **RAGAS** evaluation baseline, **LangSmith** traces, Prometheus metrics, k6 load tests, CI/CD, and security docs.
- Mock providers allow local and CI execution without cloud credentials.
- Not presented as a hosted public product.

## Senior signals

| Signal | Evidence |
|---|---|
| AI platform architecture | Provider registry, AWS / Azure / mock separation, tenant config — [ADR-001](adr/ADR-001-provider-registry.md) |
| RAG engineering | LangGraph stages, multi-query retrieval, rerank hooks, explicit source contracts — [LangGraph roadmap](roadmap/LANGGRAPH.md) |
| Evaluation discipline | RAGAS golden set, documented baseline, release-oriented gates — [Evaluation](EVALUATION.md) |
| Observability | LangSmith traces, request IDs, Prometheus metrics — [Operations](OPERATIONS.md) |
| Product judgment | KB-first answers, opt-in web research, source transparency, feedback — [Web Research roadmap](roadmap/WEB_RESEARCH.md) |
| Production thinking | CI/CD, gitleaks, dependency review, no tool attribution, rate limits, load testing, hardening backlog — [CI/CD](CI.md), [Security](SECURITY.md), [Load Testing](LOAD_TESTING.md), [Production Hardening](PRODUCTION_HARDENING.md) |

## What this repository implements

This project builds from the public [`ets-berkeley-edu/chabot`](https://github.com/ets-berkeley-edu/chabot) codebase and extends it into a source-reviewable AI platform. Implemented surface:

- Vue 3 product UI (sessions, streaming, sources, feedback, OAuth handoff)
- Provider registry for AWS, Azure, and mock execution modes
- LangGraph RAG pipeline (`condense` → `multi_query` → `retrieve` → `rerank` → `generate` → `format`)
- Tenant-hydrated prompt and config model in Postgres
- RAGAS evaluation harness with documented baseline
- LangSmith trace capture for KB and web research paths
- Opt-in web research path with disclaimer UI and WEB-labeled sources
- CI/CD, gitleaks, dependency review, no tool attribution, k6 load testing, release docs, and a production hardening backlog

## Suggested review paths

| Reviewer | Start here |
|---|---|
| Hiring manager | [Case Study](PORTFOLIO_CASE_STUDY.md) |
| Staff / principal engineer | [Architecture](ARCHITECTURE.md), [Design Notes](DESIGN.md), [ADRs](adr/README.md) |
| AI engineer | [Evaluation](EVALUATION.md), [LangGraph roadmap](roadmap/LANGGRAPH.md), [Provider registry ADR](adr/ADR-001-provider-registry.md) |
| Platform / DevOps reviewer | [CI/CD](CI.md), [Operations](OPERATIONS.md), [Security](SECURITY.md), [Load Testing](LOAD_TESTING.md) |
| Product reviewer | [Screenshots](assets/README.md), [Case Study](PORTFOLIO_CASE_STUDY.md), [Product Roadmap](roadmap/PRODUCT_ROADMAP.md) |

## What this is not

- Not an official UC Berkeley or UC product.
- Not a public hosted SaaS product.
- Not a production deployment claim.
- Not a generic chatbot demo.
- Not a claim that the current evaluation set is production-sufficient.

See [Notice](notice.md) and [License](license.md) for attribution and licensing details.
