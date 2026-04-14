"""helpers.py — Shared utility functions, OHLCV extractors, and compute guards.

Extracted from pipeline.py (Phase A, 20.03.2026).
These are used across all category modules.

SOTA patterns applied:
- OHLCVSeries: single-pass extraction via attrgetter, cached_property for lazy reuse
- verify_series / non_zero_range: standard guards from nautilus-trader / pandas-ta patterns
- Simple extractors kept for backward compat with pipeline.py
"""

from __future__ import annotations

import types
from functools import cached_property
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from indicator_engine.models import OHLCVPoint

if TYPE_CHECKING:
    from indicator_engine.models import SwarmValidationResponse

pl: types.ModuleType | None
try:
    import polars as pl
except Exception:  # noqa: BLE001
    pl = None


# ---------------------------------------------------------------------------
# OHLCVSeries — single-pass column extraction with lazy caching
# ---------------------------------------------------------------------------

_extract_ohlcv = attrgetter("time", "open", "high", "low", "close", "volume")


class OHLCVSeries:
    """Wraps list[OHLCVPoint] and lazily extracts columns once.

    Use at route handler entry point — all compute functions receive this
    instead of raw list[OHLCVPoint]. Columns are extracted on first access
    and cached for reuse across multiple indicator calls.

    Example::

        series = OHLCVSeries(req.ohlcv)
        rsi_vals = rsi(series.closes, 14)
        atr_vals = atr(series.highs, series.lows, series.closes, 14)
        # closes/highs/lows extracted only once, not 3 times
    """

    __slots__ = ("_points", "__dict__")  # __dict__ needed for cached_property

    def __init__(self, points: list[OHLCVPoint]) -> None:
        self._points = points

    def __len__(self) -> int:
        return len(self._points)

    @cached_property
    def _columns(self) -> tuple[list[int], list[float], list[float], list[float], list[float], list[float]]:
        """Single-pass extraction of all 6 columns via attrgetter (C-implemented, ~25% faster)."""
        ts: list[int] = []
        o: list[float] = []
        h: list[float] = []
        lo: list[float] = []
        c: list[float] = []
        v: list[float] = []
        for point in self._points:
            t, op, hi, lw, cl, vo = _extract_ohlcv(point)
            ts.append(t)
            o.append(op)
            h.append(hi)
            lo.append(lw)
            c.append(cl)
            v.append(vo)
        return ts, o, h, lo, c, v

    @cached_property
    def times(self) -> list[int]:
        return self._columns[0]

    @cached_property
    def opens(self) -> list[float]:
        return self._columns[1]

    @cached_property
    def highs(self) -> list[float]:
        return self._columns[2]

    @cached_property
    def lows(self) -> list[float]:
        return self._columns[3]

    @cached_property
    def closes(self) -> list[float]:
        return self._columns[4]

    @cached_property
    def volumes(self) -> list[float]:
        return self._columns[5]

    @cached_property
    def polars_df(self) -> Any:
        """Polars DataFrame from cached columns. Returns None if polars unavailable."""
        if pl is None:
            return None
        ts, o, h, lo, c, v = self._columns
        return pl.DataFrame(
            {"time": ts, "open": o, "high": h, "low": lo, "close": c, "volume": v}
        )

    @property
    def points(self) -> list[OHLCVPoint]:
        return self._points


# ---------------------------------------------------------------------------
# Compute guards (standard patterns from nautilus-trader / pandas-ta)
# ---------------------------------------------------------------------------


def verify_series(values: list[float], min_length: int = 2, name: str = "series") -> None:
    """Guard: raise ValueError if series is too short for the requested computation."""
    if len(values) < min_length:
        msg = f"{name} requires at least {min_length} values, got {len(values)}"
        raise ValueError(msg)


def non_zero_range(high: float, low: float, eps: float = 1e-10) -> float:
    """Safe high-low range that never returns zero. Prevents division-by-zero in ATR/BB/Keltner."""
    return max(high - low, eps)


# ---------------------------------------------------------------------------
# Numeric utilities
# ---------------------------------------------------------------------------


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


# ---------------------------------------------------------------------------
# Simple extractors (backward compat with pipeline.py during migration)
# ---------------------------------------------------------------------------


def closes(points: list[OHLCVPoint]) -> list[float]:
    return [point.close for point in points]


def highs(points: list[OHLCVPoint]) -> list[float]:
    return [point.high for point in points]


def lows(points: list[OHLCVPoint]) -> list[float]:
    return [point.low for point in points]


def volumes(points: list[OHLCVPoint]) -> list[float]:
    return [point.volume for point in points]


def opens(points: list[OHLCVPoint]) -> list[float]:
    return [point.open for point in points]


