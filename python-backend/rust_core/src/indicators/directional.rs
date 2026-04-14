// directional.rs — Directional Movement System (Wilder)
//
// Standalone DM-family functions: +DM, -DM, +DI, -DI, DX.
// These are the building blocks used by ADX (in oscillators.rs).
// Exposing them separately allows composing custom signals.
//
// kand-Blueprint pattern adopted:
//   batch fn()       — full series computation
//   fn _with_state() — batch + final state for _inc() bootstrap
//   fn _inc()        — incremental: prev_state + new_input -> new_value
//
// Functions: plus_dm, minus_dm, plus_di, minus_di, dx
// All use Wilder's smoothing: new = prev - prev/period + value

use super::volatility::true_range;
use crate::helper;

// ── Helpers ─────────────────────────────────────────────────────────────────

/// One-bar +DM1 (raw, unsmoothed).
#[inline]
fn plus_dm1(high: f64, prev_high: f64, low: f64, prev_low: f64) -> f64 {
    let high_diff = high - prev_high;
    let low_diff = prev_low - low;
    if high_diff > low_diff && high_diff > 0.0 {
        high_diff
    } else {
        0.0
    }
}

/// One-bar -DM1 (raw, unsmoothed).
#[inline]
fn minus_dm1(high: f64, prev_high: f64, low: f64, prev_low: f64) -> f64 {
    let high_diff = high - prev_high;
    let low_diff = prev_low - low;
    if low_diff > high_diff && low_diff > 0.0 {
        low_diff
    } else {
        0.0
    }
}

// ── Plus DM ─────────────────────────────────────────────────────────────────

/// Smoothed Plus Directional Movement (+DM) series.
///
/// Initial value = sum of first `period-1` raw +DM1 values.
/// Subsequent values use Wilder's smoothing: `prev - prev/period + dm1`.
///
/// Returns NaN for the first `period-1` bars (lookback).
pub fn plus_dm(highs: &[f64], lows: &[f64], period: usize) -> Vec<f64> {
    let n = highs.len();
    if n < period || period < 2 {
        return vec![f64::NAN; n];
    }
    let mut out = vec![f64::NAN; n];

    // Initial sum
    let mut dm_sum = 0.0;
    for i in 1..period {
        dm_sum += plus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
    }
    out[period - 1] = dm_sum;

    // Wilder smoothing
    for i in period..n {
        let dm = plus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        out[i] = helper::wilder_smooth(out[i - 1], dm, period);
    }
    out
}

/// Plus DM with state — returns (series, final_smoothed_dm) for `plus_dm_inc()`.
pub fn plus_dm_with_state(highs: &[f64], lows: &[f64], period: usize) -> (Vec<f64>, f64) {
    let result = plus_dm(highs, lows, period);
    let last = result.iter().rev().find(|v| !v.is_nan()).copied().unwrap_or(0.0);
    (result, last)
}

/// Incremental +DM update.
///
/// Returns new smoothed +DM value.
///
/// Bootstrap state from `plus_dm_with_state()`.
#[inline]
pub fn plus_dm_inc(
    high: f64,
    low: f64,
    prev_high: f64,
    prev_low: f64,
    prev_smoothed_dm: f64,
    period: usize,
) -> f64 {
    let dm = plus_dm1(high, prev_high, low, prev_low);
    helper::wilder_smooth(prev_smoothed_dm, dm, period)
}

// ── Minus DM ────────────────────────────────────────────────────────────────

/// Smoothed Minus Directional Movement (-DM) series.
///
/// Initial value = sum of first `period-1` raw -DM1 values.
/// Subsequent values use Wilder's smoothing.
///
/// Returns NaN for the first `period-1` bars.
pub fn minus_dm(highs: &[f64], lows: &[f64], period: usize) -> Vec<f64> {
    let n = highs.len();
    if n < period || period < 2 {
        return vec![f64::NAN; n];
    }
    let mut out = vec![f64::NAN; n];

    let mut dm_sum = 0.0;
    for i in 1..period {
        dm_sum += minus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
    }
    out[period - 1] = dm_sum;

    for i in period..n {
        let dm = minus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        out[i] = helper::wilder_smooth(out[i - 1], dm, period);
    }
    out
}

