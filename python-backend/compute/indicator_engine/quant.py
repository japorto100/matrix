"""quant.py — Quantitative analytics and heuristic classifiers.

Extracted from pipeline.py (Phase A, 20.03.2026).

NOTE: These are NOT real ML functions. No trained models, no sklearn/torch.
All are hardcoded heuristics or simple statistics.
Real ML lives in python-backend/ml_ai/.

Functions:
  build_features, classify_signal, fuse_hybrid, monitor_bias,
  calculate_eval_baseline, evaluate_indicator,
  calculate_signal_quality_chain, calculate_deflated_sharpe,
  calculate_alternative_bars, calculate_cusum,
  _hurst_exponent, calculate_meanrev_momentum,
  calculate_performance_metrics, calculate_order_flow_state
"""

from __future__ import annotations

import math as _math
from statistics import pstdev
from typing import Literal

from indicator_engine.helpers import clamp, closes, volumes
from indicator_engine.models import (
    AlternativeBarsRequest,
    AlternativeBarsResponse,
    BiasMonitoringRequest,
    BiasMonitoringResponse,
    CUSUMRequest,
    CUSUMResponse,
    DeflatedSharpeRequest,
    DeflatedSharpeResponse,
    EvalBaselineRequest,
    EvalBaselineResponse,
    EvalIndicatorRequest,
    EvalIndicatorResponse,
    FeatureEngineeringRequest,
    FeatureEngineeringResponse,
    HybridFusionRequest,
    HybridFusionResponse,
    MeanRevMomentumRequest,
    MeanRevMomentumResponse,
    MLClassifySignalRequest,
    MLClassifySignalResponse,
    OrderFlowStateRequest,
    OrderFlowStateResponse,
    PerformanceMetricsRequest,
    PerformanceMetricsResponse,
    SignalQualityChainRequest,
    SignalQualityChainResponse,
)
from indicator_engine.oscillators import rsi
from indicator_engine.trend import sma

# ---------------------------------------------------------------------------
# Feature Engineering & Classification (heuristic, NOT real ML)
# ---------------------------------------------------------------------------


def build_features(req: FeatureEngineeringRequest) -> FeatureEngineeringResponse:
    """Build basic feature vectors from OHLCV (heuristic, no trained model)."""
    cs = closes(req.ohlcv)
    vs = volumes(req.ohlcv)
    if not cs:
        return FeatureEngineeringResponse(features=[], feature_names=["ret", "sma_dev", "rsi", "vol_ratio"])
    sma_vals = sma(cs, req.period)
    rsi_vals = rsi(cs, req.period)
    vol_sma = sma(vs, req.period) if vs else [1.0 for _ in cs]
    feats: list[dict[str, float]] = []
    for i in range(1, len(cs)):
        prev = cs[i - 1]
        ret = (cs[i] - prev) / prev if prev != 0 else 0.0
        sma_dev = (cs[i] - sma_vals[i]) / sma_vals[i] if sma_vals[i] != 0 else 0.0
        vol_ratio = (vs[i] / vol_sma[i]) if vol_sma[i] != 0 else 1.0
        feats.append({
            "ret": round(ret, 8),
            "sma_dev": round(sma_dev, 8),
            "rsi": round(rsi_vals[i], 8),
            "vol_ratio": round(vol_ratio, 8),
        })
    return FeatureEngineeringResponse(features=feats, feature_names=["ret", "sma_dev", "rsi", "vol_ratio"])


def classify_signal(req: MLClassifySignalRequest) -> MLClassifySignalResponse:
    """Heuristic signal classifier (sigmoid on weighted features, NOT trained ML)."""
    x = req.features
    score = (
        0.35 * x.get("ret", 0.0)
        + 0.25 * x.get("sma_dev", 0.0)
        + 0.20 * ((x.get("rsi", 50.0) - 50.0) / 50.0)
        + 0.20 * (x.get("vol_ratio", 1.0) - 1.0)
    )
    prob = 1.0 / (1.0 + _math.exp(-5.0 * score))
    if prob > 0.58:
        label: Literal["buy", "sell", "hold"] = "buy"
    elif prob < 0.42:
        label = "sell"
    else:
        label = "hold"
    return MLClassifySignalResponse(label=label, score=round(prob, 6))


def fuse_hybrid(req: HybridFusionRequest) -> HybridFusionResponse:
    """Blend ML score and rule-based score into single action."""
    fused = req.ml_weight * req.ml_score + (1.0 - req.ml_weight) * req.rule_score
    if fused > 0.58:
        action: Literal["buy", "sell", "hold"] = "buy"
    elif fused < 0.42:
        action = "sell"
    else:
        action = "hold"
    return HybridFusionResponse(fused_score=round(fused, 6), action=action)


