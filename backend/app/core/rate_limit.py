"""
Sliding-window rate limiter backed by Redis (or fakeredis when REDIS_URL is unset).

Why Redis instead of the previous in-memory dict:
- The old InMemoryFixedWindowLimiter was process-local: each Gunicorn worker
  maintained independent counters, so a user could multiply their effective
  limit by the number of workers.
- Redis sorted-set sliding window is shared across all workers/instances.
- When REDIS_URL is not configured, fakeredis.FakeRedis() is used automatically
  (pure-Python, no server required) — identical API, zero-config for local dev
  and unit tests.
"""

import logging
import threading
import time
import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from backend.app.core.config_manager import settings
from backend.app.core.security import get_current_user_optional
from backend.app.models.user import User

logger = logging.getLogger(__name__)


def _make_redis_client():
    """Return a Redis client.  Falls back to fakeredis when REDIS_URL is absent."""
    redis_url = getattr(settings, 'REDIS_URL', None)
    if redis_url:
        try:
            import redis as _redis

            client = _redis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info('Rate limiter: connected to Redis at %s', redis_url)
            return client
        except Exception as exc:
            logger.warning('Rate limiter: Redis unavailable (%s), falling back to fakeredis', exc)

    try:
        import fakeredis

        logger.info('Rate limiter: using fakeredis (in-process, no server required)')
        return fakeredis.FakeRedis(decode_responses=True)
    except ImportError:
        logger.warning('Rate limiter: fakeredis not installed, falling back to in-memory shim')
        return _InMemoryFallback()


class _InMemoryFallback:
    """Last-resort shim when neither redis nor fakeredis are available."""

    def __init__(self) -> None:
        self._hits: dict = {}
        self._lock = threading.Lock()

    def pipeline(self):
        return _InMemoryPipeline(self)

    def flushall(self) -> None:
        with self._lock:
            self._hits.clear()


class _InMemoryPipeline:
    def __init__(self, store: _InMemoryFallback) -> None:
        self._store = store
        self._cmds: list = []

    def zremrangebyscore(self, key, _min, _max):
        self._cmds.append(('zremrangebyscore', key, _min, _max))
        return self

    def zadd(self, key, mapping):
        self._cmds.append(('zadd', key, mapping))
        return self

    def zcard(self, key):
        self._cmds.append(('zcard', key))
        return self

    def expire(self, key, seconds):  # noqa: ARG002
        return self

    def execute(self):
        results = []
        with self._store._lock:  # noqa: SLF001
            for cmd in self._cmds:
                if cmd[0] == 'zremrangebyscore':
                    _, key, _min, _max = cmd
                    bucket = self._store._hits.get(key, [])  # noqa: SLF001
                    self._store._hits[key] = [(s, m) for s, m in bucket if not (s <= _max and s >= _min)]  # noqa: SLF001
                    results.append(None)
                elif cmd[0] == 'zadd':
                    _, key, mapping = cmd
                    bucket = self._store._hits.setdefault(key, [])  # noqa: SLF001
                    for member, score in mapping.items():
                        bucket.append((score, member))
                    results.append(None)
                elif cmd[0] == 'zcard':
                    _, key = cmd
                    results.append(len(self._store._hits.get(key, [])))  # noqa: SLF001
        return results


class RedisWindowLimiter:
    """
    Sliding-window rate limiter using Redis sorted sets.

    Each request is stored as a unique member with the current timestamp as score.
    Members older than the window are pruned on every check.
    On any Redis error, requests are allowed through (fail-open) to avoid
    taking down the API if Redis becomes temporarily unavailable.
    """

    def __init__(self) -> None:
        self._redis = _make_redis_client()

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        if limit <= 0:
            return True
        now = time.time()
        window_start = now - window_seconds
        member = str(uuid.uuid4())

        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {member: now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 1)
            results = pipe.execute()
            count = results[2]
            return int(count) <= limit
        except Exception as exc:
            logger.warning('Rate limiter Redis error for key %s: %s — allowing request', key, exc)
            return True

    def reset(self) -> None:
        """Clear all rate-limit state.  Called by test fixtures between test runs."""
        try:
            self._redis.flushall()
        except Exception as exc:
            logger.debug('Rate limiter reset error (non-fatal): %s', exc)


limiter = RedisWindowLimiter()


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get('x-forwarded-for')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return 'unknown'


def _enforce_limit(key: str, limit: int, scope: str) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    if limiter.allow(key=key, limit=limit):
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f'Rate limit exceeded for {scope}. Please retry shortly.',
    )


def make_ip_rate_limiter(limit_getter: Callable[[], int], scope: str):
    async def dependency(request: Request) -> None:
        ip = client_ip(request)
        _enforce_limit(f'{scope}:ip:{ip}', limit_getter(), scope)

    return dependency


def make_user_and_ip_rate_limiter(limit_getter: Callable[[], int], scope: str):
    async def dependency(
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
    ) -> None:
        ip = client_ip(request)
        limit = limit_getter()
        _enforce_limit(f'{scope}:ip:{ip}', limit, scope)
        if current_user is not None:
            _enforce_limit(f'{scope}:user:{current_user.id}', limit, scope)

    return dependency


limit_login = make_ip_rate_limiter(lambda: settings.RATE_LIMIT_LOGIN_PER_MINUTE, 'auth-login')
limit_register = make_ip_rate_limiter(lambda: settings.RATE_LIMIT_REGISTER_PER_MINUTE, 'auth-register')
limit_chat = make_user_and_ip_rate_limiter(lambda: settings.RATE_LIMIT_CHAT_PER_MINUTE, 'chat-send')
