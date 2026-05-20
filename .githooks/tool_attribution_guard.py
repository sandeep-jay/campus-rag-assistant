#!/usr/bin/env python3
"""tool_attribution_guard — sanitize commit messages.

Strips lines/blocks that attribute authorship or generation to AI coding
assistants or editors. Designed to be invoked from a Git ``commit-msg`` hook
so the resulting commit history stays vendor-neutral and reviewable.

Usage:
    python3 tool_attribution_guard.py <path-to-commit-msg-file>

The script edits the file in place. It is idempotent and conservative:
only lines matching documented patterns are removed. Anything else
(including legitimate ``Co-authored-by:`` lines for human collaborators)
is preserved.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Vendor/tool keywords that should not appear as authorship in commits.
# Add new tools here; keep entries lowercase.
_TOOL_KEYWORDS = (
    "cursor",
    "cursoragent",
    "cursor-agent",
    "claude",
    "anthropic",
    "copilot",
    "github copilot",
    "codex",
    "openai",
    "chatgpt",
    "gemini",
    "bard",
    "devin",
    "aider",
    "cody",
    "windsurf",
    "tabnine",
)

_TOOLS_ALT = "|".join(re.escape(k) for k in _TOOL_KEYWORDS)

# Line-level patterns. Each must match the full stripped line (case-insensitive).
_LINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "Co-authored-by: <name> <email>" where name or email mentions a tool.
    re.compile(
        rf"^co-authored-by:\s*.*(?:{_TOOLS_ALT}).*$",
        re.IGNORECASE,
    ),
    # "Signed-off-by: <tool>" / "Generated-by: <tool>" style attribution.
    re.compile(
        rf"^(?:signed-off-by|reviewed-by|assisted-by|generated-by|authored-by):\s*.*(?:{_TOOLS_ALT}).*$",
        re.IGNORECASE,
    ),
    # Marketing footers like "Made with [Cursor](https://cursor.com)" or "Made with Cursor".
    re.compile(
        rf"^\s*made\s+with\s+\[?(?:{_TOOLS_ALT})\b.*$",
        re.IGNORECASE,
    ),
    # "Generated/Created/Powered with/by <tool>".
    re.compile(
        rf"^\s*(?:generated|created|written|drafted|composed|powered)\s+(?:with|by)\s+\[?(?:{_TOOLS_ALT})\b.*$",
        re.IGNORECASE,
    ),
    # Attribution lines that link to a vendor URL (cursor.com, anthropic.com, openai.com, etc.).
    re.compile(
        rf"^\s*(?:made|generated|created|written|powered)\s+.*https?://(?:[a-z0-9.-]+\.)?(?:{_TOOLS_ALT})[a-z0-9./?#=&_-]*.*$",
        re.IGNORECASE,
    ),
)


def sanitize(text: str) -> str:
    """Return ``text`` with any tool-attribution lines removed."""

    kept: list[str] = []
    for raw in text.splitlines(keepends=True):
        stripped = raw.strip()
        if any(pat.match(stripped) for pat in _LINE_PATTERNS):
            continue
        kept.append(raw)

    # Collapse trailing blank lines introduced by stripped footers.
    while len(kept) >= 2 and kept[-1].strip() == "" and kept[-2].strip() == "":
        kept.pop()
    cleaned = "".join(kept).rstrip() + ("\n" if text.endswith("\n") else "")
    return cleaned


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0  # Nothing to do; behave like a no-op for safety.
    path = Path(argv[1])
    if not path.is_file():
        return 0
    original = path.read_text()
    cleaned = sanitize(original)
    if cleaned != original:
        path.write_text(cleaned)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
