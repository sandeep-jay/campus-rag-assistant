#!/usr/bin/env python3
"""Docs hygiene check for Campus RAG Assistant.

Catches four categories of doc drift we cleaned up by hand:

1. Broken relative markdown links (file targets that no longer exist).
2. Broken anchor references (``foo.md#some-heading`` where the heading does
   not exist after MkDocs slugification).
3. "First-visit" docs that lapse into changelog framing -- version-suffixed
   headings or "What changed in vN" sections at the top level of a doc that
   reviewers hit first.
4. First-visit docs whose shared product introduction or capability placement
   drifts from the current review narrative.

Scope:

- Scans ``README.md`` and every ``.md`` under ``docs/`` from the repo root.
- Skips ``changelog/CHANGELOG.md`` and ``docs/changelog.md`` -- those are
  intentionally historical and reference paths that no longer exist.

Exit codes:

- 0 -- clean (warnings may print but do not fail the gate).
- 1 -- at least one broken link or anchor.

Run via ``tox -e docs`` (wired in tox.ini) or directly:

    python scripts/check_docs.py
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
HTML_ANCHOR_RE = re.compile(r'<a\s+(?:name|id)="([^"]+)"', re.IGNORECASE)

REPO_ROOT = Path(__file__).resolve().parent.parent

SKIP_FILES: set[Path] = {
    REPO_ROOT / "changelog" / "CHANGELOG.md",
    REPO_ROOT / "docs" / "changelog.md",
}

FIRST_VISIT_DOCS: tuple[Path, ...] = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "index.md",
    REPO_ROOT / "docs" / "ARCHITECTURE.md",
    REPO_ROOT / "docs" / "PORTFOLIO_CASE_STUDY.md",
    REPO_ROOT / "docs" / "REVIEWER_GUIDE.md",
    REPO_ROOT / "docs" / "helpdesk" / "index.md",
)

CHANGELOG_HEADING_PATTERNS = (
    re.compile(r"^What changed in v\d+", re.IGNORECASE),
    re.compile(r"^Diagram notes \(v\d+ vs v\d+\)", re.IGNORECASE),
    re.compile(r"^Overview \(v\d+\)$", re.IGNORECASE),
    re.compile(r"^Detailed \(v\d+\)$", re.IGNORECASE),
    re.compile(r"^Full topology \(v\d+\)$", re.IGNORECASE),
)

CANONICAL_LEDE = (
    "Campus RAG Assistant is a source-reviewable AI platform for governed campus "
    "knowledge. It pairs a cited-answer RAG path for routine questions with a "
    "bounded LangGraph helpdesk agent for what RAG cannot resolve, behind one "
    "FastAPI backend, one Vue 3 SPA, and a pluggable AWS / Azure / mock provider "
    "boundary."
)

CANONICAL_LEDE_DOCS: tuple[Path, ...] = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "index.md",
    REPO_ROOT / "docs" / "ARCHITECTURE.md",
    REPO_ROOT / "docs" / "PORTFOLIO_CASE_STUDY.md",
    REPO_ROOT / "docs" / "REVIEWER_GUIDE.md",
)
CANONICAL_LEDE_DOCS_RESOLVED = {p.resolve() for p in CANONICAL_LEDE_DOCS}

CAPABILITY_DOCS: tuple[Path, ...] = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "index.md",
    REPO_ROOT / "docs" / "PORTFOLIO_CASE_STUDY.md",
    REPO_ROOT / "docs" / "REVIEWER_GUIDE.md",
)
CAPABILITY_DOCS_RESOLVED = {p.resolve() for p in CAPABILITY_DOCS}


@dataclass(frozen=True)
class Finding:
    severity: str  # "error" | "warning"
    file: Path
    message: str


def slugify(text: str) -> str:
    """Approximate the MkDocs / python-markdown default heading slug."""
    text = text.lower().strip()
    text = re.sub(r"[`*_]+", "", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text


def normalize_ws(text: str) -> str:
    return " ".join(text.split())


def collect_anchors(path: Path) -> set[str]:
    if path.suffix.lower() != ".md" or not path.exists():
        return set()
    anchors: set[str] = set()
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return anchors
    for line in text.splitlines():
        stripped = line.strip()
        m = HEADING_RE.match(stripped)
        if m:
            anchors.add(slugify(m.group(2)))
        m2 = HTML_ANCHOR_RE.search(line)
        if m2:
            anchors.add(m2.group(1).lower())
    return anchors


def iter_markdown_files() -> list[Path]:
    files: list[Path] = [REPO_ROOT / "README.md"]
    files.extend(sorted((REPO_ROOT / "docs").rglob("*.md")))
    return [p for p in files if p.exists() and p not in SKIP_FILES]


def check_links(path: Path, anchor_cache: dict[Path, set[str]]) -> list[Finding]:
    findings: list[Finding] = []
    text = path.read_text(errors="ignore")
    for _label, target in LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "tel:", "#")):
            continue
        url_part, _, anchor = target.partition("#")
        url_part = unquote(url_part).split("?", 1)[0]
        if url_part.startswith("/"):
            continue
        try:
            resolved = (
                (path.resolve().parent / url_part).resolve()
                if url_part
                else path.resolve()
            )
        except OSError as exc:
            findings.append(
                Finding("error", path, f"link [{target}] could not resolve: {exc}")
            )
            continue
        try:
            resolved.relative_to(REPO_ROOT)
        except ValueError:
            continue
        if not resolved.exists():
            findings.append(
                Finding(
                    "error",
                    path,
                    f"link [{target}] points to missing file "
                    f"{resolved.relative_to(REPO_ROOT)}",
                )
            )
            continue
        if anchor and resolved.suffix.lower() == ".md":
            if resolved not in anchor_cache:
                anchor_cache[resolved] = collect_anchors(resolved)
            if anchor.lower() not in anchor_cache[resolved]:
                findings.append(
                    Finding(
                        "error",
                        path,
                        f"link [{target}] points to missing anchor #{anchor} "
                        f"in {resolved.relative_to(REPO_ROOT)}",
                    )
                )
    return findings


def check_changelog_framing(path: Path) -> list[Finding]:
    """Warn if a first-visit doc has top-level changelog-style headings.

    Headings inside MkDocs collapsible admonitions (``??? info "..."`` or
    ``???+ ...``) are indented with at least four spaces and are exempt -- the
    point is to flag *uncollapsed* changelog framing, not drill-down history.
    """
    findings: list[Finding] = []
    if path.resolve() not in {p.resolve() for p in FIRST_VISIT_DOCS}:
        return findings
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
        if line.startswith("    "):
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        heading_text = m.group(2).strip()
        for pat in CHANGELOG_HEADING_PATTERNS:
            if pat.match(heading_text):
                findings.append(
                    Finding(
                        "warning",
                        path,
                        f"line {lineno}: changelog-style heading "
                        f'"{heading_text}" -- keep current-state framing at top '
                        "level; move version history into a collapsible "
                        '"??? info" block.',
                    )
                )
                break
    return findings


def check_intro_consistency(path: Path) -> list[Finding]:
    """Keep first-visit docs aligned on the same product narrative."""
    findings: list[Finding] = []
    resolved = path.resolve()
    text = path.read_text(errors="ignore")
    normalized = normalize_ws(text)

    if resolved in CANONICAL_LEDE_DOCS_RESOLVED:
        if normalize_ws(CANONICAL_LEDE) not in normalized:
            findings.append(
                Finding(
                    "error",
                    path,
                    "missing canonical product lede; keep the first-visit "
                    "introduction aligned across README, docs index, reviewer "
                    "guide, case study, and architecture.",
                )
            )

    if resolved in CAPABILITY_DOCS_RESOLVED:
        if "## What this shows" not in text:
            findings.append(
                Finding(
                    "error",
                    path,
                    'missing "## What this shows" near the top of the doc.',
                )
            )
        if "| **Bounded helpdesk agent** |" not in text:
            findings.append(
                Finding(
                    "error",
                    path,
                    "missing bounded-helpdesk-agent row in the capability table; "
                    "the agent should stay visible in quick-review docs.",
                )
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Promote changelog-framing warnings to errors.",
    )
    args = parser.parse_args()

    anchor_cache: dict[Path, set[str]] = {}
    all_findings: list[Finding] = []
    files = iter_markdown_files()
    for path in files:
        all_findings.extend(check_links(path, anchor_cache))
        all_findings.extend(check_changelog_framing(path))
        all_findings.extend(check_intro_consistency(path))

    errors = [f for f in all_findings if f.severity == "error"]
    warnings = [f for f in all_findings if f.severity == "warning"]

    if warnings:
        print("Docs review -- warnings:", file=sys.stderr)
        for f in warnings:
            rel = f.file.relative_to(REPO_ROOT)
            print(f"  warn  {rel}: {f.message}", file=sys.stderr)
        print(file=sys.stderr)

    if errors:
        print("Docs review -- errors:", file=sys.stderr)
        for f in errors:
            rel = f.file.relative_to(REPO_ROOT)
            print(f"  err   {rel}: {f.message}", file=sys.stderr)
        print(file=sys.stderr)
        print(
            f"FAIL: {len(errors)} broken link(s), anchor(s), or intro "
            "consistency issue(s). Fix before opening the PR.",
            file=sys.stderr,
        )
        return 1

    if args.warnings_as_errors and warnings:
        print(
            f"FAIL: {len(warnings)} changelog-framing warning(s) and "
            "--warnings-as-errors was passed.",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: scanned {len(files)} markdown files -- "
        f"0 broken links, {len(warnings)} warning(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
