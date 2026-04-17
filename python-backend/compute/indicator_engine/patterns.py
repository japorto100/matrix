"""patterns.py — Pattern detection (chart patterns, candlestick, timing, fibonacci).

Extracted from pipeline.py (Phase A, 20.03.2026).

Functions:
  fibonacci_levels, build_fibonacci_levels, build_fibonacci_confluence,
  build_candlestick_patterns, build_harmonic_patterns,
  build_td_timing_patterns, build_price_patterns,
  build_elliott_wave_patterns, calculate_swing_points,
  apply_chart_transform, build_strategy_metrics
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from indicator_engine.helpers import (
    clamp,
    closes,
    detect_close_turning_pivots,
    detect_swings,
    highs,
    lows,
    volumes,
)
from indicator_engine.models import (
    ChartTransformRequest,
    ChartTransformResponse,
    ConfluenceZone,
    EvaluateStrategyRequest,
    FibonacciConfluenceRequest,
    FibonacciConfluenceResponse,
    FibonacciLevel,
    FibonacciResponse,
    OHLCVPoint,
    PatternData,
    PatternDirection,
    PatternRequest,
    PatternResponse,
    Pivot,
    StrategyEvaluationResponse,
    StrategyMetrics,
    SwingDetectRequest,
    SwingDetectResponse,
    SwingPoint,
    TDCountdownState,
)

# ---------------------------------------------------------------------------
# Pivot Points (Classic / Fibonacci / Camarilla)
# ---------------------------------------------------------------------------


def pivot_points_classic(
    prev_high: float,
    prev_low: float,
    prev_close: float,
) -> dict[str, float]:
    """Classic (Standard) Pivot Points from prior session H/L/C.

    Returns PP, R1-R3, S1-S3.
    """
    pp = (prev_high + prev_low + prev_close) / 3.0
    return {
        "pp": pp,
        "r1": 2 * pp - prev_low,
        "r2": pp + (prev_high - prev_low),
        "r3": prev_high + 2 * (pp - prev_low),
        "s1": 2 * pp - prev_high,
        "s2": pp - (prev_high - prev_low),
        "s3": prev_low - 2 * (prev_high - pp),
    }


def pivot_points_fibonacci(
    prev_high: float,
    prev_low: float,
    prev_close: float,
) -> dict[str, float]:
    """Fibonacci Pivot Points — PP + Fib retracements of prior range."""
    pp = (prev_high + prev_low + prev_close) / 3.0
    r = prev_high - prev_low
    return {
        "pp": pp,
        "r1": pp + 0.382 * r,
        "r2": pp + 0.618 * r,
        "r3": pp + 1.000 * r,
        "s1": pp - 0.382 * r,
        "s2": pp - 0.618 * r,
        "s3": pp - 1.000 * r,
    }


def pivot_points_camarilla(
    prev_high: float,
    prev_low: float,
    prev_close: float,
) -> dict[str, float]:
    """Camarilla Pivot Points — Close-anchored with 1.1/N multipliers (Nick Scott, 1989)."""
    r = prev_high - prev_low
    return {
        "pp": (prev_high + prev_low + prev_close) / 3.0,
        "h1": prev_close + r * 1.1 / 12,
        "h2": prev_close + r * 1.1 / 6,
        "h3": prev_close + r * 1.1 / 4,
        "h4": prev_close + r * 1.1 / 2,
        "l1": prev_close - r * 1.1 / 12,
        "l2": prev_close - r * 1.1 / 6,
        "l3": prev_close - r * 1.1 / 4,
        "l4": prev_close - r * 1.1 / 2,
    }


def pivot_points(
    prev_high: float,
    prev_low: float,
    prev_close: float,
    variant: str = "classic",
) -> dict[str, float]:
    """Unified Pivot Points — dispatches to classic/fibonacci/camarilla."""
    if variant == "fibonacci":
        return pivot_points_fibonacci(prev_high, prev_low, prev_close)
    if variant == "camarilla":
        return pivot_points_camarilla(prev_high, prev_low, prev_close)
    return pivot_points_classic(prev_high, prev_low, prev_close)


# ---------------------------------------------------------------------------
# ZigZag
# ---------------------------------------------------------------------------


def zigzag(
    high: list[float],
    low: list[float],
    deviation: float = 5.0,
) -> list[dict]:
    """ZigZag — percentage-based reversal detection (TradingView standard).

    Connects significant turning points where price reverses by at least `deviation`%.
    Returns list of pivot dicts: {index, price, type: "high"|"low"}.

    Default: deviation=5.0 (5%).
    Note: the last pivot is tentative and may change as new bars arrive (non-causal).
    """
    n = len(high)
    if n < 2:
        return []

    threshold = deviation / 100.0
    pivots: list[dict] = []

    last_type = "high"
    last_price = high[0]
    last_idx = 0

    # Determine initial direction from first bar
    if low[0] < high[0]:
        # Check if the initial move looks more bearish
        pass  # default to tracking high first

    for i in range(1, n):
        if last_type == "high":
            if high[i] > last_price:
                # Extend the current high
                last_price = high[i]
                last_idx = i
            elif low[i] < last_price * (1 - threshold):
                # Reversal confirmed — emit the high pivot
                pivots.append({"index": last_idx, "price": last_price, "type": "high"})
                last_type = "low"
                last_price = low[i]
                last_idx = i
        else:  # last_type == "low"
            if low[i] < last_price:
                # Extend the current low
                last_price = low[i]
                last_idx = i
            elif high[i] > last_price * (1 + threshold):
                # Reversal confirmed — emit the low pivot
                pivots.append({"index": last_idx, "price": last_price, "type": "low"})
                last_type = "high"
                last_price = high[i]
                last_idx = i

    # Emit last tentative pivot
    pivots.append({"index": last_idx, "price": last_price, "type": last_type})
    return pivots


# ---------------------------------------------------------------------------
# Market Structure (HH / HL / LH / LL)
# ---------------------------------------------------------------------------


def detect_swing_points(
    high: list[float],
    low: list[float],
    lookback: int = 2,
) -> list[dict]:
    """Detect confirmed swing highs and lows using N-bar lookback/lookahead.

    A bar at index i is a swing high if high[i] >= max(high[i-N..i+N]).
    A bar at index i is a swing low if low[i] <= min(low[i-N..i+N]).
    TradingView default: lookback=2 (5-bar window).

    Returns list of {index, price, type: "high"|"low"}, sorted by index.
    """
    n = len(high)
    swings: list[dict] = []

    for i in range(lookback, n - lookback):
        # Check swing high
        is_sh = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and high[j] > high[i]:
                is_sh = False
                break
        if is_sh:
            swings.append({"index": i, "price": high[i], "type": "high"})

        # Check swing low
        is_sl = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and low[j] < low[i]:
                is_sl = False
                break
        if is_sl:
            swings.append({"index": i, "price": low[i], "type": "low"})

    swings.sort(key=lambda s: s["index"])
    return swings


def market_structure(
    high: list[float],
    low: list[float],
    lookback: int = 2,
) -> list[dict]:
    """Market Structure — label swing points as HH/HL/LH/LL.

    Uses N-bar confirmed swing detection, then classifies each pivot relative
    to the prior pivot of the same type.

    Returns list of {index, price, type, label} where label is one of:
        HH (Higher High), LH (Lower High), EH (Equal High),
        HL (Higher Low), LL (Lower Low), EL (Equal Low),
        SH (first swing high), SL (first swing low).
    """
    swings = detect_swing_points(high, low, lookback)

    last_sh: float | None = None
    last_sl: float | None = None
    labeled: list[dict] = []

    for s in swings:
        if s["type"] == "high":
            if last_sh is None:
                label = "SH"
            elif s["price"] > last_sh:
                label = "HH"
            elif s["price"] < last_sh:
                label = "LH"
            else:
                label = "EH"
            last_sh = s["price"]
            labeled.append({**s, "label": label})
        else:
            if last_sl is None:
                label = "SL"
            elif s["price"] > last_sl:
                label = "HL"
            elif s["price"] < last_sl:
                label = "LL"
            else:
                label = "EL"
            last_sl = s["price"]
            labeled.append({**s, "label": label})

    return labeled


def market_structure_trend(labels: list[dict]) -> str:
    """Determine trend from market structure labels.

    Returns "bullish" (HH+HL), "bearish" (LH+LL), or "ranging".
    """
    if len(labels) < 2:
        return "ranging"

    last_high_label = None
    last_low_label = None
    for lb in reversed(labels):
        if lb["type"] == "high" and last_high_label is None:
            last_high_label = lb["label"]
        elif lb["type"] == "low" and last_low_label is None:
            last_low_label = lb["label"]
        if last_high_label and last_low_label:
            break

    if last_high_label == "HH" and last_low_label == "HL":
        return "bullish"
    if last_high_label == "LH" and last_low_label == "LL":
        return "bearish"
    return "ranging"


# ---------------------------------------------------------------------------
# Fibonacci Levels
# ---------------------------------------------------------------------------


def fibonacci_levels(points: list[OHLCVPoint]) -> FibonacciResponse:
    """Compute Fibonacci retracement levels from the last two swing pivots."""
    pivots = detect_swings(points, window=4)
    if len(pivots) < 2:
        low = min(points, key=lambda item: item.low)
        high = max(points, key=lambda item: item.high)
        start = Pivot(0, low.time, low.low, "low")
        end = Pivot(len(points) - 1, high.time, high.high, "high")
    else:
        start = pivots[-2]
        end = pivots[-1]

    anchor_low = min(start.price, end.price)
    anchor_high = max(start.price, end.price)
    span = anchor_high - anchor_low
    ratios = [0.236, 0.382, 0.5, 0.618, 0.786, 0.886, 1.0, 1.13, 1.272, 1.618, 2.0, 2.24, 2.618]
    levels = [FibonacciLevel(ratio=ratio, price=anchor_high - span * ratio) for ratio in ratios]
    return FibonacciResponse(
        swing={
            "start_time": start.time,
            "end_time": end.time,
            "start_price": start.price,
            "end_price": end.price,
        },
        levels=levels,
    )


def build_fibonacci_levels(payload: PatternRequest) -> FibonacciResponse:
    """Fibonacci levels endpoint — delegates to fibonacci_levels."""
    return fibonacci_levels(payload.ohlcv[-payload.lookback :])


def build_fibonacci_confluence(payload: FibonacciConfluenceRequest) -> FibonacciConfluenceResponse:
    """Detect Fibonacci level clusters across multiple swing pairs."""
    pivots = detect_swings(payload.ohlcv, window=4)
    ratios = [0.236, 0.382, 0.5, 0.618, 0.786, 0.886, 1.0, 1.13, 1.272, 1.618, 2.0, 2.24, 2.618]
    all_levels: list[FibonacciLevel] = []
    num_pairs = min(payload.numSwings, max(0, len(pivots) - 1))
    start_idx = max(0, len(pivots) - 1 - num_pairs)
    for i in range(start_idx, len(pivots) - 1):
        anchor_low = min(pivots[i].price, pivots[i + 1].price)
        anchor_high = max(pivots[i].price, pivots[i + 1].price)
        span = anchor_high - anchor_low
        for ratio in ratios:
            all_levels.append(FibonacciLevel(ratio=ratio, price=anchor_high - span * ratio))
    if not all_levels:
        return FibonacciConfluenceResponse(
            zones=[],
            metadata={"numSwings": payload.numSwings, "thresholdPct": payload.thresholdPct, "totalLevels": 0},
        )
    sorted_levels = sorted(all_levels, key=lambda lv: lv.price)
    zones: list[ConfluenceZone] = []
    i = 0
    while i < len(sorted_levels):
        cluster = [sorted_levels[i]]
        ref_price = sorted_levels[i].price
        j = i + 1
        while j < len(sorted_levels):
            price_diff = abs(sorted_levels[j].price - ref_price)
            if price_diff / max(abs(ref_price), 1e-9) <= payload.thresholdPct:
                cluster.append(sorted_levels[j])
                j += 1
            else:
                break
        if len(cluster) >= 2:
            center = mean([lv.price for lv in cluster])
            low_price = min(lv.price for lv in cluster)
            high_price = max(lv.price for lv in cluster)
            zones.append(
                ConfluenceZone(
                    priceCenter=center,
                    priceRange=(low_price, high_price),
                    levels=cluster,
                    strength=len(cluster),
                )
            )
        i = j if j > i + 1 else i + 1
    zones.sort(key=lambda z: z.strength, reverse=True)
    return FibonacciConfluenceResponse(
        zones=zones,
        metadata={
            "numSwings": payload.numSwings,
            "thresholdPct": payload.thresholdPct,
            "totalLevels": len(all_levels),
        },
    )


# ---------------------------------------------------------------------------
# Candlestick Patterns
# ---------------------------------------------------------------------------


def build_candlestick_patterns(payload: PatternRequest) -> PatternResponse:
    """Detect candlestick patterns (single, two-bar, three-bar)."""
    points = payload.ohlcv[-payload.lookback :]
    patterns: list[PatternData] = []

    # Single- and two-bar patterns
    for i in range(1, len(points)):
        current = points[i]
        previous = points[i - 1]
        body = abs(current.close - current.open)
        range_size = max(1e-9, current.high - current.low)
        upper_wick = current.high - max(current.open, current.close)
        lower_wick = min(current.open, current.close) - current.low
        body_ratio = body / range_size

        # Doji variants
        if body_ratio <= 0.15:
            if lower_wick > 2 * body and upper_wick < 0.1 * range_size:
                patterns.append(PatternData(
                    type="dragonfly_doji", direction="bullish",
                    start_time=current.time, end_time=current.time, confidence=0.65,
                    details={"body_ratio": round(body_ratio, 4)},
                ))
            elif upper_wick > 2 * body and lower_wick < 0.1 * range_size:
                patterns.append(PatternData(
                    type="gravestone_doji", direction="bearish",
                    start_time=current.time, end_time=current.time, confidence=0.65,
                    details={"body_ratio": round(body_ratio, 4)},
                ))
            else:
                patterns.append(PatternData(
                    type="doji", direction="neutral",
                    start_time=current.time, end_time=current.time, confidence=0.64,
                    details={"body_ratio": round(body_ratio, 4)},
                ))

        # Spinning Top
        if 0.15 < body_ratio <= 0.40 and lower_wick > 0.2 * range_size and upper_wick > 0.2 * range_size:
            patterns.append(PatternData(
                type="spinning_top", direction="neutral",
                start_time=current.time, end_time=current.time, confidence=0.50,
                details={"body_ratio": round(body_ratio, 4)},
            ))

        # Bullish/Bearish Engulfing
        if current.close > current.open and previous.close < previous.open:
            if current.close >= previous.open and current.open <= previous.close:
                patterns.append(PatternData(
                    type="bullish_engulfing", direction="bullish",
                    start_time=previous.time, end_time=current.time, confidence=0.69,
                ))
        if current.close < current.open and previous.close > previous.open:
            if current.open >= previous.close and current.close <= previous.open:
                patterns.append(PatternData(
                    type="bearish_engulfing", direction="bearish",
                    start_time=previous.time, end_time=current.time, confidence=0.69,
                ))

        # Hammer / Shooting Star
        if lower_wick > body * 2.0 and current.close > current.open:
            patterns.append(PatternData(
                type="hammer", direction="bullish",
                start_time=current.time, end_time=current.time, confidence=0.62,
            ))
        if upper_wick > body * 2.0 and current.close < current.open:
            patterns.append(PatternData(
                type="shooting_star", direction="bearish",
                start_time=current.time, end_time=current.time, confidence=0.62,
            ))

        # Piercing Line
        prev_bearish = previous.close < previous.open
        cur_bullish = current.close > current.open
        if prev_bearish and cur_bullish:
            prev_mid = (previous.open + previous.close) / 2.0
            if current.open < previous.low and current.close > prev_mid:
                patterns.append(PatternData(
                    type="piercing_line", direction="bullish",
                    start_time=previous.time, end_time=current.time, confidence=0.67,
                ))

        # Dark Cloud Cover
        prev_bullish = previous.close > previous.open
        cur_bearish = current.close < current.open
        if prev_bullish and cur_bearish:
            prev_mid = (previous.open + previous.close) / 2.0
            if current.open > previous.high and current.close < prev_mid:
                patterns.append(PatternData(
                    type="dark_cloud_cover", direction="bearish",
                    start_time=previous.time, end_time=current.time, confidence=0.67,
                ))

    # Three-bar patterns
    for i in range(2, len(points)):
        b0, b1, b2 = points[i - 2], points[i - 1], points[i]

        def _body(bar: OHLCVPoint) -> float:
            return abs(bar.close - bar.open)

        def _range(bar: OHLCVPoint) -> float:
            return max(1e-9, bar.high - bar.low)

        b0_bear = b0.close < b0.open
        b2_bull = b2.close > b2.open
        b0_bull = b0.close > b0.open
        b2_bear = b2.close < b2.open

        # Morning Star
        b1_small = _body(b1) <= 0.3 * _range(b1)
        b0_mid = (b0.open + b0.close) / 2.0
        if (b0_bear and _body(b0) >= 0.5 * _range(b0)
                and b1_small and b2_bull
                and b2.close > b0_mid):
            patterns.append(PatternData(
                type="morning_star", direction="bullish",
                start_time=b0.time, end_time=b2.time, confidence=0.75,
            ))

        # Evening Star
        if (b0_bull and _body(b0) >= 0.5 * _range(b0)
                and b1_small and b2_bear
                and b2.close < b0_mid):
            patterns.append(PatternData(
                type="evening_star", direction="bearish",
                start_time=b0.time, end_time=b2.time, confidence=0.75,
            ))

        # Three White Soldiers
        if (b0_bull and b1.close > b1.open and b2_bull
                and b1.close > b0.close and b2.close > b1.close
                and b1.open > b0.open and b2.open > b1.open
                and b2.close >= b2.open + 0.7 * _body(b2)):
            patterns.append(PatternData(
                type="three_white_soldiers", direction="bullish",
                start_time=b0.time, end_time=b2.time, confidence=0.72,
            ))

        # Three Black Crows
        if (b0_bear and b1.close < b1.open and b2_bear
                and b1.close < b0.close and b2.close < b1.close
                and b1.open < b0.open and b2.open < b1.open
                and b2.close <= b2.open - 0.7 * _body(b2)):
            patterns.append(PatternData(
                type="three_black_crows", direction="bearish",
                start_time=b0.time, end_time=b2.time, confidence=0.72,
            ))

        # Bottle — Kaabar Ch.7: 2-bar momentum continuation.
        # Bullish: both bars bullish, bar[i] opens == low (no lower wick), gap lower
        # Bearish: both bars bearish, bar[i] opens == high (no upper wick), gap higher
        wick_tol = 0.02 * _range(b2)  # tolerance for "no wick"
        b1_bull = b1.close > b1.open
        b1_bear_flag = b1.close < b1.open
        b2_bull_flag = b2.close > b2.open
        b2_bear_flag = b2.close < b2.open
        if b1_bull and b2_bull_flag:
            no_lower_wick = (b2.open - b2.low) <= wick_tol
            gap_lower = b2.open < b1.close
            if no_lower_wick and gap_lower:
                patterns.append(PatternData(
                    type="bottle", direction="bullish",
                    start_time=b1.time, end_time=b2.time, confidence=0.62,
                ))
        if b1_bear_flag and b2_bear_flag:
            no_upper_wick = (b2.high - b2.open) <= wick_tol
            gap_higher = b2.open > b1.close
            if no_upper_wick and gap_higher:
                patterns.append(PatternData(
                    type="bottle", direction="bearish",
                    start_time=b1.time, end_time=b2.time, confidence=0.62,
                ))

    # Double Trouble — Kaabar Ch.7: ATR-filtered 2-bar momentum continuation.
    # Bullish: 2 consecutive bullish bars, close[i] > close[i-1], body[i] > 2×ATR[i-1]
    # Bearish: mirror.
    from indicator_engine.volatility import calculate_atr as _calc_atr

    atr_values = _calc_atr(points, 14)
    for i in range(1, len(points)):
        cur, prev = points[i], points[i - 1]
        cur_body = abs(cur.close - cur.open)
        prev_atr = atr_values[i - 1] if i - 1 < len(atr_values) else 0.0
        if prev_atr <= 0:
            continue
        if (cur.close > cur.open and prev.close > prev.open
                and cur.close > prev.close and cur_body > 2 * prev_atr):
            patterns.append(PatternData(
                type="double_trouble", direction="bullish",
                start_time=prev.time, end_time=cur.time, confidence=0.68,
                details={"body_atr_ratio": round(cur_body / prev_atr, 2)},
            ))
        elif (cur.close < cur.open and prev.close < prev.open
                and cur.close < prev.close and cur_body > 2 * prev_atr):
            patterns.append(PatternData(
                type="double_trouble", direction="bearish",
                start_time=prev.time, end_time=cur.time, confidence=0.68,
                details={"body_atr_ratio": round(cur_body / prev_atr, 2)},
            ))

    # Extreme Euphoria — Kaabar Ch.7: 5-bar exhaustion reversal.
    # Bullish: 5 consecutive bearish bars + body[i] > body[i-1] > body[i-2]
    # Bearish: 5 consecutive bullish bars + same increasing body condition.
    if len(points) >= 5:
        for i in range(4, len(points)):
            window = points[i - 4: i + 1]
            bodies = [abs(b.close - b.open) for b in window]
            all_bearish = all(b.close < b.open for b in window)
            all_bullish = all(b.close > b.open for b in window)
            increasing = bodies[4] > bodies[3] > bodies[2]
            if all_bearish and increasing:
                patterns.append(PatternData(
                    type="extreme_euphoria", direction="bullish",
                    start_time=window[0].time, end_time=window[4].time, confidence=0.63,
                    details={"last_3_bodies": [round(b, 4) for b in bodies[2:]]},
                ))
            elif all_bullish and increasing:
                patterns.append(PatternData(
                    type="extreme_euphoria", direction="bearish",
                    start_time=window[0].time, end_time=window[4].time, confidence=0.63,
                    details={"last_3_bodies": [round(b, 4) for b in bodies[2:]]},
                ))

    # R Pattern — Kaabar Ch.7: 4-bar RSI-filtered reversal.
    # Bullish: V-shape in lows + 4 rising closes + RSI(14) < 50
    # Bearish: inverse V in highs + 4 falling closes + RSI(14) > 50
    from indicator_engine.oscillators import rsi as _rsi

    rsi_values = _rsi(closes(points), 14)
    for i in range(3, len(points)):
        p0, p1, p2, p3 = points[i - 3], points[i - 2], points[i - 1], points[i]
        rsi_val = rsi_values[i]
        # Bullish R: V-shape lows, rising closes, RSI < 50
        v_lows = p1.low < p0.low and p2.low > p1.low and p3.low > p2.low
        rising_closes = p1.close > p0.close and p2.close > p1.close and p3.close > p2.close
        if v_lows and rising_closes and rsi_val < 50:
            patterns.append(PatternData(
                type="r_pattern", direction="bullish",
                start_time=p0.time, end_time=p3.time, confidence=0.70,
                details={"rsi": round(rsi_val, 2)},
            ))
        # Bearish R: inverse V highs, falling closes, RSI > 50
        v_highs = p1.high > p0.high and p2.high < p1.high and p3.high < p2.high
        falling_closes = p1.close < p0.close and p2.close < p1.close and p3.close < p2.close
        if v_highs and falling_closes and rsi_val > 50:
            patterns.append(PatternData(
                type="r_pattern", direction="bearish",
                start_time=p0.time, end_time=p3.time, confidence=0.70,
                details={"rsi": round(rsi_val, 2)},
            ))

    # Hidden Shovel — Kaabar Ch.7 CARSI pattern.
    # Bullish: RSI_low < 30, all other RSI > 30, previous RSI_low > 30
    # Bearish: RSI_high > 70, all other RSI < 70, previous RSI_high < 70
    rsi_open = _rsi([p.open for p in points], 14)
    rsi_high = _rsi([p.high for p in points], 14)
    rsi_low = _rsi([p.low for p in points], 14)
    rsi_close = _rsi(closes(points), 14)
    for i in range(1, len(points)):
        ro, rh, rl, rc = rsi_open[i], rsi_high[i], rsi_low[i], rsi_close[i]
        rl_prev = rsi_low[i - 1]
        rh_prev = rsi_high[i - 1]
        # Bullish Hidden Shovel
        if rl < 30 and ro > 30 and rh > 30 and rc > 30 and rl_prev > 30:
            patterns.append(PatternData(
                type="hidden_shovel", direction="bullish",
                start_time=points[i - 1].time, end_time=points[i].time, confidence=0.66,
                details={"rsi_low": round(rl, 2), "rsi_close": round(rc, 2)},
            ))
        # Bearish Hidden Shovel
        if rh > 70 and ro < 70 and rl < 70 and rc < 70 and rh_prev < 70:
            patterns.append(PatternData(
                type="hidden_shovel", direction="bearish",
                start_time=points[i - 1].time, end_time=points[i].time, confidence=0.66,
                details={"rsi_high": round(rh, 2), "rsi_close": round(rc, 2)},
            ))

    # Absolute U-Turn — Kaabar Ch.7 CARSI pattern.
    # Bullish: RSI_low[i] > 20, previous 5 RSI_low all < 20
    # Bearish: RSI_high[i] < 80, previous 5 RSI_high all > 80
    for i in range(5, len(points)):
        if rsi_low[i] > 20 and all(rsi_low[i - k] < 20 for k in range(1, 6)):
            patterns.append(PatternData(
                type="absolute_u_turn", direction="bullish",
                start_time=points[i - 5].time, end_time=points[i].time, confidence=0.72,
                details={"rsi_low_current": round(rsi_low[i], 2)},
            ))
        if rsi_high[i] < 80 and all(rsi_high[i - k] > 80 for k in range(1, 6)):
            patterns.append(PatternData(
                type="absolute_u_turn", direction="bearish",
                start_time=points[i - 5].time, end_time=points[i].time, confidence=0.72,
                details={"rsi_high_current": round(rsi_high[i], 2)},
            ))

    return PatternResponse(
        patterns=patterns[:50],
        metadata={"scanned_bars": len(points), "patterns_found": len(patterns)},
    )


# ---------------------------------------------------------------------------
# Harmonic Patterns
# ---------------------------------------------------------------------------


def build_harmonic_patterns(payload: PatternRequest) -> PatternResponse:
    """XABCD harmonic patterns (Gartley/Bat/Butterfly/Crab) + FEIW + legacy ABCD."""
    from indicator_engine.volatility import calculate_atr as _calc_atr

    points = payload.ohlcv[-payload.lookback :]
    pivots = detect_swings(points, window=2)
    if len(pivots) < 5:
        pivots = detect_close_turning_pivots(points)
    patterns: list[PatternData] = []
    tol = 0.05

    # ATR for risk management (stop-loss calculation)
    atr_values = _calc_atr(points, 14)
    last_atr = atr_values[-1] if atr_values else 0.0

    def _in_range(v: float, lo: float, hi: float) -> bool:
        return lo - tol <= v <= hi + tol

    def _risk_mgmt(a_price: float, d_price: float, is_bearish: bool) -> dict[str, float]:
        """Kaabar Ch.8: Fib targets from AD leg + ATR stop beyond D."""
        ad = abs(d_price - a_price)
        if is_bearish:
            # Bearish: expect price to fall from D
            t1 = d_price - ad * 0.382
            t2 = d_price - ad * 0.618
            stop = d_price + 2 * last_atr
        else:
            # Bullish: expect price to rise from D
            t1 = d_price + ad * 0.382
            t2 = d_price + ad * 0.618
            stop = d_price - 2 * last_atr
        return {
            "target_1": round(t1, 4),
            "target_2": round(t2, 4),
            "stop_loss": round(stop, 4),
        }

    # XABCD patterns (5 pivots)
    if len(pivots) >= 5:
        for idx in range(len(pivots) - 4):
            x, a, b, c, d = pivots[idx], pivots[idx + 1], pivots[idx + 2], pivots[idx + 3], pivots[idx + 4]
            xa = abs(a.price - x.price)
            ab = abs(b.price - a.price)
            bc = abs(c.price - b.price)
            cd = abs(d.price - c.price)
            if xa < 1e-9 or ab < 1e-9 or bc < 1e-9:
                continue
            ab_xa = ab / xa
            bc_ab = bc / ab
            cd_bc = cd / bc
            ad_xa = abs(d.price - a.price) / xa
            bearish_d = d.kind == "high"
            direction: PatternDirection = "bearish" if bearish_d else "bullish"
            inv_factor = 1.01 if bearish_d else 0.99
            rm = _risk_mgmt(a.price, d.price, bearish_d)

            # Gartley: AD/XA ≈ 0.786, D stays within X→A range
            if (_in_range(ab_xa, 0.618, 0.618)
                    and _in_range(bc_ab, 0.382, 0.886)
                    and _in_range(cd_bc, 1.272, 1.618)
                    and _in_range(ad_xa, 0.786, 0.786)):
                patterns.append(PatternData(
                    type="gartley", direction=direction, start_time=x.time, end_time=d.time,
                    confidence=0.78,
                    details={"xa_b": round(ab_xa, 4), "bc": round(bc_ab, 4),
                             "cd_bc": round(cd_bc, 4), "d_xa": round(ad_xa, 4),
                             "invalidation_level": round(d.price * inv_factor, 4), **rm},
                ))

            # Bat: AD/XA ≈ 0.886
            if (_in_range(ab_xa, 0.382, 0.50)
                    and _in_range(bc_ab, 0.382, 0.886)
                    and _in_range(cd_bc, 1.618, 2.618)
                    and _in_range(ad_xa, 0.886, 0.886)):
                patterns.append(PatternData(
                    type="bat", direction=direction, start_time=x.time, end_time=d.time,
                    confidence=0.76,
                    details={"xa_b": round(ab_xa, 4), "bc": round(bc_ab, 4),
                             "cd_bc": round(cd_bc, 4), "d_xa": round(ad_xa, 4),
                             "invalidation_level": round(d.price * inv_factor, 4), **rm},
                ))

            if (_in_range(ab_xa, 0.786, 0.786) and _in_range(bc_ab, 0.382, 0.886)
                    and _in_range(cd_bc, 1.618, 2.618) and _in_range(ad_xa, 1.272, 1.618)):
                patterns.append(PatternData(
                    type="butterfly", direction=direction, start_time=x.time, end_time=d.time,
                    confidence=0.74,
                    details={"xa_b": round(ab_xa, 4), "bc": round(bc_ab, 4),
                             "cd_bc": round(cd_bc, 4), "d_xa": round(ad_xa, 4),
                             "invalidation_level": round(d.price * inv_factor, 4), **rm},
                ))

            if (_in_range(ab_xa, 0.382, 0.618) and _in_range(bc_ab, 0.382, 0.886)
                    and _in_range(cd_bc, 2.24, 3.618) and _in_range(ad_xa, 1.618, 1.618)):
                patterns.append(PatternData(
                    type="crab", direction=direction, start_time=x.time, end_time=d.time,
                    confidence=0.72,
                    details={"xa_b": round(ab_xa, 4), "bc": round(bc_ab, 4),
                             "cd_bc": round(cd_bc, 4), "d_xa": round(ad_xa, 4),
                             "invalidation_level": round(d.price * inv_factor, 4), **rm},
                ))

    # FEIW: failed breakout/breakdown (3 pivots) — Kaabar Ch.8: with Fib-ratio validation
    _fib_targets = [0.382, 0.5, 0.618, 0.786, 0.886, 1.0, 1.272, 1.618]
    if len(pivots) >= 3 and len(points) >= 2:
        last_close = points[-1].close
        for idx in range(len(pivots) - 2):
            p1, p2, p3 = pivots[idx], pivots[idx + 1], pivots[idx + 2]
            ab = abs(p2.price - p1.price)
            ac = abs(p3.price - p1.price)
            ac_ab = ac / ab if ab > 1e-9 else 0.0
            # Fib-ratio quality: closest match to known ratio
            fib_dist = min(abs(ac_ab - f) for f in _fib_targets) if ac_ab > 0 else 1.0
            if fib_dist > 0.10:
                continue  # skip if AC/AB doesn't match any Fib ratio within 10%
            if p1.kind == "high" and p3.kind == "high" and p3.price > p1.price and last_close < p1.price:
                patterns.append(PatternData(
                    type="feiw_failed_breakout", direction="bearish",
                    start_time=p1.time, end_time=p3.time, confidence=0.65,
                    details={"prior_extreme": round(p1.price, 4), "breakout_level": round(p3.price, 4),
                             "ac_ab_ratio": round(ac_ab, 4)},
                ))
                break
            if p1.kind == "low" and p3.kind == "low" and p3.price < p1.price and last_close > p1.price:
                patterns.append(PatternData(
                    type="feiw_failed_breakdown", direction="bullish",
                    start_time=p1.time, end_time=p3.time, confidence=0.65,
                    details={"prior_extreme": round(p1.price, 4), "breakdown_level": round(p3.price, 4),
                             "ac_ab_ratio": round(ac_ab, 4)},
                ))
                break

    # Legacy ABCD (4-pivot)
    if len(pivots) >= 4:
        a, b, c, d = pivots[-4], pivots[-3], pivots[-2], pivots[-1]
        ab = abs(b.price - a.price)
        bc = abs(c.price - b.price)
        cd = abs(d.price - c.price)
        if ab > 0 and bc > 0:
            ratio_bc_ab = bc / ab
            ratio_cd_bc = cd / bc
            if 0.55 <= ratio_bc_ab <= 0.78 and 1.13 <= ratio_cd_bc <= 1.9:
                is_bear = d.kind == "high"
                ad_dist = abs(d.price - a.price)
                # Kaabar Ch.8: projected D via AB=CD symmetry from C
                projected_d = c.price - ab if d.kind == "low" else c.price + ab
                # Risk management: Fib targets from A→D + ATR stop
                t1 = d.price + ad_dist * 0.382 if not is_bear else d.price - ad_dist * 0.382
                t2 = d.price + ad_dist * 0.618 if not is_bear else d.price - ad_dist * 0.618
                patterns.append(PatternData(
                    type="abcd",
                    direction="bearish" if is_bear else "bullish",
                    start_time=a.time, end_time=d.time, confidence=0.74,
                    details={"bc_ab": round(ratio_bc_ab, 4), "cd_bc": round(ratio_cd_bc, 4),
                             "fibonacci_valid": True,
                             "projected_d": round(projected_d, 4),
                             "target_1": round(t1, 4), "target_2": round(t2, 4)},
                ))

    return PatternResponse(
        patterns=patterns[:30],
        metadata={"scanned_bars": len(points), "patterns_found": len(patterns)},
    )


# ---------------------------------------------------------------------------
# TD Timing Patterns (Tom DeMark)
# ---------------------------------------------------------------------------


def build_td_timing_patterns(payload: PatternRequest) -> PatternResponse:
    """TD Setup 9 + TDST levels + TD Countdown 13."""
    points = payload.ohlcv[-payload.lookback :]
    closes_data = closes(points)
    lows_data = lows(points)
    highs_data = highs(points)
    bullish_count = 0
    bearish_count = 0
    patterns: list[PatternData] = []

    active_countdowns: list[TDCountdownState] = []

    for i in range(4, len(points)):
        # Kaabar Ch.9: falling closes = exhaustion = BULLISH reversal expected
        # rising closes = exhaustion = BEARISH reversal expected
        if closes_data[i] < closes_data[i - 4]:
            bullish_count += 1
            bearish_count = 0
        elif closes_data[i] > closes_data[i - 4]:
            bearish_count += 1
            bullish_count = 0
        else:
            bullish_count = 0
            bearish_count = 0

        # TD Setup 9 + TDST + Perfection check (Kaabar Ch.9/12)
        if bullish_count == 9:
            setup_start = i - 8
            tdst_level = min(closes_data[setup_start : i + 1])
            # Perfected Bullish: Low of bar 8 or 9 < Low of bar 6 AND bar 7
            b6_low = lows_data[setup_start + 5]
            b7_low = lows_data[setup_start + 6]
            b8_low = lows_data[setup_start + 7]
            b9_low = lows_data[i]
            perfected = (b8_low < b6_low and b8_low < b7_low) or (b9_low < b6_low and b9_low < b7_low)
            ptype = "td_setup_9_bullish_perfected" if perfected else "td_setup_9_bullish"
            patterns.append(PatternData(
                type=ptype, direction="bullish",
                start_time=points[setup_start].time, end_time=points[i].time,
                confidence=0.80 if perfected else 0.73,
                details={"perfected": perfected},
            ))
            patterns.append(PatternData(
                type="tdst_level", direction="bullish",
                start_time=points[setup_start].time, end_time=points[i].time, confidence=0.70,
                details={"level": round(tdst_level, 4), "kind": "support"},
            ))
            active_countdowns.append({
                "kind": "bullish", "start_idx": i, "tdst": tdst_level, "count": 0,
            })
            bullish_count = 0

        if bearish_count == 9:
            setup_start = i - 8
            tdst_level = max(closes_data[setup_start : i + 1])
            # Perfected Bearish: High of bar 8 or 9 > High of bar 6 AND bar 7
            b6_high = highs_data[setup_start + 5]
            b7_high = highs_data[setup_start + 6]
            b8_high = highs_data[setup_start + 7]
            b9_high = highs_data[i]
            perfected = (b8_high > b6_high and b8_high > b7_high) or (b9_high > b6_high and b9_high > b7_high)
            ptype = "td_setup_9_bearish_perfected" if perfected else "td_setup_9_bearish"
            patterns.append(PatternData(
                type=ptype, direction="bearish",
                start_time=points[setup_start].time, end_time=points[i].time,
                confidence=0.80 if perfected else 0.73,
                details={"perfected": perfected},
            ))
            patterns.append(PatternData(
                type="tdst_level", direction="bearish",
                start_time=points[setup_start].time, end_time=points[i].time, confidence=0.70,
                details={"level": round(tdst_level, 4), "kind": "resistance"},
            ))
            active_countdowns.append({
                "kind": "bearish", "start_idx": i, "tdst": tdst_level, "count": 0,
            })
            bearish_count = 0

        # TD Countdown 13
        if i >= 2:
            completed: list[TDCountdownState] = []
            for cd in active_countdowns:
                if i <= cd["start_idx"]:
                    continue
                if cd["kind"] == "bearish":
                    if closes_data[i] <= lows_data[i - 2]:
                        cd["count"] += 1
                else:
                    if closes_data[i] >= highs_data[i - 2]:
                        cd["count"] += 1
                if cd["count"] >= 13:
                    ptype = f"td_countdown_13_{cd['kind']}"
                    direction_cd: PatternDirection = "bearish" if cd["kind"] == "bearish" else "bullish"
                    patterns.append(PatternData(
                        type=ptype, direction=direction_cd,
                        start_time=points[cd["start_idx"]].time, end_time=points[i].time, confidence=0.76,
                    ))
                    completed.append(cd)
            for cd in completed:
                active_countdowns.remove(cd)

    # Fibonacci Timing Pattern — Kaabar Ch.9 proprietary.
    # Bullish: 8 consecutive bars where close[i] < close[i-5] AND close[i-5] < close[i-21]
    # Bearish: mirror (> instead of <).
    fib_bull = 0
    fib_bear = 0
    for i in range(21, len(points)):
        c = closes_data[i]
        c5 = closes_data[i - 5]
        c21 = closes_data[i - 21]
        if c < c5 < c21:
            fib_bull += 1
            fib_bear = 0
        elif c > c5 > c21:
            fib_bear += 1
            fib_bull = 0
        else:
            fib_bull = 0
            fib_bear = 0
        if fib_bull == 8:
            patterns.append(PatternData(
                type="fibonacci_timing", direction="bullish",
                start_time=points[i - 7].time, end_time=points[i].time, confidence=0.71,
            ))
            fib_bull = 0
        if fib_bear == 8:
            patterns.append(PatternData(
                type="fibonacci_timing", direction="bearish",
                start_time=points[i - 7].time, end_time=points[i].time, confidence=0.71,
            ))
            fib_bear = 0

    return PatternResponse(
        patterns=patterns,
        metadata={"scanned_bars": len(points), "patterns_found": len(patterns)},
    )


# ---------------------------------------------------------------------------
# Price Patterns (Double Top/Bottom, H&S, Gaps)
# ---------------------------------------------------------------------------


def build_price_patterns(payload: PatternRequest) -> PatternResponse:
    """Structural price patterns: double top/bottom, H&S, gaps."""
    points = payload.ohlcv[-payload.lookback :]
    patterns: list[PatternData] = []
    pivots = detect_swings(points, window=2)
    if len(pivots) < 3:
        pivots = detect_close_turning_pivots(points)
    thr = payload.threshold

    # Quick 3-bar fallback for terminal double-top/bottom
    if len(points) >= 3:
        p1, p2, p3 = points[-3], points[-2], points[-1]
        highs_diff = abs(p3.high - p1.high) / max(1e-9, p1.high)
        lows_diff = abs(p3.low - p1.low) / max(1e-9, p1.low)
        if highs_diff <= thr and p2.low < min(p1.low, p3.low):
            patterns.append(PatternData(
                type="double_top", direction="bearish",
                start_time=p1.time, end_time=p3.time, confidence=0.71,
                details={"height_diff": round(highs_diff, 4)},
            ))
        if lows_diff <= thr and p2.high > max(p1.high, p3.high):
            patterns.append(PatternData(
                type="double_bottom", direction="bullish",
                start_time=p1.time, end_time=p3.time, confidence=0.71,
                details={"depth_diff": round(lows_diff, 4)},
            ))

    # Double Top / Double Bottom (pivot-based) — Kaabar Ch.10: requires neckline breakout.
    closes_data = closes(points)
    if len(pivots) >= 3:
        p1, p2_neckline, p3 = pivots[-3], pivots[-2], pivots[-1]
        price_diff = abs(p3.price - p1.price) / max(1e-9, p1.price)
        neckline = p2_neckline.price
        if p1.kind == "high" and p3.kind == "high" and price_diff <= thr:
            # Kaabar Ch.10: scan after p3 for neckline breakout confirmation
            p3_idx = next((j for j, pt in enumerate(points) if pt.time == p3.time), len(points) - 1)
            confirmed = any(closes_data[j] < neckline for j in range(p3_idx, len(points)))
            patterns.append(PatternData(
                type="double_top", direction="bearish",
                start_time=p1.time, end_time=p3.time,
                confidence=0.78 if confirmed else 0.55,
                details={"height_diff": round(price_diff, 4), "neckline": round(neckline, 4),
                         "confirmed": confirmed},
            ))
        if p1.kind == "low" and p3.kind == "low" and price_diff <= thr:
            p3_idx = next((j for j, pt in enumerate(points) if pt.time == p3.time), len(points) - 1)
            confirmed = any(closes_data[j] > neckline for j in range(p3_idx, len(points)))
            patterns.append(PatternData(
                type="double_bottom", direction="bullish",
                start_time=p1.time, end_time=p3.time,
                confidence=0.78 if confirmed else 0.55,
                details={"depth_diff": round(price_diff, 4), "neckline": round(neckline, 4),
                         "confirmed": confirmed},
            ))

    # Head & Shoulders / Inverse H&S (5-pivot)
    # Kaabar Ch.10: neckline can be horizontal (average) or slanted (line through 2 valleys).
    use_slanted = payload.slanted_neckline
    if len(pivots) >= 5:
        for idx in range(len(pivots) - 4):
            ls, lv, h, rv, rs = pivots[idx], pivots[idx + 1], pivots[idx + 2], pivots[idx + 3], pivots[idx + 4]

            if (ls.kind == "high" and lv.kind == "low" and h.kind == "high"
                    and rv.kind == "low" and rs.kind == "high"):
                shoulder_diff = abs(rs.price - ls.price) / max(1e-9, ls.price)
                neckline_diff = abs(rv.price - lv.price) / max(1e-9, lv.price)
                if (h.price > ls.price and h.price > rs.price
                        and shoulder_diff <= thr * 2
                        and neckline_diff <= thr * 2):
                    if use_slanted:
                        # Slanted neckline: line through lv and rv
                        neckline_slope = (rv.price - lv.price) / max(1, rv.index - lv.index)
                        neckline_at_rs = lv.price + neckline_slope * (rs.index - lv.index)
                        neckline_mid = (lv.price + rv.price) / 2.0
                        head_height = h.price - neckline_mid
                        target = neckline_at_rs - head_height
                    else:
                        neckline_at_rs = (lv.price + rv.price) / 2.0
                        neckline_mid = neckline_at_rs
                        neckline_slope = 0.0
                        head_height = h.price - neckline_mid
                        target = neckline_mid - head_height
                    patterns.append(PatternData(
                        type="head_and_shoulders", direction="bearish",
                        start_time=ls.time, end_time=rs.time, confidence=0.72,
                        details={
                            "neckline_level": round(neckline_mid, 4),
                            "neckline_slope": round(neckline_slope, 6),
                            "neckline_at_rs": round(neckline_at_rs, 4),
                            "target_price": round(target, 4),
                            "shoulder_diff": round(shoulder_diff, 4),
                            "slanted": use_slanted,
                        },
                    ))

            if (ls.kind == "low" and lv.kind == "high" and h.kind == "low"
                    and rv.kind == "high" and rs.kind == "low"):
                shoulder_diff = abs(rs.price - ls.price) / max(1e-9, ls.price)
                neckline_diff = abs(rv.price - lv.price) / max(1e-9, lv.price)
                if (h.price < ls.price and h.price < rs.price
                        and shoulder_diff <= thr * 2
                        and neckline_diff <= thr * 2):
                    if use_slanted:
                        neckline_slope = (rv.price - lv.price) / max(1, rv.index - lv.index)
                        neckline_at_rs = lv.price + neckline_slope * (rs.index - lv.index)
                        neckline_mid = (lv.price + rv.price) / 2.0
                        head_depth = neckline_mid - h.price
                        target = neckline_at_rs + head_depth
                    else:
                        neckline_at_rs = (lv.price + rv.price) / 2.0
                        neckline_mid = neckline_at_rs
                        neckline_slope = 0.0
                        head_depth = neckline_mid - h.price
                        target = neckline_mid + head_depth
                    patterns.append(PatternData(
                        type="inverse_head_and_shoulders", direction="bullish",
                        start_time=ls.time, end_time=rs.time, confidence=0.72,
                        details={
                            "neckline_level": round(neckline_mid, 4),
                            "neckline_slope": round(neckline_slope, 6),
                            "neckline_at_rs": round(neckline_at_rs, 4),
                            "target_price": round(target, 4),
                            "shoulder_diff": round(shoulder_diff, 4),
                            "slanted": use_slanted,
                        },
                    ))

    # Gap Up / Gap Down — Kaabar Ch.10: ATR-filtered minimum gap size
    from indicator_engine.volatility import calculate_atr as _gap_atr

    gap_atr = _gap_atr(points, 14)
    for i in range(1, len(points)):
        prev = points[i - 1]
        cur = points[i]
        min_gap = gap_atr[i - 1] if i - 1 < len(gap_atr) else 0.0
        if cur.low > prev.high * (1.0 + thr) and (cur.low - prev.high) > min_gap:
            patterns.append(PatternData(
                type="gap_up", direction="bullish",
                start_time=prev.time, end_time=cur.time, confidence=0.62,
                details={"gap_size": round(cur.low - prev.high, 4), "atr": round(min_gap, 4)},
            ))
        if cur.high < prev.low * (1.0 - thr) and (prev.low - cur.high) > min_gap:
            patterns.append(PatternData(
                type="gap_down", direction="bearish",
                start_time=prev.time, end_time=cur.time, confidence=0.62,
                details={"gap_size": round(prev.low - cur.high, 4), "atr": round(min_gap, 4)},
            ))

    # Kaabar Ch.5 — Fibonacci Signal Techniques (post-processing on Fib levels)
    # 23.6% Reintegration: breakout below 23.6% → bearish continuation to 61.8%
    # 61.8% Reactionary: price reaches 61.8% → contrarian reaction
    if len(pivots) >= 2:
        for pi in range(len(pivots) - 1):
            s, e = pivots[pi], pivots[pi + 1]
            lo = min(s.price, e.price)
            hi = max(s.price, e.price)
            span = hi - lo
            if span < 1e-9:
                continue
            level_236 = hi - span * 0.236
            level_618 = hi - span * 0.618
            last_c = closes_data[-1]
            # 23.6% Reintegration: close breaks through 23.6% level
            if s.price < e.price and last_c < level_236:
                patterns.append(PatternData(
                    type="fib_reintegration_236", direction="bearish",
                    start_time=s.time, end_time=e.time, confidence=0.62,
                    details={"level_236": round(level_236, 4), "target_618": round(level_618, 4)},
                ))
            elif s.price > e.price and last_c > level_236:
                patterns.append(PatternData(
                    type="fib_reintegration_236", direction="bullish",
                    start_time=s.time, end_time=e.time, confidence=0.62,
                    details={"level_236": round(level_236, 4), "target_618": round(level_618, 4)},
                ))
            # 61.8% Reactionary: close near 61.8% level (within 1%)
            if abs(last_c - level_618) / max(1e-9, span) < 0.01:
                react_dir = "bullish" if s.price < e.price else "bearish"
                patterns.append(PatternData(
                    type="fib_reactionary_618", direction=react_dir,
                    start_time=s.time, end_time=e.time, confidence=0.65,
                    details={"level_618": round(level_618, 4)},
                ))

    return PatternResponse(
        patterns=patterns[:30],
        metadata={"scanned_bars": len(points), "patterns_found": len(patterns)},
    )


# ---------------------------------------------------------------------------
# Elliott Wave Patterns
# ---------------------------------------------------------------------------


def build_elliott_wave_patterns(payload: PatternRequest) -> PatternResponse:
    """Elliott 5-3 wave pattern with R1-R7 rule validation.

    Rules (Frost & Prechter canonical set):
      R1  (hard):  W2 retraces <= 100% of W1
      R1b (soft):  W2 retraces 38.2-78.6% of W1 (Fibonacci quality)
      R2:          W3 extends beyond W1
      R3:          W3 is not the shortest of W1, W3, W5
      R4  (hard):  W4 does not enter W1 price territory (cardinal rule)
      R5:          W3 >= 1.272x W1 (Fibonacci extension)
      R5b (soft):  W3 <= 4.236x W1 (upper bound, prevents noise spikes)
      R6:          ABC correction retraces 38.2-78.6% of impulse
      R7:          W5 within reasonable range (0.382-2.618x W1)

    Gate: R4 must pass — without it the structure is not an impulse wave.
    Confidence: 0.0 baseline + rule-weighted scoring.
    """
    points = payload.ohlcv[-payload.lookback :]
    pivots = detect_swings(points, window=2)
    patterns: list[PatternData] = []
    if len(pivots) >= 8:
        wave = pivots[-8:]
        impulse = wave[:5]
        correction = wave[5:]

        w1 = abs(impulse[1].price - impulse[0].price)
        w2 = abs(impulse[2].price - impulse[1].price)
        w3 = abs(impulse[3].price - impulse[2].price)
        w4 = abs(impulse[4].price - impulse[3].price)
        w5 = abs(impulse[4].price - impulse[3].price)  # W5 = move from W4 end to impulse end
        # W4 is the retracement (pivot 3→4), W5 is the final thrust (pivot 4→impulse end)
        # In a 5-pivot impulse: 0→1=W1, 1→2=W2, 2→3=W3, 3→4=W4, but W5 needs 6 pivots.
        # With 5 impulse pivots (indices 0-4): W5 is approximated as the last segment.
        impulse_span = abs(impulse[-1].price - impulse[0].price)
        correction_span = abs(correction[-1].price - correction[0].price)
        bullish = impulse[-1].price > impulse[0].price

        # --- R4 gate: cardinal rule, must pass to emit pattern ---
        r4_pass = False
        if bullish:
            if impulse[3].kind == "low" and impulse[3].price > impulse[0].price:
                r4_pass = True
        else:
            if impulse[3].kind == "high" and impulse[3].price < impulse[0].price:
                r4_pass = True

        if not r4_pass:
            return PatternResponse(
                patterns=[],
                metadata={"scanned_bars": len(points), "patterns_found": 0},
            )

        rules_passed: list[str] = ["R4_w4_no_overlap"]

        # R1 (hard): W2 retracement <= 100% of W1
        if w1 > 0 and w2 <= w1:
            rules_passed.append("R1_w2_retrace_valid")
        # R1b (soft): W2 retraces within Fibonacci quality zone
        if w1 > 0 and 0.382 <= w2 / w1 <= 0.786:
            rules_passed.append("R1b_w2_fib_quality")
        # R2: W3 extends beyond W1
        if w3 > w1:
            rules_passed.append("R2_w3_gt_w1")
        # R3 (corrected): W3 not shortest of W1, W3, W5
        if w3 >= min(w1, w5):
            rules_passed.append("R3_w3_not_shortest")
        # R5: W3 Fibonacci extension >= 1.272x W1
        if w1 > 0 and w3 >= 1.272 * w1:
            rules_passed.append("R5_w3_fib_ext")
        # R5b: W3 upper bound (prevents noise spikes as Wave 3)
        if w1 > 0 and w3 <= 4.236 * w1:
            rules_passed.append("R5b_w3_upper_bound")
        # R6: ABC correction retraces 38.2-78.6% of impulse
        if impulse_span > 0 and 0.382 <= correction_span / impulse_span <= 0.786:
            rules_passed.append("R6_correction_fib")
        # R7: W5 within reasonable range relative to W1
        if w1 > 0 and 0.382 <= w5 / w1 <= 2.618:
            rules_passed.append("R7_w5_reasonable")

        direction: PatternDirection = "bullish" if bullish else "bearish"
        # Confidence: 0.0 baseline, weighted by rule count (max 9 rules → max ~0.90)
        confidence = clamp(len(rules_passed) * 0.10, 0.0, 1.0)

        fib_ratios: dict[str, float] = {}
        if w1 > 0:
            fib_ratios["w2_w1"] = round(w2 / w1, 4)
            fib_ratios["w3_w1"] = round(w3 / w1, 4)
            fib_ratios["w5_w1"] = round(w5 / w1, 4)
        if impulse_span > 0:
            fib_ratios["correction_retrace"] = round(correction_span / impulse_span, 4)

        patterns.append(PatternData(
            type="elliott_5_3", direction=direction,
            start_time=wave[0].time, end_time=wave[-1].time, confidence=confidence,
            details={
                "impulse_points": [pivot.time for pivot in impulse],
                "correction_points": [pivot.time for pivot in correction],
                "fibonacci_valid": len(rules_passed) >= 5,
                "wave_lengths": {
                    "w1": round(w1, 4), "w2": round(w2, 4),
                    "w3": round(w3, 4), "w4": round(w4, 4), "w5": round(w5, 4),
                },
                "fib_ratios": fib_ratios,
                "rules_passed": rules_passed,
            },
        ))
    return PatternResponse(
        patterns=patterns,
        metadata={"scanned_bars": len(points), "patterns_found": len(patterns)},
    )


# ---------------------------------------------------------------------------
# Swing Points Endpoint
# ---------------------------------------------------------------------------


def calculate_swing_points(payload: SwingDetectRequest) -> SwingDetectResponse:
    """Detect and return swing highs/lows."""
    pivots = detect_swings(payload.ohlcv, window=payload.window)
    swings = [
        SwingPoint(index=p.index, time=p.time, price=p.price, kind=p.kind)
        for p in pivots
    ]
    return SwingDetectResponse(
        swings=swings,
        metadata={"count": len(swings), "window": payload.window},
    )


# ---------------------------------------------------------------------------
# Chart Transforms (Heikin-Ashi, Volume Candles, CARSI)
# ---------------------------------------------------------------------------


def apply_chart_transform(payload: ChartTransformRequest) -> ChartTransformResponse:
    """Transform OHLCV bars: Heikin-Ashi, K's CCS, Volume Candles, or CARSI."""
    from indicator_engine.oscillators import rsi

    points = payload.ohlcv
    transformed: list[OHLCVPoint] = []
    if payload.transformType == "heikin_ashi":
        previous_open = points[0].open
        previous_close = points[0].close
        for point in points:
            ha_close = (point.open + point.high + point.low + point.close) / 4.0
            ha_open = (previous_open + previous_close) / 2.0
            ha_high = max(point.high, ha_open, ha_close)
            ha_low = min(point.low, ha_open, ha_close)
            transformed.append(OHLCVPoint(
                time=point.time, open=ha_open, high=ha_high, low=ha_low,
                close=ha_close, volume=point.volume,
            ))
            previous_open = ha_open
            previous_close = ha_close
    elif payload.transformType == "volume_candles":
        # Kaabar Ch.4: Volume Candles keep OHLC unchanged.  Only metadata
        # (volume_tier 1-4) is added — the frontend renders candle width.
        avg_volume = mean(volumes(points)) if points else 1.0
        tiers: list[int] = []
        for point in points:
            ratio = point.volume / max(1e-9, avg_volume)
            if ratio >= 2.0:
                tiers.append(4)
            elif ratio >= 1.25:
                tiers.append(3)
            elif ratio >= 0.75:
                tiers.append(2)
            else:
                tiers.append(1)
            transformed.append(OHLCVPoint(
                time=point.time, open=point.open, high=point.high,
                low=point.low, close=point.close, volume=point.volume,
            ))
    elif payload.transformType == "k_candles":
        # Kaabar Ch.4 — K's Candlestick Charting System (K's CCS):
        # Apply EMA(5) independently to each OHLC column.
        from indicator_engine.trend import ema as _ema

        opens = [p.open for p in points]
        high_vals = [p.high for p in points]
        low_vals = [p.low for p in points]
        close_vals = [p.close for p in points]
        k_open = _ema(opens, 5)
        k_high = _ema(high_vals, 5)
        k_low = _ema(low_vals, 5)
        k_close = _ema(close_vals, 5)
        for i, point in enumerate(points):
            transformed.append(OHLCVPoint(
                time=point.time,
                open=k_open[i],
                high=max(k_open[i], k_high[i], k_low[i], k_close[i]),
                low=min(k_open[i], k_high[i], k_low[i], k_close[i]),
                close=k_close[i],
                volume=point.volume,
            ))
    elif payload.transformType == "carsi":
        # Kaabar Ch.4 — CARSI: RSI on all 4 OHLC columns → CARSI candles.
        opens = [p.open for p in points]
        high_vals = [p.high for p in points]
        low_vals = [p.low for p in points]
        close_vals = [p.close for p in points]
        rsi_open = rsi(opens, 14)
        rsi_high = rsi(high_vals, 14)
        rsi_low = rsi(low_vals, 14)
        rsi_close = rsi(close_vals, 14)
        for i, point in enumerate(points):
            ro = rsi_open[i]
            rh = rsi_high[i]
            rl = rsi_low[i]
            rc = rsi_close[i]
            transformed.append(OHLCVPoint(
                time=point.time,
                open=ro,
                high=max(ro, rh, rl, rc),
                low=min(ro, rh, rl, rc),
                close=rc,
                volume=point.volume,
            ))
    else:
        transformed = points

    extra: dict[str, Any] = {"transform": payload.transformType, "points": len(transformed)}
    if payload.transformType == "volume_candles":
        extra["volume_tiers"] = tiers
    return ChartTransformResponse(data=transformed, metadata=extra)


