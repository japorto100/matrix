"""Tests for indicator_engine.volatility — BB, ATR, Keltner, Squeeze, Regime, BB signals."""

from __future__ import annotations



from indicator_engine.models import OHLCVPoint
from indicator_engine.volatility import (
    bollinger_bands_raw,
    bollinger_bandwidth,
    bollinger_percent_b,
    calculate_atr,
    calculate_atr_rsi,
    calculate_bb_aggressive,
    calculate_bb_bandwidth,
    calculate_bb_conservative,
    calculate_bb_percent_b,
    calculate_bb_trend_friendly,
    calculate_bollinger_keltner_squeeze,
    calculate_bollinger_on_rsi,
    calculate_hmm_regime,
    calculate_keltner,
    calculate_markov_regime,
    calculate_regime,
    calculate_volatility_suite,
    donchian_channels,
    keltner_channels,
)


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


class TestBollingerBands:
    def test_lengths(self, closes_1000: list[float]) -> None:
        upper, mid, lower = bollinger_bands_raw(closes_1000, 20)
        assert len(upper) == len(mid) == len(lower) == 1000

    def test_upper_ge_lower(self, closes_1000: list[float]) -> None:
        upper, _, lower = bollinger_bands_raw(closes_1000, 20)
        for i in range(len(upper)):
            assert upper[i] >= lower[i]

    def test_bandwidth_positive(self, closes_1000: list[float]) -> None:
        bw = bollinger_bandwidth(closes_1000, 20)
        for v in bw:
            assert v >= 0.0

    def test_percent_b_range(self, closes_1000: list[float]) -> None:
        pctb = bollinger_percent_b(closes_1000, 20)
        # %B can go outside 0-1 when price is outside bands
        assert len(pctb) == 1000


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------


