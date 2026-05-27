"""SQLite checkpoint store for helpdesk agent sessions.

This is the Phase-B persistence layer. It intentionally keeps a tiny surface
area so the runner can later swap to LangGraph SqliteSaver without changing
API behavior.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from backend.app.core.config_manager import settings
from backend.app.schemas.helpdesk import ConversationTurn, TicketDraft
from backend.app.services.helpdesk_graph.state import AwaitingUserPayload, GitHubIssue, HelpdeskState, ProposedSolution


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


def _serialize_state(state: HelpdeskState) -> str:
    return json.dumps(_dump_model(dict(state)), separators=(',', ':'), sort_keys=True)


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