# ---------------------------------------------------------------------------
# Strategy Metrics
# ---------------------------------------------------------------------------


def build_strategy_metrics(payload: EvaluateStrategyRequest) -> StrategyEvaluationResponse:
    """Compute strategy performance metrics from trade list."""
    pnl_values: list[float] = []
    returns: list[float] = []
    wins: list[float] = []
    losses: list[float] = []
    for trade in payload.trades:
        gross = (trade.exit - trade.entry) * trade.quantity
        if trade.side == "short":
            gross = -gross
        pnl = gross - trade.fee
        pnl_values.append(pnl)
        base = trade.entry * trade.quantity
        returns.append(pnl / base if base else 0.0)
        if pnl >= 0:
            wins.append(pnl)
        else:
            losses.append(pnl)

    total = sum(pnl_values)
    count = len(payload.trades)
    hit_ratio = (len(wins) / count) if count else 0.0
    average_win = mean(wins) if wins else 0.0
    average_loss_abs = abs(mean(losses)) if losses else 0.0
    rr_ratio = (average_win / average_loss_abs) if average_loss_abs else 0.0
    expectancy = (hit_ratio * average_win) - ((1.0 - hit_ratio) * average_loss_abs)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss else (gross_profit if gross_profit > 0 else 0.0)

    if returns:
        avg_return = mean(returns)
        std_dev = pstdev(returns) if len(returns) > 1 else 0.0
        downside_values = [r for r in returns if r < 0]
        downside_std = pstdev(downside_values) if len(downside_values) > 1 else 0.0
        sharpe = ((avg_return - payload.riskFreeRate) / std_dev) if std_dev > 0 else 0.0
        sortino = ((avg_return - payload.riskFreeRate) / downside_std) if downside_std > 0 else 0.0
    else:
        sharpe = 0.0
        sortino = 0.0

    metrics = StrategyMetrics(
        net_return=total,
        hit_ratio=hit_ratio,
        risk_reward_ratio=rr_ratio,
        expectancy=expectancy,
        profit_factor=profit_factor,
        sharpe=sharpe,
        sortino=sortino,
        average_win=average_win,
        average_loss=-average_loss_abs,
    )
    return StrategyEvaluationResponse(metrics=metrics, tradeCount=count)
