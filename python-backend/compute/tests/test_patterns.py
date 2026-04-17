"""Tests for indicator_engine.patterns — candlestick, harmonic, timing, price, elliott, transforms."""

from __future__ import annotations

from indicator_engine.models import OHLCVPoint
from indicator_engine.patterns import (
    apply_chart_transform,
    build_candlestick_patterns,
    build_elliott_wave_patterns,
    build_fibonacci_confluence,
    build_fibonacci_levels,
    build_harmonic_patterns,
    build_price_patterns,
    build_strategy_metrics,
    build_td_timing_patterns,
    calculate_swing_points,
    detect_swing_points,
    fibonacci_levels,
    market_structure,
    market_structure_trend,
    pivot_points,
    zigzag,
)

# ---------------------------------------------------------------------------
# Fibonacci
# ---------------------------------------------------------------------------


class TestFibonacci:
    def test_levels_count(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        resp = fibonacci_levels(ohlcv_points_1000)
        assert len(resp.levels) == 13  # 13 standard ratios

    def test_swing_keys(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        resp = fibonacci_levels(ohlcv_points_1000)
        assert "start_time" in resp.swing
        assert "end_time" in resp.swing

    def test_endpoint(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=250)
        resp = build_fibonacci_levels(req)
        assert len(resp.levels) == 13


class TestFibConfluence:
    def test_response(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import FibonacciConfluenceRequest
        req = FibonacciConfluenceRequest(ohlcv=ohlcv_points_1000)
        resp = build_fibonacci_confluence(req)
        # May have 0 zones if data doesn't cluster
        assert isinstance(resp.zones, list)
        assert "totalLevels" in resp.metadata


# ---------------------------------------------------------------------------
# Candlestick Patterns
# ---------------------------------------------------------------------------


class TestCandlestickPatterns:
    def test_returns_patterns(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=250)
        resp = build_candlestick_patterns(req)
        assert isinstance(resp.patterns, list)
        assert resp.metadata["scanned_bars"] == 250

    def test_pattern_fields(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=250)
        resp = build_candlestick_patterns(req)
        for p in resp.patterns:
            assert p.direction in ("bullish", "bearish", "neutral")
            assert 0.0 <= p.confidence <= 1.0
            assert p.start_time <= p.end_time

    def test_max_50_patterns(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=1000)
        resp = build_candlestick_patterns(req)
        assert len(resp.patterns) <= 50


# ---------------------------------------------------------------------------
# Harmonic Patterns
# ---------------------------------------------------------------------------


class TestHarmonicPatterns:
    def test_returns_list(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=250)
        resp = build_harmonic_patterns(req)
        assert isinstance(resp.patterns, list)

    def test_valid_types(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=500)
        resp = build_harmonic_patterns(req)
        valid_types = {
            "gartley", "bat", "butterfly", "crab", "abcd",
            "feiw_failed_breakout", "feiw_failed_breakdown",
        }
        for p in resp.patterns:
            assert p.type in valid_types, f"Unknown type: {p.type}"


# ---------------------------------------------------------------------------
# TD Timing Patterns
# ---------------------------------------------------------------------------


class TestTDTiming:
    def test_returns_patterns(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=500)
        resp = build_td_timing_patterns(req)
        assert isinstance(resp.patterns, list)

    def test_valid_types(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=500)
        resp = build_td_timing_patterns(req)
        valid_prefixes = {"td_setup_9", "tdst_level", "td_countdown_13", "fibonacci_timing"}
        for p in resp.patterns:
            assert any(p.type.startswith(prefix) for prefix in valid_prefixes), f"Unknown: {p.type}"


# ---------------------------------------------------------------------------
# Price Patterns
# ---------------------------------------------------------------------------


class TestPricePatterns:
    def test_returns_list(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=250)
        resp = build_price_patterns(req)
        assert isinstance(resp.patterns, list)

    def test_valid_types(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=500)
        resp = build_price_patterns(req)
        valid_types = {
            "double_top", "double_bottom", "head_and_shoulders",
            "inverse_head_and_shoulders", "gap_up", "gap_down",
            "fib_reintegration_236", "fib_reactionary_618",
        }
        for p in resp.patterns:
            assert p.type in valid_types, f"Unknown: {p.type}"


# ---------------------------------------------------------------------------
# Elliott Wave
# ---------------------------------------------------------------------------


class TestElliottWave:
    def test_returns_list(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=500)
        resp = build_elliott_wave_patterns(req)
        assert isinstance(resp.patterns, list)

    def test_confidence_weighted(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import PatternRequest
        req = PatternRequest(ohlcv=ohlcv_points_1000, lookback=500)
        resp = build_elliott_wave_patterns(req)
        for p in resp.patterns:
            assert 0.0 <= p.confidence <= 1.0
            if p.details.get("rules_passed"):
                assert "R4_w4_no_overlap" in p.details["rules_passed"]


# ---------------------------------------------------------------------------
# Swing Points
# ---------------------------------------------------------------------------


class TestSwingPoints:
    def test_response(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import SwingDetectRequest
        req = SwingDetectRequest(ohlcv=ohlcv_points_1000, window=3)
        resp = calculate_swing_points(req)
        assert len(resp.swings) > 0
        for s in resp.swings:
            assert s.kind in ("high", "low")


# ---------------------------------------------------------------------------
# Chart Transforms
# ---------------------------------------------------------------------------


class TestChartTransforms:
    def test_heikin_ashi(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import ChartTransformRequest
        req = ChartTransformRequest(ohlcv=ohlcv_points_100, transformType="heikin_ashi")
        resp = apply_chart_transform(req)
        assert len(resp.data) == 100
        # HA high >= HA low
        for pt in resp.data:
            assert pt.high >= pt.low

    def test_k_candles(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import ChartTransformRequest
        req = ChartTransformRequest(ohlcv=ohlcv_points_100, transformType="k_candles")
        resp = apply_chart_transform(req)
        assert len(resp.data) == 100

    def test_carsi(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import ChartTransformRequest
        req = ChartTransformRequest(ohlcv=ohlcv_points_100, transformType="carsi")
        resp = apply_chart_transform(req)
        assert len(resp.data) == 100
        # CARSI values are RSI-based (0-100 range)
        for pt in resp.data:
            assert 0.0 <= pt.close <= 100.0


# ---------------------------------------------------------------------------
# Strategy Metrics
# ---------------------------------------------------------------------------


class TestStrategyMetrics:
    def test_basic_trades(self) -> None:
        from indicator_engine.models import EvaluateStrategyRequest, TradeInput
        trades = [
            TradeInput(entry=100, exit=110, quantity=1, side="long"),
            TradeInput(entry=100, exit=95, quantity=1, side="long"),
            TradeInput(entry=100, exit=120, quantity=1, side="long"),
        ]
        req = EvaluateStrategyRequest(trades=trades)
        resp = build_strategy_metrics(req)
        assert resp.tradeCount == 3
        assert resp.metrics.hit_ratio == 2 / 3
        assert resp.metrics.net_return == 10 + (-5) + 20  # = 25
        assert resp.metrics.profit_factor > 0

    def test_empty_trades(self) -> None:
        from indicator_engine.models import EvaluateStrategyRequest
        req = EvaluateStrategyRequest(trades=[])
        resp = build_strategy_metrics(req)
        assert resp.tradeCount == 0
        assert resp.metrics.net_return == 0


# ---------------------------------------------------------------------------
# Pivot Points
# ---------------------------------------------------------------------------


class TestPivotPoints:
    def test_classic_known_values(self) -> None:
        # H=110, L=90, C=105 → PP = (110+90+105)/3 = 101.667
        result = pivot_points(110.0, 90.0, 105.0, "classic")
        assert abs(result["pp"] - 101.6667) < 0.01
        assert result["r1"] > result["pp"]
        assert result["s1"] < result["pp"]
        assert result["r2"] > result["r1"]
        assert result["s2"] < result["s1"]

    def test_fibonacci_has_fib_ratios(self) -> None:
        result = pivot_points(110.0, 90.0, 105.0, "fibonacci")
        r = 110.0 - 90.0  # = 20
        pp = result["pp"]
        assert abs(result["r1"] - (pp + 0.382 * r)) < 0.01
        assert abs(result["s1"] - (pp - 0.382 * r)) < 0.01

    def test_camarilla_close_anchored(self) -> None:
        result = pivot_points(110.0, 90.0, 105.0, "camarilla")
        # Camarilla uses close as anchor, not PP
        assert result["h1"] > 105.0
        assert result["l1"] < 105.0
        assert result["h4"] > result["h3"] > result["h2"] > result["h1"]
        assert result["l4"] < result["l3"] < result["l2"] < result["l1"]

    def test_flat_bar(self) -> None:
        # H == L == C → all levels collapse
        result = pivot_points(100.0, 100.0, 100.0, "classic")
        assert result["pp"] == 100.0
        assert result["r1"] == 100.0
        assert result["s1"] == 100.0


# ---------------------------------------------------------------------------
# ZigZag
# ---------------------------------------------------------------------------


class TestZigZag:
    def test_basic_output(self, ohlcv_dict_1000: dict) -> None:
        result = zigzag(ohlcv_dict_1000["high"], ohlcv_dict_1000["low"])
        assert len(result) >= 2
        # All pivots have required keys
        for p in result:
            assert "index" in p
            assert "price" in p
            assert p["type"] in ("high", "low")

    def test_alternating_types(self, ohlcv_dict_1000: dict) -> None:
        result = zigzag(ohlcv_dict_1000["high"], ohlcv_dict_1000["low"])
        # After the first pivot, types should alternate (high→low→high...)
        for i in range(1, len(result)):
            assert result[i]["type"] != result[i - 1]["type"], f"Non-alternating at pivot {i}"

    def test_higher_deviation_fewer_pivots(self, ohlcv_dict_1000: dict) -> None:
        highs, lows = ohlcv_dict_1000["high"], ohlcv_dict_1000["low"]
        pivots_5 = zigzag(highs, lows, deviation=5.0)
        pivots_15 = zigzag(highs, lows, deviation=15.0)
        assert len(pivots_15) <= len(pivots_5)

    def test_short_series(self) -> None:
        assert zigzag([100.0], [90.0]) == []


# ---------------------------------------------------------------------------
# Market Structure (HH/HL/LH/LL)
# ---------------------------------------------------------------------------


class TestMarketStructure:
    def test_basic_output(self, ohlcv_dict_1000: dict) -> None:
        result = market_structure(ohlcv_dict_1000["high"], ohlcv_dict_1000["low"])
        assert len(result) > 0
        for s in result:
            assert s["label"] in ("HH", "HL", "LH", "LL", "SH", "SL", "EH", "EL")

    def test_known_uptrend(self) -> None:
        # Clearly rising prices → should produce HH + HL labels
        high = [10.0 + i * 2 for i in range(30)]
        low = [8.0 + i * 2 for i in range(30)]
        result = market_structure(high, low, lookback=2)
        labels = [s["label"] for s in result if s["label"] in ("HH", "LH")]
        # Most high-labels should be HH in uptrend
        hh_count = labels.count("HH")
        assert hh_count >= len(labels) // 2, f"Expected mostly HH in uptrend, got {labels}"

    def test_trend_determination(self) -> None:
        high = [10.0 + i * 2 for i in range(30)]
        low = [8.0 + i * 2 for i in range(30)]
        labels = market_structure(high, low, lookback=2)
        trend = market_structure_trend(labels)
        assert trend in ("bullish", "bearish", "ranging")

    def test_swing_detection_symmetry(self) -> None:
        # Symmetric zigzag → should detect both highs and lows
        high = [100 + 10 * (1 if i % 4 < 2 else -1) for i in range(40)]
        low = [90 + 10 * (1 if i % 4 < 2 else -1) for i in range(40)]
        swings = detect_swing_points(high, low, lookback=2)
        types = [s["type"] for s in swings]
        assert "high" in types
        assert "low" in types