def monitor_bias(req: BiasMonitoringRequest) -> BiasMonitoringResponse:
    """Check for geographic/regime distribution imbalance."""
    def _imbalance(d: dict[str, int]) -> float:
        vals = [v for v in d.values() if v >= 0]
        if not vals:
            return 0.0
        total = sum(vals)
        if total == 0:
            return 0.0
        shares = [v / total for v in vals]
        return max(shares) - min(shares) if len(shares) > 1 else shares[0]

    geo = _imbalance(req.geographic_distribution)
    reg = _imbalance(req.regime_distribution)
    alert = geo > 0.45 or reg > 0.45 or req.agreement_rate < 0.35
    return BiasMonitoringResponse(
        geographic_imbalance=round(geo, 6),
        regime_imbalance=round(reg, 6),
        agreement_rate=round(req.agreement_rate, 6),
        alert=alert,
    )


# ---------------------------------------------------------------------------
# Alternative Bars & CUSUM
# ---------------------------------------------------------------------------


def calculate_alternative_bars(req: AlternativeBarsRequest) -> AlternativeBarsResponse:
    """Volume/Dollar/Tick bars from OHLCV."""
    bs = req.bucketSize
    pts = req.ohlcv
    if not pts:
        return AlternativeBarsResponse(volume_bar_closes=[], dollar_bar_closes=[], tick_bar_closes=[], metadata={"bucketSize": bs})

    vol_bars: list[float] = []
    dol_bars: list[float] = []
    tick_bars: list[float] = []
    vol_acc = 0.0
    dol_acc = 0.0
    vol_target = sum(p.volume for p in pts) / max(len(pts) / bs, 1.0)
    dol_target = sum(p.close * p.volume for p in pts) / max(len(pts) / bs, 1.0)

    for i, p in enumerate(pts):
        vol_acc += p.volume
        dol_acc += p.close * p.volume
        if vol_acc >= vol_target:
            vol_bars.append(p.close)
            vol_acc = 0.0
        if dol_acc >= dol_target:
            dol_bars.append(p.close)
            dol_acc = 0.0
        if (i + 1) % bs == 0:
            tick_bars.append(p.close)

    return AlternativeBarsResponse(
        volume_bar_closes=vol_bars, dollar_bar_closes=dol_bars, tick_bar_closes=tick_bars,
        metadata={"bucketSize": bs, "points": len(pts)},
    )


def calculate_cusum(req: CUSUMRequest) -> CUSUMResponse:
    """CUSUM structural break detection."""
    closes_vals = req.closes
    rets = [(closes_vals[i] - closes_vals[i - 1]) / closes_vals[i - 1] for i in range(1, len(closes_vals)) if closes_vals[i - 1] != 0]
    if not rets:
        return CUSUMResponse(break_indices=[], break_signals=[], cumulative_pos=0.0, cumulative_neg=0.0)
    mean_r = sum(rets) / len(rets)
    s_pos = 0.0
    s_neg = 0.0
    idx: list[int] = []
    sig: list[str] = []
    for i, r in enumerate(rets, start=1):
        d = r - mean_r
        s_pos = max(0.0, s_pos + d)
        s_neg = min(0.0, s_neg + d)
        if s_pos > req.threshold:
            idx.append(i)
            sig.append("up_break")
            s_pos = 0.0
        if abs(s_neg) > req.threshold:
            idx.append(i)
            sig.append("down_break")
            s_neg = 0.0
    return CUSUMResponse(break_indices=idx, break_signals=sig, cumulative_pos=round(s_pos, 6), cumulative_neg=round(s_neg, 6))


# ---------------------------------------------------------------------------
# Hurst & Mean-Reversion/Momentum
# ---------------------------------------------------------------------------


def _hurst_exponent(values: list[float]) -> float:
    """Hurst exponent via rescaled range (R/S) method."""
    if len(values) < 40:
        return 0.5
    lags = [2, 4, 8, 16]
    tau: list[float] = []
    x_log: list[float] = []
    for lag in lags:
        if lag >= len(values):
            continue
        diffs = [values[i] - values[i - lag] for i in range(lag, len(values))]
        sd = pstdev(diffs) if len(diffs) > 1 else 0.0
        if sd > 0:
            tau.append(sd)
            x_log.append(_math.log(lag))
    if len(tau) < 2:
        return 0.5
    y_log = [_math.log(t) for t in tau]
    x_mean = sum(x_log) / len(x_log)
    y_mean = sum(y_log) / len(y_log)
    denom = sum((x - x_mean) ** 2 for x in x_log)
    if denom == 0:
        return 0.5
    slope_val = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_log, y_log)) / denom
    return float(clamp(slope_val, 0.0, 1.0))


