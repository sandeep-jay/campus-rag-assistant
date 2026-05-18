#!/usr/bin/env bash
# Backend API bound to the **test** Postgres DB (repo-root `.env.test`).
# Start this before k6 / tox load-smoke / load-stress so load traffic does not touch `chatbot_dev`.
#
# Usage (from repo root): ./scripts/run-backend-loadtest.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found" >&2
  exit 1
fi

if [ ! -d "venv" ]; then
  echo "Creating venv at $ROOT/venv ..."
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

if [ "${PIP_SYNC:-1}" = "1" ]; then
  pip install -q -r requirements.txt
fi

ENV_FILE="$ROOT/.env.test"
if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE — create it for POSTGRES_* / chatbot_test." >&2
  exit 1
fi

eval "$(ROOT="$ROOT" python3 <<'PY'
import os
import shlex
from pathlib import Path

from dotenv import dotenv_values

root = Path(os.environ["ROOT"])
vals = {k: v for k, v in dotenv_values(root / ".env.test").items() if v not in (None, "")}
vals["APP_ENV"] = "test"
user = vals.get("POSTGRES_USER", "chatbot")
password = vals.get("POSTGRES_PASSWORD", "chatbot")
host = vals.get("POSTGRES_HOST", "localhost")
port = vals.get("POSTGRES_PORT", "5432")
db = vals.get("POSTGRES_DB", "chatbot_test")
vals["DATABASE_URL"] = f"postgresql://{user}:{password}@{host}:{port}/{db}"
for key, val in vals.items():
    print(f"export {key}={shlex.quote(str(val))}")
PY
)"

HOST="${API_HOST:-127.0.0.1}"
PORT="${API_PORT:-8000}"
# bcrypt-heavy concurrent logins + chat saturate a single worker; default multi-worker load serving.
WORKERS="${UVICORN_WORKERS:-4}"

echo "Starting uvicorn (APP_ENV=test, test DB) on http://${HOST}:${PORT}"
COMMON_ARGS=(backend.app.main:app --host "$HOST" --port "$PORT")
if [ "${WORKERS}" = "1" ]; then
  exec uvicorn "${COMMON_ARGS[@]}" --reload --reload-dir backend/app
fi

echo "Workers=${WORKERS} (set UVICORN_WORKERS=1 for reload/dev-style single worker)."
exec uvicorn "${COMMON_ARGS[@]}" --workers "${WORKERS}"
