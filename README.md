# Campus RAG Assistant

[![CI](https://github.com/sandeep-jay/campus-rag-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/sandeep-jay/campus-rag-assistant/actions/workflows/ci.yml)

Production-style **retrieval-augmented chat** over a campus knowledge base (Berkeley bCourses / ServiceNow KB on AWS Bedrock), with **tenant-hydrated** prompts (`tenant.rag_config` in Postgres). **FastAPI** backend, **Vue 3** SPA, pluggable **AWS / Azure / mock** providers, and a **LangGraph** RAG pipeline with evaluation and observability built in.

Ask questions in natural language; the app retrieves relevant docs, streams a cited answer, and keeps conversation history per user.

## Highlights

- **Full-stack** — Vue 3 + FastAPI + PostgreSQL (Alembic), JWT auth, GitHub OAuth, Prometheus metrics
- **LangGraph RAG** — `RAG_ENGINE=langgraph`: condense → multi-query → retrieve → rerank → generate (KB path); optional web branch
- **Retrieval quality** — multi-query fusion (RRF), metadata filters, FlashRank / keyword rerank
- **Opt-in web research** — per-message `research_mode=web`, disclaimer UI, optional Tavily
- **Eval discipline** — RAGAS golden set (10 rows), baseline scores, optional CI gates; LangSmith per-node traces
- **Portfolio-ready** — mock mode in <15 min; live AWS via `.env`; screenshots and demo script in [docs/assets/](docs/assets/README.md)

## Architecture

<p align="center">
  <img
    src="https://raw.githubusercontent.com/sandeep-jay/campus-rag-assistant/main/docs/assets/architecture_v2.png"
    alt="Campus RAG Assistant system architecture (v2)"
    width="900"
  />
</p>

<p align="center"><em>High-level v2 overview.</em> Detailed diagram and upstream v1: <a href="docs/ARCHITECTURE.md">docs/ARCHITECTURE.md</a></p>

## Features

### Knowledge-base chat (default)

- **RAG over Bedrock Knowledge Base** — retrieval + grounded generation with cited sources
- **LangGraph pipeline** — `condense` → `multi_query` → `retrieve` → `rerank` → `generate` → `format` when `RAG_ENGINE=langgraph`
- **Legacy chain path** — `RAG_ENGINE=chain` (default) for true Bedrock token streaming via LangChain
- **Scoped topics** — declines off-topic questions via `SUPPORTED_TOPICS` / `tenant.rag_config`
- **Structured markdown** — summary, `##` sections, bullets, numbered steps
- **Sources panel** — KB article chips, scores, expandable excerpt (Sources / Content tabs)

### Web research (opt-in)

- **Per-message toggle** — `research_mode=web` (Vue + API); not silent open-web mode
- **Disclaimer banner** on web answers; sources labeled **WEB**
- **Providers** — mock for demos; **Tavily** when `WEB_SEARCH_PROVIDER=tavily` and `WEB_RESEARCH_ENABLED=true`

### App and platform

- **SSE streaming** — `POST /api/chat/stream` with buffered fallback to `POST /api/chat/chat`
- **Sessions** — multi-turn history; sidebar to create, switch, and delete chats
- **Feedback** — thumbs up/down on assistant messages
- **Auth** — email/password or **GitHub OAuth** (Google-ready); JWT in HTTP-only cookies; local dev uses API-port OAuth + handoff to Vue ([docs/PRODUCTION_TLS.md](docs/PRODUCTION_TLS.md))
- **UI** — dark/light mode, mobile-friendly layout, copy answer
- **Ops** — rate limiting, `X-Request-ID`, Alembic migrations, optional Streamlit client on the same API

## Screenshots

<p align="center">
  <img src="docs/assets/product/chat-empty-state.png" alt="Campus RAG Assistant welcome screen" width="720" />
</p>
<p align="center"><em>Welcome screen with suggested campus prompts.</em></p>

<p align="center">
  <img src="docs/assets/product/chat-assistant-response.png" alt="Structured RAG answer with bCourses sources" width="720" />
</p>
<p align="center"><em>Knowledge-base answers with structured markdown and session history.</em></p>

<p align="center">
  <img src="docs/assets/product/chat-sources-kb.png" alt="Expandable KB source citations" width="520" />
</p>
<p align="center"><em>Source transparency — Berkeley ServiceNow KB articles with scores.</em></p>

<p align="center">
  <img src="docs/assets/product/chat-web-research-answer.png" alt="Web research mode with disclaimer" width="720" />
</p>
<p align="center"><em>Opt-in web research with an explicit disclaimer banner.</em></p>

**Demo script (~2–3 min):** [docs/assets/README.md#product-demo-script-23-min](docs/assets/README.md#product-demo-script-23-min).

## Stack

| Layer | Technologies |
|-------|----------------|
| **Backend** | FastAPI, SQLAlchemy, Alembic, JWT auth, rate limiting, Prometheus (`/api/metrics`) |
| **Frontend** | Vue 3, TypeScript, Pinia, Tailwind, Vitest, Playwright (`frontend-vue/`) |
| **RAG orchestration** | **LangGraph** (`RAG_ENGINE=langgraph`) or LangChain **ConversationalRetrievalChain** (`RAG_ENGINE=chain`) |
| **Retrieval** | AWS Bedrock Knowledge Base, Azure AI Search; multi-query + RRF; optional FlashRank / keyword rerank |
| **LLM** | AWS Bedrock, Azure OpenAI, or **mock** (`LLM_PROVIDER` / `RETRIEVER_PROVIDER`) |
| **Web search** | Mock or **Tavily** (`tavily-python`) behind `research_mode=web` |
| **Eval** | **RAGAS** harness (`backend/tests/eval/`), golden dataset, `tox -e eval` |
| **Observability** | **LangSmith** (`LANGCHAIN_TRACING_V2`), structured logs, first-token latency metric |
| **CI/CD** | GitHub Actions — `tox -e lint,backend,frontend-vue` on PRs and `main` ([docs/CI.md](docs/CI.md)) |
| **Load tests** | k6 ([docs/LOAD_TESTING.md](docs/LOAD_TESTING.md)) |

Local demos: `RAG_FORCE_MOCK=true` with no cloud credentials. Design detail: [docs/roadmap/LANGGRAPH.md](docs/roadmap/LANGGRAPH.md), [docs/roadmap/WEB_RESEARCH.md](docs/roadmap/WEB_RESEARCH.md).

## Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Node.js 20+ (Vue; see `frontend-vue/.nvmrc`)
- Optional: AWS Bedrock Knowledge Base or Azure OpenAI + AI Search

## Quick start (mock RAG, no cloud)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# RAG_FORCE_MOCK=true, LLM_PROVIDER=mock, RETRIEVER_PROVIDER=mock

createdb chatbot_dev   # or name from POSTGRES_DB in .env
alembic upgrade head

./scripts/run-backend-venv.sh          # terminal 1 — http://127.0.0.1:8000
cp frontend-vue/.env.example frontend-vue/.env.local
# VITE_API_URL=http://127.0.0.1:8000
# GitHub OAuth: VITE_OAUTH_API_URL=http://127.0.0.1:8000 — see docs/PRODUCTION_TLS.md
./scripts/run-frontend-vue.sh          # terminal 2 — http://127.0.0.1:5173
```

Register a user and start a chat. Responses use the mock provider.

**Streamlit (optional):**

```bash
source venv/bin/activate
export API_URL=http://127.0.0.1:8000
streamlit run frontend-streamlit/app/main.py
```

## Cloud-backed RAG

Set `RAG_FORCE_MOCK=false` and configure providers in `.env` (see [docs/OPERATIONS.md](docs/OPERATIONS.md)).

| Variable | Purpose |
|----------|---------|
| `RAG_ENGINE` | `chain` (default, true streaming) or `langgraph` (graph + per-node LangSmith spans) |
| `LLM_PROVIDER` | `aws` \| `azure` \| `mock` |
| `RETRIEVER_PROVIDER` | `aws` \| `azure` \| `mock` |
| `BEDROCK_KNOWLEDGE_BASE_ID` | AWS Knowledge Base |
| `RERANK_ENABLED`, `MULTI_QUERY_ENABLED` | Phase 5 retrieval tuning — see `.env.example` |
| `WEB_RESEARCH_ENABLED`, `WEB_SEARCH_PROVIDER` | Opt-in web mode (`mock` \| `tavily`) |
| Azure OpenAI / Search vars | Per `backend/app/config/` and `.env.example` |

**Tuned eval profile (live AWS):** `./scripts/run_eval_phase5.sh` — see [docs/eval_baseline_2026-05-19.md](docs/eval_baseline_2026-05-19.md).

## Testing

**CI:** GitHub Actions on push to `main` and on PRs ([`ci.yml`](.github/workflows/ci.yml)). CD on `qa` / `release`: [docs/CI.md](docs/CI.md), [docs/RELEASE.md](docs/RELEASE.md).

**CI-style suite (local):**

```bash
tox -e lint,backend,frontend-vue
```

**Optional suites:**

```bash
tox -e eval    # RAGAS golden-dataset eval (slow; judge LLM — docs/EVALUATION.md)
tox -e e2e     # Playwright; start API first: ./scripts/run-backend-venv.sh
tox -e lint,backend,frontend-streamlit,frontend-vue   # include Streamlit client
```

```bash
pytest backend/tests/ -m "not slow"
pytest backend/tests/eval/ -m slow
cd frontend-vue && npm run e2e
```

Load tests: [docs/LOAD_TESTING.md](docs/LOAD_TESTING.md).

## Quality and observability

Two complementary tools — see [docs/EVALUATION.md](docs/EVALUATION.md).

| Tool | Role |
|------|------|
| **RAGAS** | Regression **quality metrics** on a golden dataset (`backend/tests/eval/`) |
| **LangSmith** | **Traces** per chat turn and LangGraph node (`LANGCHAIN_TRACING_V2=true`) |

### RAGAS

```bash
tox -e eval
RAGAS_QUALITY_GATE=1 tox -e eval   # strict gates (release / local milestone)
```

Golden set (**10** rows), thresholds, bootstrap, and baseline scores: [docs/EVALUATION.md](docs/EVALUATION.md) and [docs/eval_baseline_2026-05-19.md](docs/eval_baseline_2026-05-19.md).

### LangSmith

Enable `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, and `LANGCHAIN_PROJECT` in `.env`; filter runs by `chat-session-<id>`. Per-node spans with `RAG_ENGINE=langgraph`.

![LangSmith trace — KB path](docs/assets/observability/langsmith-trace-kb-waterfall.png)

Web path: [langsmith-trace-web-waterfall.png](docs/assets/observability/langsmith-trace-web-waterfall.png). Capture steps: [EVALUATION.md — LangSmith](docs/EVALUATION.md#capture-a-trace-for-docs).

### Ops quick reference

| Item | Where |
|------|--------|
| Request correlation | `X-Request-ID` header (echoed on responses) |
| Metrics | `GET /api/metrics` (Prometheus) |
| Mock vs live RAG | `RAG_FORCE_MOCK`, `LLM_PROVIDER`, `RETRIEVER_PROVIDER` in `.env.example` |

## What's next

Optional follow-ups (not required for portfolio demo): **LangGraph-native SSE** (Phase 6a), stricter RAGAS gates after ingestion improvements, campus-scale ops (Redis HA, EB). Status: [docs/roadmap/PORTFOLIO_PHASED_ROADMAP.md](docs/roadmap/PORTFOLIO_PHASED_ROADMAP.md).

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, chat/SSE flow, API surface |
| [docs/assets/README.md](docs/assets/README.md) | Screenshots catalog + demo script |
| [docs/EVALUATION.md](docs/EVALUATION.md) | RAGAS vs LangSmith, bootstrap, CI gates |
| [docs/eval_baseline_2026-05-19.md](docs/eval_baseline_2026-05-19.md) | RAGAS baseline scores |
| [docs/roadmap/PORTFOLIO_PHASED_ROADMAP.md](docs/roadmap/PORTFOLIO_PHASED_ROADMAP.md) | Phases shipped vs optional |
| [docs/CI.md](docs/CI.md) | GitHub Actions, branch gates |
| [docs/PRODUCTION_TLS.md](docs/PRODUCTION_TLS.md) | HTTPS, OAuth (API-port + handoff) |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Runbooks, metrics, migrations |
| [changelog/CHANGELOG.md](changelog/CHANGELOG.md) | Release history |

## License

Software in this repository is licensed under the [Regents of the University of California](LICENSE) terms (educational/research use; commercial use requires an agreement with [UC OTL](http://ipira.berkeley.edu/industry-info)).

### Attribution

- **Original Chabot** — © The Regents of the University of California. Upstream: [ets-berkeley-edu/chabot](https://github.com/ets-berkeley-edu/chabot).
- **Author & maintainer** — [sandeep-jay](https://github.com/sandeep-jay) developed on the Berkeley ETS Chabot codebase and authored this **independent portfolio fork** (multicloud providers, Vue SPA, LangGraph, streaming chat, Alembic, tox/CI, RAGAS + LangSmith eval, and related extensions). This repo is **not** an official or endorsed UC Berkeley product.
