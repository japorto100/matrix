"""Tests for agent/billing/insights.py (InsightsEngine over agent.spans)."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from agent.billing.insights import InsightsEngine, InsightsReport


class _FakeCursor:
    """Minimal sync-cursor that satisfies InsightsEngine._fetch."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._description = (
            [(k,) for k in rows[0].keys()] if rows else [("span_id",), ("attributes",)]
        )

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *exc) -> None:
        pass

    @property
    def description(self):
        return self._description

    def execute(self, sql, params):
        return self

    def fetchall(self):
        return [tuple(r.get(k[0]) for k in self._description) for r in self._rows]


class _FakeConn:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self._rows)


def _span(
    *,
    session_id: str = "sess1",
    name: str = "agent.turn",
    cost: str | None = "0.05",
    input_tokens: int = 1000,
    output_tokens: int = 500,
    model: str = "gpt-4o",
    **extra_attrs,
) -> dict:
    attrs = {
        "llm.input_tokens": input_tokens,
        "llm.completion_tokens": output_tokens,
        "llm.model": model,
    }
    if cost is not None:
        attrs["llm.cost_usd"] = cost
    attrs.update(extra_attrs)
    return {
        "span_id": f"sp_{name}_{session_id}",
        "trace_id": "tr1",
        "name": name,
        "attributes": attrs,
        "events": [],
        "start_time": "2026-04-20T10:00:00+00:00",
        "session_id": session_id,
    }


@pytest.mark.asyncio
async def test_generate_basic_aggregation():
    spans = [
        _span(session_id="sess1", input_tokens=1000, output_tokens=500, cost="0.05"),
        _span(session_id="sess1", input_tokens=2000, output_tokens=1000, cost="0.10"),
        _span(session_id="sess2", input_tokens=500, output_tokens=200, cost="0.02"),
    ]
    engine = InsightsEngine(_FakeConn(spans))
    report = await engine.generate("u1", days=7)

    assert isinstance(report, InsightsReport)
    assert report.total_sessions == 2
    assert report.total_turns == 3  # all spans are agent.turn
    assert report.total_input_tokens == 3500
    assert report.total_output_tokens == 1700
    assert report.total_cost_usd == Decimal("0.17")
    assert report.cost_status == "known"
    assert report.per_model_cost["gpt-4o"] == Decimal("0.17")
    assert report.per_model_tokens["gpt-4o"] == 5200


@pytest.mark.asyncio
async def test_generate_with_unknown_cost():
    spans = [
        _span(session_id="sess1", cost="0.05"),
        _span(session_id="sess1", cost=None),  # missing cost attribute
    ]
    engine = InsightsEngine(_FakeConn(spans))
    report = await engine.generate("u1", days=7)
    assert report.cost_status == "partial"
    assert report.total_cost_usd == Decimal("0.05")


@pytest.mark.asyncio
async def test_generate_empty_window():
    engine = InsightsEngine(_FakeConn([]))
    report = await engine.generate("u1", days=7)
    assert report.total_sessions == 0
    assert report.total_cost_usd == Decimal("0")
    # No spans at all → no "unknown" flag ever set → status stays "known"
    # which is the correct degenerate answer (nothing to report).
    assert report.cost_status == "known"


@pytest.mark.asyncio
async def test_cost_for_session():
    spans = [
        _span(session_id="sess1", cost="0.05"),
        _span(session_id="sess1", cost="0.07"),
    ]
    engine = InsightsEngine(_FakeConn(spans))
    total = await engine.cost_for_session("sess1")
    assert total == Decimal("0.12")


@pytest.mark.asyncio
async def test_attributes_may_arrive_as_json_string():
    spans = [
        {
            "span_id": "sp1",
            "trace_id": "t1",
            "name": "agent.turn",
            "attributes": json.dumps({
                "llm.input_tokens": 100,
                "llm.completion_tokens": 50,
                "llm.cost_usd": "0.01",
                "llm.model": "gpt-4o",
            }),
            "events": [],
            "start_time": "2026-04-20T10:00:00+00:00",
            "session_id": "s1",
        },
    ]
    engine = InsightsEngine(_FakeConn(spans))
    report = await engine.generate("u1", days=7)
    assert report.total_cost_usd == Decimal("0.01")


def test_to_json_shape():
    now = datetime(2026, 4, 20, tzinfo=UTC)
    report = InsightsReport(
        user_id="u1",
        since=now,
        until=now,
        total_sessions=1,
        total_turns=3,
        total_input_tokens=100,
        total_output_tokens=50,
        total_cache_read_tokens=0,
        total_cache_write_tokens=0,
        total_cost_usd=Decimal("0.01"),
        cost_status="known",
        per_model_cost={"gpt-4o": Decimal("0.01")},
        per_model_tokens={"gpt-4o": 150},
    )
    shape = report.to_json()
    assert shape["total_cost_usd"] == "0.01"
    assert shape["per_model_cost"]["gpt-4o"] == "0.01"
