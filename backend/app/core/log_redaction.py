"""Safe logging helpers — avoid PII and secrets in log lines at INFO."""

from __future__ import annotations

import hashlib


def query_log_preview(text: str, *, max_len: int = 80) -> str:
    """Summarize user text for INFO logs (length, hash, truncated preview)."""
    if not text:
        return 'len=0'
    normalized = text.strip().replace('\n', ' ')
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
    if len(normalized) <= max_len:
        preview = normalized
    else:
        preview = normalized[:max_len] + '…'
    return f'len={len(text)} sha256={digest} preview={preview!r}'


def jwt_subject_for_log(payload: dict | None) -> str:
    """Return JWT ``sub`` for logs — never log the full payload at INFO."""
    if payload is None:
        return '<invalid>'
    sub = payload.get('sub')
    return str(sub) if sub is not None else '<no-sub>'
