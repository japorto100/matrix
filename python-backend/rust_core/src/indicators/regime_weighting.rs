// regime_weighting.rs — Regime-aware signal weighting (Kaabar 2026, Ch. 1)
//
// Mirrors Python: indicator_engine/regime_weighting.py
// Dependencies: trend (ema, sma)
//
// Functions:
//   detect_regime — market regime (bullish/bearish/ranging) via ADX + SMA
//   apply_regime_weight — adjust signal confidence based on regime alignment
//   regime_weight_patterns — batch-apply regime weighting to pattern results

use super::patterns::{PatternData, PatternDirection, PatternResult};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// Market regime classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MarketRegime {
    Bullish,
    Bearish,
    Ranging,
}

/// Configuration for regime weighting.
pub struct RegimeWeightConfig {
    /// Multiplier for aligned signals (default 1.3)
    pub boost_aligned: f64,
    /// Multiplier for opposed signals (default 0.7)
    pub dampen_opposed: f64,
    /// If true, filter out opposed signals below threshold
    pub filter_mode: bool,
    /// Threshold for filtering (default 0.3)
    pub filter_threshold: f64,
}

impl Default for RegimeWeightConfig {
    fn default() -> Self {
        Self {
            boost_aligned: 1.3,
            dampen_opposed: 0.7,
            filter_mode: false,
            filter_threshold: 0.3,
        }
    }
}

// ---------------------------------------------------------------------------
// detect_regime
// ---------------------------------------------------------------------------

/// Detect market regime using SMA slope + simplified ADX.
///
/// Returns (regime, confidence) where confidence is 0.0–1.0.
/// Uses SMA direction for trend direction + ADX-proxy for trend strength.
/// ADX > 25 = trending, ADX < 20 = ranging.
pub fn detect_regime(
    closes: &[f64],
    adx_period: usize,
    sma_period: usize,
) -> (MarketRegime, f64) {
    let n = closes.len();
    let min_len = (adx_period * 2).max(sma_period) + 1;
    if n < min_len {
        return (MarketRegime::Ranging, 0.5);
    }

    // SMA slope direction
    let sma_vals = super::trend::sma(closes, sma_period);
    let slope_period = 10.min(sma_vals.len() - 1);
    let last = sma_vals.len() - 1;
    let sma_slope = sma_vals[last] - sma_vals[last - slope_period];

    // Simplified ADX from directional movement (close-to-close)
    let mut plus_dm = vec![0.0; n];
    let mut minus_dm = vec![0.0; n];
    let mut tr_vals = vec![0.0; n];
    for i in 1..n {
        let high_diff = if closes[i] > closes[i - 1] { closes[i] - closes[i - 1] } else { 0.0 };
        let low_diff = if closes[i - 1] > closes[i] { closes[i - 1] - closes[i] } else { 0.0 };
        if high_diff > low_diff && high_diff > 0.0 {
            plus_dm[i] = high_diff;
        } else if low_diff > high_diff && low_diff > 0.0 {
            minus_dm[i] = low_diff;
        }
        tr_vals[i] = (closes[i] - closes[i - 1]).abs();
    }

    // Wilder smoothing (EMA with period = 2*adx_period - 1)
    let smooth_period = adx_period * 2 - 1;
    let smooth_plus = super::trend::ema(&plus_dm, smooth_period);
    let smooth_minus = super::trend::ema(&minus_dm, smooth_period);
    let smooth_tr = super::trend::ema(&tr_vals, smooth_period);

    // DX series for ADX
    let mut dx_vals = vec![0.0; n];
    for i in 0..n {
        let tr = smooth_tr[i];
        if tr < 1e-10 {
            continue;
        }
        let di_plus = 100.0 * smooth_plus[i] / tr;
        let di_minus = 100.0 * smooth_minus[i] / tr;
        let di_sum = di_plus + di_minus;
        if di_sum > 0.0 {
            dx_vals[i] = 100.0 * (di_plus - di_minus).abs() / di_sum;
        }
    }

    let adx_vals = super::trend::ema(&dx_vals, smooth_period);
    let adx = *adx_vals.last().unwrap_or(&0.0);

    // Regime classification
    if adx < 20.0 {
        let conf = (1.0 - adx / 40.0).max(0.3);
        (MarketRegime::Ranging, conf)
    } else if sma_slope > 0.0 {
        let conf = (adx / 50.0).min(1.0);
        (MarketRegime::Bullish, conf)
    } else if sma_slope < 0.0 {
        let conf = (adx / 50.0).min(1.0);
        (MarketRegime::Bearish, conf)
    } else {
        (MarketRegime::Ranging, 0.5)
    }
}

