# Changelog

Notable changes to this **portfolio fork** of the UC Berkeley ETS Chabot platform
([multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot)).

[Keep a Changelog](https://keepachangelog.com/) format.  
Attribution and license: [README](README.md#license).

**Author & maintainer:** [sandeep-jay](https://github.com/sandeep-jay) — primary developer on the
Berkeley ETS Chabot codebase and author of this **independent portfolio fork**. Not an official
UC Berkeley product.

**Convention:** sections use **session dates** (when work happened). GitHub PR numbers are noted
where the public merge story matters.

Edit **`[Unreleased]`** while you work. When a session is done, rename it to
`## [YYYY-MM-DD] — short title` and open a new `[Unreleased]`.

---

## [Unreleased]

### Changed

- Documentation: attribution under README License; removed `PORTFOLIO.md`, `EXECUTION_PLAN.md`, `DOC_AUDIT.md`; trimmed `ARCHITECTURE.md`.
- **CHANGELOG.md** — session-based running log (all sessions, not only 2026-05-01).

### Removed

- `scripts/new-changelog.sh` and tracked `changelog/` files (`changelog/` gitignored).

---

## [2026-05-17] — tox and Vue in CI

*Merged as PR #9.*

### Added

- **tox** `frontend-vue` env: `npm ci`, typecheck, ESLint, Vitest (Node 20 via `.nvmrc`).
- **requirements.txt**: `langchain-openai`, Azure SDKs; `bcrypt>=4.0.1,<4.1.0` for passlib in tox.
- Lazy Azure provider imports in `backend/app/services/providers/__init__.py`.

### Changed

- **tox** `backend`: `RATE_LIMIT_ENABLED=false`, exclude `slow` (RAGAS) by default.
- **README** Testing: `tox -e lint,backend,frontend-streamlit,frontend-vue`.
- Ruff/pytest marker cleanups.

---

## [2026-05-17] — Portfolio publish to GitHub

*PRs #1–#8 → [multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot) `main`.*
*Packages work from May 2026 dev sessions into reviewable commits.*

### PR #1 — Dev tooling

- `.githooks/pre-commit`, `scripts/install-hooks.sh`, `run-backend-venv.sh`, `run-frontend-vue.sh`, `kill-dev-servers.sh`, load-test helpers.
- `.gitignore` portfolio hygiene.

### PR #2 — Alembic

- `alembic.ini`, `backend/alembic/`, `0001_initial_schema.py`.

### PR #3 — Platform middleware

- `request_context.py`, `metrics.py`, `rate_limit.py`, `dev_routes.py`; wired in `main.py`, `auth.py`, `chat.py`.

### PR #4 — Providers, RAG, eval

- `backend/app/services/providers/` (AWS / Azure / mock); `rag.py` registry wiring.
- `backend/tests/eval/` RAGAS golden harness.

### PR #5 — Vue 3 SPA

- `frontend-vue/` scaffold, API/auth, chat UI, sessions, sources, Vitest + Playwright scaffolding.

### PR #6 — Streamlit client

- `frontend-streamlit/` (auth, chat services, UI components, pytest).

### PR #7 — Load tests

- `load-tests/` k6 smoke + auth-chat-session; user seed script.

### PR #8 — Docs and README

- `docs/` architecture, operations, E2E, evaluation, roadmaps, LangGraph design.
- Portfolio **README**, mock **`.env.example`**.

### Post-publish cleanup (PR #7–#8 follow-ups)

- Removed duplicate **`frontend/`** tree; **`run_services.sh` / tox** → `frontend-streamlit/`.
- **`main.py`**: `create_all` only in dev/test; **`requirements.txt`**: `alembic`, `redis`.
- Removed root **`root-open-k6.js`**, empty root **`package-lock.json`**.

---

## [2026-05-01] — RAG platform, Vue, providers (dev session)

*Implementation work; landed on `main` via 2026-05-17 PRs above. Some session notes describe features not merged.*

### Added — on `main`

- **Vue 3 SPA**, **Streamlit** tree, **provider registry**, **Redis rate limiter**, **Prometheus metrics**, **dev routes**, **RAGAS eval**, core **scripts**.

### Added — session plan only (**not** on `main`)

- **`POST /api/chat/stream` (SSE)**; **FlashRank** `RERANK_*`; extra tox envs (`eval`, `load-smoke`, …).

### Changed / fixed / security

- **`rag.py`**, **`chat.py`**, schemas, **`.env.example`**, **requirements**, **ruff** / **pytest**; password rules; `MessageBubble.vue`; generic chat 500s; EB health proxy.

### Follow-ups

- RAGAS golden Q&A; production `REDIS_URL`; LangGraph / SSE / rerank — [docs/roadmap/LANGGRAPH.md](docs/roadmap/LANGGRAPH.md).

---

## [2026-05-01] — Logging and request correlation (dev session)

### Summary

One **request id** per HTTP request (`X-Request-ID`); optional **JSON** logs; quieter **auth** logs.

### Added

- `request_context.py`, `LOG_JSON`, tests, `kill-dev-servers.sh`, Vue `interceptors.ts` for `X-Request-ID`.

### Changed / removed / security

- `logger.py`, `main.py`, `security.py`, config; removed unused `LOGGING_PROPAGATION_LEVEL`; no JWT dumps at INFO.

---

## Berkeley ETS Chabot (baseline)

**Chabot** — campus RAG chatbot for **UC Berkeley ETS** over AWS Bedrock.  
Upstream: [ets-berkeley-edu/chabot](https://github.com/ets-berkeley-edu/chabot).  
© The Regents of the University of California — [LICENSE](LICENSE).

**[sandeep-jay](https://github.com/sandeep-jay)** led implementation (CBO-tracked PRs below). Regents headers remain on derived files in this fork.

---

## [2025-08-01] — Streamlit UX and frontend tests

### Added

- Streamlit refactor: chat interface, message display, feedback UI and stylesheets ([CBO-86]).
- Frontend test suite covering auth, chat, and message modules ([CBO-89]).

---

## [2025-06-13] — Backend and API test suites

### Added

- Pytest for RAG workflow, AWS/Bedrock/LangSmith, auth, DB/models/services ([CBO-69], [CBO-71], [CBO-72], [CBO-84]).
- Chat API interaction tests: CRUD, feedback, sources, mocks ([CBO-70]).
- **`pyproject.toml`** tool config; tox/travis alignment ([CBO-72]).

---

## [2025-06-05] — Streamlit cleanup

### Changed

- Removed basic Streamlit prototype in favor of modular refactor ([CBO-99]).

---

## [2025-05-30] — Chat API and Streamlit auth

### Added

- Chat endpoints: sessions, messages, feedback, `test_langsmith` ([CBO-45]–[CBO-47]).
- Streamlit login, auth module, client services ([CBO-65], [CBO-66], [CBO-80], [CBO-81]).

---

## [2025-05-29] — JWT auth and advanced RAG

### Added

- JWT authentication module and auth endpoints ([CBO-74], [CBO-75]).
- Advanced RAG with Bedrock integration ([CBO-85]).

---

## [2025-05-28] — Elastic Beanstalk deploy sketch

### Added

- `.ebextensions` and Nginx config for FastAPI + Streamlit ([CBO-63]).

---

## [2025-05-12] — Bedrock RAG and first UI

### Added

- AWS, LangChain, Bedrock; simple RAG and `/chat` integration; prompt templates ([CBO-31], [CBO-34], [CBO-36], [CBO-41]).
- Basic Streamlit chat UI + LangSmith tracing ([CBO-36], [CBO-42]).
- **ruff** and **tox** ([CBO-67]).

---

## [2025-05-05] — FastAPI foundation

### Added

- FastAPI boilerplate (`/`, `/health`) ([CBO-30]).
- Pydantic-settings config manager ([CBO-32]).
- Modular logger ([CBO-35]).
- SQLAlchemy + chatbot table design ([CBO-49]).

---

## [2025-05-13] — CI and README

### Added

- Travis CI linters ([CBO-82]).
- README instructions ([CBO-82]).

### Changed

- `.gitignore` for `.tox` and `.ruff*` ([NOJIRA]).
