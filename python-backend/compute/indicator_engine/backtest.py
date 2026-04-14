"""backtest.py — Backtesting and strategy validation.

Extracted from pipeline.py (Phase A, 20.03.2026).

Functions:
  run_backtest, calculate_triple_barrier, _triple_barrier_labels,
  run_parameter_sensitivity, run_walk_forward
"""

from __future__ import annotations

import math as _math
from statistics import pstdev
from typing import Literal

from indicator_engine.models import (
    BacktestRequest,
    BacktestResponse,
    ParameterSensitivityRequest,
    ParameterSensitivityResponse,
    TripleBarrierRequest,
    TripleBarrierResponse,
    WalkForwardRequest,
    WalkForwardResponse,
)
from indicator_engine.trend import sma


# ---------------------------------------------------------------------------
# Core backtest
# ---------------------------------------------------------------------------


def run_backtest(req: BacktestRequest) -> BacktestResponse:
    """Simple SMA crossover backtest with transaction costs."""
    c = req.closes
    ma = sma(c, req.lookback)
    rets: list[float] = []
    in_pos = False
    cost = (req.slippage_bps + req.commission_bps) / 10_000.0
    for i in range(1, len(c)):
        if c[i - 1] > ma[i - 1]:
            in_pos = True
        elif c[i - 1] < ma[i - 1]:
            in_pos = False
        if in_pos and c[i - 1] != 0:
            gross = (c[i] - c[i - 1]) / c[i - 1]
            rets.append(gross - cost)
        else:
            rets.append(0.0)
    cum = _math.prod(1.0 + r for r in rets) - 1.0 if rets else 0.0
    trades = sum(1 for i in range(1, len(c)) if (c[i - 1] > ma[i - 1]) != (c[i - 2] > ma[i - 2])) if len(c) > 2 else 0
    return BacktestResponse(strategy_returns=rets, cumulative_return=round(cum, 6), trade_count=trades)


# ---------------------------------------------------------------------------
# Triple Barrier
# ---------------------------------------------------------------------------


def _triple_barrier_labels(closes_vals: list[float], horizon: int, tp: float, sl: float) -> list[Literal["tp", "sl", "timeout"]]:
    """Triple barrier labeling."""
    labels: list[Literal["tp", "sl", "timeout"]] = []
    for i in range(0, len(closes_vals) - horizon):
        entry = closes_vals[i]
        up = entry * (1.0 + tp)
        dn = entry * (1.0 - sl)
        label: Literal["tp", "sl", "timeout"] = "timeout"
        for j in range(i + 1, i + horizon + 1):
            px = closes_vals[j]
            if px >= up:
                label = "tp"
                break
            if px <= dn:
                label = "sl"
                break
        labels.append(label)
    return labels


def calculate_triple_barrier(req: TripleBarrierRequest) -> TripleBarrierResponse:
    """Compute triple barrier labels for a price series."""
    labels = _triple_barrier_labels(req.closes, req.horizon, req.take_profit, req.stop_loss)
    tp = sum(1 for x in labels if x == "tp")
    sl = sum(1 for x in labels if x == "sl")
    timeout = len(labels) - tp - sl
    return TripleBarrierResponse(labels=labels, tp_count=tp, sl_count=sl, timeout_count=timeout)


# ---------------------------------------------------------------------------
# Parameter Sensitivity & Walk-Forward
# ---------------------------------------------------------------------------


def run_parameter_sensitivity(req: ParameterSensitivityRequest) -> ParameterSensitivityResponse:
    """Test strategy across multiple lookback periods."""
    results: dict[str, float] = {}
    vals: list[float] = []
    for lb in req.lookbacks:
        if lb < 2:
            continue
        bt = run_backtest(BacktestRequest(closes=req.closes, lookback=lb))
        results[str(lb)] = bt.cumulative_return
        vals.append(bt.cumulative_return)
    if not vals:
        return ParameterSensitivityResponse(by_lookback={}, stability_score=0.0)
    st = pstdev(vals) if len(vals) > 1 else 0.0
    stability = 1.0 / (1.0 + st)
    return ParameterSensitivityResponse(
        by_lookback={k: round(v, 6) for k, v in results.items()},
        stability_score=round(stability, 6),
    )


def run_walk_forward(req: WalkForwardRequest) -> WalkForwardResponse:
    """Walk-forward out-of-sample validation."""
    c = req.closes
    tw = req.train_window
    vw = req.test_window
    scores: list[float] = []
    i = 0
    while i + tw + vw <= len(c):
        train = c[i : i + tw]
        test = c[i + tw : i + tw + vw]
        train_bt = run_backtest(BacktestRequest(closes=train, lookback=min(10, max(2, tw // 4))))
        test_bt = run_backtest(BacktestRequest(closes=test, lookback=min(10, max(2, vw // 3))))
        base = abs(train_bt.cumulative_return) + 1e-9
        scores.append(test_bt.cumulative_return / base)
        i += vw
    if not scores:
        return WalkForwardResponse(oos_scores=[], mean_oos_score=0.0, stability_score=0.0)
    mean_score = sum(scores) / len(scores)
    st = pstdev(scores) if len(scores) > 1 else 0.0
    stability = 1.0 / (1.0 + st)
    return WalkForwardResponse(
        oos_scores=[round(s, 6) for s in scores],
        mean_oos_score=round(mean_score, 6),
        stability_score=round(stability, 6),
    )
