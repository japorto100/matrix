// rainbow.rs — Kaabar Rainbow Collection + proprietary patterns (Kaabar 2026, Ch. 3/7/10)
//
// Mirrors Python: indicator_engine/rainbow.py
// Dependencies: stats::slope, oscillators::rsi, trend::hma, volatility::{e_bollinger_bands, atr}
//
// 7 Rainbow indicators each return Vec<f64>: 1.0 bullish, -1.0 bearish, 0.0 neutral.
// Signals emitted at i+1 (next bar), matching book convention.

const FIB_LAGS: [usize; 7] = [1, 2, 3, 5, 8, 13, 21];

// ---------------------------------------------------------------------------
// 7 Rainbow indicators (Kaabar 2026, Ch. 3)
// ---------------------------------------------------------------------------

/// Red: EMA-Bollinger extreme-duration reversal (min 3 periods outside band).
pub fn red(closes: &[f64], period: usize, num_std: f64) -> Vec<f64> {
    let (upper, middle, lower) = super::volatility::e_bollinger_bands(closes, period, num_std);
    let n = closes.len();
    let mut out = vec![0.0; n];
    if n < 5 {
        return out;
    }
    for i in 3..(n - 1) {
        let (c, c1, c2, c3) = (closes[i], closes[i - 1], closes[i - 2], closes[i - 3]);
        if c > lower[i] && c < middle[i]
            && c1 < lower[i - 1] && c2 < lower[i - 2] && c3 < lower[i - 3]
        {
            out[i + 1] = 1.0;
        } else if c < upper[i] && c > middle[i]
            && c1 > upper[i - 1] && c2 > upper[i - 2] && c3 > upper[i - 3]
        {
            out[i + 1] = -1.0;
        }
    }
    out
}

/// Orange: RSI extreme-duration reversal (min 5 bars in oversold/overbought zone).
pub fn orange(closes: &[f64], rsi_period: usize, lower: f64, upper: f64) -> Vec<f64> {
    let rs = super::oscillators::rsi(closes, rsi_period);
    let n = closes.len();
    let mut out = vec![0.0; n];
    if n < 7 {
        return out;
    }
    for i in 5..(n - 1) {
        let r = rs[i];
        if r > lower && r < 50.0 && (1..=5).all(|k| rs[i - k] < lower) {
            out[i + 1] = 1.0;
        } else if r < upper && r > 50.0 && (1..=5).all(|k| rs[i - k] > upper) {
            out[i + 1] = -1.0;
        }
    }
    out
}

/// Yellow: RSI-slope vs price-slope divergence while RSI is in extreme zone.
pub fn yellow(
    closes: &[f64],
    rsi_period: usize,
    slope_period: usize,
    lower: f64,
    upper: f64,
) -> Vec<f64> {
    let rs = super::oscillators::rsi(closes, rsi_period);
    let sl_rsi = super::stats::slope(&rs, slope_period);
    let sl_close = super::stats::slope(closes, slope_period);
    let n = closes.len();
    let mut out = vec![0.0; n];
    let start = slope_period + 1;
    if n <= start + 1 {
        return out;
    }
    for i in start..(n - 1) {
        if sl_rsi[i] > 0.0 && sl_rsi[i - 1] < 0.0
            && sl_close[i] < 0.0 && sl_close[i - 1] < 0.0
            && rs[i] < lower
        {
            out[i + 1] = 1.0;
        } else if sl_rsi[i] < 0.0 && sl_rsi[i - 1] > 0.0
            && sl_close[i] > 0.0 && sl_close[i - 1] > 0.0
            && rs[i] > upper
        {
            out[i + 1] = -1.0;
        }
    }
    out
}

/// Green: RSI-slope zero-cross while RSI is in extreme zone.
pub fn green(
    closes: &[f64],
    rsi_period: usize,
    slope_period: usize,
    lower: f64,
    upper: f64,
) -> Vec<f64> {
    let rs = super::oscillators::rsi(closes, rsi_period);
    let sl_rsi = super::stats::slope(&rs, slope_period);
    let n = closes.len();
    let mut out = vec![0.0; n];
    let start = slope_period + 1;
    if n <= start + 1 {
        return out;
    }
    for i in start..(n - 1) {
        if sl_rsi[i] > 0.0 && sl_rsi[i - 1] < 0.0 && rs[i] < lower {
            out[i + 1] = 1.0;
        } else if sl_rsi[i] < 0.0 && sl_rsi[i - 1] > 0.0 && rs[i] > upper {
            out[i + 1] = -1.0;
        }
    }
    out
}

