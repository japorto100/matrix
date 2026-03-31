"""Tool Execution Node — fuehrt pending tool_calls parallel aus.

Wiederverwendet: ToolRegistry, TradingTool ABC, validators.
Parallel execution via asyncio.gather mit per-tool timeout.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import anyio

from agent.context import AgentExecutionContext
from agent.graph.state import AgentGraphState, ToolResult
from agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

TOOL_TIMEOUT_SEC = 30


async def tool_node(state: AgentGraphState) -> dict[str, Any]:
    """Fuehrt alle pending tool_calls parallel aus."""
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        return {"tool_results": [], "tool_calls": []}

    registry = ToolRegistry.load()

    # Minimaler Context fuer Tool-Execution
    ctx = AgentExecutionContext(
        user_id=state.get("user_id", "default"),
        thread_id=state.get("thread_id", ""),
        model=state.get("model", ""),
        system_prompt="",
        tools=tuple(registry.all()),
        reasoning_effort=state.get("reasoning_effort"),
    )

    # Parallel execution
    tasks = [_execute_single(tc, registry, ctx) for tc in tool_calls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    tool_results: list[ToolResult] = []
    tool_messages: list[dict[str, Any]] = []

    for tc, result in zip(tool_calls, results):
        if isinstance(result, Exception):
            tr = ToolResult(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                result={},
                error=str(result),
            )
        else:
            tr = result

        tool_results.append(tr)

        # Add tool result as message for LLM context
        tool_messages.append({
            "role": "tool",
            "tool_use_id": tc["tool_call_id"],
            "content": json.dumps(tr["result"]) if not tr["error"] else json.dumps({"error": tr["error"]}),
        })

    return {
        "tool_results": tool_results,
        "tool_calls": [],  # Clear pending calls
        "messages": tool_messages,
    }


async def _execute_single(
    tc: dict[str, Any],
    registry: ToolRegistry,
    ctx: AgentExecutionContext,
) -> ToolResult:
    """Fuehrt ein einzelnes Tool mit Timeout aus."""
    tool = registry.lookup(tc["tool_name"])
    if not tool:
        return ToolResult(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            result={},
            error=f"Unknown tool: {tc['tool_name']}",
        )

    try:
        # Validation
        tool.validate(tc["tool_input"], ctx)

        # Execute with timeout
        with anyio.fail_after(TOOL_TIMEOUT_SEC):
            result = await tool.execute(tc["tool_input"], ctx)

        return ToolResult(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            result=result,
            error=None,
        )
    except TimeoutError:
        return ToolResult(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            result={},
            error=f"Tool '{tc['tool_name']}' timed out after {TOOL_TIMEOUT_SEC}s",
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            result={},
            error=str(e),
        )
