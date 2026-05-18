# Changelog

Notable changes to this **portfolio fork** of the UC Berkeley ETS Chabot platform
([multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot)).

Format follows [Keep a Changelog](https://keepachangelog.com/).  
Attribution and license: [README](README.md#license).

Session working drafts (more detail, some planned items) were consolidated from
`changelog/2026-05-01-*.md` — see [changelog/README.md](changelog/README.md).

---

## [Unreleased]

### Changed

- Documentation: attribution under README License; removed publish-era docs
  (`PORTFOLIO.md`, `EXECUTION_PLAN.md`, `DOC_AUDIT.md`); trimmed `ARCHITECTURE.md`.

---

## [2026-05-18] — Test harness

### Added

- **tox** `frontend-vue` env: `npm ci`, typecheck, ESLint, Vitest (Node 20 via `.nvmrc`).
- **requirements.txt**: `langchain-openai`, Azure SDKs; `bcrypt<4.1` pin for passlib in fresh tox envs.
- Lazy Azure provider imports in `backend/app/services/providers/__init__.py`.

### Changed

- **tox** `backend`: `RATE_LIMIT_ENABLED=false`, exclude `slow` (RAGAS) tests by default.
- **README** Testing section documents unified `tox -e lint,backend,frontend-streamlit,frontend-vue`.
- Ruff/pytest marker cleanups.

---

## [2026-05-17] — Portfolio publish on `main`

Summary of merged PRs #1–#8 on [multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot).
Consolidated from portfolio execution plan and 2026-05-01 session notes.

### Added

- **Vue 3 SPA** (`frontend-vue/`): TypeScript, Vite, Pinia, Vue Router, Vitest (124 tests), Playwright e2e scaffolding, MSW mocks.
- **Streamlit client** (`frontend-streamlit/`): same REST API as Vue.
- **Provider registry** (`backend/app/services/providers/`): LLM and retriever for `aws`, `azure`, `mock`; wired in `rag.py`; `RAG_FORCE_MOCK` for zero-cloud demos.
- **Platform middleware**: `RequestContextMiddleware` + `X-Request-ID`; Prometheus metrics; Redis/fakeredis rate limits on auth/chat; dev-only routes.
- **Alembic** (`backend/alembic/`, `0001_initial_schema.py`); production expects `alembic upgrade head`.
- **RAGAS eval** (`backend/tests/eval/`, `golden_dataset.json`); see [docs/EVALUATION.md](docs/EVALUATION.md).
- **k6 load tests** (`load-tests/`); [docs/LOAD_TESTING.md](docs/LOAD_TESTING.md).
- **Dev tooling**: `.githooks/pre-commit`, `scripts/` (venv, Vue, loadtest, hooks).
- **Docs**: architecture, operations, E2E, evaluation, roadmap, LangGraph design.

### Changed

- **README**: portfolio quick start, mock RAG, feature list, upstream link.
- **`.env.example`**: mock-friendly defaults.
- **`run_services.sh` / tox**: `frontend-streamlit/` path after duplicate tree removal.
- **Logging**: `LOG_JSON`, request ID in logs, quieter auth INFO logs.
- **`main.py`**: `create_all` only in dev/test.
- **Password rules** on registration; tests updated.

### Removed

- Duplicate **`frontend/`** tree (same as `frontend-streamlit/`).
- Root **`root-open-k6.js`** and empty root **`package-lock.json`**.

### Security

- Rate limiting on auth and chat (shared Redis when `REDIS_URL` set).
- Generic 500 messages on chat errors.

### Known gaps (planned in session notes, not on `main`)

| Item | Status |
|------|--------|
| `POST /api/chat/stream` (SSE) | Not implemented |
| FlashRank / `RERANK_*` in `rag.py` | Not implemented |
| `tox -e eval` | Use `pytest backend/tests/eval/ -m slow` |
| LangGraph | Design only — [docs/roadmap/LANGGRAPH.md](docs/roadmap/LANGGRAPH.md) |

---

## [Earlier] — Berkeley ETS Chabot baseline

Original Chabot developed for UC Berkeley ETS. © The Regents of the University of California — [LICENSE](LICENSE).

---

## How to update

1. Edit **[Unreleased]**, then move entries under a dated section when merging a milestone.
2. Optional draft: `./scripts/new-changelog.sh <slug>` → fold summary into this file before push.