def calculate_meanrev_momentum(req: MeanRevMomentumRequest) -> MeanRevMomentumResponse:
    """Classify series as mean-reverting, momentum, or random walk."""
    c = req.closes
    x = c[:-1]
    y = c[1:]
    n = len(x)
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    denom = sum((xi - x_mean) ** 2 for xi in x)
    phi = (sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / denom) if denom else 1.0
    adf_proxy = (phi - 1.0) * 100.0
    half_life = float(-_math.log(2) / _math.log(phi)) if 0 < phi < 1 else float("inf")
    hurst = _hurst_exponent(c)
    if hurst < 0.45 and phi < 0.99:
        cls: Literal["mean_reverting", "momentum", "random_walk"] = "mean_reverting"
    elif hurst > 0.55 and phi >= 0.99:
        cls = "momentum"
    else:
        cls = "random_walk"
    return MeanRevMomentumResponse(
        hurst=round(hurst, 6),
        adf_proxy_stat=round(adf_proxy, 6),
        half_life=round(half_life, 6) if _math.isfinite(half_life) else float("inf"),
        classification=cls,
    )


# ---------------------------------------------------------------------------
# Performance Metrics
# ---------------------------------------------------------------------------


def calculate_performance_metrics(req: PerformanceMetricsRequest) -> PerformanceMetricsResponse:
    """Compute Sharpe, Sortino, max drawdown, profit factor from returns."""
    r = req.returns
    if not r:
        return PerformanceMetricsResponse(
            net_return=0.0, hit_ratio=0.0, profit_factor=0.0,
            sharpe=0.0, sortino=0.0, max_drawdown=0.0,
        )
    net = _math.prod(1.0 + x for x in r) - 1.0
    wins = [x for x in r if x > 0]
    losses = [x for x in r if x < 0]
    hit = len(wins) / len(r)
    gain = sum(wins) if wins else 0.0
    loss = abs(sum(losses)) if losses else 0.0
    pf = (gain / loss) if loss > 0 else float("inf")
    mean_r = sum(r) / len(r)
    stdev_val = pstdev(r) if len(r) > 1 else 0.0
    down = [x for x in r if x < 0]
    down_std = pstdev(down) if len(down) > 1 else 0.0
    rf_daily = req.riskFreeRate / 252.0
    sharpe = ((mean_r - rf_daily) / stdev_val * _math.sqrt(252.0)) if stdev_val > 0 else 0.0
    sortino = ((mean_r - rf_daily) / down_std * _math.sqrt(252.0)) if down_std > 0 else 0.0
    eq = 1.0
    peak = 1.0
    max_dd = 0.0
    for x in r:
        eq *= 1.0 + x
        peak = max(peak, eq)
        dd = (eq - peak) / peak if peak > 0 else 0.0
        max_dd = min(max_dd, dd)
    return PerformanceMetricsResponse(
        net_return=round(net, 6), hit_ratio=round(hit, 6),
        profit_factor=round(pf, 6) if _math.isfinite(pf) else float("inf"),
        sharpe=round(sharpe, 6), sortino=round(sortino, 6), max_drawdown=round(max_dd, 6),
    )


# ---------------------------------------------------------------------------
# Signal Quality Chain & Order Flow
# ---------------------------------------------------------------------------


def calculate_signal_quality_chain(req: SignalQualityChainRequest) -> SignalQualityChainResponse:
    """Markov chain of signal quality transitions."""
    states = ["strong", "weak", "invalid"]
    counts: dict[str, dict[str, int]] = {s: {t: 0 for t in states} for s in states}
    for i in range(len(req.labels) - 1):
        counts[req.labels[i]][req.labels[i + 1]] += 1
    trans: dict[str, dict[str, float]] = {}
    for s in states:
        total = sum(counts[s].values())
        trans[s] = {t: (counts[s][t] / total if total else 1.0 / 3.0) for t in states}
    quality = trans["strong"]["strong"] - trans["strong"]["invalid"]
    return SignalQualityChainResponse(transition=trans, quality_score=round(quality, 6))


