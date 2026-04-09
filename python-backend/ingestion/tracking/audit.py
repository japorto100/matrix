"""Audit event emitter — writes to `agent.audit_events` table.

This is the same audit table the main agent writes to (exec-12 Phase 2.1).
We write directly via psycopg without importing agent code (D17 decoupling).

Schema (from alembic 001_audit_events.py):
    id BIGSERIAL PK, timestamp TIMESTAMPTZ, action TEXT, user_id TEXT,
    thread_id TEXT, agent_class TEXT, agent_role TEXT, tool_name TEXT,
    input JSON, output JSON, duration_ms INT, success BOOL, error TEXT,
    metadata JSON
"""

from __future__ import annotations

import json
from typing import Any

import psycopg
from loguru import logger


class AuditEmitter:
    """Emit audit events to `agent.audit_events`."""

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url

    def emit(
        self,
        action: str,
        user_id: str = "local",
        target_type: str | None = None,
        target_id: str | None = None,
        result: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Insert an audit event row.

        target_type/target_id are folded into metadata for compatibility with
        the existing schema (which uses thread_id/tool_name as semantic refs).
        """
        meta = dict(metadata or {})
        if target_type:
            meta["target_type"] = target_type
        if target_id:
            meta["target_id"] = target_id
        meta["actor"] = "ingestion-worker"

        try:
            with psycopg.connect(self.db_url, autocommit=True) as conn:
                conn.execute(
                    """
                    INSERT INTO agent.audit_events
                      (action, user_id, success, metadata)
                    VALUES (%s, %s, %s, %s::json)
                    """,
                    (
                        action,
                        user_id,
                        result == "success",
                        json.dumps(meta),
                    ),
                )
        except Exception as e:  # noqa: BLE001
            # Audit failures must NEVER break the pipeline
            logger.warning("audit emit failed for {}: {}", action, e)
