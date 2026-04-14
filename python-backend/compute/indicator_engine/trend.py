"""trend.py — Moving average family + Ichimoku.

Extracted from pipeline.py (Phase A, 20.03.2026).
Contains all MA primitives, endpoint handlers, and Ichimoku system.

Functions:
  Primitives: sma, ema, smma, wma, hma, kama, alma, iwma, ols_ma
  Endpoints:  calculate_exotic_ma, calculate_hma, calculate_ichimoku
  Private:    _ichi_midpoint
"""

from __future__ import annotations

from math import exp
from statistics import mean

from indicator_engine.helpers import closes, volumes
from indicator_engine.models import (
    ExoticMARequest,
    HMARequest,
    IchimokuRequest,
    IchimokuResponse,
    IchimokuSignals,
    IndicatorPoint,
    IndicatorResponse,
)
from indicator_engine.rust_bridge import (
    calculate_indicators_batch as rust_calculate_indicators_batch,
)


# ---------------------------------------------------------------------------
# MA primitives
# ---------------------------------------------------------------------------


def sma(values: list[float], period: int) -> list[float]:
    """Simple Moving Average — running sum, O(n)."""
    if period <= 1:
        return values[:]
    output: list[float] = []
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= period:
            running -= values[i - period]
        window_size = min(period, i + 1)
        output.append(running / window_size)
    return output


def ema(values: list[float], period: int) -> list[float]:
    """Exponential Moving Average — alpha = 2/(period+1)."""
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (1.0 - alpha) * output[-1])
    return output


def smma(values: list[float], period: int) -> list[float]:
    """Smoothed Moving Average (Wilder's smoothing) — alpha = 1/period."""
    if not values:
        return []
    output = [values[0]]
    for value in values[1:]:
        output.append((output[-1] * (period - 1) + value) / period)
    return output


def wma(values: list[float], period: int) -> list[float]:
    """Weighted Moving Average — linearly weighted, most recent bar has highest weight."""
    if not values:
        return []
    out: list[float] = []
    for i in range(len(values)):
        start = max(0, i + 1 - period)
        window = values[start : i + 1]
        w = list(range(1, len(window) + 1))
        w_sum = sum(w)
        out.append(sum(v * wt for v, wt in zip(window, w)) / w_sum)
    return out