/// Minus DM with state — returns (series, final_smoothed_dm) for `minus_dm_inc()`.
pub fn minus_dm_with_state(highs: &[f64], lows: &[f64], period: usize) -> (Vec<f64>, f64) {
    let result = minus_dm(highs, lows, period);
    let last = result.iter().rev().find(|v| !v.is_nan()).copied().unwrap_or(0.0);
    (result, last)
}

/// Incremental -DM update.
///
/// Returns new smoothed -DM value.
///
/// Bootstrap state from `minus_dm_with_state()`.
#[inline]
pub fn minus_dm_inc(
    high: f64,
    low: f64,
    prev_high: f64,
    prev_low: f64,
    prev_smoothed_dm: f64,
    period: usize,
) -> f64 {
    let dm = minus_dm1(high, prev_high, low, prev_low);
    helper::wilder_smooth(prev_smoothed_dm, dm, period)
}

// ── Plus DI ─────────────────────────────────────────────────────────────────

/// Plus Directional Indicator (+DI) series.
///
/// `+DI = 100 * smoothed_+DM / smoothed_TR`
///
/// Returns NaN for the first `period` bars (lookback = period because TR
/// needs prev_close, adding one bar of delay vs raw DM).
pub fn plus_di(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    period: usize,
) -> Vec<f64> {
    let n = highs.len();
    if n < period + 1 || period < 2 {
        return vec![f64::NAN; n];
    }
    let mut out = vec![f64::NAN; n];

    // Accumulate initial sums over bars 1..period
    let mut dm_sum = 0.0;
    let mut tr_sum = 0.0;
    for i in 1..period {
        dm_sum += plus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        tr_sum += true_range(highs[i], lows[i], closes[i - 1]);
    }

    // First valid bar at index=period (one extra bar for Wilder smoothing start)
    let dm = plus_dm1(highs[period], highs[period - 1], lows[period], lows[period - 1]);
    let tr = true_range(highs[period], lows[period], closes[period - 1]);
    let mut s_dm = helper::wilder_smooth(dm_sum, dm, period);
    let mut s_tr = helper::wilder_smooth(tr_sum, tr, period);
    out[period] = if s_tr > 1e-12 { 100.0 * s_dm / s_tr } else { 0.0 };

    for i in (period + 1)..n {
        let dm_val = plus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        let tr_val = true_range(highs[i], lows[i], closes[i - 1]);
        s_dm = helper::wilder_smooth(s_dm, dm_val, period);
        s_tr = helper::wilder_smooth(s_tr, tr_val, period);
        out[i] = if s_tr > 1e-12 { 100.0 * s_dm / s_tr } else { 0.0 };
    }
    out
}

/// Plus DI with state — returns (series, final_smoothed_dm, final_smoothed_tr)
/// for `plus_di_inc()`.
pub fn plus_di_with_state(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    period: usize,
) -> (Vec<f64>, f64, f64) {
    let n = highs.len();
    if n < period + 1 || period < 2 {
        return (vec![f64::NAN; n], 0.0, 0.0);
    }

    let mut out = vec![f64::NAN; n];
    let mut dm_sum = 0.0;
    let mut tr_sum = 0.0;
    for i in 1..period {
        dm_sum += plus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        tr_sum += true_range(highs[i], lows[i], closes[i - 1]);
    }

    let dm = plus_dm1(highs[period], highs[period - 1], lows[period], lows[period - 1]);
    let tr = true_range(highs[period], lows[period], closes[period - 1]);
    let mut s_dm = helper::wilder_smooth(dm_sum, dm, period);
    let mut s_tr = helper::wilder_smooth(tr_sum, tr, period);
    out[period] = if s_tr > 1e-12 { 100.0 * s_dm / s_tr } else { 0.0 };

    for i in (period + 1)..n {
        let dm_val = plus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        let tr_val = true_range(highs[i], lows[i], closes[i - 1]);
        s_dm = helper::wilder_smooth(s_dm, dm_val, period);
        s_tr = helper::wilder_smooth(s_tr, tr_val, period);
        out[i] = if s_tr > 1e-12 { 100.0 * s_dm / s_tr } else { 0.0 };
    }
    (out, s_dm, s_tr)
}

