"""Tests for indicator_engine.oscillators — RSI, MACD, Stochastic, ADX, K's Collection, Composite, Rob Booker, Cross-Asset, Connors RSI."""

from __future__ import annotations

import pytest
from indicator_engine.models import OHLCVPoint
from indicator_engine.oscillators import (
    adx_series,
    build_composite_signal,
    calculate_adx,
    calculate_cross_asset_convergence,
    calculate_ks_collection,
    calculate_macd,
    calculate_rob_booker_reversal,
    calculate_rsi_dcc,
    calculate_rsi_ma_cross,
    calculate_rsi_v_technique,
    calculate_stochastic,
    connors_rsi,
    heartbeat_score,
    macd,
    percent_rank,
    rsi,
    stochastic,
)

# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------


class TestRSI:
    def test_length(self, closes_1000: list[float]) -> None:
        assert len(rsi(closes_1000, 14)) == 1000

    def test_range_0_100(self, closes_1000: list[float]) -> None:
        result = rsi(closes_1000, 14)
        for v in result[15:]:  # skip warmup
            assert 0.0 <= v <= 100.0

    def test_warmup_is_50(self, closes_1000: list[float]) -> None:
        result = rsi(closes_1000, 14)
        assert result[0] == 50.0

    def test_short_input(self) -> None:
        assert rsi([100.0], 14) == [50.0]


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------


class TestMACD:
    def test_lengths(self, closes_1000: list[float]) -> None:
        macd_line, signal_line, histogram = macd(closes_1000)
        assert len(macd_line) == 1000
        assert len(signal_line) == 1000
        assert len(histogram) == 1000

    def test_histogram_is_difference(self, closes_1000: list[float]) -> None:
        macd_line, signal_line, histogram = macd(closes_1000)
        for i in range(len(histogram)):
            assert histogram[i] == pytest.approx(macd_line[i] - signal_line[i], abs=1e-9)


