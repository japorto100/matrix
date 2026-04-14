"""rainbow.py — Kaabar Rainbow Collection + proprietary patterns.

Extracted from pipeline.py (Phase A, 20.03.2026).
All Kaabar-proprietary — Python-only by design (no Rust port planned).

Functions:
  Rainbow:  _red, _orange, _yellow, _green, _blue, _indigo, _violet
  Endpoints: calculate_rainbow_collection, calculate_r_pattern, calculate_gap_pattern
  Helper:   _rainbow_series
"""

from __future__ import annotations

from indicator_engine.helpers import closes, highs, lows, slope
from indicator_engine.models import (
    GapPatternRequest,
    GapPatternResponse,
    IndicatorPoint,
    IndicatorResponse,
    OHLCVPoint,
    RPatternRequest,
    RPatternResponse,
    RainbowRequest,
    RainbowResponse,
    RainbowSignalSeries,
)
from indicator_engine.oscillators import rsi
from indicator_engine.trend import hma
from indicator_engine.volatility import calculate_atr, e_bollinger_bands


_FIB_LAGS = (1, 2, 3, 5, 8, 13, 21)


def _rainbow_series(
    name: str, signals: list[float], points: list[OHLCVPoint]
) -> RainbowSignalSeries:
    return RainbowSignalSeries(
        data=[IndicatorPoint(time=p.time, value=signals[i]) for i, p in enumerate(points)],
        metadata={"indicator": name, "points": len(signals)},
    )


# ---------------------------------------------------------------------------
# 7 Rainbow indicators (Kaabar 2026, Ch. 3)
# Each returns list[float]: 1.0 bullish, -1.0 bearish, 0.0 neutral.
# Signals emitted at i+1 (next bar), matching book convention.
# ---------------------------------------------------------------------------


def _red(closes_: list[float], period: int = 20, num_std: float = 2.0) -> list[float]:
    """EMA-Bollinger extreme-duration reversal (min 3 periods outside band)."""
    upper, middle, lower = e_bollinger_bands(closes_, period, num_std)
    n = len(closes_)
    out = [0.0] * n
    for i in range(3, n - 1):
        c, c1, c2, c3 = closes_[i], closes_[i - 1], closes_[i - 2], closes_[i - 3]
        if c > lower[i] and c < middle[i] and c1 < lower[i - 1] and c2 < lower[i - 2] and c3 < lower[i - 3]:
            out[i + 1] = 1.0
        elif c < upper[i] and c > middle[i] and c1 > upper[i - 1] and c2 > upper[i - 2] and c3 > upper[i - 3]:
            out[i + 1] = -1.0
    return out


def _orange(
    closes_: list[float],
    rsi_period: int = 8,
    lower: float = 35.0,
    upper: float = 65.0,
) -> list[float]:
    """RSI extreme-duration reversal (min 5 bars in oversold/overbought zone)."""
    rs = rsi(closes_, rsi_period)
    n = len(closes_)
    out = [0.0] * n
    for i in range(5, n - 1):
        r = rs[i]
        if r > lower and r < 50 and all(rs[i - k] < lower for k in range(1, 6)):
            out[i + 1] = 1.0
        elif r < upper and r > 50 and all(rs[i - k] > upper for k in range(1, 6)):
            out[i + 1] = -1.0
    return out


def _yellow(
    closes_: list[float],
    rsi_period: int = 14,
    slope_period: int = 14,
    lower: float = 35.0,
    upper: float = 65.0,
) -> list[float]:
    """RSI-slope vs price-slope divergence while RSI is in extreme zone."""
    rs = rsi(closes_, rsi_period)
    sl_rsi = slope(rs, slope_period)
    sl_close = slope(closes_, slope_period)
    n = len(closes_)
    out = [0.0] * n
    for i in range(slope_period + 1, n - 1):
        if sl_rsi[i] > 0 and sl_rsi[i - 1] < 0 and sl_close[i] < 0 and sl_close[i - 1] < 0 and rs[i] < lower:
            out[i + 1] = 1.0
        elif sl_rsi[i] < 0 and sl_rsi[i - 1] > 0 and sl_close[i] > 0 and sl_close[i - 1] > 0 and rs[i] > upper:
            out[i + 1] = -1.0
    return out


