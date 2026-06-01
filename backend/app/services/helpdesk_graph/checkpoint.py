"""Checkpoint helpers for helpdesk agent sessions.

Phase 1b makes LangGraph's checkpointers the default persistence layer:
Postgres for the app, SQLite for zero-infra demos, and in-memory for tests.
The original JSON SQLite store remains behind
``HELPDESK_AGENT_USE_LANGGRAPH_CHECKPOINT=false`` for one release as an
instant rollback path.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.app.core.config_manager import settings
from backend.app.schemas.helpdesk import ConversationTurn, TicketDraft
from backend.app.services.helpdesk_graph.state import AwaitingUserPayload, GitHubIssue, HelpdeskState, ProposedSolution

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

CheckpointBackend = Literal['postgres', 'sqlite', 'memory']

_MEMORY_SAVER = MemorySaver()
_LAST_GC_AT = 0.0


def use_langgraph_checkpoint() -> bool:
    return bool(getattr(settings, 'HELPDESK_AGENT_USE_LANGGRAPH_CHECKPOINT', True))


def checkpoint_backend() -> CheckpointBackend:
    backend = str(getattr(settings, 'HELPDESK_AGENT_CHECKPOINT_BACKEND', 'postgres') or 'postgres').lower()
    if backend not in {'postgres', 'sqlite', 'memory'}:
        raise ValueError(f'Unsupported HELPDESK_AGENT_CHECKPOINT_BACKEND: {backend}')
    return backend  # type: ignore[return-value]


@asynccontextmanager
async def checkpointer_context() -> AsyncIterator[Any]:
    """Yield the configured LangGraph checkpointer.

    Postgres schema is owned by Alembic, so this factory intentionally does
    not call ``AsyncPostgresSaver.setup()``. SQLite's saver initializes its
    local file lazily because it is a development fallback, not the production
    schema owner.
    """
    backend = checkpoint_backend()
    if backend == 'memory':
        yield _MEMORY_SAVER
        return
    if backend == 'postgres':
        async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as saver:
            yield saver
        return

    path = _checkpoint_path()
    if path.parent != Path('.'):
        path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        yield saver


def _checkpoint_path() -> Path:
    return Path(settings.HELPDESK_AGENT_CHECKPOINT_PATH).expanduser()


def _connect() -> sqlite3.Connection:
    path = _checkpoint_path()
    if path.parent != Path('.'):
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS helpdesk_agent_checkpoints (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            state_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            expires_at REAL NOT NULL
        )
        """
    )
    return conn


