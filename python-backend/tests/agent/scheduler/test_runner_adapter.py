"""Tests for execute_for_scheduler — ensures the SSE generator drain path
produces a usable SchedulerTurnResult without hitting the real LLM.
"""

from __future__ import annotations

import pytest

from agent.context import AgentExecutionContext
from agent.scheduler.runner_adapter import (
    SchedulerTurnResult,
    execute_for_scheduler,
    summary_line,
)


async def _fake_generator_ok(*_args, **_kwargs):
    # Simulate the Vercel AI SSE wire format the runner emits.
    yield 'data: {"type": "thread-id", "thread_id": "trace-abc"}\n\n'
    yield 'data: {"type": "text-delta", "text": "Hello "}\n\n'
    yield 'data: {"type": "text-delta", "text": "World"}\n\n'
    yield 'data: {"type": "tool-start", "tool_name": "search", "input": {"q": "x"}}\n\n'
    yield 'data: {"type": "finish"}\n\n'


async def _fake_generator_error(*_args, **_kwargs):
    yield 'data: {"type": "text-delta", "text": "partial"}\n\n'
    raise RuntimeError("simulated failure")


@pytest.fixture
def fake_ctx():
    return AgentExecutionContext(
        user_id="test-user",
        thread_id="thread-1",
        model="claude-sonnet",
        system_prompt="",
        tools=(),
    )


async def test_execute_drains_text_and_toolcalls(monkeypatch, fake_ctx):
    import agent.scheduler.runner_adapter as mod

    monkeypatch.setattr(mod, "run_agent_loop", _fake_generator_ok)
    result = await execute_for_scheduler(fake_ctx, [])
    assert isinstance(result, SchedulerTurnResult)
    assert result.error is None
    assert "Hello World" in result.final_text
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search"
    assert result.trace_id == "trace-abc"


async def test_execute_captures_exception(monkeypatch, fake_ctx):
    import agent.scheduler.runner_adapter as mod

    monkeypatch.setattr(mod, "run_agent_loop", _fake_generator_error)
    result = await execute_for_scheduler(fake_ctx, [])
    assert result.error is not None
    assert "simulated failure" in result.error
    # Pre-error text-delta should still be captured.
    assert "partial" in result.final_text


def test_summary_line_error_path():
    result = SchedulerTurnResult(final_text="", error="boom")
    assert summary_line(result).startswith("error:")


def test_summary_line_happy_path():
    result = SchedulerTurnResult(
        final_text="first-line\nsecond line",
        tool_calls=[],
    )
    assert summary_line(result) == "first-line"


def test_summary_line_tool_prefix():
    from agent.scheduler.runner_adapter import ToolCallSummary

    result = SchedulerTurnResult(
        final_text="done",
        tool_calls=[ToolCallSummary(name="search", input_preview="{}")],
    )
    assert summary_line(result).startswith("[1 tools]")
