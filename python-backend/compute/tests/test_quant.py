"""Tests for indicator_engine.quant — features, classifiers, CUSUM, mean-rev, order flow."""

from __future__ import annotations

import math

from indicator_engine.models import OHLCVPoint
from indicator_engine.quant import (
    calculate_alternative_bars,
    calculate_cusum,
    calculate_deflated_sharpe,
    calculate_eval_baseline,
    calculate_meanrev_momentum,
    calculate_order_flow_state,
    calculate_performance_metrics,
    calculate_signal_quality_chain,
    build_features,
    classify_signal,
    fuse_hybrid,
    monitor_bias,
)


class TestBuildFeatures:
    def test_length(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import FeatureEngineeringRequest
        req = FeatureEngineeringRequest(ohlcv=ohlcv_points_1000, period=14)
        resp = build_features(req)
        assert len(resp.features) == 999  # n-1
        assert resp.feature_names == ["ret", "sma_dev", "rsi", "vol_ratio"]

    def test_feature_keys(self, ohlcv_points_100: list[OHLCVPoint]) -> None:
        from indicator_engine.models import FeatureEngineeringRequest
        req = FeatureEngineeringRequest(ohlcv=ohlcv_points_100, period=14)
        resp = build_features(req)
        for f in resp.features:
            assert set(f.keys()) == {"ret", "sma_dev", "rsi", "vol_ratio"}


class TestClassifySignal:
    def test_buy(self) -> None:
        from indicator_engine.models import MLClassifySignalRequest
        req = MLClassifySignalRequest(features={"ret": 0.5, "sma_dev": 0.3, "rsi": 80.0, "vol_ratio": 2.0})
        resp = classify_signal(req)
        assert resp.label in ("buy", "sell", "hold")
        assert 0.0 <= resp.score <= 1.0

    def test_hold_zone(self) -> None:
        from indicator_engine.models import MLClassifySignalRequest
        req = MLClassifySignalRequest(features={"ret": 0.0, "sma_dev": 0.0, "rsi": 50.0, "vol_ratio": 1.0})
        resp = classify_signal(req)
        assert resp.label == "hold"


class TestFuseHybrid:
    def test_blend(self) -> None:
        from indicator_engine.models import HybridFusionRequest
        req = HybridFusionRequest(ml_score=0.8, rule_score=0.3, ml_weight=0.6)
        resp = fuse_hybrid(req)
        assert resp.fused_score == round(0.6 * 0.8 + 0.4 * 0.3, 6)


class TestMonitorBias:
    def test_alert_on_imbalance(self) -> None:
        from indicator_engine.models import BiasMonitoringRequest
        req = BiasMonitoringRequest(
            geographic_distribution={"US": 90, "EU": 5, "ASIA": 5},
            regime_distribution={"bull": 50, "bear": 50},
            agreement_rate=0.8,
        )
        resp = monitor_bias(req)
        assert resp.alert is True  # geo imbalance > 0.45


class TestAlternativeBars:
    def test_tick_bars(self, ohlcv_points_1000: list[OHLCVPoint]) -> None:
        from indicator_engine.models import AlternativeBarsRequest
        req = AlternativeBarsRequest(ohlcv=ohlcv_points_1000, bucketSize=50)
        resp = calculate_alternative_bars(req)
        assert len(resp.tick_bar_closes) == 20  # 1000 / 50


class TestCUSUM:
    def test_break_detection(self, closes_1000: list[float]) -> None:
        from indicator_engine.models import CUSUMRequest
        req = CUSUMRequest(closes=closes_1000, threshold=0.02)
        resp = calculate_cusum(req)
        assert isinstance(resp.break_indices, list)
        for sig in resp.break_signals:
            assert sig in ("up_break", "down_break")


class TestMeanRevMomentum:
    def test_classification(self, closes_1000: list[float]) -> None:
        from indicator_engine.models import MeanRevMomentumRequest
        req = MeanRevMomentumRequest(closes=closes_1000)
        resp = calculate_meanrev_momentum(req)
        assert resp.classification in ("mean_reverting", "momentum", "random_walk")
        assert 0.0 <= resp.hurst <= 1.0


class TestPerformanceMetrics:
    def test_basic(self) -> None:
        from indicator_engine.models import PerformanceMetricsRequest
        req = PerformanceMetricsRequest(returns=[0.01, -0.005, 0.02, -0.01, 0.015])
        resp = calculate_performance_metrics(req)
        assert resp.hit_ratio == 0.6  # 3 wins / 5
        assert resp.max_drawdown <= 0.0

    def test_all_wins(self) -> None:
        from indicator_engine.models import PerformanceMetricsRequest
        req = PerformanceMetricsRequest(returns=[0.01, 0.02, 0.03])
        resp = calculate_performance_metrics(req)
        assert resp.hit_ratio == 1.0
        assert math.isinf(resp.profit_factor)


class TestSignalQualityChain:
    def test_transition_matrix(self) -> None:
        from indicator_engine.models import SignalQualityChainRequest
        req = SignalQualityChainRequest(labels=["strong", "strong", "weak", "invalid", "strong"])
        resp = calculate_signal_quality_chain(req)
        assert "strong" in resp.transition
        assert "weak" in resp.transition


class TestOrderFlowState:
    def test_accumulation(self) -> None:
        from indicator_engine.models import OrderFlowStateRequest
        req = OrderFlowStateRequest(buy_volumes=[100, 90, 80], sell_volumes=[20, 30, 25])
        resp = calculate_order_flow_state(req)
        assert resp.dominant_state == "accumulation"

    def test_squeeze(self) -> None:
        from indicator_engine.models import OrderFlowStateRequest
        req = OrderFlowStateRequest(buy_volumes=[50, 50, 50], sell_volumes=[50, 50, 50])
        resp = calculate_order_flow_state(req)
        assert resp.dominant_state == "squeeze"


class TestDeflatedSharpe:
    def test_penalty(self) -> None:
        from indicator_engine.models import DeflatedSharpeRequest
        req = DeflatedSharpeRequest(sharpe=2.0, trials=10, sample_length=252)
        resp = calculate_deflated_sharpe(req)
        assert resp.deflated_sharpe < 2.0
        assert resp.pass_gate is True


class TestEvalBaseline:
    def test_response(self, closes_1000: list[float]) -> None:
        from indicator_engine.models import EvalBaselineRequest
        req = EvalBaselineRequest(closes=closes_1000)
        resp = calculate_eval_baseline(req)
        assert resp.regime in ("bullish", "bearish", "ranging")
        assert 0.0 <= resp.hit_ratio <= 1.0
