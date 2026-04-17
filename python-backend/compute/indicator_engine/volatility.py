"""volatility.py — Volatility measures, bands, regime detection.

Extracted from pipeline.py (Phase A, 20.03.2026).

Primitives:  bollinger_bands_raw, e_bollinger_bands, bollinger_bandwidth,
             bollinger_percent_b, _atr_wilder, calculate_atr, keltner_channels
Endpoints:   calculate_keltner, calculate_bb_bandwidth, calculate_bb_percent_b,
             calculate_bollinger_keltner_squeeze, calculate_atr_rsi,
             calculate_bollinger_on_rsi, calculate_volatility_suite,
             calculate_regime, calculate_markov_regime, calculate_hmm_regime
Helpers:     _compute_sma_simple, _compute_adx_from_closes
"""

from __future__ import annotations

import math as _math
from statistics import mean, stdev

from indicator_engine.helpers import clamp, closes, volumes
from indicator_engine.models import (
    BollingerOnRSIResponse,
    BollingerSqueezeRequest,
    BollingerSqueezeResponse,
    BollingerVariantRequest,
    HMMRegimeResponse,
    IndicatorPoint,
    IndicatorResponse,
    KeltnerRequest,
    KeltnerResponse,
    MarkovRegimeResponse,
    OHLCVPoint,
    RegimeDetectRequest,
    RegimeDetectResponse,
    RSIVariantRequest,
    VolatilitySuiteRequest,
    VolatilitySuiteResponse,
)
from indicator_engine.rust_bridge import (
    calculate_indicators_batch as rust_calculate_indicators_batch,
)
from indicator_engine.trend import ema, sma

# ---------------------------------------------------------------------------
# Donchian Channels
# ---------------------------------------------------------------------------


def donchian_channels(
    high: list[float],
    low: list[float],
    period: int = 20,
) -> tuple[list[float], list[float], list[float]]:
    """Donchian Channels — highest high / lowest low over N bars.

    Returns (upper, middle, lower). Partial window for first period-1 bars.
    TradingView default: period=20.
    """
    n = len(high)
    upper: list[float] = []
    lower: list[float] = []
    middle: list[float] = []
    for i in range(n):
        start = max(0, i - period + 1)
        hh = max(high[start : i + 1])
        ll = min(low[start : i + 1])
        upper.append(hh)
        lower.append(ll)
        middle.append((hh + ll) / 2.0)
    return upper, middle, lower


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


def bollinger_bands_raw(
    values: list[float], period: int, num_std: float = 2.0
) -> tuple[list[float], list[float], list[float]]:
    """Compute (upper, middle, lower) Bollinger Band series (sample std-dev, F3)."""
    upper: list[float] = []
    middle: list[float] = []
    lower: list[float] = []
    for i in range(len(values)):
        start = max(0, i - period + 1)
        window = values[start : i + 1]
        mid = mean(window)
        std = stdev(window) if len(window) > 1 else 0.0
        upper.append(mid + num_std * std)
        middle.append(mid)
        lower.append(mid - num_std * std)
    return upper, middle, lower


def e_bollinger_bands(
    values: list[float], period: int = 20, num_std: float = 2.0
) -> tuple[list[float], list[float], list[float]]:
    """EMA-based Bollinger Bands (upper, middle, lower).

    Uses EMA as the middle band instead of SMA to reduce lag.
    Required by the Red Rainbow indicator (Kaabar 2026).
    Std-dev is computed over a rolling `period` window (sample, F3).
    """
    mid = ema(values, period)
    upper: list[float] = []
    lower: list[float] = []
    for i in range(len(values)):
        start = max(0, i - period + 1)
        window = values[start : i + 1]
        std = stdev(window) if len(window) > 1 else 0.0
        upper.append(mid[i] + num_std * std)
        lower.append(mid[i] - num_std * std)
    return upper, mid, lower


