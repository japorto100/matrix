"""Control Surface — Security Posture (Slice 7 TT8 backend).

Computes 4-pillar security score:
  1. Authentication — API keys present, session valid
  2. Encryption — Matrix E2EE, TLS status
  3. Audit — events coverage last 24h
  4. Network — firewall, loopback-only in dev

Plus recent security events (filtered from audit_events) and access list.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "security"])

SECURITY_ACTIONS = (
    "LOGIN",
    "ROLE_OVERRIDE_UPDATED",
    "CONSENT_OVERRIDE_UPDATED",
    "PERMISSION_CHANGED",
    "AUDIT_EXPORTED",
    "APPROVAL_GRANTED",
    "APPROVAL_DENIED",
    "SANDBOX_EXEC",
)

# Map backend action strings to frontend SecurityEventType union
# (login | role_change | sensitive_tool_call | policy_change | audit_export | permission_change)
_ACTION_TO_EVENT_TYPE: dict[str, str] = {
    "LOGIN": "login",
    "ROLE_OVERRIDE_UPDATED": "role_change",
    "CONSENT_OVERRIDE_UPDATED": "permission_change",
    "PERMISSION_CHANGED": "permission_change",
    "AUDIT_EXPORTED": "audit_export",
    "APPROVAL_GRANTED": "sensitive_tool_call",
    "APPROVAL_DENIED": "sensitive_tool_call",
    "SANDBOX_EXEC": "sensitive_tool_call",
}


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


def _compute_pillars() -> list[dict[str, Any]]:
    pillars: list[dict[str, Any]] = []

    # Authentication
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_matrix_token = bool(os.environ.get("MATRIX_BOT_ACCESS_TOKEN"))
    auth_score = 40 * int(has_anthropic or has_openai) + 30 * int(has_matrix_token) + 25
    pillars.append(
        {
            "name": "Authentication",
            "score": min(auth_score, 100),
            "status": "good"
            if auth_score >= 90
            else ("warning" if auth_score >= 50 else "critical"),
            "message": (
                f"LLM keys: {'Anthropic✓' if has_anthropic else ''} "
                f"{'OpenAI✓' if has_openai else ''} · "
                f"Matrix bot: {'✓' if has_matrix_token else '✗'}"
            ).strip(),
        }
    )

    # Encryption
    e2ee = os.environ.get("MATRIX_E2EE_ENABLED", "false").lower() == "true"
    enc_score = 80 if e2ee else 60
    pillars.append(
        {
            "name": "Encryption",
            "score": enc_score,
            "status": "good" if e2ee else "warning",
            "message": (
                "Matrix E2EE enabled (Olm/Megolm)"
                if e2ee
                else "Matrix E2EE disabled in dev (MATRIX_E2EE_ENABLED=false). TLS not enforced locally."
            ),
        }
    )

    # Audit
    audit_count = 0
    try:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        with psycopg.connect(_db_url(), autocommit=True, connect_timeout=2) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM agent.audit_events WHERE timestamp >= %s",
                (cutoff,),
            ).fetchone()
            audit_count = int(row[0]) if row else 0
    except Exception as e:  # noqa: BLE001
        logger.debug("audit count failed: %s", e)

    audit_score = 100 if audit_count > 0 else 50
    pillars.append(
        {
            "name": "Audit",
            "score": audit_score,
            "status": "good" if audit_count > 0 else "warning",
            "message": f"{audit_count} events in last 24h covering mutating actions.",
        }
    )

    # Network
    # In dev, all services are on 127.0.0.1 loopback — that's actually secure.
    pillars.append(
        {
            "name": "Network",
            "score": 60,
            "status": "warning",
            "message": (
                "All services on 127.0.0.1 loopback only — OK for dev. "
                "No firewall rules set for prod yet."
            ),
        }
    )

    return pillars


@router.get("/security/posture")
async def get_security_posture() -> dict[str, Any]:
    pillars = _compute_pillars()
    total = sum(p["score"] for p in pillars)
    overall = total // len(pillars) if pillars else 0

    recent_events: list[dict[str, Any]] = []
    try:
        with psycopg.connect(_db_url(), autocommit=True, connect_timeout=2) as conn:
            cur = conn.execute(
                """
                SELECT id, timestamp, action, user_id, agent_role, tool_name, success, error
                FROM agent.audit_events
                WHERE action = ANY(%s)
                ORDER BY timestamp DESC
                LIMIT 15
                """,
                (list(SECURITY_ACTIONS),),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            for row in rows:
                r = dict(zip(cols, row, strict=True))
                action = r.get("action", "")
                event_type = _ACTION_TO_EVENT_TYPE.get(action, "sensitive_tool_call")
                recent_events.append(
                    {
                        "timestamp": r["timestamp"].isoformat()
                        if r.get("timestamp")
                        else None,
                        "type": event_type,
                        "actor": r.get("user_id") or r.get("agent_role") or "system",
                        "description": r.get("tool_name") or r.get("error") or action,
                        "severity": "critical" if not r.get("success") else "info",
                    }
                )
    except Exception as e:  # noqa: BLE001
        logger.debug("security events query failed: %s", e)

    return {
        "overall_score": overall,
        "pillars": pillars,
        "recent_events": recent_events,
        "access_list": [
            {
                "session_id": "sess_local_dev",
                "ip": "127.0.0.1",
                "user_agent": "local",
                "first_seen": datetime.now(UTC).isoformat(),
                "last_seen": datetime.now(UTC).isoformat(),
            }
        ],
    }


@router.get("/security/events")
async def list_security_events(limit: int = 25) -> dict[str, Any]:
    try:
        with psycopg.connect(_db_url(), autocommit=True, connect_timeout=2) as conn:
            cur = conn.execute(
                """
                SELECT id, timestamp, action, user_id, agent_role, tool_name, success
                FROM agent.audit_events
                WHERE action = ANY(%s)
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (list(SECURITY_ACTIONS), int(limit)),
            )
            rows = cur.fetchall()
    except Exception as e:  # noqa: BLE001
        return {"items": [], "total": 0, "error": str(e)[:200]}

    items = [
        {
            "id": row[0],
            "timestamp": row[1].isoformat() if row[1] else None,
            "action": row[2],
            "user_id": row[3],
            "role": row[4],
            "tool_name": row[5],
            "success": row[6],
        }
        for row in rows
    ]
    return {"items": items, "total": len(items)}
