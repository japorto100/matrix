"""Control Surface — Tools Registry (Slice 5 backend).

Enumerates tools from multiple sources:
- builtin: agent.tools.registry (existing)
- mcp: /mcp sub-app introspection
- skill: agent.skills.loader (listed as tools)
- a2a: agent.a2a (delegation tools)

Aggregates call_count_24h + avg_latency from agent.audit_events.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agent.control.request_scope import RequestScope, resolve_scope

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "tools"])


class ImportToolRequest(BaseModel):
    url: str
    name: str | None = None
    description: str | None = None
    category: str | None = None


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


def _tool_stats_24h() -> dict[str, dict[str, Any]]:
    """Aggregate tool call counts + avg duration from audit_events last 24h."""
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            rows = conn.execute(
                """
                SELECT tool_name,
                       COUNT(*) as call_count,
                       AVG(duration_ms) as avg_latency_ms,
                       MAX(timestamp) as last_called_at
                FROM agent.audit_events
                WHERE tool_name IS NOT NULL AND timestamp >= %s
                GROUP BY tool_name
                """,
                (cutoff,),
            ).fetchall()
    except Exception as e:  # noqa: BLE001
        logger.warning("tool_stats_24h failed: %s", e)
        return {}

    return {
        row[0]: {
            "call_count_24h": int(row[1]),
            "avg_latency_ms": float(row[2]) if row[2] is not None else None,
            "last_called_at": row[3].isoformat() if row[3] else None,
        }
        for row in rows
    }


def _builtin_tools() -> list[dict[str, Any]]:
    """Enumerate builtin agent tools."""
    out: list[dict[str, Any]] = []
    try:
        from agent.tools import registry as tools_registry

        # Try the ToolRegistry class (newer) or fall back to module-level attrs
        if hasattr(tools_registry, "ToolRegistry"):
            reg = tools_registry.ToolRegistry()
            if hasattr(reg, "load"):
                reg.load()
            if hasattr(reg, "list_tools"):
                tools = reg.list_tools()
                for t in tools:
                    out.append(
                        {
                            "id": f"builtin:{t.name}"
                            if hasattr(t, "name")
                            else f"builtin:{t}",
                            "name": t.name if hasattr(t, "name") else str(t),
                            "type": "builtin",
                            "description": getattr(t, "description", ""),
                            "provider": "matrix-builtin",
                            "input_schema_summary": str(getattr(t, "input_schema", {}))[
                                :100
                            ],
                            "categories": getattr(t, "categories", []),
                            "enabled": True,
                        }
                    )
        return out
    except Exception as e:  # noqa: BLE001
        logger.debug("builtin tools enumeration skipped: %s", e)
        return out


def _mcp_tools() -> list[dict[str, Any]]:
    """Enumerate tools exposed by the /mcp sub-app."""
    out: list[dict[str, Any]] = []
    try:
        from agent.mcp_server import create_mcp_server

        mcp = create_mcp_server()
        # FastMCP stores tools internally — introspect via _tools attribute if available
        tools = getattr(mcp, "_tools", None) or getattr(mcp, "tools", None)
        if tools:
            for name, tool in (
                tools.items() if isinstance(tools, dict) else enumerate(tools)
            ):
                if isinstance(name, int):
                    name = getattr(tool, "name", f"mcp_tool_{name}")
                out.append(
                    {
                        "id": f"mcp:{name}",
                        "name": name,
                        "type": "mcp",
                        "description": getattr(tool, "description", "")
                        if not isinstance(tool, str)
                        else "",
                        "provider": "matrix-mcp",
                        "input_schema_summary": "",
                        "categories": [],
                        "enabled": True,
                    }
                )
    except Exception as e:  # noqa: BLE001
        logger.debug("mcp tools enumeration skipped: %s", e)
    return out


@router.get("/tools")
async def list_tools(
    type: str | None = None, category: str | None = None
) -> dict[str, Any]:
    """List all available tools across builtin/mcp/skill/a2a sources."""
    all_tools: list[dict[str, Any]] = []
    all_tools.extend(_builtin_tools())
    all_tools.extend(_mcp_tools())

    # Merge with stats
    stats = _tool_stats_24h()
    for t in all_tools:
        s = stats.get(t["name"], {})
        t["call_count_24h"] = s.get("call_count_24h", 0)
        t["avg_latency_ms"] = s.get("avg_latency_ms")
        t["last_called_at"] = s.get("last_called_at")

    # Filter
    if type:
        all_tools = [t for t in all_tools if t["type"] == type]
    if category:
        all_tools = [t for t in all_tools if category in (t.get("categories") or [])]

    return {"items": all_tools, "total": len(all_tools)}


@router.get("/tools/{tool_id}")
async def get_tool(tool_id: str) -> dict[str, Any]:
    all_tools = _builtin_tools() + _mcp_tools()
    for t in all_tools:
        if t["id"] == tool_id:
            stats = _tool_stats_24h().get(t["name"], {})
            return {**t, **stats}
    raise HTTPException(status_code=404, detail="Tool not found")


@router.post("/tools/import")
async def import_tool_from_url(
    req: ImportToolRequest,
    scope: RequestScope = Depends(resolve_scope),
) -> dict[str, Any]:
    """Queue bounded-write import of a tool from URL (Phase 1 scaffold)."""
    user_id = scope.user_id
    updated_by = scope.actor
    if not (req.url.startswith("http://") or req.url.startswith("https://")):
        raise HTTPException(
            status_code=400, detail="url must start with http:// or https://"
        )
    now = datetime.now(UTC)
    tool_id = f"url:{req.url}"
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            conn.execute(
                """
                INSERT INTO agent.audit_events
                    (timestamp, action, user_id, success, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    now,
                    "TOOL_IMPORT_REQUESTED",
                    user_id,
                    True,
                    json.dumps(
                        {
                            "tool_id": tool_id,
                            "url": req.url,
                            "name": req.name,
                            "description": req.description,
                            "category": req.category,
                            "updated_by": updated_by,
                            "status": "queued_phase2",
                        }
                    ),
                ),
            )
    except Exception as e:  # noqa: BLE001
        logger.exception("import_tool_from_url failed")
        raise HTTPException(status_code=500, detail=f"import: {e}") from e

    return {"status": "queued", "tool_id": tool_id}