def hma(values: list[float], period: int) -> list[float]:
    """Hull Moving Average = WMA(2*WMA(n/2) - WMA(n), sqrt(n)).

    Reduces lag vs SMA/EMA while staying smooth.
    """
    if len(values) < period:
        return values[:]
    half = max(1, period // 2)
    sqrt_p = max(1, int(period**0.5))
    wma_half = wma(values, half)
    wma_full = wma(values, period)
    diff = [2.0 * h - f for h, f in zip(wma_half, wma_full)]
    return wma(diff, sqrt_p)


def kama(values: list[float], period: int, fast: int = 2, slow: int = 30) -> list[float]:
    """Kaufman Adaptive Moving Average — adapts speed based on efficiency ratio."""
    if not values:
        return []
    result = [values[0]]
    fast_sc = 2.0 / (fast + 1.0)
    slow_sc = 2.0 / (slow + 1.0)
    for i in range(1, len(values)):
        if i < period:
            result.append(values[i])
            continue
        change = abs(values[i] - values[i - period])
        volatility = sum(abs(values[j] - values[j - 1]) for j in range(i - period + 1, i + 1)) or 1e-9
        er = change / volatility
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        result.append(result[-1] + sc * (values[i] - result[-1]))
    return result


def alma(values: list[float], period: int, offset: float = 0.85, sigma: float = 6.0) -> list[float]:
    """Arnaud Legoux Moving Average — Gaussian-weighted, offset controls responsiveness."""
    if period <= 1:
        return values[:]
    result: list[float] = []
    m = offset * (period - 1)
    s = period / sigma
    raw_weights = [exp(-((i - m) ** 2) / (2 * s * s)) for i in range(period)]
    norm = sum(raw_weights) or 1.0
    weights = [weight / norm for weight in raw_weights]
    for i in range(len(values)):
        start = max(0, i - period + 1)
        window = values[start : i + 1]
        if len(window) < period:
            result.append(mean(window))
            continue
        value = 0.0
        for j, close in enumerate(window):
            value += close * weights[j]
        result.append(value)
    return result


def iwma(values: list[float], period: int) -> list[float]:
    """Inverse-Weighted Moving Average — older bars get more weight (contrarian smoothing)."""
    if period <= 1:
        return values[:]
    result: list[float] = []
    weights = [1.0 / (i + 1) for i in range(period)]
    denominator = sum(weights)
    for i in range(len(values)):
        start = max(0, i - period + 1)
        window = values[start : i + 1]
        if len(window) < period:
            result.append(mean(window))
            continue
        weighted = 0.0
        for j, value in enumerate(window):
            weighted += value * weights[period - 1 - j]
        result.append(weighted / denominator)
    return result


def ols_ma(values: list[float], period: int) -> list[float]:
    """Ordinary Least Squares Moving Average — linear regression endpoint value."""
    if period <= 1:
        return values[:]
    result: list[float] = []
    x_vals = list(range(period))
    x_mean = mean(x_vals)
    denominator = sum((x - x_mean) ** 2 for x in x_vals) or 1.0
    for i in range(len(values)):
        start = max(0, i - period + 1)
        window = values[start : i + 1]
        if len(window) < period:
            result.append(mean(window))
            continue
        y_mean = mean(window)
        numerator = sum((x_vals[j] - x_mean) * (window[j] - y_mean) for j in range(period))
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        result.append(intercept + slope * (period - 1))
    return result


# ---------------------------------------------------------------------------
# Endpoint handlers
# ---------------------------------------------------------------------------


def calculate_exotic_ma(payload: ExoticMARequest) -> IndicatorResponse:
    """Unified exotic MA endpoint — dispatches to the correct MA primitive.

    Supports Rust-first path for SMA/EMA via batch bridge.
    """
    series = closes(payload.ohlcv)
    ma_type = payload.maType.lower()

    if ma_type == "kama":
        values = kama(series, payload.period)
    elif ma_type == "alma":
        values = alma(series, payload.period, sigma=payload.alma_sigma)
    elif ma_type == "iwma":
        values = iwma(series, payload.period)
    elif ma_type == "ols":
        values = ols_ma(series, payload.period)
    elif ma_type == "ema":
        rust_batch = rust_calculate_indicators_batch(
            [p.time for p in payload.ohlcv],
            [p.open for p in payload.ohlcv],
            [p.high for p in payload.ohlcv],
            [p.low for p in payload.ohlcv],
            series,
            volumes(payload.ohlcv),
            [f"ema_{payload.period}"],
        )
        key = f"ema_{payload.period}"
        if rust_batch and key in rust_batch and len(rust_batch[key]) == len(series):
            values = [float(v) for v in rust_batch[key]]
        else:
            values = ema(series, payload.period)
    elif ma_type == "sma":
        rust_batch = rust_calculate_indicators_batch(
            [p.time for p in payload.ohlcv],
            [p.open for p in payload.ohlcv],
            [p.high for p in payload.ohlcv],
            [p.low for p in payload.ohlcv],
            series,
            volumes(payload.ohlcv),
            [f"sma_{payload.period}"],
        )
        key = f"sma_{payload.period}"
        if rust_batch and key in rust_batch and len(rust_batch[key]) == len(series):
            values = [float(v) for v in rust_batch[key]]
        else:
            values = sma(series, payload.period)
    elif ma_type == "smma":
        values = smma(series, payload.period)
    else:
        values = sma(series, payload.period)

    return IndicatorResponse(
        data=[IndicatorPoint(time=point.time, value=values[i]) for i, point in enumerate(payload.ohlcv)],
        metadata={"indicator": ma_type.upper(), "period": payload.period, "points": len(values)},
    )


def calculate_wma_iwma_cross(payload: "WMAIWMACrossRequest") -> IndicatorResponse:
    """WMA/IWMA single-parameter cross (Kaabar Ch.3).

    WMA is recent-biased, IWMA is history-biased. Same period removes one parameter.
    Bullish: WMA crosses above IWMA. Bearish: WMA crosses below IWMA.
    """
    series = closes(payload.ohlcv)
    wma_vals = wma(series, payload.period)
    iwma_vals = iwma(series, payload.period)
    n = len(series)
    signals: list[float] = [0.0] * n
    for i in range(1, n):
        if wma_vals[i] > iwma_vals[i] and wma_vals[i - 1] <= iwma_vals[i - 1]:
            signals[i] = 1.0
        elif wma_vals[i] < iwma_vals[i] and wma_vals[i - 1] >= iwma_vals[i - 1]:
            signals[i] = -1.0
    return IndicatorResponse(
        data=[IndicatorPoint(time=payload.ohlcv[i].time, value=signals[i]) for i in range(n)],
        metadata={"indicator": "WMA_IWMA_CROSS", "period": payload.period, "points": n},
    )


def calculate_hma(payload: HMARequest) -> IndicatorResponse:
    """Hull MA endpoint."""
    series = closes(payload.ohlcv)
    hma_vals = hma(series, payload.period)
    return IndicatorResponse(
        data=[IndicatorPoint(time=payload.ohlcv[i].time, value=hma_vals[i]) for i in range(len(payload.ohlcv))],
        metadata={"indicator": "HMA", "period": payload.period},
    )


# ---------------------------------------------------------------------------
# Ichimoku Kinko Hyo
# ---------------------------------------------------------------------------


def _ichi_midpoint(highs: list[float], lows: list[float], period: int) -> list[float]:
    """Rolling (max+min)/2 — core Ichimoku primitive. Returns nan for warm-up bars."""
    n = len(highs)
    out: list[float] = []
    for i in range(n):
        if i < period - 1:
            out.append(float("nan"))
        else:
            h = max(highs[i - period + 1 : i + 1])
            lo = min(lows[i - period + 1 : i + 1])
            out.append((h + lo) / 2.0)
    return out


def calculate_ichimoku(payload: IchimokuRequest) -> IchimokuResponse:
    """Ichimoku Kinko Hyo — 5 lines + signal quality flags.

    Standard periods 9/26/52 (equities). Crypto-adjusted: pass tenkan=10, kijun=30, senkou_b=60.
    displacement must equal kijun_period for standard Ichimoku (default behaviour).

    Future cloud: the last `displacement` values of span_a/B are repeated into synthetic
    future IndicatorPoints (time extrapolated from the last known bar interval).
    Set include_future=False to omit those extra points.
    """
    pts = payload.ohlcv
    n = len(pts)
    if n < 2:
        empty: list[IndicatorPoint] = []
        return IchimokuResponse(
            tenkan=empty, kijun=empty, span_a=empty, span_b=empty, chikou=empty,
            signals=IchimokuSignals(
                above_cloud=[], below_cloud=[], in_cloud=[], bullish_cloud=[],
                tk_bull=[], tk_bear=[], chikou_bull=[], chikou_bear=[],
                chikou_above_cloud=[], chikou_below_cloud=[],
                kijun_cross_bull=[], kijun_cross_bear=[], strength=[],
            ),
            metadata={"indicator": "Ichimoku", "n": 0},
        )

    highs_list = [p.high for p in pts]
    lows_list = [p.low for p in pts]
    closes_list = [p.close for p in pts]
    times_list = [p.time for p in pts]
    d = payload.displacement

    tenkan_raw = _ichi_midpoint(highs_list, lows_list, payload.tenkan_period)
    kijun_raw = _ichi_midpoint(highs_list, lows_list, payload.kijun_period)
    span_b_raw = _ichi_midpoint(highs_list, lows_list, payload.senkou_b_period)

    # span_a_raw[i] = (tenkan[i] + kijun[i]) / 2  (before forward-displacement)
    span_a_raw: list[float] = []
    for i in range(n):
        tk = tenkan_raw[i]
        kj = kijun_raw[i]
        if tk != tk or kj != kj:  # nan check
            span_a_raw.append(float("nan"))
        else:
            span_a_raw.append((tk + kj) / 2.0)

    # Cloud lines displaced forward by `d` bars
    span_a_hist: list[float] = [float("nan")] * d + span_a_raw[: n - d]
    span_b_hist: list[float] = [float("nan")] * d + span_b_raw[: n - d]
    chikou_vals: list[float] = closes_list[d:] + [float("nan")] * d

    # Future cloud: append d synthetic points extrapolating time from last known interval
    future_span_a: list[IndicatorPoint] = []
    future_span_b: list[IndicatorPoint] = []
    if payload.include_future and n >= 2:
        dt = times_list[-1] - times_list[-2]
        for j in range(1, d + 1):
            future_t = times_list[-1] + dt * j
            sa = span_a_raw[n - d + j - 1] if (n - d + j - 1) >= 0 else float("nan")
            sb = span_b_raw[n - d + j - 1] if (n - d + j - 1) >= 0 else float("nan")
            future_span_a.append(IndicatorPoint(time=future_t, value=sa))
            future_span_b.append(IndicatorPoint(time=future_t, value=sb))

    def _pts(vals: list[float], ts: list[int]) -> list[IndicatorPoint]:
        return [IndicatorPoint(time=ts[i], value=vals[i]) for i in range(len(ts))]

    tenkan_pts = _pts(tenkan_raw, times_list)
    kijun_pts = _pts(kijun_raw, times_list)
    span_a_pts = _pts(span_a_hist, times_list) + future_span_a
    span_b_pts = _pts(span_b_hist, times_list) + future_span_b
    chikou_pts = _pts(chikou_vals, times_list)

    # Signals (historical bars only — no future rows)
    nan = float("nan")
    above_cloud: list[bool] = []
    below_cloud: list[bool] = []
    in_cloud_: list[bool] = []
    bull_cloud: list[bool] = []
    tk_bull_: list[bool] = []
    tk_bear_: list[bool] = []
    chikou_bull_: list[bool] = []
    chikou_bear_: list[bool] = []
    chikou_above_cloud_: list[bool] = []
    chikou_below_cloud_: list[bool] = []
    kj_cross_bull: list[bool] = []
    kj_cross_bear: list[bool] = []
    strength: list[str] = []

    for i in range(n):
        c = closes_list[i]
        sa = span_a_hist[i]
        sb = span_b_hist[i]
        tk = tenkan_raw[i]
        kj = kijun_raw[i]

        cloud_valid = sa == sa and sb == sb  # not nan
        cloud_top = max(sa, sb) if cloud_valid else nan
        cloud_bottom = min(sa, sb) if cloud_valid else nan

        _above = cloud_valid and c > cloud_top
        _below = cloud_valid and c < cloud_bottom
        _in = cloud_valid and not _above and not _below

        _bull_cld = cloud_valid and sa > sb
        _bear_cld = cloud_valid and sa < sb

        # TK cross
        prev_tk = tenkan_raw[i - 1] if i > 0 else nan
        prev_kj = kijun_raw[i - 1] if i > 0 else nan
        lines_valid = tk == tk and kj == kj and prev_tk == prev_tk and prev_kj == prev_kj
        _tk_bull = lines_valid and tk > kj and prev_tk <= prev_kj
        _tk_bear = lines_valid and tk < kj and prev_tk >= prev_kj

        # Chikou price cross
        _chi_bull = i >= d and closes_list[i] > closes_list[i - d]
        _chi_bear = i >= d and closes_list[i] < closes_list[i - d]

        # Chikou vs cloud 26 bars ago
        if i >= d:
            sa_d = span_a_hist[i - d]
            sb_d = span_b_hist[i - d]
            cloud_d_valid = sa_d == sa_d and sb_d == sb_d
            cloud_top_d = max(sa_d, sb_d) if cloud_d_valid else nan
            cloud_bottom_d = min(sa_d, sb_d) if cloud_d_valid else nan
            _chi_above_cloud = cloud_d_valid and c > cloud_top_d
            _chi_below_cloud = cloud_d_valid and c < cloud_bottom_d
        else:
            _chi_above_cloud = False
            _chi_below_cloud = False

        # Kijun cross
        prev_c = closes_list[i - 1] if i > 0 else nan
        kj_valid = kj == kj and prev_kj == prev_kj and prev_c == prev_c
        _kj_cbull = kj_valid and c > kj and prev_c <= prev_kj
        _kj_cbear = kj_valid and c < kj and prev_c >= prev_kj

        # Signal strength score
        bull_score = int(_above) + int(_bull_cld) + int(_tk_bull) + int(_chi_bull)
        bear_score = int(_below) + int(_bear_cld) + int(_tk_bear) + int(_chi_bear)
        if bull_score == 4:
            q = "strong_bull"
        elif bull_score == 3:
            q = "weak_bull"
        elif bear_score == 4:
            q = "strong_bear"
        elif bear_score == 3:
            q = "weak_bear"
        else:
            q = "neutral"

        above_cloud.append(_above)
        below_cloud.append(_below)
        in_cloud_.append(_in)
        bull_cloud.append(_bull_cld)
        tk_bull_.append(_tk_bull)
        tk_bear_.append(_tk_bear)
        chikou_bull_.append(_chi_bull)
        chikou_bear_.append(_chi_bear)
        chikou_above_cloud_.append(_chi_above_cloud)
        chikou_below_cloud_.append(_chi_below_cloud)
        kj_cross_bull.append(_kj_cbull)
        kj_cross_bear.append(_kj_cbear)
        strength.append(q)

    return IchimokuResponse(
        tenkan=tenkan_pts,
        kijun=kijun_pts,
        span_a=span_a_pts,
        span_b=span_b_pts,
        chikou=chikou_pts,
        signals=IchimokuSignals(
            above_cloud=above_cloud,
            below_cloud=below_cloud,
            in_cloud=in_cloud_,
            bullish_cloud=bull_cloud,
            tk_bull=tk_bull_,
            tk_bear=tk_bear_,
            chikou_bull=chikou_bull_,
            chikou_bear=chikou_bear_,
            chikou_above_cloud=chikou_above_cloud_,
            chikou_below_cloud=chikou_below_cloud_,
            kijun_cross_bull=kj_cross_bull,
            kijun_cross_bear=kj_cross_bear,
            strength=strength,
        ),
        metadata={
            "indicator": "Ichimoku",
            "tenkan_period": payload.tenkan_period,
            "kijun_period": payload.kijun_period,
            "senkou_b_period": payload.senkou_b_period,
            "displacement": d,
            "n": n,
        },
    )


def parabolic_sar(
    high: list[float],
    low: list[float],
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
) -> list[float]:
    """
    Parabolic SAR — Trendfolge-Indikator (J. Welles Wilder).

    Punkte unter dem Preis → Aufwärtstrend (Long-Signal).
    Punkte über dem Preis → Abwärtstrend (Short-Signal).

    Args:
        high:     Tageshöchstkurse (gleiche Länge wie low).
        low:      Tagestiefkurse.
        af_start: Anfangs-Acceleration-Factor (default 0.02).
        af_step:  AF-Increment bei neuem Extrempunkt (default 0.02).
        af_max:   Maximaler AF (default 0.20).

    Returns:
        SAR-Serie (gleiche Länge wie high/low).

    kand-Blueprint: kand::sar(high, low, af_start, af_step, af_max)
    Phase C.1 Rust-Bridge: nach D3-Migration via rust_core.parabolic_sar().
    """
    n = len(high)
    if n == 0:
        return []
    if n == 1:
        return [low[0]]

    sar = [0.0] * n
    af = af_start
    ep = high[0]   # Extreme Point
    is_bull = True
    sar[0] = low[0]

    for i in range(1, n):
        prev_sar = sar[i - 1]
        if is_bull:
            sar[i] = prev_sar + af * (ep - prev_sar)
            # SAR darf nicht über den beiden letzten Tiefs liegen
            sar[i] = min(sar[i], low[i - 1], low[max(0, i - 2)])
            if low[i] < sar[i]:
                # Trend dreht → Abwärtstrend
                is_bull = False
                sar[i] = ep
                ep = low[i]
                af = af_start
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            sar[i] = prev_sar + af * (ep - prev_sar)
            # SAR darf nicht unter den beiden letzten Hochs liegen
            sar[i] = max(sar[i], high[i - 1], high[max(0, i - 2)])
            if high[i] > sar[i]:
                # Trend dreht → Aufwärtstrend
                is_bull = True
                sar[i] = ep
                ep = high[i]
                af = af_start
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

    return sar
