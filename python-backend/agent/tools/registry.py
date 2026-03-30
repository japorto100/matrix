# ToolRegistry — Phase 22g / ABP.2
# Loads all TradingTool instances for a given agent context.
# Pattern: explicit registration (no dynamic import magic).

from __future__ import annotations

from typing import TYPE_CHECKING

from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class ToolRegistry:
    """Registry for all available trading tools."""

    def __init__(self) -> None:
        self._tools: dict[str, TradingTool] = {}

    def register(self, tool: TradingTool) -> None:
        self._tools[tool.name] = tool

    def lookup(self, name: str) -> TradingTool | None:
        return self._tools.get(name)

    def all(self) -> list[TradingTool]:
        return list(self._tools.values())

    @classmethod
    def load(cls, ctx: "AgentExecutionContext | None" = None) -> "ToolRegistry":
        """Build the default registry with all standard trading tools.
        ctx is optional — passed through for future context-aware tool selection.
        """
        from agent.tools.chart_state import GetChartStateTool, SetChartStateTool
        from agent.tools.geomap import GetGeomapFocusTool
        from agent.tools.memory_tool import LoadMemoryTool, SaveMemoryTool
        from agent.tools.portfolio import GetPortfolioSummaryTool

        registry = cls()
        registry.register(GetChartStateTool())
        registry.register(SetChartStateTool())
        registry.register(GetPortfolioSummaryTool())
        registry.register(GetGeomapFocusTool())
        registry.register(SaveMemoryTool())
        registry.register(LoadMemoryTool())
        return registry
