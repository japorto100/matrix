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
from agent.roles import TRADING_ROLE_TOOLS, TradingRole
from agent.runtime_events import make_runtime_event
from agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def _get_tool_timeout() -> float:
    try:
        from agent.consent.config import get_consent_config

        return get_consent_config().rate_limits.get_tool_timeout()
    except Exception:
        return float(os.environ.get("AGENT_TOOL_TIMEOUT_SEC", "30"))


TOOL_TIMEOUT_SEC = _get_tool_timeout()

# Sandbox tools need much longer timeouts (up to 30min for backtesting)
SANDBOX_TOOL_TIMEOUT_SEC = float(os.environ.get("SANDBOX_TOOL_TIMEOUT_SEC", "1800"))
SANDBOX_TOOLS = {"sandbox_execute", "sandbox_browser"}
MEMORY_TOOL_TIMEOUT_SEC = float(os.environ.get("MEMORY_TOOL_TIMEOUT_SEC", "90"))
MEMORY_TOOLS = {"memory_add", "memory_search"}
TOOL_LLM_OUTPUT_MAX_CHARS = int(os.environ.get("AGENT_TOOL_LLM_OUTPUT_MAX_CHARS", "12000"))
_TOOL_LLM_TRUNCATION_MARKER = "[tool_output_truncated"


def _effective_tool_timeout(tool_name: str) -> float:
    if tool_name in SANDBOX_TOOLS:
        return SANDBOX_TOOL_TIMEOUT_SEC
    if tool_name in MEMORY_TOOLS:
        return MEMORY_TOOL_TIMEOUT_SEC
    return TOOL_TIMEOUT_SEC


async def tool_node(state: AgentGraphState) -> dict[str, Any]:
    """Fuehrt alle pending tool_calls parallel aus."""
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        return {"tool_results": [], "tool_calls": []}

    registry = ToolRegistry.load()
    role = _trading_role_from_state(state)
    if role is not None:
        registry = registry.filter_by_names(TRADING_ROLE_TOOLS.get(role, set()))

    # Minimaler Context fuer Tool-Execution
    ctx = AgentExecutionContext(
        user_id=state.get("user_id", "default"),
        thread_id=state.get("thread_id", ""),
        model=state.get("model", ""),
        system_prompt="",
        tools=tuple(registry.all()),
        reasoning_effort=state.get("reasoning_effort"),
    )

    hook_policy = state.get("tool_hook_policy") or {}

    # Parallel execution
    if hook_policy:
        tasks = [
            _execute_single(tc, registry, ctx, hook_policy=hook_policy)
            for tc in tool_calls
        ]
    else:
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
    runtime_events: list[dict[str, Any]] = []

    for tc, raw_result in zip(tool_calls, results):
        if isinstance(raw_result, BaseException):
            tr: ToolResult = ToolResult(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                result={},
                error=str(raw_result),
            )
        else:
            tr = raw_result  # type: ignore[assignment]  # gather returns ToolResult when no exception

        tool_results.append(tr)
        runtime_events.append(
            _tool_runtime_event(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                status="failed" if tr["error"] else "completed",
                thread_id=ctx.thread_id,
                summary="Tool execution failed" if tr["error"] else "Tool execution completed",
                metadata=_tool_result_event_metadata(tr),
            )
        )

        # Sanitize before sending to LLM (P0: XML tags, P1: regex, P2: PromptGuard)
        if tr["error"]:
            llm_content = json.dumps({"error": tr["error"]})
        else:
            model_output = _model_output_for_tool(
                registry=registry,
                tool_name=tc["tool_name"],
                result=tr["result"],
            )
            raw_content = (
                json.dumps(model_output)
                if isinstance(model_output, dict)
                else str(model_output)
            )
            san = sanitize_input(tc["tool_name"], raw_content)
            if san.blocked:
                llm_content = san.content
                logger.warning(
                    "Tool output blocked by sanitizer: %s %s",
                    tc["tool_name"],
                    san.audit_metadata,
                )
            else:
                llm_content = san.content
                if san.p1_detections:
                    logger.info(
                        "Sanitizer detections for %s: %s",
                        tc["tool_name"],
                        san.p1_detections,
                    )

        tool_messages.append(
            {
                "role": "tool",
                "tool_call_id": tc["tool_call_id"],
                "tool_use_id": tc["tool_call_id"],
                "content": _cap_tool_llm_content(tc["tool_name"], llm_content),
            }
        )
        runtime_events.extend(_runtime_events_from_tool_result(tr))

    return {
        "tool_results": tool_results,
        "tool_calls": [],  # Clear pending calls
        "messages": tool_messages,
        "runtime_events": runtime_events,
    }