/// Blue: RSI applied to price-slope — crosses into 30-35/65-70 with confirming H/L.
pub fn blue(
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
    rsi_period: usize,
    slope_period: usize,
    lower: f64,
    upper: f64,
    margin: f64,
) -> Vec<f64> {
    let sl_close = super::stats::slope(closes, slope_period);
    let rs_slope = super::oscillators::rsi(&sl_close, rsi_period);
    let n = closes.len();
    let mut out = vec![0.0; n];
    let start = slope_period + rsi_period + 1;
    if n <= start + 1 {
        return out;
    }
    for i in start..(n - 1) {
        let (r, r1) = (rs_slope[i], rs_slope[i - 1]);
        if r > lower && r < lower + margin && r1 < lower && lows[i] < lows[i - 1] {
            out[i + 1] = 1.0;
        } else if r < upper && r > upper - margin && r1 > upper && highs[i] > highs[i - 1] {
            out[i + 1] = -1.0;
        }
    }
    out
}

/// Indigo: Fibonacci-indexed consecutive comparison.
pub fn indigo(closes: &[f64]) -> Vec<f64> {
    let fib_ext: [usize; 8] = [1, 2, 3, 5, 8, 13, 21, 34];
    let min_i = fib_ext[7] + 1; // 35
    let n = closes.len();
    let mut out = vec![0.0; n];
    if n <= min_i + 1 {
        return out;
    }
    for i in min_i..(n - 1) {
        if closes[i] > closes[i - 1]
            && (0..7).all(|k| closes[i - FIB_LAGS[k]] < closes[i - fib_ext[k + 1]])
        {
            out[i + 1] = 1.0;
        } else if closes[i] < closes[i - 1]
            && (0..7).all(|k| closes[i - FIB_LAGS[k]] > closes[i - fib_ext[k + 1]])
        {
            out[i + 1] = -1.0;
        }
    }
    out
}

/// Violet: HMA cross with Fibonacci-indexed confirmation bars.
pub fn violet(closes: &[f64], hma_period: usize) -> Vec<f64> {
    let hma_vals = super::trend::hma(closes, hma_period);
    let min_i = FIB_LAGS[6] + 1; // 22
    let n = closes.len();
    let mut out = vec![0.0; n];
    let start = hma_period + min_i;
    if n <= start + 1 {
        return out;
    }
    for i in start..(n - 1) {
        if closes[i] > hma_vals[i]
            && FIB_LAGS.iter().all(|&lag| closes[i - lag] < hma_vals[i - lag])
        {
            out[i + 1] = 1.0;
        } else if closes[i] < hma_vals[i]
            && FIB_LAGS.iter().all(|&lag| closes[i - lag] > hma_vals[i - lag])
        {
            out[i + 1] = -1.0;
        }
    }
    out
}

// ---------------------------------------------------------------------------
// Aggregate endpoints
// ---------------------------------------------------------------------------

/// Result type for rainbow_collection: all 7 signal arrays.
pub struct RainbowCollection {
    pub red: Vec<f64>,
    pub orange: Vec<f64>,
    pub yellow: Vec<f64>,
    pub green: Vec<f64>,
    pub blue: Vec<f64>,
    pub indigo: Vec<f64>,
    pub violet: Vec<f64>,
}

/// Compute all 7 Rainbow indicators (Kaabar 2026, Ch. 3).
pub fn calculate_rainbow_collection(
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
) -> RainbowCollection {
    RainbowCollection {
        red: red(closes, 20, 2.0),
        orange: orange(closes, 8, 35.0, 65.0),
        yellow: yellow(closes, 14, 14, 35.0, 65.0),
        green: green(closes, 14, 14, 35.0, 65.0),
        blue: blue(closes, highs, lows, 5, 5, 30.0, 70.0, 5.0),
        indigo: indigo(closes),
        violet: violet(closes, 20),
    }
}

