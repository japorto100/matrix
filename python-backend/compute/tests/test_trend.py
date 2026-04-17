"""Tests for indicator_engine.trend — MA primitives + Ichimoku + WMA/IWMA cross + SAR."""

from __future__ import annotations

import math

import pytest
from indicator_engine.models import OHLCVPoint
from indicator_engine.trend import (
    alma,
    calculate_exotic_ma,
    calculate_hma,
    calculate_ichimoku,
    calculate_wma_iwma_cross,
    ema,
    hma,
    iwma,
    kama,
    ols_ma,
    parabolic_sar,
    sma,
    smma,
    wma,
)

# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------


class TestSMA:
    def test_length_matches_input(self, closes_1000: list[float]) -> None:
        result = sma(closes_1000, 20)
        assert len(result) == 1000

    def test_period_1_identity(self, closes_1000: list[float]) -> None:
        result = sma(closes_1000, 1)
        assert result == closes_1000

    def test_known_values(self) -> None:
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = sma(data, 3)
        assert result[2] == pytest.approx(2.0, abs=1e-9)
        assert result[4] == pytest.approx(4.0, abs=1e-9)

    def test_no_nan(self, closes_1000: list[float]) -> None:
        result = sma(closes_1000, 20)
        assert all(not math.isnan(v) for v in result)


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------


class TestEMA:
    def test_length_matches_input(self, closes_1000: list[float]) -> None:
        result = ema(closes_1000, 20)
        assert len(result) == 1000

    def test_first_value_is_close(self, closes_1000: list[float]) -> None:
        result = ema(closes_1000, 20)
        assert result[0] == closes_1000[0]

    def test_empty_input(self) -> None:
        assert ema([], 10) == []

    def test_smoothing_reduces_variance(self, closes_1000: list[float]) -> None:
        result = ema(closes_1000, 50)
        from statistics import pstdev
        assert pstdev(result[50:]) < pstdev(closes_1000[50:])


# ---------------------------------------------------------------------------
# Other MAs
# ---------------------------------------------------------------------------


class TestSMMA:
    def test_length(self, closes_1000: list[float]) -> None:
        assert len(smma(closes_1000, 14)) == 1000

    def test_empty(self) -> None:
        assert smma([], 5) == []


class TestWMA:
    def test_length(self, closes_1000: list[float]) -> None:
        assert len(wma(closes_1000, 10)) == 1000

    def test_empty(self) -> None:
        assert wma([], 5) == []

    def test_recent_weighted_more(self) -> None:
        data = [1.0, 1.0, 1.0, 1.0, 10.0]
        result = wma(data, 5)
        # Last value 10 has highest weight, so WMA > SMA
        sma_val = sum(data) / 5
        assert result[-1] > sma_val


class TestHMA:
    def test_length(self, closes_1000: list[float]) -> None:
        result = hma(closes_1000, 9)
        assert len(result) == 1000

    def test_short_input_passthrough(self) -> None:
        data = [1.0, 2.0]
        assert hma(data, 9) == data


class TestKAMA:
    def test_length(self, closes_1000: list[float]) -> None:
        assert len(kama(closes_1000, 10)) == 1000

    def test_empty(self) -> None:
        assert kama([], 10) == []


class TestALMA:
    def test_length(self, closes_1000: list[float]) -> None:
        assert len(alma(closes_1000, 20)) == 1000

    def test_period_1_identity(self, closes_1000: list[float]) -> None:
        assert alma(closes_1000, 1) == closes_1000


class TestIWMA:
    def test_length(self, closes_1000: list[float]) -> None:
        assert len(iwma(closes_1000, 20)) == 1000


class TestOLSMA:
    def test_length(self, closes_1000: list[float]) -> None:
        assert len(ols_ma(closes_1000, 20)) == 1000


# ---------------------------------------------------------------------------
# Endpoint handlers
# ---------------------------------------------------------------------------


