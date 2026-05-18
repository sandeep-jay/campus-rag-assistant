#!/usr/bin/env bash
# kill-dev-servers.sh — stop local dev listeners for this repo (FastAPI + Vite defaults).
#
# Usage (from repo root):
#   ./scripts/kill-dev-servers.sh
#
# Override ports (space-separated):
#   DEV_PORTS="8000 5173 3000" ./scripts/kill-dev-servers.sh

set -euo pipefail

PORTS="${DEV_PORTS:-8000 5173}"

for port in $PORTS; do
  pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    echo "Stopping PID(s) on :${port}: ${pids}"
    kill ${pids} 2>/dev/null || true
    sleep 1
    kill -9 ${pids} 2>/dev/null || true
  else
    echo "Nothing listening on :${port}"
  fi
done

echo "Done."
