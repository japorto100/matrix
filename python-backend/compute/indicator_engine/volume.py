"""volume.py — Volume-based indicators.

Extracted from pipeline.py (Phase A, 20.03.2026).

Primitives: vwap, obv, cmf
Endpoints:  calculate_vwap
"""

from __future__ import annotations

from indicator_engine.helpers import volumes
from indicator_engine.models import (
    IndicatorPoint,
    IndicatorResponse,
    OHLCVPoint,
    VWAPRequest,
)
from indicator_engine.trend import sma


# ---------------------------------------------------------------------------
# Volume primitives
# ---------------------------------------------------------------------------


def vwap(points: list[OHLCVPoint]) -> list[float]:
    """VWAP = cumulative(typical_price * volume) / cumulative(volume).

    Typical price = (high + low + close) / 3. No daily reset.
    """
    result: list[float] = []
    cum_tpv = 0.0
    cum_vol = 0.0
    for p in points:
        tp = (p.high + p.low + p.close) / 3.0
        cum_tpv += tp * p.volume
        cum_vol += p.volume
        result.append(cum_tpv / cum_vol if cum_vol > 0.0 else p.close)
    return result


def obv(points: list[OHLCVPoint]) -> list[float]:
    """On-Balance Volume — cumulative volume direction indicator."""
    if not points:
        return []
    values = [0.0]
    for i in range(1, len(points)):
        if points[i].close > points[i - 1].close:
            values.append(values[-1] + points[i].volume)
        elif points[i].close < points[i - 1].close:
            values.append(values[-1] - points[i].volume)
        else:
            values.append(values[-1])
    return values


def cmf(points: list[OHLCVPoint], period: int = 20) -> list[float]:
    """Chaikin Money Flow — measures buying/selling pressure over a rolling period."""
    mfv: list[float] = []
    vols = volumes(points)
    for point in points:
        hl_range = point.high - point.low
        multiplier = ((point.close - point.low) - (point.high - point.close)) / hl_range if hl_range > 0 else 0.0
        mfv.append(multiplier * point.volume)
    sum_mfv = sma(mfv, period)
    sum_vol = sma(vols, period)
    return [sum_mfv[i] / sum_vol[i] if sum_vol[i] else 0.0 for i in range(len(points))]


# ---------------------------------------------------------------------------
# Volume Profile / POC
# ---------------------------------------------------------------------------


def volume_profile(
    high: list[float],
    low: list[float],
    volume: list[float],
    num_bins: int = 24,
    va_pct: float = 0.70,
) -> dict:
    """Volume Profile with Point of Control (POC) and Value Area.

    Distributes volume proportionally across price bins based on bar H-L overlap.
    TradingView defaults: num_bins=24, va_pct=0.70 (70% of total volume).

    Returns dict with:
        poc_price: float — price level with highest volume
        va_high: float — Value Area upper bound
        va_low: float — Value Area lower bound
        histogram: list[dict] — {price_low, price_high, volume} per bin
    """
    n = len(high)
    if n == 0:
        return {"poc_price": 0.0, "va_high": 0.0, "va_low": 0.0, "histogram": []}

    price_min = min(low)
    price_max = max(high)
    price_range = price_max - price_min
    if price_range <= 0:
        return {
            "poc_price": price_min,
            "va_high": price_min,
            "va_low": price_min,
            "histogram": [{"price_low": price_min, "price_high": price_min, "volume": sum(volume)}],
        }

    bin_size = price_range / num_bins
    histogram = [0.0] * num_bins

    # Distribute volume proportionally by H-L overlap with each bin
    for i in range(n):
        bar_range = high[i] - low[i]
        for b in range(num_bins):
            bin_low = price_min + b * bin_size
            bin_high = bin_low + bin_size
            overlap = max(0.0, min(high[i], bin_high) - max(low[i], bin_low))
            if bar_range > 0:
                vol_fraction = overlap / bar_range
            else:
                vol_fraction = 1.0 if bin_low <= low[i] < bin_high else 0.0
            histogram[b] += volume[i] * vol_fraction

    # POC = bin with max volume
    poc_bin = max(range(num_bins), key=lambda b: histogram[b])
    poc_price = price_min + (poc_bin + 0.5) * bin_size

    # Value Area — expand from POC until va_pct of total volume reached
    total_vol = sum(histogram)
    target_vol = total_vol * va_pct
    cumulative = histogram[poc_bin]
    lo_idx = poc_bin
    hi_idx = poc_bin

    while cumulative < target_vol and (lo_idx > 0 or hi_idx < num_bins - 1):
        vol_below = histogram[lo_idx - 1] if lo_idx > 0 else 0.0
        vol_above = histogram[hi_idx + 1] if hi_idx < num_bins - 1 else 0.0
        if vol_below >= vol_above and lo_idx > 0:
            lo_idx -= 1
            cumulative += histogram[lo_idx]
        elif hi_idx < num_bins - 1:
            hi_idx += 1
            cumulative += histogram[hi_idx]
        else:
            lo_idx -= 1
            cumulative += histogram[lo_idx]

    va_low = price_min + lo_idx * bin_size
    va_high = price_min + (hi_idx + 1) * bin_size

    hist_out = [
        {
            "price_low": round(price_min + b * bin_size, 6),
            "price_high": round(price_min + (b + 1) * bin_size, 6),
            "volume": round(histogram[b], 2),
        }
        for b in range(num_bins)
    ]

    return {
        "poc_price": round(poc_price, 6),
        "va_high": round(va_high, 6),
        "va_low": round(va_low, 6),
        "histogram": hist_out,
    }


# ---------------------------------------------------------------------------
# Endpoint handlers
# ---------------------------------------------------------------------------


def calculate_vwap(payload: VWAPRequest) -> IndicatorResponse:
    """VWAP endpoint — cumulative, no daily reset."""
    vwap_vals = vwap(payload.ohlcv)
    return IndicatorResponse(
        data=[IndicatorPoint(time=payload.ohlcv[i].time, value=vwap_vals[i]) for i in range(len(payload.ohlcv))],
        metadata={"indicator": "VWAP"},
    )