def _trading_role_from_state(state: AgentGraphState) -> TradingRole | None:
    role = state.get("current_role")
    if not role:
        return None
    try:
        return TradingRole(role)
    except ValueError:
        return None


def _cap_tool_llm_content(tool_name: str, content: str) -> str:
    """Cap sanitized tool content before it enters the next LLM call."""

    if (
        len(content) <= TOOL_LLM_OUTPUT_MAX_CHARS
        or _TOOL_LLM_TRUNCATION_MARKER in content
    ):
        return content
    marker = (
        f"\n{_TOOL_LLM_TRUNCATION_MARKER} "
        f"tool={tool_name} original_chars={len(content)} "
        f"max_chars={TOOL_LLM_OUTPUT_MAX_CHARS}]"
    )
    return content[:TOOL_LLM_OUTPUT_MAX_CHARS].rstrip() + marker


def _model_output_for_tool(
    *,
    registry: ToolRegistry,
    tool_name: str,
    result: dict[str, Any] | str,
) -> dict[str, Any] | str:
    if not isinstance(result, dict):
        return result
    tool = registry.lookup(tool_name)
    if tool is None:
        return result
    try:
        return tool.to_model_output(result)
    except Exception:  # noqa: BLE001
        logger.warning("Tool model-output transform failed for %s", tool_name)
        return result


def _runtime_events_from_tool_result(result: ToolResult) -> list[dict[str, Any]]:
    payload = result.get("result")
    if not isinstance(payload, dict):
        return []
    events = payload.get("runtime_events")
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, dict)]


def _tool_runtime_event(
    *,
    tool_call_id: str,
    tool_name: str,
    status: str,
    thread_id: str,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        **(metadata or {}),
    }
    return make_runtime_event(
        kind="tool",  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        name=f"tool.{tool_name}",
        summary=summary,
        thread_id=thread_id,
        metadata=payload,
    )


def _tool_result_event_metadata(result: ToolResult) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "result_type": type(result["result"]).__name__,
        "has_error": bool(result["error"]),
    }
    if isinstance(result["result"], dict):
        metadata["result_keys"] = list(result["result"].keys())[:20]
    if result["error"]:
        metadata["error_type"] = "tool_error"
    return metadata


def _hook_policy_veto(
    *,
    tool_name: str,
    hook_policy: dict[str, Any] | None,
) -> dict[str, Any] | None:
    policy = hook_policy or {}
    deny_tools = {str(item) for item in policy.get("deny_tools") or ()}
    veto_map = policy.get("pre_tool_veto") or {}
    if not isinstance(veto_map, dict):
        veto_map = {}
    if tool_name in veto_map:
        return {
            "hook": "pre_tool_call",
            "decision": "veto",
            "reason": str(veto_map.get(tool_name) or "tool-vetoed"),
        }
    if tool_name in deny_tools:
        return {
            "hook": "pre_tool_call",
            "decision": "veto",
            "reason": str(policy.get("reason") or "tool-denylisted"),
        }
    return None


def _result_transform_policy(
    *,
    tool_name: str,
    hook_policy: dict[str, Any] | None,
) -> tuple[str, ...]:
    policy = hook_policy or {}
    redact_config = policy.get("redact_result_keys") or {}
    if not isinstance(redact_config, dict):
        return ()
    keys: list[str] = []
    for item in redact_config.get("*") or ():
        keys.append(str(item))
    for item in redact_config.get(tool_name) or ():
        keys.append(str(item))
    return tuple(dict.fromkeys(keys))