def _green(
    closes_: list[float],
    rsi_period: int = 14,
    slope_period: int = 14,
    lower: float = 35.0,
    upper: float = 65.0,
) -> list[float]:
    """RSI-slope zero-cross while RSI is in extreme zone."""
    rs = rsi(closes_, rsi_period)
    sl_rsi = slope(rs, slope_period)
    n = len(closes_)
    out = [0.0] * n
    for i in range(slope_period + 1, n - 1):
        if sl_rsi[i] > 0 and sl_rsi[i - 1] < 0 and rs[i] < lower:
            out[i + 1] = 1.0
        elif sl_rsi[i] < 0 and sl_rsi[i - 1] > 0 and rs[i] > upper:
            out[i + 1] = -1.0
    return out


def _blue(
    closes_: list[float],
    highs_: list[float],
    lows_: list[float],
    rsi_period: int = 5,
    slope_period: int = 5,
    lower: float = 30.0,
    upper: float = 70.0,
    margin: float = 5.0,
) -> list[float]:
    """RSI applied to price-slope: crosses into 30-35 / 65-70 with confirming H/L."""
    sl_close = slope(closes_, slope_period)
    rs_slope = rsi(sl_close, rsi_period)
    n = len(closes_)
    out = [0.0] * n
    for i in range(slope_period + rsi_period + 1, n - 1):
        r, r1 = rs_slope[i], rs_slope[i - 1]
        if r > lower and r < lower + margin and r1 < lower and lows_[i] < lows_[i - 1]:
            out[i + 1] = 1.0
        elif r < upper and r > upper - margin and r1 > upper and highs_[i] > highs_[i - 1]:
            out[i + 1] = -1.0
    return out


def _indigo(closes_: list[float]) -> list[float]:
    """Fibonacci-indexed consecutive comparison."""
    fib_ext = _FIB_LAGS + (34,)
    min_i = fib_ext[-1] + 1
    n = len(closes_)
    out = [0.0] * n
    for i in range(min_i, n - 1):
        if (
            closes_[i] > closes_[i - 1]
            and all(closes_[i - _FIB_LAGS[k]] < closes_[i - fib_ext[k + 1]] for k in range(len(_FIB_LAGS)))
        ):
            out[i + 1] = 1.0
        elif (
            closes_[i] < closes_[i - 1]
            and all(closes_[i - _FIB_LAGS[k]] > closes_[i - fib_ext[k + 1]] for k in range(len(_FIB_LAGS)))
        ):
            out[i + 1] = -1.0
    return out


def _violet(closes_: list[float], hma_period: int = 20) -> list[float]:
    """HMA cross with Fibonacci-indexed confirmation bars."""
    hma_vals = hma(closes_, hma_period)
    min_i = _FIB_LAGS[-1] + 1
    n = len(closes_)
    out = [0.0] * n
    for i in range(hma_period + min_i, n - 1):
        if closes_[i] > hma_vals[i] and all(closes_[i - lag] < hma_vals[i - lag] for lag in _FIB_LAGS):
            out[i + 1] = 1.0
        elif closes_[i] < hma_vals[i] and all(closes_[i - lag] > hma_vals[i - lag] for lag in _FIB_LAGS):
            out[i + 1] = -1.0
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def calculate_rainbow_collection(payload: RainbowRequest) -> RainbowResponse:
    """Compute all 7 Rainbow indicators (Kaabar 2026, Ch. 3)."""
    pts = payload.ohlcv
    c = closes(pts)
    h = highs(pts)
    lo = lows(pts)
    return RainbowResponse(
        red=_rainbow_series("RAINBOW_RED", _red(c), pts),
        orange=_rainbow_series("RAINBOW_ORANGE", _orange(c), pts),
        yellow=_rainbow_series("RAINBOW_YELLOW", _yellow(c), pts),
        green=_rainbow_series("RAINBOW_GREEN", _green(c), pts),
        blue=_rainbow_series("RAINBOW_BLUE", _blue(c, h, lo), pts),
        indigo=_rainbow_series("RAINBOW_INDIGO", _indigo(c), pts),
        violet=_rainbow_series("RAINBOW_VIOLET", _violet(c), pts),
    )