/// Incremental +DI update.
///
/// Returns `(new_plus_di, new_smoothed_dm, new_smoothed_tr)`.
///
/// Bootstrap state from `plus_di_with_state()`.
#[inline]
pub fn plus_di_inc(
    high: f64,
    low: f64,
    prev_high: f64,
    prev_low: f64,
    prev_close: f64,
    prev_smoothed_dm: f64,
    prev_smoothed_tr: f64,
    period: usize,
) -> (f64, f64, f64) {
    let dm = plus_dm1(high, prev_high, low, prev_low);
    let tr = true_range(high, low, prev_close);
    let new_s_dm = helper::wilder_smooth(prev_smoothed_dm, dm, period);
    let new_s_tr = helper::wilder_smooth(prev_smoothed_tr, tr, period);
    let di = if new_s_tr > 1e-12 { 100.0 * new_s_dm / new_s_tr } else { 0.0 };
    (di, new_s_dm, new_s_tr)
}

// ── Minus DI ────────────────────────────────────────────────────────────────

/// Minus Directional Indicator (-DI) series.
///
/// `-DI = 100 * smoothed_-DM / smoothed_TR`
///
/// Returns NaN for the first `period` bars.
pub fn minus_di(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    period: usize,
) -> Vec<f64> {
    let n = highs.len();
    if n < period + 1 || period < 2 {
        return vec![f64::NAN; n];
    }
    let mut out = vec![f64::NAN; n];

    let mut dm_sum = 0.0;
    let mut tr_sum = 0.0;
    for i in 1..period {
        dm_sum += minus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        tr_sum += true_range(highs[i], lows[i], closes[i - 1]);
    }

    let dm = minus_dm1(highs[period], highs[period - 1], lows[period], lows[period - 1]);
    let tr = true_range(highs[period], lows[period], closes[period - 1]);
    let mut s_dm = helper::wilder_smooth(dm_sum, dm, period);
    let mut s_tr = helper::wilder_smooth(tr_sum, tr, period);
    out[period] = if s_tr > 1e-12 { 100.0 * s_dm / s_tr } else { 0.0 };

    for i in (period + 1)..n {
        let dm_val = minus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        let tr_val = true_range(highs[i], lows[i], closes[i - 1]);
        s_dm = helper::wilder_smooth(s_dm, dm_val, period);
        s_tr = helper::wilder_smooth(s_tr, tr_val, period);
        out[i] = if s_tr > 1e-12 { 100.0 * s_dm / s_tr } else { 0.0 };
    }
    out
}

/// Minus DI with state — returns (series, final_smoothed_dm, final_smoothed_tr)
/// for `minus_di_inc()`.
pub fn minus_di_with_state(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    period: usize,
) -> (Vec<f64>, f64, f64) {
    let n = highs.len();
    if n < period + 1 || period < 2 {
        return (vec![f64::NAN; n], 0.0, 0.0);
    }

    let mut out = vec![f64::NAN; n];
    let mut dm_sum = 0.0;
    let mut tr_sum = 0.0;
    for i in 1..period {
        dm_sum += minus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        tr_sum += true_range(highs[i], lows[i], closes[i - 1]);
    }

    let dm = minus_dm1(highs[period], highs[period - 1], lows[period], lows[period - 1]);
    let tr = true_range(highs[period], lows[period], closes[period - 1]);
    let mut s_dm = helper::wilder_smooth(dm_sum, dm, period);
    let mut s_tr = helper::wilder_smooth(tr_sum, tr, period);
    out[period] = if s_tr > 1e-12 { 100.0 * s_dm / s_tr } else { 0.0 };

    for i in (period + 1)..n {
        let dm_val = minus_dm1(highs[i], highs[i - 1], lows[i], lows[i - 1]);
        let tr_val = true_range(highs[i], lows[i], closes[i - 1]);
        s_dm = helper::wilder_smooth(s_dm, dm_val, period);
        s_tr = helper::wilder_smooth(s_tr, tr_val, period);
        out[i] = if s_tr > 1e-12 { 100.0 * s_dm / s_tr } else { 0.0 };
    }
    (out, s_dm, s_tr)
}

