from __future__ import annotations

import pytest

from agent.control import tools as control_tools


@pytest.mark.asyncio
async def test_control_tools_exposes_builtin_catalog_policy(monkeypatch):
    monkeypatch.setattr(control_tools, "_tool_stats_24h", lambda: {})
    monkeypatch.setattr(control_tools, "_mcp_tools", lambda: [])

    payload = await control_tools.list_tools(type="builtin")
    by_name = {item["name"]: item for item in payload["items"]}

    assert "memory_add" in by_name
    assert by_name["memory_add"]["group"] == "memory"
    assert by_name["memory_add"]["approval"] == "confirm"
    assert by_name["sandbox_execute"]["risk"] == "critical"
    assert by_name["get_portfolio_summary"]["progressive_disclosure_level"] == 1


@pytest.mark.asyncio
async def test_control_tools_search_progressively_discloses_builtin_tools(monkeypatch):
    monkeypatch.setattr(control_tools, "_tool_stats_24h", lambda: {})

    payload = await control_tools.search_tools(
        control_tools.SearchToolsRequest(query="portfolio memory", max_level=2)
    )
    names = [item["name"] for item in payload["items"]]

    assert "memory_search" in names
    assert "get_portfolio_summary" in names
    assert "sandbox_execute" not in names
    assert "input_schema" not in payload["items"][0]
