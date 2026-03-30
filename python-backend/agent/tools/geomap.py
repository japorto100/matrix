# GeoMap tool — Phase 22g
# Phase 22g+: ABP.2c — shared httpx client

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent.http_client import get_client
from agent.tools.base import TradingTool
from shared.config import GO_GATEWAY_URL

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


async def get_geomap_focus(*, user_id: str | None = None) -> dict[str, Any]:
    """
    Get GeoMap focus (region, markers). Read-only. Phase 10e.3.
    Proxies to Go Gateway geopolitical API.
    """
    try:
        client = get_client()
        r = await client.get(f"{GO_GATEWAY_URL}/api/v1/geopolitical/events")
        if r.status_code == 200:
            data = r.json()
            return {
                "region": "global",
                "markers": data.get("events", [])[:10],
                "body": "Earth",
                "source": "api",
            }
    except Exception:
        pass
    return {"region": "global", "markers": [], "body": "Earth", "source": "stub"}


class GetGeomapFocusTool(TradingTool):
    """Get GeoMap focus: current region and geopolitical event markers. Read-only."""

    @property
    def name(self) -> str:
        return "get_geomap_focus"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Get the current geopolitical map focus: active region and "
                "top geopolitical event markers. Useful for correlating market moves "
                "with geopolitical events. Read-only."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        return await get_geomap_focus(user_id=ctx.user_id)
