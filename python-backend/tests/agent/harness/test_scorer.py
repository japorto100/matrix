"""Tests for agent/harness/scorer.py — composite fitness + A/B backfill."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.harness import scorer


def test_composite_fitness_perfect_session():
    """All dimensions at their best → fitness close to 1.0."""
    s = {
        "tool_success_rate": 1.0,
        "tool_calls": 5,
        "completed": True,
        "session_status": "completed",
        "turn_efficiency": 1.0,
        "memory_utilization": True,
        "cost_estimate_usd": 0.0,
    }
    assert scorer.composite_fitness(s) == pytest.approx(1.0, abs=0.01)


def test_composite_fitness_errored_session_drops():
    """errored session_status must zero out the completion weight."""
    s = {
        "tool_success_rate": 1.0,
        "tool_calls": 0,
        "completed": True,
        "session_status": "errored",
        "turn_efficiency": 1.0,
        "memory_utilization": True,
        "cost_estimate_usd": 0.0,
    }
    # completed weight (0.25) goes to 0 → max fitness ~0.75
    assert 0.7 <= scorer.composite_fitness(s) <= 0.8


def test_composite_fitness_no_tool_calls_doesnt_penalise():
    s = {
        "tool_success_rate": 0.0,   # would be 0 because tool_calls == 0
        "tool_calls": 0,
        "completed": True,
        "session_status": "completed",
        "turn_efficiency": 0.5,
        "memory_utilization": False,
        "cost_estimate_usd": 0.01,
    }
    fitness = scorer.composite_fitness(s)
    # tsr treated as 1.0 because no tool calls → no failures possible
    assert fitness > 0.5


def test_composite_fitness_expensive_session_hurts():
    cheap = {
        "tool_success_rate": 1.0,
        "tool_calls": 1,
        "completed": True,
        "session_status": "completed",
        "turn_efficiency": 1.0,
        "memory_utilization": True,
        "cost_estimate_usd": 0.01,
    }
    expensive = {**cheap, "cost_estimate_usd": 100.0}
    assert scorer.composite_fitness(cheap) > scorer.composite_fitness(expensive)


def test_composite_fitness_handles_missing_fields():
    assert 0.0 <= scorer.composite_fitness({}) <= 1.0
    assert 0.0 <= scorer.composite_fitness({"completed": None}) <= 1.0


def test_composite_fitness_handles_malformed_types():
    s = {
        "tool_success_rate": "not-a-number",
        "turn_efficiency": None,
        "cost_estimate_usd": "free",
        "completed": True,
        "session_status": "completed",
    }
    assert 0.0 <= scorer.composite_fitness(s) <= 1.0


def test_composite_fitness_clamped_to_unit_interval():
    # Even with crazy input, output must stay in [0, 1]
    s = {
        "tool_success_rate": 5.0,
        "completed": True,
        "session_status": "completed",
        "turn_efficiency": 99.0,
        "memory_utilization": True,
        "cost_estimate_usd": -10.0,
    }
    f = scorer.composite_fitness(s)
    assert 0.0 <= f <= 1.0


def test_composite_fitness_accepts_custom_weights():
    s = {
        "tool_success_rate": 0.0,
        "tool_calls": 1,
        "completed": True,
        "session_status": "completed",
        "turn_efficiency": 0.0,
        "memory_utilization": False,
        "cost_estimate_usd": 0.0,
    }
    weights = scorer.ScoreWeights(
        tool_success_rate=0.0,
        completion=1.0,
        turn_efficiency=0.0,
        memory_utilization=0.0,
        cost_inverse=0.0,
    )
    assert scorer.composite_fitness(s, weights=weights) == 1.0


@pytest.mark.asyncio
async def test_audit_session_scorer_implements_interface(monkeypatch):
    async def _fake_score_session(thread_id, *, eval_id=None):
        return {"thread_id": thread_id, "eval_id": eval_id}

    monkeypatch.setattr(scorer, "score_session", _fake_score_session)

    audit_scorer = scorer.AuditSessionScorer()
    result = await audit_scorer.score_session("t-1", eval_id="eval-1")

    assert result == {"thread_id": "t-1", "eval_id": "eval-1"}


@pytest.mark.asyncio
async def test_backfill_returns_false_without_ids():
    assert await scorer.backfill_ab_experiment_fitness(
        thread_id="", fitness_score=0.5,
    ) is False


@pytest.mark.asyncio
async def test_backfill_calls_psycopg_with_thread_id(monkeypatch):
    """When no session_id is given, UPDATE by thread_id."""
    captured: dict = {}

    class _FakeConn:
        async def execute(self, sql: str, params):
            captured["sql"] = sql
            captured["params"] = params

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

    class _FakePsycopg:
        class AsyncConnection:
            @staticmethod
            async def connect(dsn, autocommit=False):
                return _FakeConn()

    import sys

    monkeypatch.setitem(sys.modules, "psycopg", _FakePsycopg())

    ok = await scorer.backfill_ab_experiment_fitness(
        thread_id="t-xyz", fitness_score=0.75, eval_id="eval-1",
    )
    assert ok is True
    assert "UPDATE agent.ab_experiments" in captured["sql"]
    assert "thread_id = %s" in captured["sql"]
    assert captured["params"] == (0.75, "eval-1", "t-xyz")


@pytest.mark.asyncio
async def test_backfill_calls_psycopg_with_session_id(monkeypatch):
    captured: dict = {}

    class _FakeConn:
        async def execute(self, sql: str, params):
            captured["sql"] = sql
            captured["params"] = params

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

    class _FakePsycopg:
        class AsyncConnection:
            @staticmethod
            async def connect(dsn, autocommit=False):
                return _FakeConn()

    import sys

    monkeypatch.setitem(sys.modules, "psycopg", _FakePsycopg())

    ok = await scorer.backfill_ab_experiment_fitness(
        thread_id="t-xyz", session_id="s-abc", fitness_score=0.9,
    )
    assert ok is True
    assert "session_id = %s" in captured["sql"]
    assert captured["params"] == (0.9, None, "s-abc")


@pytest.mark.asyncio
async def test_backfill_fail_soft_on_db_error(monkeypatch):
    """DB exception must not propagate — scorer callers rely on fail-soft."""
    class _FakePsycopg:
        class AsyncConnection:
            @staticmethod
            async def connect(dsn, autocommit=False):
                raise RuntimeError("db-down")

    import sys

    monkeypatch.setitem(sys.modules, "psycopg", _FakePsycopg())

    ok = await scorer.backfill_ab_experiment_fitness(
        thread_id="t-xyz", fitness_score=0.5,
    )
    assert ok is False


@pytest.mark.asyncio
async def test_score_session_dispatches_backfill(monkeypatch):
    """score_session must schedule the backfill as a fire-and-forget task."""
    calls = {"n": 0, "args": None}

    async def _fake_backfill(**kwargs):
        calls["n"] += 1
        calls["args"] = kwargs
        return True

    class _FakeStore:
        async def query(self, *args, **kwargs):
            return [
                {
                    "action": "llm_response",
                    "duration_ms": 10,
                    "metadata": {"token_usage": 100, "model": "gpt-4o", "done": True},
                },
            ]

    def _fake_get_store():
        return _FakeStore()

    def _fake_get_session(thread_id):
        return {"status": "completed", "summary": {}}

    with patch("agent.audit.store.get_audit_store", _fake_get_store), patch(
        "agent.sessions.get_session", _fake_get_session
    ), patch.object(scorer, "backfill_ab_experiment_fitness", _fake_backfill):
        import asyncio

        result = await scorer.score_session("t-dispatch-test")
        # Give the create_task callback a moment to run.
        await asyncio.sleep(0.05)

    assert "fitness_score" in result
    assert 0.0 <= result["fitness_score"] <= 1.0
    assert calls["n"] == 1
    assert calls["args"]["thread_id"] == "t-dispatch-test"
    assert calls["args"]["fitness_score"] == result["fitness_score"]
    # Default: no eval_id forwarded for ad-hoc invocations.
    assert calls["args"]["eval_id"] is None


@pytest.mark.asyncio
async def test_score_session_forwards_eval_id(monkeypatch):
    """§4g.4: when score_session is called with eval_id, it must flow into
    backfill_ab_experiment_fitness so harness_eval_id gets populated."""
    calls = {"args": None}

    async def _fake_backfill(**kwargs):
        calls["args"] = kwargs
        return True

    class _FakeStore:
        async def query(self, *args, **kwargs):
            return [
                {
                    "action": "llm_response",
                    "duration_ms": 10,
                    "metadata": {"token_usage": 100, "model": "gpt-4o", "done": True},
                },
            ]

    with patch("agent.audit.store.get_audit_store", lambda: _FakeStore()), patch(
        "agent.sessions.get_session", lambda tid: {"status": "completed", "summary": {}}
    ), patch.object(scorer, "backfill_ab_experiment_fitness", _fake_backfill):
        import asyncio

        await scorer.score_session("t-eval-test", eval_id="run-xyz")
        await asyncio.sleep(0.05)

    assert calls["args"] is not None
    assert calls["args"]["eval_id"] == "run-xyz"


@pytest.mark.asyncio
async def test_score_sessions_forwards_eval_id():
    """score_sessions must forward eval_id to every per-session score_session call."""
    forwarded: list[str | None] = []

    async def _fake_score_session(tid, *, eval_id=None):
        forwarded.append(eval_id)
        return {"thread_id": tid, "fitness_score": 0.5}

    with patch.object(scorer, "score_session", _fake_score_session):
        results = await scorer.score_sessions(["a", "b", "c"], eval_id="eval-batch-1")

    assert forwarded == ["eval-batch-1", "eval-batch-1", "eval-batch-1"]
    assert len(results) == 3
