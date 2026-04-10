# Audit Store — exec-12 Phase 2.1
# Append-only storage backends for audit events.
# Default: JSON Lines file (data/audit/).
# Optional: PostgreSQL (AUDIT_DB_URL or HINDSIGHT_DB_URL).
#
# DB Schema: "matrix" (eigenes Alembic, getrennt von Hindsight's "public")
# Migration: alembic/versions/001_audit_events.py
# Ausfuehren: uv run alembic upgrade head

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_store_instance: AuditStore | None = None

TABLE = "agent.audit_events"


# ── Abstract base ──────────────────────────────────────────────────────────

class AuditStore(ABC):
    @abstractmethod
    async def append(self, entry: dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def query(
        self,
        *,
        thread_id: str | None = None,
        session_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        ...


# ── JSON Lines (dev default, zero dependencies) ───────────────────────────

class JsonLinesAuditStore(AuditStore):
    """Append-only JSON Lines file store. One file per day."""

    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _current_file(self) -> Path:
        return self._base_dir / f"audit-{date.today().isoformat()}.jsonl"

    async def append(self, entry: dict[str, Any]) -> None:
        try:
            line = json.dumps(entry, default=str, ensure_ascii=False)
            with open(self._current_file(), "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.warning("Audit write failed: %s", e)

    async def query(
        self,
        *,
        thread_id: str | None = None,
        session_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        path = self._current_file()
        if not path.exists():
            return results
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if thread_id and entry.get("threadId") != thread_id:
                        continue
                    if session_id and entry.get("sessionId") != session_id:
                        continue
                    if action and entry.get("action") != action:
                        continue
                    results.append(entry)
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.warning("Audit query failed: %s", e)
        return results


# ── PostgreSQL (production, Grafana-ready) ─────────────────────────────────

class PostgresAuditStore(AuditStore):
    """PostgreSQL audit store using psycopg3.

    Tabelle wird via Alembic erstellt (agent.audit_events).
    Kein auto-create — `uv run alembic upgrade head` muss vorher laufen.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    async def append(self, entry: dict[str, Any]) -> None:
        try:
            import psycopg
            with psycopg.connect(self._dsn) as conn:
                conn.execute(
                    f"""
                    INSERT INTO {TABLE}
                        (timestamp, action, user_id, thread_id, agent_class,
                         agent_role, tool_name, input, output, duration_ms,
                         success, error, metadata)
                    VALUES
                        (%(timestamp)s, %(action)s, %(user_id)s, %(thread_id)s, %(agent_class)s,
                         %(agent_role)s, %(tool_name)s, %(input)s, %(output)s, %(duration_ms)s,
                         %(success)s, %(error)s, %(metadata)s)
                    """,
                    {
                        "timestamp": entry.get("timestamp"),
                        "action": entry.get("action", ""),
                        "user_id": entry.get("userId"),
                        "thread_id": entry.get("threadId", ""),
                        "agent_class": entry.get("agentClass", "advisory"),
                        "agent_role": entry.get("agentRole"),
                        "tool_name": entry.get("toolName"),
                        "input": json.dumps(entry.get("input")) if entry.get("input") else None,
                        "output": json.dumps(entry.get("output")) if entry.get("output") else None,
                        "duration_ms": entry.get("duration_ms"),
                        "success": entry.get("success", True),
                        "error": entry.get("error"),
                        "metadata": json.dumps(entry.get("metadata")) if entry.get("metadata") else None,
                    },
                )
                conn.commit()
        except Exception as e:
            logger.warning("Audit PG write failed: %s", e)

    async def query(
        self,
        *,
        thread_id: str | None = None,
        session_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: dict[str, Any] = {"limit": limit}

        if thread_id:
            conditions.append("thread_id = %(thread_id)s")
            params["thread_id"] = thread_id
        if action:
            conditions.append("action = %(action)s")
            params["action"] = action

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM {TABLE} {where} ORDER BY id DESC LIMIT %(limit)s"

        try:
            import psycopg
            from psycopg.rows import dict_row
            with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
                rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning("Audit PG query failed: %s", e)
            return []


# ── Factory ────────────────────────────────────────────────────────────────

def get_audit_store() -> AuditStore:
    """Get or create the singleton audit store.

    Priority: AUDIT_DB_URL → HINDSIGHT_DB_URL (shared PG) → JSON Lines fallback.
    """
    global _store_instance
    if _store_instance is None:
        db_url = os.environ.get("AUDIT_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
        if db_url:
            _store_instance = PostgresAuditStore(db_url)
            logger.info("Audit store: PostgreSQL (%s)", db_url.split("@")[-1] if "@" in db_url else "local")
        else:
            base_dir = os.environ.get(
                "AUDIT_LOG_DIR",
                str(Path(__file__).resolve().parents[2] / "data" / "audit"),
            )
            _store_instance = JsonLinesAuditStore(base_dir)
            logger.info("Audit store: JSON Lines (%s)", base_dir)
    return _store_instance