// ---------------------------------------------------------------------------
// apply_regime_weight
// ---------------------------------------------------------------------------

/// Adjust signal confidence based on regime alignment.
///
/// Aligned: bullish signal in bullish regime → boost (×1.3 default)
/// Opposed: bullish signal in bearish regime → dampen (×0.7 default)
/// Ranging or neutral: no change
pub fn apply_regime_weight(
    direction: PatternDirection,
    regime: MarketRegime,
    confidence: f64,
    config: &RegimeWeightConfig,
) -> f64 {
    if direction == PatternDirection::Neutral || regime == MarketRegime::Ranging {
        return confidence;
    }

    let aligned = matches!(
        (direction, regime),
        (PatternDirection::Bullish, MarketRegime::Bullish)
            | (PatternDirection::Bearish, MarketRegime::Bearish)
    );
    let opposed = matches!(
        (direction, regime),
        (PatternDirection::Bullish, MarketRegime::Bearish)
            | (PatternDirection::Bearish, MarketRegime::Bullish)
    );

    if aligned {
        (confidence * config.boost_aligned).min(1.0)
    } else if opposed {
        let weighted = confidence * config.dampen_opposed;
        if config.filter_mode && weighted < config.filter_threshold {
            0.0 // filtered out
        } else {
            weighted
        }
    } else {
        confidence
    }
}

// ---------------------------------------------------------------------------
// regime_weight_patterns
// ---------------------------------------------------------------------------

