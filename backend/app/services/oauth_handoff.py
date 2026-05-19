"""One-time codes to pass OAuth JWT from API port to Vue dev server (cross-port cookies)."""

from __future__ import annotations

import secrets
import time
from threading import Lock

_TTL_SECONDS = 120
_store: dict[str, tuple[str, float]] = {}
_lock = Lock()


def create_handoff_code(access_token: str) -> str:
    code = secrets.token_urlsafe(32)
    expires = time.time() + _TTL_SECONDS
    with _lock:
        _purge_expired_locked()
        _store[code] = (access_token, expires)
    return code


def consume_handoff_code(code: str) -> str | None:
    if not code:
        return None
    with _lock:
        _purge_expired_locked()
        entry = _store.pop(code, None)
    if entry is None:
        return None
    token, expires = entry
    if time.time() > expires:
        return None
    return token


def _purge_expired_locked() -> None:
    now = time.time()
    expired = [key for key, (_, exp) in _store.items() if now > exp]
    for key in expired:
        del _store[key]