def _apply_tool_result_transform(
    *,
    tool_name: str,
    result: Any,
    hook_policy: dict[str, Any] | None,
) -> tuple[Any, dict[str, Any] | None]:
    redact_keys = _result_transform_policy(tool_name=tool_name, hook_policy=hook_policy)
    if not redact_keys or not isinstance(result, dict):
        return result, None
    transformed = dict(result)
    redacted: list[str] = []
    for key in redact_keys:
        if key in transformed:
            transformed[key] = "[redacted_by_tool_hook]"
            redacted.append(key)
    if not redacted:
        return result, None
    return transformed, {
        "hook": "transform_tool_result",
        "decision": "transformed",
        "redacted_keys": redacted,
    }


async def _execute_single(
    tc: dict[str, Any],
    registry: ToolRegistry,
    ctx: AgentExecutionContext,
    *,
    hook_policy: dict[str, Any] | None = None,
) -> ToolResult:
    """Fuehrt ein einzelnes Tool mit Timeout aus. Audit-logged + OTel traced."""
    from agent.audit.logger import AuditAction, audit_duration, audit_log, audit_timer
    from agent.tracing import tool_span

    tool = registry.lookup(tc["tool_name"])
    budget_metadata = _tool_budget_metadata(ctx.thread_id, tc["tool_name"])
    if not tool:
        runtime_event = _tool_runtime_event(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            status="failed",
            thread_id=ctx.thread_id,
            summary="Tool lookup failed",
            metadata={"error_type": "unknown_tool"},
        )
        await audit_log(
            action=AuditAction.TOOL_RESULT,
            thread_id=ctx.thread_id,
            tool_name=tc["tool_name"],
            input_data=tc["tool_input"],
            success=False,
            output_data={"error": f"Unknown tool: {tc['tool_name']}"},
            metadata={**budget_metadata, "runtime_events": [runtime_event]},
        )
        return ToolResult(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            result={},
            error=f"Unknown tool: {tc['tool_name']}",
        )

    with tool_span(
        tc["tool_name"], "mcp" if hasattr(tool, "mcp") else "builtin"
    ) as span:
        start = audit_timer()
        started_event = _tool_runtime_event(
            tool_call_id=tc["tool_call_id"],
            tool_name=tc["tool_name"],
            status="started",
            thread_id=ctx.thread_id,
            summary="Tool execution started",
            metadata=budget_metadata,
        )
        await audit_log(
            action=AuditAction.TOOL_CALL,
            thread_id=ctx.thread_id,
            agent_id=ctx.user_id,
            tool_name=tc["tool_name"],
            input_data=tc["tool_input"],
            metadata={**budget_metadata, "runtime_events": [started_event]},
        )

        veto = _hook_policy_veto(tool_name=tc["tool_name"], hook_policy=hook_policy)
        if veto is not None:
            elapsed = audit_duration(start)
            runtime_event = _tool_runtime_event(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                status="blocked",
                thread_id=ctx.thread_id,
                summary="Tool execution vetoed by hook policy",
                metadata={
                    **budget_metadata,
                    "duration_ms": elapsed,
                    "hook_policy": veto,
                    "error_type": "tool_hook_veto",
                },
            )
            await audit_log(
                action=AuditAction.TOOL_RESULT,
                thread_id=ctx.thread_id,
                agent_id=ctx.user_id,
                tool_name=tc["tool_name"],
                input_data=tc["tool_input"],
                duration_ms=elapsed,
                success=False,
                output_data={
                    "error": "tool vetoed by hook policy",
                    "reason": veto["reason"],
                },
                metadata={**budget_metadata, "runtime_events": [runtime_event]},
            )
            span.set_attribute("tool.duration_ms", elapsed)
            span.set_attribute("tool.success", False)
            span.set_attribute("tool.hook_policy_decision", "veto")
            return ToolResult(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                result={},
                error=f"Tool vetoed by hook policy: {veto['reason']}",
            )

        try:
            # Validation
            tool.validate(tc["tool_input"], ctx)

            # Execute with timeout (sandbox tools get extended timeout)
            timeout = _effective_tool_timeout(tc["tool_name"])
            with anyio.fail_after(timeout):
                result = await tool.execute(tc["tool_input"], ctx)
            result, transform = _apply_tool_result_transform(
                tool_name=tc["tool_name"],
                result=result,
                hook_policy=hook_policy,
            )

            elapsed = audit_duration(start)
            runtime_event = _tool_runtime_event(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                status="completed",
                thread_id=ctx.thread_id,
                summary="Tool execution completed",
                metadata={
                    **budget_metadata,
                    "duration_ms": elapsed,
                    "result_type": type(result).__name__,
                    **(
                        {"result_keys": list(result.keys())[:20]}
                        if isinstance(result, dict)
                        else {}
                    ),
                    **({"hook_policy": transform} if transform else {}),
                },
            )
            await audit_log(
                action=AuditAction.TOOL_RESULT,
                thread_id=ctx.thread_id,
                agent_id=ctx.user_id,
                tool_name=tc["tool_name"],
                input_data=tc["tool_input"],
                output_data=result,
                duration_ms=elapsed,
                success=True,
                metadata={**budget_metadata, "runtime_events": [runtime_event]},
            )

            span.set_attribute("tool.duration_ms", elapsed)
            span.set_attribute("tool.success", True)

            return ToolResult(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                result=result,
                error=None,
            )
        except TimeoutError:
            elapsed = audit_duration(start)
            effective_timeout = _effective_tool_timeout(tc["tool_name"])
            runtime_event = _tool_runtime_event(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                status="stale",
                thread_id=ctx.thread_id,
                summary="Tool execution timed out",
                metadata={
                    **budget_metadata,
                    "duration_ms": elapsed,
                    "timeout_s": effective_timeout,
                    "error_type": "timeout",
                },
            )
            await audit_log(
                action=AuditAction.TOOL_RESULT,
                thread_id=ctx.thread_id,
                agent_id=ctx.user_id,
                tool_name=tc["tool_name"],
                input_data=tc["tool_input"],
                duration_ms=elapsed,
                success=False,
                output_data={"error": f"timeout after {effective_timeout}s"},
                metadata={**budget_metadata, "runtime_events": [runtime_event]},
            )

            span.set_attribute("tool.duration_ms", elapsed)
            span.set_attribute("tool.success", False)
            span.set_attribute("tool.error", f"timeout after {effective_timeout}s")

            return ToolResult(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                result={},
                error=f"Tool '{tc['tool_name']}' timed out after {effective_timeout}s",
            )
        except Exception as e:
            elapsed = audit_duration(start)
            runtime_event = _tool_runtime_event(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                status="failed",
                thread_id=ctx.thread_id,
                summary="Tool execution failed",
                metadata={
                    **budget_metadata,
                    "duration_ms": elapsed,
                    "error_type": type(e).__name__,
                },
            )
            await audit_log(
                action=AuditAction.TOOL_RESULT,
                thread_id=ctx.thread_id,
                agent_id=ctx.user_id,
                tool_name=tc["tool_name"],
                input_data=tc["tool_input"],
                duration_ms=elapsed,
                success=False,
                output_data={"error": str(e)},
                metadata={**budget_metadata, "runtime_events": [runtime_event]},
            )

            span.set_attribute("tool.duration_ms", elapsed)
            span.set_attribute("tool.success", False)
            span.set_attribute("tool.error", str(e)[:500])

            return ToolResult(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                result={},
                error=str(e),
            )