def times_list(points: list[OHLCVPoint]) -> list[int]:
    return [point.time for point in points]


# ---------------------------------------------------------------------------
# Slope helper
# ---------------------------------------------------------------------------


def slope(values: list[float], period: int) -> list[float]:
    """Linear slope over `period` bars: (values[i] - values[i-period]) / period.

    Warm-up indices (i < period) emit 0.0.
    Used by Yellow, Green, and Blue Rainbow indicators (Kaabar 2026).
    """
    out: list[float] = []
    for i in range(len(values)):
        if i < period:
            out.append(0.0)
        else:
            out.append((values[i] - values[i - period]) / period)
    return out


# ---------------------------------------------------------------------------
# Polars integration (standalone — for use without OHLCVSeries)
# ---------------------------------------------------------------------------


def indicator_dataframe_status() -> dict[str, Any]:
    if pl is None:
        return {"available": False, "engine": None, "version": None, "error": "polars import failed"}
    return {
        "available": True,
        "engine": "polars",
        "version": getattr(pl, "__version__", None),
        "error": None,
    }


def ohlcv_polars_frame(points: list[OHLCVPoint]) -> Any:
    """Convert OHLCVPoint list to a Polars DataFrame. Returns None if polars unavailable."""
    return OHLCVSeries(points).polars_df


# ---------------------------------------------------------------------------
# Swing / Pivot detection (shared by oscillators + patterns)
# ---------------------------------------------------------------------------


def detect_swings(points: list[OHLCVPoint], window: int = 3) -> list["Pivot"]:
    """Detect swing highs/lows using a rolling window. Returns sorted, deduped pivots."""
    from indicator_engine.models import Pivot

    if len(points) < window * 2 + 1:
        return []
    output: list[Pivot] = []
    highs_data = highs(points)
    lows_data = lows(points)
    for i in range(window, len(points) - window):
        high_slice = highs_data[i - window : i + window + 1]
        low_slice = lows_data[i - window : i + window + 1]
        center_high = highs_data[i]
        center_low = lows_data[i]

        surrounding_highs = high_slice[:window] + high_slice[window + 1 :]
        surrounding_lows = low_slice[:window] + low_slice[window + 1 :]
        is_local_high = center_high == max(high_slice) and center_high > max(surrounding_highs)
        is_local_low = center_low == min(low_slice) and center_low < min(surrounding_lows)

        if is_local_high:
            output.append(Pivot(index=i, time=points[i].time, price=points[i].high, kind="high"))
        elif is_local_low:
            output.append(Pivot(index=i, time=points[i].time, price=points[i].low, kind="low"))

    # Boundary pivots (terminal-leg harmonic and top/bottom patterns)
    for i in (0, len(points) - 1):
        edge_start = max(0, i - window)
        edge_end = min(len(points), i + window + 1)
        high_slice = highs_data[edge_start:edge_end]
        low_slice = lows_data[edge_start:edge_end]
        center_high = highs_data[i]
        center_low = lows_data[i]
        center_pos = i - edge_start
        surrounding_highs = high_slice[:center_pos] + high_slice[center_pos + 1 :]
        surrounding_lows = low_slice[:center_pos] + low_slice[center_pos + 1 :]
        if not surrounding_highs or not surrounding_lows:
            continue

        is_edge_high = center_high == max(high_slice) and center_high > max(surrounding_highs)
        is_edge_low = center_low == min(low_slice) and center_low < min(surrounding_lows)
        if is_edge_high:
            output.append(Pivot(index=i, time=points[i].time, price=points[i].high, kind="high"))
        elif is_edge_low:
            output.append(Pivot(index=i, time=points[i].time, price=points[i].low, kind="low"))

    output.sort(key=lambda pivot: pivot.index)

    deduped: list[Pivot] = []
    for pivot in output:
        if not deduped:
            deduped.append(pivot)
            continue
        previous = deduped[-1]
        if previous.kind == pivot.kind:
            if (pivot.kind == "high" and pivot.price >= previous.price) or (
                pivot.kind == "low" and pivot.price <= previous.price
            ):
                deduped[-1] = pivot
            continue
        deduped.append(pivot)
    return deduped