class TestATR:
    def test_length(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        result = calculate_atr(ohlcv_points_1000, 14)
        assert len(result) == 1000

    def test_non_negative(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        result = calculate_atr(ohlcv_points_1000, 14)
        for v in result:
            assert v >= 0.0

    def test_short_input(self) -> None:
        pt = OHLCVPoint(time=1, open=100, high=105, low=95, close=102, volume=1000)
        result = calculate_atr([pt], 14)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Keltner
# ---------------------------------------------------------------------------


class TestKeltner:
    def test_lengths(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        upper, mid, lower = keltner_channels(ohlcv_points_1000)
        assert len(upper) == len(mid) == len(lower) == 1000

    def test_upper_ge_lower(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        upper, _, lower = keltner_channels(ohlcv_points_1000)
        for i in range(len(upper)):
            assert upper[i] >= lower[i]


class TestKeltnerEndpoint:
    def test_response(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import KeltnerRequest
        req = KeltnerRequest(ohlcv=ohlcv_points_100)
        resp = calculate_keltner(req)
        assert len(resp.upper) == 100
        assert len(resp.middle) == 100
        assert len(resp.lower) == 100


# ---------------------------------------------------------------------------
# BB Variant Endpoints
# ---------------------------------------------------------------------------


class TestBBBandwidthEndpoint:
    def test_response(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import BollingerVariantRequest
        req = BollingerVariantRequest(ohlcv=ohlcv_points_100, period=20, numStd=2.0)
        resp = calculate_bb_bandwidth(req)
        assert len(resp.data) == 100


class TestBBPercentBEndpoint:
    def test_response(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import BollingerVariantRequest
        req = BollingerVariantRequest(ohlcv=ohlcv_points_100, period=20, numStd=2.0)
        resp = calculate_bb_percent_b(req)
        assert len(resp.data) == 100


class TestBBOnRSI:
    def test_response(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import BollingerVariantRequest
        req = BollingerVariantRequest(ohlcv=ohlcv_points_100, period=14, numStd=2.0)
        resp = calculate_bollinger_on_rsi(req)
        assert len(resp.upper) == 100
        assert len(resp.mid) == 100
        assert len(resp.lower) == 100


# ---------------------------------------------------------------------------
# BB/Keltner Squeeze
# ---------------------------------------------------------------------------


class TestSqueeze:
    def test_response_format(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import BollingerSqueezeRequest
        req = BollingerSqueezeRequest(ohlcv=ohlcv_points_100)
        resp = calculate_bollinger_keltner_squeeze(req)
        assert len(resp.squeeze) == 100
        assert len(resp.histogram) == 100
        assert all(isinstance(v, bool) for v in resp.squeeze)


# ---------------------------------------------------------------------------
# Volatility Suite
# ---------------------------------------------------------------------------


class TestVolatilitySuite:
    def test_response_fields(self, closes_1000: list[float]) -> None:
        from indicator_engine.models import VolatilitySuiteRequest
        req = VolatilitySuiteRequest(closes=closes_1000, lookback=20)
        resp = calculate_volatility_suite(req)
        assert resp.spike_weighted_vol >= 0
        assert resp.volatility_index >= 0
        assert resp.exp_weighted_stddev >= 0
        assert resp.volatility_regime in ("elevated", "normal", "compressed")
        assert resp.spike_weighted_regime in ("very_quiet", "normal", "elevated", "high_volatility")


# ---------------------------------------------------------------------------
# Regime Detection
# ---------------------------------------------------------------------------


class TestRegimeDetection:
    def test_rule_based(self, closes_1000: list[float]) -> None:
        from indicator_engine.models import RegimeDetectRequest
        req = RegimeDetectRequest(closes=closes_1000)
        resp = calculate_regime(req)
        assert resp.current_regime in ("bullish", "bearish", "ranging")
        assert 0.0 <= resp.confidence <= 1.0


# ---------------------------------------------------------------------------
# BB Signal Techniques
# ---------------------------------------------------------------------------


class TestBBConservative:
    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import BollingerVariantRequest
        req = BollingerVariantRequest(ohlcv=ohlcv_points_1000, period=20, numStd=2.0)
        resp = calculate_bb_conservative(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)


class TestBBAggressive:
    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import BollingerVariantRequest
        req = BollingerVariantRequest(ohlcv=ohlcv_points_1000, period=20, numStd=2.0)
        resp = calculate_bb_aggressive(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)


class TestBBTrendFriendly:
    def test_signals_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import BBTrendFriendlyRequest
        req = BBTrendFriendlyRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_bb_trend_friendly(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# ATR-RSI
# ---------------------------------------------------------------------------


class TestATRRSI:
    def test_range_0_100(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RSIVariantRequest
        req = RSIVariantRequest(ohlcv=ohlcv_points_1000, rsiPeriod=14, atrPeriod=14)
        resp = calculate_atr_rsi(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert 0.0 <= pt.value <= 100.0

    def test_metadata(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import RSIVariantRequest
        req = RSIVariantRequest(ohlcv=ohlcv_points_1000, rsiPeriod=14, atrPeriod=14)
        resp = calculate_atr_rsi(req)
        assert resp.metadata["indicator"] == "ATR_RSI"


# ---------------------------------------------------------------------------
# Markov Regime
# ---------------------------------------------------------------------------


class TestMarkovRegime:
    def test_response_fields(self, closes_1000: list[float]) -> None:
        from indicator_engine.models import RegimeDetectRequest
        req = RegimeDetectRequest(closes=closes_1000)
        resp = calculate_markov_regime(req)
        assert resp.current_regime in ("bullish", "bearish", "ranging")
        assert isinstance(resp.transition_probs, dict)
        assert resp.expected_duration > 0
        assert 0.0 <= resp.shift_probability <= 1.0

    def test_stationary_sums_to_1(self, closes_1000: list[float]) -> None:
        from indicator_engine.models import RegimeDetectRequest
        req = RegimeDetectRequest(closes=closes_1000)
        resp = calculate_markov_regime(req)
        total = sum(resp.stationary_distribution.values())
        assert abs(total - 1.0) < 0.01


# ---------------------------------------------------------------------------
# HMM Regime
# ---------------------------------------------------------------------------


class TestHMMRegime:
    def test_response_without_hmmlearn(self, closes_1000: list[float]) -> None:
        """HMM gracefully degrades if hmmlearn is not installed."""
        from indicator_engine.models import RegimeDetectRequest
        req = RegimeDetectRequest(closes=closes_1000)
        resp = calculate_hmm_regime(req)
        # Either returns real results or fallback (n_components=0)
        assert isinstance(resp.n_components, int)
        assert isinstance(resp.means, list)
        assert isinstance(resp.bic_score, float)


# ---------------------------------------------------------------------------
# Donchian Channels
# ---------------------------------------------------------------------------


class TestDonchianChannels:
    def test_length(self, ohlcv_dict_1000: dict) -> None:
        upper, middle, lower = donchian_channels(ohlcv_dict_1000["high"], ohlcv_dict_1000["low"])
        assert len(upper) == 1000
        assert len(middle) == 1000
        assert len(lower) == 1000

    def test_upper_gte_lower(self, ohlcv_dict_1000: dict) -> None:
        upper, middle, lower = donchian_channels(ohlcv_dict_1000["high"], ohlcv_dict_1000["low"])
        for i in range(1000):
            assert upper[i] >= lower[i]
            assert abs(middle[i] - (upper[i] + lower[i]) / 2.0) < 1e-9

    def test_known_values(self) -> None:
        high = [10.0, 12.0, 11.0, 13.0, 9.0]
        low = [8.0, 9.0, 7.0, 10.0, 6.0]
        upper, middle, lower = donchian_channels(high, low, period=3)
        # At index 2 (full window): max(10,12,11)=12, min(8,9,7)=7
        assert upper[2] == 12.0
        assert lower[2] == 7.0
        assert abs(middle[2] - 9.5) < 1e-9
