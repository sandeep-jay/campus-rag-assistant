"""Lightweight secret/PII redaction used before sending conversation text to the summarizer agent or to GitHub.

This is intentionally conservative — false positives are preferable to leaking
credentials into an LLM prompt or a public-ish issue tracker. Callers should
still display a "review for sensitive info" warning in the UI before submit.
"""

from __future__ import annotations

import re

EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
JWT_LIKE = re.compile(r'\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b')
AWS_ACCESS_KEY = re.compile(r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b')
GITHUB_TOKEN = re.compile(r'\bgh[poursa]_[A-Za-z0-9]{20,}\b')
GENERIC_BEARER = re.compile(r'(?i)bearer\s+[A-Za-z0-9._\-]{12,}')
# Catches `password=...`, `api_key: ...`, `token = ...` (last-resort).
KEYED_SECRET = re.compile(r'(?i)\b(password|passwd|secret|api[_-]?key|token|authorization)\b\s*[:=]\s*[^\s,;]{6,}')

REPLACEMENT = '[REDACTED]'


def redact_text(text: str) -> str:
    """Replace likely secrets with a marker. Idempotent on already-redacted text."""
    if not text:
        return text
    redacted = text
    for pattern in (JWT_LIKE, AWS_ACCESS_KEY, GITHUB_TOKEN, GENERIC_BEARER):
        redacted = pattern.sub(REPLACEMENT, redacted)
    redacted = KEYED_SECRET.sub(
        lambda m: f'{m.group(1)}={REPLACEMENT}',
        redacted,
    )
    return EMAIL.sub(REPLACEMENT, redacted)


def redact_conversation(turns: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return a new list of turns with content redacted."""
    return [{'role': t.get('role', ''), 'content': redact_text(t.get('content', ''))} for t in turns]
