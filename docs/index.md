# Campus RAG Assistant

[![CI](https://github.com/sandeep-jay/campus-rag-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/sandeep-jay/campus-rag-assistant/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-UC%20Regents-orange.svg)](license.md)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://github.com/sandeep-jay/campus-rag-assistant/blob/main/pyproject.toml)
[![Node](https://img.shields.io/badge/node-20%2B-green.svg)](https://github.com/sandeep-jay/campus-rag-assistant/blob/main/frontend-vue/.nvmrc)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://github.com/sandeep-jay/campus-rag-assistant/blob/main/backend/app/main.py)
[![LangGraph](https://img.shields.io/badge/RAG-LangGraph-purple.svg)](roadmap/LANGGRAPH.md)
[![RAGAS](https://img.shields.io/badge/eval-RAGAS-yellow.svg)](EVALUATION.md)

**Production-style enterprise RAG platform** for governed campus knowledge.

This independent extension evolves an institutional chatbot into a multicloud AI platform: **AWS Bedrock KB**, **Azure AI Search**, **LangGraph** orchestration, cited answers, tenant-aware prompts, **RAGAS** evals, **LangSmith** traces, CI/CD, load testing, and a **Vue 3** product UI.

**Portfolio focus:** Lead AI Engineering and AI Platform Architecture.

**[View source on GitHub ->](https://github.com/sandeep-jay/campus-rag-assistant)**

![Structured KB answer with session history](assets/product/chat-assistant-response.png)

## Why this repo exists

Campus RAG Assistant demonstrates how governed institutional knowledge can become a measurable, observable RAG product instead of a generic chatbot. It surfaces:

- cited answers over campus knowledge bases users can verify
- provider boundaries across AWS, Azure, and mock CI/local modes
- explicit LangGraph retrieval stages for tuning and traceability
- RAGAS regression baselines and LangSmith traces for quality review
- production-shaped concerns: auth, streaming, migrations, metrics, CI/CD, security scanning, and runbooks

## What this shows

| Layer | What is demonstrated |
|-------|----------------------|
| **Product** | Governed KB-first chat, cited sources, opt-in web research, feedback loop, and campus-ready UX |
| **RAG engineering** | LangGraph retrieval stages, multi-query retrieval, rerank hooks, fallback chain streaming, and explicit source contracts |
| **Platform architecture** | AWS/Azure/mock provider registry, tenant config, feature flags, Alembic migrations, and CI-safe local mode |
| **Evaluation** | RAGAS golden-set regression harness, documented Phase 5 baseline, and LangSmith traces for KB/web paths |
| **Operations** | GitHub Actions, gitleaks, dependency review, Prometheus metrics, k6 load tests, release docs, and runbooks |

## Quality baseline

The project includes a **RAGAS golden-set harness** and a documented baseline. Phase 5 retrieval tuning improved AWS **context recall to 0.800**, passing the retrieval coverage gate. **Context precision** remains the main improvement target; next work focuses on ingestion/chunking and rerank tuning.

This is intentionally presented as an engineering baseline, not a marketing claim. Strict RAGAS gates are release controls, not blockers for local demo or ordinary PR CI.

Read more: [Evaluation approach](EVALUATION.md) and [baseline scores](eval_baseline_2026-05-19.md).

## Architecture

```mermaid
flowchart LR
  VueSPA["Vue 3 SPA"] --> FastAPI["FastAPI"]
  FastAPI --> LangGraph["LangGraph RAG"]
  LangGraph --> Providers["Provider Registry"]
  Providers --> BedrockKB["AWS Bedrock KB"]
  Providers --> AzureAI["Azure AI Search"]
  FastAPI --> Postgres[("Postgres")]
  FastAPI --> Prometheus["Prometheus"]
  LangGraph --> LangSmith["LangSmith"]
  LangGraph --> RAGAS["RAGAS eval"]
```

Design detail: [Architecture](ARCHITECTURE.md) and [Design Notes](DESIGN.md).

## Documentation

| Visitor | Best entry point |
|---------|------------------|
| New here | This page |
| Hiring / portfolio reviewer | [Case Study](PORTFOLIO_CASE_STUDY.md) |
| Architecture reviewer | [Architecture](ARCHITECTURE.md), [Design Notes](DESIGN.md), [ADRs](adr/README.md) |
| Evaluation reviewer | [Evaluation Approach](EVALUATION.md), [Evaluation Baseline](eval_baseline_2026-05-19.md) |
| Operations reviewer | [Operations](OPERATIONS.md), [CI/CD](CI.md), [Release](RELEASE.md), [Security](SECURITY.md) |
| Product demo reviewer | [Screenshots and demo script](assets/README.md) |
| Roadmap reviewer | [Product Roadmap](roadmap/PRODUCT_ROADMAP.md) |

## Screenshots

### Knowledge-base answer

![Structured KB answer with session history](assets/product/chat-assistant-response.png)

### Source transparency

![Source transparency — KB articles with scores](assets/product/chat-sources-kb.png)

### Opt-in web research

![Web mode answer with disclaimer banner](assets/product/chat-web-research-answer.png)

### LangSmith trace

![LangSmith trace — KB path](assets/observability/langsmith-trace-kb-waterfall.png)

More assets: [screenshots catalog](assets/README.md).

## Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | FastAPI, SQLAlchemy, Alembic, JWT auth, rate limiting, Prometheus metrics |
| **Frontend** | Vue 3, TypeScript, Pinia, Tailwind, Vitest, Playwright |
| **RAG orchestration** | LangGraph (`RAG_ENGINE=langgraph`) or LangChain `ConversationalRetrievalChain` (`RAG_ENGINE=chain`) |
| **Retrieval** | Bedrock KB / OpenSearch Serverless, Azure AI Search, multi-query + RRF, optional rerank |
| **LLM** | AWS Bedrock, Azure OpenAI, or mock provider |
| **Web search** | Mock or Tavily behind `research_mode=web` |
| **Eval** | RAGAS golden dataset, `tox -e eval`, LangSmith traces |
| **CI/CD** | GitHub Actions, tox, gitleaks, dependency review, optional EB deploy |

## Feature availability

| Configuration | What works |
|---------------|------------|
| **No cloud keys** (`RAG_FORCE_MOCK=true`) | Register/login, chat UX, streaming path, source panel, feedback, local tests |
| **AWS Bedrock KB** | Managed KB retrieval, Bedrock generation, LangGraph retrieval stages, LangSmith trace capture |
| **Azure OpenAI + AI Search** | Azure provider path with vector/keyword/hybrid retrieval and cited answers |
| **Web research enabled** | Per-message web mode with disclaimer UI and WEB-labeled sources (`mock` or Tavily) |
| **OAuth configured** | GitHub OAuth handoff to Vue; Google-ready provider config |
| **Eval keys available** | RAGAS golden-set runs, release quality gates, LangSmith trace inspection |

## Getting started

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set RAG_FORCE_MOCK=true, LLM_PROVIDER=mock, RETRIEVER_PROVIDER=mock
createdb chatbot_dev
alembic upgrade head
./scripts/run-backend-venv.sh          # http://127.0.0.1:8000
./scripts/run-frontend-vue.sh          # http://127.0.0.1:5173
```

Register a user and start a chat. Responses use the mock provider unless you configure live AWS/Azure providers.

## Demo readiness

| Area | Status |
|------|--------|
| Local mock demo | Implemented — clone, run backend/Vue, register, chat with cited mock sources |
| Live AWS KB path | Implemented — Bedrock KB retrieval, LangGraph stages, LangSmith traces, RAGAS baseline |
| Azure path | Implemented — Azure OpenAI + Azure AI Search provider path |
| Web research | Implemented — explicit per-message toggle, disclaimer banner, WEB-labeled sources |
| Hosted public demo | Deferred — local demo + screenshots are the review path |
| Official campus deployment | Intentionally not claimed — this is an independent extension, not a UC product |

## License

Software in this repository is licensed under the [Regents of the University of California](license.md) terms. See [Notice](notice.md) for attribution details. Commercial use requires an agreement with UC OTL.