/// Incremental -DI update.
///
/// Returns `(new_minus_di, new_smoothed_dm, new_smoothed_tr)`.
///
/// Bootstrap state from `minus_di_with_state()`.
#[inline]
pub fn minus_di_inc(
    high: f64,
    low: f64,
    prev_high: f64,
    prev_low: f64,
    prev_close: f64,
    prev_smoothed_dm: f64,
    prev_smoothed_tr: f64,
    period: usize,
) -> (f64, f64, f64) {
    let dm = minus_dm1(high, prev_high, low, prev_low);
    let tr = true_range(high, low, prev_close);
    let new_s_dm = helper::wilder_smooth(prev_smoothed_dm, dm, period);
    let new_s_tr = helper::wilder_smooth(prev_smoothed_tr, tr, period);
    let di = if new_s_tr > 1e-12 { 100.0 * new_s_dm / new_s_tr } else { 0.0 };
    (di, new_s_dm, new_s_tr)
}

// ── DX ──────────────────────────────────────────────────────────────────────

/// Directional Movement Index (DX) series.
///
/// `DX = 100 * |+DI - -DI| / (+DI + -DI)`
///
/// Returns NaN for the first `period` bars (same lookback as DI).
pub fn dx(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    period: usize,
) -> Vec<f64> {
    let pdi = plus_di(highs, lows, closes, period);
    let mdi = minus_di(highs, lows, closes, period);
    pdi.iter()
        .zip(mdi.iter())
        .map(|(&p, &m)| {
            if p.is_nan() || m.is_nan() {
                f64::NAN
            } else {
                let sum = p + m;
                if sum > 1e-12 {
                    100.0 * (p - m).abs() / sum
                } else {
                    0.0
                }
            }
        })
        .collect()
}

/// DX with state — returns (series, final_smoothed_plus_dm, final_smoothed_minus_dm,
/// final_smoothed_tr) for `dx_inc()`.
pub fn dx_with_state(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    period: usize,
) -> (Vec<f64>, f64, f64, f64) {
    let (pdi, s_plus_dm, s_tr_p) = plus_di_with_state(highs, lows, closes, period);
    let (mdi, s_minus_dm, _s_tr_m) = minus_di_with_state(highs, lows, closes, period);

    let dx_vals: Vec<f64> = pdi
        .iter()
        .zip(mdi.iter())
        .map(|(&p, &m)| {
            if p.is_nan() || m.is_nan() {
                f64::NAN
            } else {
                let sum = p + m;
                if sum > 1e-12 {
                    100.0 * (p - m).abs() / sum
                } else {
                    0.0
                }
            }
        })
        .collect();

    (dx_vals, s_plus_dm, s_minus_dm, s_tr_p)
}

