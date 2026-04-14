// regime.rs — Volatility regime detection and classification
//
// Mirrors Python: volatility.py (calculate_volatility_suite, calculate_regime, calculate_markov_regime)
// HMM regime (calculate_hmm_regime) stays Python-only — requires hmmlearn.

use crate::helper;
// All functions here are pure math — no external dependencies beyond std.

use super::oscillators::adx_components;
use super::trend::sma;

// ── Volatility Suite ────────────────────────────────────────────────────────

/// Volatility suite result — spike-weighted vol, historical vol, EWMA stddev, regime labels.
#[derive(Debug, Clone)]
pub struct VolatilitySuiteResult {
    pub spike_weighted_vol: f64,
    pub volatility_index: f64,
    pub exp_weighted_stddev: f64,
    pub volatility_regime: VolRegime,
    pub spike_weighted_regime: SwvRegime,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VolRegime {
    Compressed,
    Normal,
    Elevated,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SwvRegime {
    VeryQuiet,
    Normal,
    Elevated,
    HighVolatility,
}

/// Compute spike-weighted vol, historical vol, EW stddev, and regime labels.
///
/// Python ref: `volatility.py::calculate_volatility_suite()`.
/// Kaabar Ch.6: spike-weighted vol with z-score weighting, EWMA stddev.
pub fn volatility_suite(closes: &[f64], lookback: usize) -> VolatilitySuiteResult {
    let default = VolatilitySuiteResult {
        spike_weighted_vol: 0.0,
        volatility_index: 0.0,
        exp_weighted_stddev: 0.0,
        volatility_regime: VolRegime::Normal,
        spike_weighted_regime: SwvRegime::VeryQuiet,
    };

    if closes.len() < 2 {
        return default;
    }

    // Log returns
    let mut returns = Vec::with_capacity(closes.len() - 1);
    for i in 1..closes.len() {
        if closes[i - 1] > 0.0 && closes[i] > 0.0 {
            returns.push((closes[i] / closes[i - 1]).ln());
        }
    }
    if returns.is_empty() {
        return default;
    }

    let lb = lookback.min(returns.len());
    let recent = &returns[returns.len() - lb..];

    // Historical volatility (annualised)
    let mean_r = helper::mean(recent);
    let variance = helper::sample_variance(recent);
    let hv = variance.sqrt() * 252.0_f64.sqrt();

    // EWMA stddev — Kaabar Ch.6
    let alpha = 2.0 / (lookback as f64 + 1.0);
    let mut ewm_mean = returns[0];
    let mut ewm_var = 0.0_f64;
    for &r in &returns[1..] {
        ewm_mean = alpha * r + (1.0 - alpha) * ewm_mean;
        ewm_var = alpha * (r - ewm_mean).powi(2) + (1.0 - alpha) * ewm_var;
    }
    let ewm_std = ewm_var.max(0.0).sqrt();

    // Spike-weighted vol — Kaabar Ch.6
    let std_recent = variance.sqrt();
    let mut weighted_sq_sum = 0.0_f64;
    for &r in recent {
        let z = (r - mean_r).abs() / (std_recent + 1e-8);
        weighted_sq_sum += r * r * (1.0 + z);
    }
    let spike_vol = (weighted_sq_sum / recent.len() as f64).sqrt() * 252.0_f64.sqrt();

    // Historical median of rolling HV for regime classification
    let mut roll_hvs = Vec::new();
    for i in lb..=returns.len() {
        let start = i.saturating_sub(lb);
        let window = &returns[start..i];
        if window.len() < 2 {
            continue;
        }
        let v = helper::sample_variance(window);
        roll_hvs.push(v.sqrt() * 252.0_f64.sqrt());
    }

    const ELEVATED_ABS: f64 = 0.40;
    const COMPRESSED_ABS: f64 = 0.05;

    let hist_median = if roll_hvs.is_empty() {
        hv
    } else {
        roll_hvs.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        roll_hvs[roll_hvs.len() / 2]
    };

    let vol_regime = if hv > ELEVATED_ABS {
        VolRegime::Elevated
    } else if hv < COMPRESSED_ABS {
        VolRegime::Compressed
    } else if hv > hist_median * 1.3 {
        VolRegime::Elevated
    } else if hv < hist_median * 0.7 {
        VolRegime::Compressed
    } else {
        VolRegime::Normal
    };

    // SWV 4-tier — Kaabar Ch.6 thresholds (daily data)
    let swv_daily = if spike_vol > 0.0 {
        spike_vol / 252.0_f64.sqrt()
    } else {
        0.0
    };
    let swv_regime = if swv_daily > 0.030 {
        SwvRegime::HighVolatility
    } else if swv_daily > 0.015 {
        SwvRegime::Elevated
    } else if swv_daily > 0.005 {
        SwvRegime::Normal
    } else {
        SwvRegime::VeryQuiet
    };

    VolatilitySuiteResult {
        spike_weighted_vol: spike_vol,
        volatility_index: hv,
        exp_weighted_stddev: ewm_std,
        volatility_regime: vol_regime,
        spike_weighted_regime: swv_regime,
    }
}

// ── Rule-based Regime Detection ─────────────────────────────────────────────

/// Rule-based regime result.
#[derive(Debug, Clone)]
pub struct RegimeResult {
    pub regime: MarketRegime,
    pub sma_slope: f64,
    pub adx: f64,
    pub confidence: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MarketRegime {
    Bullish,
    Bearish,
    Ranging,
}

/// Tier-1: Rule-based regime using SMA slope + ADX.
///
/// Uses actual DI/DX calculation from `directional.rs` (not the close-only proxy
/// from Python — Rust has the real implementation with H/L/C).
///
/// For close-only data, use `regime_from_closes()` below.
///
/// Python ref: `volatility.py::calculate_regime()`.
pub fn regime_detect(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    sma_period: usize,
    adx_period: usize,
) -> RegimeResult {
    let n = closes.len();
    if n < 10 {
        return RegimeResult {
            regime: MarketRegime::Ranging,
            sma_slope: 0.0,
            adx: 0.0,
            confidence: 0.3,
        };
    }

    let sma_vals = sma(closes, sma_period.min(n - 1));

    // SMA slope: (sma[-1] - sma[-6]) / |sma[-6]|
    let slope = if sma_vals.len() >= 6 {
        let ref_val = sma_vals[sma_vals.len() - 6];
        if ref_val.abs() > 1e-10 {
            (sma_vals[sma_vals.len() - 1] - ref_val) / ref_val.abs()
        } else {
            0.0
        }
    } else {
        0.0
    };

    // ADX from oscillators module (Wilder-smoothed, proper H/L/C calculation)
    let (adx_vals, _, _) = adx_components(highs, lows, closes, adx_period);
    let adx_val = *adx_vals.last().unwrap_or(&0.0);

    let (regime, confidence) = if slope > 0.001 && adx_val > 25.0 {
        let conf = (0.5 + slope * 50.0 + (adx_val - 25.0) / 100.0).min(1.0);
        (MarketRegime::Bullish, conf)
    } else if slope < -0.001 && adx_val > 25.0 {
        let conf = (0.5 + slope.abs() * 50.0 + (adx_val - 25.0) / 100.0).min(1.0);
        (MarketRegime::Bearish, conf)
    } else {
        let conf = (1.0 - adx_val / 100.0).max(0.3);
        (MarketRegime::Ranging, conf)
    };

    RegimeResult {
        regime,
        sma_slope: slope,
        adx: adx_val,
        confidence: confidence.clamp(0.0, 1.0),
    }
}

// ── Markov Regime ───────────────────────────────────────────────────────────

/// Markov regime result.
#[derive(Debug, Clone)]
pub struct MarkovRegimeResult {
    pub current_regime: MarketRegime,
    /// Transition probabilities from current state: [bullish, bearish, ranging]
    pub transition_probs: [f64; 3],
    pub expected_duration: f64,
    pub shift_probability: f64,
    /// Stationary distribution: [bullish, bearish, ranging]
    pub stationary_distribution: [f64; 3],
}

/// Tier-2: Markov transition matrix from rolling rule-based regimes.
///
/// Splits the close series into segments, classifies each via `regime_detect`,
/// then builds a transition matrix + stationary distribution via power iteration.
///
/// Python ref: `volatility.py::calculate_markov_regime()`.
pub fn markov_regime(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    lookback: usize,
) -> MarkovRegimeResult {
    let n = closes.len();
    let step = (n / lookback).max(1);

    // Build segment labels
    let mut labels: Vec<usize> = Vec::new(); // 0=bullish, 1=bearish, 2=ranging
    let mut i = 0;
    while i + step < n {
        let end = (i + step + 1).min(n);
        if end - i < 20 {
            i += step;
            continue;
        }
        let result = regime_detect(
            &highs[i..end],
            &lows[i..end],
            &closes[i..end],
            50.min(end - i - 1),
            14,
        );
        labels.push(match result.regime {
            MarketRegime::Bullish => 0,
            MarketRegime::Bearish => 1,
            MarketRegime::Ranging => 2,
        });
        i += step;
    }

    let uniform = [1.0 / 3.0; 3];
    if labels.is_empty() {
        return MarkovRegimeResult {
            current_regime: MarketRegime::Ranging,
            transition_probs: uniform,
            expected_duration: 1.0,
            shift_probability: 0.5,
            stationary_distribution: uniform,
        };
    }

    // Build 3x3 transition count matrix
    let mut counts = [[0u32; 3]; 3];
    for w in labels.windows(2) {
        counts[w[0]][w[1]] += 1;
    }

    // Normalise to probabilities
    let mut trans = [[1.0 / 3.0; 3]; 3];
    for s in 0..3 {
        let total: u32 = counts[s].iter().sum();
        if total > 0 {
            for t in 0..3 {
                trans[s][t] = counts[s][t] as f64 / total as f64;
            }
        }
    }

    let current_idx = *labels.last().unwrap_or(&2);
    let p_same = trans[current_idx][current_idx];
    let expected_dur = if p_same < 1.0 {
        1.0 / (1.0 - p_same)
    } else {
        999.0
    };
    let shift_prob = 1.0 - p_same;

    // Stationary distribution via power iteration (200 steps)
    let mut dist = [1.0 / 3.0; 3];
    for _ in 0..200 {
        let mut new_dist = [0.0; 3];
        for s in 0..3 {
            for t in 0..3 {
                new_dist[t] += dist[s] * trans[s][t];
            }
        }
        dist = new_dist;
    }

    let current_regime = match current_idx {
        0 => MarketRegime::Bullish,
        1 => MarketRegime::Bearish,
        _ => MarketRegime::Ranging,
    };

    MarkovRegimeResult {
        current_regime,
        transition_probs: trans[current_idx],
        expected_duration: expected_dur,
        shift_probability: shift_prob,
        stationary_distribution: dist,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    fn synth_trending_up(n: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
        let mut h = Vec::with_capacity(n);
        let mut l = Vec::with_capacity(n);
        let mut c = Vec::with_capacity(n);
        for i in 0..n {
            // Strong uptrend: +2.0 per bar with narrow range → high DX
            let base = 100.0 + i as f64 * 2.0;
            h.push(base + 1.0);
            l.push(base - 1.0);
            c.push(base);
        }
        (h, l, c)
    }

    fn synth_sideways(n: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
        let mut h = Vec::with_capacity(n);
        let mut l = Vec::with_capacity(n);
        let mut c = Vec::with_capacity(n);
        for i in 0..n {
            let base = 100.0 + (i as f64 * 0.5).sin() * 2.0;
            h.push(base + 1.0);
            l.push(base - 1.0);
            c.push(base);
        }
        (h, l, c)
    }

    // ── Volatility Suite ──────────────────────────────────────────────────

    #[test]
    fn vol_suite_basic() {
        let closes: Vec<f64> = (0..100).map(|i| 100.0 + (i as f64 * 0.1).sin() * 5.0).collect();
        let result = volatility_suite(&closes, 20);
        assert!(result.spike_weighted_vol >= 0.0);
        assert!(result.volatility_index >= 0.0);
        assert!(result.exp_weighted_stddev >= 0.0);
    }

    #[test]
    fn vol_suite_short_input() {
        let result = volatility_suite(&[100.0], 20);
        assert_abs_diff_eq!(result.spike_weighted_vol, 0.0, epsilon = 1e-9);
        assert_eq!(result.volatility_regime, VolRegime::Normal);
        assert_eq!(result.spike_weighted_regime, SwvRegime::VeryQuiet);
    }

    #[test]
    fn vol_suite_constant_prices() {
        let closes = vec![100.0; 50];
        let result = volatility_suite(&closes, 20);
        // Constant prices → zero returns → zero vol
        assert_abs_diff_eq!(result.volatility_index, 0.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result.spike_weighted_vol, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn vol_suite_high_vol_regime() {
        // Large swings → high vol
        let mut closes = Vec::with_capacity(100);
        for i in 0..100 {
            closes.push(if i % 2 == 0 { 150.0 } else { 50.0 });
        }
        let result = volatility_suite(&closes, 20);
        assert_eq!(result.volatility_regime, VolRegime::Elevated);
    }

    // ── Rule-based Regime ─────────────────────────────────────────────────

    #[test]
    fn regime_detect_trending_up() {
        let (h, l, c) = synth_trending_up(100);
        let result = regime_detect(&h, &l, &c, 50, 14);
        assert_eq!(result.regime, MarketRegime::Bullish);
        assert!(result.sma_slope > 0.0);
        assert!(result.confidence > 0.3);
    }

    #[test]
    fn regime_detect_short_input() {
        let result = regime_detect(&[100.0; 5], &[99.0; 5], &[99.5; 5], 50, 14);
        assert_eq!(result.regime, MarketRegime::Ranging);
        assert_abs_diff_eq!(result.confidence, 0.3, epsilon = 1e-9);
    }

    // ── Markov Regime ─────────────────────────────────────────────────────

    #[test]
    fn markov_transition_probs_sum_to_one() {
        let (h, l, c) = synth_trending_up(200);
        let result = markov_regime(&h, &l, &c, 20);
        let sum: f64 = result.transition_probs.iter().sum();
        assert_abs_diff_eq!(sum, 1.0, epsilon = 1e-6);
    }

    #[test]
    fn markov_stationary_sums_to_one() {
        let (h, l, c) = synth_sideways(200);
        let result = markov_regime(&h, &l, &c, 20);
        let sum: f64 = result.stationary_distribution.iter().sum();
        assert_abs_diff_eq!(sum, 1.0, epsilon = 1e-6);
    }

    #[test]
    fn markov_shift_probability_bounded() {
        let (h, l, c) = synth_trending_up(200);
        let result = markov_regime(&h, &l, &c, 20);
        assert!(result.shift_probability >= 0.0 && result.shift_probability <= 1.0);
        assert!(result.expected_duration >= 1.0);
    }

    #[test]
    fn markov_short_input() {
        let result = markov_regime(&[100.0; 10], &[99.0; 10], &[99.5; 10], 20);
        assert_eq!(result.current_regime, MarketRegime::Ranging);
    }
}
