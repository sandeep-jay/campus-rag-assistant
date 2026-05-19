# Security

Dependency audit, static analysis, and production hardening for Campus RAG Assistant.

## Regular checks

From repo root (project `venv` recommended):

```bash
./venv/bin/python -m pip install pip-audit bandit
./venv/bin/pip-audit
./venv/bin/bandit -r backend/app -ll
cd frontend-vue && npm audit
```

Run `pip install -r requirements.txt` before `pip-audit` so the environment matches production deps.

## Production hardening

| Item | Dev default | Production |
|------|-------------|------------|
| `SECRET_KEY` | placeholder in `default.py` | Strong random secret via env |
| `BACKEND_CORS_ORIGINS` | `['*']` | Explicit frontend origin(s) only |
| `.env` | Local secrets | Never commit; use secrets manager / EB env |
| OAuth | `127.0.0.1` alignment | HTTPS + registered callbacks — [PRODUCTION_TLS.md](./PRODUCTION_TLS.md) |
| `WEB_RESEARCH_ENABLED` | `false` | Enable only with Tavily key and policy review |

## Dependency policy (2026-05-18)

Runtime bumps on `feature/security-deps`:

- **FastAPI / Starlette** — `fastapi>=0.115` (Starlette CVE fixes)
- **Auth** — `python-jose>=3.4`, `PyJWT>=2.12`
- **Uploads** — `python-multipart>=0.0.27`
- **HTTP** — `requests>=2.32.4`, `urllib3>=2.2`, `httpx>=0.27` (LangGraph 0.2.x)
- **LangGraph** — `langgraph==0.2.76`, `langgraph-checkpoint==2.0.26`

Dev-only packages (Streamlit, RAGAS, old pip/setuptools) may still appear in audits; track separately.

## Reporting

Open a GitHub security advisory or contact the maintainer in [README](../README.md).
