#!/usr/bin/env bash
# install-hooks.sh — wire Git hooks for this repo and (optionally) for the
# current user globally.
#
# Usage:
#   ./scripts/install-hooks.sh           # point this repo at .githooks/
#   ./scripts/install-hooks.sh --global  # also install global hooks under
#                                        # ~/.config/git/hooks so every repo
#                                        # gets the same protections.
#
# Local repo hooks (this repo's .githooks/) win over global because Git
# resolves the local config first.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

install_local() {
  git -C "$REPO_ROOT" config core.hooksPath .githooks
  echo "Local hooks installed (core.hooksPath=.githooks). Active hooks:"
  ls "$REPO_ROOT/.githooks/"
}

install_global() {
  local target="${HOME}/.config/git/hooks"
  mkdir -p "$target"

  # tool_attribution_guard.py — strips AI-tool attribution from commit msgs.
  cp "$REPO_ROOT/.githooks/tool_attribution_guard.py" "$target/tool_attribution_guard.py"
  chmod +x "$target/tool_attribution_guard.py"

  # commit-msg — delegates to the guard.
  cat > "$target/commit-msg" <<'HOOK'
#!/usr/bin/env bash
# commit-msg (global) — delegate to tool_attribution_guard.
set -euo pipefail
MSG_FILE="${1:-}"
[[ -z "$MSG_FILE" || ! -f "$MSG_FILE" ]] && exit 0
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD="$HOOK_DIR/tool_attribution_guard.py"
[[ -x "$GUARD" ]] || exit 0
python3 "$GUARD" "$MSG_FILE"
HOOK
  chmod +x "$target/commit-msg"

  # pre-push — runs gitleaks on the commits being pushed. No-op (warn only)
  # if gitleaks isn't installed; CI still enforces the same check.
  cp "$REPO_ROOT/.githooks/pre-push" "$target/pre-push"
  chmod +x "$target/pre-push"

  git config --global core.hooksPath "$target"
  echo "Global hooks installed at: $target"
  echo "global core.hooksPath: $(git config --global --get core.hooksPath)"

  if ! command -v gitleaks >/dev/null 2>&1; then
    echo
    echo "NOTE: 'gitleaks' is not installed. The pre-push hook will skip the"
    echo "      secret scan until you install it:"
    echo "        macOS : brew install gitleaks"
    echo "        Linux : apt-get install gitleaks  (or download the binary)"
  fi
}

case "${1:-}" in
  --global) install_local; install_global ;;
  "")       install_local ;;
  *)        echo "unknown flag: $1" >&2; exit 2 ;;
esac
