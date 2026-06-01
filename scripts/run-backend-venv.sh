#!/usr/bin/env bash
# FastAPI backend with a local Python virtualenv (repo-root ./venv).
# Usage: from repo root: ./scripts/run-backend-venv.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DOCKER_COMPOSE_ENV_FILE="${DOCKER_COMPOSE_ENV_FILE:-/dev/null}"

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

if [ "${SKIP_DOCKER_DB:-0}" != "1" ]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found. Install Docker Desktop or set SKIP_DOCKER_DB=1 to use an existing Postgres." >&2
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "docker compose not available. Install Docker Compose v2 or set SKIP_DOCKER_DB=1." >&2
    exit 1
  fi

  echo "Ensuring Docker Postgres service is running ..."
  docker compose --env-file "$DOCKER_COMPOSE_ENV_FILE" up -d db

  container_id="$(docker compose --env-file "$DOCKER_COMPOSE_ENV_FILE" ps -q db)"
  for _ in {1..30}; do
    if [ -n "$container_id" ] && [ "$(docker inspect --format '{{.State.Health.Status}}' "$container_id" 2>/dev/null || true)" = "healthy" ]; then
      break
    fi
    sleep 1
  done

  if [ -z "$container_id" ] || [ "$(docker inspect --format '{{.State.Health.Status}}' "$container_id" 2>/dev/null || true)" != "healthy" ]; then
    echo "Docker Postgres did not become healthy. Check 'docker compose --env-file $DOCKER_COMPOSE_ENV_FILE logs db'." >&2
    exit 1
  fi

  if command -v lsof >/dev/null 2>&1; then
    non_docker_5432_listeners="$(
      lsof -nP -iTCP:5432 -sTCP:LISTEN 2>/dev/null \
        | awk 'NR > 1 && $1 !~ /^com\.docke/ && $1 !~ /^docker/ { print }'
    )"
    if [ -n "$non_docker_5432_listeners" ]; then
      echo "Port 5432 is also owned by a non-Docker process; stop it or set SKIP_DOCKER_DB=1." >&2
      echo "$non_docker_5432_listeners" >&2
      exit 1
    fi
  fi
else
  echo "Skipping Docker Postgres startup because SKIP_DOCKER_DB=1."
fi

echo "Starting uvicorn on http://127.0.0.1:8000 (venv active)"
exec ./venv/bin/python -m uvicorn backend.app.main:app --reload --reload-dir backend/app --host 127.0.0.1 --port 8000
