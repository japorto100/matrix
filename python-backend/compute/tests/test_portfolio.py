"""Tests for indicator_engine.portfolio — Rust-backed portfolio analytics.

Expected values are derived from the algorithm definitions:
  drawdown:      (equity[i] - running_max) / running_max
  rolling_sharpe: (mean - rf) / std * sqrt(252), NaN during warmup
  kelly:         mu / sigma², capped at [-2, 2]; half_kelly = kelly / 2
"""

from __future__ import annotations

import math

import pytest

from indicator_engine.portfolio import (
    DrawdownRequest,
    KellyRequest,
    RollingSharpeRequest,
    calculate_kelly_fraction,
    calculate_portfolio_drawdown,
    calculate_rolling_sharpe,
)


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------


class TestPortfolioDrawdown:
    def test_known_values(self) -> None:
        """[100, 90, 80, 100, 90] → underwater=[0, -0.1, -0.2, 0, -0.1]"""
        req = DrawdownRequest(equity=[100.0, 90.0, 80.0, 100.0, 90.0])
        resp = calculate_portfolio_drawdown(req)
        expected = [0.0, -0.1, -0.2, 0.0, -0.1]
        assert len(resp.underwater) == 5
        for pt, exp in zip(resp.underwater, expected):
            assert pt.value == pytest.approx(exp, abs=1e-9)
        assert resp.max_drawdown == pytest.approx(-0.2, abs=1e-9)

    def test_monotone_rise_no_drawdown(self) -> None:
        """Steadily rising equity → all zeros."""
        equity = [100.0 + i * 5.0 for i in range(20)]
        resp = calculate_portfolio_drawdown(DrawdownRequest(equity=equity))
        for pt in resp.underwater:
            assert pt.value == pytest.approx(0.0, abs=1e-10)
        assert resp.max_drawdown == pytest.approx(0.0, abs=1e-10)

    def test_single_peak_then_fall(self) -> None:
        """Peak at index 0, then falls: all values <= 0."""
        equity = [200.0, 180.0, 160.0, 140.0, 100.0]
        resp = calculate_portfolio_drawdown(DrawdownRequest(equity=equity))
        assert resp.underwater[0].value == pytest.approx(0.0, abs=1e-10)
        for pt in resp.underwater[1:]:
            assert pt.value < 0.0
        assert resp.max_drawdown == pytest.approx(-0.5, abs=1e-9)

    def test_output_length_matches_input(self, closes_1000: list[float]) -> None:
        resp = calculate_portfolio_drawdown(DrawdownRequest(equity=closes_1000))
        assert len(resp.underwater) == 1000

    def test_engine_is_rust_or_python(self, closes_1000: list[float]) -> None:
        resp = calculate_portfolio_drawdown(DrawdownRequest(equity=closes_1000))
        assert resp.engine in ("rust", "python")

    def test_values_nonpositive(self, closes_1000: list[float]) -> None:
        """Drawdown values must be in [-1, 0]."""
        resp = calculate_portfolio_drawdown(DrawdownRequest(equity=closes_1000))
        for pt in resp.underwater:
            assert -1.0 <= pt.value <= 0.0 + 1e-10


# ---------------------------------------------------------------------------
# Rolling Sharpe
# ---------------------------------------------------------------------------


class TestRollingSharpe:
    def test_warmup_positions_are_none(self, closes_1000: list[float]) -> None:
        returns = [closes_1000[i] / closes_1000[i - 1] - 1.0 for i in range(1, 100)]
        resp = calculate_rolling_sharpe(RollingSharpeRequest(returns=returns, window=20))
        # First 19 positions should be None (warmup)
        for pt in resp.series[:19]:
            assert pt.sharpe is None

    def test_non_warmup_positions_are_finite(self, closes_1000: list[float]) -> None:
        returns = [closes_1000[i] / closes_1000[i - 1] - 1.0 for i in range(1, 100)]
        resp = calculate_rolling_sharpe(RollingSharpeRequest(returns=returns, window=20))
        for pt in resp.series[19:]:
            assert pt.sharpe is not None
            assert math.isfinite(pt.sharpe)

    def test_constant_returns_sharpe_zero(self) -> None:
        """Constant returns → std=0 → sharpe=0.0 (not NaN)."""
        returns = [0.005] * 30
        resp = calculate_rolling_sharpe(RollingSharpeRequest(returns=returns, window=10))
        for pt in resp.series[9:]:
            assert pt.sharpe == pytest.approx(0.0, abs=1e-8)

    def test_output_length_matches_input(self) -> None:
        returns = [0.01] * 50
        resp = calculate_rolling_sharpe(RollingSharpeRequest(returns=returns, window=20))
        assert len(resp.series) == 50

    def test_avg_sharpe_matches_valid_series(self) -> None:
        returns = [0.01, -0.005] * 25  # alternating
        resp = calculate_rolling_sharpe(RollingSharpeRequest(returns=returns, window=10))
        valid = [pt.sharpe for pt in resp.series if pt.sharpe is not None]
        if valid:
            expected_avg = sum(valid) / len(valid)
            assert resp.avg_sharpe == pytest.approx(expected_avg, abs=1e-4)

    def test_engine_field_present(self) -> None:
        resp = calculate_rolling_sharpe(RollingSharpeRequest(returns=[0.01] * 30))
        assert resp.engine in ("rust", "python")


# ---------------------------------------------------------------------------
# Kelly Fraction
# ---------------------------------------------------------------------------


class TestKellyFraction:
    def test_mixed_returns_positive_kelly(self) -> None:
        """60% wins at +2%, 40% losses at -1% → positive Kelly."""
        returns = [0.02] * 60 + [-0.01] * 40
        resp = calculate_kelly_fraction(KellyRequest(returns=returns))
        assert resp.kelly_fraction > 0.0
        assert resp.half_kelly == pytest.approx(resp.kelly_fraction / 2.0, abs=1e-9)

    def test_negative_returns_negative_kelly(self) -> None:
        """Mostly losing returns → negative Kelly."""
        returns = [-0.02] * 70 + [0.01] * 30
        resp = calculate_kelly_fraction(KellyRequest(returns=returns))
        assert resp.kelly_fraction < 0.0

    def test_capped_at_bounds(self) -> None:
        """Kelly is always within [-2, 2]."""
        # Extremely skewed returns to force a large Kelly before capping
        returns = [1.0] * 99 + [-0.001]
        resp = calculate_kelly_fraction(KellyRequest(returns=returns))
        assert -2.0 <= resp.kelly_fraction <= 2.0

    def test_constant_returns_zero(self) -> None:
        """Constant returns → variance=0 → kelly=0.0."""
        returns = [0.01] * 50
        resp = calculate_kelly_fraction(KellyRequest(returns=returns))
        assert resp.kelly_fraction == pytest.approx(0.0, abs=1e-9)
        assert resp.half_kelly == pytest.approx(0.0, abs=1e-9)

    def test_half_kelly_is_half(self) -> None:
        returns = [0.02, -0.01, 0.03, -0.005, 0.015] * 20
        resp = calculate_kelly_fraction(KellyRequest(returns=returns))
        assert resp.half_kelly == pytest.approx(resp.kelly_fraction / 2.0, abs=1e-9)

    def test_engine_field(self) -> None:
        resp = calculate_kelly_fraction(KellyRequest(returns=[0.01, 0.02, -0.005]))
        assert resp.engine in ("rust", "python")
