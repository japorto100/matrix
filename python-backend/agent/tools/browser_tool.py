"""BrowserToolProxy — exec-09 Phase 4

Wrapper der WebMCP Browser-Tools als TradingTool exponiert.
Browser-Tools koennen nicht direkt vom Python Backend ausgefuehrt werden —
das Result kommt vom Frontend via SSE Roundtrip zurueck.

Fuer den Agent Loop sehen Browser-Tools aus wie normale Tools:
- definition() gibt das Schema zurueck (fuer LLM Tool-Choice)
- execute() gibt ein Placeholder-Result zurueck das das Frontend
  als "browser_tool_call" erkennt und via navigator.modelContext ausfuehrt

Der eigentliche Execution-Flow:
1. Agent waehlt Browser-Tool via tool_use
2. Python sendet tool_result mit action="browser_execute" + tool_name
3. Frontend erkennt browser_* Tool-Result → navigator.modelContext.callTool()
4. Frontend sendet echtes Result als Follow-up Message
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class BrowserToolProxy(TradingTool):
    """Proxy fuer WebMCP Browser-Tools — ausfuehrbar nur im Frontend."""

    def __init__(self, tool_name: str, description: str, input_schema: dict) -> None:
        self._name = tool_name
        self._description = description
        self._input_schema = input_schema

    @property
    def name(self) -> str:
        return self._name

    def definition(self) -> dict:
        return {
            "name": self._name,
            "description": f"[Browser Tool] {self._description}",
            "input_schema": self._input_schema or {"type": "object", "properties": {}},
        }

    async def execute(self, tool_input: dict, ctx: AgentExecutionContext) -> dict:
        # Browser-Tools koennen nicht serverseitig ausgefuehrt werden.
        # Wir geben ein Marker-Result zurueck das das Frontend erkennt.
        return {
            "action": "browser_execute",
            "tool_name": self._name,
            "tool_input": tool_input,
            "status": "pending_browser",
            "message": f"Tool '{self._name}' requires browser execution via WebMCP.",
        }
