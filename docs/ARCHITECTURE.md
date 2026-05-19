# Architecture

**Campus RAG Assistant** is a retrieval-augmented chat product: a **FastAPI** backend, a **Vue 3** SPA (`frontend-vue/`), and an optional **Streamlit** client on the same REST API.

Evolution from upstream [ets-berkeley-edu/chabot](https://github.com/ets-berkeley-edu/chabot): dual frontends, pluggable **AWS / Azure / mock** providers, **Bedrock Knowledge Base** retrieval (replacing direct OpenSearch client calls), SSE streaming, JWT cookie auth, Alembic migrations, and Prometheus metrics.

## System architecture

Diagrams live in [`docs/assets/`](./assets/). The **v2 overview** is in the root [README](../README.md#architecture). Below: **detailed v2**, then **v1** (upstream [ets-berkeley-edu/chabot](https://github.com/ets-berkeley-edu/chabot)) for comparison.

### Detailed (v2)

![Campus RAG Assistant — detailed architecture](./assets/architecture_detailed_v2.png)

### Upstream reference (v1)

Original Berkeley ETS Chabot architecture (Streamlit-only UI, LangChain → OpenSearch + Bedrock directly):

![Upstream chabot architecture (v1)](./assets/architecture_v1.png)

### Diagram notes

| Area | Upstream chabot (v1) | Campus RAG Assistant (v2) |
|------|----------------------|---------------------------|
| **UI** | Streamlit only | **Vue 3 SPA** (primary); Streamlit optional, same API |
| **API** | Chat endpoints | **SSE** `POST /api/chat/stream`, sessions CRUD, feedback, sources |
| **Auth** | — | **JWT** in HTTP-only cookies (`/api/auth/*`) |
| **Retrieval (AWS)** | LangChain → **OpenSearch** directly | LangChain → **Bedrock Knowledge Base** (`AmazonKnowledgeBasesRetriever`); OpenSearch may back the KB in AWS but is not called from app code |
| **Retrieval (Azure)** | — | **Azure AI Search** hybrid + Azure OpenAI embeddings |
| **LLM** | Bedrock only | **Bedrock** or **Azure OpenAI** or **mock** via `LLM_PROVIDER` |
| **DB** | PostgreSQL | PostgreSQL + **Alembic** (no `create_all` in production) |
| **Ops** | LangSmith | LangSmith + **Prometheus** (`/api/metrics`, pool snapshot, first-token histogram); chat history capped via `CHAT_HISTORY_MAX_MESSAGES` — [PERFORMANCE.md](./PERFORMANCE.md) |
| **Quality** | — | **RAGAS** harness (`backend/tests/eval/`), k6 load tests |
| **Deploy** | EB + Nginx + Terraform | Same pattern; `run_services.sh` starts API (+ Streamlit on EB); Vue often hosted separately (CDN/static) with `FRONTEND_URL` / CORS |

| Asset | Description |
|-------|-------------|
| [`architecture_v2.png`](./assets/architecture_v2.png) | High-level overview — shown in [README](../README.md#architecture) |
| [`architecture_detailed_v2.png`](./assets/architecture_detailed_v2.png) | Current architecture with component detail |
| [`architecture_v1.png`](./assets/architecture_v1.png) | Upstream chabot (historical reference) |

## Chat request flow

```mermaid
sequenceDiagram
  participant UI as Vue SPA
  participant API as FastAPI /api/chat
  participant RAG as RAGService
  participant KB as Provider retriever

  UI->>API: POST /stream (SSE) or POST /chat
  API->>RAG: stream_query / query + history
  RAG->>KB: retrieve context
  KB-->>RAG: documents + metadata
  RAG-->>API: tokens + sources
  API-->>UI: SSE events or JSON message
  UI->>UI: normalize markdown, render + sources panel
```

- **Streaming (preferred):** `POST /api/chat/stream` emits Server-Sent Events (`token`, then `done` with sources). The Vue store appends tokens live, then persists the final message.
- **Buffered fallback:** `POST /api/chat/chat` returns the full assistant message when streaming fails or is disabled.
- **Sessions:** Messages belong to a `ChatSession` per user; history is passed into the LangChain conversational chain for follow-up questions.
- **Answer shape:** The model is instructed via `backend/app/templates/prompt_prefix.txt` to use a consistent Markdown template (summary → `##` sections → bold lead-ins → bullets / numbered steps). Backend and frontend apply **light sanitization only** (drop prompt leakage, optional `**Title**` → `## Title`); they do not rewrite structure with topic-specific heuristics.

## Backend

- **Entry**: [`backend/app/main.py`](../backend/app/main.py) builds the FastAPI app; runs SQLAlchemy `create_all` only in dev/test (production uses Alembic); configures CORS, and mounts routers under `/api/auth` and `/api/chat`.
- **Configuration**: Pydantic settings in [`backend/app/config/default.py`](../backend/app/config/default.py), loaded via [`backend/app/core/config_manager.py`](../backend/app/core/config_manager.py) from layered `.env` files (`APP_ENV`, repo root `.env`, `.env.{APP_ENV}`).
- **Auth**: JWT plus HTTP-only cookies (`/api/auth/login-json`, register, **OAuth** via `/api/auth/oauth/{provider}/…`). Cookie `Secure` and `SameSite` follow `AUTH_COOKIE_*` settings (see `.env.example`, [PRODUCTION_TLS.md](./PRODUCTION_TLS.md)).
- **RAG**: [`backend/app/services/rag.py`](../backend/app/services/rag.py) builds a LangChain conversational retrieval chain. - **LangGraph streaming:** When `RAG_ENGINE=langgraph`, `/api/chat/stream` emits a `status` event, runs the graph in a worker thread, then streams the buffered answer in paced chunks (not token-level Bedrock streaming). Use `RAG_ENGINE=chain` for `astream_events` TTFT.

Optional **LangGraph** runner under [`backend/app/services/graph/`](../backend/app/services/graph/) when `RAG_ENGINE=langgraph` (default `chain`). **One shared instance** is returned by `get_rag_service()` (thread-safe singleton) for all chat handlers.
- **Providers**: [`backend/app/services/providers/`](../backend/app/services/providers/) registers LLM and retriever implementations (`aws`, `azure`, `mock`) selected by `LLM_PROVIDER`, `RETRIEVER_PROVIDER`, optional `RAG_PROVIDER`, and `RAG_FORCE_MOCK`. When both `LLM_PROVIDER` and `RETRIEVER_PROVIDER` are set, they take precedence over `RAG_PROVIDER`.

### Chat API surface (summary)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/chat/stream` | SSE streaming reply |
| `POST /api/chat/chat` | Buffered reply |
| `GET/POST/DELETE /api/chat/sessions` | Conversation CRUD |
| `POST /api/chat/feedback` | Thumbs up/down |
| `GET /api/auth/oauth/{provider}/start` | OAuth redirect (e.g. `github`) |
| `GET /api/auth/oauth/{provider}/callback` | OAuth callback; sets session cookie |
| `GET /api/chat/messages/{id}/sources` | Source metadata for a message |

## Frontend (`frontend-vue/`)

- **Data flow**: Axios client (`src/api/`) → Pinia stores (`src/stores/`) → views/components. Cookies sent with `withCredentials`.
- **Chat UI**: `ChatView` + sidebar session list; `MessageBubble` (Markdown, user/assistant lanes, accessible accent); `SourcesPanel` / `SourcesSummary` below assistant replies; `MessageFeedback`; SSE streaming with typing/status indicator. Dev server: `http://127.0.0.1:5173`.
- **Routing**: Vue Router guards call `fetchCurrentUser` for protected routes.
- **Testing**: Vitest + MSW (`src/mocks/`) for unit/integration tests; Playwright under `e2e/` (see [E2E.md](./E2E.md)).

## Production-oriented behavior

When `ENVIRONMENT` is `production` or `prod` (configurable via `.env`):

- `ENABLE_DEV_API_ROUTES` defaults to **false** (hides `/api/auth/debug-auth`, `/api/chat/test_langsmith`).
- `ENABLE_OPENAPI_DOCS` defaults to **false** (no Swagger/ReDoc/OpenAPI JSON).
- `AUTH_COOKIE_SECURE` defaults to **true**.

Override any of these explicitly in `.env` when needed.

## CORS

- If `BACKEND_CORS_ORIGINS` is `*`, the app allows a fixed list of local origins plus `FRONTEND_URL`.
- For production, set `BACKEND_CORS_ORIGINS` to an explicit comma-separated list of allowed origins (see `.env.example`).

## Testing note

Integration tests mock RAG by patching **`backend.app.api.chat.get_rag_service`** (the name bound in the chat router module), not only `backend.app.services.rag.get_rag_service`, because the router imports that function by reference at load time.

## Rate limiting

- `backend/app/core/rate_limit.py` — process-local sliding windows on auth/chat (`RATE_LIMIT_ENABLED`). Use Redis-backed limits for multi-instance production.