def _tool_budget_metadata(thread_id: str, tool_name: str) -> dict[str, Any]:
    """Return non-blocking budget context for audit/Meta-Harness traces."""
    metadata: dict[str, Any] = {"thread_id": thread_id, "tool_name": tool_name}
    try:
        from agent.consent.config import get_consent_config
        from agent.consent.rate_limiter import get_rate_limiter

        config = get_consent_config().rate_limits
        limiter = get_rate_limiter()
        usage = limiter.get_usage(thread_id)
        tool_limit = config.per_tool.get(tool_name)
        metadata.update(
            {
                "tool_calls_total_before": usage.tool_calls_total,
                "tool_calls_total_limit": config.max_tool_calls_total,
                "tool_calls_for_tool_before": usage.tool_calls_per_tool.get(
                    tool_name, 0
                ),
                "tool_calls_for_tool_limit": tool_limit.max_calls if tool_limit else 0,
                "tokens_used": usage.tokens_used,
                "tokens_limit": config.max_tokens_per_session,
                "iterations_used": usage.iterations,
                "iterations_limit": config.get_max_iterations(),
            }
        )
    except Exception:  # noqa: BLE001
        logger.debug("tool budget metadata unavailable", exc_info=True)
        metadata["budget_metadata_available"] = False
    return metadata
