"""Tool Execution Node — fuehrt pending tool_calls parallel aus.

Wiederverwendet: ToolRegistry, TradingTool ABC, validators.
Parallel execution via asyncio.gather mit per-tool timeout.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import anyio

from agent.context import AgentExecutionContext
from agent.graph.state import AgentGraphState, ToolResult
from agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

def _get_tool_timeout() -> float:
    try:
        from agent.consent.config import get_consent_config
        return get_consent_config().rate_limits.get_tool_timeout()
    except Exception:
        return float(os.environ.get("AGENT_TOOL_TIMEOUT_SEC", "30"))

TOOL_TIMEOUT_SEC = _get_tool_timeout()


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

    # Record tool calls in rate limiter
    from agent.consent.rate_limiter import get_rate_limiter
    limiter = get_rate_limiter()
    for tc in tool_calls:
        limiter.record_tool_call(ctx.thread_id, tc["tool_name"])

    # P0-P2: Sanitize tool outputs before they reach LLM
    from agent.middleware.sanitizer import sanitize_input

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

        # Sanitize before sending to LLM (P0: XML tags, P1: regex, P2: PromptGuard)
        if tr["error"]:
            llm_content = json.dumps({"error": tr["error"]})
        else:
            raw_content = json.dumps(tr["result"]) if isinstance(tr["result"], dict) else str(tr["result"])
            san = sanitize_input(tc["tool_name"], raw_content)
            if san.blocked:
                llm_content = san.content
                logger.warning("Tool output blocked by sanitizer: %s %s", tc["tool_name"], san.audit_metadata)
            else:
                llm_content = san.content
                if san.p1_detections:
                    logger.info("Sanitizer detections for %s: %s", tc["tool_name"], san.p1_detections)

        tool_messages.append({
            "role": "tool",
            "tool_use_id": tc["tool_call_id"],
            "content": llm_content,
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
    """Fuehrt ein einzelnes Tool mit Timeout aus. Audit-logged."""
    from agent.audit.logger import AuditAction, audit_log, audit_timer, audit_duration

    tool = registry.lookup(tc["tool_name"])
    if not tool:
        await audit_log(
            action=AuditAction.TOOL_RESULT,
            thread_id=ctx.thread_id,
            tool_name=tc["tool_name"],
            input_data=tc["tool_input"],
            success=False,
            output_data={"error": f"Unknown tool: {tc['tool_name']}"},
        )
        return ToolResult(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            result={},
            error=f"Unknown tool: {tc['tool_name']}",
        )

    start = audit_timer()
    await audit_log(
        action=AuditAction.TOOL_CALL,
        thread_id=ctx.thread_id,
        agent_id=ctx.user_id,
        tool_name=tc["tool_name"],
        input_data=tc["tool_input"],
    )

    try:
        # Validation
        tool.validate(tc["tool_input"], ctx)

        # Execute with timeout
        with anyio.fail_after(TOOL_TIMEOUT_SEC):
            result = await tool.execute(tc["tool_input"], ctx)

        elapsed = audit_duration(start)
        await audit_log(
            action=AuditAction.TOOL_RESULT,
            thread_id=ctx.thread_id,
            agent_id=ctx.user_id,
            tool_name=tc["tool_name"],
            input_data=tc["tool_input"],
            output_data=result,
            duration_ms=elapsed,
            success=True,
        )

        return ToolResult(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            result=result,
            error=None,
        )
    except TimeoutError:
        elapsed = audit_duration(start)
        await audit_log(
            action=AuditAction.TOOL_RESULT,
            thread_id=ctx.thread_id,
            agent_id=ctx.user_id,
            tool_name=tc["tool_name"],
            input_data=tc["tool_input"],
            duration_ms=elapsed,
            success=False,
            output_data={"error": f"timeout after {TOOL_TIMEOUT_SEC}s"},
        )
        return ToolResult(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            result={},
            error=f"Tool '{tc['tool_name']}' timed out after {TOOL_TIMEOUT_SEC}s",
        )
    except Exception as e:
        elapsed = audit_duration(start)
        await audit_log(
            action=AuditAction.TOOL_RESULT,
            thread_id=ctx.thread_id,
            agent_id=ctx.user_id,
            tool_name=tc["tool_name"],
            input_data=tc["tool_input"],
            duration_ms=elapsed,
            success=False,
            output_data={"error": str(e)},
        )
        return ToolResult(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            result={},
            error=str(e),
        )
