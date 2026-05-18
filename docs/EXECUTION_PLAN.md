# Master plan — commits, PRs, and portfolio publish

**Last updated:** 2026-05-17  
**Canonical doc** for staging uncommitted work (public copy in `docs/`). The matching file under `changelog/PR_PLAN.md` is gitignored locally. Supersedes the Cursor plan `logical_commit_breakdown_e582d942` (kept as a pointer only).

| Doc | Purpose |
|-----|---------|
| **This file** | Commit order, PR slices, hygiene, remotes |
| [docs/roadmap/PORTFOLIO_PHASED_ROADMAP.md](./roadmap/PORTFOLIO_PHASED_ROADMAP.md) | High-ROI phases: publish, RAGAS, LangGraph, agentic deferral |
| [docs/PORTFOLIO.md](./PORTFOLIO.md) | New repo vs detach fork; LICENSE; rename |
| [docs/EVALUATION.md](./EVALUATION.md) | RAGAS vs LangSmith; scorecard |
| [docs/roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) | Graph modules and flags |

`changelog/` may be gitignored — this file is the durable checklist.

---

## Strategy: portfolio first, Berkeley optional

1. **Publish** on your standalone GitHub repo (new repo or **Leave fork network** — see [PORTFOLIO.md](./PORTFOLIO.md)).
2. **Commit** pending work in dependency order below (local `main` or `dev`).
3. **Optional:** cherry-pick small backend fixes to `ets-berkeley-edu/chabot` — do **not** merge entire portfolio `main` unless ETS asks.

You authored the original system; this plan optimizes for **reviewable history + mock demo**, not upstream PR throughput.

---

## Hygiene before staging

Do **not** commit secrets or generated artifacts (extend [`.gitignore`](../.gitignore) if missing):

| Exclude | Why |
|---------|-----|
| `frontend-vue/.env.local` | Secrets |
| `frontend-vue/coverage/` | Generated |
| `frontend-vue/playwright-report/`, `test-results/` | Generated |
| `frontend-vue/e2e/.auth/` | Generated Playwright auth |
| Root `.env` | Secrets |

**Do commit:** `frontend-vue/.env.example`, `frontend-vue/.env.test`, `.env.example` patterns.

---

## What is pending (current tree)

Almost all new work is **untracked** (~150 paths): `.githooks/`, `alembic.ini`, `backend/alembic/`, `backend/app/core/{dev_routes,metrics,rate_limit,request_context}.py`, `backend/app/services/providers/`, tests (`backend/tests/core/`, `eval/`, `services/providers/`), `docs/`, `frontend-vue/`, `frontend-streamlit/`, `load-tests/`, `scripts/`, root k6/npm artifacts.

**Integration gap (fix in platform/RAG commits):**

- [`backend/app/main.py`](../backend/app/main.py) — new middleware not wired yet
- [`backend/app/api/chat.py`](../backend/app/api/chat.py), [`auth.py`](../backend/app/api/auth.py) — rate limit / context not wired
- [`backend/app/services/rag.py`](../backend/app/services/rag.py) — still direct Bedrock, not provider registry

### Implementation status (2026-05-17 audit)

| Area | Status |
|------|--------|
| Platform modules (`request_context`, `metrics`, `rate_limit`, `dev_routes`) | **Present, not wired** in `main.py` / routers |
| Provider registry | **Present**; `rag.py` still uses Bedrock directly |
| LangGraph (`backend/app/services/graph/`) | **Not started** (roadmap Phase 4) |
| `/api/chat/stream` (SSE) | **Not present** in `chat.py` (Phase 6 / org Phase 0 target) |
| RAGAS eval tests | **Present** under `backend/tests/eval/` |
| `tox -e eval` | **Not defined** — use `pytest backend/tests/eval/` from repo root with `PYTHONPATH=.` |


---

## Dependency order (commits and PRs)

```text
PR1 (tooling) ──┐
PR2 (alembic) ──┼──► PR3 (platform+wiring) ──► PR4 (providers/RAG/eval) ──► PR5 (Vue) ──┐
                │                                                              PR6 (Streamlit)
                └──────────────────────────────────────────────────────────────► PR7 (load tests) ──► PR8 (docs)
                                                                                    │
                                                                        PR4b/c LangGraph (after PR4a)
```

- **PR3 before PR4** — platform middleware and env flags providers may need.
- **PR4a before PR4b** — LangGraph requires provider wiring in `rag.py`.
- **PR5 / PR6** — parallel after API stable.
- **PR8** — docs; can fold small doc updates into feature PRs.

---

## Logical commits (stage one at a time)

Each row = one `git commit` (or squash PR slice). Use prefixes: `chore:`, `feat(backend):`, `feat(vue):`, `docs:`.

| # | Commit contents | PR |
|---|-----------------|-----|
| **0** | `.gitignore` hygiene only | — |
| **1** | `.githooks/pre-commit`, `scripts/install-hooks.sh` | PR1 |
| **1b** | Remaining `scripts/*` (venv, vue, kill-dev, loadtest, changelog) | PR1 |
| **2** | `root-open-k6.js` + root `package-lock.json` (if used together) | PR1 |
| **3** | `alembic.ini`, `backend/alembic/` (+ DB config if needed) | PR2 |
| **4** | `request_context.py` + test + **`main.py` middleware** | PR3 |
| **5** | `metrics.py` + **`main.py`** + config / `.env.example` | PR3 |
| **6** | `rate_limit.py` + **`auth.py` / `chat.py`** + settings | PR3 |
| **7** | `dev_routes.py` + guarded router in **`main.py`** | PR3 |
| **8** | `providers/` + tests + **`rag.py` wiring** | PR4a |
| **9** | `backend/tests/eval/` (golden + RAGAS) | PR4 |
| **10a–d** | Vue: scaffold → shell → auth/chat → tests/e2e (no artifacts) | PR5 |
| **11** | `frontend-streamlit/` | PR6 |
| **12** | `load-tests/` (+ script ties) | PR7 |
| **13** | `docs/` (architecture, portfolio, roadmap, eval, langgraph) | PR8 |

