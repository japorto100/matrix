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

    def filter_by_names(self, allowed: set[str]) -> ToolRegistry:
        """Gibt eine neue Registry zurueck die nur die erlaubten Tools enthaelt (exec-10)."""
        filtered = ToolRegistry()
        for name, tool in self._tools.items():
            if name in allowed:
                filtered.register(tool)
        return filtered

    @classmethod
    def load(cls, ctx: AgentExecutionContext | None = None) -> ToolRegistry:
        """Build the default registry with all standard trading tools.
        ctx is optional — passed through for future context-aware tool selection.
        """
        from agent.tools.a2ui_surface import RenderA2uiSurfaceTool
        from agent.tools.canvas import (
            CreateCanvasShapeTool,
            CreateNovelBlockTool,
            DeleteCanvasShapeTool,
            UpdateCanvasShapeTool,
        )
        from agent.tools.chart_state import GetChartStateTool, SetChartStateTool
        from agent.tools.file_analyze import FileAnalyzeTool
        from agent.tools.geomap import GetGeomapFocusTool
        from agent.tools.memory_hindsight import MemoryAddTool, MemorySearchTool
        from agent.tools.memory_tool import LoadMemoryTool, SaveMemoryTool
        from agent.tools.portfolio import GetPortfolioSummaryTool
        from agent.tools.sandbox_browser_tool import SandboxBrowserTool
        from agent.tools.sandbox_tool import SandboxExecuteTool
        from agent.tools.scheduler_tools import (
            ScheduleCancelTool,
            ScheduleEditTool,
            ScheduleListRunsTool,
            ScheduleListTool,
            SchedulePauseTool,
            ScheduleResumeTool,
            ScheduleRunNowTool,
            ScheduleTaskTool,
        )
        from agent.tools.semantic_lookup import SemanticLookupTool

        registry = cls()
        registry.register(GetChartStateTool())
        registry.register(SetChartStateTool())
        registry.register(GetPortfolioSummaryTool())
        registry.register(GetGeomapFocusTool())
        registry.register(SaveMemoryTool())
        registry.register(LoadMemoryTool())
        # Memory Tools (exec-11 Hindsight)
        registry.register(MemorySearchTool())
        registry.register(MemoryAddTool())
        # Canvas Tools (exec-09 Phase 3)
        registry.register(CreateCanvasShapeTool())
        registry.register(CreateNovelBlockTool())
        registry.register(UpdateCanvasShapeTool())
        registry.register(DeleteCanvasShapeTool())
        # Sandbox Tools (exec-12 Phase 1)
        registry.register(SandboxExecuteTool())
        registry.register(SandboxBrowserTool())
        registry.register(FileAnalyzeTool())
        # Semantic Layer (Feature 025) — read-only metric/term contract lookup
        registry.register(SemanticLookupTool())
        # A2UI surface rendering (Ansatz Y — virtual tool emitting widget envelope)
        registry.register(RenderA2uiSurfaceTool())
        # Scheduler Tools (exec-scheduler Lane C — 7 tools, LLM-native NL)
        registry.register(ScheduleTaskTool())
        registry.register(ScheduleListTool())
        registry.register(SchedulePauseTool())
        registry.register(ScheduleResumeTool())
        registry.register(ScheduleCancelTool())
        registry.register(ScheduleListRunsTool())
        registry.register(ScheduleEditTool())
        registry.register(ScheduleRunNowTool())
        return registry
