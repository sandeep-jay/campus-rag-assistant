# Load Validation

## Goal

Validate backend behavior for **100 active users** with realistic auth + session + chat traffic.

## Before you run k6 (canonical order)

Do these steps **every time** you use a fresh `chatbot_test` database or hit **401** on login during load:

1. **Start the load-test backend** (test DB + `APP_ENV=test`), from repo root:

   ```bash
   ./scripts/run-backend-loadtest.sh
   ```

   Defaults to **multiple uvicorn workers** (`UVICORN_WORKERS`, default `4`) so bcrypt and chat do not saturate one process. Use `UVICORN_WORKERS=1` if you need `--reload` for local debugging.

2. **Confirm health and environment**:

   ```bash
   curl -s http://127.0.0.1:8000/api/health
   ```

   Expect `"status":"ok"` and **`"app_env":"test"`**. If `app_env` is not `test`, k6 aborts unless you set `K6_ALLOW_NON_TEST_BACKEND=1`.

3. **Seed accounts** from [`load-tests/users.json`](../load-tests/users.json) (idempotent — safe to re-run):

   ```bash
   BASE_URL=http://127.0.0.1:8000 python3 load-tests/seed_users.py
   ```

   Missing users cause **`401 Unauthorized`** on `/api/auth/login-json` for VUs assigned to usernames that were never registered.

4. **Point k6 at the same origin**:

   ```bash
   export BASE_URL=http://127.0.0.1:8000   # must match seed_users BASE_URL
   ```

5. **Run smoke first**, then the full ramp when smoke is green (see below).