/// Rainbow Confluence Detection (Kaabar Ch.3).
///
/// Scans a ±window bar range across all 7 Rainbow indicators.
/// If >= min_count fire in the same direction within that window,
/// emits the count as signal strength (positive=bullish, negative=bearish).
pub fn calculate_rainbow_confluence(
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
    window: usize,
    min_count: i32,
) -> Vec<f64> {
    let rc = calculate_rainbow_collection(closes, highs, lows);
    let arrays: [&[f64]; 7] = [
        &rc.red, &rc.orange, &rc.yellow, &rc.green, &rc.blue, &rc.indigo, &rc.violet,
    ];
    let n = closes.len();
    let mut composite = vec![0.0; n];

    for i in 0..n {
        let mut bull_count: i32 = 0;
        let mut bear_count: i32 = 0;
        let lo_idx = if i > window { i - window } else { 0 };
        let hi_idx = (i + window + 1).min(n);
        for arr in &arrays {
            if (lo_idx..hi_idx).any(|j| arr[j] == 1.0) {
                bull_count += 1;
            }
            if (lo_idx..hi_idx).any(|j| arr[j] == -1.0) {
                bear_count += 1;
            }
        }
        if bull_count >= min_count {
            composite[i] = bull_count as f64;
        } else if bear_count >= min_count {
            composite[i] = -(bear_count as f64);
        }
    }
    composite
}

/// Rainbow Composite Score (Kaabar Ch.3): average of all 7 indicators.
pub fn rainbow_composite_score(
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
) -> Vec<f64> {
    let rc = calculate_rainbow_collection(closes, highs, lows);
    let n = closes.len();
    (0..n)
        .map(|i| {
            (rc.red[i] + rc.orange[i] + rc.yellow[i] + rc.green[i]
                + rc.blue[i] + rc.indigo[i] + rc.violet[i])
                / 7.0
        })
        .collect()
}

// ---------------------------------------------------------------------------
// R-Pattern (Kaabar 2026, Ch. 7)
// ---------------------------------------------------------------------------

/// Detect R-Pattern reversal signals (Kaabar 2026, Ch. 7).
///
/// Returns Vec<f64>: 1.0 bullish, -1.0 bearish, 0.0 neutral.
/// Signal emitted at i+1 (next-bar convention).
pub fn calculate_r_pattern(
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
    rsi_period: usize,
) -> Vec<f64> {
    let rs = super::oscillators::rsi(closes, rsi_period);
    let n = closes.len();
    let mut signals = vec![0.0; n];
    if n < 5 {
        return signals;
    }
    for i in 3..(n - 1) {
        // Bullish R
        if lows[i] > lows[i - 1] && lows[i - 1] > lows[i - 2] && lows[i - 2] < lows[i - 3]
            && closes[i] > closes[i - 1] && closes[i - 1] > closes[i - 2] && closes[i - 2] > closes[i - 3]
            && rs[i] < 50.0
        {
            signals[i + 1] = 1.0;
        }
        // Bearish R
        else if highs[i] < highs[i - 1] && highs[i - 1] < highs[i - 2] && highs[i - 2] > highs[i - 3]
            && closes[i] < closes[i - 1] && closes[i - 1] < closes[i - 2] && closes[i - 2] < closes[i - 3]
            && rs[i] > 50.0
        {
            signals[i + 1] = -1.0;
        }
    }
    signals
}

// ---------------------------------------------------------------------------
// Gap-Pattern (Kaabar 2026, Ch. 10)
// ---------------------------------------------------------------------------

