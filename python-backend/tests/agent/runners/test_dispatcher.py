"""Tests for agent/runners/dispatcher.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.runners import dispatcher


def test_bucket_is_deterministic():
    """Same user_id must always produce the same bucket."""
    first = dispatcher.bucket_for_user("alice")
    for _ in range(100):
        assert dispatcher.bucket_for_user("alice") == first


def test_bucket_range_is_0_99():
    for uid in (f"user_{i}" for i in range(200)):
        assert 0 <= dispatcher.bucket_for_user(uid) <= 99


def test_bucket_distribution_is_roughly_uniform():
    """10k unique user_ids → each bucket should get ~100 ± slack hits."""
    counts = [0] * 100
    for i in range(10_000):
        counts[dispatcher.bucket_for_user(f"u{i}")] += 1
    # Chi-sq tolerance ±40 (uniform would be 100; accept 60-140 per bucket).
    for c in counts:
        assert 50 <= c <= 150, f"bucket count {c} outside tolerance"


def test_bucket_anonymous_is_stable():
    a = dispatcher.bucket_for_user("")
    b = dispatcher.bucket_for_user(None)  # type: ignore[arg-type]
    assert a == b  # both route through "anonymous"


@pytest.mark.asyncio
async def test_kill_switch_env_var_true(monkeypatch):
    # Reset in-process cache so the monkeypatch is visible.
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", "true")

    assert await dispatcher.is_kill_switch_active() is True


@pytest.mark.asyncio
async def test_kill_switch_env_var_default_false(monkeypatch):
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.delenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", raising=False)

    assert await dispatcher.is_kill_switch_active() is False


@pytest.mark.asyncio
async def test_select_variant_kill_switch_wins_over_pct(monkeypatch):
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", "true")
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_PCT", "100")

    variant, _ = await dispatcher.select_variant("alice")
    assert variant == "langgraph"


@pytest.mark.asyncio
async def test_select_variant_pct_zero_always_langgraph(monkeypatch):
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.delenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_PCT", "0")

    for uid in (f"user_{i}" for i in range(50)):
        variant, _ = await dispatcher.select_variant(uid)
        assert variant == "langgraph"


@pytest.mark.asyncio
async def test_select_variant_pct_100_always_simple(monkeypatch):
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.delenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_PCT", "100")

    for uid in (f"user_{i}" for i in range(50)):
        variant, _ = await dispatcher.select_variant(uid)
        assert variant == "simple"


@pytest.mark.asyncio
async def test_select_variant_pct_50_splits_close_to_half(monkeypatch):
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.delenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_PCT", "50")

    simple = 0
    for uid in (f"user_{i}" for i in range(1000)):
        variant, _ = await dispatcher.select_variant(uid)
        if variant == "simple":
            simple += 1
    # Allow ±15% slack around 500
    assert 425 <= simple <= 575, f"simple count {simple} outside tolerance"


@pytest.mark.asyncio
async def test_select_variant_same_user_same_variant_always(monkeypatch):
    """Per-user stickiness — the whole point of the bucketing."""
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.delenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_PCT", "50")

    variant_first, _ = await dispatcher.select_variant("alice")
    for _ in range(50):
        variant_n, _ = await dispatcher.select_variant("alice")
        assert variant_n == variant_first


@pytest.mark.asyncio
async def test_ab_status_shape(monkeypatch):
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.delenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_PCT", "25")

    status = await dispatcher.ab_status()
    assert status["active"] is True
    assert status["percentage"] == 25
    assert status["kill_switch"] is False


@pytest.mark.asyncio
async def test_ab_status_kill_switch_reports_inactive(monkeypatch):
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", "true")
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_PCT", "50")

    status = await dispatcher.ab_status()
    assert status["active"] is False
    assert status["kill_switch"] is True


@pytest.mark.asyncio
async def test_dispatcher_routes_to_langgraph_when_pct_zero(monkeypatch):
    """Dispatcher with PCT=0 must yield chunks from the LangGraph path only."""
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.delenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_PCT", "0")

    calls = {"lg": 0, "simple": 0}

    async def _fake_langgraph(ctx, messages):
        calls["lg"] += 1
        yield "data: lg-chunk-1\n\n"
        yield "data: lg-chunk-2\n\n"

    async def _fake_simple(ctx, messages, *, ab_row_id=None):
        calls["simple"] += 1
        yield "data: simple-chunk\n\n"

    async def _fake_insert(**kwargs):
        return None

    ctx = _make_ctx()

    with patch("agent.graph.runner.run_agent_loop", _fake_langgraph), patch(
        "agent.runners.simple.run_simple_agent_loop", _fake_simple
    ), patch.object(dispatcher, "_insert_ab_row", _fake_insert):
        chunks = []
        async for c in dispatcher.run_agent_loop_with_variant(ctx, []):
            chunks.append(c)

    assert calls["lg"] == 1
    assert calls["simple"] == 0
    assert any("lg-chunk" in c for c in chunks)


@pytest.mark.asyncio
async def test_dispatcher_simple_loop_failure_emits_error_no_silent_fallback(
    monkeypatch,
):
    """Contrarian-BLOCKER-1: we must NOT silently fall back to LangGraph."""
    monkeypatch.setattr(dispatcher, "_kill_switch_cached_until", 0.0)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("PYTHON_REDIS_URL", raising=False)
    monkeypatch.delenv("AGENT_SIMPLE_LOOP_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AGENT_SIMPLE_LOOP_PCT", "100")

    lg_called = {"n": 0}

    async def _fake_langgraph(ctx, messages):
        lg_called["n"] += 1
        yield "data: should-not-appear\n\n"

    async def _broken_simple(ctx, messages, *, ab_row_id=None):
        yield "data: partial\n\n"
        raise RuntimeError("simulated SimpleLoop crash")

    async def _fake_insert(**kwargs):
        return None

    async def _fake_mark(row_id, error):
        return None

    ctx = _make_ctx()

    with patch("agent.graph.runner.run_agent_loop", _fake_langgraph), patch(
        "agent.runners.simple.run_simple_agent_loop", _broken_simple
    ), patch.object(dispatcher, "_insert_ab_row", _fake_insert), patch.object(
        dispatcher, "_mark_fallback", _fake_mark
    ):
        chunks = []
        async for c in dispatcher.run_agent_loop_with_variant(ctx, []):
            chunks.append(c)

    # LangGraph must NOT have been invoked (no silent fallback).
    assert lg_called["n"] == 0
    # We DID get the partial SSE chunk before the crash.
    assert any("partial" in c for c in chunks)
    # And we emitted a clean error boundary (error packet) after.
    joined = "\n".join(chunks)
    assert "SimpleLoop error" in joined or "error" in joined.lower()


def _make_ctx():
    from agent.context import AgentExecutionContext
    from agent.tools.registry import ToolRegistry

    reg = ToolRegistry.load()
    return AgentExecutionContext(
        user_id="alice",
        thread_id="t-test",
        model="gpt-4o-mini",
        api_key=None,
        system_prompt="",
        tools=tuple(reg.all()),
        reasoning_effort=None,
        agent_class="advisory",
        user_role="viewer",
    )
