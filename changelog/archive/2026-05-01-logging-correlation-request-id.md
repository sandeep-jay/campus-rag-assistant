# 2026-05-01 — Logging: request correlation, JSON mode, auth log hygiene

> **Session / PR:** dev / working tree  
> **Commit range:** <!-- c9e4b4c..HEAD --> (logging-related paths and new files below)

## Summary

Aligned backend and Vue logging with an ops-friendly shape: **one request id per HTTP request**
(carried in logs and echoed as `X-Request-ID`), optional **JSON lines** for aggregators, and **quieter,
safer auth logs** (no JWT payload dumps at INFO). Logger startup is **explicit from `main`** (no
duplicate import-time init). **`LOGGING_PROPAGATION_LEVEL`** was removed as unused; **`LOG_JSON`**
replaces that knob in settings exports.

## Added

- **`backend/app/core/request_context.py`**: `RequestContextMiddleware` (validates or generates
  correlation id, sets contextvar), `RequestIdFilter` for `record.request_id`, `normalize_request_id`.
- **`LOG_JSON`** in `backend/app/config/default.py`: when true, `JsonFormatter` emits one JSON object
  per line (`timestamp`, `level`, `logger`, `message`, `request_id`, `exception` when present).
- **`backend/tests/core/test_request_context.py`**: normalization, filter + contextvar, middleware
  header behaviour via Starlette `TestClient`.
- **`scripts/kill-dev-servers.sh`**: terminate listeners on default dev ports **8000** / **5173**
  (override with `DEV_PORTS`).
- **`scripts/new-changelog.sh`**: creates `changelog/YYYY-MM-DD-<slug>.md` from `_template.md` with
  git `diff --stat` injection.

## Changed

- **`backend/app/core/logger.py`**: idempotent root setup + optional FastAPI logger attachment;
  `RequestIdFilter` on handlers; text format expects `%(request_id)s`; LangSmith/urllib3 handlers
  aligned; **`app` logger** propagates to root only (no duplicate handlers).
- **`backend/app/main.py`**: `initialize_logger()` before router/db logs; `initialize_logger(app)`
  after `FastAPI()`; **`RequestContextMiddleware`** registered after CORS (outermost); CORS
  **`expose_headers=['X-Request-ID']`**.
- **`backend/app/core/security.py`**: routine token/JWT tracing → **DEBUG**; **INFO** only for
  outcomes (`Authenticated user=…`); failures mostly **WARNING**; inline comment documenting policy.
- **`backend/app/config/default.py`**: default **`LOGGING_FORMAT`** includes `req=%(request_id)s`;
  **`LOG_JSON`**; removed **`LOGGING_PROPAGATION_LEVEL`**.
- **`backend/app/core/config_manager.py`**: export **`LOG_JSON`** instead of propagation level.
- **`.env.example`** / **`.env.test`**: logging format notes and optional **`LOG_JSON`** comment.
- **`frontend-vue/src/api/interceptors.ts`**: sets **`X-Request-ID`** (`crypto.randomUUID()`) per
  outgoing API request.

## Fixed

- **`tox -e lint`**: wrapped long comment in `security.py`; **`@pytest.fixture`** style per Ruff;
  **`ruff format`** on `default.py` and `request_context.py`.
- Restored truncated tail of **`backend/app/config/default.py`** (RAG/provider/`model_config`) after
  an earlier edit accident.

## Removed

- **`LOGGING_PROPAGATION_LEVEL`** from settings (was never wired to logger propagation).

## Security

- Auth path no longer logs **full JWT payloads** at INFO; reduces accidental claim leakage and log noise.

## Testing

- `backend/tests/core/test_request_context.py` (6 tests).
- `tests/api/test_auth.py` still green after security log changes.
- Full **`tox`** green after lint/format fixes.

## Files touched

**Tracked changes (subset — `git diff --stat HEAD`):**

```
 .env.example                       |  99 +++++++++++++++++-
 .env.test                          |   7 +-
 backend/app/config/default.py      |  96 +++++++++++++++++-
 backend/app/core/config_manager.py |   2 +-
 backend/app/core/logger.py         | 199 +++++++++++++++++++------------------
 backend/app/core/security.py       | 144 ++++++++++++++++++++++-----
 backend/app/main.py                | 104 ++++++++++++++++---
 7 files changed, 504 insertions(+), 147 deletions(-)
```

**New / previously untracked (add explicitly when committing):**

- `backend/app/core/request_context.py`
- `backend/tests/core/test_request_context.py`
- `frontend-vue/src/api/interceptors.ts` (and broader `frontend-vue/` if not yet committed)
- `scripts/kill-dev-servers.sh`
- `scripts/new-changelog.sh`
- `changelog/2026-05-01-logging-correlation-request-id.md` (this file)

## Notes / Follow-ups

- Ensure **`httpx`** stays aligned with Starlette **`TestClient`** (project pins **`httpx==0.27.2`** in
  `requirements.txt`).
- Optional: document **`X-Request-ID`** / **`LOG_JSON`** in `README.md` if operators need a pointer.