/// Batch-apply regime weighting to all patterns in a PatternResult.
///
/// Detects regime once, then adjusts each pattern's confidence.
/// Patterns filtered out (confidence → 0.0) are removed.
pub fn regime_weight_patterns(
    result: &PatternResult,
    closes: &[f64],
    config: Option<&RegimeWeightConfig>,
    adx_period: usize,
    sma_period: usize,
) -> PatternResult {
    let default_config = RegimeWeightConfig::default();
    let cfg = config.unwrap_or(&default_config);
    let (regime, _regime_conf) = detect_regime(closes, adx_period, sma_period);

    let weighted_patterns: Vec<PatternData> = result
        .patterns
        .iter()
        .filter_map(|p| {
            let new_conf = apply_regime_weight(p.direction, regime, p.confidence, cfg);
            if new_conf <= 0.0 {
                None // filtered out
            } else {
                let mut details = p.details.clone();
                details.push(("regime_weighted", 1.0));
                Some(PatternData {
                    pattern_type: p.pattern_type,
                    direction: p.direction,
                    start_idx: p.start_idx,
                    end_idx: p.end_idx,
                    confidence: (new_conf * 10000.0).round() / 10000.0, // round to 4 decimals
                    details,
                })
            }
        })
        .collect();

    PatternResult {
        scanned_bars: result.scanned_bars,
        patterns: weighted_patterns,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_uptrend(n: usize) -> Vec<f64> {
        (0..n).map(|i| 100.0 + i as f64 * 2.0).collect()
    }

    fn make_downtrend(n: usize) -> Vec<f64> {
        (0..n).map(|i| 200.0 - i as f64 * 2.0).collect()
    }

    fn make_flat(n: usize) -> Vec<f64> {
        vec![100.0; n]
    }

    #[test]
    fn test_detect_regime_uptrend() {
        let closes = make_uptrend(100);
        let (regime, conf) = detect_regime(&closes, 14, 50);
        assert_eq!(regime, MarketRegime::Bullish);
        assert!(conf > 0.0);
    }

    #[test]
    fn test_detect_regime_downtrend() {
        let closes = make_downtrend(100);
        let (regime, conf) = detect_regime(&closes, 14, 50);
        assert_eq!(regime, MarketRegime::Bearish);
        assert!(conf > 0.0);
    }

    #[test]
    fn test_detect_regime_flat_is_ranging() {
        let closes = make_flat(100);
        let (regime, _) = detect_regime(&closes, 14, 50);
        assert_eq!(regime, MarketRegime::Ranging);
    }

    #[test]
    fn test_detect_regime_short_input() {
        let closes = vec![1.0, 2.0, 3.0];
        let (regime, conf) = detect_regime(&closes, 14, 50);
        assert_eq!(regime, MarketRegime::Ranging);
        assert_eq!(conf, 0.5);
    }

    #[test]
    fn test_apply_weight_aligned_boost() {
        let config = RegimeWeightConfig::default();
        let result = apply_regime_weight(
            PatternDirection::Bullish,
            MarketRegime::Bullish,
            0.7,
            &config,
        );
        assert!((result - 0.91).abs() < 0.01); // 0.7 * 1.3 = 0.91
    }

    #[test]
    fn test_apply_weight_opposed_dampen() {
        let config = RegimeWeightConfig::default();
        let result = apply_regime_weight(
            PatternDirection::Bullish,
            MarketRegime::Bearish,
            0.7,
            &config,
        );
        assert!((result - 0.49).abs() < 0.01); // 0.7 * 0.7 = 0.49
    }

    #[test]
    fn test_apply_weight_neutral_unchanged() {
        let config = RegimeWeightConfig::default();
        let result = apply_regime_weight(
            PatternDirection::Neutral,
            MarketRegime::Bullish,
            0.65,
            &config,
        );
        assert_eq!(result, 0.65);
    }

    #[test]
    fn test_apply_weight_ranging_unchanged() {
        let config = RegimeWeightConfig::default();
        let result = apply_regime_weight(
            PatternDirection::Bullish,
            MarketRegime::Ranging,
            0.65,
            &config,
        );
        assert_eq!(result, 0.65);
    }

    #[test]
    fn test_apply_weight_filter_mode() {
        let config = RegimeWeightConfig {
            filter_mode: true,
            filter_threshold: 0.3,
            dampen_opposed: 0.3,
            ..Default::default()
        };
        // 0.5 * 0.3 = 0.15 < 0.3 threshold → filtered
        let result = apply_regime_weight(
            PatternDirection::Bullish,
            MarketRegime::Bearish,
            0.5,
            &config,
        );
        assert_eq!(result, 0.0);
    }

    #[test]
    fn test_regime_weight_patterns_basic() {
        let closes = make_uptrend(100);
        let input = PatternResult {
            scanned_bars: 100,
            patterns: vec![
                PatternData {
                    pattern_type: "test_bull",
                    direction: PatternDirection::Bullish,
                    start_idx: 50,
                    end_idx: 55,
                    confidence: 0.70,
                    details: vec![],
                },
                PatternData {
                    pattern_type: "test_bear",
                    direction: PatternDirection::Bearish,
                    start_idx: 60,
                    end_idx: 65,
                    confidence: 0.70,
                    details: vec![],
                },
            ],
        };
        let result = regime_weight_patterns(&input, &closes, None, 14, 50);
        assert_eq!(result.patterns.len(), 2);
        // In uptrend: bullish should be boosted, bearish dampened
        let bull_conf = result.patterns[0].confidence;
        let bear_conf = result.patterns[1].confidence;
        assert!(bull_conf > 0.70, "bullish should be boosted: {bull_conf}");
        assert!(bear_conf < 0.70, "bearish should be dampened: {bear_conf}");
    }
}
