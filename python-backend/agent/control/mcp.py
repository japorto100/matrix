"""Control Surface — MCP Servers (Slice 6 backend).

Lists MCP servers configured for the agent. Matrix has its own MCP server
mounted at /mcp (agent/mcp_server.py). External MCP servers (Playwright, Exa,
filesystem, GitHub, etc.) would be configured via ENV vars or a JSON file.

Phase 1: enumerate the internal /mcp server + any configured external ones.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from agent.control.cache_impact import (
    build_cache_impact,
    cache_impact_runtime_event,
    digest_records,
)
from agent.control.request_scope import ensure_user_scope
from agent.mcp_gateway.policy import (
    McpCatalogEntry,
    McpServerConfig,
    build_effective_catalog,
    diff_descriptor_snapshots,
    search_effective_catalog,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "mcp"])


class ReloadMcpRequest(BaseModel):
    confirm: bool = False
    previous_digest: str | None = None
    server_id: str = "matrix-internal"
    session_id: str = ""
    thread_id: str = ""


def _catalog_entry_payload(entry: McpCatalogEntry) -> dict[str, Any]:
    """Return Control UI payload with descriptor drift metadata."""

    payload = entry.as_dict()
    payload["descriptor_diff"] = diff_descriptor_snapshots(
        entry.snapshot,
        entry.snapshot,
    )
    return payload


def _internal_matrix_mcp() -> dict[str, Any]:
    """The Matrix-internal FastMCP server mounted at /mcp."""
    tools: list[str] = []
    try:
        from agent.mcp_server import create_mcp_server

        mcp = create_mcp_server()
        # FastMCP introspection — different versions expose tools differently
        internal = getattr(mcp, "_tools", None) or getattr(mcp, "tools", None)
        if internal:
            if isinstance(internal, dict):
                tools = list(internal.keys())
            else:
                tools = [getattr(t, "name", str(t)) for t in internal]
    except Exception as e:  # noqa: BLE001
        logger.warning("matrix mcp introspection failed: %s", e)

    return {
        "id": "matrix-internal",
        "name": "Matrix Internal MCP",
        "url": "http://127.0.0.1:8094/mcp",
        "transport": "http",
        "status": "connected",
        "tools": tools,
        "last_ping": None,
    }


def _internal_matrix_descriptors(server: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": tool_name,
            "description": "Matrix internal MCP tool",
            "inputSchema": {"type": "object"},
        }
        for tool_name in server["tools"]
    ]


def _internal_matrix_server_config(server: dict[str, Any]) -> McpServerConfig:
    return McpServerConfig(
        server_id="matrix-internal",
        display_name="Matrix Internal MCP",
        transport="streamable-http",
        url=server["url"],
        enabled=True,
    )


def _effective_internal_catalog(
    *,
    tenant_id: str = "matrix-local",
    user_id: str = "control-ui",
) -> list[McpCatalogEntry]:
    server = _internal_matrix_mcp()
    return build_effective_catalog(
        _internal_matrix_server_config(server),
        _internal_matrix_descriptors(server),
        tenant_id=tenant_id,
        user_id=user_id,
    )


def _mcp_catalog_digest(catalog: list[McpCatalogEntry]) -> str:
    records = [
        {
            "matrix_name": entry.snapshot.matrix_name,
            "descriptor_hash": entry.snapshot.descriptor_hash,
            "approval_level": entry.snapshot.approval_level,
            "risk_flags": list(entry.snapshot.risk_flags),
            "enabled": entry.snapshot.enabled,
            "visible": entry.visible,
            "denial_reasons": list(entry.denial_reasons),
        }
        for entry in catalog
    ]
    records.sort(key=lambda item: str(item.get("matrix_name") or ""))
    return digest_records(records)


@router.get("/mcp/servers")
async def list_mcp_servers() -> dict[str, Any]:
    """List all configured MCP servers."""
    servers = [_internal_matrix_mcp()]
    # TODO Phase 2: load external MCP server config from ENV or JSON file
    # For now, return just the internal one.
    return {"items": servers, "total": len(servers)}


@router.get("/mcp/servers/{server_id}/tools")
async def list_mcp_tools(server_id: str) -> dict[str, Any]:
    if server_id != "matrix-internal":
        return {"items": [], "total": 0, "note": "External MCP introspection Phase 2"}
    server = _internal_matrix_mcp()
    return {"items": server["tools"], "total": len(server["tools"])}


@router.get("/mcp/catalog")
async def list_mcp_catalog() -> dict[str, Any]:
    """Read-only effective MCP catalog with descriptor policy metadata."""

    catalog = _effective_internal_catalog()
    items = [_catalog_entry_payload(entry) for entry in catalog]
    return {
        "items": items,
        "total": len(items),
        "secrets_redacted": True,
        "catalog_digest": _mcp_catalog_digest(catalog),
    }


@router.post("/mcp/reload")
async def reload_mcp_catalog(
    req: ReloadMcpRequest,
    request: Request,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Preview or confirm MCP catalog reload and cache-impact metadata."""

    if req.server_id != "matrix-internal":
        return {
            "status": "unsupported",
            "server_id": req.server_id,
            "detail": "External MCP reload is gated until external server config exists.",
        }

    scope = ensure_user_scope(request, user_id)
    tenant_id = getattr(scope, "tenant_id", None) or "matrix-local"
    catalog = _effective_internal_catalog(
        tenant_id=tenant_id,
        user_id=scope.user_id,
    )
    digest = _mcp_catalog_digest(catalog)
    impact = build_cache_impact(
        source="mcp_reload",
        reason="mcp_descriptor_catalog_reloaded",
        previous_digest=req.previous_digest,
        next_digest=digest,
        scope={
            "tenant_id": tenant_id,
            "user_id": scope.user_id,
            "server_id": req.server_id,
            "session_id": req.session_id,
            "thread_id": req.thread_id,
        },
        details={
            "tool_count": len(catalog),
            "visible_tool_count": sum(1 for entry in catalog if entry.visible),
            "denied_tool_count": sum(1 for entry in catalog if not entry.visible),
        },
    )
    runtime_event = cache_impact_runtime_event(
        impact,
        session_id=req.session_id,
        thread_id=req.thread_id,
    )
    if not req.confirm:
        return {
            "status": "confirmation_required",
            "server_id": req.server_id,
            "catalog_digest": digest,
            "cache_impact": impact,
            "runtime_events": [runtime_event],
            "confirm_required": impact["action"] == "rebind_required",
        }

    try:
        from agent.audit.logger import AuditAction, audit_log

        await audit_log(
            action=AuditAction.ROUTE_DECISION,
            user_id=scope.user_id,
            session_id=req.session_id,
            thread_id=req.thread_id,
            metadata={
                "control_action": "mcp_reload",
                "cache_impact": impact,
                "runtime_events": [runtime_event],
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("mcp reload audit failed: %s", exc)

    return {
        "status": "reloaded",
        "server_id": req.server_id,
        "catalog_digest": digest,
        "cache_impact": impact,
        "runtime_events": [runtime_event],
    }


@router.get("/mcp/catalog/agent")
async def list_agent_mcp_catalog(
    tenant_id: str = Query(default="matrix-local"),
    user_id: str = Query(default="agent"),
    session_id: str = Query(default=""),
) -> dict[str, Any]:
    """Agent-facing MCP catalog filtered to visible tools for one session."""

    catalog = _effective_internal_catalog(
        tenant_id=tenant_id,
        user_id=user_id,
    )
    items = [entry.as_dict() for entry in catalog if entry.visible]
    return {
        "items": items,
        "total": len(items),
        "secrets_redacted": True,
        "session_id": session_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "catalog_digest": _mcp_catalog_digest(catalog),
    }


@router.get("/mcp/catalog/agent/search")
async def search_agent_mcp_catalog(
    q: str = Query(default=""),
    limit: int = Query(default=5, ge=1, le=20),
    tenant_id: str = Query(default="matrix-local"),
    user_id: str = Query(default="agent"),
    session_id: str = Query(default=""),
) -> dict[str, Any]:
    """Search visible MCP catalog summaries for progressive disclosure."""

    catalog = _effective_internal_catalog(
        tenant_id=tenant_id,
        user_id=user_id,
    )
    search_limit = int(limit) if isinstance(limit, int) else 5
    items = search_effective_catalog(catalog, q, limit=search_limit)
    return {
        "items": items,
        "total": len(items),
        "secrets_redacted": True,
        "session_id": session_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
    }
