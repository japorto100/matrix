"""MCP Server — exponiert TradingTools als standardisierte MCP Tools.

Nutzt FastMCP (mcp SDK v1.26+) mit Streamable HTTP Transport.
Bestehende TradingTools aus tools/registry.py werden automatisch registriert.

Normal: Gemountet im Agent Service unter /mcp (agent/app.py, Port 8094)
Standalone: uv run python -m agent.mcp_server (Port 8095, fuer isoliertes Testing)
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

from agent.tools.base import TradingTool
from agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "trading-agent",
    instructions="Trading Agent MCP Server — provides market data, chart state, portfolio, and memory tools.",
    # Mount FastMCP's streamable-HTTP endpoint at "/" so the effective path
    # after app.mount("/mcp", ...) in agent/app.py is /mcp/ (not /mcp/mcp/).
    streamable_http_path="/",
)


def _register_trading_tool(mcp_server: FastMCP, tool: TradingTool) -> None:
    """Registriert ein TradingTool als MCP Tool mit korrektem Schema."""
    defn = tool.definition()
    name = defn["name"]
    description = defn.get("description", "")
    input_schema = defn.get("input_schema", {})

    # Extrahiere Parameter-Properties fuer die MCP Tool-Signatur
    input_schema.get("properties", {})
    set(input_schema.get("required", []))

    # Closure ueber tool — MCP SDK inspiziert die Signatur,
    # daher keine _-Prefix Parameter erlaubt
    captured_tool = tool

    async def execute(**kwargs: object) -> str:
        from agent.context import AgentExecutionContext

        ctx = AgentExecutionContext(
            user_id="mcp-client",
            thread_id="mcp-session",
            model="",
            system_prompt="",
            tools=(),
        )
        result = await captured_tool.execute(dict(kwargs), ctx)
        return json.dumps(result, ensure_ascii=False, indent=2)

    # Funktionsname setzen damit MCP den richtigen Namen sieht
    execute.__name__ = name
    execute.__qualname__ = name

    mcp_server.tool(name=name, description=description)(execute)
    logger.info("Registered MCP tool: %s", name)


def create_mcp_server() -> FastMCP:
    """Erstellt den MCP Server mit allen TradingTools."""
    registry = ToolRegistry.load()
    for tool in registry.all():
        _register_trading_tool(mcp, tool)

    logger.info("MCP Server ready with %d tools", len(registry.all()))
    return mcp


# Entry Point: uv run python -m agent.mcp_server
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    server = create_mcp_server()
    server.run(transport="streamable-http", host="127.0.0.1", port=8095)
