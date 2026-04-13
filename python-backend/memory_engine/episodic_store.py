"""Episodic store: SQLite-backed agent episode persistence (LEGACY).

⚠️ LEGACY — Hindsight replaces this store for memory browsing in Slice 3+.
The aktuelle Path ist:
    agent/memory/engine.py → get_memory_engine() → hindsight_api.MemoryEngine
    agent/control/episodes.py uses MemoryEngine.list_memory_units() directly

This SQLite store remains for:
    - legacy memory-service process bookkeeping (if HINDSIGHT_DB_URL unset)
    - testing + offline dev
    - A2A task history (different schema)

NEW Control endpoints (agent/control/episodes.py) MUST NOT use this file —
they go directly to Hindsight via agent.memory.engine.get_memory_engine().
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_DEFAULT_DB_PATH = str(Path(__file__).resolve().parents[3] / "data" / "episodic.db")


class EpisodicStore:
    def __init__(self, db_path: str | None = None) -> None:
        import threading

        self._path = db_path or _DEFAULT_DB_PATH
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._write_lock = threading.Lock()  # #17 fix: serialize concurrent writes
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_episodes (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                agent_role TEXT NOT NULL,
                input_json TEXT NOT NULL,
                output_json TEXT NOT NULL,
                tools_used TEXT NOT NULL DEFAULT '[]',
                duration_ms INTEGER NOT NULL,
                token_count INTEGER NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 0.0,
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                retain_until TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ep_session ON agent_episodes(session_id);
            CREATE INDEX IF NOT EXISTS idx_ep_role ON agent_episodes(agent_role);
            CREATE INDEX IF NOT EXISTS idx_ep_created ON agent_episodes(created_at);
        """)
        self._conn.commit()

    def create(
        self,
        session_id: str,
        agent_role: str,
        input_json: str,
        output_json: str,
        duration_ms: int,
        tools_used: list[str] | None = None,
        token_count: int = 0,
        confidence: float = 0.0,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        retain_days: int = 90,
    ) -> dict[str, Any]:
        ep_id = f"ep_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()
        retain_until = (datetime.now(UTC) + timedelta(days=retain_days)).isoformat()
        with self._write_lock:
            self._conn.execute(
                """INSERT INTO agent_episodes
                   (id, session_id, agent_role, input_json, output_json, tools_used,
                    duration_ms, token_count, confidence, tags_json, metadata_json,
                    retain_until, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ep_id,
                    session_id,
                    agent_role,
                    input_json,
                    output_json,
                    json.dumps(tools_used or []),
                    duration_ms,
                    token_count,
                    confidence,
                    json.dumps(tags or []),
                    json.dumps(metadata or {}),
                    retain_until,
                    now,
                ),
            )
            self._conn.commit()
        return {"id": ep_id, "created_at": now}

    def list_episodes(
        self,
        *,
        user_id: str | None = None,  # noqa: ARG002 — reserved for multi-tenant (D3)
        agent_role: str | None = None,
        session_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        tags: list[str] | None = None,
        confidence_min: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Faceted list with dynamic WHERE clauses.

        Slice 3 backend — used by agent/control/episodes.py.
        Note: `user_id` is reserved for multi-tenant (D3) — current schema has no
        user_id column, so single-tenant Phase 1 ignores it.
        """
        clauses: list[str] = []
        params: list[Any] = []

        if agent_role:
            clauses.append("agent_role = ?")
            params.append(agent_role)
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if from_date is not None:
            clauses.append("created_at >= ?")
            params.append(from_date.isoformat())
        if to_date is not None:
            clauses.append("created_at <= ?")
            params.append(to_date.isoformat())
        if confidence_min is not None:
            clauses.append("confidence >= ?")
            params.append(confidence_min)
        if tags:
            # SQLite JSON1 each()-free substring fallback: we store tags as JSON string,
            # so naive LIKE works OK for small tag counts. For prod with pg/FTS, switch.
            for tag in tags:
                clauses.append("tags_json LIKE ?")
                params.append(f'%"{tag}"%')

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            f"SELECT * FROM agent_episodes {where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        rows = self._conn.execute(sql, tuple(params)).fetchall()
        return [
            {
                **dict(row),
                "tools_used": json.loads(row["tools_used"]),
                "tags": json.loads(row["tags_json"]),
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in rows
        ]

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM agent_episodes WHERE id = ?", (episode_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            **dict(row),
            "tools_used": json.loads(row["tools_used"]),
            "tags": json.loads(row["tags_json"]),
            "metadata": json.loads(row["metadata_json"]),
        }

    def delete_episode(self, episode_id: str) -> bool:
        """Delete a single episode. Returns True if deleted, False if not found."""
        with self._write_lock:
            cur = self._conn.execute(
                "DELETE FROM agent_episodes WHERE id = ?", (episode_id,)
            )
            self._conn.commit()
        return (cur.rowcount or 0) > 0

    def patch_episode(
        self,
        episode_id: str,
        *,
        tags: list[str] | None = None,
        metadata_patch: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Update tags and/or merge metadata for an existing episode."""
        current = self.get_episode(episode_id)
        if current is None:
            return None

        updates: list[str] = []
        params: list[Any] = []

        if tags is not None:
            updates.append("tags_json = ?")
            params.append(json.dumps(tags))
        if metadata_patch:
            merged = {**current["metadata"], **metadata_patch}
            updates.append("metadata_json = ?")
            params.append(json.dumps(merged))

        if not updates:
            return current

        params.append(episode_id)
        with self._write_lock:
            self._conn.execute(
                f"UPDATE agent_episodes SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            self._conn.commit()
        return self.get_episode(episode_id)

    def count_by_role(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT agent_role, COUNT(*) as n FROM agent_episodes GROUP BY agent_role"
        ).fetchall()
        return {row["agent_role"]: int(row["n"]) for row in rows}

    def layer_health(self) -> dict[str, Any]:
        """Rich layer health summary for Slice 3 MemoryHealthCards."""
        total = self.count()
        last_row = self._conn.execute(
            "SELECT created_at FROM agent_episodes ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return {
            "status": "ready",
            "total": total,
            "last_created": last_row["created_at"] if last_row else None,
            "by_role": self.count_by_role(),
            "schema_version": "1.0",
        }

    def prune_expired(self) -> int:
        now = datetime.now(UTC).isoformat()
        with self._write_lock:
            cur = self._conn.execute(
                "DELETE FROM agent_episodes WHERE retain_until < ?", (now,)
            )
            self._conn.commit()
        return cur.rowcount

    def count(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM agent_episodes").fetchone()[0]
        )

    def status(self) -> str:
        try:
            self.count()
            return "ready"
        except Exception:
            return "unavailable"
