# Documentation audit (2026-05-17)

Review of portfolio/consolidation docs against the current codebase (`dev` branch, uncommitted work mostly **untracked**).

## Summary

| Verdict | Detail |
|---------|--------|
| **Commit order & PR slices** | **Correct** — matches tree and dependencies |
| **Integration gaps** | **Correctly documented** — platform not wired; `rag.py` not on providers |
| **Portfolio / fork / LICENSE** | **Correct** — legal nuance appropriately cautious |
| **LangGraph / RAGAS design** | **Correct as plan** — clearly future or partial |
| **Fixed in this audit** | PR_PLAN visibility, `tox -e eval`, phase overlap, streaming status, LangGraph status |

---

## Critical issues (fixed)

### 1. `changelog/PR_PLAN.md` is gitignored

`.gitignore` lists `changelog/`. A public portfolio repo would **not** include the master commit plan if only that path is used.

**Fix:** Added [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) (copy for `docs/` — **commit in PR8**). `changelog/PR_PLAN.md` now points to it.

### 2. `tox -e eval` does not exist

`test_rag_quality.py` header mentions `tox -e eval`, but `tox.ini` only defines `backend`, `frontend`, `lint`. The `frontend` env points at `frontend/` not `frontend-vue/`.

**Fix:** [EVALUATION.md](./EVALUATION.md) and [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) now say `PYTHONPATH=. pytest backend/tests/eval/ -v`.

### 3. Portfolio Phase 1 vs Phase 2 overlap

Phase 1 commits **include** platform wiring (commits 4–7); Phase 2 was titled as if all that work happens after publish.

**Fix:** Phase 2 renamed to **verify** platform + providers.

### 4. SSE streaming assumed but missing

`PHASED_IMPROVEMENT_ROADMAP` Phase 0 and portfolio Phase 6 reference `/api/chat/stream`. **`chat.py` has no stream route** (only buffered `/chat` and session messages).

**Fix:** Phase 6 notes streaming is **not implemented**; org Phase 0 banner clarified as planned/in-flight.

### 5. LangGraph described without status

`backend/app/services/graph/` does not exist; `langgraph` not in `requirements.txt`.

**Fix:** [LANGGRAPH.md](./roadmap/LANGGRAPH.md) states **not implemented**.

---

## Accurate claims (no change needed)

| Claim | Evidence |
|-------|----------|
| ~150 untracked paths | Matches `git status` |
| `main.py` lacks new middleware | Only CORS + routers in `main.py` |
| `rag.py` uses `ConversationalRetrievalChain` + Bedrock | Confirmed |
| RAGAS thresholds 0.85 / 0.80 / 0.75 / 0.70 | `test_rag_quality.py` |
| `RAG_FORCE_MOCK` in provider registry | `providers/__init__.py` |
| Rate limit helpers exist (`limit_chat`, etc.) | `rate_limit.py` — not attached to routes yet |
| LangSmith tracing | `simple_tracer.py`, `test_langsmith` route |
| Detach fork / new repo guidance | Valid GitHub workflow |

---

## Overstated elsewhere (not rewritten fully)

[ARCHITECTURE.md](./ARCHITECTURE.md) describes capabilities that are **partially aspirational** relative to `main.py`:

| ARCHITECTURE claim | Code reality |
|--------------------|--------------|
| Providers drive RAG | Registry exists; **`rag.py` not wired** |
| Provider timeout/retry/circuit breaker / `degraded_mode` | **Not found** in services (metrics have `PROVIDER_*` labels only) |
| CSRF double-submit on mutating routes | **No CSRF** matches in `backend/app` |
| `/api/auth/refresh` | **No refresh route** in `auth.py` |
| Rate limiter on auth/chat | Module exists; **not `Depends` on routes** |

Recommend a follow-up pass on ARCHITECTURE after PR3 wiring, or add an "Implementation status" section there matching [EXECUTION_PLAN.md](./EXECUTION_PLAN.md).

---

## Minor / optional improvements

| Item | Suggestion |
|------|------------|
| `LLM_PROVIDER` in `.env.example` | Confirm vars exist in committed `default.py` before README cites them |
| `tox.ini` `frontend` env | Update to `frontend-vue` or document pytest/npm instead |
| Cursor plan `logical_commit_breakdown` | Links use absolute Workbench paths — use `docs/EXECUTION_PLAN.md` |
| Org vs portfolio phase numbers | Easy to confuse Phase 4 (LangGraph) vs org Phase 4 (cost) — cross-links help |

---

## Doc map (canonical)

| Read this | For |
|-----------|-----|
| [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) | Commits, PRs, publish |
| [roadmap/PORTFOLIO_PHASED_ROADMAP.md](./roadmap/PORTFOLIO_PHASED_ROADMAP.md) | High-ROI phases |
| [EVALUATION.md](./EVALUATION.md) | RAGAS vs LangSmith |
| [PORTFOLIO.md](./PORTFOLIO.md) | Fork detach, LICENSE |
| [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) | Graph design (planned) |
| [roadmap/PHASED_IMPROVEMENT_ROADMAP.md](./roadmap/PHASED_IMPROVEMENT_ROADMAP.md) | Campus/scale track |
