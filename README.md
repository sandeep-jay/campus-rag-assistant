# Multicloud RAG Chatbot

Portfolio continuation of the UC Berkeley ETS **Chabot** platform: a multi-tenant RAG chat API with swappable LLM/retriever providers (AWS Bedrock, Azure OpenAI, mock), a Vue 3 SPA, and a Streamlit client.

## Features

- **FastAPI** backend with JWT auth, chat sessions, feedback, and Prometheus metrics
- **Provider registry** — `LLM_PROVIDER` / `RETRIEVER_PROVIDER` (`mock` | `aws` | `azure`); `RAG_FORCE_MOCK` for zero-cloud local demos
- **Vue 3** frontend (`frontend-vue/`) — TypeScript, Pinia, Vitest, Playwright e2e
- **Streamlit** client (`frontend-streamlit/`) — same REST API
- **Alembic** migrations, **k6** load tests, **RAGAS** eval harness (`backend/tests/eval/`)

## Known gaps (roadmap)

- **`POST /api/chat/stream` (SSE)** — **not implemented on the backend.** Chat uses buffered **`POST /api/chat/chat`** (works with Azure/AWS/mock). The Vue app tries SSE first, then **falls back** to `/api/chat/chat`, so Azure tests succeed but responses are not token-streamed from the server.
- **LangGraph** — **not implemented** (design only: [docs/roadmap/LANGGRAPH.md](docs/roadmap/LANGGRAPH.md)). RAG today is the LangChain chain in `rag.py`.

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

From the repo root (recommended — matches CI):

```bash
tox -e lint,backend,frontend-streamlit,frontend-vue
```

Or run suites individually:

```bash
tox -e lint              # ruff (backend + Streamlit)
tox -e backend           # pytest; excludes slow RAGAS eval
tox -e frontend-streamlit
tox -e frontend-vue      # Node 20+; uses frontend-vue/.nvmrc via nvm when installed
```

Manual equivalents:

```bash
source venv/bin/activate
export PYTHONPATH=.
pytest backend/tests/ -m "not slow"
cd frontend-vue && npm ci && npm run ci
pytest frontend-streamlit/tests/
pytest backend/tests/eval/ -m slow   # optional; see docs/EVALUATION.md
```

Load tests: [docs/LOAD_TESTING.md](docs/LOAD_TESTING.md).

## Documentation

| Doc | Description |
|-----|-------------|
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System overview |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Runbooks, metrics, migrations |
| [docs/EVALUATION.md](docs/EVALUATION.md) | RAGAS quality gates |
| [docs/roadmap/PORTFOLIO_PHASED_ROADMAP.md](docs/roadmap/PORTFOLIO_PHASED_ROADMAP.md) | Roadmap (RAGAS, LangGraph, retrieval) |

## License

Software in this repository is licensed under the [Regents of the University of California](LICENSE) terms (educational/research use; commercial use requires an agreement with [UC OTL](http://ipira.berkeley.edu/industry-info)).

### Attribution

- **Original Chabot** — © The Regents of the University of California. Upstream: [ets-berkeley-edu/chabot](https://github.com/ets-berkeley-edu/chabot).
- **Author & maintainer** — [sandeep-jay](https://github.com/sandeep-jay) developed on the Berkeley ETS Chabot codebase and authored this **independent portfolio fork** (multicloud providers, Vue SPA, Alembic, tox/CI, eval harness, and related extensions). This repo is **not** an official or endorsed UC Berkeley product.
