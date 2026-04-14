// helper.rs — Shared primitives for indicator modules.
//
// Two categories:
//   1. Candle geometry: real_body, upper_shadow, lower_shadow, range, gaps
//   2. Scalar primitives: typical_price, wilder_smooth, period_to_k, lookback
//
// These are single-step, stateless functions. For rolling-window operations
// (variance, stddev, correlation) see indicators/stats.rs.

use crate::error::{TAError, TAResult};

// ── Candle Geometry ──────────────────────────────────────────────────────────

/// Candlestick real body length: |close - open|
#[inline]
#[must_use]
pub fn real_body(open: f64, close: f64) -> f64 {
    (close - open).abs()
}

/// Upper shadow length: high - max(open, close)
#[inline]
#[must_use]
pub fn upper_shadow(high: f64, open: f64, close: f64) -> f64 {
    high - if close >= open { close } else { open }
}

/// Lower shadow length: min(open, close) - low
#[inline]
#[must_use]
pub fn lower_shadow(low: f64, open: f64, close: f64) -> f64 {
    (if close >= open { open } else { close }) - low
}

/// Candle range: high - low
#[inline]
#[must_use]
pub fn candle_range(high: f64, low: f64) -> f64 {
    high - low
}

/// True if the second candle's real body gaps above the first candle's real body.
#[inline]
#[must_use]
pub fn has_gap_up(open2: f64, close2: f64, open1: f64, close1: f64) -> bool {
    open2.min(close2) > open1.max(close1)
}

/// True if the second candle's real body gaps below the first candle's real body.
#[inline]
#[must_use]
pub fn has_gap_down(open2: f64, close2: f64, open1: f64, close1: f64) -> bool {
    open2.max(close2) < open1.min(close1)
}

// ── Price Primitives ─────────────────────────────────────────────────────────

/// Typical price: (high + low + close) / 3
#[inline]
#[must_use]
pub fn typical_price(high: f64, low: f64, close: f64) -> f64 {
    (high + low + close) / 3.0
}

/// Wilder smoothing step: `prev - prev/period + value`
///
/// Used by DM system (+DM, -DM, TR smoothing) and ADX.
/// Equivalent to EMA with alpha = 1/period.
#[inline]
#[must_use]
pub fn wilder_smooth(prev: f64, value: f64, period: usize) -> f64 {
    prev - prev / period as f64 + value
}

/// Wilder average step: `prev - prev/period + value/period`
///
/// Like `wilder_smooth` but divides the new value by period too.
/// Used by Wilder's RSI smoothing, ATR, ADX averaging.
#[inline]
#[must_use]
pub fn wilder_avg_step(prev: f64, value: f64, period: usize) -> f64 {
    prev - prev / period as f64 + value / period as f64
}

// ── Lookback ─────────────────────────────────────────────────────────────────

/// Number of bars back to the lowest value in a lookback window.
/// Returns 0 if the lowest is at `start_idx` itself.
pub fn lowest_bars(array: &[f64], start_idx: usize, lookback: usize) -> TAResult<usize> {
    if array.is_empty() || start_idx >= array.len() || lookback == 0 || start_idx < lookback - 1 {
        return Err(TAError::InvalidParameter("lowest_bars: invalid index/lookback"));
    }
    let mut lowest = array[start_idx];
    let mut lowest_idx = 0;
    for i in 1..lookback {
        if array[start_idx - i] < lowest {
            lowest = array[start_idx - i];
            lowest_idx = i;
        }
    }
    Ok(lowest_idx)
}

/// Number of bars back to the highest value in a lookback window.
/// Returns 0 if the highest is at `start_idx` itself.
pub fn highest_bars(array: &[f64], start_idx: usize, lookback: usize) -> TAResult<usize> {
    if array.is_empty() || start_idx >= array.len() || lookback == 0 || start_idx < lookback - 1 {
        return Err(TAError::InvalidParameter("highest_bars: invalid index/lookback"));
    }
    let mut highest = array[start_idx];
    let mut highest_idx = 0;
    for i in 1..lookback {
        if array[start_idx - i] > highest {
            highest = array[start_idx - i];
            highest_idx = i;
        }
    }
    Ok(highest_idx)
}

/// EMA smoothing factor: k = 2 / (period + 1)
#[inline]
pub fn period_to_k(period: usize) -> TAResult<f64> {
    if period == 0 {
        return Err(TAError::InvalidParameter("period must be > 0"));
    }
    Ok(2.0 / (period as f64 + 1.0))
}

/// Compute mean of a slice. Returns 0.0 for empty input.
#[inline]
#[must_use]
pub fn mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    values.iter().sum::<f64>() / values.len() as f64
}

/// Sample variance of a slice (Bessel-corrected, n-1 denominator).
/// Returns 0.0 for slices with fewer than 2 elements.
#[inline]
#[must_use]
pub fn sample_variance(values: &[f64]) -> f64 {
    if values.len() < 2 {
        return 0.0;
    }
    let m = mean(values);
    let ss: f64 = values.iter().map(|v| (v - m).powi(2)).sum();
    ss / (values.len() - 1) as f64
}

/// Sample standard deviation (sqrt of sample_variance).
#[inline]
#[must_use]
pub fn sample_stddev(values: &[f64]) -> f64 {
    sample_variance(values).sqrt()
}

/// Population variance (n denominator, no Bessel correction).
/// Returns 0.0 for empty input.
#[inline]
#[must_use]
pub fn pop_variance(values: &[f64]) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let m = mean(values);
    values.iter().map(|v| (v - m).powi(2)).sum::<f64>() / values.len() as f64
}

/// Population standard deviation (sqrt of pop_variance).
#[inline]
#[must_use]
pub fn pop_stddev(values: &[f64]) -> f64 {
    pop_variance(values).sqrt()
}
