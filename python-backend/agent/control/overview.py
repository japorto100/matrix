"""Control Surface — Overview snapshot (Slice 7 TT1 backend).

Aggregates stats from multiple sources for the Overview tab:
- AI health (derived from ingestion worker status)
- Active sessions count (LangGraph checkpoints)
- Memory facts total (Hindsight)
- KG nodes total (Kuzu)
- Last agent error (audit_events success=false)
- Recent activity (audit_events last 5-10)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg
from fastapi import APIRouter

from agent.memory.engine import get_bank_id, get_memory_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "overview"])


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


@router.get("/overview")
async def get_overview(user_id: str = "local") -> dict[str, Any]:
    """Aggregate stats for Slice 7 OverviewTab (User Mode default landing)."""

    # Memory facts via Hindsight
    memory_facts = 0
    try:
        engine = await get_memory_engine()
        if engine is not None:
            from hindsight_api.models import RequestContext

            result = await engine.list_memory_units(
                bank_id=get_bank_id(user_id),
                limit=1,
                offset=0,
                request_context=RequestContext(),
            )
            memory_facts = int(result.get("total", 0))
    except Exception as e:  # noqa: BLE001
        logger.debug("overview memory facts failed: %s", e)

    # KG nodes via memory_engine/kg_store.py
    kg_nodes = 0
    try:
        from memory_engine.kg_store import create_kg_store

        kg_nodes = create_kg_store().node_count()
    except Exception as e:  # noqa: BLE001
        logger.debug("overview kg count failed: %s", e)

    # Sessions + last error + recent activity from audit_events + checkpoints
    active_sessions = 0
    active_tasks = 0
    last_error: dict[str, Any] | None = None
    recent_activity: list[dict[str, Any]] = []

    try:
        with psycopg.connect(_db_url(), autocommit=True, connect_timeout=2) as conn:
            # Active sessions: distinct thread_ids from last 1 hour
            session_row = conn.execute(
                """
                SELECT COUNT(DISTINCT thread_id)
                FROM agent.audit_events
                WHERE thread_id IS NOT NULL
                  AND timestamp >= NOW() - INTERVAL '1 hour'
                """
            ).fetchone()
            if session_row:
                active_sessions = int(session_row[0])

            # Active tasks: running sandbox + ingestion
            tasks_row = conn.execute(
                """
                SELECT COUNT(*)
                FROM agent.audit_events
                WHERE (metadata::jsonb ->> 'status') = 'running'
                  AND timestamp >= NOW() - INTERVAL '10 minutes'
                """
            ).fetchone()
            if tasks_row:
                active_tasks = int(tasks_row[0])

            # Last error
            err_row = conn.execute(
                """
                SELECT timestamp, agent_role, error, action
                FROM agent.audit_events
                WHERE success = FALSE
                ORDER BY timestamp DESC
                LIMIT 1
                """
            ).fetchone()
            if err_row:
                last_error = {
                    "timestamp": err_row[0].isoformat() if err_row[0] else None,
                    "role": err_row[1] or "unknown",
                    "message": err_row[2] or f"Action {err_row[3]} failed",
                }

            # Recent activity
            recent_rows = conn.execute(
                """
                SELECT timestamp, action, agent_role, tool_name, duration_ms, success
                FROM agent.audit_events
                ORDER BY timestamp DESC
                LIMIT 8
                """
            ).fetchall()
            for row in recent_rows:
                ts, action, role, tool, dur_ms, success = row
                text_parts = [role or "system"]
                if tool:
                    text_parts.append(tool)
                if dur_ms:
                    text_parts.append(f"{dur_ms}ms")
                text = " · ".join(p for p in text_parts if p)

                kind = "tool_call"
                if action and "MEMORY" in action:
                    kind = "memory"
                elif action and "SANDBOX" in action:
                    kind = "sandbox"
                elif action and "INGESTION" in action:
                    kind = "ingestion"
                elif not success:
                    kind = "error"

                recent_activity.append(
                    {
                        "timestamp": ts.isoformat() if ts else None,
                        "text": text,
                        "kind": kind,
                    }
                )
    except Exception as e:  # noqa: BLE001
        logger.debug("overview audit queries failed: %s", e)

    # AI health derived from ingestion worker reachability
    ai_health = "online"
    ai_health_message = "All systems nominal"
    try:
        import httpx

        ingestion_url = os.environ.get("INGESTION_WORKER_URL", "http://127.0.0.1:8098")
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{ingestion_url}/health")
            if r.status_code != 200:
                ai_health = "degraded"
                ai_health_message = f"ingestion-worker degraded ({r.status_code})"
    except Exception as e:  # noqa: BLE001
        ai_health = "degraded"
        ai_health_message = f"ingestion-worker unreachable: {str(e)[:100]}"

    return {
        "ai_health": ai_health,
        "ai_health_message": ai_health_message,
        "active_sessions": active_sessions,
        "active_tasks": active_tasks,
        "memory_facts_total": memory_facts,
        "kg_nodes_total": kg_nodes,
        "last_agent_error": last_error,
        "recent_activity": recent_activity,
    }