**Do not** `git add .` once — history becomes unreviewable and cherry-picks to Berkeley break.

### Vue sub-commits (10)

1. `package.json`, lockfile, Vite/TS, `index.html`, `frontend-vue/README.md`
2. Router, layout, styles, API client
3. Auth + chat components, stores, composables
4. Vitest + Playwright configs (exclude coverage/reports)

---

## PR breakdown (detail)

### PR1 — Tooling and hooks

| Paths |
|-------|
| `.githooks/pre-commit`, `scripts/install-hooks.sh`, other `scripts/`, optional root k6/npm |

**Goal:** Automation only; no runtime behavior change.

---

### PR2 — Alembic

| Paths |
|-------|
| `alembic.ini`, `backend/alembic/versions/` |

**Goal:** Schema migration path; document `create_all` vs migrate for dev/prod.

---

### PR3 — Platform (prefer one integration commit on `main.py`)

| Paths |
|-------|
| `request_context.py`, `metrics.py`, `rate_limit.py`, `dev_routes.py`, tests, **wiring** in `main.py`, `auth.py`, `chat.py` |

**Goal:** One coherent middleware order; each slice testable.

---

### PR4 — Providers, RAG, eval

| Slice | Paths |
|-------|--------|
| **4a** | `backend/app/services/providers/`, tests, **`rag.py` → registry** |
| **4b** | `backend/app/services/graph/`, `RAG_ENGINE`, tests (see [LANGGRAPH.md](./roadmap/LANGGRAPH.md)) |
| **4c** | Default `langgraph` after RAGAS parity; remove legacy chain |

| **Eval** | `backend/tests/eval/` — commit 9; gate via `RAGAS_QUALITY_GATE` |

**Goal:** Swappable LLM/retriever; measurable RAG quality; optional LangGraph parity.

---

### PR5 — Vue

| Paths |
|-------|
| `frontend-vue/` (hygiene exclusions) |

**Goal:** Primary portfolio UI; mock-friendly E2E.

---

### PR6 — Streamlit

| Paths |
|-------|
| `frontend-streamlit/` |

**Goal:** Second client, same API — optional in portfolio README.

---

### PR7 — Load testing

| Paths |
|-------|
| `load-tests/`, `scripts/run-backend-loadtest.sh` |

**Goal:** Document base URL + auth for k6 ([LOAD_TESTING.md](../docs/LOAD_TESTING.md)).

---

### PR8 — Documentation

| Paths |
|-------|
| `docs/` including `PORTFOLIO.md`, `EVALUATION.md`, `roadmap/PORTFOLIO_PHASED_ROADMAP.md`, `roadmap/LANGGRAPH.md` |

**Goal:** Architecture, portfolio publish, eval and LangGraph guides.

---

## Portfolio publish workflow

### Option A — New repo (cleanest)

1. Copy tree (exclude `.git`, secrets, artifacts) — [PORTFOLIO.md](./PORTFOLIO.md)
2. `git init` → commits **0–13** → push to **new** GitHub repo (not Fork)
3. README: rename, attribution, mock quick start

### Option B — Detach existing fork

1. GitHub **Settings → Leave fork network**
2. `origin` = your repo; optional `upstream` = ETS for fetch only
3. Same commits **0–13** on `main`

### After publish (roadmap)

Follow [PORTFOLIO_PHASED_ROADMAP.md](./roadmap/PORTFOLIO_PHASED_ROADMAP.md):

| Phase | Focus |
|-------|--------|
| 0–1 | Publish + commits + demo |
| 2–3 | Complete platform wiring if needed; RAGAS + LangSmith |
| 4 | LangGraph parity |
| 5 | Retrieval graph nodes |
| 6 | Streaming + bounded agentic (optional) |

---

## Remotes

| Remote | URL | Use |
|--------|-----|-----|
| `origin` | `https://github.com/<you>/<portfolio-repo>.git` | Daily push |
| `upstream` | `https://github.com/ets-berkeley-edu/chabot.git` | Optional fetch; cherry-pick only |

If `origin` still points at ETS: `git remote rename origin upstream` then `git remote add origin <your-url>`.

---

## Optional: contribute to Berkeley

1. `git fetch upstream`
2. Branch from `upstream/dev` (or `main`)
3. Cherry-pick or re-apply **small** backend commits (PR3/PR4a slices)
4. Open PR to ETS — **not** portfolio Vue/LangGraph wholesale

---

## Per-PR / per-commit checklist

- [ ] Scope matches one row in commit table
- [ ] Tests green for touched areas
- [ ] No secrets or generated artifacts
- [ ] Platform/RAG commits include **wire-up**
- [ ] LangGraph: RAGAS parity before default flip ([EVALUATION.md](./EVALUATION.md))
- [ ] README updated for portfolio-facing PRs (PR5, PR8)

---

## Consolidation note

The Cursor plan **Logical commit breakdown** (`logical_commit_breakdown_e582d942`) is merged here. Update **this file** when commit strategy changes.
