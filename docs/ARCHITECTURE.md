# Architecture

This repository is a **RAG chatbot** with a **FastAPI** backend and a **Vue 3** SPA (`frontend-vue/`).

## Backend

- **Entry**: [`backend/app/main.py`](../backend/app/main.py) builds the FastAPI app, runs SQLAlchemy `create_all`, configures CORS, and mounts routers under `/api/auth` and `/api/chat`.
- **Configuration**: Pydantic settings in [`backend/app/config/default.py`](../backend/app/config/default.py), loaded via [`backend/app/core/config_manager.py`](../backend/app/core/config_manager.py) from layered `.env` files (`APP_ENV`, repo root `.env`, `.env.{APP_ENV}`).
- **Auth**: JWT plus HTTP-only cookies (`/api/auth/login-json`, etc.). Cookie `Secure` and `SameSite` follow `AUTH_COOKIE_*` settings (see `.env.example`).
- **RAG**: [`backend/app/services/rag.py`](../backend/app/services/rag.py) builds a LangChain conversational retrieval chain. **One shared instance** is returned by `get_rag_service()` (thread-safe singleton) for all chat handlers.
- **Providers**: [`backend/app/services/providers/`](../backend/app/services/providers/) registers LLM and retriever implementations (`aws`, `azure`, `mock`) selected by `LLM_PROVIDER`, `RETRIEVER_PROVIDER`, optional `RAG_PROVIDER`, and `RAG_FORCE_MOCK`.

## Frontend (`frontend-vue/`)

- **Data flow**: Axios client (`src/api/`) → Pinia stores (`src/stores/`) → views/components. Cookies sent with `withCredentials`.
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


## Provider resilience

- RAG provider calls now run behind timeout and retry controls (`PROVIDER_*` settings).
- Circuit breaker protection opens after repeated failures and cools down automatically.
- Bulkhead limits cap concurrent provider calls per process to avoid cascading overload.
- API metadata marks degraded responses (`degraded_mode`, `degraded_reason`) when fallback paths are used.


## Security controls

- **Rate limiter**: `backend/app/core/rate_limit.py` provides pragmatic process-local windows for auth/chat endpoints. For multi-instance deployments, replace with Redis-backed coordination.
- **CSRF posture**: cookie-authenticated mutating routes enforce double-submit CSRF (`csrf_token` cookie + `X-CSRF-Token` header). Bearer-token requests are exempt.
- **Session lifecycle**: auth responses include explicit `expires_in`; `/api/auth/refresh` rotates cookie session access tokens without re-entering credentials.