def calculate_order_flow_state(req: OrderFlowStateRequest) -> OrderFlowStateResponse:
    """Classify order flow as accumulation/distribution/squeeze."""
    n = min(len(req.buy_volumes), len(req.sell_volumes))
    states: list[Literal["accumulation", "distribution", "squeeze"]] = []
    for i in range(n):
        buy = req.buy_volumes[i]
        sell = req.sell_volumes[i]
        total = buy + sell
        if total <= 0:
            states.append("squeeze")
            continue
        imbalance = (buy - sell) / total
        if abs(imbalance) < req.squeeze_threshold:
            states.append("squeeze")
        elif imbalance > 0:
            states.append("accumulation")
        else:
            states.append("distribution")
    dominant = max(("accumulation", "distribution", "squeeze"), key=states.count) if states else "squeeze"
    return OrderFlowStateResponse(states=states, dominant_state=dominant)


# ---------------------------------------------------------------------------
# Eval & Deflated Sharpe
# ---------------------------------------------------------------------------


def _triple_barrier_labels(closes_vals: list[float], horizon: int, tp: float, sl: float) -> list[Literal["tp", "sl", "timeout"]]:
    """Triple barrier labeling for backtesting."""
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


def calculate_eval_baseline(req: EvalBaselineRequest) -> EvalBaselineResponse:
    """Evaluate indicator baseline using triple barrier + regime detection."""
    from indicator_engine.models import RegimeDetectRequest
    from indicator_engine.volatility import calculate_regime

    labels = _triple_barrier_labels(req.closes, req.horizon, req.take_profit, req.stop_loss)
    if not labels:
        return EvalBaselineResponse(
            labels=[], hit_ratio=0.0, expectancy=0.0, regime="ranging",
            precision_proxy=0.0, recall_proxy=0.0, f1_proxy=0.0,
        )
    tp = sum(1 for x in labels if x == "tp")
    sl = sum(1 for x in labels if x == "sl")
    timeout = len(labels) - tp - sl
    hit = tp / len(labels)
    expectancy = (tp * req.take_profit - sl * req.stop_loss) / len(labels)
    precision = tp / max(tp + sl, 1)
    recall = tp / max(tp + timeout, 1)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    regime = calculate_regime(RegimeDetectRequest(closes=req.closes, lookback=min(100, len(req.closes)))).current_regime
    return EvalBaselineResponse(
        labels=labels, hit_ratio=round(hit, 6), expectancy=round(expectancy, 6), regime=regime,
        precision_proxy=round(precision, 6), recall_proxy=round(recall, 6), f1_proxy=round(f1, 6),
    )


def calculate_deflated_sharpe(req: DeflatedSharpeRequest) -> DeflatedSharpeResponse:
    """Deflated Sharpe Ratio — adjusts for multiple testing."""
    penalty = _math.sqrt(2.0 * _math.log(max(req.trials, 1)) / max(req.sample_length, 1))
    ds = req.sharpe - penalty
    return DeflatedSharpeResponse(deflated_sharpe=round(ds, 6), pass_gate=ds > 0.0)


def evaluate_indicator(req: EvalIndicatorRequest) -> EvalIndicatorResponse:
    """Full indicator evaluation: walk-forward + baseline + deflated Sharpe."""
    from indicator_engine.backtest import run_backtest, run_walk_forward
    from indicator_engine.models import BacktestRequest, WalkForwardRequest

    wf = run_walk_forward(WalkForwardRequest(
        closes=req.closes,
        train_window=min(60, max(20, len(req.closes) // 2)),
        test_window=min(20, max(5, len(req.closes) // 6)),
    ))
    baseline = calculate_eval_baseline(EvalBaselineRequest(closes=req.closes))
    bt = run_backtest(BacktestRequest(closes=req.closes, lookback=10))
    from indicator_engine.models import PerformanceMetricsRequest as PMR
    pm = calculate_performance_metrics(PMR(returns=bt.strategy_returns))
    ds = calculate_deflated_sharpe(DeflatedSharpeRequest(sharpe=pm.sharpe, trials=20, sample_length=len(bt.strategy_returns)))
    execution_realism_pass = pm.max_drawdown > -0.6 and pm.profit_factor >= 0.8
    gate_pass = ds.pass_gate and execution_realism_pass and wf.stability_score > 0.3
    return EvalIndicatorResponse(
        walk_forward=wf, baseline=baseline, deflated_sharpe=ds,
        execution_realism_pass=execution_realism_pass, gate_pass=gate_pass,
    )