def detect_close_turning_pivots(points: list[OHLCVPoint]) -> list["Pivot"]:
    """Close-based turning point detection (3-bar reversal). Used by TD timing patterns."""
    from indicator_engine.models import Pivot

    if len(points) < 3:
        return []

    output: list[Pivot] = []

    def _kind_at(i: int) -> str | None:
        if i <= 0 or i >= len(points) - 1:
            return None
        prev_close = points[i - 1].close
        cur_close = points[i].close
        next_close = points[i + 1].close
        if (cur_close >= prev_close and cur_close > next_close) or (
            cur_close > prev_close and cur_close >= next_close
        ):
            return "high"
        if (cur_close <= prev_close and cur_close < next_close) or (
            cur_close < prev_close and cur_close <= next_close
        ):
            return "low"
        return None

    for i in range(1, len(points) - 1):
        kind = _kind_at(i)
        if kind is None:
            continue
        price = points[i].high if kind == "high" else points[i].low
        output.append(Pivot(index=i, time=points[i].time, price=price, kind=kind))

    if len(points) >= 2:
        first_kind = "low" if points[0].close <= points[1].close else "high"
        first_price = points[0].low if first_kind == "low" else points[0].high
        output.insert(0, Pivot(index=0, time=points[0].time, price=first_price, kind=first_kind))

        last_kind = "high" if points[-1].close >= points[-2].close else "low"
        last_price = points[-1].high if last_kind == "high" else points[-1].low
        output.append(
            Pivot(index=len(points) - 1, time=points[-1].time, price=last_price, kind=last_kind)
        )

    deduped: list[Pivot] = []
    for pivot in output:
        if not deduped:
            deduped.append(pivot)
            continue
        previous = deduped[-1]
        if previous.kind == pivot.kind:
            if (pivot.kind == "high" and pivot.price >= previous.price) or (
                pivot.kind == "low" and pivot.price <= previous.price
            ):
                deduped[-1] = pivot
            continue
        deduped.append(pivot)
    return deduped


# ---------------------------------------------------------------------------
# Swarming — Multi-Chart-System Validation (Kaabar 2026, Kap. 4/9/11)
# ---------------------------------------------------------------------------


def swarm_validate(
    ohlcv: list[OHLCVPoint],
    pattern_fn: str,
    lookback: int = 250,
    threshold: float = 0.015,
) -> "SwarmValidationResponse":
    """Run pattern detection on Standard + Heikin-Ashi + K's CCS, return swarmed signals.

    Kaabar: "The interesting part is where you consider the signal only when it's
    visible across all three candlestick systems."

    pattern_fn: one of "candlestick", "timing", "price"
    Returns SwarmSignal entries with swarming_ratio (0.33, 0.67, 1.0).
    """
    from indicator_engine.models import (
        PatternRequest,
        SwarmSignal,
        SwarmValidationResponse,
    )
    from indicator_engine.patterns import (
        apply_chart_transform,
        build_candlestick_patterns,
        build_price_patterns,
        build_td_timing_patterns,
    )

    fn_map = {
        "candlestick": build_candlestick_patterns,
        "timing": build_td_timing_patterns,
        "price": build_price_patterns,
    }
    detect = fn_map.get(pattern_fn, build_td_timing_patterns)

    # 3 chart systems
    systems: list[tuple[str, list[OHLCVPoint]]] = [
        ("standard", ohlcv),
    ]
    # Heikin-Ashi transform
    ha_data = apply_chart_transform(ohlcv, "heikin_ashi")
    systems.append(("heikin_ashi", ha_data))
    # K's CCS transform
    k_data = apply_chart_transform(ohlcv, "k_candles")
    systems.append(("k_candles", k_data))

    # Run pattern detection on each system
    all_results: dict[str, list[dict[str, Any]]] = {}
    for sys_name, data in systems:
        req = PatternRequest(ohlcv=data, lookback=lookback, threshold=threshold)
        result = detect(req)
        for p in result.patterns:
            key = f"{p.type}_{p.direction}_{p.start_time}_{p.end_time}"
            if key not in all_results:
                all_results[key] = []
            all_results[key].append({"system": sys_name, "pattern": p})

    # Build swarmed signals
    signals: list[SwarmSignal] = []
    seen_keys: set[str] = set()
    for key, entries in all_results.items():
        if key in seen_keys:
            continue
        seen_keys.add(key)
        fired_on = [e["system"] for e in entries]
        ratio = len(fired_on) / 3.0
        p = entries[0]["pattern"]
        signals.append(SwarmSignal(
            type=p.type,
            direction=p.direction,
            start_time=p.start_time,
            end_time=p.end_time,
            swarming_ratio=round(ratio, 2),
            fired_on=fired_on,
            confidence=round(p.confidence * ratio, 4),
        ))

    # Sort by swarming_ratio descending (strongest signals first)
    signals.sort(key=lambda s: s.swarming_ratio, reverse=True)

    return SwarmValidationResponse(
        signals=signals,
        metadata={
            "pattern_type": pattern_fn,
            "systems": ["standard", "heikin_ashi", "k_candles"],
            "total_signals": len(signals),
            "fully_swarmed": sum(1 for s in signals if s.swarming_ratio >= 1.0),
        },
    )
