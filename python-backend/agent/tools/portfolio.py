# Portfolio tool — Phase 22g
# Phase 22g+: ABP.2c — shared httpx client

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent.http_client import get_client
from agent.tools.base import TradingTool
from shared.config import GO_GATEWAY_URL

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


async def get_portfolio_summary(*, user_id: str | None = None) -> dict[str, Any]:
    """
    Get portfolio summary. Read-only. Phase 10e.2.
    Proxies to Go Gateway GCT portfolio API.
    """
    try:
        client = get_client()
        r = await client.get(f"{GO_GATEWAY_URL}/api/v1/gct/portfolio/summary")
        if r.status_code == 200:
            data = r.json()
            return {
                "positions": data.get("balances", []),
                "total_exposure": data.get("total", 0),
                "source": "gct",
            }
    except Exception:
        pass
    return {"positions": [], "total_exposure": 0, "source": "stub"}


class GetPortfolioSummaryTool(TradingTool):
    """Get portfolio summary — positions and total exposure. Read-only."""

    @property
    def name(self) -> str:
        return "get_portfolio_summary"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Get the user's portfolio summary: open positions, exposure, "
                "and balances from the Go Gateway. Read-only."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        return await get_portfolio_summary(user_id=ctx.user_id)
