"""HTTP request correlation id for logs and response headers.

Incoming ``X-Request-ID`` is accepted when it matches a safe pattern (length and
characters). Invalid or missing values get a new UUID4. The id is stored in a
contextvar for the request scope so logging filters can attach it to records.

Routine JWT debugging belongs at DEBUG in ``security.py``, not INFO.
"""

from __future__ import annotations

import contextvars
import logging
import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = 'X-Request-ID'
_MAX_REQUEST_ID_LEN = 128
_SAFE_REQUEST_ID_RE = re.compile(r'^[A-Za-z0-9._@-]+$')
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    'request_id',
    default=None,
)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def normalize_request_id(raw: str | None) -> str:
    """Return client id if valid, otherwise a new UUID4."""
    if raw is None:
        return str(uuid.uuid4())
    candidate = raw.strip()
    if len(candidate) > _MAX_REQUEST_ID_LEN or not _SAFE_REQUEST_ID_RE.match(candidate):
        return str(uuid.uuid4())
    if _UUID_RE.match(candidate):
        return candidate.lower()
    return candidate


class RequestIdFilter(logging.Filter):
    """Inject ``record.request_id`` for formatters (outside request: '-')."""

    def filter(self, record: logging.LogRecord) -> bool:
        rid = get_request_id()
        record.request_id = rid if rid is not None else '-'
        return True


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Set contextvar and echo ``X-Request-ID`` on the response."""

    async def dispatch(self, request, call_next):
        header_val = request.headers.get(REQUEST_ID_HEADER)
        rid = normalize_request_id(header_val)
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = rid
            return response
        finally:
            request_id_ctx.reset(token)