/// Incremental DX update.
///
/// Returns `(new_dx, new_smoothed_plus_dm, new_smoothed_minus_dm, new_smoothed_tr)`.
///
/// Bootstrap state from `dx_with_state()`.
#[inline]
pub fn dx_inc(
    high: f64,
    low: f64,
    prev_high: f64,
    prev_low: f64,
    prev_close: f64,
    prev_smoothed_plus_dm: f64,
    prev_smoothed_minus_dm: f64,
    prev_smoothed_tr: f64,
    period: usize,
) -> (f64, f64, f64, f64) {
    let tr = true_range(high, low, prev_close);
    let p_dm = plus_dm1(high, prev_high, low, prev_low);
    let m_dm = minus_dm1(high, prev_high, low, prev_low);

    let new_s_plus_dm = helper::wilder_smooth(prev_smoothed_plus_dm, p_dm, period);
    let new_s_minus_dm = helper::wilder_smooth(prev_smoothed_minus_dm, m_dm, period);
    let new_s_tr = helper::wilder_smooth(prev_smoothed_tr, tr, period);

    let pdi = if new_s_tr > 1e-12 { 100.0 * new_s_plus_dm / new_s_tr } else { 0.0 };
    let mdi = if new_s_tr > 1e-12 { 100.0 * new_s_minus_dm / new_s_tr } else { 0.0 };
    let di_sum = pdi + mdi;
    let dx_val = if di_sum > 1e-12 { 100.0 * (pdi - mdi).abs() / di_sum } else { 0.0 };

    (dx_val, new_s_plus_dm, new_s_minus_dm, new_s_tr)
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    // Generate realistic OHLC test data
    fn gen_ohlc(n: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
        let mut highs = Vec::with_capacity(n);
        let mut lows = Vec::with_capacity(n);
        let mut closes = Vec::with_capacity(n);
        for i in 0..n {
            let base = 100.0 + (i as f64 * 0.2).sin() * 10.0;
            highs.push(base + 2.0 + (i as f64 * 0.7).sin().abs());
            lows.push(base - 2.0 - (i as f64 * 0.5).sin().abs());
            closes.push(base + (i as f64 * 0.3).sin());
        }
        (highs, lows, closes)
    }

    // ── Plus DM ────────────────────────────────────────────────────────

    #[test]
    fn plus_dm_basic() {
        let (highs, lows, _) = gen_ohlc(30);
        let result = plus_dm(&highs, &lows, 14);
        assert_eq!(result.len(), 30);
        // First 13 bars are NaN (lookback = period - 1)
        for i in 0..13 {
            assert!(result[i].is_nan(), "bar {i} should be NaN");
        }
        // First valid value at index 13
        assert!(!result[13].is_nan());
        // All subsequent values non-negative
        for i in 13..30 {
            assert!(result[i] >= 0.0, "plus_dm[{i}] = {} should be >= 0", result[i]);
        }
    }

    #[test]
    fn plus_dm_inc_matches_batch() {
        let (highs, lows, _) = gen_ohlc(40);
        let n = 35;
        let (batch, last_dm) = plus_dm_with_state(&highs[..n], &lows[..n], 14);
        assert_eq!(batch.len(), n);

        // Extend by one bar via _inc
        let inc_dm = plus_dm_inc(highs[n], lows[n], highs[n - 1], lows[n - 1], last_dm, 14);

        // Compare against full batch
        let full = plus_dm(&highs[..=n], &lows[..=n], 14);
        assert_abs_diff_eq!(inc_dm, *full.last().unwrap(), epsilon = 1e-9);
    }

    #[test]
    fn plus_dm_inc_multi_step() {
        let (highs, lows, _) = gen_ohlc(50);
        let init_len = 20;
        let (batch_init, mut s_dm) = plus_dm_with_state(&highs[..init_len], &lows[..init_len], 14);
        assert_eq!(batch_init.len(), init_len);

        for step in init_len..50 {
            let inc_dm = plus_dm_inc(highs[step], lows[step], highs[step - 1], lows[step - 1], s_dm, 14);
            let full = plus_dm(&highs[..=step], &lows[..=step], 14);
            assert_abs_diff_eq!(inc_dm, *full.last().unwrap(), epsilon = 1e-9);
            s_dm = inc_dm;
        }
    }

    // ── Minus DM ───────────────────────────────────────────────────────

    #[test]
    fn minus_dm_basic() {
        let (highs, lows, _) = gen_ohlc(30);
        let result = minus_dm(&highs, &lows, 14);
        assert_eq!(result.len(), 30);
        for i in 0..13 {
            assert!(result[i].is_nan());
        }
        assert!(!result[13].is_nan());
        for i in 13..30 {
            assert!(result[i] >= 0.0);
        }
    }

    #[test]
    fn minus_dm_inc_matches_batch() {
        let (highs, lows, _) = gen_ohlc(40);
        let n = 35;
        let (batch, last_dm) = minus_dm_with_state(&highs[..n], &lows[..n], 14);
        assert_eq!(batch.len(), n);

        let inc_dm = minus_dm_inc(highs[n], lows[n], highs[n - 1], lows[n - 1], last_dm, 14);
        let full = minus_dm(&highs[..=n], &lows[..=n], 14);
        assert_abs_diff_eq!(inc_dm, *full.last().unwrap(), epsilon = 1e-9);
    }

    #[test]
    fn minus_dm_inc_multi_step() {
        let (highs, lows, _) = gen_ohlc(50);
        let init_len = 20;
        let (batch_init, mut s_dm) = minus_dm_with_state(&highs[..init_len], &lows[..init_len], 14);
        assert_eq!(batch_init.len(), init_len);

        for step in init_len..50 {
            let inc_dm = minus_dm_inc(highs[step], lows[step], highs[step - 1], lows[step - 1], s_dm, 14);
            let full = minus_dm(&highs[..=step], &lows[..=step], 14);
            assert_abs_diff_eq!(inc_dm, *full.last().unwrap(), epsilon = 1e-9);
            s_dm = inc_dm;
        }
    }

    // ── Plus DI ────────────────────────────────────────────────────────

    #[test]
    fn plus_di_basic() {
        let (highs, lows, closes) = gen_ohlc(30);
        let result = plus_di(&highs, &lows, &closes, 14);
        assert_eq!(result.len(), 30);
        // Lookback = period = 14 → first valid at index 14
        for i in 0..14 {
            assert!(result[i].is_nan(), "bar {i} should be NaN");
        }
        assert!(!result[14].is_nan());
        // DI in range [0, 100]
        for i in 14..30 {
            assert!(result[i] >= 0.0 && result[i] <= 100.0,
                "+DI[{i}] = {} out of range", result[i]);
        }
    }

    #[test]
    fn plus_di_inc_matches_batch() {
        let (highs, lows, closes) = gen_ohlc(40);
        let n = 35;
        let (batch, s_dm, s_tr) = plus_di_with_state(&highs[..n], &lows[..n], &closes[..n], 14);
        assert_eq!(batch.len(), n);

        let (inc_di, new_dm, new_tr) = plus_di_inc(
            highs[n], lows[n], highs[n - 1], lows[n - 1], closes[n - 1],
            s_dm, s_tr, 14,
        );

        let full = plus_di(&highs[..=n], &lows[..=n], &closes[..=n], 14);
        assert_abs_diff_eq!(inc_di, *full.last().unwrap(), epsilon = 1e-9);
        assert!(new_dm >= 0.0);
        assert!(new_tr > 0.0);
    }

    #[test]
    fn plus_di_inc_multi_step() {
        let (highs, lows, closes) = gen_ohlc(50);
        let init_len = 20;
        let (batch_init, mut s_dm, mut s_tr) =
            plus_di_with_state(&highs[..init_len], &lows[..init_len], &closes[..init_len], 14);
        assert_eq!(batch_init.len(), init_len);

        for step in init_len..50 {
            let (inc_di, nd, nt) = plus_di_inc(
                highs[step], lows[step], highs[step - 1], lows[step - 1], closes[step - 1],
                s_dm, s_tr, 14,
            );
            let full = plus_di(&highs[..=step], &lows[..=step], &closes[..=step], 14);
            assert_abs_diff_eq!(inc_di, *full.last().unwrap(), epsilon = 1e-9);
            s_dm = nd;
            s_tr = nt;
        }
    }

    // ── Minus DI ───────────────────────────────────────────────────────

    #[test]
    fn minus_di_basic() {
        let (highs, lows, closes) = gen_ohlc(30);
        let result = minus_di(&highs, &lows, &closes, 14);
        assert_eq!(result.len(), 30);
        for i in 0..14 {
            assert!(result[i].is_nan());
        }
        assert!(!result[14].is_nan());
        for i in 14..30 {
            assert!(result[i] >= 0.0 && result[i] <= 100.0,
                "-DI[{i}] = {} out of range", result[i]);
        }
    }

    #[test]
    fn minus_di_inc_matches_batch() {
        let (highs, lows, closes) = gen_ohlc(40);
        let n = 35;
        let (batch, s_dm, s_tr) = minus_di_with_state(&highs[..n], &lows[..n], &closes[..n], 14);
        assert_eq!(batch.len(), n);

        let (inc_di, new_dm, new_tr) = minus_di_inc(
            highs[n], lows[n], highs[n - 1], lows[n - 1], closes[n - 1],
            s_dm, s_tr, 14,
        );

        let full = minus_di(&highs[..=n], &lows[..=n], &closes[..=n], 14);
        assert_abs_diff_eq!(inc_di, *full.last().unwrap(), epsilon = 1e-9);
        assert!(new_dm >= 0.0);
        assert!(new_tr > 0.0);
    }

    #[test]
    fn minus_di_inc_multi_step() {
        let (highs, lows, closes) = gen_ohlc(50);
        let init_len = 20;
        let (batch_init, mut s_dm, mut s_tr) =
            minus_di_with_state(&highs[..init_len], &lows[..init_len], &closes[..init_len], 14);
        assert_eq!(batch_init.len(), init_len);

        for step in init_len..50 {
            let (inc_di, nd, nt) = minus_di_inc(
                highs[step], lows[step], highs[step - 1], lows[step - 1], closes[step - 1],
                s_dm, s_tr, 14,
            );
            let full = minus_di(&highs[..=step], &lows[..=step], &closes[..=step], 14);
            assert_abs_diff_eq!(inc_di, *full.last().unwrap(), epsilon = 1e-9);
            s_dm = nd;
            s_tr = nt;
        }
    }

    // ── DX ─────────────────────────────────────────────────────────────

    #[test]
    fn dx_basic() {
        let (highs, lows, closes) = gen_ohlc(30);
        let result = dx(&highs, &lows, &closes, 14);
        assert_eq!(result.len(), 30);
        for i in 0..14 {
            assert!(result[i].is_nan());
        }
        // DX in range [0, 100]
        for i in 14..30 {
            assert!(!result[i].is_nan());
            assert!(result[i] >= 0.0 && result[i] <= 100.0,
                "DX[{i}] = {} out of range", result[i]);
        }
    }

    #[test]
    fn dx_inc_matches_batch() {
        let (highs, lows, closes) = gen_ohlc(40);
        let n = 35;
        let (batch, s_pdm, s_mdm, s_tr) =
            dx_with_state(&highs[..n], &lows[..n], &closes[..n], 14);
        assert_eq!(batch.len(), n);

        let (inc_dx, new_pdm, new_mdm, new_tr) = dx_inc(
            highs[n], lows[n], highs[n - 1], lows[n - 1], closes[n - 1],
            s_pdm, s_mdm, s_tr, 14,
        );

        let full = dx(&highs[..=n], &lows[..=n], &closes[..=n], 14);
        assert_abs_diff_eq!(inc_dx, *full.last().unwrap(), epsilon = 1e-9);
        assert!(new_pdm >= 0.0);
        assert!(new_mdm >= 0.0);
        assert!(new_tr > 0.0);
    }

    #[test]
    fn dx_inc_multi_step() {
        let (highs, lows, closes) = gen_ohlc(50);
        let init_len = 20;
        let (batch_init, mut s_pdm, mut s_mdm, mut s_tr) =
            dx_with_state(&highs[..init_len], &lows[..init_len], &closes[..init_len], 14);
        assert_eq!(batch_init.len(), init_len);

        for step in init_len..50 {
            let (inc_dx, np, nm, nt) = dx_inc(
                highs[step], lows[step], highs[step - 1], lows[step - 1], closes[step - 1],
                s_pdm, s_mdm, s_tr, 14,
            );
            let full = dx(&highs[..=step], &lows[..=step], &closes[..=step], 14);
            assert_abs_diff_eq!(inc_dx, *full.last().unwrap(), epsilon = 1e-9);
            s_pdm = np;
            s_mdm = nm;
            s_tr = nt;
        }
    }

    // ── Cross-validation: DI sum consistency ───────────────────────────

    #[test]
    fn di_sum_consistent() {
        let (highs, lows, closes) = gen_ohlc(40);
        let pdi = plus_di(&highs, &lows, &closes, 14);
        let mdi = minus_di(&highs, &lows, &closes, 14);
        // +DI and -DI should both be non-negative after warmup
        for i in 14..40 {
            assert!(pdi[i] >= 0.0, "+DI[{i}] negative");
            assert!(mdi[i] >= 0.0, "-DI[{i}] negative");
            // At least one should be > 0 for non-flat data
            assert!(pdi[i] > 0.0 || mdi[i] > 0.0, "both DI zero at {i}");
        }
    }

    // ── Edge case: period = 2 (minimum) ────────────────────────────────

    #[test]
    fn dm_period_2() {
        let (highs, lows, _) = gen_ohlc(10);
        let pdm = plus_dm(&highs, &lows, 2);
        let mdm = minus_dm(&highs, &lows, 2);
        // Lookback = 1 → first valid at index 1
        assert!(pdm[0].is_nan());
        assert!(!pdm[1].is_nan());
        assert!(mdm[0].is_nan());
        assert!(!mdm[1].is_nan());
    }
}
