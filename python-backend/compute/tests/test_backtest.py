"""Tests for indicator_engine.backtest — backtest, triple barrier, walk-forward, sensitivity."""

from __future__ import annotations

from indicator_engine.backtest import (
    calculate_triple_barrier,
    run_backtest,
    run_parameter_sensitivity,
    run_walk_forward,
)
from indicator_engine.models import (
    BacktestRequest,
    ParameterSensitivityRequest,
    TripleBarrierRequest,
    WalkForwardRequest,
)


class TestRunBacktest:
    def test_returns_length(self, closes_1000: list[float]) -> None:
        req = BacktestRequest(closes=closes_1000, lookback=10)
        resp = run_backtest(req)
        assert len(resp.strategy_returns) == 999  # n-1 returns

    def test_cumulative_return_finite(self, closes_1000: list[float]) -> None:
        req = BacktestRequest(closes=closes_1000, lookback=10)
        resp = run_backtest(req)
        import math
        assert math.isfinite(resp.cumulative_return)

    def test_with_costs(self, closes_1000: list[float]) -> None:
        req_no_cost = BacktestRequest(closes=closes_1000, lookback=10)
        req_cost = BacktestRequest(closes=closes_1000, lookback=10, slippage_bps=10, commission_bps=10)
        resp_no = run_backtest(req_no_cost)
        resp_cost = run_backtest(req_cost)
        # With costs, cumulative return should be lower
        assert resp_cost.cumulative_return <= resp_no.cumulative_return


class TestTripleBarrier:
    def test_labels_valid(self, closes_1000: list[float]) -> None:
        req = TripleBarrierRequest(closes=closes_1000, horizon=10)
        resp = calculate_triple_barrier(req)
        for label in resp.labels:
            assert label in ("tp", "sl", "timeout")

    def test_counts_sum(self, closes_1000: list[float]) -> None:
        req = TripleBarrierRequest(closes=closes_1000, horizon=10)
        resp = calculate_triple_barrier(req)
        assert resp.tp_count + resp.sl_count + resp.timeout_count == len(resp.labels)

    def test_label_count(self, closes_1000: list[float]) -> None:
        req = TripleBarrierRequest(closes=closes_1000, horizon=10)
        resp = calculate_triple_barrier(req)
        assert len(resp.labels) == 990  # 1000 - horizon


class TestParameterSensitivity:
    def test_response(self, closes_1000: list[float]) -> None:
        req = ParameterSensitivityRequest(closes=closes_1000, lookbacks=[5, 10, 20, 50])
        resp = run_parameter_sensitivity(req)
        assert len(resp.by_lookback) == 4
        assert 0.0 < resp.stability_score <= 1.0


class TestWalkForward:
    def test_response(self, closes_1000: list[float]) -> None:
        req = WalkForwardRequest(closes=closes_1000, train_window=100, test_window=20)
        resp = run_walk_forward(req)
        assert len(resp.oos_scores) > 0
        assert 0.0 < resp.stability_score <= 1.0
