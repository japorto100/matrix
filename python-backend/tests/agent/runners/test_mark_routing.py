"""ADR-001 G4 — _mark_routing fire-and-forget UPDATE helper."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.runners import dispatcher


def _make_fake_conn(record):
    cursor = MagicMock()
    cursor.fetchone = AsyncMock(return_value=None)

    async def _capture_execute(sql, params):
        record["sql"] = sql
        record["params"] = params
        return cursor

    conn = MagicMock()
    conn.execute = AsyncMock(side_effect=_capture_execute)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    return conn


@pytest.mark.asyncio
async def test_mark_routing_no_row_id_is_noop(monkeypatch):
    called = {"n": 0}

    async def fake_connect(_dsn, **_kw):
        called["n"] += 1
        return _make_fake_conn({})

    monkeypatch.setattr("psycopg.AsyncConnection.connect", fake_connect)
    await dispatcher._mark_routing(
        "", routing_used=True, routing_reason="simple_turn", routing_picked_model="x",
    )
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_mark_routing_writes_all_three_columns(monkeypatch):
    record: dict = {}

    async def fake_connect(_dsn, **_kw):
        return _make_fake_conn(record)

    monkeypatch.setattr("psycopg.AsyncConnection.connect", fake_connect)

    await dispatcher._mark_routing(
        "row-123",
        routing_used=True,
        routing_reason="simple_turn",
        routing_picked_model="gpt-4o-mini",
    )

    assert "UPDATE agent.ab_experiments" in record["sql"]
    assert "routing_used" in record["sql"]
    assert "routing_reason" in record["sql"]
    assert "routing_picked_model" in record["sql"]
    assert record["params"] == (True, "simple_turn", "gpt-4o-mini", "row-123")


@pytest.mark.asyncio
async def test_mark_routing_swallows_db_errors(monkeypatch):
    """Telemetry must never break the LLM call."""
    async def fake_connect(_dsn, **_kw):
        raise RuntimeError("db down")

    monkeypatch.setattr("psycopg.AsyncConnection.connect", fake_connect)

    # Must not raise.
    await dispatcher._mark_routing(
        "row-456",
        routing_used=False,
        routing_reason="complex_heuristic",
        routing_picked_model="claude-opus-4-7",
    )


@pytest.mark.asyncio
async def test_dispatcher_threads_ab_row_id_into_context():
    """dataclasses.replace must produce a ctx with ab_row_id set before runner runs."""
    from agent.context import AgentExecutionContext

    captured_ctx: dict = {}

    async def fake_runner(ctx, _messages):
        captured_ctx["ctx"] = ctx
        yield "data: stub\n\n"

    ctx = AgentExecutionContext(
        user_id="alice",
        thread_id="t-1",
        model="claude-opus-4-7",
        system_prompt="sys",
        tools=(),
    )

    with patch.object(dispatcher, "select_variant", AsyncMock(return_value=("langgraph", 0))), \
         patch("agent.runners.dispatcher._insert_ab_row", AsyncMock()), \
         patch("agent.graph.runner.run_agent_loop", fake_runner):
        gen = dispatcher.run_agent_loop_with_variant(ctx, [])
        async for _ in gen:
            pass

    assert "ctx" in captured_ctx
    assert captured_ctx["ctx"].ab_row_id, (
        "dispatcher must set ctx.ab_row_id before invoking runner"
    )
    # Must look like a UUID hex-ish string.
    assert len(captured_ctx["ctx"].ab_row_id) >= 32