def calculate_rainbow_confluence(
    payload: RainbowRequest,
    window: int = 3,
    min_count: int = 3,
) -> IndicatorResponse:
    """Rainbow Confluence Detection (Kaabar Ch.3).

    Scans a ±window bar range across all 7 Rainbow indicators.
    If >= min_count fire in the same direction within that window,
    emits the count as signal strength (positive=bullish, negative=bearish).

    Kaabar: "Signals should occur within ±3 time periods of each other."
    """
    pts = payload.ohlcv
    c = closes(pts)
    h = highs(pts)
    lo = lows(pts)
    arrays = [_red(c), _orange(c), _yellow(c), _green(c), _blue(c, h, lo), _indigo(c), _violet(c)]
    n = len(pts)
    composite: list[float] = [0.0] * n

    for i in range(n):
        bull_count = 0
        bear_count = 0
        for arr in arrays:
            lo_idx = max(0, i - window)
            hi_idx = min(n, i + window + 1)
            if any(arr[j] == 1.0 for j in range(lo_idx, hi_idx)):
                bull_count += 1
            if any(arr[j] == -1.0 for j in range(lo_idx, hi_idx)):
                bear_count += 1
        if bull_count >= min_count:
            composite[i] = float(bull_count)
        elif bear_count >= min_count:
            composite[i] = -float(bear_count)

    return IndicatorResponse(
        data=[IndicatorPoint(time=pts[i].time, value=composite[i]) for i in range(n)],
        metadata={
            "indicator": "RAINBOW_CONFLUENCE",
            "window": window,
            "min_count": min_count,
            "points": n,
        },
    )


def rainbow_composite_score(payload: RainbowRequest) -> IndicatorResponse:
    """Kaabar Ch.3: Average of all 7 Rainbow indicators as a single composite score.

    Also emits WMA/IWMA cross signals as discrete {-1, 0, 1} values.
    """
    pts = payload.ohlcv
    c = closes(pts)
    h = highs(pts)
    lo = lows(pts)
    red = _red(c)
    orange = _orange(c)
    yellow = _yellow(c)
    green = _green(c)
    blue = _blue(c, h, lo)
    indigo = _indigo(c)
    violet = _violet(c)
    n = len(pts)
    composite = [
        (red[i] + orange[i] + yellow[i] + green[i] + blue[i] + indigo[i] + violet[i]) / 7.0
        for i in range(n)
    ]
    return IndicatorResponse(
        data=[IndicatorPoint(time=pts[i].time, value=composite[i]) for i in range(n)],
        metadata={"indicator": "RAINBOW_COMPOSITE", "points": n},
    )


# ---------------------------------------------------------------------------
# R-Pattern (Kaabar 2026, Ch. 7)
# ---------------------------------------------------------------------------


def calculate_r_pattern(payload: RPatternRequest) -> RPatternResponse:
    """Detect R-Pattern reversal signals (Kaabar 2026, Ch. 7)."""
    pts = payload.ohlcv
    c = closes(pts)
    h = highs(pts)
    lo = lows(pts)
    rs = rsi(c, payload.rsi_period)
    n = len(pts)
    signals = [0.0] * n

    for i in range(3, n - 1):
        if (lo[i] > lo[i - 1] and lo[i - 1] > lo[i - 2] and lo[i - 2] < lo[i - 3]
                and c[i] > c[i - 1] and c[i - 1] > c[i - 2] and c[i - 2] > c[i - 3]
                and rs[i] < 50.0):
            signals[i + 1] = 1.0
        elif (h[i] < h[i - 1] and h[i - 1] < h[i - 2] and h[i - 2] > h[i - 3]
              and c[i] < c[i - 1] and c[i - 1] < c[i - 2] and c[i - 2] < c[i - 3]
              and rs[i] > 50.0):
            signals[i + 1] = -1.0

    return RPatternResponse(
        data=[IndicatorPoint(time=p.time, value=signals[i]) for i, p in enumerate(pts)],
        metadata={"indicator": "R_PATTERN", "rsiPeriod": payload.rsi_period, "points": n},
    )


# ---------------------------------------------------------------------------
# Gap-Pattern (Kaabar 2026, Ch. 10)
# ---------------------------------------------------------------------------


def calculate_gap_pattern(payload: GapPatternRequest) -> GapPatternResponse:
    """Detect tradeable gap patterns with ATR-based size filter (Kaabar 2026, Ch. 10)."""
    pts = payload.ohlcv
    n = len(pts)
    atr_vals = calculate_atr(pts, payload.atr_period)
    signals = [0.0] * n

    for i in range(1, n):
        prev_close = pts[i - 1].close
        cur_open = pts[i].open
        gap_size = abs(cur_open - prev_close)
        min_gap = atr_vals[i - 1] * payload.min_size

        if gap_size <= min_gap:
            continue

        if cur_open < prev_close:
            signals[i] = 1.0
        elif cur_open > prev_close:
            signals[i] = -1.0

    return GapPatternResponse(
        data=[IndicatorPoint(time=p.time, value=signals[i]) for i, p in enumerate(pts)],
        metadata={
            "indicator": "GAP_PATTERN",
            "atrPeriod": payload.atr_period,
            "minSize": payload.min_size,
            "points": n,
        },
    )
