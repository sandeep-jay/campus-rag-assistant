#!/usr/bin/env bash
# Vue dev server (Node 18+; Node 20 recommended — see frontend-vue/.nvmrc).
# Usage: from repo root: ./scripts/run-frontend-vue.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend-vue"

if [ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "${NVM_DIR:-$HOME/.nvm}/nvm.sh"
  [ -f ".nvmrc" ] && nvm use 2>/dev/null || true
fi

echo "Starting Vite on http://127.0.0.1:5173/"
exec npm run dev
