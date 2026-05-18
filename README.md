# Multicloud RAG Chatbot

Portfolio continuation of the UC Berkeley ETS **Chabot** platform: a multi-tenant RAG chat API with swappable LLM/retriever providers (AWS Bedrock, Azure OpenAI, mock), a Vue 3 SPA, and a Streamlit client.

> **Attribution:** Original Chabot software and documentation are © The Regents of the University of California. See [LICENSE](LICENSE). This repository is an **independent portfolio project** by [sandeep-jay](https://github.com/sandeep-jay) and is not an official or endorsed UC Berkeley product. Upstream: [ets-berkeley-edu/chabot](https://github.com/ets-berkeley-edu/chabot).

## Features

- **FastAPI** backend with JWT auth, chat sessions, feedback, and Prometheus metrics
- **Provider registry** — `LLM_PROVIDER` / `RETRIEVER_PROVIDER` (`mock` | `aws` | `azure`); `RAG_FORCE_MOCK` for zero-cloud local demos
- **Vue 3** frontend (`frontend-vue/`) — TypeScript, Pinia, Vitest, Playwright e2e
- **Streamlit** client (`frontend-streamlit/`) — same REST API
- **Alembic** migrations, **k6** load tests, **RAGAS** eval harness (`backend/tests/eval/`)

## Known gaps (roadmap)

- **`POST /api/chat/stream` (SSE)** — not implemented; chat is buffered JSON only. Vue may fake-stream in the UI; see [docs/roadmap/LANGGRAPH.md](docs/roadmap/LANGGRAPH.md) and [docs/DOC_AUDIT.md](docs/DOC_AUDIT.md).
- **LangGraph** orchestration — designed, not merged (see roadmap).

## Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Node.js 20+ (Vue frontend; see `frontend-vue/.nvmrc`)
- Optional: AWS Bedrock or Azure OpenAI for non-mock RAG

## Quick start (mock RAG, no cloud)

Runs the API and UI without Bedrock/Azure credentials.

```bash
# 1. Virtualenv and dependencies
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Environment — copy and set mock-friendly values
cp .env.example .env
# In .env (or export):
#   RAG_FORCE_MOCK=true
#   LLM_PROVIDER=mock
#   RETRIEVER_PROVIDER=mock

# 3. Database (adjust user/db names to match .env)
createuser chatbot --no-createdb --no-superuser --no-createrole --pwprompt  # if needed
createdb chatbot_dev   # or name from POSTGRES_DB in .env
alembic upgrade head

# 4. Git hooks (optional, strips Cursor co-author trailers)
./scripts/install-hooks.sh

# 5. Backend (terminal 1)
./scripts/run-backend-venv.sh

# 6. Vue frontend (terminal 2)
cp frontend-vue/.env.example frontend-vue/.env.local
# Set VITE_API_URL=http://localhost:8000
./scripts/run-frontend-vue.sh
```

Open http://localhost:5173 — register a user, start a chat; responses use the **mock RAG** path.

### Streamlit (optional)

```bash
source venv/bin/activate
export API_URL=http://localhost:8000
streamlit run frontend-streamlit/app/main.py
```

## Cloud-backed RAG

Configure real providers in `.env` (see [docs/OPERATIONS.md](docs/OPERATIONS.md)):

| Variable | Purpose |
|----------|---------|
| `RAG_FORCE_MOCK=false` | Allow real providers |
| `LLM_PROVIDER` | `aws` or `azure` |
| `RETRIEVER_PROVIDER` | `aws` or `azure` |
| `BEDROCK_KNOWLEDGE_BASE_ID` | AWS KB (not a placeholder) |
| Azure OpenAI / Search vars | Per `backend/app/config/` |

## Testing

```bash
source venv/bin/activate
export PYTHONPATH=.

# Backend
pytest backend/tests/

# Vue unit tests
cd frontend-vue && npm ci && npm test

# Streamlit
pytest frontend-streamlit/tests/

# RAGAS eval (slow; needs judge LLM — see docs/EVALUATION.md)
pytest backend/tests/eval/ -m slow

# Lint (repo root)
tox -e lint
```

Load tests: [docs/LOAD_TESTING.md](docs/LOAD_TESTING.md).

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System overview |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Runbooks, metrics, migrations |
| [docs/EVALUATION.md](docs/EVALUATION.md) | RAGAS quality gates |
| [docs/PORTFOLIO.md](docs/PORTFOLIO.md) | Publishing this repo |
| [docs/EXECUTION_PLAN.md](docs/EXECUTION_PLAN.md) | Commit/PR history map |

## License

Regents of the University of California — see [LICENSE](LICENSE). Use for educational and research purposes per license terms; commercial use requires UC OTL agreement.