class TestExoticMAEndpoint:
    def test_sma_response_format(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import ExoticMARequest
        req = ExoticMARequest(ohlcv=ohlcv_points_100, maType="sma", period=10)
        resp = calculate_exotic_ma(req)
        assert len(resp.data) == 100
        assert resp.metadata["indicator"] == "SMA"

    def test_ema_response(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import ExoticMARequest
        req = ExoticMARequest(ohlcv=ohlcv_points_100, maType="ema", period=10)
        resp = calculate_exotic_ma(req)
        assert len(resp.data) == 100

    def test_kama_response(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import ExoticMARequest
        req = ExoticMARequest(ohlcv=ohlcv_points_100, maType="kama", period=10)
        resp = calculate_exotic_ma(req)
        assert len(resp.data) == 100


class TestHMAEndpoint:
    def test_response_format(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import HMARequest
        req = HMARequest(ohlcv=ohlcv_points_100, period=9)
        resp = calculate_hma(req)
        assert len(resp.data) == 100
        assert resp.metadata["indicator"] == "HMA"


class TestWMAIWMACross:
    def test_signals_are_discrete(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import WMAIWMACrossRequest
        req = WMAIWMACrossRequest(ohlcv=ohlcv_points_1000, period=20)
        resp = calculate_wma_iwma_cross(req)
        assert len(resp.data) == 1000
        for pt in resp.data:
            assert pt.value in (-1.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Ichimoku
# ---------------------------------------------------------------------------


class TestIchimoku:
    def test_response_structure(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import IchimokuRequest
        req = IchimokuRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_ichimoku(req)
        assert len(resp.tenkan) == 1000
        assert len(resp.kijun) == 1000
        # span_a/b include future points
        assert len(resp.span_a) >= 1000
        assert len(resp.span_b) >= 1000
        assert len(resp.chikou) == 1000

    def test_signals_length(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import IchimokuRequest
        req = IchimokuRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_ichimoku(req)
        assert len(resp.signals.above_cloud) == 1000
        assert len(resp.signals.strength) == 1000

    def test_strength_values(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import IchimokuRequest
        req = IchimokuRequest(ohlcv=ohlcv_points_1000)
        resp = calculate_ichimoku(req)
        valid = {"strong_bull", "weak_bull", "neutral", "weak_bear", "strong_bear"}
        for s in resp.signals.strength:
            assert s in valid

    def test_short_input(self) -> None:
        """IchimokuRequest requires min_length=2; verify ValidationError on single point."""
        import pytest
        from indicator_engine.models import IchimokuRequest
        with pytest.raises(Exception):
            IchimokuRequest(ohlcv=[
                OHLCVPoint(time=1, open=1, high=2, low=0.5, close=1.5, volume=100),
            ])


# ---------------------------------------------------------------------------
# Parabolic SAR (IND.V1)
# ---------------------------------------------------------------------------

class TestParabolicSAR:
    def _uptrend_data(self, n: int = 50) -> tuple[list[float], list[float]]:
        """Gleichmäßig steigender Markt."""
        high  = [100.0 + i * 0.5 + 0.3 for i in range(n)]
        low   = [100.0 + i * 0.5 - 0.3 for i in range(n)]
        return high, low

    def _downtrend_data(self, n: int = 50) -> tuple[list[float], list[float]]:
        """Gleichmäßig fallender Markt."""
        high = [200.0 - i * 0.5 + 0.3 for i in range(n)]
        low  = [200.0 - i * 0.5 - 0.3 for i in range(n)]
        return high, low

    def test_basic_length(self) -> None:
        """Output-Länge gleich Input-Länge."""
        high, low = self._uptrend_data(100)
        result = parabolic_sar(high, low)
        assert len(result) == 100

    def test_all_floats(self) -> None:
        """Alle Werte sind float."""
        high, low = self._uptrend_data(50)
        result = parabolic_sar(high, low)
        assert all(isinstance(v, float) for v in result)

    def test_nonzero_after_warmup(self) -> None:
        """SAR ist nach Bar 0 nicht 0.0."""
        high, low = self._uptrend_data(50)
        result = parabolic_sar(high, low)
        assert result[1] != 0.0

    def test_uptrend_sar_below_price(self) -> None:
        """In Aufwärtstrend liegt SAR unter dem Low."""
        high, low = self._uptrend_data(60)
        result = parabolic_sar(high, low)
        # Nach einer Anlaufphase von ~5 Bars ist der Trend etabliert
        for i in range(10, 60):
            assert result[i] <= low[i], (
                f"SAR[{i}]={result[i]:.4f} sollte ≤ low[{i}]={low[i]:.4f} sein"
            )

    def test_downtrend_sar_above_price(self) -> None:
        """In Abwärtstrend liegt SAR über dem High."""
        high, low = self._downtrend_data(60)
        result = parabolic_sar(high, low)
        for i in range(10, 60):
            assert result[i] >= high[i], (
                f"SAR[{i}]={result[i]:.4f} sollte ≥ high[{i}]={high[i]:.4f} sein"
            )

    def test_empty_input(self) -> None:
        assert parabolic_sar([], []) == []

    def test_single_bar(self) -> None:
        result = parabolic_sar([105.0], [95.0])
        assert len(result) == 1
        assert result[0] == 95.0

    def test_af_max_capped(self) -> None:
        """AF darf af_max nie überschreiten — bei sehr langen Aufwärtstrends."""
        n = 200
        high = [100.0 + i for i in range(n)]
        low  = [99.0  + i for i in range(n)]
        result = parabolic_sar(high, low, af_start=0.02, af_step=0.02, af_max=0.20)
        assert len(result) == n
        # SAR sollte irgendwann konvergieren (nicht explodieren)
        assert all(math.isfinite(v) for v in result)
