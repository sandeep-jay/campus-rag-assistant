# Campus RAG Assistant

Production-style **retrieval-augmented chat** over your knowledge base, with **tenant-hydrated** prompts (generic defaults; per-tenant `rag_config` in Postgres). **FastAPI** backend, **Vue 3** SPA, and pluggable **AWS / Azure / mock** LLM and retriever providers.

Ask questions in natural language; the app retrieves relevant docs, streams a cited answer, and keeps conversation history per user.

## Architecture

<p align="center">
  <img
    src="https://raw.githubusercontent.com/sandeep-jay/campus-rag-assistant/main/docs/assets/architecture_v2.png"
    alt="Campus RAG Assistant system architecture (v2)"
    width="900"
  />
</p>

<p align="center"><em>High-level v2 overview.</em> Detailed diagram and upstream v1: <a href="docs/ARCHITECTURE.md">docs/ARCHITECTURE.md</a></p>


## Chatbot features

- **RAG answers** — retrieval + generation from your KB (not open-web search)
- **Scoped topics** — declines off-topic questions using `SUPPORTED_TOPICS` / `tenant.rag_config`
- **Markdown replies** — summary, `##` sections, bullets, numbered steps
- **SSE streaming** — `POST /api/chat/stream` with fallback to `POST /api/chat/chat`
- **Sources** — KB chips and expandable excerpt panel per message
- **Sessions** — multi-turn history; sidebar to create, switch, and delete chats
- **Feedback** — thumbs up/down on assistant messages
- **Auth** — email/password or **GitHub OAuth** (Google-ready); JWT in HTTP-only cookies
- **UI** — streaming chat, copy answer, sources panel, dark/light mode, mobile-friendly layout

Optional **Streamlit** client (`frontend-streamlit/`) uses the same API.

## Stack

- **Backend:** FastAPI, SQLAlchemy, Alembic, JWT auth, rate limiting, Prometheus (`/api/metrics`)
- **Frontend:** Vue 3, TypeScript, Pinia, Tailwind, Vitest, Playwright (`frontend-vue/`)
- **RAG:** LangChain conversational chain in `backend/app/services/rag.py` (optional LangGraph scaffold via `RAG_ENGINE=langgraph`)
- **Providers:** `LLM_PROVIDER` / `RETRIEVER_PROVIDER` — `mock` | `aws` | `azure`; `RAG_FORCE_MOCK` for local demos
- **Eval:** RAGAS harness (`backend/tests/eval/`), k6 load tests

## Roadmap (in progress)

- **LangGraph + web research** — [today sprint](docs/roadmap/TODAY_SPRINT.md): `RAG_ENGINE=langgraph`, opt-in `research_mode=web`. Default remains LangChain until graph MVP ships.
- **RAGAS quality gates** — deferred until after graph; harness exists under `backend/tests/eval/`.

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
# For GitHub OAuth, use 127.0.0.1 (not localhost) in the browser — see docs/PRODUCTION_TLS.md
./scripts/run-frontend-vue.sh        # terminal 2 — http://127.0.0.1:5173
```

Register a user and start a chat. Responses use the mock provider.

**Streamlit (optional):**

```bash
source venv/bin/activate
export API_URL=http://localhost:8000
streamlit run frontend-streamlit/app/main.py
```

## Cloud-backed RAG

Set `RAG_FORCE_MOCK=false` and configure providers in `.env` (see [docs/OPERATIONS.md](docs/OPERATIONS.md)).

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `aws` \| `azure` \| `mock` |
| `RETRIEVER_PROVIDER` | `aws` \| `azure` \| `mock` |
| `BEDROCK_KNOWLEDGE_BASE_ID` | AWS Knowledge Base |
| Azure OpenAI / Search vars | Per `backend/app/config/` and `.env.example` |

When both `LLM_PROVIDER` and `RETRIEVER_PROVIDER` are set, they override `RAG_PROVIDER`.

## Testing

**Default CI-style suite** (lint + unit tests):

```bash
tox -e lint,backend,frontend-streamlit,frontend-vue
```

**Optional suites** (not in default `envlist`):

```bash
tox -e eval    # RAGAS golden-dataset eval (slow; needs ragas + judge LLM — see docs/EVALUATION.md)
tox -e e2e     # Playwright; start API first: ./scripts/run-backend-venv.sh
```

Manual equivalents:

```bash
pytest backend/tests/ -m "not slow"
pytest backend/tests/eval/ -m slow
cd frontend-vue && npm run e2e
```

Load tests: [docs/LOAD_TESTING.md](docs/LOAD_TESTING.md).

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/README.md](docs/README.md) | Index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System overview, diagrams ([v2](./docs/assets/architecture_v2.png)), chat/SSE flow |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Runbooks, metrics, migrations |
| [docs/EVALUATION.md](docs/EVALUATION.md) | RAGAS quality gates |
| [changelog/CHANGELOG.md](changelog/CHANGELOG.md) | Release history |

## License

Software in this repository is licensed under the [Regents of the University of California](LICENSE) terms (educational/research use; commercial use requires an agreement with [UC OTL](http://ipira.berkeley.edu/industry-info)).

### Attribution

- **Original Chabot** — © The Regents of the University of California. Upstream: [ets-berkeley-edu/chabot](https://github.com/ets-berkeley-edu/chabot).
- **Author & maintainer** — [sandeep-jay](https://github.com/sandeep-jay) developed on the Berkeley ETS Chabot codebase and authored this **independent portfolio fork** (multicloud providers, Vue SPA, streaming chat, Alembic, tox/CI, eval harness, and related extensions). This repo is **not** an official or endorsed UC Berkeley product.
