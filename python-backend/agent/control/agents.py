"""Control Surface — Agent Roles + Overlays (Slice 5 backend).

Merges hardcoded defaults from agent/roles.py with DB overrides from
`agent.agent_role_overrides` table (Migration 004). Pattern D1.

PATCH creates/updates overlay entries. DELETE resets to default.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agent.roles import (
    TRADING_ROLE_MEMORY,
    TRADING_ROLE_PROMPTS,
    TRADING_ROLE_TOOLS,
    TradingRole,
)
from agent.control.request_scope import get_request_scope

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "agents"])

OVERLAY_FIELDS = frozenset(
    {"system_prompt", "allowed_tools", "memory_access", "approval_required"}
)


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


def _load_overlays(user_id: str = "local") -> dict[str, dict[str, Any]]:
    """Return {role_id: {field: value, ...}, ...} from DB."""
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            rows = conn.execute(
                "SELECT role_id, field, value, updated_by, updated_at "
                "FROM agent.agent_role_overrides WHERE user_id = %s",
                (user_id,),
            ).fetchall()
    except Exception as e:  # noqa: BLE001
        logger.warning("load_overlays failed: %s", e)
        return {}

    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        role_id, field, value, updated_by, updated_at = row
        if role_id not in out:
            out[role_id] = {"_updated_at": None, "_updated_by": None}
        out[role_id][field] = value
        if updated_at and (
            out[role_id]["_updated_at"] is None
            or updated_at > out[role_id]["_updated_at"]
        ):
            out[role_id]["_updated_at"] = updated_at
            out[role_id]["_updated_by"] = updated_by
    return out


def _default_role(role_id: str) -> dict[str, Any] | None:
    """Build default role dict from hardcoded TRADING_ROLE_* dicts."""
    try:
        role = TradingRole(role_id)
    except ValueError:
        return None
    return {
        "id": role.value,
        "display_name": role.name.title().replace("_", " "),
        "system_prompt": TRADING_ROLE_PROMPTS.get(role, ""),
        "allowed_tools": sorted(TRADING_ROLE_TOOLS.get(role, set())),
        "memory_access": "read_write"
        if TRADING_ROLE_MEMORY.get(role, {}).get("memory_write", False)
        else "read",
        "approval_required": role == TradingRole.TRADER or role == TradingRole.RISK_MANAGER,
    }


def _merge(default: dict[str, Any], overlay: dict[str, Any] | None) -> dict[str, Any]:
    """Merge default with overlay. Returns copy with is_default + updated_at."""
    if not overlay:
        return {**default, "is_default": True}
    merged = dict(default)
    for field in OVERLAY_FIELDS:
        if field in overlay:
            merged[field] = overlay[field]
    merged["is_default"] = False
    merged["updated_at"] = (
        overlay["_updated_at"].isoformat() if overlay.get("_updated_at") else None
    )
    merged["updated_by"] = overlay.get("_updated_by")
    return merged


# ─── Request models ────────────────────────────────────────────────────────


class PatchRoleRequest(BaseModel):
    system_prompt: str | None = None
    allowed_tools: list[str] | None = None
    memory_access: str | None = None
    approval_required: bool | None = None
    updated_by: str = "local"


# ─── Routes ────────────────────────────────────────────────────────────────


@router.get("/agents")
async def list_agents(request: Request) -> dict[str, Any]:
    """List all trading roles with overrides merged."""
    scope = get_request_scope(request)
    user_id = scope.user_id
    overlays = _load_overlays(user_id)
    items: list[dict[str, Any]] = []
    for role in TradingRole:
        default = _default_role(role.value)
        if default is None:
            continue
        items.append(_merge(default, overlays.get(role.value)))
    return {"items": items, "total": len(items)}


@router.get("/agents/{role_id}")
async def get_agent(role_id: str, request: Request) -> dict[str, Any]:
    default = _default_role(role_id)
    if default is None:
        raise HTTPException(status_code=404, detail="Unknown role")
    scope = get_request_scope(request)
    user_id = scope.user_id
    overlays = _load_overlays(user_id)
    return _merge(default, overlays.get(role_id))


@router.patch("/agents/{role_id}")
async def patch_agent(
    role_id: str, req: PatchRoleRequest, request: Request
) -> dict[str, Any]:
    """UPSERT role overlay fields (bounded-write)."""
    default = _default_role(role_id)
    if default is None:
        raise HTTPException(status_code=404, detail="Unknown role")
    scope = get_request_scope(request)
    user_id = scope.user_id

    updates: list[tuple[str, Any]] = []
    if req.system_prompt is not None:
        updates.append(("system_prompt", req.system_prompt))
    if req.allowed_tools is not None:
        updates.append(("allowed_tools", req.allowed_tools))
    if req.memory_access is not None:
        if req.memory_access not in {"read", "read_write", "none"}:
            raise HTTPException(status_code=400, detail="memory_access invalid")
        updates.append(("memory_access", req.memory_access))
    if req.approval_required is not None:
        updates.append(("approval_required", req.approval_required))

    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            for field, value in updates:
                conn.execute(
                    """
                    INSERT INTO agent.agent_role_overrides
                        (role_id, user_id, field, value, updated_by, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT (role_id, user_id, field)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        role_id,
                        user_id,
                        field,
                        json.dumps(value),
                        req.updated_by,
                        datetime.now(timezone.utc),
                    ),
                )
    except Exception as e:  # noqa: BLE001
        logger.exception("patch_agent failed")
        raise HTTPException(status_code=500, detail=f"patch: {e}") from e

    overlays = _load_overlays(user_id)
    return _merge(default, overlays.get(role_id))


@router.delete("/agents/{role_id}/overrides/{field}")
async def reset_agent_field(
    role_id: str, field: str, request: Request
) -> dict[str, Any]:
    """Reset a single overridden field to its default."""
    if field not in OVERLAY_FIELDS:
        raise HTTPException(status_code=400, detail=f"Unknown field. Allowed: {sorted(OVERLAY_FIELDS)}")
    scope = get_request_scope(request)
    user_id = scope.user_id
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            cur = conn.execute(
                "DELETE FROM agent.agent_role_overrides "
                "WHERE role_id = %s AND user_id = %s AND field = %s",
                (role_id, user_id, field),
            )
            deleted = cur.rowcount or 0
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"reset: {e}") from e
    return {"status": "reset", "field": field, "deleted": deleted > 0}
