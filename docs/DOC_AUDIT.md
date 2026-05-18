# Documentation audit (2026-05-18)

Review of portfolio docs against **`main` on [multicloud-rag-chatbot](https://github.com/sandeep-jay/multicloud-rag-chatbot)** after PR1–PR8, README, and PR7 (remove duplicate `frontend/`).

## Summary

| Verdict | Detail |
|---------|--------|
| **Publish queue (PR1–PR8)** | **Complete** on `main` |
| **Platform + RAG wiring** | **Shipped** — middleware, rate limits, provider registry in `rag.py` |
| **Streamlit path** | **Single tree** — `frontend-streamlit/` only (`frontend/` removed PR7) |
| **SSE streaming** | **Not implemented** on backend; Vue falls back to buffered chat |
| **LangGraph** | **Planned** — see [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) |

---

## Implementation status (current `main`)

| Area | Status |
|------|--------|
| Git hooks, scripts, Alembic baseline | On `main` |
| `request_context`, metrics middleware | Wired in `main.py` |
| Rate limits | `limit_login` / `limit_register` / `limit_chat` on routes |
| Provider registry + `rag.py` | Wired; default mock via `RAG_FORCE_MOCK` / `LLM_PROVIDER` |
| Vue + Streamlit clients | `frontend-vue/`, `frontend-streamlit/` |
| k6 load tests | `load-tests/` |
| RAGAS eval | `backend/tests/eval/` — run with `pytest`, not `tox -e eval` |
| `/api/chat/stream` | **Missing** — [ARCHITECTURE.md](./ARCHITECTURE.md) / README note gap |
| LangGraph (`backend/app/services/graph/`) | **Not started** |
| `metadata.create_all` at startup | **Dev/test only** — production should use `alembic upgrade head` |
| Root `root-open-k6.js` / empty `package-lock.json` | **Removed** — use `load-tests/*.js` |

---

## Doc accuracy issues (follow-up)

| Doc / claim | Reality |
|-------------|---------|
| [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) “pending untracked” section | **Stale** — historical; see “Publish status” below |
| [ARCHITECTURE.md](./ARCHITECTURE.md) CSRF, refresh token, circuit breaker | **Not implemented** — aspirational or Berkeley-era |
| `AwsLlmProvider.get_streaming_llm` | Calls missing `BedrockService.get_streaming_llm` until SSE PR |
| `tox.ini` | `frontend-vue` env runs typecheck, ESLint, Vitest; no `eval` env yet |
| `tox -e eval` | **Not defined** — use `PYTHONPATH=. pytest backend/tests/eval/` |

---

## Accurate claims

| Claim | Evidence |
|-------|----------|
| Mock demo without cloud | `RAG_FORCE_MOCK`, providers `mock` default, README quick-start |
| RAGAS thresholds | `test_rag_quality.py` |
| Prometheus `/api/metrics` | `main.py` |
| Dev-only debug routes | `require_dev_api_routes` on `/debug-auth`, `/test_langsmith` |

---

## Doc map (canonical)

| Read this | For |
|-----------|-----|
| [README.md](../README.md) | Quick start |
| [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) | Historical PR/commit map + future work |
| [roadmap/PORTFOLIO_PHASED_ROADMAP.md](./roadmap/PORTFOLIO_PHASED_ROADMAP.md) | High-ROI phases |
| [EVALUATION.md](./EVALUATION.md) | RAGAS vs LangSmith |
| [PORTFOLIO.md](./PORTFOLIO.md) | Fork detach, LICENSE |
| [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md) | Graph design (planned) |
