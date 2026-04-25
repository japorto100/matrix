from __future__ import annotations

import asyncio

import pytest

from agent.harness import evaluator


@pytest.mark.asyncio
async def test_evaluate_search_set_runs_queries_in_parallel(monkeypatch):
    running = 0
    max_running = 0

    monkeypatch.setattr(
        evaluator,
        "load_search_set",
        lambda: [
            {"id": "q1", "message": "one", "category": "smoke"},
            {"id": "q2", "message": "two", "category": "smoke"},
        ],
    )

    async def _fake_evaluate_single(query, **kwargs):
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        await asyncio.sleep(0.01)
        running -= 1
        return {
            "query_id": query["id"],
            "completed": True,
            "turns": 1,
            "total_tokens": 10,
            "tool_success_rate": 1.0,
            "cost_estimate_usd": 0.001,
        }

    monkeypatch.setattr(evaluator, "evaluate_single", _fake_evaluate_single)

    result = await evaluator.evaluate_search_set(
        concurrency=2,
        use_cache=False,
        eval_id="eval-parallel",
    )

    assert result["queries_evaluated"] == 2
    assert result["completion_rate"] == 1.0
    assert result["concurrency"] == 2
    assert max_running == 2


@pytest.mark.asyncio
async def test_evaluate_search_set_uses_json_cache(tmp_path, monkeypatch):
    calls = {"n": 0}
    cache = evaluator.EvaluationCache(tmp_path / "eval_cache.json")

    monkeypatch.setattr(
        evaluator,
        "load_search_set",
        lambda: [{"id": "q1", "message": "one", "category": "smoke"}],
    )

    async def _fake_evaluate_single(query, **kwargs):
        calls["n"] += 1
        return {
            "query_id": query["id"],
            "completed": True,
            "turns": 1,
            "total_tokens": 10,
            "tool_success_rate": 1.0,
            "cost_estimate_usd": 0.001,
        }

    monkeypatch.setattr(evaluator, "evaluate_single", _fake_evaluate_single)

    first = await evaluator.evaluate_search_set(cache=cache, use_cache=True)
    second = await evaluator.evaluate_search_set(cache=cache, use_cache=True)

    assert calls["n"] == 1
    assert first["cache_hits"] == 0
    assert second["cache_hits"] == 1
    assert second["per_query"][0]["cache_hit"] is True
