# Changelog

Notable changes to this **portfolio fork** of the UC Berkeley ETS Chabot platform
([multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot)).

Format: [Keep a Changelog](https://keepachangelog.com/).  
Attribution and license: [README](README.md#license).

**Running log:** edit `[Unreleased]` below. When you merge a milestone, rename it to `## [YYYY-MM-DD] — title` and open a new `[Unreleased]`.

**Detailed session history:** [changelog/archive/](changelog/archive/) (frozen notes). Policy: [changelog/README.md](changelog/README.md).

---

## [Unreleased]

### Added

- **changelog/archive/** — tracked copies of 2026-05-01 session notes; [changelog/README.md](changelog/README.md) documents workflow.

### Changed

- Documentation: attribution under README License; removed `PORTFOLIO.md`, `EXECUTION_PLAN.md`, `DOC_AUDIT.md`; trimmed `ARCHITECTURE.md`.
- Pre-commit hook reminds to update **CHANGELOG.md** only.

### Removed

- `scripts/new-changelog.sh` (use **CHANGELOG.md** + optional `changelog/archive/` instead).

---

## [2026-05-18] — Test harness

### Added

- **tox** `frontend-vue` env: `npm ci`, typecheck, ESLint, Vitest (Node 20 via `.nvmrc`).
- **requirements.txt**: `langchain-openai`, Azure SDKs; `bcrypt<4.1` pin for passlib in fresh tox envs.
- Lazy Azure provider imports in `backend/app/services/providers/__init__.py`.

### Changed

- **tox** `backend`: `RATE_LIMIT_ENABLED=false`, exclude `slow` (RAGAS) tests by default.
- **README** Testing: `tox -e lint,backend,frontend-streamlit,frontend-vue`.
- Ruff/pytest marker cleanups.

---

## [2026-05-17] — Portfolio publish on `main`

Merged PRs #1–#8. Consolidated from May 2026 development sessions (providers, Vue, platform, logging, eval).

### Added

- **Vue 3 SPA** (`frontend-vue/`): TypeScript, Vite, Pinia, Vue Router, Vitest (124 tests), Playwright e2e, MSW mocks, API interceptors.
- **Streamlit client** (`frontend-streamlit/`).
- **Provider registry** (`backend/app/services/providers/`): `aws`, `azure`, `mock`; wired in `rag.py`; `RAG_FORCE_MOCK`.
- **Request context**: `RequestContextMiddleware`, `X-Request-ID`, `RequestIdFilter`, `backend/tests/core/test_request_context.py`.
- **Observability**: Prometheus metrics (`/api/metrics`); optional `LOG_JSON` structured logs.
- **Rate limiting**: Redis sliding window with fakeredis fallback (`backend/app/core/rate_limit.py`).
- **Dev routes** gated by environment (`dev_routes.py`).
- **Alembic** initial migration `0001_initial_schema.py`.
- **RAGAS eval** (`backend/tests/eval/`, `golden_dataset.json`).
- **k6 load tests** (`load-tests/`, seed script).
- **Scripts**: `run-backend-venv.sh`, `run-frontend-vue.sh`, `kill-dev-servers.sh`, `install-hooks.sh`, load-test helpers.
- **Docs**: architecture, operations, E2E, evaluation, portfolio roadmap, LangGraph design.

### Changed

- **README** and **`.env.example`**: portfolio quick start, mock defaults.
- **`run_services.sh` / tox**: `frontend-streamlit/` after duplicate `frontend/` removal.
- **Logging**: request ID in log format; auth routine logs at DEBUG; INFO for auth outcomes only.
- **`main.py`**: `create_all` only in dev/test; Alembic for production.
- **Registration**: password strength validation (8+ chars, upper, lower, digit).

### Removed

- Duplicate **`frontend/`** tree.
- Root **`root-open-k6.js`** and empty root **`package-lock.json`**.

### Security

- Shared rate limits on auth/chat when `REDIS_URL` is set.
- Generic 500 responses on chat errors.

### Planned but not shipped

Session notes once described these; they are **not** on `main`:

| Item | Notes |
|------|--------|
| `POST /api/chat/stream` (SSE) | Buffered JSON chat only |
| FlashRank / `RERANK_*` | Not in `rag.py` |
| `tox -e eval` | Use `pytest backend/tests/eval/ -m slow` |
| LangGraph | [docs/roadmap/LANGGRAPH.md](docs/roadmap/LANGGRAPH.md) |

---

## [Earlier] — Berkeley ETS Chabot baseline

Original Chabot for UC Berkeley ETS. © The Regents of the University of California — [LICENSE](LICENSE).
