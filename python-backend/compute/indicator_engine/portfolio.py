"""portfolio.py — Synchronous portfolio analytics with Rust fast-path.

Extracted from pipeline.py (Phase A, 20.03.2026).

Functions here are data-agnostic (no Go-gateway calls) and purely computational.
They are called by portfolio_analytics.py (the async, Go-fetch layer) as hot-path
replacements for numpy computations.

Endpoints:
  calculate_portfolio_drawdown  — underwater curve + max drawdown
  calculate_rolling_sharpe      — rolling annualised Sharpe series + summary
  calculate_kelly_fraction      — single-asset Kelly fraction

Rust fast-path: portfolio_drawdown_series, portfolio_rolling_sharpe,
                portfolio_kelly_fraction (all via rust_bridge.py).
Python fallback: pure Python implementation with no external dependencies.
"""

from __future__ import annotations

import math
from statistics import mean, stdev

from pydantic import BaseModel, Field

from indicator_engine.rust_bridge import (
    portfolio_drawdown_series as rust_drawdown,
    portfolio_kelly_fraction as rust_kelly,
    portfolio_rolling_sharpe as rust_rolling_sharpe,
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DrawdownRequest(BaseModel):
    equity: list[float] = Field(..., min_length=1)


class DrawdownPoint(BaseModel):
    index: int
    value: float  # 0.0 at peak, negative fraction in drawdown (e.g. -0.12 = -12%)


class DrawdownResponse(BaseModel):
    underwater: list[DrawdownPoint]
    max_drawdown: float  # most negative value, e.g. -0.25
    engine: str


class RollingSharpeRequest(BaseModel):
    returns: list[float] = Field(..., min_length=2)
    window: int = 20
    rf_annual: float = 0.04  # annualised risk-free rate


class RollingSharpePoint(BaseModel):
    index: int
    sharpe: float | None  # None for warmup positions


class RollingSharpeResponse(BaseModel):
    series: list[RollingSharpePoint]
    avg_sharpe: float | None
    engine: str


class KellyRequest(BaseModel):
    returns: list[float] = Field(..., min_length=2)


class KellyResponse(BaseModel):
    kelly_fraction: float   # raw Kelly (mu / sigma²), capped at [-2, 2]
    half_kelly: float       # conventional risk-managed sizing
    engine: str


# ---------------------------------------------------------------------------
# Python fallbacks
# ---------------------------------------------------------------------------


def _py_drawdown(equity: list[float]) -> list[float]:
    """Underwater curve: (equity[i] - running_max) / running_max."""
    out: list[float] = []
    running_max = equity[0]
    for e in equity:
        if e > running_max:
            running_max = e
        dd = (e - running_max) / running_max if running_max > 0.0 else 0.0
        out.append(dd)
    return out


def _py_rolling_sharpe(
    returns: list[float], window: int, rf_daily: float
) -> list[float]:
    n = len(returns)
    out = [float("nan")] * n
    ann = math.sqrt(252.0)
    for i in range(window - 1, n):
        sl = returns[i + 1 - window : i + 1]
        m = mean(sl)
        if len(sl) < 2:
            out[i] = 0.0
            continue
        s = stdev(sl)
        out[i] = (m - rf_daily) / s * ann if s > 1e-12 else 0.0
    return out


def _py_kelly(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    m = mean(returns)
    s = stdev(returns)
    var = s * s
    if var <= 1e-14:
        return 0.0
    return max(-2.0, min(2.0, m / var))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def calculate_portfolio_drawdown(req: DrawdownRequest) -> DrawdownResponse:
    """Underwater curve for an equity series.

    Expected values (for reference / tests):
        equity=[100, 90, 80, 100, 90]
        → underwater=[0.0, -0.1, -0.2, 0.0, -0.1]
        → max_drawdown=-0.2
    """
    rust_result = rust_drawdown(req.equity)
    if rust_result is not None and len(rust_result) == len(req.equity):
        underwater = rust_result
        engine = "rust"
    else:
        underwater = _py_drawdown(req.equity)
        engine = "python"

    max_dd = min(underwater) if underwater else 0.0
    points = [DrawdownPoint(index=i, value=v) for i, v in enumerate(underwater)]
    return DrawdownResponse(underwater=points, max_drawdown=max_dd, engine=engine)


def calculate_rolling_sharpe(req: RollingSharpeRequest) -> RollingSharpeResponse:
    """Rolling annualised Sharpe ratio series.

    Positions before the first full window are None (warmup).
    Expected values (for reference):
        constant returns of 0.005/day, window=5, rf=0
        → std=0 → sharpe=0.0 at every non-NaN position
    """
    rf_daily = req.rf_annual / 252.0
    rust_result = rust_rolling_sharpe(req.returns, req.window, rf_daily)
    if rust_result is not None and len(rust_result) == len(req.returns):
        raw = rust_result
        engine = "rust"
    else:
        raw = _py_rolling_sharpe(req.returns, req.window, rf_daily)
        engine = "python"

    series: list[RollingSharpePoint] = []
    valid: list[float] = []
    for i, v in enumerate(raw):
        if math.isnan(v):
            series.append(RollingSharpePoint(index=i, sharpe=None))
        else:
            series.append(RollingSharpePoint(index=i, sharpe=round(v, 6)))
            valid.append(v)

    avg = round(mean(valid), 6) if valid else None
    return RollingSharpeResponse(series=series, avg_sharpe=avg, engine=engine)


def calculate_kelly_fraction(req: KellyRequest) -> KellyResponse:
    """Single-asset Kelly criterion: mu / sigma² (capped [-2, 2]).

    Expected values (for reference):
        all-positive returns (0.02) with slight variance → positive Kelly
        mixed returns (60% wins at +2%, 40% losses at -1%) → positive Kelly > 0
        constant returns → var=0 → kelly=0.0

    half_kelly = kelly / 2 — standard risk-managed sizing recommendation.
    """
    rust_result = rust_kelly(req.returns)
    if rust_result is not None:
        k = rust_result
        engine = "rust"
    else:
        k = _py_kelly(req.returns)
        engine = "python"

    return KellyResponse(
        kelly_fraction=round(k, 6),
        half_kelly=round(k / 2.0, 6),
        engine=engine,
    )
