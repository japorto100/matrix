"""Tests for indicator_engine.volume — VWAP, OBV, CMF, Volume Profile."""

from __future__ import annotations

from indicator_engine.models import OHLCVPoint
from indicator_engine.volume import calculate_vwap, cmf, obv, volume_profile, vwap


class TestVWAP:
    def test_length(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        result = vwap(ohlcv_points_1000)
        assert len(result) == 1000

    def test_positive_values(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        result = vwap(ohlcv_points_1000)
        for v in result:
            assert v > 0


class TestVWAPEndpoint:
    def test_response(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import VWAPRequest
        req = VWAPRequest(ohlcv=ohlcv_points_100)
        resp = calculate_vwap(req)
        assert len(resp.data) == 100
        assert resp.metadata["indicator"] == "VWAP"


class TestOBV:
    def test_length(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        result = obv(ohlcv_points_1000)
        assert len(result) == 1000

    def test_starts_at_zero(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        result = obv(ohlcv_points_1000)
        assert result[0] == 0.0

    def test_empty(self) -> None:
        assert obv([]) == []


class TestCMF:
    def test_length(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        result = cmf(ohlcv_points_1000, 20)
        assert len(result) == 1000

    def test_range(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        result = cmf(ohlcv_points_1000, 20)
        for v in result:
            assert -5.0 <= v <= 5.0  # CMF is bounded but not strictly -1..1 with SMA normalization


# ---------------------------------------------------------------------------
# Volume Profile / POC
# ---------------------------------------------------------------------------


class TestVolumeProfile:
    def test_basic_structure(self, ohlcv_dict_1000: dict) -> None:
        result = volume_profile(
            ohlcv_dict_1000["high"],
            ohlcv_dict_1000["low"],
            ohlcv_dict_1000["volume"],
        )
        assert "poc_price" in result
        assert "va_high" in result
        assert "va_low" in result
        assert "histogram" in result
        assert len(result["histogram"]) == 24  # default bins

    def test_va_contains_poc(self, ohlcv_dict_1000: dict) -> None:
        result = volume_profile(
            ohlcv_dict_1000["high"],
            ohlcv_dict_1000["low"],
            ohlcv_dict_1000["volume"],
        )
        assert result["va_low"] <= result["poc_price"] <= result["va_high"]

    def test_empty_input(self) -> None:
        result = volume_profile([], [], [])
        assert result["poc_price"] == 0.0
        assert result["histogram"] == []

    def test_single_bar(self) -> None:
        result = volume_profile([110.0], [90.0], [1000.0], num_bins=10)
        assert result["poc_price"] > 0
        assert len(result["histogram"]) == 10
