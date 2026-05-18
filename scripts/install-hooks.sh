#!/usr/bin/env bash
# install-hooks.sh — point Git to the committed hook scripts in .githooks/
# Run once after cloning:
#   ./scripts/install-hooks.sh

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
git -C "$REPO_ROOT" config core.hooksPath .githooks
echo "Git hooks installed. Active hooks:"
ls "$REPO_ROOT/.githooks/"