def _dump_model(value: Any) -> Any:
    if hasattr(value, 'model_dump'):
        return value.model_dump()
    if isinstance(value, list):
        return [_dump_model(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump_model(item) for key, item in value.items()}
    return value


_TRANSIENT_KEYS: frozenset[str] = frozenset(
    {
        'entry',
        'resume_answer',
        'confirm_draft',
        '_next',
        '_graph_turn',
    }
)


def _serialize_state(state: HelpdeskState) -> str:
    clean = {key: value for key, value in dict(state).items() if key not in _TRANSIENT_KEYS}
    return json.dumps(_dump_model(clean), separators=(',', ':'), sort_keys=True)


def _restore_state(raw: str) -> HelpdeskState:
    data = json.loads(raw)
    if 'conversation' in data:
        data['conversation'] = [ConversationTurn(**turn) for turn in data['conversation']]
    if data.get('duplicate_candidates') is not None:
        data['duplicate_candidates'] = [GitHubIssue(**issue) for issue in data['duplicate_candidates']]
    if data.get('proposed_solutions') is not None:
        data['proposed_solutions'] = [ProposedSolution(**solution) for solution in data['proposed_solutions']]
    if data.get('awaiting_user') is not None:
        data['awaiting_user'] = AwaitingUserPayload(**data['awaiting_user'])
    if data.get('draft') is not None:
        data['draft'] = TicketDraft(**data['draft'])
    return data


def save_checkpoint(state: HelpdeskState) -> None:
    if use_langgraph_checkpoint():
        return
    now = time.time()
    ttl = max(0, int(settings.HELPDESK_AGENT_CHECKPOINT_TTL_SECONDS))
    session_id = state['session_id']
    user_id = str(state['user_id'])
    with _connect() as conn:
        existing = conn.execute(
            'SELECT created_at FROM helpdesk_agent_checkpoints WHERE session_id = ?',
            (session_id,),
        ).fetchone()
        created_at = float(existing['created_at']) if existing else now
        conn.execute(
            """
            INSERT INTO helpdesk_agent_checkpoints
                (session_id, user_id, state_json, created_at, updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                user_id = excluded.user_id,
                state_json = excluded.state_json,
                updated_at = excluded.updated_at,
                expires_at = excluded.expires_at
            """,
            (session_id, user_id, _serialize_state(state), created_at, now, now + ttl),
        )


def load_checkpoint(session_id: str, *, user_id: int | str) -> HelpdeskState | None:
    if use_langgraph_checkpoint():
        raise RuntimeError('load_checkpoint is only available when LangGraph checkpointing is disabled.')
    with _connect() as conn:
        row = conn.execute(
            'SELECT user_id, state_json, expires_at FROM helpdesk_agent_checkpoints WHERE session_id = ?',
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    if float(row['expires_at']) < time.time():
        delete_checkpoint(session_id)
        return None
    if str(row['user_id']) != str(user_id):
        return None
    return _restore_state(row['state_json'])


def delete_checkpoint(session_id: str) -> None:
    with _connect() as conn:
        conn.execute('DELETE FROM helpdesk_agent_checkpoints WHERE session_id = ?', (session_id,))


def gc_checkpoints() -> int:
    now = time.time()
    with _connect() as conn:
        cur = conn.execute('DELETE FROM helpdesk_agent_checkpoints WHERE expires_at < ?', (now,))
        return int(cur.rowcount or 0)


async def gc_langgraph_checkpoints() -> int:
    """Prune expired LangGraph checkpoints for the configured backend."""
    ttl = max(0, int(settings.HELPDESK_AGENT_CHECKPOINT_TTL_SECONDS))
    if ttl <= 0 or checkpoint_backend() == 'memory':
        return 0

    cutoff = time.time() - ttl
    async with checkpointer_context() as saver:
        latest_by_thread: dict[str, float] = {}
        async for item in saver.alist(None):
            ts = item.checkpoint.get('ts') if isinstance(item.checkpoint, dict) else None
            if not isinstance(ts, str):
                continue
            try:
                checkpoint_ts = _parse_checkpoint_ts(ts)
            except ValueError:
                continue
            thread_id = item.config.get('configurable', {}).get('thread_id')
            if thread_id:
                key = str(thread_id)
                latest_by_thread[key] = max(checkpoint_ts, latest_by_thread.get(key, 0.0))

        expired_threads = {thread_id for thread_id, latest_ts in latest_by_thread.items() if latest_ts < cutoff}
        for thread_id in expired_threads:
            await saver.adelete_thread(thread_id)
        return len(expired_threads)


async def maybe_gc_langgraph_checkpoints() -> int:
    """Run checkpoint GC periodically from normal agent traffic."""
    global _LAST_GC_AT
    if not use_langgraph_checkpoint():
        return gc_checkpoints()

    now = time.time()
    ttl = max(0, int(settings.HELPDESK_AGENT_CHECKPOINT_TTL_SECONDS))
    interval = max(60.0, min(float(ttl or 3600), 3600.0))
    if now - _LAST_GC_AT < interval:
        return 0
    _LAST_GC_AT = now
    return await gc_langgraph_checkpoints()


def _parse_checkpoint_ts(value: str) -> float:
    # LangGraph stores ISO-8601 UTC timestamps in ``checkpoint["ts"]``.
    from datetime import datetime

    normalized = value.replace('Z', '+00:00')
    return datetime.fromisoformat(normalized).timestamp()
