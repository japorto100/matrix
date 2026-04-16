"""Session CRUD — thin layer over `agent.sessions` (exec-18).

Provides create/update/get for agent sessions. Sessions link to:
- Hindsight banks via bank_id
- Audit events via thread_id (legacy compat)
- Traces via session_id FK on agent.traces
- Memory via session_memories bridge (future)
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import psycopg

logger = logging.getLogger(__name__)


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class Session:
    session_id: str
    session_type: str
    agent_id: str | None = None
    user_id: str | None = None
    thread_id: str | None = None
    bank_id: str | None = None
    status: str = "active"
    session_data: dict | None = None
    agent_data: dict | None = None
    metadata: dict | None = None
    runs: list | None = None
    summary: dict | None = None
    started_at: int = 0
    completed_at: int | None = None
    created_at: int = 0
    updated_at: int | None = None


def create_session(
    *,
    session_type: str = "agent_chat",
    agent_id: str | None = None,
    user_id: str | None = None,
    thread_id: str | None = None,
    bank_id: str | None = None,
    session_data: dict | None = None,
    agent_data: dict | None = None,
) -> Session:
    """Create a new session row in agent.sessions. Returns Session object."""
    import json as _json

    sid = str(uuid.uuid4())
    now = _now_ms()
    session = Session(
        session_id=sid,
        session_type=session_type,
        agent_id=agent_id,
        user_id=user_id,
        thread_id=thread_id,
        bank_id=bank_id,
        status="active",
        session_data=session_data,
        agent_data=agent_data,
        started_at=now,
        created_at=now,
    )

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            conn.execute(
                """
                INSERT INTO agent.sessions
                    (session_id, session_type, agent_id, user_id, thread_id,
                     bank_id, session_data, agent_data, status,
                     started_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
                """,
                (
                    sid,
                    session_type,
                    agent_id,
                    user_id,
                    thread_id,
                    bank_id,
                    _json.dumps(session_data) if session_data else None,
                    _json.dumps(agent_data) if agent_data else None,
                    "active",
                    now,
                    now,
                ),
            )
    except Exception as e:  # noqa: BLE001
        logger.warning("create_session failed: %s", e)

    return session


def update_session(
    session_id: str,
    *,
    status: str | None = None,
    summary: dict | None = None,
    runs: list | None = None,
    metadata: dict | None = None,
) -> None:
    """Update an existing session. Best-effort, never raises."""
    import json as _json

    sets: list[str] = ["updated_at = %s"]
    params: list[Any] = [_now_ms()]

    if status:
        sets.append("status = %s")
        params.append(status)
        if status in ("completed", "errored", "timeout"):
            sets.append("completed_at = %s")
            params.append(_now_ms())

    if summary is not None:
        sets.append("summary = %s::jsonb")
        params.append(_json.dumps(summary))

    if runs is not None:
        sets.append("runs = %s::jsonb")
        params.append(_json.dumps(runs))

    if metadata is not None:
        sets.append("metadata = %s::jsonb")
        params.append(_json.dumps(metadata))

    params.append(session_id)

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            conn.execute(
                f"UPDATE agent.sessions SET {', '.join(sets)} WHERE session_id = %s",
                params,
            )
    except Exception as e:  # noqa: BLE001
        logger.debug("update_session failed: %s", e)


def get_session(session_id: str) -> dict[str, Any] | None:
    """Fetch a session by ID. Returns dict or None."""
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                row = cur.execute(
                    "SELECT * FROM agent.sessions WHERE session_id = %s",
                    (session_id,),
                ).fetchone()
                return dict(row) if row else None
    except Exception as e:  # noqa: BLE001
        logger.debug("get_session failed: %s", e)
        return None
