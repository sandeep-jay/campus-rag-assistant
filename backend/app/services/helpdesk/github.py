"""GitHub issue client for helpdesk escalation.

- Uses httpx.AsyncClient with a short timeout.
- Accepts an optional transport so tests can inject ``httpx.MockTransport``.
- Server-side idempotency: a short-lived in-process cache keyed by
  (user_id, sha256(title + description prefix)) returns the prior issue
  without re-filing on retry. This is intentionally process-local — sufficient
  for the demo; replace with Redis if running multi-process.
- Token is held as ``SecretStr`` in settings and unwrapped only at the call
  site. The token is never logged.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

import httpx
from fastapi import HTTPException, status

from backend.app.core.config_manager import settings
from backend.app.core.metrics import HELPDESK_CREATE_ISSUE_TOTAL
from backend.app.schemas.helpdesk import CreateIssueResponse, TicketDraft

logger = logging.getLogger(__name__)


def _format_body(draft: TicketDraft) -> str:
    body = (
        '## Problem Description\n'
        f'{draft.description}\n\n'
        '## Details\n'
        '| Field | Value |\n'
        '|---|---|\n'
        f'| Severity | {draft.severity.value} |\n'
        f'| Category | {draft.category.value} |\n'
        f'| Impact | {draft.impact.value} |\n'
    )
    if draft.steps_to_reproduce:
        body += f'\n## Steps to Reproduce\n{draft.steps_to_reproduce}\n'
    body += '\n---\n*Filed via Campus RAG Assistant Helpdesk. Review for sensitive info.*'
    return body


def _labels(draft: TicketDraft) -> list[str]:
    extra = [lbl.strip() for lbl in (settings.GITHUB_DEFAULT_LABELS or '').split(',') if lbl.strip()]
    return list(dict.fromkeys([draft.severity.value, draft.category.value, *extra]))


@dataclass
class _DedupEntry:
    issue_url: str
    issue_number: int
    expires_at: float


class _DedupCache:
    """In-process TTL cache keyed by (user_id, draft hash)."""

    def __init__(self) -> None:
        self._store: dict[str, _DedupEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> _DedupEntry | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.time():
                self._store.pop(key, None)
                return None
            return entry

    def put(self, key: str, value: _DedupEntry) -> None:
        with self._lock:
            self._store[key] = value
            # Opportunistic cleanup
            now = time.time()
            stale = [k for k, v in self._store.items() if v.expires_at < now]
            for k in stale:
                self._store.pop(k, None)


_dedup_cache = _DedupCache()


def _dedup_key(user_id: int | str, draft: TicketDraft) -> str:
    fingerprint = f'{draft.title.strip()}|{draft.description.strip()[:200]}'
    digest = hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()
    return f'{user_id}:{digest}'


def _require_settings() -> tuple[str, str]:
    token_secret = settings.GITHUB_TOKEN
    repo = settings.GITHUB_REPO
    if not token_secret or not repo:
        HELPDESK_CREATE_ISSUE_TOTAL.labels(outcome='disabled').inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Helpdesk is enabled but GITHUB_TOKEN/GITHUB_REPO are not configured.',
        )
    return token_secret.get_secret_value(), repo


async def create_github_issue(
    draft: TicketDraft,
    *,
    user_id: int | str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> CreateIssueResponse:
    """Create a GitHub issue from a reviewed ticket draft.

    Idempotency: repeated calls with the same (user_id, draft fingerprint)
    within ``HELPDESK_DEDUP_WINDOW_SECONDS`` return the previously created
    issue without contacting GitHub again.
    """
    token, repo = _require_settings()

    cache_key = _dedup_key(user_id, draft)
    cached = _dedup_cache.get(cache_key)
    if cached is not None:
        HELPDESK_CREATE_ISSUE_TOTAL.labels(outcome='deduplicated').inc()
        return CreateIssueResponse(
            issue_url=cached.issue_url,
            issue_number=cached.issue_number,
            deduplicated=True,
        )

    payload: dict[str, Any] = {
        'title': draft.title,
        'body': _format_body(draft),
        'labels': _labels(draft),
    }
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'campus-rag-assistant-helpdesk',
    }

    async with httpx.AsyncClient(timeout=10.0, transport=transport) as client:
        try:
            response = await client.post(
                f'https://api.github.com/repos/{repo}/issues',
                headers=headers,
                json=payload,
            )
        except httpx.HTTPError as exc:
            HELPDESK_CREATE_ISSUE_TOTAL.labels(outcome='github_error').inc()
            logger.exception('GitHub issue creation failed (network): %s', exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Failed to reach GitHub. Please try again later.',
            ) from exc

    if response.status_code >= 400:
        HELPDESK_CREATE_ISSUE_TOTAL.labels(outcome='github_error').inc()
        # Pull the API's own ``message`` (and ``errors[*].message`` when
        # available) into the surfaced detail so the modal toast tells the
        # user what GitHub actually objected to (auth scope, validation,
        # rate limit, etc.) rather than just an opaque 502.
        github_detail = ''
        try:
            payload_err = response.json()
        except ValueError:
            payload_err = None
        if isinstance(payload_err, dict):
            msg = payload_err.get('message')
            if isinstance(msg, str) and msg.strip():
                github_detail = msg.strip()
            sub_errors = payload_err.get('errors')
            if isinstance(sub_errors, list) and sub_errors:
                fragments = [str(item.get('message') or item.get('code') or '').strip() for item in sub_errors if isinstance(item, dict)]
                fragments = [f for f in fragments if f]
                if fragments:
                    github_detail = f'{github_detail}: {"; ".join(fragments)}' if github_detail else '; '.join(fragments)
        logger.error(
            'GitHub issue creation failed: status=%s repo=%s detail=%s',
            response.status_code,
            repo,
            github_detail or '(none)',
        )
        detail = f'GitHub API rejected the issue (status {response.status_code}).'
        if github_detail:
            detail = f'{detail} {github_detail}'
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    data = response.json()
    issue_url = data.get('html_url') or ''
    issue_number = int(data.get('number') or 0)

    _dedup_cache.put(
        cache_key,
        _DedupEntry(
            issue_url=issue_url,
            issue_number=issue_number,
            expires_at=time.time() + max(0, settings.HELPDESK_DEDUP_WINDOW_SECONDS),
        ),
    )

    HELPDESK_CREATE_ISSUE_TOTAL.labels(outcome='success').inc()
    return CreateIssueResponse(
        issue_url=issue_url,
        issue_number=issue_number,
        deduplicated=False,
    )
