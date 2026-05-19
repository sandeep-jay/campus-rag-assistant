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

## OAuth and local development

- Enable providers in `.env`: `OAUTH_ENABLED_PROVIDERS=github` (or `google,github`) plus client ID/secret vars (see `.env.example`).
- **Browser URL, `FRONTEND_URL`, and `OAUTH_REDIRECT_BASE_URL` must use the same host** (e.g. all `127.0.0.1`, not `localhost` mixed with `127.0.0.1`) or OAuth state cookies will not match (`MismatchingStateError`).
- Vue dev server defaults to `http://127.0.0.1:5173` (`frontend-vue/vite.config.ts`). GitHub OAuth app callback: `http://127.0.0.1:5173/api/auth/oauth/github/callback` (proxied to the API).
- Verify setup: `./scripts/verify_oauth.py` (from repo root with venv active).
- Production HTTPS, redirect URIs, and `AUTH_COOKIE_SECURE`: [PRODUCTION_TLS.md](./PRODUCTION_TLS.md).

