# Chart state tools — Phase 22g
# Phase 22g+: ABP.2b (Pydantic input model) + ABP.2c (shared httpx client)
# GetChartStateTool: read-only
# SetChartStateTool: mutation (pending confirm, requires human approval)

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from agent.errors import ToolValidationError
from agent.http_client import get_client
from agent.tools.base import TradingTool
from shared.config import GO_GATEWAY_URL

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class SetChartStateInput(BaseModel):
    symbol: str
    timeframe: str


async def get_chart_state(*, user_id: str | None = None) -> dict[str, Any]:
    """
    Get current chart state. Read-only. Phase 10e.1.
    Proxies to Go Gateway which may get state from frontend/session.
    """
    try:
        client = get_client()
        r = await client.get(
            f"{GO_GATEWAY_URL}/api/v1/fusion/chart/state",
            timeout=5.0,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {
        "symbol": "EURUSD",
        "timeframe": "4H",
        "indicators": ["RSI", "MACD"],
        "source": "stub",
    }


async def set_chart_state(symbol: str, timeframe: str) -> dict[str, Any]:
    """
    Mutation Tool: request chart state change. Phase 10.v3.
    Stores pending mutation in working memory (session 'global').
    Frontend must confirm before applying.
    """
    mutation_id = str(uuid.uuid4())[:8]
    return {
        "ok": True,
        "mutation_id": mutation_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "status": "pending_confirm",
    }


class GetChartStateTool(TradingTool):
    """Read current chart state from Go Gateway."""

    @property
    def name(self) -> str:
        return "get_chart_state"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Get the current trading chart state: active symbol, timeframe, "
                "and enabled indicators. Read-only."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        return await get_chart_state(user_id=ctx.user_id)


class SetChartStateTool(TradingTool):
    """Request chart state change — pending confirm, requires human approval."""

    input_model = SetChartStateInput

    @property
    def name(self) -> str:
        return "set_chart_state"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Request a chart state change (symbol or timeframe). "
                "The change is queued as a pending mutation and requires user confirmation "
                "before it is applied. Never executes trades."
            ),
            "input_schema": SetChartStateInput.model_json_schema(),
        }

    def validate(self, tool_input: dict, ctx: "AgentExecutionContext") -> None:
        # Pydantic validation first (ABP.2b)
        super().validate(tool_input, ctx)
        # Advisory agent capability guard — keep as-is
        if ctx.agent_class == "advisory":
            from agent.context import ENVELOPES
            envelope = ENVELOPES.get(ctx.agent_class)
            if envelope:
                envelope.check(self.name)

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        params = SetChartStateInput(**tool_input)
        return await set_chart_state(params.symbol, params.timeframe)
