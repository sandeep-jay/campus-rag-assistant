# Active sprint

**Status:** No single-day sprint is in progress (2026-05-18 LangGraph sprint completed).

| Next | Doc |
|------|-----|
| **Portfolio priorities** | [PORTFOLIO_PHASED_ROADMAP.md](./PORTFOLIO_PHASED_ROADMAP.md) |
| **Completed 2026-05-18 sprint** | [archive/SPRINT_2026-05-18_LANGGRAPH.md](./archive/SPRINT_2026-05-18_LANGGRAPH.md) |
| **LangGraph design** | [LANGGRAPH.md](./LANGGRAPH.md) |
| **Web research** | [WEB_RESEARCH.md](./WEB_RESEARCH.md) |

## Quick commands

```bash
tox -e lint,backend          # CI-style backend (mock RAG)
tox -e frontend-vue          # Vue typecheck, lint, unit tests
./scripts/run-backend-venv.sh  # API — use PIP_SYNC=0 if venv is current
./scripts/run-frontend-vue.sh
```

Live AWS validation uses `RAG_ENGINE=langgraph` in local `.env` only (not required for tox).
