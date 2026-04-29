"""Control Surface — MCP Servers (Slice 6 backend).

Lists MCP servers configured for the agent. Matrix has its own MCP server
mounted at /mcp (agent/mcp_server.py). External MCP servers (Playwright, Exa,
filesystem, GitHub, etc.) would be configured via ENV vars or a JSON file.

Phase 1: enumerate the internal /mcp server + any configured external ones.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from agent.mcp_gateway.policy import McpServerConfig, build_effective_catalog

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "mcp"])


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

    server = _internal_matrix_mcp()
    server_config = McpServerConfig(
        server_id="matrix-internal",
        transport="streamable-http",
        url=server["url"],
        enabled=True,
    )
    descriptors = [
        {
            "name": tool_name,
            "description": "Matrix internal MCP tool",
            "inputSchema": {"type": "object"},
        }
        for tool_name in server["tools"]
    ]
    catalog = build_effective_catalog(
        server_config,
        descriptors,
        tenant_id="matrix-local",
        user_id="control-ui",
    )
    items = [entry.as_dict() for entry in catalog]
    return {"items": items, "total": len(items), "secrets_redacted": True}
