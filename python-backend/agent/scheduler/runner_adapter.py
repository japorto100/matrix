"""Adapter for invoking the agent graph from a non-HTTP trigger.

``run_agent_loop`` yields SSE strings bound to an AsyncGenerator — ideal
for web responses, useless for the NATS subscriber that just needs the
final response text + tool-call summary to write into task_executions.

``execute_for_scheduler`` drains the generator, parses the few SSE packet
types we care about, and returns a structured result.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from agent.context import AgentExecutionContext
from agent.graph.runner import run_agent_loop


@dataclass
class ToolCallSummary:
    name: str
    input_preview: str
    error: str | None = None


@dataclass
class SchedulerTurnResult:
    """Collected output of an agent turn run from a scheduled-task fire."""

    final_text: str
    tool_calls: list[ToolCallSummary] = field(default_factory=list)
    error: str | None = None
    trace_id: str | None = None


_SSE_DATA = re.compile(r"^data:\s*(\{.*\})\s*$", re.MULTILINE)


async def execute_for_scheduler(
    ctx: AgentExecutionContext,
    messages: list[dict],
) -> SchedulerTurnResult:
    """Drain ``run_agent_loop`` and return the compacted turn result.

    Errors raised during the stream are captured as ``result.error`` —
    the caller (subscriber) decides whether to surface them to the user
    via delivery or only log + record to task_executions.
    """
    text_buf: list[str] = []
    tool_calls: list[ToolCallSummary] = []
    error: str | None = None
    trace_id: str | None = None

    try:
        async for chunk in run_agent_loop(ctx, messages):
            for match in _SSE_DATA.finditer(chunk):
                try:
                    pkt = json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
                kind = pkt.get("type") or pkt.get("kind")
                if kind == "text-delta":
                    text_buf.append(pkt.get("text", "") or pkt.get("delta", ""))
                elif kind in ("tool-start", "tool-input-start"):
                    tool_calls.append(
                        ToolCallSummary(
                            name=pkt.get("tool_name", "") or pkt.get("toolName", ""),
                            input_preview=json.dumps(pkt.get("input", {}))[:200],
                        )
                    )
                elif kind in ("tool-error", "tool-output-error"):
                    if tool_calls:
                        tool_calls[-1].error = (
                            pkt.get("error", "") or pkt.get("errorText", "")
                        )
                elif kind == "thread-id":
                    trace_id = pkt.get("thread_id") or pkt.get("threadId") or trace_id
                elif kind == "start":
                    # AI-SDK v6 'start' packet carries messageId which we use as thread id.
                    trace_id = pkt.get("messageId") or pkt.get("message_id") or trace_id
                elif kind == "message-metadata":
                    md = pkt.get("metadata") or {}
                    trace_id = md.get("threadId") or md.get("thread_id") or trace_id
                elif kind == "finish":
                    break
    except Exception as exc:  # noqa: BLE001 — we want any failure recorded
        error = f"{type(exc).__name__}: {exc}"

    final_text = "".join(text_buf).strip()
    return SchedulerTurnResult(
        final_text=final_text,
        tool_calls=tool_calls,
        error=error,
        trace_id=trace_id,
    )


def summary_line(result: SchedulerTurnResult, max_len: int = 480) -> str:
    """Single-line description for scheduler.task_executions.result_summary.

    Control-UI list page surfaces this next to the task row; keep short.
    """
    if result.error:
        return f"error: {result.error}"[:max_len]
    head = result.final_text.splitlines()[0] if result.final_text else ""
    if len(result.tool_calls) > 0:
        head = f"[{len(result.tool_calls)} tools] {head}"
    return head[:max_len]
