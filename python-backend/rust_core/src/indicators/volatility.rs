// volatility.rs — Volatility measures and bands
//
// Mirrors Python: indicator_engine/volatility.py
// Migrated from lib.rs: atr, sample_std, bb_bandwidth, bb_percent_b, keltner_channels
//
// kand-Blueprint pattern adopted:
//   batch fn()       — full series computation
//   fn _inc()        — incremental: prev_state + new_input -> new_value
// kand new (future): SAR, NATR

use super::trend::ema_seed_first as ema;
use super::stats::{rolling_max, rolling_min};

// ── True Range ───────────────────────────────────────────────────────────────

/// True Range for a single bar.
///
/// `TR = max(high - low, |high - prev_close|, |low - prev_close|)`
#[inline]
pub fn true_range(high: f64, low: f64, prev_close: f64) -> f64 {
    f64::max(
        high - low,
        f64::max((high - prev_close).abs(), (low - prev_close).abs()),
    )
}

// ── ATR ──────────────────────────────────────────────────────────────────────

/// Sample standard deviation (/ n-1) — matches pandas rolling.std().
pub fn sample_std(values: &[f64]) -> f64 {
    let n = values.len();
    if n < 2 {
        return 0.0;
    }
    let mean = values.iter().sum::<f64>() / n as f64;
    let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (n as f64 - 1.0);
    variance.sqrt()
}

