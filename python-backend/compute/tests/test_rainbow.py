"""Tests for indicator_engine.rainbow — 7 Rainbow indicators, confluence, R-Pattern, Gap."""

from __future__ import annotations

from indicator_engine.models import OHLCVPoint
from indicator_engine.rainbow import (
    calculate_gap_pattern,
    calculate_r_pattern,
    calculate_rainbow_collection,
    calculate_rainbow_confluence,
    rainbow_composite_score,
)


class TestRainbowCollection:
    def test_all_7_colors(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RainbowRequest
        req = RainbowRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_rainbow_collection(req)
        for color in ("red", "orange", "yellow", "green", "blue", "indigo", "violet"):
            series = getattr(resp, color)
            assert len(series.data) == 1000
            assert color.upper() in series.metadata["indicator"].upper()

    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RainbowRequest
        req = RainbowRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_rainbow_collection(req)
        for color in ("red", "orange", "yellow", "green", "blue", "indigo", "violet"):
            series = getattr(resp, color)
            for pt in series.data:
                assert pt.value in (-1.0, 0.0, 1.0), f"{color} has invalid signal {pt.value}"


class TestRainbowConfluence:
    def test_length(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RainbowRequest
        req = RainbowRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_rainbow_confluence(req)
        assert len(resp.data) == 1000

    def test_signal_strength_range(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RainbowRequest
        req = RainbowRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_rainbow_confluence(req)
        for pt in resp.data:
            assert -7.0 <= pt.value <= 7.0  # max 7 indicators


class TestRainbowComposite:
    def test_length(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RainbowRequest
        req = RainbowRequest(ohlcv=ohlcv_points_1000)
        resp = rainbow_composite_score(req)
        assert len(resp.data) == 1000

    def test_value_range(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RainbowRequest
        req = RainbowRequest(ohlcv=ohlcv_points_1000)
        resp = rainbow_composite_score(req)
        for pt in resp.data:
            assert -1.0 <= pt.value <= 1.0


class TestRPattern:
    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RPatternRequest
        req = RPatternRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_r_pattern(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)


class TestGapPattern:
    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import GapPatternRequest
        req = GapPatternRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_gap_pattern(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)
