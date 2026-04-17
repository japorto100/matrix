"""oscillators.py — Momentum oscillators and composite signals.

Extracted from pipeline.py (Phase A, 20.03.2026).

Primitives: rsi, macd, stochastic, adx_series
Endpoints:  calculate_macd, calculate_stochastic, calculate_adx,
            calculate_ks_collection, build_composite_signal
Helpers:    heartbeat_score, _wilder_sum, _wilder_avg
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from indicator_engine.helpers import (
    clamp,
    closes,
    detect_swings,
    highs,
    lows,
    ohlcv_polars_frame,
    volumes,
)
from indicator_engine.models import (
    ADXRequest,
    ADXResponse,
    CompositeComponent,
    CompositeSignalRequest,
    CompositeSignalResponse,
    IndicatorPoint,
    IndicatorResponse,
    KsCollectionRequest,
    MACDRequest,
    MACDResponse,
    OHLCVPoint,
    SignalDirection,
    StochasticRequest,
    StochasticResponse,
)
from indicator_engine.rust_bridge import (
    calculate_heartbeat as rust_calculate_heartbeat,
)
from indicator_engine.rust_bridge import (
    calculate_indicators_batch as rust_calculate_indicators_batch,
)
from indicator_engine.rust_bridge import (
    composite_sma50_slope_norm as rust_composite_sma50_slope_norm,
)
from indicator_engine.trend import ema, sma

# ---------------------------------------------------------------------------
# Oscillator primitives
# ---------------------------------------------------------------------------


def percent_rank(values: list[float], period: int) -> list[float]:
    """Percent rank: what % of the last `period` values are strictly < current value.

    Returns 0–100 scale. First `period-1` values use partial window.
    Used by Connors RSI (Component 3).
    """
    n = len(values)
    out = [0.0] * n
    for i in range(n):
        start = max(0, i - period + 1)
        window = values[start : i + 1]
        if len(window) <= 1:
            out[i] = 50.0
            continue
        count = sum(1 for v in window if v < values[i])
        out[i] = count / len(window) * 100.0
    return out


def connors_rsi(
    close: list[float],
    rsi_period: int = 3,
    streak_period: int = 2,
    pct_period: int = 100,
) -> list[float]:
    """Connors RSI — composite of 3 components (Connors & Alvarez, 2012).

    CRSI = (RSI(close, rsi_period) + RSI(streak, streak_period) + PercentRank(ROC1, pct_period)) / 3

    Component 1: Standard Wilder RSI on close prices.
    Component 2: RSI applied to consecutive up/down streak count.
    Component 3: Percentile rank of 1-bar rate of change over pct_period bars.

    Default params: rsi_period=3, streak_period=2, pct_period=100 (Connors original).
    Output: 0–100 scale.
    """
    n = len(close)
    if n < 2:
        return [50.0] * n

    # Component 1: RSI on close
    rsi_close = rsi(close, rsi_period)

    # Component 2: streak → RSI of streak
    streak = [0.0] * n
    for i in range(1, n):
        if close[i] > close[i - 1]:
            streak[i] = (streak[i - 1] + 1) if streak[i - 1] >= 0 else 1.0
        elif close[i] < close[i - 1]:
            streak[i] = (streak[i - 1] - 1) if streak[i - 1] <= 0 else -1.0
        else:
            streak[i] = 0.0
    rsi_streak = rsi(streak, streak_period)

    # Component 3: percent rank of ROC-1
    roc1 = [0.0] * n
    for i in range(1, n):
        if close[i - 1] != 0:
            roc1[i] = (close[i] - close[i - 1]) / close[i - 1] * 100.0
    pct = percent_rank(roc1, pct_period)

    # Final CRSI
    return [(rsi_close[i] + rsi_streak[i] + pct[i]) / 3.0 for i in range(n)]


def rsi(values: list[float], period: int = 14) -> list[float]:
    """RSI with Wilder warmup — SMA for first `period` changes, then Wilder smoothing.

    Book ref: mastering-finance-python.md §RSI.
    """
    if len(values) < 2:
        return [50.0 for _ in values]
    gains: list[float] = [0.0]
    losses: list[float] = [0.0]
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(0.0, delta))
        losses.append(abs(min(0.0, delta)))

    n = len(gains)
    output = [50.0] * n
    if n <= period:
        return output

    # SMA warmup for first `period` changes
    avg_gain = sum(gains[1 : period + 1]) / period
    avg_loss = sum(losses[1 : period + 1]) / period
    output[period] = 100.0 if avg_loss == 0.0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    # Wilder smoothing for the rest
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        output[i] = 100.0 if avg_loss == 0.0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    return output


def macd(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    """MACD = EMA(fast) - EMA(slow); signal = EMA(macd, signal); histogram = macd - signal.

    Book ref: mastering-finance-python.md L5264-5298.
    """
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, histogram


def stochastic(
    points: list[OHLCVPoint],
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[list[float], list[float]]:
    """Stochastic Oscillator: %K = (C - LowestLow) / (HighestHigh - LowestLow) * 100.

    %D = SMA(%K, d_period).
    """
    h = highs(points)
    lo = lows(points)
    c = closes(points)
    k_values: list[float] = []
    for i in range(len(c)):
        start = max(0, i + 1 - k_period)
        period_h = max(h[start : i + 1])
        period_l = min(lo[start : i + 1])
        denom = period_h - period_l
        k_values.append(100.0 * (c[i] - period_l) / denom if denom != 0.0 else 50.0)
    d_values = sma(k_values, d_period)
    return k_values, d_values


def _wilder_sum(vals: list[float], p: int) -> list[float]:
    """Wilder smoothing with sum-based init (for ATR and DM)."""
    if len(vals) < p:
        return [0.0] * len(vals)
    first = sum(vals[:p])
    result = [0.0] * (p - 1) + [first]
    for v in vals[p:]:
        result.append(result[-1] - result[-1] / p + v)
    return result


def _wilder_avg(vals: list[float], p: int) -> list[float]:
    """Wilder smoothing with average-based init (for ADX)."""
    if len(vals) < p:
        return [0.0] * len(vals)
    first = sum(vals[:p]) / p
    result = [0.0] * (p - 1) + [first]
    for v in vals[p:]:
        result.append(result[-1] - result[-1] / p + v / p)
    return result


def adx_series(
    points: list[OHLCVPoint],
    period: int = 14,
) -> tuple[list[float], list[float], list[float]]:
    """Full ADX + DI+ + DI- series using true OHLCV.

    Uses Wilder smoothing (alpha = 1/period).
    Returns (adx, di_plus, di_minus) — all same length as input.
    """
    h = highs(points)
    lo = lows(points)
    c = closes(points)
    n = len(c)
    if n < 2:
        return [0.0] * n, [0.0] * n, [0.0] * n

    tr_list: list[float] = [0.0]
    pdm_list: list[float] = [0.0]
    mdm_list: list[float] = [0.0]
    for i in range(1, n):
        tr = max(h[i] - lo[i], abs(h[i] - c[i - 1]), abs(lo[i] - c[i - 1]))
        up = h[i] - h[i - 1]
        down = lo[i - 1] - lo[i]
        pdm = up if (up > down and up > 0.0) else 0.0
        mdm = down if (down > up and down > 0.0) else 0.0
        tr_list.append(tr)
        pdm_list.append(pdm)
        mdm_list.append(mdm)

    atr_s = _wilder_sum(tr_list, period)
    pdi_s = _wilder_sum(pdm_list, period)
    mdi_s = _wilder_sum(mdm_list, period)

    dx_list: list[float] = []
    di_plus: list[float] = []
    di_minus: list[float] = []
    for a, p, m in zip(atr_s, pdi_s, mdi_s):
        dip = 100.0 * p / a if a else 0.0
        dim = 100.0 * m / a if a else 0.0
        denom = dip + dim
        dx_list.append(100.0 * abs(dip - dim) / denom if denom else 0.0)
        di_plus.append(dip)
        di_minus.append(dim)

    adx_out = _wilder_avg(dx_list, period)
    return adx_out, di_plus, di_minus


# ---------------------------------------------------------------------------
# Endpoint handlers
# ---------------------------------------------------------------------------


def calculate_macd(payload: MACDRequest) -> MACDResponse:
    """MACD endpoint: line, signal, histogram. Book ref: mastering-finance-python.md L5264."""
    series = closes(payload.ohlcv)
    macd_line, signal_line, histogram = macd(series, payload.fast, payload.slow, payload.signal)
    pts = payload.ohlcv
    return MACDResponse(
        macd_line=[IndicatorPoint(time=pts[i].time, value=macd_line[i]) for i in range(len(pts))],
        signal_line=[IndicatorPoint(time=pts[i].time, value=signal_line[i]) for i in range(len(pts))],
        histogram=[IndicatorPoint(time=pts[i].time, value=histogram[i]) for i in range(len(pts))],
        metadata={"fast": payload.fast, "slow": payload.slow, "signal": payload.signal},
    )


def calculate_stochastic(payload: StochasticRequest) -> StochasticResponse:
    """Stochastic %K/%D endpoint."""
    k_vals, d_vals = stochastic(payload.ohlcv, payload.k_period, payload.d_period)
    pts = payload.ohlcv
    return StochasticResponse(
        k=[IndicatorPoint(time=pts[i].time, value=k_vals[i]) for i in range(len(pts))],
        d=[IndicatorPoint(time=pts[i].time, value=d_vals[i]) for i in range(len(pts))],
        metadata={"k_period": payload.k_period, "d_period": payload.d_period},
    )


def calculate_adx(payload: ADXRequest) -> ADXResponse:
    """ADX + DI+ + DI- endpoint."""
    adx_vals, dip_vals, dim_vals = adx_series(payload.ohlcv, payload.period)
    pts = payload.ohlcv
    return ADXResponse(
        adx=[IndicatorPoint(time=pts[i].time, value=adx_vals[i]) for i in range(len(pts))],
        di_plus=[IndicatorPoint(time=pts[i].time, value=dip_vals[i]) for i in range(len(pts))],
        di_minus=[IndicatorPoint(time=pts[i].time, value=dim_vals[i]) for i in range(len(pts))],
        metadata={"period": payload.period},
    )


# ---------------------------------------------------------------------------
# Heartbeat score (cyclicality measure)
# ---------------------------------------------------------------------------


def heartbeat_score(points: list[OHLCVPoint]) -> tuple[float, dict[str, Any]]:
    """Market heartbeat — measures cyclicality via swing pivot regularity.

    Uses Rust fast-path when available, falls back to Python pivot analysis.
    """
    rust_score = rust_calculate_heartbeat(closes(points), highs(points), lows(points), 0.02)
    if rust_score is not None:
        rust_score = clamp(rust_score, 0.0, 1.0)
        pivots = detect_swings(points, window=2)
        period_hint = 0.0
        if len(pivots) >= 2:
            periods = [pivots[i].index - pivots[i - 1].index for i in range(1, len(pivots))]
            period_hint = round(mean(periods), 2) if periods else 0.0
        return rust_score, {
            "swings": len(pivots),
            "cycleBars": period_hint,
            "amplitudeStability": None,
            "periodStability": None,
            "engine": "rust",
        }

    pivots = detect_swings(points, window=2)
    if len(pivots) < 6:
        return 0.0, {
            "swings": len(pivots),
            "cycleBars": 0,
            "amplitudeStability": 0.0,
            "periodStability": 0.0,
            "engine": "python",
        }
    periods = [pivots[i].index - pivots[i - 1].index for i in range(1, len(pivots))]
    amplitudes = [abs(pivots[i].price - pivots[i - 1].price) for i in range(1, len(pivots))]
    period_mean = mean(periods) if periods else 0.0
    amp_mean = mean(amplitudes) if amplitudes else 0.0
    period_cv = (pstdev(periods) / period_mean) if period_mean else 1.0
    amp_cv = (pstdev(amplitudes) / amp_mean) if amp_mean else 1.0
    period_stability = clamp(1.0 - period_cv, 0.0, 1.0)
    amp_stability = clamp(1.0 - amp_cv, 0.0, 1.0)
    score = clamp((period_stability + amp_stability) / 2.0, 0.0, 1.0)
    return score, {
        "swings": len(pivots),
        "cycleBars": round(period_mean, 2),
        "amplitudeStability": round(amp_stability, 4),
        "periodStability": round(period_stability, 4),
        "engine": "python",
    }


# ---------------------------------------------------------------------------
# K's Collection (Kaabar 2026, Ch. 11) — 6 indicators
# ---------------------------------------------------------------------------

_FIB_MA_PERIODS = (2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597)


def calculate_ks_collection(payload: KsCollectionRequest) -> dict[str, IndicatorResponse]:
    """K's Collection — 6 indicators (Kaabar 2026, Ch. 11).

    Reversal I/II and MARSI return discrete signals {-1.0, 0.0, 1.0}.
    ATR-RSI and RSI² return continuous 0-100 oscillator values.
    FMA returns price-level band values (high/low/mid).
    """
    # Lazy imports to avoid circular deps during Phase A
    from indicator_engine.volatility import _atr_wilder, bollinger_bands_raw

    pts = payload.ohlcv
    series = closes(pts)
    h = highs(pts)
    lo = lows(pts)
    n = len(series)

    # K's Reversal I: BB(100, SMA) + MACD(12/26/9) crossover
    bb_upper, bb_mid, bb_lower = bollinger_bands_raw(series, 100, 2.0)
    macd_l, macd_sig, _ = macd(series, 12, 26, 9)
    rev_i: list[float] = [0.0] * n
    for i in range(1, n - 1):
        if (lo[i] < bb_lower[i] and h[i] < bb_mid[i]
                and macd_l[i] > macd_sig[i] and macd_l[i - 1] < macd_sig[i - 1]):
            rev_i[i + 1] = 1.0
        elif (h[i] > bb_upper[i] and lo[i] > bb_mid[i]
              and macd_l[i] < macd_sig[i] and macd_l[i - 1] > macd_sig[i - 1]):
            rev_i[i + 1] = -1.0

    # K's Reversal II: SMA(13) + rolling 21-bar above-count
    sma_13 = sma(series, 13)
    rev_ii: list[float] = [0.0] * n
    for i in range(20, n):
        count = sum(1 for j in range(i - 20, i + 1) if series[j] > sma_13[j])
        if count == 0:
            rev_ii[i] = 1.0
        elif count == 21:
            rev_ii[i] = -1.0

    # K's ATR-Adjusted RSI: RSI(13)*ATR(5) → RSI(13)
    rsi_13 = rsi(series, 13)
    atr_5 = _atr_wilder(pts, 5)
    rsi_x_atr = [r * a for r, a in zip(rsi_13, atr_5)]
    atr_rsi = rsi(rsi_x_atr, 13)

    # K's RSI²: RSI(14, close) → RSI(5, rsi14)
    rsi_14 = rsi(series, 14)
    rsi_sq = rsi(rsi_14, 5)

    # K's MARSI: SMA(200, close) → RSI(20) + signal logic (Kaabar Ch.11)
    # Bullish: MARSI > 2 after 3+ bars below 2. Bearish: MARSI < 98 after 3+ bars above 98.
    sma_200 = sma(series, 200)
    marsi_vals = rsi(sma_200, 20)
    marsi_signals: list[float] = [0.0] * n
    for i in range(3, n):
        if marsi_vals[i] > 2 and all(marsi_vals[i - j] < 2 for j in range(1, 4)):
            marsi_signals[i] = 1.0
        elif marsi_vals[i] < 98 and all(marsi_vals[i - j] > 98 for j in range(1, 4)):
            marsi_signals[i] = -1.0

    # K's Fibonacci MA: avg of 15 Fib EMAs on highs + lows
    ema_h_list = [ema(h, p) for p in _FIB_MA_PERIODS]
    ema_l_list = [ema(lo, p) for p in _FIB_MA_PERIODS]
    k = len(_FIB_MA_PERIODS)
    fma_h = [sum(ema_h_list[j][i] for j in range(k)) / k for i in range(n)]
    fma_l = [sum(ema_l_list[j][i] for j in range(k)) / k for i in range(n)]
    fma_mid = [(fh + fl) / 2.0 for fh, fl in zip(fma_h, fma_l)]

    def to_response(name: str, values: list[float], extra: dict[str, Any] | None = None) -> IndicatorResponse:
        meta: dict[str, Any] = {"indicator": name, "points": len(values)}
        if extra:
            meta.update(extra)
        return IndicatorResponse(
            data=[IndicatorPoint(time=point.time, value=values[i]) for i, point in enumerate(pts)],
            metadata=meta,
        )

    return {
        "reversalI": to_response("K_REVERSAL_I", rev_i, {"bbPeriod": 100, "macdFast": 12, "macdSlow": 26, "macdSignal": 9}),
        "reversalII": to_response("K_REVERSAL_II", rev_ii, {"smaPeriod": 13, "countWindow": 21}),
        "atrAdjustedRSI": to_response("K_ATR_RSI", atr_rsi, {"rsiPeriod": 13, "atrPeriod": 5}),
        "rsiSquared": to_response("K_RSI_SQUARED", rsi_sq, {"rsiInner": 14, "rsiOuter": 5}),
        "marsi": to_response("K_MARSI", marsi_vals, {"smaPeriod": 200, "rsiPeriod": 20}),
        "marsiSignal": to_response("K_MARSI_SIGNAL", marsi_signals, {"thresholds": [2, 98], "dwellBars": 3}),
        "fibonacciMA": to_response("K_FIB_MA", fma_mid, {"fibPeriods": 15}),
        "fibonacciMAHigh": to_response("K_FIB_MA_HIGH", fma_h, {"fibPeriods": 15}),
        "fibonacciMALow": to_response("K_FIB_MA_LOW", fma_l, {"fibPeriods": 15}),
    }


# ---------------------------------------------------------------------------
# Composite Signal
# ---------------------------------------------------------------------------


def build_composite_signal(payload: CompositeSignalRequest) -> CompositeSignalResponse:
    """Multi-factor composite signal: SMA slope + heartbeat + volume power.

    Uses Rust fast-path for SMA slope and RVOL when available.
    """
    # Lazy imports for cross-module deps
    from indicator_engine.volume import cmf, obv

    points = payload.ohlcv
    frame = ohlcv_polars_frame(points)
    if frame is not None:
        dataframe_engine = "polars"
        close_series = [float(value) for value in frame.get_column("close").to_list()]
        volume_series = [float(value) for value in frame.get_column("volume").to_list()]
    else:
        dataframe_engine = "python"
        close_series = closes(points)
        volume_series = volumes(points)

    rust_slope = rust_composite_sma50_slope_norm(close_series)
    if rust_slope is not None:
        slope_value, slope_norm, _last_sma = rust_slope
        sma_engine = "rust"
    else:
        sma50 = sma(close_series, 50)
        slope_period = min(5, len(sma50) - 1)
        if slope_period <= 0:
            slope_value = 0.0
        else:
            slope_value = sma50[-1] - sma50[-1 - slope_period]
        slope_norm = slope_value / max(1e-9, abs(sma50[-1]))
        sma_engine = "python"
    sma_score = clamp(abs(slope_norm) * 180.0, 0.0, 1.0)
    sma_direction = "rising" if slope_value > 0 else "falling" if slope_value < 0 else "flat"

    heartbeat, heartbeat_details = heartbeat_score(points)
    heartbeat_details = {**heartbeat_details, "dataframeEngine": dataframe_engine}
    vol_period = min(20, len(volume_series))
    latest_vol = volume_series[-1] if volume_series else 0.0
    rust_batch = rust_calculate_indicators_batch(
        [point.time for point in points],
        [point.open for point in points],
        [point.high for point in points],
        [point.low for point in points],
        close_series,
        volume_series,
        ["rvol_20"],
    )
    rust_rvol_series = rust_batch.get("rvol_20") if rust_batch else None
    if rust_rvol_series and len(rust_rvol_series) == len(volume_series):
        latest_rvol = float(rust_rvol_series[-1])
        rvol_engine = "rust"
    else:
        avg_vol = mean(volume_series[-vol_period:]) if vol_period else 0.0
        latest_rvol = latest_vol / avg_vol if avg_vol else 1.0
        rvol_engine = "python"

    obv_values = obv(points)
    obv_slope = obv_values[-1] - obv_values[-min(5, len(obv_values))]
    obv_trend = "up" if obv_slope > 0 else "down" if obv_slope < 0 else "flat"
    cmf_values = cmf(points, period=min(20, len(points)))
    latest_cmf = cmf_values[-1] if cmf_values else 0.0

    volume_score = 0.0
    if latest_rvol >= payload.volumeSpikeThreshold:
        volume_score += 0.45
    if obv_slope > 0:
        volume_score += 0.3
    if latest_cmf > 0:
        volume_score += 0.25
    volume_score = clamp(volume_score, 0.0, 1.0)

    bullish = slope_value > 0 and heartbeat >= payload.heartbeatThreshold and volume_score >= 0.55
    bearish = slope_value < 0 and heartbeat >= payload.heartbeatThreshold and volume_score >= 0.55
    if bullish:
        signal: SignalDirection = "buy"
    elif bearish:
        signal = "sell"
    else:
        signal = "neutral"

    confidence = clamp((sma_score + heartbeat + volume_score) / 3.0, 0.0, 1.0)
    components = {
        "sma50_slope": CompositeComponent(
            score=sma_score,
            details={
                "value": round(slope_norm, 6),
                "direction": sma_direction,
                "raw": round(slope_value, 6),
                "engine": sma_engine,
                "dataframeEngine": dataframe_engine,
            },
        ),
        "heartbeat": CompositeComponent(score=heartbeat, details=heartbeat_details),
        "volume_power": CompositeComponent(
            score=volume_score,
            details={
                "rvol": round(latest_rvol, 4),
                "rvolEngine": rvol_engine,
                "obv_trend": obv_trend,
                "cmf": round(latest_cmf, 6),
                "dataframeEngine": dataframe_engine,
            },
        ),
    }

    return CompositeSignalResponse(
        signal=signal,
        confidence=confidence,
        components=components,
        timestamp=points[-1].time,
    )


# ---------------------------------------------------------------------------
# Rob Booker Reversal (Kaabar 2026, Ch. 12)
# Stochastic(70, 10, 10) + MACD(12, 26, 9) Zero-Cross
# Backtest: 60% hit, Profit Factor 1.50, Sortino 2.05
# ---------------------------------------------------------------------------


def calculate_rob_booker_reversal(
    payload: RobBookerReversalRequest,  # noqa: F821
) -> IndicatorResponse:
    """Rob Booker Reversal: MACD zero-cross confirmed by extreme Stochastic.

    Bullish: MACD crosses above 0 AND %K(70,10,10) < 30
    Bearish: MACD crosses below 0 AND %K(70,10,10) > 70

    The unusual Stochastic lookback (70) measures historical context:
    "is the market oversold relative to its long-term range?"
    """

    pts = payload.ohlcv
    c = closes(pts)

    # MACD
    macd_line, _, _ = macd(c, payload.macd_fast, payload.macd_slow, payload.macd_signal)

    # Stochastic with custom params — need raw %K then smooth it
    h = highs(pts)
    lo = lows(pts)
    n = len(c)
    raw_k: list[float] = []
    for i in range(n):
        start = max(0, i + 1 - payload.stoch_k_period)
        period_h = max(h[start : i + 1])
        period_l = min(lo[start : i + 1])
        denom = period_h - period_l
        raw_k.append(100.0 * (c[i] - period_l) / denom if denom != 0.0 else 50.0)
    # Smooth %K with SMA(stoch_smooth_k)
    smooth_k = sma(raw_k, payload.stoch_smooth_k)

    signals: list[float] = [0.0] * n
    for i in range(1, n):
        # MACD zero-cross
        macd_cross_up = macd_line[i] > 0 and macd_line[i - 1] <= 0
        macd_cross_down = macd_line[i] < 0 and macd_line[i - 1] >= 0
        if macd_cross_up and smooth_k[i] < payload.stoch_lower:
            signals[i] = 1.0
        elif macd_cross_down and smooth_k[i] > payload.stoch_upper:
            signals[i] = -1.0

    return IndicatorResponse(
        data=[IndicatorPoint(time=pts[i].time, value=signals[i]) for i in range(n)],
        metadata={
            "indicator": "ROB_BOOKER_REVERSAL",
            "stoch_k_period": payload.stoch_k_period,
            "stoch_smooth_k": payload.stoch_smooth_k,
            "macd_fast": payload.macd_fast,
            "macd_slow": payload.macd_slow,
            "points": n,
        },
    )


# ---------------------------------------------------------------------------
# Cross-Asset RSI Convergence (Kaabar 2026, Ch. 6)
# Works for any inversely-correlated pair: SPX+VIX, Equities+Bonds, USD+Gold
# ---------------------------------------------------------------------------


def calculate_cross_asset_convergence(
    payload: CrossAssetConvergenceRequest,  # noqa: F821
) -> CrossAssetConvergenceResponse:  # noqa: F821
    """RSI convergence across inversely-correlated assets.

    Bullish: primary RSI < lower (oversold) AND inverse RSI > upper (overbought)
    Bearish: primary RSI > upper AND inverse RSI < lower

    Kaabar (Ch.6): "Imagine having a bullish signal from the RSI on the S&P 500,
    and at the same time, there is a bearish signal from the RSI on VIX."
    """
    from indicator_engine.models import CrossAssetConvergenceResponse  # noqa: F811

    p_rsi = rsi(payload.primary_closes, payload.rsi_period)
    i_rsi = rsi(payload.inverse_closes, payload.rsi_period)
    n = min(len(p_rsi), len(i_rsi))

    signals: list[float] = [0.0] * n
    for i in range(n):
        p, inv = p_rsi[i], i_rsi[i]
        # Bullish convergence: primary oversold + inverse overbought
        if p < payload.lower and inv > payload.upper:
            signals[i] = 1.0
        # Bearish convergence: primary overbought + inverse oversold
        elif p > payload.upper and inv < payload.lower:
            signals[i] = -1.0

    return CrossAssetConvergenceResponse(
        signals=signals,
        primary_rsi=p_rsi[:n],
        inverse_rsi=i_rsi[:n],
        metadata={
            "indicator": "CROSS_ASSET_RSI_CONVERGENCE",
            "rsi_period": payload.rsi_period,
            "thresholds": [payload.lower, payload.upper],
            "points": n,
        },
    )


# ---------------------------------------------------------------------------
# RSI V-Technique (Kaabar 2026, Ch. 3)
# RSI(5), barriers 15/85, V-bounce pattern at oversold/overbought extremes
# ---------------------------------------------------------------------------


def calculate_rsi_v_technique(
    payload: RSIVTechniqueRequest,  # noqa: F821
) -> IndicatorResponse:
    """RSI V-Technique: V-shaped bounce from extreme zone.

    Bullish: RSI dips below lower, exits while still < 50 (V-bounce from oversold).
    Bearish: RSI spikes above upper, drops while still > 50 (Lambda-form from overbought).
    """
    pts = payload.ohlcv
    c = closes(pts)
    rs = rsi(c, payload.rsi_period)
    n = len(pts)
    signals: list[float] = [0.0] * n
    for i in range(2, n):
        # V-bounce: was above lower → dipped below → exited back (still < 50)
        if rs[i] > payload.lower and rs[i] < 50 and rs[i - 1] < payload.lower and rs[i - 2] > payload.lower:
            signals[i] = 1.0
        # Lambda: was below upper → spiked above → dropped back (still > 50)
        elif rs[i] < payload.upper and rs[i] > 50 and rs[i - 1] > payload.upper and rs[i - 2] < payload.upper:
            signals[i] = -1.0
    return IndicatorResponse(
        data=[IndicatorPoint(time=pts[i].time, value=signals[i]) for i in range(n)],
        metadata={"indicator": "RSI_V_TECHNIQUE", "rsi_period": payload.rsi_period, "points": n},
    )


# ---------------------------------------------------------------------------
# RSI DCC — Double Conservative Confirmation (Kaabar 2026, Ch. 3)
# Fibonacci dual-RSI(13, 34) simultaneous threshold cross
# ---------------------------------------------------------------------------


def calculate_rsi_dcc(
    payload: RSIDCCRequest,  # noqa: F821
) -> IndicatorResponse:
    """RSI DCC: both RSI(13) and RSI(34) cross threshold on same bar (±tolerance).

    Kaabar: "A personal favorite of mine, despite having significantly less frequency."
    Bullish: both cross above lower. Bearish: both cross below upper.
    """
    pts = payload.ohlcv
    c = closes(pts)
    rs_fast = rsi(c, payload.fast_period)
    rs_slow = rsi(c, payload.slow_period)
    n = len(pts)
    tol = payload.tolerance
    signals: list[float] = [0.0] * n

    for i in range(1, n):
        # Fast RSI crosses above lower
        fast_bull = rs_fast[i] > payload.lower and rs_fast[i - 1] <= payload.lower
        # Slow RSI crosses above lower (within ±tolerance bars)
        slow_bull = any(
            j >= 1 and rs_slow[j] > payload.lower and rs_slow[j - 1] <= payload.lower
            for j in range(max(1, i - tol), min(n, i + tol + 1))
        )
        if fast_bull and slow_bull:
            signals[i] = 1.0
            continue

        # Fast RSI crosses below upper
        fast_bear = rs_fast[i] < payload.upper and rs_fast[i - 1] >= payload.upper
        slow_bear = any(
            j >= 1 and rs_slow[j] < payload.upper and rs_slow[j - 1] >= payload.upper
            for j in range(max(1, i - tol), min(n, i + tol + 1))
        )
        if fast_bear and slow_bear:
            signals[i] = -1.0

    return IndicatorResponse(
        data=[IndicatorPoint(time=pts[i].time, value=signals[i]) for i in range(n)],
        metadata={
            "indicator": "RSI_DCC",
            "fast_period": payload.fast_period,
            "slow_period": payload.slow_period,
            "points": n,
        },
    )


# ---------------------------------------------------------------------------
# RSI MA Cross Technique (Kaabar 2026, Ch. 3)
# RSI crosses its own SMA while in extreme zone
# ---------------------------------------------------------------------------


def calculate_rsi_ma_cross(
    payload: RSIMACrossRequest,  # noqa: F821
) -> IndicatorResponse:
    """RSI MA Cross: RSI crosses above/below SMA(RSI) while in extreme zone.

    Bullish: RSI crosses above SMA(RSI) while RSI < lower (oversold bounce).
    Bearish: RSI crosses below SMA(RSI) while RSI > upper (overbought reversal).
    """
    pts = payload.ohlcv
    c = closes(pts)
    rs = rsi(c, payload.rsi_period)
    rs_sma = sma(rs, payload.sma_period)
    n = len(pts)
    signals: list[float] = [0.0] * n
    for i in range(1, n):
        if rs[i] > rs_sma[i] and rs[i - 1] <= rs_sma[i - 1] and rs[i] < payload.lower:
            signals[i] = 1.0
        elif rs[i] < rs_sma[i] and rs[i - 1] >= rs_sma[i - 1] and rs[i] > payload.upper:
            signals[i] = -1.0
    return IndicatorResponse(
        data=[IndicatorPoint(time=pts[i].time, value=signals[i]) for i in range(n)],
        metadata={
            "indicator": "RSI_MA_CROSS",
            "rsi_period": payload.rsi_period,
            "sma_period": payload.sma_period,
            "points": n,
        },
    )