6. **Interpret results**: Smoke prioritizes **correctness** (checks, low `http_req_failed`) and **phase-aware latency** (tight auth/session, coarse chat when using real LLM+RAG). See [Smoke thresholds](#smoke-thresholds-and-performance).

## Tooling

- Smoke: [`load-tests/k6-smoke.js`](../load-tests/k6-smoke.js)
- Full ramp: [`load-tests/k6-auth-chat-session.js`](../load-tests/k6-auth-chat-session.js)
- User fixture: [`load-tests/users.json`](../load-tests/users.json)
- Seed: [`load-tests/seed_users.py`](../load-tests/seed_users.py)

## Prerequisites (reference)

**Guard:** k6 aborts unless `GET /api/health` reports `app_env: "test"` when `./scripts/run-backend-loadtest.sh` is used (`.env.test` / `chatbot_test`). To intentionally hit a non-test backend, export `K6_ALLOW_NON_TEST_BACKEND=1`.

- Postgres reachable with enough connections for **`chatbot_test`** (or `POSTGRES_DB` from `.env.test`).
- k6 installed locally (`brew install k6` on macOS).

## Execute staged load test

```bash
k6 run --env BASE_URL=http://127.0.0.1:8000 load-tests/k6-auth-chat-session.js
```

The default scenario ramps to 100 VUs, sustains, then ramps down.

## Smoke first (5 VUs, ~45s)

```bash
tox -e load-smoke
# or:
k6 run --env BASE_URL=http://127.0.0.1:8000 load-tests/k6-smoke.js
```

### Smoke thresholds and performance

Smoke is tuned for **correctness first**, then **latency by phase**:

- **`http_req_failed`**: keep low (`rate<0.15` in the script).
- **`checks{phase:auth}` / `checks{phase:chat}`**: login/session/chat behavior must pass at high rates (see script).
- **Latency**: requests are tagged `phase: auth | session | chat`. Thresholds are **strict for auth and session** (app + DB + bcrypt) and **coarse for chat** because embeddings, search, and LLM calls dominate and vary with **Azure quotas and retries**.

If you need CI smoke with **sub-second chat p95**, run against **mock/minimal LLM** in `APP_ENV=test` or maintain a separate profile — do not expect real GPT+RAG to meet API-only SLOs.

## Full ramp (~100 VUs)

### Stress readiness checklist

Before the ~12 minute ramp:

1. **Azure capacity**: Confirm quota / TPM–RPM for the OpenAI deployment and Search tier referenced from `.env.test`. Concurrent chat produces **429 Too Many Requests**; SDK retries inflate tail latency.
2. **Backend process**: Run [`scripts/run-backend-loadtest.sh`](../scripts/run-backend-loadtest.sh) with default **`UVICORN_WORKERS`** (multi-worker UVicorn, **no `--reload`**). Use `UVICORN_WORKERS=1` only for short debugging runs.
3. **Accounts**: Run [`load-tests/seed_users.py`](../load-tests/seed_users.py) so every username in [`users.json`](../load-tests/users.json) exists (missing rows → **401** on login-json).
4. **Smoke first**: [`k6-smoke.js`](../load-tests/k6-smoke.js) should be green against the same `BASE_URL`.
5. **During the run**:
   - Tail logs for **`429`**, **`Too Many Requests`**, or **`Retrying request`** on `/chat/completions` (or equivalent provider lines).
   - Ensure Postgres **`max_connections`** comfortably exceeds **`SQLALCHEMY_POOL_SIZE` × worker count** plus admin / migration connections.

### Stress latency profile (`K6_LATENCY_PROFILE`)

[`k6-auth-chat-session.js`](../load-tests/k6-auth-chat-session.js) chooses thresholds from `K6_LATENCY_PROFILE`:

| Profile | Use case | Latency gates |
|---------|-----------|----------------|
| **`live`** (default) | Real Azure (or other remote) LLM + retriever | Phase-tagged HTTP caps: auth/session tight, chat **p(95) < 45s** (handles retries under ramp). |
| **`mock`** | Mock / fast providers | Global **`http_req_duration`**: **p(95) < 1200ms**, **p(99) < 2500ms** (legacy strict SLO). |

```bash
tox -e load-stress
# same as default live profile:
K6_LATENCY_PROFILE=live tox -e load-stress

K6_LATENCY_PROFILE=mock tox -e load-stress
k6 run --env BASE_URL=http://127.0.0.1:8000 --env K6_LATENCY_PROFILE=mock load-tests/k6-auth-chat-session.js
```

### Mock backend for strict latency SLOs

For repeatable CI-style runs without cloud variance, configure the **load-test** backend (`.env.test`) with mock providers, for example:

- `LLM_PROVIDER=mock`
- `RETRIEVER_PROVIDER=mock`
- Optionally `RAG_FORCE_MOCK=true`

See [`.env.example`](../.env.example) for field names. Then run stress with **`K6_LATENCY_PROFILE=mock`** (commands under **Stress latency profile** above) so k6’s strict thresholds match the fast stack.
## Expected output signals (summary)

| Profile | What to watch |
|--------|----------------|
| **Smoke** | Auth/chat checks near 100%; `http_req_failed` low; auth/session **p95** bounded tightly; chat **p95** allows tens of seconds when using live LLM+RAG. |
| **Full ramp (`live`)** | Same checks; phase-split latency; watch **429/retry** noise and DB saturation as VUs climb. |
| **Full ramp (`mock`)** | Sub-second **p95** global HTTP latency when the API is mock-backed; still watch `http_req_failed`. |

## Tuning guidance from results

- If CPU saturated and DB usage low: increase uvicorn **`UVICORN_WORKERS`** in [`scripts/run-backend-loadtest.sh`](../scripts/run-backend-loadtest.sh) moderately.
- If DB pool usage ratio > 0.85: increase `SQLALCHEMY_POOL_SIZE` and DB max connections, or reduce workers.
- If provider latency dominates: tune `PROVIDER_TIMEOUT_SECONDS`, retries, and circuit breaker settings; ensure quotas fit the ramp.
- If long-tail latency spikes: lower `CHAT_HISTORY_MAX_MESSAGES` and reduce per-request payload size.
