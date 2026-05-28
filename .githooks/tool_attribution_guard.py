#!/usr/bin/env python3
"""tool_attribution_guard — sanitize commit messages.

Strips lines/blocks that attribute authorship or generation to AI coding
assistants or editors. Designed to be invoked from a Git ``commit-msg`` hook
so the resulting commit history stays vendor-neutral and reviewable.

Usage:
    python3 tool_attribution_guard.py <path-to-commit-msg-file>
    python3 tool_attribution_guard.py --check <path> [<path> ...]

Without ``--check``, the script edits one commit-message file in place. In
``--check`` mode, it scans one or more files and exits non-zero if any
attribution line is found. The matching is conservative: legitimate
``Co-authored-by:`` lines for human collaborators are preserved.
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
    # Standalone vendor identities that can be pasted into PR descriptions.
    re.compile(
        r"^.*(?:cursoragent@cursor\.com|https?://(?:www\.)?(?:cursor|anthropic|openai)\.com).*$",
        re.IGNORECASE,
    ),
)


def is_tool_attribution_line(line: str) -> bool:
    """Return whether ``line`` attributes authorship to an AI tool."""

    stripped = line.strip()
    return any(pat.match(stripped) for pat in _LINE_PATTERNS)


def find_tool_attribution_lines(text: str) -> list[tuple[int, str]]:
    """Return ``(line_number, line)`` pairs for tool-attribution lines."""

    return [
        (line_number, line)
        for line_number, line in enumerate(text.splitlines(), 1)
        if is_tool_attribution_line(line)
    ]


def sanitize(text: str) -> str:
    """Return ``text`` with any tool-attribution lines removed."""

    kept: list[str] = []
    for raw in text.splitlines(keepends=True):
        if is_tool_attribution_line(raw):
            continue
        kept.append(raw)

    # Collapse trailing blank lines introduced by stripped footers.
    while len(kept) >= 2 and kept[-1].strip() == "" and kept[-2].strip() == "":
        kept.pop()
    cleaned = "".join(kept).rstrip() + ("\n" if text.endswith("\n") else "")
    return cleaned


def check_paths(paths: list[Path]) -> int:
    """Print findings for ``paths`` and return a process exit status."""

    found = False
    for path in paths:
        if not path.is_file():
            continue
        for line_number, line in find_tool_attribution_lines(path.read_text()):
            found = True
            print(f"{path}:{line_number}: tool attribution: {line}", file=sys.stderr)
    return 1 if found else 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0  # Nothing to do; behave like a no-op for safety.

    if argv[1] == "--check":
        return check_paths([Path(arg) for arg in argv[2:]])

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