def bollinger_bandwidth(values: list[float], period: int, num_std: float = 2.0) -> list[float]:
    """(upper - lower) / middle — normalised BB width."""
    upper, middle, lower = bollinger_bands_raw(values, period, num_std)
    return [
        (upper[i] - lower[i]) / middle[i] if middle[i] != 0.0 else 0.0
        for i in range(len(values))
    ]


def bollinger_percent_b(values: list[float], period: int, num_std: float = 2.0) -> list[float]:
    """(close - lower) / (upper - lower) — position within the BB."""
    upper, _, lower = bollinger_bands_raw(values, period, num_std)
    result: list[float] = []
    for i in range(len(values)):
        band_width = upper[i] - lower[i]
        result.append((values[i] - lower[i]) / band_width if band_width != 0.0 else 0.5)
    return result


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------


def _atr_wilder(points: list[OHLCVPoint], period: int) -> list[float]:
    """ATR using Wilder's smoothing (EWM span=2*period-1), matching book formula.

    Book ref: mastering-finance-python.md §ATR — vol_lookback=(vol_lookback*2)-1.
    """
    h = [p.high for p in points]
    lo = [p.low for p in points]
    c = [p.close for p in points]
    tr: list[float] = [0.0]
    for i in range(1, len(c)):
        tr.append(max(h[i] - lo[i], abs(h[i] - c[i - 1]), abs(lo[i] - c[i - 1])))
    return ema(tr, period * 2 - 1)


def calculate_atr(points: list[OHLCVPoint], period: int = 14) -> list[float]:
    """Average True Range — max(H-L, |H-prevC|, |L-prevC|) smoothed via SMMA (Wilder). Rust-first."""
    rust_batch = rust_calculate_indicators_batch(
        [p.time for p in points],
        [p.open for p in points],
        [p.high for p in points],
        [p.low for p in points],
        closes(points),
        volumes(points),
        [f"atr_{period}"],
    )
    key = f"atr_{period}"
    if rust_batch and key in rust_batch and len(rust_batch[key]) == len(points):
        return [float(v) for v in rust_batch[key]]
    # Python fallback
    if len(points) < 2:
        return [0.0] * len(points)
    tr_values: list[float] = [0.0]
    for i in range(1, len(points)):
        h = points[i].high
        low_value = points[i].low
        prev_c = points[i - 1].close
        tr_values.append(max(h - low_value, abs(h - prev_c), abs(low_value - prev_c)))
    # Wilder SMMA: EMA with span = (2×period − 1), equivalent to Wilder's smoothing.
    # Kaabar Ch.6: "The ATR is the SMMA of the TR."
    return ema(tr_values, period * 2 - 1)


# ---------------------------------------------------------------------------
# Keltner Channels
# ---------------------------------------------------------------------------


def keltner_channels(
    points: list[OHLCVPoint],
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0,
) -> tuple[list[float], list[float], list[float]]:
    """Keltner Channels: middle = EMA(close), upper/lower = middle ± multiplier * ATR.

    Returns (upper, middle, lower).
    """
    mid = ema(closes(points), ema_period)
    atr_vals = calculate_atr(points, atr_period)
    upper = [m + multiplier * a for m, a in zip(mid, atr_vals)]
    lower = [m - multiplier * a for m, a in zip(mid, atr_vals)]
    return upper, mid, lower


def calculate_keltner(payload: KeltnerRequest) -> KeltnerResponse:
    """Keltner Channels endpoint."""
    upper, mid, lower = keltner_channels(payload.ohlcv, payload.ema_period, payload.atr_period, payload.multiplier)
    pts = payload.ohlcv
    return KeltnerResponse(
        upper=[IndicatorPoint(time=pts[i].time, value=upper[i]) for i in range(len(pts))],
        middle=[IndicatorPoint(time=pts[i].time, value=mid[i]) for i in range(len(pts))],
        lower=[IndicatorPoint(time=pts[i].time, value=lower[i]) for i in range(len(pts))],
        metadata={"ema_period": payload.ema_period, "atr_period": payload.atr_period, "multiplier": payload.multiplier},
    )


