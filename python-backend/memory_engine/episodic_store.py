"""Episodic store: SQLite-backed agent episode persistence for memory service.

This is a lightweight direct SQLite store used by the memory-service process.
The primary episodic store for Next.js is in src/lib/server/memory-episodic-store.ts
(Prisma-backed). This store is for the Python memory service's own bookkeeping.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

_DEFAULT_DB_PATH = str(Path(__file__).resolve().parents[3] / "data" / "episodic.db")


class EpisodicStore:
    def __init__(self, db_path: str | None = None) -> None:
        self._path = db_path or _DEFAULT_DB_PATH
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
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
        now = datetime.now(timezone.utc).isoformat()
        retain_until = (datetime.now(timezone.utc) + timedelta(days=retain_days)).isoformat()
        self._conn.execute(
            """INSERT INTO agent_episodes
               (id, session_id, agent_role, input_json, output_json, tools_used,
                duration_ms, token_count, confidence, tags_json, metadata_json,
                retain_until, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ep_id, session_id, agent_role, input_json, output_json,
                json.dumps(tools_used or []), duration_ms, token_count, confidence,
                json.dumps(tags or []), json.dumps(metadata or {}),
                retain_until, now,
            ),
        )
        self._conn.commit()
        return {"id": ep_id, "created_at": now}

    def list_episodes(
        self,
        agent_role: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if agent_role:
            rows = self._conn.execute(
                "SELECT * FROM agent_episodes WHERE agent_role=? ORDER BY created_at DESC LIMIT ?",
                (agent_role, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM agent_episodes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                **dict(row),
                "tools_used": json.loads(row["tools_used"]),
                "tags": json.loads(row["tags_json"]),
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in rows
        ]

    def prune_expired(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            "DELETE FROM agent_episodes WHERE retain_until < ?", (now,)
        )
        self._conn.commit()
        return cur.rowcount

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM agent_episodes").fetchone()[0])

    def status(self) -> str:
        try:
            self.count()
            return "ready"
        except Exception:
            return "unavailable"
