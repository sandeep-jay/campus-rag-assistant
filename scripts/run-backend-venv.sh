#!/usr/bin/env bash
# FastAPI backend with a local Python virtualenv (repo-root ./venv).
# Usage: from repo root: ./scripts/run-backend-venv.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.11+ and retry." >&2
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

echo "Starting uvicorn on http://127.0.0.1:8000 (venv active)"
exec ./venv/bin/python -m uvicorn backend.app.main:app --reload --reload-dir backend/app --host 127.0.0.1 --port 8000
