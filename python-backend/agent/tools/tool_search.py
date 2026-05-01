"""Tool discovery tool for deferred schema loading."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from agent.tools.base import TradingTool
from agent.tools.discovery import TOOL_SEARCH_NAME, int_env, tool_discovery_matches

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class ToolSearchInput(BaseModel):
    query: str = Field(..., description="Natural language search query for needed tools.")
    limit: int = Field(5, ge=1, le=10, description="Maximum number of tool matches.")


class ToolSearchTool(TradingTool):
    """Search available normal tools without preloading every full schema."""

    input_model = ToolSearchInput

    @property
    def name(self) -> str:
        return TOOL_SEARCH_NAME

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Search the available tool catalog when the needed tool schema "
                "is not currently loaded. Use this before asking for a tool that "
                "is not in the current tool list."
            ),
            "input_schema": ToolSearchInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict[str, Any], ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        from agent.tools.registry import ToolRegistry

        query = str(tool_input.get("query") or "").strip()
        limit = int(tool_input.get("limit") or 5)
        registry = ToolRegistry.load()
        tools = [tool for tool in registry.all() if tool.name != self.name]
        matches = tool_discovery_matches(
            tools,
            query,
            limit=max(1, min(limit, 10)),
            max_level=max(1, int_env("AGENT_TOOL_SEARCH_MAX_LEVEL", 3)),
        )
        compact = [
            {
                "name": str(item.get("name") or ""),
                "group": item.get("group"),
                "summary": item.get("summary"),
                "risk": item.get("risk"),
                "approval": item.get("approval"),
            }
            for item in matches
            if item.get("name")
        ]
        return {
            "query": query,
            "matches": compact,
            "tool_names": [item["name"] for item in compact],
            "deferred_schema_loading": True,
        }

    def to_model_output(self, result: dict[str, Any]) -> dict[str, Any] | str:
        return {
            "matches": result.get("matches", []),
            "instruction": (
                "If a matching tool is needed, call it in the next step; its "
                "schema has been made available."
            ),
        }
