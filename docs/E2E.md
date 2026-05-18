# End-to-end tests (Playwright)

Playwright lives under [`frontend-vue/e2e/`](../frontend-vue/e2e/). Tests assume:

1. **API** is running and reachable at **`http://127.0.0.1:8000`** (default).
2. **Vite dev server** is started by Playwright (`webServer` in `playwright.config.ts`), unless `CI` reuse rules apply.

## Prerequisites

- PostgreSQL available for the backend (same as normal app startup).
- Backend serving routes including `/api/health` and `/api/auth/register`.
- Migrations must be applied before backend start: `alembic upgrade head`.

## Running locally

Terminal 1 — backend (example):

```bash
./scripts/run-backend-venv.sh
# or: uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — E2E:

```bash
cd frontend-vue
npm run e2e
```

## Global setup

[`frontend-vue/e2e/global-setup.ts`](../frontend-vue/e2e/global-setup.ts) waits for **`GET /api/health`** before registering a throwaway user and saving cookie state to `e2e/.auth/user.json`.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `PLAYWRIGHT_API_BASE_URL` | API base URL (default `http://127.0.0.1:8000`) |

## CI

For CI, run Postgres + migrations (if any) + backend **before** `npm run e2e`, or start the API as a service step. The health wait reduces flakes but does not replace a running API.
