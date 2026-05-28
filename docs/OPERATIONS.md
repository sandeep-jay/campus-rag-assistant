# Operations and Observability

## Runtime model (production)

- Run the API with multiple workers via gunicorn + uvicorn workers.
- Set `API_WORKERS` according to available CPU (start with `2 * cores`, cap based on DB pool).
- `run_services.sh` now traps `SIGTERM`/`SIGINT` and performs graceful child shutdown.

Example API startup:

```bash
API_WORKERS=4 API_TIMEOUT=60 API_GRACEFUL_TIMEOUT=30 USE_GUNICORN=1 ./run_services.sh
```

## Database migration workflow (Alembic)

Alembic scaffolding is included (`alembic.ini`, `backend/alembic/`).

Create migration:

```bash
alembic revision --autogenerate -m "add_new_table"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback one migration:

```bash
alembic downgrade -1
```

### Deploy order

1. Build artifact/container.
2. Run `alembic upgrade head` against target DB.
3. Start/restart API workers.
4. Verify `/api/health` and `/api/metrics`.


## Logging

| Setting | Purpose |
|---------|---------|
| `LOGGING_LEVEL` | App log level (`INFO` recommended for production) |
| `LOGGING_FORMAT` | Include `%(request_id)s` — wired via `RequestIdFilter` on all handlers |
| `LOGGING_LOCATION` | Rotating file path when `LOG_TO_FILE=true` (default `backend_logs.log`) |
| `LOG_JSON` | When `true`, emit one JSON object per line (for aggregators) |
| `LOG_TO_FILE` | Enable rotating file handler (10 MB × 20 backups) |

**Privacy:** JWT payloads and full chat queries are not logged at `INFO`. Use `DEBUG` locally for verbose auth/RAG text. Access lines: `app.access` logger (`METHOD path status duration`).

## Local logs

`*.log` files (`app.log`, `backend/app.log`, etc.) are gitignored. After stopping uvicorn/Vite, remove them to reclaim disk:

```bash
find . -name '*.log' -not -path './venv/*' -not -path './node_modules/*' -delete
```

## Security

See [SECURITY.md](./SECURITY.md) for `pip-audit`, bandit, and production hardening.

## Metrics baseline

Exposed endpoints:

- `GET /api/metrics` (Prometheus format)
- `GET /api/metrics/db-pool` (JSON snapshot)

Included metrics:

- HTTP request count/latency/errors
- Provider call latency and provider error reasons
- DB pool size/checkouts/overflow/usage ratio

## Dashboard and alerts baseline

### Suggested SLOs

- API availability: `>= 99.9%` monthly (`5xx` responses considered failures).
- **Auth / session API** (no LLM): `p95 < 1.2s`, `p99 < 2.5s` at steady load.
- **Chat with RAG** (live LLM + retrieval): use phase-aware targets — see [LOAD_TESTING.md](./LOAD_TESTING.md) (`K6_LATENCY_PROFILE=live` allows chat `p95` up to ~45s under ramp; `mock` profile targets sub-second HTTP).
- **SSE time-to-first-token**: track `chatbot_chat_first_token_latency_seconds` (lower is better; dominated by condense + retrieve on live providers).
- Error budget: `<= 0.1%` failed requests over 30 days.

### Alerts

- **High 5xx rate**: `rate(chatbot_http_requests_total{status_code=~"5.."}[5m]) > 0.02`.
- **Slow auth/session**: same histogram on `/api/auth/*` and `/api/chat/sessions` with `> 1.2` threshold.
- **Slow buffered chat**: `histogram_quantile(0.95, sum(rate(chatbot_http_request_latency_seconds_bucket{path="/api/chat/chat"}[5m])) by (le)) > 45` for live RAG, or `> 1.2` when using mock providers.
- **Slow first token**: `histogram_quantile(0.95, rate(chatbot_chat_first_token_latency_seconds_bucket[5m])) > 30` (tune per provider).
- **Provider failures spike**: `increase(chatbot_provider_errors_total[10m]) > 20`.
- **DB pool pressure**: `avg_over_time(chatbot_db_pool_usage_ratio[5m]) > 0.85`.

## Runbook

### High latency

1. Check `chatbot_http_request_latency_seconds` by path.
2. Check `chatbot_provider_latency_seconds` for degraded providers.
3. Increase `API_WORKERS` only if CPU has headroom.
4. If DB bound, raise `SQLALCHEMY_POOL_SIZE` and validate DB connection limits.

### Elevated 5xx

1. Correlate with `chatbot_provider_errors_total` and application logs.
2. If provider timeouts dominate, tune `PROVIDER_TIMEOUT_SECONDS` and retries.
3. If DB pool saturation is high, increase pool and reduce worker count temporarily.

### DB pool saturation

1. Inspect `/api/metrics/db-pool` and dashboard for `usage_ratio` and overflow.
2. Reduce worker count or per-worker concurrency to lower connection demand.
3. Increase DB max connections and corresponding app pool settings.

## Helpdesk agent runtime

| Flag / variable | Purpose |
|---|---|
| `HELPDESK_ENABLED` | Master flag for ASK-mode `/api/helpdesk/{summarize,draft-ticket,create-issue}` |
| `HELPDESK_AGENT_ENABLED` | Enables AGENT-mode `/api/helpdesk/agent/*` LangGraph endpoints |
| `HELPDESK_AGENT_KILL_SWITCH` | Set `true` to short-circuit all in-flight agent sessions (returns `aborted`) |
| `GITHUB_TOKEN` | Fine-grained PAT (`issues:write`) for the demo repo; **SecretStr**, never log |
| `GITHUB_REPO` | `owner/repo` of the **private** demo repo issues are filed to |
| `GITHUB_DEFAULT_LABELS` | Comma-separated labels added to every filed issue |
| `HELPDESK_KB_RESOLVED_MIN_SCORE` | Optional rerank-score floor for `kb_resolved` heuristic |
| `HELPDESK_DEDUP_WINDOW_SECONDS` | Suppress duplicate filings inside this window |
| `HELPDESK_SUMMARIZE_MAX_TURNS` | Number of recent chat turns fed into recap/draft |
| `HELPDESK_AGENT_CHECKPOINT_PATH` | SQLite checkpointer path (`.helpdesk_agent_checkpoints.sqlite` by default) |

Prometheus metrics: `chatbot_helpdesk_recap_*`, `chatbot_helpdesk_draft_ticket_*`, `chatbot_helpdesk_create_issue_total`, `chatbot_helpdesk_kb_resolved_total`, `chatbot_helpdesk_agent_started_total`, `chatbot_helpdesk_agent_tool_total`, `chatbot_helpdesk_agent_outcome_total`, `chatbot_helpdesk_agent_funnel_total`, `chatbot_helpdesk_agent_error_total`. Engineering spec: [HELPDESK_AGENT.md](./roadmap/HELPDESK_AGENT.md).

## OAuth and local development

- Enable providers in `.env`: `OAUTH_ENABLED_PROVIDERS=github` (or `google,github`) plus client ID/secret vars (see `.env.example`).
- **Local dev:** OAuth runs on the API (`OAUTH_REDIRECT_BASE_URL=http://127.0.0.1:8000`); Vue uses `VITE_OAUTH_API_URL` and `/oauth/handoff`. Full checklist: [PRODUCTION_TLS.md — Local OAuth](./PRODUCTION_TLS.md#local-oauth-development-vite--github).
- Verify setup: `./scripts/verify_oauth.py` (repo root, venv active).
- Production HTTPS, redirect URIs, and `AUTH_COOKIE_SECURE`: [PRODUCTION_TLS.md](./PRODUCTION_TLS.md).

