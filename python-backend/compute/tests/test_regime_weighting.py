"""Tests for indicator_engine.regime_weighting — regime detection + signal weighting."""

from __future__ import annotations

from indicator_engine.models import (
    PatternData,
    PatternResponse,
    RegimeWeightConfig,
)
from indicator_engine.regime_weighting import (
    apply_regime_weight,
    detect_regime,
    regime_weight_patterns,
)


class TestDetectRegime:
    def test_returns_valid_regime(self, closes_1000: list[float]) -> None:
        regime, confidence = detect_regime(closes_1000)
        assert regime in ("bullish", "bearish", "ranging")
        assert 0.0 <= confidence <= 1.0

    def test_short_input_defaults_ranging(self) -> None:
        regime, confidence = detect_regime([100.0] * 10)
        assert regime == "ranging"


class TestApplyRegimeWeight:
    def test_aligned_boosts(self) -> None:
        result = apply_regime_weight("bullish", "bullish", 0.7)
        assert result > 0.7  # boosted

    def test_opposed_dampens(self) -> None:
        result = apply_regime_weight("bullish", "bearish", 0.7)
        assert result < 0.7  # dampened

    def test_neutral_unchanged(self) -> None:
        result = apply_regime_weight("neutral", "bullish", 0.7)
        assert result == 0.7

    def test_ranging_unchanged(self) -> None:
        result = apply_regime_weight("bullish", "ranging", 0.7)
        assert result == 0.7

    def test_filter_mode(self) -> None:
        config = RegimeWeightConfig(mode="filter", dampen_opposed=0.3, filter_threshold=0.25)
        result = apply_regime_weight("bullish", "bearish", 0.5, config)
        # 0.5 * 0.3 = 0.15 < threshold 0.25 → filtered to 0.0
        assert result == 0.0

    def test_capped_at_1(self) -> None:
        result = apply_regime_weight("bullish", "bullish", 0.95)
        assert result <= 1.0


class TestRegimeWeightPatterns:
    def test_batch_weighting(self, closes_1000: list[float]) -> None:
        patterns = [
            PatternData(type="hammer", direction="bullish", start_time=1, end_time=2, confidence=0.7),
            PatternData(type="shooting_star", direction="bearish", start_time=3, end_time=4, confidence=0.6),
            PatternData(type="doji", direction="neutral", start_time=5, end_time=6, confidence=0.5),
        ]
        response = PatternResponse(patterns=patterns, metadata={"scanned_bars": 100})
        weighted = regime_weight_patterns(response, closes_1000)
        assert weighted.metadata["regime_weighted"] is True
        assert weighted.metadata["regime"] in ("bullish", "bearish", "ranging")
        # All patterns should still exist (no filter mode)
        assert len(weighted.patterns) >= 1
        for p in weighted.patterns:
            assert p.details.get("regime_weighted") is True
