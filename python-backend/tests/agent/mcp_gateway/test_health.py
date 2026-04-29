from __future__ import annotations

import pytest

from agent.mcp_gateway.health import (
    fixture_mcp_descriptors,
    fixture_mcp_server_config,
    probe_mcp_server_health,
)
from agent.mcp_gateway.policy import McpServerConfig, build_effective_catalog


@pytest.mark.asyncio
async def test_health_probe_disabled_server_does_not_invoke_tools():
    result = await probe_mcp_server_health(fixture_mcp_server_config(enabled=False))

    assert result.status == "disabled"
    assert result.reason == "server-disabled"
    assert result.model_visible_tools_invoked is False


@pytest.mark.asyncio
async def test_health_probe_fails_static_config_without_tool_listing():
    result = await probe_mcp_server_health(
        McpServerConfig(
            server_id="bad",
            transport="streamable-http",
            enabled=True,
        )
    )

    assert result.status == "unhealthy"
    assert result.reason == "missing-url"
    assert result.model_visible_tools_invoked is False


@pytest.mark.asyncio
async def test_health_probe_uses_explicit_non_tool_probe():
    calls: list[str] = []

    async def probe(server: McpServerConfig) -> bool:
        calls.append(server.server_id)
        return True

    result = await probe_mcp_server_health(
        fixture_mcp_server_config(),
        probe=probe,
    )

    assert calls == ["fixture-mcp"]
    assert result.status == "healthy"
    assert result.reason == "probe-healthy"
    assert result.model_visible_tools_invoked is False


def test_fixture_descriptors_are_policy_compatible():
    server = fixture_mcp_server_config()
    catalog = build_effective_catalog(server, fixture_mcp_descriptors())

    assert [entry.snapshot.original_name for entry in catalog] == [
        "fixture_lookup",
        "fixture_widget",
    ]
    assert all(entry.visible for entry in catalog)
