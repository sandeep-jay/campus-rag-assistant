#!/usr/bin/env bash
# new-changelog.sh — generate a pre-filled changelog draft for the current working session.
#
# Usage:
#   ./scripts/new-changelog.sh              # prompts for a slug
#   ./scripts/new-changelog.sh my-feature   # uses "my-feature" as the slug directly
#
# Output:
#   changelog/YYYY-MM-DD-<slug>.md   (created from changelog/_template.md)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHANGELOG_DIR="$REPO_ROOT/changelog"
TEMPLATE="$CHANGELOG_DIR/_template.md"

# ── Slug ─────────────────────────────────────────────────────────────────────
if [[ $# -ge 1 ]]; then
  SLUG="$1"
else
  printf "Changelog slug (e.g. add-caching, fix-auth-bug): "
  read -r SLUG
fi

# Sanitise: lowercase, spaces → hyphens, strip non-alphanumeric except hyphens
SLUG="$(echo "$SLUG" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')"

if [[ -z "$SLUG" ]]; then
  echo "Error: slug cannot be empty." >&2
  exit 1
fi

# ── File path ─────────────────────────────────────────────────────────────────
DATE="$(date +%Y-%m-%d)"
OUTFILE="$CHANGELOG_DIR/${DATE}-${SLUG}.md"

if [[ -f "$OUTFILE" ]]; then
  echo "File already exists: $OUTFILE"
  printf "Overwrite? [y/N] "
  read -r CONFIRM
  [[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

# ── Build draft ───────────────────────────────────────────────────────────────
# Start from template, replace date/title placeholders
sed \
  -e "s/YYYY-MM-DD/${DATE}/g" \
  -e "s/<short title>/${SLUG}/g" \
  "$TEMPLATE" > "$OUTFILE"

# Inject last-commit hash for the commit-range line
LAST_COMMIT="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
sed -i.bak "s|<git diff --stat HEAD output here>|$(
  git -C "$REPO_ROOT" diff --stat HEAD 2>/dev/null \
    | sed 's/|/\\|/g' \
    | sed 's/\//\\\//g'
)|" "$OUTFILE" 2>/dev/null || true
rm -f "${OUTFILE}.bak"

# Replace the commit-range placeholder properly
python3 - "$OUTFILE" "$LAST_COMMIT" << 'PY'
import sys, subprocess, pathlib

outfile = pathlib.Path(sys.argv[1])
last_commit = sys.argv[2]

# Get clean git diff --stat output
try:
    diff_stat = subprocess.check_output(
        ["git", "diff", "--stat", "HEAD"],
        cwd=outfile.parent.parent,
        text=True,
    )
except Exception:
    diff_stat = "(git diff --stat failed — run manually)"

content = outfile.read_text()

# Replace commit range placeholder
content = content.replace(
    "<!-- e.g. c9e4b4c..HEAD -->",
    f"<!-- {last_commit}..HEAD -->",
)

# Replace the files-touched block
placeholder = "<git diff --stat HEAD output here>"
if placeholder in content:
    content = content.replace(placeholder, diff_stat.rstrip())

outfile.write_text(content)
PY

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "Created: $OUTFILE"
echo ""
echo "Next steps:"
echo "  1. Fill in the Summary and relevant sections"
echo "  2. Delete any sections that do not apply"
echo "  3. Fold the summary into CHANGELOG.md [Unreleased]"
echo "  4. Commit CHANGELOG.md alongside your code changes"
echo ""

# Open in editor if available
if [[ -n "${EDITOR:-}" ]]; then
  "$EDITOR" "$OUTFILE"
elif command -v code &>/dev/null; then
  code "$OUTFILE"
fi
