from __future__ import annotations

import asyncio
import json

import pytest

from agent.mcp_gateway.execution import (
    McpGatewayExecutionConfig,
    McpToolCallRequest,
    execute_mcp_tool_call,
)
from agent.mcp_gateway.health import fixture_mcp_descriptors, fixture_mcp_server_config
from agent.mcp_gateway.policy import build_effective_catalog


@pytest.mark.asyncio
async def test_execute_mcp_tool_call_preserves_tool_call_id():
    request = McpToolCallRequest(
        tool_call_id="call-1",
        matrix_name="mcp_fixture__lookup",
        tool_input={"q": "x"},
        session_id="s1",
        audit_ref="audit-1",
    )

    result = await execute_mcp_tool_call(
        request,
        lambda req: {"echo": req.tool_input["q"]},
    )

    assert result.ok is True
    message = result.to_tool_message()
    content = json.loads(message["content"])
    assert message["role"] == "tool"
    assert message["tool_call_id"] == "call-1"
    assert message["tool_use_id"] == "call-1"
    assert content["tool_call_id"] == "call-1"
    assert content["result"] == {"echo": "x"}


@pytest.mark.asyncio
async def test_execute_mcp_tool_call_times_out_as_structured_tool_message():
    async def slow(_request: McpToolCallRequest) -> dict:
        await asyncio.sleep(0.05)
        return {"late": True}

    request = McpToolCallRequest(
        tool_call_id="call-timeout",
        matrix_name="mcp_fixture__slow",
        tool_input={},
    )

    result = await execute_mcp_tool_call(
        request,
        slow,
        config=McpGatewayExecutionConfig(timeout_seconds=0.001),
    )

    content = json.loads(result.to_tool_message()["content"])
    assert result.ok is False
    assert result.error is not None
    assert result.error["type"] == "timeout"
    assert content["error"]["tool_call_id"] == "call-timeout"


@pytest.mark.asyncio
async def test_execute_mcp_tool_call_converts_exception_to_structured_error():
    def broken(_request: McpToolCallRequest) -> dict:
        raise RuntimeError("remote closed")

    request = McpToolCallRequest(
        tool_call_id="call-error",
        matrix_name="mcp_fixture__broken",
        tool_input={},
    )

    result = await execute_mcp_tool_call(request, broken)

    content = json.loads(result.content)
    assert result.ok is False
    assert content["error"]["type"] == "RuntimeError"
    assert content["error"]["message"] == "remote closed"
    assert result.to_tool_message()["tool_call_id"] == "call-error"


@pytest.mark.asyncio
async def test_execute_mcp_tool_call_converts_cancellation_when_configured():
    async def cancelled(_request: McpToolCallRequest) -> dict:
        raise asyncio.CancelledError

    request = McpToolCallRequest(
        tool_call_id="call-cancelled",
        matrix_name="mcp_fixture__cancelled",
        tool_input={},
    )

    result = await execute_mcp_tool_call(request, cancelled)

    assert result.ok is False
    assert result.error is not None
    assert result.error["type"] == "cancelled"
    assert result.to_tool_message()["tool_call_id"] == "call-cancelled"


@pytest.mark.asyncio
async def test_execute_mcp_tool_call_caps_output_before_agent_context():
    request = McpToolCallRequest(
        tool_call_id="call-big",
        matrix_name="mcp_fixture__big",
        tool_input={},
    )

    result = await execute_mcp_tool_call(
        request,
        lambda _request: {"blob": "x" * 500},
        config=McpGatewayExecutionConfig(max_output_bytes=256),
    )

    content = json.loads(result.content)
    assert result.ok is True
    assert result.truncated is True
    assert content["truncated"] is True
    assert content["original_bytes"] > content["max_output_bytes"]


@pytest.mark.asyncio
async def test_fixture_mcp_catalog_tool_executes_through_gateway():
    server = fixture_mcp_server_config()
    catalog = build_effective_catalog(server, fixture_mcp_descriptors())
    lookup = next(entry for entry in catalog if entry.snapshot.original_name == "fixture_lookup")

    async def fixture_invoker(request: McpToolCallRequest) -> dict:
        assert request.matrix_name == lookup.snapshot.matrix_name
        return {
            "source": "fixture-mcp",
            "query": request.tool_input["query"],
            "rows": [{"id": "row-1", "value": 42}],
        }

    request = McpToolCallRequest(
        tool_call_id="call-fixture",
        matrix_name=lookup.snapshot.matrix_name,
        tool_input={"query": "portfolio"},
        session_id="session-fixture",
        audit_ref="audit-fixture",
    )

    result = await execute_mcp_tool_call(request, fixture_invoker)
    content = json.loads(result.content)

    assert lookup.visible is True
    assert result.ok is True
    assert result.to_tool_message()["tool_call_id"] == "call-fixture"
    assert content["matrix_name"] == lookup.snapshot.matrix_name
    assert content["result"]["rows"][0]["value"] == 42