# ---------------------------------------------------------------------------
# BB variant endpoints (Rust-first)
# ---------------------------------------------------------------------------


def calculate_bb_bandwidth(payload: BollingerVariantRequest) -> IndicatorResponse:
    """Bollinger Bandwidth = (upper - lower) / middle. Rust-first when numStd==2.0."""
    series = closes(payload.ohlcv)
    bw: list[float] | None = None
    if payload.numStd == 2.0:
        rust_batch = rust_calculate_indicators_batch(
            [p.time for p in payload.ohlcv],
            [p.open for p in payload.ohlcv],
            [p.high for p in payload.ohlcv],
            [p.low for p in payload.ohlcv],
            series,
            volumes(payload.ohlcv),
            [f"bb_bw_{payload.period}"],
        )
        key = f"bb_bw_{payload.period}"
        if rust_batch and key in rust_batch and len(rust_batch[key]) == len(series):
            bw = [float(v) for v in rust_batch[key]]
    if bw is None:
        upper, middle, lower = bollinger_bands_raw(series, payload.period, payload.numStd)
        bw = [
            (upper[i] - lower[i]) / middle[i] if middle[i] != 0.0 else 0.0
            for i in range(len(series))
        ]
    return IndicatorResponse(
        data=[IndicatorPoint(time=point.time, value=bw[i]) for i, point in enumerate(payload.ohlcv)],
        metadata={"indicator": "BB_BANDWIDTH", "period": payload.period, "numStd": payload.numStd},
    )


def calculate_bb_percent_b(payload: BollingerVariantRequest) -> IndicatorResponse:
    """Bollinger %B = (close - lower) / (upper - lower). Rust-first when numStd==2.0."""
    series = closes(payload.ohlcv)
    result: list[float] | None = None
    if payload.numStd == 2.0:
        rust_batch = rust_calculate_indicators_batch(
            [p.time for p in payload.ohlcv],
            [p.open for p in payload.ohlcv],
            [p.high for p in payload.ohlcv],
            [p.low for p in payload.ohlcv],
            series,
            volumes(payload.ohlcv),
            [f"bb_pctb_{payload.period}"],
        )
        key = f"bb_pctb_{payload.period}"
        if rust_batch and key in rust_batch and len(rust_batch[key]) == len(series):
            result = [float(v) for v in rust_batch[key]]
    if result is None:
        upper, _, lower = bollinger_bands_raw(series, payload.period, payload.numStd)
        result = []
        for i in range(len(series)):
            band_width = upper[i] - lower[i]
            result.append((series[i] - lower[i]) / band_width if band_width != 0.0 else 0.5)
    return IndicatorResponse(
        data=[IndicatorPoint(time=point.time, value=result[i]) for i, point in enumerate(payload.ohlcv)],
        metadata={"indicator": "BB_PERCENT_B", "period": payload.period, "numStd": payload.numStd},
    )


def calculate_bollinger_keltner_squeeze(payload: BollingerSqueezeRequest) -> BollingerSqueezeResponse:
    """TTM Squeeze core: BB inside Keltner Channel = squeeze on; momentum histogram."""
    series = closes(payload.ohlcv)
    bb_upper, bb_mid, bb_lower = bollinger_bands_raw(series, payload.bbPeriod, payload.numStd)
    kc_mid = ema(series, payload.kcPeriod)
    atr_values = calculate_atr(payload.ohlcv, payload.kcPeriod)
    squeeze_list: list[bool] = []
    histogram: list[IndicatorPoint] = []
    for i, point in enumerate(payload.ohlcv):
        kc_upper = kc_mid[i] + payload.kcMult * atr_values[i]
        kc_lower = kc_mid[i] - payload.kcMult * atr_values[i]
        squeeze_list.append(bb_upper[i] <= kc_upper and bb_lower[i] >= kc_lower)
        momentum = series[i] - (bb_mid[i] + kc_mid[i]) / 2.0
        histogram.append(IndicatorPoint(time=point.time, value=momentum))
    return BollingerSqueezeResponse(
        squeeze=squeeze_list,
        histogram=histogram,
        metadata={
            "bbPeriod": payload.bbPeriod,
            "kcPeriod": payload.kcPeriod,
            "kcMult": payload.kcMult,
            "numStd": payload.numStd,
        },
    )