/// Detect tradeable gap patterns with ATR-based size filter (Kaabar 2026, Ch. 10).
///
/// Returns Vec<f64>: 1.0 gap-down (bullish fade), -1.0 gap-up (bearish fade), 0.0 no gap.
pub fn calculate_gap_pattern(
    opens: &[f64],
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    atr_period: usize,
    min_size: f64,
) -> Vec<f64> {
    let atr_vals = super::volatility::atr(highs, lows, closes, atr_period);
    let n = opens.len().min(closes.len());
    let mut signals = vec![0.0; n];

    for i in 1..n {
        let prev_close = closes[i - 1];
        let cur_open = opens[i];
        let gap_size = (cur_open - prev_close).abs();
        let min_gap = atr_vals[i - 1] * min_size;

        if gap_size <= min_gap {
            continue;
        }

        if cur_open < prev_close {
            signals[i] = 1.0; // gap down → bullish fade
        } else if cur_open > prev_close {
            signals[i] = -1.0; // gap up → bearish fade
        }
    }
    signals
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_trending_data(n: usize, start: f64, step: f64) -> Vec<f64> {
        (0..n).map(|i| start + step * i as f64).collect()
    }

    #[test]
    fn test_red_output_length() {
        let closes = make_trending_data(50, 100.0, 0.5);
        let result = red(&closes, 20, 2.0);
        assert_eq!(result.len(), 50);
    }

    #[test]
    fn test_orange_output_length() {
        let closes = make_trending_data(50, 100.0, 0.5);
        let result = orange(&closes, 8, 35.0, 65.0);
        assert_eq!(result.len(), 50);
    }

    #[test]
    fn test_indigo_short_input_no_panic() {
        let closes = vec![1.0, 2.0, 3.0];
        let result = indigo(&closes);
        assert_eq!(result.len(), 3);
        assert!(result.iter().all(|&v| v == 0.0));
    }

    #[test]
    fn test_violet_short_input_no_panic() {
        let closes = vec![1.0, 2.0, 3.0];
        let result = violet(&closes, 20);
        assert_eq!(result.len(), 3);
    }

    #[test]
    fn test_rainbow_collection_runs() {
        let n = 100;
        let closes = make_trending_data(n, 100.0, 0.3);
        let highs: Vec<f64> = closes.iter().map(|c| c + 1.0).collect();
        let lows: Vec<f64> = closes.iter().map(|c| c - 1.0).collect();
        let rc = calculate_rainbow_collection(&closes, &highs, &lows);
        assert_eq!(rc.red.len(), n);
        assert_eq!(rc.violet.len(), n);
    }

    #[test]
    fn test_confluence_output_length() {
        let n = 100;
        let closes = make_trending_data(n, 100.0, 0.3);
        let highs: Vec<f64> = closes.iter().map(|c| c + 1.0).collect();
        let lows: Vec<f64> = closes.iter().map(|c| c - 1.0).collect();
        let result = calculate_rainbow_confluence(&closes, &highs, &lows, 3, 3);
        assert_eq!(result.len(), n);
    }

    #[test]
    fn test_composite_score_bounded() {
        let n = 100;
        let closes = make_trending_data(n, 100.0, 0.3);
        let highs: Vec<f64> = closes.iter().map(|c| c + 1.0).collect();
        let lows: Vec<f64> = closes.iter().map(|c| c - 1.0).collect();
        let result = rainbow_composite_score(&closes, &highs, &lows);
        assert_eq!(result.len(), n);
        for v in &result {
            assert!(*v >= -1.0 && *v <= 1.0, "composite out of range: {v}");
        }
    }

    #[test]
    fn test_r_pattern_output_length() {
        let n = 50;
        let closes = make_trending_data(n, 100.0, 0.5);
        let highs: Vec<f64> = closes.iter().map(|c| c + 2.0).collect();
        let lows: Vec<f64> = closes.iter().map(|c| c - 2.0).collect();
        let result = calculate_r_pattern(&closes, &highs, &lows, 14);
        assert_eq!(result.len(), n);
    }

    #[test]
    fn test_gap_pattern_detects_gap() {
        let closes = vec![100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0,
                          110.0, 111.0, 112.0, 113.0, 114.0, 100.0]; // big drop
        let opens = vec![100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0,
                         110.0, 111.0, 112.0, 113.0, 114.0, 85.0]; // gap down open
        let highs: Vec<f64> = closes.iter().zip(opens.iter()).map(|(&c, &o)| f64::max(c, o) + 1.0).collect();
        let lows: Vec<f64> = closes.iter().zip(opens.iter()).map(|(&c, &o)| f64::min(c, o) - 1.0).collect();
        let result = calculate_gap_pattern(&opens, &highs, &lows, &closes, 14, 1.0);
        assert_eq!(result.len(), 16);
        // Last bar has a large gap-down → should be 1.0 (bullish fade)
        assert_eq!(result[15], 1.0);
    }
}
