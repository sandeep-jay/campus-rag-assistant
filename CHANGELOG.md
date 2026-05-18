# Changelog

Notable changes to this **portfolio fork** of the UC Berkeley ETS Chabot platform
([multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot)).

[Keep a Changelog](https://keepachangelog.com/) format.  
Attribution and license: [README](README.md#license).

**Convention:** sections use **session dates** (when the work was done). GitHub PR merge
dates appear only in short **milestone** notes where that matters for the public repo story.

Edit **`[Unreleased]`** while you work. When a session is done, rename it to
`## [YYYY-MM-DD] — short title` and open a new `[Unreleased]`.

---

## [Unreleased]

### Changed

- Documentation: attribution under README License; removed `PORTFOLIO.md`, `EXECUTION_PLAN.md`, `DOC_AUDIT.md`; trimmed `ARCHITECTURE.md`.
- **CHANGELOG.md** only — session-based running log; `changelog/` gitignored.

### Removed

- `scripts/new-changelog.sh` and any tracked `changelog/` files.

---

## [2026-05-18] — tox and Vue in CI

*Merged to `main` as PR #9.*

### Added

- **tox** `frontend-vue` env: `npm ci`, typecheck, ESLint, Vitest (Node 20 via `.nvmrc`).
- **requirements.txt**: `langchain-openai`, Azure SDKs; `bcrypt>=4.0.1,<4.1.0` for passlib in tox.
- Lazy Azure provider imports in `backend/app/services/providers/__init__.py`.

### Changed

- **tox** `backend`: `RATE_LIMIT_ENABLED=false`, exclude `slow` (RAGAS) by default.
- **README** Testing: `tox -e lint,backend,frontend-streamlit,frontend-vue`.
- Ruff/pytest marker cleanups.

---

## [2026-05-17] — Portfolio publish (GitHub milestone)

*PRs #1–#8 merged to [multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot) `main`.*
*Implementation detail is in the **2026-05-01** sessions below.*

### Added

- Portfolio **README** and mock-first **`.env.example`**.
- **Docs** pack (architecture, operations, E2E, evaluation, roadmap, LangGraph design).
- **k6** load tests on `main` (`load-tests/`, seed script).

### Changed

- **`run_services.sh` / tox** → `frontend-streamlit/` after duplicate tree removed.
- **`main.py`**: `create_all` only in dev/test (PR #8 follow-up).
- **`requirements.txt`**: `alembic`, `redis` deps for deploy.

### Removed

- Duplicate **`frontend/`** directory (same as `frontend-streamlit/`).
- Root **`root-open-k6.js`**, empty root **`package-lock.json`**.

---

## [2026-05-01] — RAG platform, Vue, providers, eval

*Development session. Shipped on `main` via publish PRs; some items below were planned in notes but not merged.*

### Added — on `main`

- **Vue 3 SPA** (`frontend-vue/`): TypeScript, Vite, Pinia, Vue Router; chat, auth, sessions, sources, feedback, dark mode; Vitest (124 tests); Playwright e2e; MSW mocks.
- **Streamlit client** (`frontend-streamlit/`).
- **Provider registry** (`backend/app/services/providers/`): AWS / Azure / mock; wired in `rag.py`; `RAG_FORCE_MOCK`.
- **Redis rate limiter** (`backend/app/core/rate_limit.py`); fakeredis when `REDIS_URL` unset.
- **Prometheus metrics** (`backend/app/core/metrics.py`).
- **Dev routes** (`backend/app/core/dev_routes.py`).
- **Alembic** `0001_initial_schema.py`.
- **RAGAS eval** (`backend/tests/eval/`).
- **Scripts**: `run-backend-venv.sh`, `run-frontend-vue.sh`, `install-hooks.sh`.

### Added — session plan only (**not** on `main`)

- **`POST /api/chat/stream` (SSE)** and MSW stream handler — backend route not implemented.
- **FlashRank** reranking (`RERANK_*` in session `rag.py`) — not in current `rag.py`.
- Extra tox envs (`eval`, `backend-api`, `load-smoke`, …) — only partly adopted; use `pytest -m slow` for RAGAS.

### Changed

- **`rag.py`**, **`bedrock.py`**, **`chat.py`**, **`user` schemas**, **`.env.example`**, **`requirements.txt`**, **`ruff.toml`**, **`pyproject.toml`**.
- **`.ebextensions`**: health check proxies to FastAPI.

### Fixed

- `MessageBubble.vue` streaming `v-if` chain; test passwords; `rag.py` / RAGAS test lint issues; config tail restore.

### Security

- Password strength validation; generic chat 500s; shared rate limits when Redis configured.

### Performance

- Redis rate limit shared across Gunicorn workers.

### Follow-ups

- Real RAGAS golden Q&A; production `REDIS_URL`; `alembic upgrade head` on new DBs; LangGraph / SSE / rerank — [docs/roadmap/LANGGRAPH.md](docs/roadmap/LANGGRAPH.md).

---

## [2026-05-01] — Logging and request correlation

*Development session (same day as RAG/Vue work; separate focus).*

### Summary

One **request id** per HTTP request in logs and as **`X-Request-ID`**; optional **JSON** log lines; quieter **auth** logs (no JWT dumps at INFO).

### Added

- **`backend/app/core/request_context.py`**: middleware, `RequestIdFilter`, `normalize_request_id`.
- **`LOG_JSON`** + `JsonFormatter` in config/logger.
- **`backend/tests/core/test_request_context.py`**.
- **`scripts/kill-dev-servers.sh`** (ports 8000 / 5173).
- **`frontend-vue/src/api/interceptors.ts`**: `X-Request-ID` on API calls.

### Changed

- **`logger.py`**, **`main.py`** (middleware order, CORS expose header), **`security.py`** (DEBUG vs INFO policy), **`config` / `.env.example`**.

### Removed

- **`LOGGING_PROPAGATION_LEVEL`** (unused).

### Security

- No full JWT payload logging at INFO.

### Fixed

- Lint/format on logging paths; restored truncated `default.py` provider section.

---

## [Earlier] — Berkeley ETS Chabot baseline

Original Chabot for UC Berkeley ETS. © The Regents of the University of California — [LICENSE](LICENSE).