def calculate_atr_rsi(payload: RSIVariantRequest) -> IndicatorResponse:
    """ATR-adjusted RSI: gains/losses normalised by ATR for smoother volatile-market signal."""

    series = closes(payload.ohlcv)
    atr_values = calculate_atr(payload.ohlcv, payload.atrPeriod)
    if len(series) < 2:
        return IndicatorResponse(
            data=[IndicatorPoint(time=point.time, value=50.0) for point in payload.ohlcv],
            metadata={"indicator": "ATR_RSI", "rsiPeriod": payload.rsiPeriod, "atrPeriod": payload.atrPeriod},
        )
    gains: list[float] = [0.0]
    losses: list[float] = [0.0]
    for i in range(1, len(series)):
        delta = series[i] - series[i - 1]
        atr_norm = max(atr_values[i], 1e-9)
        gains.append(max(0.0, delta / atr_norm))
        losses.append(abs(min(0.0, delta / atr_norm)))
    avg_gain = sma(gains, payload.rsiPeriod)
    avg_loss = sma(losses, payload.rsiPeriod)
    result: list[IndicatorPoint] = []
    for i, point in enumerate(payload.ohlcv):
        g = avg_gain[i]
        lo = avg_loss[i]
        value = 100.0 if lo == 0.0 else 100.0 - (100.0 / (1.0 + g / lo))
        result.append(IndicatorPoint(time=point.time, value=clamp(value, 0.0, 100.0)))
    return IndicatorResponse(
        data=result,
        metadata={"indicator": "ATR_RSI", "rsiPeriod": payload.rsiPeriod, "atrPeriod": payload.atrPeriod},
    )


def calculate_bollinger_on_rsi(payload: BollingerVariantRequest) -> BollingerOnRSIResponse:
    """Apply Bollinger Bands to the RSI series (not to close prices)."""
    from indicator_engine.oscillators import rsi

    series = closes(payload.ohlcv)
    rsi_values = rsi(series, payload.period)
    bb_upper, bb_mid, bb_lower = bollinger_bands_raw(rsi_values, payload.period, payload.numStd)
    upper = [IndicatorPoint(time=point.time, value=bb_upper[i]) for i, point in enumerate(payload.ohlcv)]
    mid = [IndicatorPoint(time=point.time, value=bb_mid[i]) for i, point in enumerate(payload.ohlcv)]
    lower_out = [IndicatorPoint(time=point.time, value=bb_lower[i]) for i, point in enumerate(payload.ohlcv)]
    return BollingerOnRSIResponse(
        upper=upper,
        mid=mid,
        lower=lower_out,
        metadata={"indicator": "BB_RSI", "period": payload.period, "numStd": payload.numStd},
    )


# ---------------------------------------------------------------------------
# Volatility Suite (Phase 15b)
# ---------------------------------------------------------------------------


