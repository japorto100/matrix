"""regime_weighting.py — Regime-aware signal weighting (Kaabar 2026, Ch. 1).

Kaabar's fundamental principle:
  "Bullish signals within an ascending trend have more weight than bearish signals.
   Bearish signals in a descending trend have more weight. During sideways regimes,
   both bullish and bearish signals have the same weight."

This module provides:
  - detect_regime(): determine current market regime (bullish/bearish/ranging)
  - apply_regime_weight(): adjust signal confidence based on regime alignment
  - regime_weight_patterns(): batch-apply regime weighting to PatternResponse
"""

from __future__ import annotations

from indicator_engine.models import (
    MarketRegime,
    PatternData,
    PatternDirection,
    PatternResponse,
    RegimeWeightConfig,
)
from indicator_engine.trend import ema, sma


def detect_regime(
    closes: list[float],
    adx_period: int = 14,
    sma_period: int = 50,
) -> tuple[MarketRegime, float]:
    """Detect market regime using SMA slope + simplified ADX.

    Returns (regime, confidence) where confidence is 0.0-1.0.
    Uses SMA direction for trend direction + ADX-proxy for trend strength.
    ADX > 25 = trending, ADX < 20 = ranging.
    """
    if len(closes) < max(adx_period * 2, sma_period) + 1:
        return "ranging", 0.5

    # SMA slope direction
    sma_vals = sma(closes, sma_period)
    slope_period = min(10, len(sma_vals) - 1)
    sma_slope = sma_vals[-1] - sma_vals[-1 - slope_period]

    # Simplified ADX from directional movement
    n = len(closes)
    plus_dm: list[float] = [0.0]
    minus_dm: list[float] = [0.0]
    tr_vals: list[float] = [0.0]
    for i in range(1, n):
        high_diff = closes[i] - closes[i - 1] if closes[i] > closes[i - 1] else 0.0
        low_diff = closes[i - 1] - closes[i] if closes[i - 1] > closes[i] else 0.0
        if high_diff > low_diff and high_diff > 0:
            plus_dm.append(high_diff)
            minus_dm.append(0.0)
        elif low_diff > high_diff and low_diff > 0:
            plus_dm.append(0.0)
            minus_dm.append(low_diff)
        else:
            plus_dm.append(0.0)
            minus_dm.append(0.0)
        tr_vals.append(abs(closes[i] - closes[i - 1]))

    # Wilder smoothing for DI
    smooth_plus = ema(plus_dm, adx_period * 2 - 1)
    smooth_minus = ema(minus_dm, adx_period * 2 - 1)
    smooth_tr = ema(tr_vals, adx_period * 2 - 1)

    # DX series for ADX
    dx_vals: list[float] = []
    for i in range(n):
        tr = smooth_tr[i]
        if tr < 1e-10:
            dx_vals.append(0.0)
            continue
        di_plus = 100.0 * smooth_plus[i] / tr
        di_minus = 100.0 * smooth_minus[i] / tr
        di_sum = di_plus + di_minus
        dx_vals.append(100.0 * abs(di_plus - di_minus) / di_sum if di_sum > 0 else 0.0)

    adx_vals = ema(dx_vals, adx_period * 2 - 1)
    adx = adx_vals[-1] if adx_vals else 0.0

    # Regime classification
    if adx < 20:
        return "ranging", max(0.3, 1.0 - adx / 40.0)
    elif sma_slope > 0:
        confidence = min(1.0, adx / 50.0)
        return "bullish", confidence
    elif sma_slope < 0:
        confidence = min(1.0, adx / 50.0)
        return "bearish", confidence
    else:
        return "ranging", 0.5


def apply_regime_weight(
    signal_direction: PatternDirection,
    regime: MarketRegime,
    confidence: float,
    config: RegimeWeightConfig | None = None,
) -> float:
    """Adjust signal confidence based on regime alignment.

    Aligned: bullish signal in bullish regime → boost (×1.3 default)
    Opposed: bullish signal in bearish regime → dampen (×0.7 default)
    Ranging or neutral: no change
    """
    if config is None:
        from indicator_engine.models import RegimeWeightConfig
        config = RegimeWeightConfig()

    if signal_direction == "neutral" or regime == "ranging":
        return confidence

    aligned = (
        (signal_direction == "bullish" and regime == "bullish")
        or (signal_direction == "bearish" and regime == "bearish")
    )
    opposed = (
        (signal_direction == "bullish" and regime == "bearish")
        or (signal_direction == "bearish" and regime == "bullish")
    )

    if aligned:
        return min(1.0, confidence * config.boost_aligned)
    elif opposed:
        weighted = confidence * config.dampen_opposed
        if config.mode == "filter" and weighted < config.filter_threshold:
            return 0.0  # filtered out
        return weighted
    return confidence


def regime_weight_patterns(
    response: PatternResponse,
    closes: list[float],
    config: RegimeWeightConfig | None = None,
    adx_period: int = 14,
    sma_period: int = 50,
) -> PatternResponse:
    """Batch-apply regime weighting to all patterns in a PatternResponse.

    Detects regime once, then adjusts each pattern's confidence.
    Returns a new PatternResponse with weighted patterns.
    """
    regime, _regime_conf = detect_regime(closes, adx_period, sma_period)

    weighted_patterns: list[PatternData] = []
    for p in response.patterns:
        new_confidence = apply_regime_weight(p.direction, regime, p.confidence, config)
        if new_confidence <= 0.0:
            continue  # filtered out in filter mode
        weighted_patterns.append(
            PatternData(
                type=p.type,
                direction=p.direction,
                start_time=p.start_time,
                end_time=p.end_time,
                confidence=round(new_confidence, 4),
                details={**p.details, "regime": regime, "regime_weighted": True},
            )
        )

    return PatternResponse(
        patterns=weighted_patterns,
        metadata={
            **response.metadata,
            "regime": regime,
            "regime_weighted": True,
        },
    )
