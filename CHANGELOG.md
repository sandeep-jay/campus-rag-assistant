# Changelog

Notable changes to this **portfolio fork** of the UC Berkeley ETS Chabot platform
([multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot)).

[Keep a Changelog](https://keepachangelog.com/) format.  
Attribution and license: [README](README.md#license).

Edit **`[Unreleased]`** as you work. When you merge a milestone, rename that section to
`## [YYYY-MM-DD] — short title` and start a new empty `[Unreleased]`.

---

## [Unreleased]

### Changed

- Documentation: attribution under README License; removed `PORTFOLIO.md`, `EXECUTION_PLAN.md`, `DOC_AUDIT.md`; trimmed `ARCHITECTURE.md`.
- **CHANGELOG.md** is the only project changelog (no separate `changelog/` tree on git).

### Removed

- `scripts/new-changelog.sh` and tracked files under `changelog/` (local `changelog/` remains gitignored for scratch).

---

## [2026-05-18] — Test harness (PR #9)

### Added

- **tox** `frontend-vue` env: `npm ci`, typecheck, ESLint, Vitest (Node 20 via `.nvmrc`).
- **requirements.txt**: `langchain-openai`, Azure SDKs; `bcrypt>=4.0.1,<4.1.0` pin for passlib in fresh tox envs.
- Lazy Azure provider imports in `backend/app/services/providers/__init__.py`.

### Changed

- **tox** `backend`: `RATE_LIMIT_ENABLED=false`, exclude `slow` (RAGAS) tests by default.
- **README** Testing: `tox -e lint,backend,frontend-streamlit,frontend-vue`.
- Ruff/pytest marker cleanups.

---

## [2026-05-17] — Portfolio publish on `main` (PRs #1–#8)

GitHub: [multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot).  
Below consolidates May 2026 development sessions (platform, Vue, logging, eval).

### Added — shipped on `main`

- **Vue 3 SPA** (`frontend-vue/`): TypeScript, Vite, Pinia, Vue Router; chat, auth, sessions, sources, feedback, dark mode; Vitest (124 tests); Playwright e2e scaffolding; MSW mocks; `frontend-vue/src/api/interceptors.ts` sends `X-Request-ID` per request.
- **Streamlit client** (`frontend-streamlit/`) — same REST API as Vue.
- **Provider registry** (`backend/app/services/providers/`): `BaseLlmProvider`, `BaseRetrieverProvider`, AWS/Azure/mock; `create_or_mock()`; wired in `rag.py`; `RAG_FORCE_MOCK`, `LLM_PROVIDER`, `RETRIEVER_PROVIDER`.
- **Redis-backed rate limiter** (`backend/app/core/rate_limit.py`): sliding window on Redis sorted sets; `fakeredis` when `REDIS_URL` unset.
- **Request context** (`backend/app/core/request_context.py`): `RequestContextMiddleware`, `RequestIdFilter`, contextvar; tests in `backend/tests/core/test_request_context.py`.
- **Prometheus metrics** (`backend/app/core/metrics.py`): middleware + `/api/metrics`.
- **Dev routes** (`backend/app/core/dev_routes.py`): non-production only.
- **Alembic** (`backend/alembic/`, `0001_initial_schema.py`): tenant, user, chat_session, chat_message, feedback.
- **RAGAS eval** (`backend/tests/eval/`, `golden_dataset.json`, `test_rag_quality.py`); gates via `RAGAS_QUALITY_GATE=1`; `slow` pytest marker.
- **k6 load tests** (`load-tests/`, seed script).
- **Logging**: `LOG_JSON` + `JsonFormatter`; `scripts/kill-dev-servers.sh` (ports 8000/5173).
- **Scripts / hooks**: `run-backend-venv.sh`, `run-frontend-vue.sh`, `install-hooks.sh`, load-test helpers.
- **Docs**: architecture, operations, E2E, evaluation, portfolio roadmap, LangGraph design.

### Added — described in session notes but **not** on `main`

- **`POST /api/chat/stream` (SSE)** — `StreamingResponse`, token/done events; MSW handler in Vue; **not implemented** on backend today.
- **FlashRank reranking** — `RERANK_ENABLED` / `_wrap_with_reranker` in session `rag.py`; **not** in current `rag.py`.
- **tox** `eval`, `backend-api`, `frontend-typecheck`, `load-smoke`, `load-stress` — partial; use `pytest backend/tests/eval/ -m slow` instead of `tox -e eval`.

### Changed — shipped

- **`rag.py`**: provider-based retriever/LLM (not Bedrock-only).
- **`bedrock.py`**: `_base_llm_kwargs()` helper.
- **`backend/app/api/chat.py`**: session helper refactor; generic 500 messages (no raw exception strings).
- **`backend/app/config/default.py`**: `REDIS_URL`, provider switches, `LOG_JSON`, logging format with `request_id`; removed unused `LOGGING_PROPAGATION_LEVEL`.
- **`backend/app/core/logger.py`**: idempotent setup, `RequestIdFilter`, no duplicate handlers on `app` logger.
- **`backend/app/main.py`**: `initialize_logger()` before/after app; `RequestContextMiddleware` after CORS; `expose_headers=['X-Request-ID']`; **`create_all` only in dev/test**.
- **`backend/app/core/security.py`**: JWT/token detail at DEBUG; INFO for auth outcomes only.
- **`backend/app/schemas/user.py`**: password strength (8+, upper, lower, digit); username validation.
- **`.env.example`**, **`.env.test`**, **README**: portfolio quick start, mock defaults.
- **`run_services.sh` / tox**: `frontend-streamlit/` after duplicate `frontend/` removed.
- **`.ebextensions/00_ami.config`**: `/api/health` proxies to FastAPI (not static 200).
- **`requirements.txt`**: `redis`, `fakeredis`, `ragas`, `langchain-openai`, `prometheus-client`, `alembic`, etc.
- **`pyproject.toml`**: merged duplicate pytest sections; `slow` marker.
- **`ruff.toml`**: `PLC0415`, per-file ignores extended.

### Fixed — shipped

- `MessageBubble.vue`: `v-if`/`v-else` chain for streaming UI state.
- Test passwords updated to `Testpassword1`; `test_register_weak_password_rejected`.
- `rag.py`: duplicate imports removed; provider ruff fixes.
- `test_rag_quality.py`: fixture/marker/annotation fixes.
- `backend/app/config/default.py`: restored truncated RAG/provider tail after edit accident.
- `tox -e lint`: security comment wrap, pytest fixture style, ruff format.

### Removed — shipped

- Duplicate **`frontend/`** tree (content lives in `frontend-streamlit/`).
- Root **`root-open-k6.js`**, empty root **`package-lock.json`**.

### Security — shipped

- Rate limits on auth/chat (shared across workers when `REDIS_URL` set).
- Password strength on registration.
- Auth logs no longer dump full JWT payloads at INFO.
- Generic 500s on chat errors.

### Performance — shipped

- Redis rate limiter shared across Gunicorn workers (vs per-process memory limits).

### Testing — snapshot at publish

- Backend pytest + Vue Vitest green; portfolio publish used incremental PRs #1–#8.

### Follow-ups (still open)

- Replace placeholder RAGAS golden dataset with real domain Q&A before strict CI gates.
- Set `REDIS_URL` for production multi-instance rate limits.
- Run `alembic upgrade head` on fresh databases.
- LangGraph, SSE, rerank: see [docs/roadmap/LANGGRAPH.md](docs/roadmap/LANGGRAPH.md) and README known gaps.

---

## [Earlier] — Berkeley ETS Chabot baseline

Original Chabot for UC Berkeley ETS. © The Regents of the University of California — [LICENSE](LICENSE).