def calculate_volatility_suite(req: VolatilitySuiteRequest) -> VolatilitySuiteResponse:
    """Compute spike-weighted vol, historical vol, EW stddev, and regime label."""
    c = req.closes
    returns = [
        _math.log(c[i] / c[i - 1])
        for i in range(1, len(c))
        if c[i - 1] > 0 and c[i] > 0
    ]
    if not returns:
        return VolatilitySuiteResponse(
            spike_weighted_vol=0.0,
            volatility_index=0.0,
            exp_weighted_stddev=0.0,
            volatility_regime="normal",
            spike_weighted_regime="very_quiet",
        )

    lb = min(req.lookback, len(returns))
    recent = returns[-lb:]

    # Historical volatility (annualised)
    mean_r = sum(recent) / len(recent)
    variance = sum((r - mean_r) ** 2 for r in recent) / max(len(recent) - 1, 1)
    hv = _math.sqrt(variance) * _math.sqrt(252)

    # EWMA stddev — Kaabar Ch.6: pandas ewm().std() subtracts the EWM mean.
    alpha = 2.0 / (req.lookback + 1)
    ewm_mean = returns[0]
    ewm_var = 0.0
    for r in returns[1:]:
        ewm_mean = alpha * r + (1 - alpha) * ewm_mean
        ewm_var = alpha * (r - ewm_mean) ** 2 + (1 - alpha) * ewm_var
    ewm_std = _math.sqrt(max(ewm_var, 0.0))

    # Spike-weighted vol — Kaabar Ch.6: continuous z-score weighting.
    # spike_factor = |r - rolling_mean| / (rolling_std + ε)
    # weighted_sq = r² × (1 + spike_factor)
    # SWV = sqrt(mean(weighted_sq))
    mean_recent = sum(recent) / len(recent)
    std_recent = _math.sqrt(sum((r - mean_recent) ** 2 for r in recent) / max(len(recent) - 1, 1))
    weighted_sq: list[float] = []
    for r in recent:
        z = abs(r - mean_recent) / (std_recent + 1e-8)
        weighted_sq.append(r ** 2 * (1 + z))
    spike_vol = (
        _math.sqrt(sum(weighted_sq) / len(weighted_sq)) * _math.sqrt(252)
        if weighted_sq
        else 0.0
    )

    # Historical median of rolling HV for regime classification
    roll_hvs: list[float] = []
    for i in range(lb, len(returns) + 1):
        window = returns[max(0, i - lb): i]
        if len(window) < 2:
            continue
        m = sum(window) / len(window)
        v = sum((r - m) ** 2 for r in window) / max(len(window) - 1, 1)
        roll_hvs.append(_math.sqrt(v) * _math.sqrt(252))

    ELEVATED_ABS = 0.40
    COMPRESSED_ABS = 0.05
    hist_median = sorted(roll_hvs)[len(roll_hvs) // 2] if roll_hvs else hv
    if hv > ELEVATED_ABS:
        regime = "elevated"
    elif hv < COMPRESSED_ABS:
        regime = "compressed"
    elif hv > hist_median * 1.3:
        regime = "elevated"
    elif hv < hist_median * 0.7:
        regime = "compressed"
    else:
        regime = "normal"

    # Kaabar Ch.6: SWV 4-tier interpretation thresholds (daily data).
    # 0.002-0.005 very_quiet | 0.005-0.015 normal | 0.015-0.030 elevated | >0.030 high_volatility
    swv_raw = spike_vol  # already annualised — scale back to daily for Kaabar thresholds
    swv_daily = swv_raw / _math.sqrt(252) if swv_raw > 0 else 0.0
    if swv_daily > 0.030:
        swv_regime = "high_volatility"
    elif swv_daily > 0.015:
        swv_regime = "elevated"
    elif swv_daily > 0.005:
        swv_regime = "normal"
    else:
        swv_regime = "very_quiet"

    return VolatilitySuiteResponse(
        spike_weighted_vol=round(spike_vol, 6),
        volatility_index=round(hv, 6),
        exp_weighted_stddev=round(ewm_std, 6),
        volatility_regime=regime,
        spike_weighted_regime=swv_regime,
    )


# ---------------------------------------------------------------------------
# Regime Detection (Phase 15c) — 3-tier
# ---------------------------------------------------------------------------


def _compute_sma_simple(values: list[float], period: int) -> list[float]:
    """Lightweight SMA (no imports from trend to avoid circular deps)."""
    out: list[float] = []
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= period:
            running -= values[i - period]
        out.append(running / min(period, i + 1))
    return out


def _compute_adx_from_closes(closes_vals: list[float], period: int = 14) -> float:
    """ADX proxy using close prices as both high and low."""
    if len(closes_vals) < period * 2 + 2:
        return 0.0

    tr_values: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for i in range(1, len(closes_vals)):
        tr = abs(closes_vals[i] - closes_vals[i - 1])
        pdm = max(closes_vals[i] - closes_vals[i - 1], 0.0)
        mdm = max(closes_vals[i - 1] - closes_vals[i], 0.0)
        if pdm > mdm:
            mdm = 0.0
        elif mdm > pdm:
            pdm = 0.0
        else:
            pdm = mdm = 0.0
        tr_values.append(tr)
        plus_dm.append(pdm)
        minus_dm.append(mdm)

    def _smooth(vals: list[float], p: int) -> list[float]:
        if not vals:
            return []
        result = [sum(vals[:p]) / p]
        for v in vals[p:]:
            result.append(result[-1] - result[-1] / p + v)
        return result

    atr_s = _smooth(tr_values, period)
    pdi_s = _smooth(plus_dm, period)
    mdi_s = _smooth(minus_dm, period)

    dx_vals: list[float] = []
    for a, p, m in zip(atr_s, pdi_s, mdi_s):
        if a == 0:
            dx_vals.append(0.0)
            continue
        pdi = 100 * p / a
        mdi = 100 * m / a
        denom = pdi + mdi
        dx_vals.append(100 * abs(pdi - mdi) / denom if denom else 0.0)

    adx_s = _smooth(dx_vals, period)
    return adx_s[-1] if adx_s else 0.0


def calculate_regime(req: RegimeDetectRequest) -> RegimeDetectResponse:
    """Tier-1: Rule-based regime using SMA slope + ADX proxy."""
    closes_vals = req.closes
    n = len(closes_vals)
    period = min(50, n - 1)
    sma_vals = _compute_sma_simple(closes_vals, period)

    slope = 0.0
    if len(sma_vals) >= 6:
        ref = sma_vals[-6]
        if ref != 0:
            slope = (sma_vals[-1] - ref) / abs(ref)

    adx_val = _compute_adx_from_closes(closes_vals[-min(200, n):], 14)

    if slope > 0.001 and adx_val > 25:
        regime = "bullish"
        confidence = min(1.0, 0.5 + slope * 50 + (adx_val - 25) / 100)
    elif slope < -0.001 and adx_val > 25:
        regime = "bearish"
        confidence = min(1.0, 0.5 + abs(slope) * 50 + (adx_val - 25) / 100)
    else:
        regime = "ranging"
        confidence = max(0.3, 1.0 - adx_val / 100)

    return RegimeDetectResponse(
        current_regime=regime,
        sma_slope=round(slope, 6),
        adx=round(adx_val, 4),
        confidence=round(clamp(confidence, 0.0, 1.0), 4),
    )


def calculate_markov_regime(req: RegimeDetectRequest) -> MarkovRegimeResponse:
    """Tier-2: Markov transition matrix from rolling rule-based regimes."""
    closes_vals = req.closes
    step = max(1, len(closes_vals) // req.lookback)
    segments = [closes_vals[i: i + step + 1] for i in range(0, len(closes_vals) - step, step)]

    labels: list[str] = []
    for seg in segments:
        if len(seg) < 20:
            continue
        mini = RegimeDetectRequest(closes=seg, lookback=max(20, len(seg)), n_components=req.n_components)
        labels.append(calculate_regime(mini).current_regime)

    states = ["bullish", "bearish", "ranging"]

    if not labels:
        uniform = {s: round(1.0 / 3, 4) for s in states}
        return MarkovRegimeResponse(
            current_regime="ranging",
            transition_probs=uniform,
            expected_duration=1.0,
            shift_probability=0.5,
            stationary_distribution=uniform,
            warning="insufficient data for Markov estimation",
        )

    counts: dict[str, dict[str, int]] = {s: {t: 0 for t in states} for s in states}
    for i in range(len(labels) - 1):
        from_s, to_s = labels[i], labels[i + 1]
        if from_s in counts and to_s in counts[from_s]:
            counts[from_s][to_s] += 1

    trans: dict[str, dict[str, float]] = {}
    for s in states:
        total = sum(counts[s].values())
        trans[s] = {t: counts[s][t] / total if total else 1.0 / 3 for t in states}

    current = labels[-1]
    p_same = trans[current].get(current, 1.0 / 3)
    expected_dur = 1.0 / (1.0 - p_same) if p_same < 1.0 else 999.0
    shift_prob = 1.0 - p_same

    # Stationary distribution via power iteration
    dist: dict[str, float] = {s: 1.0 / 3 for s in states}
    for _ in range(200):
        new_dist: dict[str, float] = {s: 0.0 for s in states}
        for s in states:
            for t in states:
                new_dist[t] += dist[s] * trans[s].get(t, 0.0)
        dist = new_dist

    return MarkovRegimeResponse(
        current_regime=current,
        transition_probs={t: round(trans[current].get(t, 0.0), 4) for t in states},
        expected_duration=round(expected_dur, 2),
        shift_probability=round(shift_prob, 4),
        stationary_distribution={s: round(dist[s], 4) for s in states},
        warning=None,
    )


def calculate_hmm_regime(req: RegimeDetectRequest) -> HMMRegimeResponse:
    """Tier-3: Gaussian HMM with BIC-optimal n_components."""
    try:
        from hmmlearn import hmm as _hmm  # noqa: PLC0415
    except ImportError:
        return HMMRegimeResponse(
            n_components=0,
            hidden_state=-1,
            state_labels=[],
            means=[],
            bic_score=float("inf"),
        )

    closes_vals = req.closes
    returns_raw = [
        _math.log(closes_vals[i] / closes_vals[i - 1])
        for i in range(1, len(closes_vals))
        if closes_vals[i - 1] > 0
    ]
    if len(returns_raw) < 20:
        return HMMRegimeResponse(
            n_components=0,
            hidden_state=-1,
            state_labels=[],
            means=[],
            bic_score=float("inf"),
        )

    obs = [[r] for r in returns_raw]
    best_bic = float("inf")
    best_model = None
    best_n = 2
    max_n = min(req.n_components, max(2, len(returns_raw) // 20))

    for n in range(2, max_n + 1):
        try:
            model = _hmm.GaussianHMM(
                n_components=n, covariance_type="full", n_iter=100, random_state=42
            )
            model.fit(obs)
            log_lik = model.score(obs)
            n_params = n * n + n + n
            bic = -2 * log_lik + n_params * _math.log(len(returns_raw))
            if bic < best_bic:
                best_bic, best_model, best_n = bic, model, n
        except Exception:  # noqa: BLE001
            continue

    if best_model is None:
        return HMMRegimeResponse(
            n_components=0,
            hidden_state=-1,
            state_labels=[],
            means=[],
            bic_score=float("inf"),
        )

    current_state = int(best_model.predict(obs)[-1])
    raw_means = [float(best_model.means_[i][0]) for i in range(best_n)]
    label_pool = ["low_vol", "medium_vol", "high_vol", "very_high_vol", "extreme_vol", "ultra_vol"]
    state_labels = label_pool[:best_n]

    return HMMRegimeResponse(
        n_components=best_n,
        hidden_state=current_state,
        state_labels=state_labels,
        means=[round(m, 6) for m in raw_means],
        bic_score=round(best_bic, 4),
    )


# ---------------------------------------------------------------------------
# BB Signal Techniques (Kaabar 2026, Ch. 3)
# ---------------------------------------------------------------------------


def calculate_bb_conservative(payload: BollingerVariantRequest) -> IndicatorResponse:
    """BB Conservative: 'Return to Normality' — price re-enters bands from outside.

    Bullish: close crosses above lower band (re-entry), stays below middle.
    Bearish: close crosses below upper band (re-entry), stays above middle.
    """
    from indicator_engine.helpers import closes as extract_closes

    pts = payload.ohlcv
    c = extract_closes(pts)
    upper, mid, lower = bollinger_bands_raw(c, payload.period, payload.numStd)
    n = len(pts)
    signals: list[float] = [0.0] * n
    for i in range(1, n):
        if c[i] > lower[i] and c[i] < mid[i] and c[i - 1] <= lower[i - 1]:
            signals[i] = 1.0
        elif c[i] < upper[i] and c[i] > mid[i] and c[i - 1] >= upper[i - 1]:
            signals[i] = -1.0
    return IndicatorResponse(
        data=[IndicatorPoint(time=pts[i].time, value=signals[i]) for i in range(n)],
        metadata={"indicator": "BB_CONSERVATIVE", "period": payload.period, "points": n},
    )


def calculate_bb_aggressive(payload: BollingerVariantRequest) -> IndicatorResponse:
    """BB Aggressive: price pierces the band — contrarian mean-reversion entry.

    Bullish: close crosses below lower band (oversold extreme).
    Bearish: close crosses above upper band (overbought extreme).
    """
    from indicator_engine.helpers import closes as extract_closes

    pts = payload.ohlcv
    c = extract_closes(pts)
    upper, _mid, lower = bollinger_bands_raw(c, payload.period, payload.numStd)
    n = len(pts)
    signals: list[float] = [0.0] * n
    for i in range(1, n):
        if c[i] < lower[i] and c[i - 1] >= lower[i - 1]:
            signals[i] = 1.0
        elif c[i] > upper[i] and c[i - 1] <= upper[i - 1]:
            signals[i] = -1.0
    return IndicatorResponse(
        data=[IndicatorPoint(time=pts[i].time, value=signals[i]) for i in range(n)],
        metadata={"indicator": "BB_AGGRESSIVE", "period": payload.period, "points": n},
    )


def calculate_bb_trend_friendly(payload: BBTrendFriendlyRequest) -> IndicatorResponse:  # noqa: F821
    """BB Trend-Friendly: Conservative signal + SMA(100) trend filter.

    Kaabar Ch.3: uses SMA with 10-bar offset for trend confirmation.
    Bullish: re-enters bands from below AND close > SMA(100)[i-10].
    Bearish: re-enters bands from above AND close < SMA(100)[i-10].
    """
    from indicator_engine.helpers import closes as extract_closes

    pts = payload.ohlcv
    c = extract_closes(pts)
    upper, mid, lower = bollinger_bands_raw(c, payload.bb_period, payload.num_std)
    sma_trend = sma(c, payload.sma_period)
    n = len(pts)
    offset = payload.sma_offset
    signals: list[float] = [0.0] * n
    for i in range(max(1, offset), n):
        sma_ref = sma_trend[i - offset] if i >= offset else sma_trend[0]
        # Conservative + trend filter
        if c[i] > lower[i] and c[i] < mid[i] and c[i - 1] <= lower[i - 1] and c[i] > sma_ref:
            signals[i] = 1.0
        elif c[i] < upper[i] and c[i] > mid[i] and c[i - 1] >= upper[i - 1] and c[i] < sma_ref:
            signals[i] = -1.0
    return IndicatorResponse(
        data=[IndicatorPoint(time=pts[i].time, value=signals[i]) for i in range(n)],
        metadata={
            "indicator": "BB_TREND_FRIENDLY",
            "bb_period": payload.bb_period,
            "sma_period": payload.sma_period,
            "sma_offset": offset,
            "points": n,
        },
    )