class TestMACDEndpoint:
    def test_response_format(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import MACDRequest
        req = MACDRequest(ohlcv=ohlcv_points_100)
        resp = calculate_macd(req)
        assert len(resp.macd_line) == 100
        assert len(resp.signal_line) == 100
        assert len(resp.histogram) == 100


# ---------------------------------------------------------------------------
# Stochastic
# ---------------------------------------------------------------------------


class TestStochastic:
    def test_lengths(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        k, d = stochastic(ohlcv_points_1000)
        assert len(k) == 1000
        assert len(d) == 1000

    def test_k_range(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        k, _ = stochastic(ohlcv_points_1000)
        for v in k:
            assert 0.0 <= v <= 100.0


class TestStochasticEndpoint:
    def test_response(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import StochasticRequest
        req = StochasticRequest(ohlcv=ohlcv_points_100)
        resp = calculate_stochastic(req)
        assert len(resp.k) == 100
        assert len(resp.d) == 100


# ---------------------------------------------------------------------------
# ADX
# ---------------------------------------------------------------------------


class TestADX:
    def test_lengths(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        adx, dip, dim = adx_series(ohlcv_points_1000)
        assert len(adx) == 1000
        assert len(dip) == 1000
        assert len(dim) == 1000

    def test_adx_non_negative(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        adx, _, _ = adx_series(ohlcv_points_1000)
        for v in adx:
            assert v >= 0.0


class TestADXEndpoint:
    def test_response(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import ADXRequest
        req = ADXRequest(ohlcv=ohlcv_points_100)
        resp = calculate_adx(req)
        assert len(resp.adx) == 100


# ---------------------------------------------------------------------------
# K's Collection
# ---------------------------------------------------------------------------


class TestKsCollection:
    def test_response_keys(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import KsCollectionRequest
        req = KsCollectionRequest(ohlcv=ohlcv_points_1000)
        result = calculate_ks_collection(req)
        expected_keys = {
            "reversalI", "reversalII", "atrAdjustedRSI", "rsiSquared",
            "marsi", "marsiSignal", "fibonacciMA", "fibonacciMAHigh", "fibonacciMALow",
        }
        assert set(result.keys()) == expected_keys

    def test_reversal_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import KsCollectionRequest
        req = KsCollectionRequest(ohlcv=ohlcv_points_1000)
        result = calculate_ks_collection(req)
        for pt in result["reversalI"].data:
            assert pt.value in (-1.0, 0.0, 1.0)
        for pt in result["reversalII"].data:
            assert pt.value in (-1.0, 0.0, 1.0)

    def test_rsi_squared_range(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import KsCollectionRequest
        req = KsCollectionRequest(ohlcv=ohlcv_points_1000)
        result = calculate_ks_collection(req)
        for pt in result["rsiSquared"].data:
            assert 0.0 <= pt.value <= 100.0

    def test_data_length(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import KsCollectionRequest
        req = KsCollectionRequest(ohlcv=ohlcv_points_1000)
        result = calculate_ks_collection(req)
        for key, resp in result.items():
            assert len(resp.data) == 1000, f"{key} length mismatch"


# ---------------------------------------------------------------------------
# RSI Signal Techniques
# ---------------------------------------------------------------------------


class TestRSIVTechnique:
    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RSIVTechniqueRequest
        req = RSIVTechniqueRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_rsi_v_technique(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)


class TestRSIDCC:
    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RSIDCCRequest
        req = RSIDCCRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_rsi_dcc(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)


class TestRSIMACross:
    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RSIMACrossRequest
        req = RSIMACrossRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_rsi_ma_cross(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Heartbeat Score
# ---------------------------------------------------------------------------


class TestHeartbeatScore:
    def test_returns_score_and_details(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        score, details = heartbeat_score(ohlcv_points_1000)
        assert 0.0 <= score <= 1.0
        assert "swings" in details
        assert "cycleBars" in details
        assert details["engine"] in ("rust", "python")

    def test_short_input_zero(self) -> None:
        pts = [OHLCVPoint(time=i, open=100, high=101, low=99, close=100, volume=10) for i in range(10)]
        score, details = heartbeat_score(pts)
        assert score == 0.0
        assert details["swings"] < 6


# ---------------------------------------------------------------------------
# Composite Signal
# ---------------------------------------------------------------------------


class TestCompositeSignal:
    def test_response_format(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import CompositeSignalRequest
        req = CompositeSignalRequest(ohlcv=ohlcv_points_1000)
        resp = build_composite_signal(req)
        assert resp.signal in ("buy", "sell", "neutral")
        assert 0.0 <= resp.confidence <= 1.0
        assert "sma50_slope" in resp.components
        assert "heartbeat" in resp.components
        assert "volume_power" in resp.components


# ---------------------------------------------------------------------------
# Rob Booker Reversal
# ---------------------------------------------------------------------------


class TestRobBookerReversal:
    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RobBookerReversalRequest
        req = RobBookerReversalRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_rob_booker_reversal(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)

    def test_metadata(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RobBookerReversalRequest
        req = RobBookerReversalRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_rob_booker_reversal(req)
        assert resp.metadata["indicator"] == "ROB_BOOKER_REVERSAL"
        assert resp.metadata["stoch_k_period"] == 70


# ---------------------------------------------------------------------------
# Cross-Asset RSI Convergence
# ---------------------------------------------------------------------------


class TestCrossAssetConvergence:
    def test_signals_discrete(self, closes_1000: list[float]) -> None:
        from indicator_engine.models import CrossAssetConvergenceRequest
        # Invert closes as fake "inverse asset"
        inverse = [200.0 - c for c in closes_1000]
        req = CrossAssetConvergenceRequest(primary_closes=closes_1000, inverse_closes=inverse)
        resp = calculate_cross_asset_convergence(req)
        assert len(resp.signals) > 0
        for s in resp.signals:
            assert s in (-1.0, 0.0, 1.0)

    def test_rsi_series_present(self, closes_1000: list[float]) -> None:
        from indicator_engine.models import CrossAssetConvergenceRequest
        inverse = [200.0 - c for c in closes_1000]
        req = CrossAssetConvergenceRequest(primary_closes=closes_1000, inverse_closes=inverse)
        resp = calculate_cross_asset_convergence(req)
        assert len(resp.primary_rsi) == len(resp.signals)
        assert len(resp.inverse_rsi) == len(resp.signals)


# ---------------------------------------------------------------------------
# Connors RSI
# ---------------------------------------------------------------------------


class TestConnorsRSI:
    def test_length(self, closes_1000: list[float]) -> None:
        result = connors_rsi(closes_1000)
        assert len(result) == 1000

    def test_range_0_100(self, closes_1000: list[float]) -> None:
        result = connors_rsi(closes_1000)
        # Skip warmup bars
        for v in result[100:]:
            assert 0.0 <= v <= 100.0, f"CRSI out of range: {v}"

    def test_flat_series_near_50(self) -> None:
        flat = [100.0] * 200
        result = connors_rsi(flat)
        # Flat prices → no momentum → CRSI should be near 50
        for v in result[10:]:
            assert 30.0 <= v <= 70.0

    def test_rising_series_above_50(self) -> None:
        rising = [100.0 + i * 0.5 for i in range(200)]
        result = connors_rsi(rising)
        # Strong uptrend → CRSI should skew high after warmup
        avg = sum(result[120:]) / len(result[120:])
        assert avg > 50.0

    def test_short_series(self) -> None:
        result = connors_rsi([100.0])
        assert result == [50.0]


class TestPercentRank:
    def test_length(self) -> None:
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = percent_rank(vals, 5)
        assert len(result) == 5

    def test_ascending_last_is_high(self) -> None:
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = percent_rank(vals, 5)
        # Last value is the max → 4 out of 5 are strictly less = 80%
        assert abs(result[-1] - 80.0) < 0.01