/// Average True Range — Wilder's EMA smoothing.
pub fn atr(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> Vec<f64> {
    if closes.len() < 2 || period == 0 {
        return vec![0.0; closes.len()];
    }
    let mut tr = vec![0.0_f64];
    for i in 1..closes.len() {
        tr.push(true_range(highs[i], lows[i], closes[i - 1]));
    }
    // Wilder ATR — EMA with alpha=1/period (span = 2*period-1)
    ema(&tr, period * 2 - 1)
}

/// ATR with state — same as `atr()` but returns final ATR value for `atr_inc()`.
pub fn atr_with_state(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> (Vec<f64>, f64) {
    let result = atr(highs, lows, closes, period);
    let last = *result.last().unwrap_or(&0.0);
    (result, last)
}

/// Incremental ATR update.
///
/// Formula (Wilder's RMA):
/// `new_atr = (prev_atr * (period-1) + TR) / period`
///
/// Bootstrap state from `atr_with_state()`.
#[inline]
pub fn atr_inc(high: f64, low: f64, prev_close: f64, prev_atr: f64, period: usize) -> f64 {
    let tr = true_range(high, low, prev_close);
    (prev_atr * (period as f64 - 1.0) + tr) / period as f64
}

// ── Bollinger Bands ──────────────────────────────────────────────────────────

/// Bollinger Bandwidth — (upper - lower) / middle.
pub fn bb_bandwidth(values: &[f64], period: usize, num_std: f64) -> Vec<f64> {
    let len = values.len();
    let mut out = Vec::with_capacity(len);
    for i in 0..len {
        let start = (i + 1).saturating_sub(period);
        let window = &values[start..=i];
        let n = window.len() as f64;
        let mid = window.iter().sum::<f64>() / n;
        let std = sample_std(window);
        let upper = mid + num_std * std;
        let lower = mid - num_std * std;
        out.push(if mid != 0.0 {
            (upper - lower) / mid
        } else {
            0.0
        });
    }
    out
}

/// Bollinger Bands full — returns (upper, middle, lower) arrays.
///
/// Also returns final (sum, sum_sq) state for use with `bb_bands_inc()`.
pub fn bb_bands_with_state(
    values: &[f64],
    period: usize,
    num_std: f64,
) -> (Vec<f64>, Vec<f64>, Vec<f64>, f64, f64) {
    let len = values.len();
    let mut upper = Vec::with_capacity(len);
    let mut middle = Vec::with_capacity(len);
    let mut lower = Vec::with_capacity(len);
    let mut running_sum = 0.0_f64;
    let mut running_sum_sq = 0.0_f64;

    for i in 0..len {
        running_sum += values[i];
        running_sum_sq += values[i] * values[i];

        if i >= period {
            running_sum -= values[i - period];
            running_sum_sq -= values[i - period] * values[i - period];
        }

        let w = period.min(i + 1) as f64;
        let mid = running_sum / w;
        let variance = (running_sum_sq / w) - mid * mid;
        let std = if variance > 0.0 { variance.sqrt() } else { 0.0 };

        upper.push(mid + num_std * std);
        middle.push(mid);
        lower.push(mid - num_std * std);
    }

    (upper, middle, lower, running_sum, running_sum_sq)
}

/// Incremental Bollinger Bands update.
///
/// Uses running sum and sum_sq for O(1) variance computation.
/// Returns `(upper, middle, lower, new_sum, new_sum_sq)`.
///
/// # Arguments
/// * `new_price` — newest price entering the window
/// * `old_price` — oldest price leaving the window (`values[i - period]`)
/// * `prev_sum` — running sum from previous bar
/// * `prev_sum_sq` — running sum of squares from previous bar
/// * `period` — Bollinger period
/// * `num_std` — number of standard deviations
pub fn bb_bands_inc(
    new_price: f64,
    old_price: f64,
    prev_sum: f64,
    prev_sum_sq: f64,
    period: usize,
    num_std: f64,
) -> (f64, f64, f64, f64, f64) {
    let new_sum = prev_sum + new_price - old_price;
    let new_sum_sq = prev_sum_sq + new_price * new_price - old_price * old_price;
    let p = period as f64;
    let mid = new_sum / p;
    let variance = (new_sum_sq / p) - mid * mid;
    let std = if variance > 0.0 { variance.sqrt() } else { 0.0 };
    let upper = mid + num_std * std;
    let lower = mid - num_std * std;
    (upper, mid, lower, new_sum, new_sum_sq)
}

/// Bollinger %B — (close - lower) / (upper - lower).
pub fn bb_percent_b(values: &[f64], period: usize, num_std: f64) -> Vec<f64> {
    let len = values.len();
    let mut out = Vec::with_capacity(len);
    for i in 0..len {
        let start = (i + 1).saturating_sub(period);
        let window = &values[start..=i];
        let n = window.len() as f64;
        let mid = window.iter().sum::<f64>() / n;
        let std = sample_std(window);
        let upper = mid + num_std * std;
        let lower = mid - num_std * std;
        let bw = upper - lower;
        out.push(if bw > 1e-10 {
            (values[i] - lower) / bw
        } else {
            0.5
        });
    }
    out
}

// ── Keltner Channels ─────────────────────────────────────────────────────────

/// Keltner Channels — EMA ± mult*ATR. Returns (upper, middle, lower).
pub fn keltner_channels(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    ema_period: usize,
    atr_period: usize,
    mult: f64,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let middle = ema(closes, ema_period);
    let atr_vals = atr(highs, lows, closes, atr_period);
    let upper = middle.iter().zip(atr_vals.iter()).map(|(m, a)| m + mult * a).collect();
    let lower = middle.iter().zip(atr_vals.iter()).map(|(m, a)| m - mult * a).collect();
    (upper, middle, lower)
}

/// Incremental Keltner Channels update.
///
/// Returns `(upper, middle, lower)` given new EMA and ATR values.
///
/// Use `ema_inc()` and `atr_inc()` to get the individual components first.
#[inline]
pub fn keltner_inc(new_ema: f64, new_atr: f64, mult: f64) -> (f64, f64, f64) {
    (new_ema + mult * new_atr, new_ema, new_ema - mult * new_atr)
}

// ── Donchian Channels ─────────────────────────────────────────────────────────

/// Donchian Channels — highest high / lowest low over `period` bars.
///
/// Returns `(upper, middle, lower)` where middle = (upper + lower) / 2.
/// NaN for warmup bars (first `period - 1`).
///
/// Python ref: `volatility.py::donchian_channels()`.
/// Uses `stats::rolling_max` and `stats::rolling_min` — no duplicated logic.
pub fn donchian_channels(
    highs: &[f64],
    lows: &[f64],
    period: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let upper = rolling_max(highs, period);
    let lower = rolling_min(lows, period);
    let n = upper.len();
    let mut middle = Vec::with_capacity(n);
    for i in 0..n {
        if upper[i].is_nan() || lower[i].is_nan() {
            middle.push(f64::NAN);
        } else {
            middle.push((upper[i] + lower[i]) / 2.0);
        }
    }
    (upper, middle, lower)
}

/// Donchian with state — returns (upper, mid, lower, high_window, low_window).
pub fn donchian_with_state(
    highs: &[f64],
    lows: &[f64],
    period: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let (upper, middle, lower) = donchian_channels(highs, lows, period);
    let n = highs.len();
    let start = n.saturating_sub(period);
    let h_win = highs[start..].to_vec();
    let l_win = lows[start..].to_vec();
    (upper, middle, lower, h_win, l_win)
}

/// Incremental Donchian update.
///
/// Returns `(upper, middle, lower, new_high_window, new_low_window)`.
pub fn donchian_inc(
    new_high: f64,
    new_low: f64,
    high_window: &[f64],
    low_window: &[f64],
) -> (f64, f64, f64, Vec<f64>, Vec<f64>) {
    use super::stats::{rolling_max_inc, rolling_min_inc};
    let (upper, new_h_win) = rolling_max_inc(new_high, high_window);
    let (lower, new_l_win) = rolling_min_inc(new_low, low_window);
    let middle = (upper + lower) / 2.0;
    (upper, middle, lower, new_h_win, new_l_win)
}

// ── EMA-Bollinger Bands ───────────────────────────────────────────────────────

/// EMA-based Bollinger Bands — uses EMA instead of SMA as middle line.
///
/// Returns `(upper, middle, lower)`.
/// Python ref: `volatility.py::e_bollinger_bands()`.
pub fn e_bollinger_bands(
    values: &[f64],
    period: usize,
    num_std: f64,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let middle = ema(values, period);
    let n = values.len();
    let mut upper = Vec::with_capacity(n);
    let mut lower = Vec::with_capacity(n);

    for i in 0..n {
        let start = (i + 1).saturating_sub(period);
        let window = &values[start..=i];
        let std = sample_std(window);
        upper.push(middle[i] + num_std * std);
        lower.push(middle[i] - num_std * std);
    }
    (upper, middle, lower)
}

// ── BB Bandwidth / %B incremental ────────────────────────────────────────────

/// Incremental Bollinger Bandwidth from bb_bands_inc results.
///
/// Bandwidth = (upper - lower) / middle.
#[inline]
pub fn bb_bandwidth_inc(upper: f64, middle: f64, lower: f64) -> f64 {
    if middle.abs() > 1e-10 {
        (upper - lower) / middle
    } else {
        0.0
    }
}

/// Incremental Bollinger %B from bb_bands_inc results.
///
/// %B = (close - lower) / (upper - lower).
#[inline]
pub fn bb_percent_b_inc(close: f64, upper: f64, lower: f64) -> f64 {
    let bw = upper - lower;
    if bw > 1e-10 {
        (close - lower) / bw
    } else {
        0.5
    }
}

// ── NATR ──────────────────────────────────────────────────────────────────────

/// Normalized Average True Range — ATR expressed as a percentage of close price.
///
/// `NATR = (ATR / close) * 100`
///
/// Makes volatility comparable across different price levels.
/// Uses existing `atr()` from this module.
pub fn natr(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> Vec<f64> {
    let atr_vals = atr(highs, lows, closes, period);
    atr_vals
        .iter()
        .zip(closes.iter())
        .map(|(&a, &c)| {
            if c.abs() > 1e-14 {
                (a / c) * 100.0
            } else {
                0.0
            }
        })
        .collect()
}

// ── ADR ──────────────────────────────────────────────────────────────────────

/// Average Daily Range — SMA of (High - Low) over `period` bars.
///
/// Returns NaN for the first `period - 1` bars (warmup).
pub fn adr(highs: &[f64], lows: &[f64], period: usize) -> Vec<f64> {
    let n = highs.len();
    let mut out = vec![f64::NAN; n];
    if period < 2 || n < period {
        return out;
    }

    // Compute daily ranges
    let ranges: Vec<f64> = highs.iter().zip(lows.iter()).map(|(&h, &l)| h - l).collect();

    // SMA of ranges
    let mut sum: f64 = ranges[..period].iter().sum();
    out[period - 1] = sum / period as f64;

    for i in period..n {
        sum += ranges[i] - ranges[i - period];
        out[i] = sum / period as f64;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    // ── True Range ───────────────────────────────────────────────────────

    #[test]
    fn true_range_basic() {
        // Simple case: high-low is the largest
        assert_abs_diff_eq!(true_range(110.0, 90.0, 100.0), 20.0, epsilon = 1e-9);
        // Gap up: |high - prev_close| is largest
        assert_abs_diff_eq!(true_range(120.0, 115.0, 100.0), 20.0, epsilon = 1e-9);
        // Gap down: |low - prev_close| is largest
        assert_abs_diff_eq!(true_range(95.0, 80.0, 100.0), 20.0, epsilon = 1e-9);
    }

    // ── ATR _inc ─────────────────────────────────────────────────────────

    #[test]
    fn atr_inc_matches_batch() {
        let n = 40;
        let mut highs = Vec::with_capacity(n);
        let mut lows = Vec::with_capacity(n);
        let mut closes = Vec::with_capacity(n);
        for i in 0..n {
            let base = 100.0 + (i as f64 * 0.5).sin() * 8.0;
            highs.push(base + 3.0);
            lows.push(base - 3.0);
            closes.push(base + 0.5);
        }

        let (batch, last_atr) = atr_with_state(&highs, &lows, &closes, 14);
        assert_eq!(batch.len(), n);

        // Extend by one bar and compare
        let new_h = 115.0;
        let new_l = 109.0;
        let prev_c = *closes.last().unwrap();
        let inc_atr = atr_inc(new_h, new_l, prev_c, last_atr, 14);

        let mut ext_h = highs.clone();
        let mut ext_l = lows.clone();
        let mut ext_c = closes.clone();
        ext_h.push(new_h);
        ext_l.push(new_l);
        ext_c.push(112.0);
        let (ext_batch, _) = atr_with_state(&ext_h, &ext_l, &ext_c, 14);

        assert_abs_diff_eq!(inc_atr, *ext_batch.last().unwrap(), epsilon = 0.1);
    }

    // ── BB Bands _inc ────────────────────────────────────────────────────

    #[test]
    fn bb_bands_inc_matches_batch() {
        let v: Vec<f64> = (0..40).map(|i| 100.0 + (i as f64 * 0.4).sin() * 5.0).collect();
        let period = 20;
        let num_std = 2.0;

        let (batch_upper, batch_mid, batch_lower, last_sum, last_sum_sq) =
            bb_bands_with_state(&v, period, num_std);

        assert_eq!(batch_upper.len(), 40);
        assert_eq!(batch_mid.len(), 40);
        assert_eq!(batch_lower.len(), 40);

        // Upper >= lower always
        for i in 0..40 {
            assert!(batch_upper[i] >= batch_lower[i]);
        }

        // Extend by one value and test inc
        let new_price = 103.0;
        let old_price = v[40 - period]; // the value dropping out
        let (inc_upper, inc_mid, inc_lower, new_sum, new_sum_sq) =
            bb_bands_inc(new_price, old_price, last_sum, last_sum_sq, period, num_std);

        // Verify against full batch with extended series
        let mut extended = v.clone();
        extended.push(new_price);
        let (ext_upper, ext_mid, ext_lower, _, _) =
            bb_bands_with_state(&extended, period, num_std);

        assert_abs_diff_eq!(inc_upper, *ext_upper.last().unwrap(), epsilon = 1e-6);
        assert_abs_diff_eq!(inc_mid, *ext_mid.last().unwrap(), epsilon = 1e-6);
        assert_abs_diff_eq!(inc_lower, *ext_lower.last().unwrap(), epsilon = 1e-6);

        // Verify state carries forward
        assert_abs_diff_eq!(new_sum, last_sum + new_price - old_price, epsilon = 1e-9);
        assert_abs_diff_eq!(
            new_sum_sq,
            last_sum_sq + new_price * new_price - old_price * old_price,
            epsilon = 1e-6
        );
    }

    // ── Keltner _inc ─────────────────────────────────────────────────────

    #[test]
    fn keltner_inc_basic() {
        let (upper, mid, lower) = keltner_inc(100.0, 5.0, 2.0);
        assert_abs_diff_eq!(upper, 110.0, epsilon = 1e-9);
        assert_abs_diff_eq!(mid, 100.0, epsilon = 1e-9);
        assert_abs_diff_eq!(lower, 90.0, epsilon = 1e-9);
    }

    // ── Donchian Channels ─────────────────────────────────────────────────

    #[test]
    fn donchian_basic() {
        let highs = vec![10.0, 12.0, 11.0, 14.0, 13.0, 15.0, 12.0, 16.0];
        let lows = vec![8.0, 9.0, 7.0, 10.0, 11.0, 12.0, 9.0, 13.0];
        let (upper, middle, lower) = donchian_channels(&highs, &lows, 3);

        // First 2 bars are warmup (NaN)
        assert!(upper[0].is_nan());
        assert!(upper[1].is_nan());
        assert!(lower[0].is_nan());
        assert!(middle[0].is_nan());

        // Bar 2 (index 2): max(10,12,11)=12, min(8,9,7)=7, mid=9.5
        assert_abs_diff_eq!(upper[2], 12.0, epsilon = 1e-9);
        assert_abs_diff_eq!(lower[2], 7.0, epsilon = 1e-9);
        assert_abs_diff_eq!(middle[2], 9.5, epsilon = 1e-9);

        // Bar 3 (index 3): max(12,11,14)=14, min(9,7,10)=7, mid=10.5
        assert_abs_diff_eq!(upper[3], 14.0, epsilon = 1e-9);
        assert_abs_diff_eq!(lower[3], 7.0, epsilon = 1e-9);
        assert_abs_diff_eq!(middle[3], 10.5, epsilon = 1e-9);
    }

    #[test]
    fn donchian_inc_matches_batch() {
        let highs = vec![10.0, 12.0, 11.0, 14.0, 13.0, 15.0];
        let lows = vec![8.0, 9.0, 7.0, 10.0, 11.0, 12.0];
        let period = 3;

        let (_, _, _, h_win, l_win) = donchian_with_state(&highs, &lows, period);

        // Extend by one bar
        let new_h = 16.0;
        let new_l = 13.0;
        let (inc_upper, inc_mid, inc_lower, _, _) = donchian_inc(new_h, new_l, &h_win, &l_win);

        // Compare with full batch
        let mut ext_h = highs.clone();
        let mut ext_l = lows.clone();
        ext_h.push(new_h);
        ext_l.push(new_l);
        let (batch_upper, batch_mid, batch_lower) = donchian_channels(&ext_h, &ext_l, period);

        assert_abs_diff_eq!(inc_upper, *batch_upper.last().unwrap(), epsilon = 1e-9);
        assert_abs_diff_eq!(inc_mid, *batch_mid.last().unwrap(), epsilon = 1e-9);
        assert_abs_diff_eq!(inc_lower, *batch_lower.last().unwrap(), epsilon = 1e-9);
    }

    // ── EMA-Bollinger Bands ───────────────────────────────────────────────

    #[test]
    fn e_bollinger_bands_basic() {
        let v: Vec<f64> = (0..30).map(|i| 100.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let (upper, middle, lower) = e_bollinger_bands(&v, 10, 2.0);

        assert_eq!(upper.len(), 30);
        assert_eq!(middle.len(), 30);
        assert_eq!(lower.len(), 30);

        // Upper >= lower always
        for i in 0..30 {
            assert!(upper[i] >= lower[i], "bar {}: upper < lower", i);
        }

        // Middle should be between upper and lower
        for i in 0..30 {
            assert!(middle[i] >= lower[i] - 1e-9, "bar {}: mid < lower", i);
            assert!(middle[i] <= upper[i] + 1e-9, "bar {}: mid > upper", i);
        }
    }

    #[test]
    fn e_bollinger_bands_constant_input() {
        // Constant input → std=0 → upper=middle=lower
        let v = vec![50.0; 20];
        let (upper, middle, lower) = e_bollinger_bands(&v, 5, 2.0);

        for i in 0..20 {
            assert_abs_diff_eq!(upper[i], middle[i], epsilon = 1e-9);
            assert_abs_diff_eq!(lower[i], middle[i], epsilon = 1e-9);
        }
    }

    // ── BB Bandwidth / %B incremental ─────────────────────────────────────

    #[test]
    fn bb_bandwidth_inc_known() {
        // upper=110, mid=100, lower=90 → bw = (110-90)/100 = 0.2
        assert_abs_diff_eq!(bb_bandwidth_inc(110.0, 100.0, 90.0), 0.2, epsilon = 1e-9);
    }

    #[test]
    fn bb_bandwidth_inc_zero_middle() {
        // middle ≈ 0 → returns 0
        assert_abs_diff_eq!(bb_bandwidth_inc(0.01, 0.0, -0.01), 0.0, epsilon = 1e-9);
    }

    #[test]
    fn bb_percent_b_inc_known() {
        // close=105, upper=110, lower=90 → %B = (105-90)/(110-90) = 15/20 = 0.75
        assert_abs_diff_eq!(bb_percent_b_inc(105.0, 110.0, 90.0), 0.75, epsilon = 1e-9);
    }

    #[test]
    fn bb_percent_b_inc_at_lower() {
        // close at lower band → %B = 0
        assert_abs_diff_eq!(bb_percent_b_inc(90.0, 110.0, 90.0), 0.0, epsilon = 1e-9);
    }

    #[test]
    fn bb_percent_b_inc_at_upper() {
        // close at upper band → %B = 1
        assert_abs_diff_eq!(bb_percent_b_inc(110.0, 110.0, 90.0), 1.0, epsilon = 1e-9);
    }

    #[test]
    fn bb_percent_b_inc_zero_bandwidth() {
        // upper ≈ lower → returns 0.5 (fallback)
        assert_abs_diff_eq!(bb_percent_b_inc(100.0, 100.0, 100.0), 0.5, epsilon = 1e-9);
    }

    // ── NATR ──────────────────────────────────────────────────────────────

    #[test]
    fn natr_basic() {
        let highs = vec![110.0, 112.0, 111.0, 114.0, 113.0, 115.0, 112.0, 116.0];
        let lows = vec![98.0, 99.0, 97.0, 100.0, 101.0, 102.0, 99.0, 103.0];
        let closes = vec![105.0, 106.0, 104.0, 108.0, 107.0, 110.0, 105.0, 112.0];
        let result = natr(&highs, &lows, &closes, 3);

        assert_eq!(result.len(), 8);
        // NATR = (ATR / close) * 100 — should be positive where ATR > 0
        for i in 2..8 {
            assert!(result[i] > 0.0, "natr at bar {} should be positive", i);
        }
    }

    #[test]
    fn natr_matches_manual() {
        let highs = vec![110.0, 112.0, 115.0, 114.0, 113.0];
        let lows = vec![100.0, 105.0, 108.0, 107.0, 106.0];
        let closes = vec![105.0, 110.0, 112.0, 110.0, 109.0];
        let atr_vals = atr(&highs, &lows, &closes, 3);
        let natr_vals = natr(&highs, &lows, &closes, 3);

        for i in 0..5 {
            let expected = if closes[i].abs() > 1e-14 {
                (atr_vals[i] / closes[i]) * 100.0
            } else {
                0.0
            };
            assert_abs_diff_eq!(natr_vals[i], expected, epsilon = 1e-9);
        }
    }

    // ── ADR ──────────────────────────────────────────────────────────────

    #[test]
    fn adr_basic() {
        let highs = vec![10.0, 12.0, 15.0, 14.0, 13.0];
        let lows = vec![8.0, 9.0, 11.0, 10.0, 9.0];
        let result = adr(&highs, &lows, 3);

        assert_eq!(result.len(), 5);
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        // Bar 2: ranges = [2, 3, 4], avg = 3.0
        assert_abs_diff_eq!(result[2], 3.0, epsilon = 1e-9);
        // Bar 3: ranges = [3, 4, 4], avg = 11.0/3.0
        assert_abs_diff_eq!(result[3], 11.0 / 3.0, epsilon = 1e-9);
        // Bar 4: ranges = [4, 4, 4], avg = 4.0
        assert_abs_diff_eq!(result[4], 4.0, epsilon = 1e-9);
    }

    #[test]
    fn adr_too_short() {
        let highs = vec![10.0, 12.0];
        let lows = vec![8.0, 9.0];
        let result = adr(&highs, &lows, 5);
        assert!(result.iter().all(|v| v.is_nan()));
    }
}
