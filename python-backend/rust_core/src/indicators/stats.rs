// stats.rs — Statistical primitives used by all indicator modules
//
// kand-Blueprint pattern adopted:
//   batch fn()       — full series computation (NaN for warmup period)
//   fn _inc()        — incremental: prev_state + new_input -> new_value
//   fn _with_state() — batch that also returns final state for _inc() bootstrap
//
// Functions: rolling_sum, rolling_max, rolling_min, variance, stddev, correlation,
//            slope, percent_rank
//
// These are foundational utilities — trend, oscillators, volatility, volume, and
// portfolio modules can (and should) depend on them.

// ── Rolling Sum ────────────────────────────────────────────────────────────────

/// Rolling sum over `period` bars.
///
/// Returns NaN for the first `period - 1` bars (warmup).
pub fn rolling_sum(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    let mut out = vec![f64::NAN; n];
    if period < 2 || n < period {
        return out;
    }

    let mut sum = 0.0;
    for v in values.iter().take(period) {
        sum += v;
    }
    out[period - 1] = sum;

    for i in period..n {
        sum += values[i] - values[i - period];
        out[i] = sum;
    }
    out
}

/// Rolling sum with state — returns (series, last_sum) for `rolling_sum_inc()`.
pub fn rolling_sum_with_state(values: &[f64], period: usize) -> (Vec<f64>, f64) {
    let result = rolling_sum(values, period);
    let last = *result.last().unwrap_or(&f64::NAN);
    (result, last)
}

/// Incremental rolling sum update.
///
/// `new_sum = prev_sum + new_value - old_value`
#[inline]
pub fn rolling_sum_inc(new_value: f64, old_value: f64, prev_sum: f64) -> f64 {
    prev_sum + new_value - old_value
}

// ── Rolling Max ────────────────────────────────────────────────────────────────

/// Rolling maximum over `period` bars.
///
/// Returns NaN for the first `period - 1` bars (warmup).
/// Uses O(period) scan per bar. For streaming, use `rolling_max_inc()`.
pub fn rolling_max(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    let mut out = vec![f64::NAN; n];
    if period < 2 || n < period {
        return out;
    }

    for i in (period - 1)..n {
        let start = i + 1 - period;
        let mut max_val = values[start];
        for v in &values[start + 1..=i] {
            if *v > max_val {
                max_val = *v;
            }
        }
        out[i] = max_val;
    }
    out
}

/// Rolling max with state — returns (series, last window) for `rolling_max_inc()`.
pub fn rolling_max_with_state(values: &[f64], period: usize) -> (Vec<f64>, Vec<f64>) {
    let result = rolling_max(values, period);
    let win_start = values.len().saturating_sub(period);
    let window = values[win_start..].to_vec();
    (result, window)
}

/// Incremental rolling max update.
///
/// Slides the window by one. If the new value >= prev_max, it's the new max.
/// If the dropped value was the max, rescans the window.
///
/// Returns `(new_max, new_window)`.
pub fn rolling_max_inc(new_value: f64, window: &[f64]) -> (f64, Vec<f64>) {
    if window.is_empty() {
        return (new_value, vec![new_value]);
    }
    let mut new_win: Vec<f64> = Vec::with_capacity(window.len());
    for v in &window[1..] {
        new_win.push(*v);
    }
    new_win.push(new_value);

    let max_val = new_win.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    (max_val, new_win)
}

// ── Rolling Min ────────────────────────────────────────────────────────────────

/// Rolling minimum over `period` bars.
///
/// Returns NaN for the first `period - 1` bars (warmup).
pub fn rolling_min(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    let mut out = vec![f64::NAN; n];
    if period < 2 || n < period {
        return out;
    }

    for i in (period - 1)..n {
        let start = i + 1 - period;
        let mut min_val = values[start];
        for v in &values[start + 1..=i] {
            if *v < min_val {
                min_val = *v;
            }
        }
        out[i] = min_val;
    }
    out
}

/// Rolling min with state — returns (series, last window) for `rolling_min_inc()`.
pub fn rolling_min_with_state(values: &[f64], period: usize) -> (Vec<f64>, Vec<f64>) {
    let result = rolling_min(values, period);
    let win_start = values.len().saturating_sub(period);
    let window = values[win_start..].to_vec();
    (result, window)
}

/// Incremental rolling min update.
///
/// Returns `(new_min, new_window)`.
pub fn rolling_min_inc(new_value: f64, window: &[f64]) -> (f64, Vec<f64>) {
    if window.is_empty() {
        return (new_value, vec![new_value]);
    }
    let mut new_win: Vec<f64> = Vec::with_capacity(window.len());
    for v in &window[1..] {
        new_win.push(*v);
    }
    new_win.push(new_value);

    let min_val = new_win.iter().copied().fold(f64::INFINITY, f64::min);
    (min_val, new_win)
}

// ── Variance ───────────────────────────────────────────────────────────────────

/// Rolling population variance over `period` bars.
///
/// Uses running sum / sum_sq for O(1) per-bar after warmup.
/// Returns NaN for the first `period - 1` bars.
///
/// Note: This is **population** variance (/ n), matching kand.
/// For sample variance (/ n-1), use `sample_std()` in volatility.rs.
pub fn variance(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    let mut out = vec![f64::NAN; n];
    if period < 2 || n < period {
        return out;
    }

    let mut sum = 0.0;
    let mut sum_sq = 0.0;
    for v in values.iter().take(period) {
        sum += v;
        sum_sq += v * v;
    }
    let p = period as f64;
    let mean = sum / p;
    out[period - 1] = (sum_sq / p) - mean * mean;

    for i in period..n {
        let old = values[i - period];
        let new_val = values[i];
        sum += new_val - old;
        sum_sq += new_val * new_val - old * old;
        let mean = sum / p;
        out[i] = (sum_sq / p) - mean * mean;
    }
    out
}

/// Variance with state — returns (series, last_sum, last_sum_sq) for `variance_inc()`.
pub fn variance_with_state(values: &[f64], period: usize) -> (Vec<f64>, f64, f64) {
    let n = values.len();
    let result = variance(values, period);
    if n < period || period < 2 {
        return (result, 0.0, 0.0);
    }

    // Reconstruct final running sum/sum_sq
    let start = n - period;
    let sum: f64 = values[start..].iter().sum();
    let sum_sq: f64 = values[start..].iter().map(|v| v * v).sum();
    (result, sum, sum_sq)
}

/// Incremental variance update.
///
/// Returns `(variance, new_sum, new_sum_sq)`.
#[inline]
pub fn variance_inc(
    new_value: f64,
    old_value: f64,
    prev_sum: f64,
    prev_sum_sq: f64,
    period: usize,
) -> (f64, f64, f64) {
    let new_sum = prev_sum + new_value - old_value;
    let new_sum_sq = prev_sum_sq + new_value * new_value - old_value * old_value;
    let p = period as f64;
    let mean = new_sum / p;
    let var = (new_sum_sq / p) - mean * mean;
    (var, new_sum, new_sum_sq)
}

// ── Standard Deviation ─────────────────────────────────────────────────────────

/// Rolling population standard deviation — sqrt(variance).
///
/// Returns NaN for the first `period - 1` bars.
pub fn stddev(values: &[f64], period: usize) -> Vec<f64> {
    let var = variance(values, period);
    var.into_iter()
        .map(|v| if v.is_nan() { f64::NAN } else if v > 0.0 { v.sqrt() } else { 0.0 })
        .collect()
}

/// Stddev with state — returns (series, last_sum, last_sum_sq) for `stddev_inc()`.
pub fn stddev_with_state(values: &[f64], period: usize) -> (Vec<f64>, f64, f64) {
    let (var_series, sum, sum_sq) = variance_with_state(values, period);
    let std_series: Vec<f64> = var_series
        .into_iter()
        .map(|v| if v.is_nan() { f64::NAN } else if v > 0.0 { v.sqrt() } else { 0.0 })
        .collect();
    (std_series, sum, sum_sq)
}

/// Incremental stddev update.
///
/// Returns `(stddev, new_sum, new_sum_sq)`.
#[inline]
pub fn stddev_inc(
    new_value: f64,
    old_value: f64,
    prev_sum: f64,
    prev_sum_sq: f64,
    period: usize,
) -> (f64, f64, f64) {
    let (var, new_sum, new_sum_sq) = variance_inc(new_value, old_value, prev_sum, prev_sum_sq, period);
    let std = if var > 0.0 { var.sqrt() } else { 0.0 };
    (std, new_sum, new_sum_sq)
}

// ── Pearson Correlation ────────────────────────────────────────────────────────

/// Rolling Pearson correlation between two series over `period` bars.
///
/// Returns NaN for the first `period - 1` bars and when either series has zero variance.
pub fn correlation(x: &[f64], y: &[f64], period: usize) -> Vec<f64> {
    let n = x.len().min(y.len());
    let mut out = vec![f64::NAN; n];
    if period < 2 || n < period {
        return out;
    }

    let p = period as f64;
    let mut sx = 0.0;
    let mut sy = 0.0;
    let mut sxx = 0.0;
    let mut syy = 0.0;
    let mut sxy = 0.0;

    for i in 0..period {
        sx += x[i];
        sy += y[i];
        sxx += x[i] * x[i];
        syy += y[i] * y[i];
        sxy += x[i] * y[i];
    }

    let num = p * sxy - sx * sy;
    let den0 = p * sxx - sx * sx;
    let den1 = p * syy - sy * sy;
    let den = (den0 * den1).sqrt();
    out[period - 1] = if den > 0.0 { num / den } else { f64::NAN };

    for i in period..n {
        let ox = x[i - period];
        let oy = y[i - period];
        sx += x[i] - ox;
        sy += y[i] - oy;
        sxx += x[i] * x[i] - ox * ox;
        syy += y[i] * y[i] - oy * oy;
        sxy += x[i] * y[i] - ox * oy;

        let num = p * sxy - sx * sy;
        let den0 = p * sxx - sx * sx;
        let den1 = p * syy - sy * sy;
        let den = (den0 * den1).sqrt();
        out[i] = if den > 0.0 { num / den } else { f64::NAN };
    }
    out
}

/// Correlation state for incremental updates.
pub struct CorrelState {
    pub sx: f64,
    pub sy: f64,
    pub sxx: f64,
    pub syy: f64,
    pub sxy: f64,
}

/// Correlation with state — returns (series, CorrelState) for `correlation_inc()`.
pub fn correlation_with_state(x: &[f64], y: &[f64], period: usize) -> (Vec<f64>, CorrelState) {
    let n = x.len().min(y.len());
    let result = correlation(x, y, period);

    if n < period || period < 2 {
        return (result, CorrelState { sx: 0.0, sy: 0.0, sxx: 0.0, syy: 0.0, sxy: 0.0 });
    }

    let start = n - period;
    let mut sx = 0.0;
    let mut sy = 0.0;
    let mut sxx = 0.0;
    let mut syy = 0.0;
    let mut sxy = 0.0;
    for i in start..n {
        sx += x[i];
        sy += y[i];
        sxx += x[i] * x[i];
        syy += y[i] * y[i];
        sxy += x[i] * y[i];
    }

    (result, CorrelState { sx, sy, sxx, syy, sxy })
}

/// Incremental correlation update.
///
/// Returns `(correlation, new_state)`.
pub fn correlation_inc(
    new_x: f64,
    new_y: f64,
    old_x: f64,
    old_y: f64,
    state: &CorrelState,
    period: usize,
) -> (f64, CorrelState) {
    let sx = state.sx + new_x - old_x;
    let sy = state.sy + new_y - old_y;
    let sxx = state.sxx + new_x * new_x - old_x * old_x;
    let syy = state.syy + new_y * new_y - old_y * old_y;
    let sxy = state.sxy + new_x * new_y - old_x * old_y;

    let p = period as f64;
    let num = p * sxy - sx * sy;
    let den0 = p * sxx - sx * sx;
    let den1 = p * syy - sy * sy;
    let den = (den0 * den1).sqrt();
    let corr = if den > 0.0 { num / den } else { f64::NAN };

    (corr, CorrelState { sx, sy, sxx, syy, sxy })
}

// ── Slope ─────────────────────────────────────────────────────────────────────

/// Linear slope over `period` bars: `(values[i] - values[i - period]) / period`.
///
/// Returns 0.0 for the first `period` bars (warmup).
/// Python ref: `helpers.py::slope()` — used by Rainbow, Composite Signal, Regime Detection.
pub fn slope(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    let mut out = vec![0.0; n];
    if period == 0 {
        return out;
    }
    let p = period as f64;
    for i in period..n {
        out[i] = (values[i] - values[i - period]) / p;
    }
    out
}

/// Slope with state — returns (series, last_value, value_at_lag) for `slope_inc()`.
pub fn slope_with_state(values: &[f64], period: usize) -> (Vec<f64>, f64, f64) {
    let result = slope(values, period);
    let n = values.len();
    if n == 0 || period == 0 {
        return (result, 0.0, 0.0);
    }
    let last = *values.last().unwrap();
    let lag = if n > period { values[n - period] } else { values[0] };
    (result, last, lag)
}

/// Incremental slope update.
///
/// `new_value` is the current bar's value, `old_value` is the value `period` bars ago.
#[inline]
pub fn slope_inc(new_value: f64, old_value: f64, period: usize) -> f64 {
    (new_value - old_value) / period as f64
}

// ── Percent Rank ──────────────────────────────────────────────────────────────

/// Percent rank: what % of the last `period` values are strictly < current value.
///
/// Returns 0–100 scale. First bar with window <= 1 returns 50.0.
/// Python ref: `oscillators.py::percent_rank()` — Connors RSI component.
pub fn percent_rank(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    let mut out = vec![0.0; n];
    for i in 0..n {
        let start = if i + 1 > period { i + 1 - period } else { 0 };
        let window_len = i + 1 - start;
        if window_len <= 1 {
            out[i] = 50.0;
            continue;
        }
        let current = values[i];
        let mut count = 0usize;
        for j in start..=i {
            if values[j] < current {
                count += 1;
            }
        }
        out[i] = count as f64 / window_len as f64 * 100.0;
    }
    out
}

/// Percent rank with state — returns (series, last window) for `percent_rank_inc()`.
pub fn percent_rank_with_state(values: &[f64], period: usize) -> (Vec<f64>, Vec<f64>) {
    let result = percent_rank(values, period);
    let n = values.len();
    let start = n.saturating_sub(period);
    let window = values[start..].to_vec();
    (result, window)
}

/// Incremental percent rank update.
///
/// Slides the window, counts how many values in the new window are strictly < new_value.
/// Returns `(percent_rank, new_window)`.
pub fn percent_rank_inc(new_value: f64, window: &[f64]) -> (f64, Vec<f64>) {
    let mut new_win: Vec<f64> = Vec::with_capacity(window.len());
    // Drop oldest, add newest
    for v in &window[1..] {
        new_win.push(*v);
    }
    new_win.push(new_value);

    let wlen = new_win.len();
    if wlen <= 1 {
        return (50.0, new_win);
    }
    let count = new_win.iter().filter(|&&v| v < new_value).count();
    let rank = count as f64 / wlen as f64 * 100.0;
    (rank, new_win)
}

// ── Midpoint ────────────────────────────────────────────────────────────────

/// Midpoint — `(highest(values, period) + lowest(values, period)) / 2`.
///
/// Returns NaN for the first `period - 1` bars (warmup).
pub fn midpoint(values: &[f64], period: usize) -> Vec<f64> {
    let hi = rolling_max(values, period);
    let lo = rolling_min(values, period);
    hi.iter()
        .zip(lo.iter())
        .map(|(&h, &l)| {
            if h.is_nan() || l.is_nan() {
                f64::NAN
            } else {
                (h + l) / 2.0
            }
        })
        .collect()
}

// ── Midprice ────────────────────────────────────────────────────────────────

/// Midprice — `(highest(highs, period) + lowest(lows, period)) / 2`.
///
/// Returns NaN for the first `period - 1` bars (warmup).
pub fn midprice(highs: &[f64], lows: &[f64], period: usize) -> Vec<f64> {
    let hi = rolling_max(highs, period);
    let lo = rolling_min(lows, period);
    hi.iter()
        .zip(lo.iter())
        .map(|(&h, &l)| {
            if h.is_nan() || l.is_nan() {
                f64::NAN
            } else {
                (h + l) / 2.0
            }
        })
        .collect()
}

// ── Future Value ────────────────────────────────────────────────────────────

/// Future value of a present value compounded at a given rate.
///
/// `FV = pv * (1 + rate)^periods`
#[inline]
pub fn future_value(pv: f64, rate: f64, periods: u32) -> f64 {
    pv * (1.0 + rate).powi(periods as i32)
}

// ── NPER ────────────────────────────────────────────────────────────────────

/// Number of compounding periods to grow `pv` to `fv` at given `rate`.
///
/// `nper = ln(fv / pv) / ln(1 + rate)`
///
/// Returns NaN if inputs are invalid (rate <= 0, pv <= 0, fv <= 0, fv <= pv with rate > 0).
#[inline]
pub fn nper(rate: f64, pv: f64, fv: f64) -> f64 {
    if rate <= 0.0 || pv <= 0.0 || fv <= 0.0 {
        return f64::NAN;
    }
    (fv / pv).ln() / (1.0 + rate).ln()
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    // ── Rolling Sum ─────────────────────────────────────────────────────

    #[test]
    fn rolling_sum_basic() {
        let v = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = rolling_sum(&v, 3);
        assert_eq!(result.len(), 5);
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        assert_abs_diff_eq!(result[2], 6.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[3], 9.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[4], 12.0, epsilon = 1e-9);
    }

    #[test]
    fn rolling_sum_inc_matches_batch() {
        let n = 40;
        let v: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.5).sin() * 10.0).collect();
        let period = 14;

        let (batch, last_sum) = rolling_sum_with_state(&v, period);
        assert_eq!(batch.len(), n);

        let new_val = 107.0;
        let old_val = v[n - period];
        let inc_sum = rolling_sum_inc(new_val, old_val, last_sum);

        let mut ext = v.clone();
        ext.push(new_val);
        let (ext_batch, _) = rolling_sum_with_state(&ext, period);
        assert_abs_diff_eq!(inc_sum, *ext_batch.last().unwrap(), epsilon = 1e-9);
    }

    // ── Rolling Max ─────────────────────────────────────────────────────

    #[test]
    fn rolling_max_basic() {
        let v = vec![3.0, 1.0, 4.0, 1.0, 5.0, 2.0];
        let result = rolling_max(&v, 3);
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        assert_abs_diff_eq!(result[2], 4.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[3], 4.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[4], 5.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[5], 5.0, epsilon = 1e-9);
    }

    #[test]
    fn rolling_max_inc_matches_batch() {
        let n = 40;
        let v: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0).collect();
        let period = 14;

        let (batch, window) = rolling_max_with_state(&v, period);
        assert_eq!(batch.len(), n);
        assert_eq!(window.len(), period);

        let new_val = 115.0;
        let (inc_max, new_win) = rolling_max_inc(new_val, &window);

        let mut ext = v.clone();
        ext.push(new_val);
        let (ext_batch, ext_win) = rolling_max_with_state(&ext, period);
        assert_abs_diff_eq!(inc_max, *ext_batch.last().unwrap(), epsilon = 1e-9);
        for j in 0..new_win.len() {
            assert_abs_diff_eq!(new_win[j], ext_win[j], epsilon = 1e-9);
        }
    }

    // ── Rolling Min ─────────────────────────────────────────────────────

    #[test]
    fn rolling_min_basic() {
        let v = vec![3.0, 1.0, 4.0, 1.0, 5.0, 2.0];
        let result = rolling_min(&v, 3);
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        assert_abs_diff_eq!(result[2], 1.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[3], 1.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[4], 1.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[5], 1.0, epsilon = 1e-9);
    }

    #[test]
    fn rolling_min_inc_matches_batch() {
        let n = 40;
        let v: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0).collect();
        let period = 14;

        let (batch, window) = rolling_min_with_state(&v, period);
        assert_eq!(batch.len(), n);

        let new_val = 88.0;
        let (inc_min, new_win) = rolling_min_inc(new_val, &window);

        let mut ext = v.clone();
        ext.push(new_val);
        let (ext_batch, ext_win) = rolling_min_with_state(&ext, period);
        assert_abs_diff_eq!(inc_min, *ext_batch.last().unwrap(), epsilon = 1e-9);
        for j in 0..new_win.len() {
            assert_abs_diff_eq!(new_win[j], ext_win[j], epsilon = 1e-9);
        }
    }

    // ── Variance ────────────────────────────────────────────────────────

    #[test]
    fn variance_basic() {
        // [1,2,3] → mean=2, var = ((1-2)²+(2-2)²+(3-2)²)/3 = 2/3
        let v = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = variance(&v, 3);
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        assert_abs_diff_eq!(result[2], 2.0 / 3.0, epsilon = 1e-9);
        // [2,3,4] → mean=3, var = 2/3
        assert_abs_diff_eq!(result[3], 2.0 / 3.0, epsilon = 1e-9);
    }

    #[test]
    fn variance_inc_matches_batch() {
        let n = 40;
        let v: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.4).sin() * 5.0).collect();
        let period = 14;

        let (batch, sum, sum_sq) = variance_with_state(&v, period);
        assert_eq!(batch.len(), n);

        let new_val = 103.0;
        let old_val = v[n - period];
        let (inc_var, new_sum, new_sum_sq) = variance_inc(new_val, old_val, sum, sum_sq, period);

        let mut ext = v.clone();
        ext.push(new_val);
        let (ext_batch, ext_sum, ext_sum_sq) = variance_with_state(&ext, period);
        assert_abs_diff_eq!(inc_var, *ext_batch.last().unwrap(), epsilon = 1e-6);
        assert_abs_diff_eq!(new_sum, ext_sum, epsilon = 1e-6);
        assert_abs_diff_eq!(new_sum_sq, ext_sum_sq, epsilon = 1e-4);
    }

    // ── Stddev ──────────────────────────────────────────────────────────

    #[test]
    fn stddev_basic() {
        let v = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = stddev(&v, 3);
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        // sqrt(2/3) ≈ 0.8165
        assert_abs_diff_eq!(result[2], (2.0_f64 / 3.0).sqrt(), epsilon = 1e-9);
    }

    #[test]
    fn stddev_inc_matches_batch() {
        let n = 40;
        let v: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.4).sin() * 5.0).collect();
        let period = 14;

        let (batch, sum, sum_sq) = stddev_with_state(&v, period);
        assert_eq!(batch.len(), n);

        let new_val = 103.0;
        let old_val = v[n - period];
        let (inc_std, _new_sum, _new_sum_sq) = stddev_inc(new_val, old_val, sum, sum_sq, period);

        let mut ext = v.clone();
        ext.push(new_val);
        let (ext_batch, _, _) = stddev_with_state(&ext, period);
        assert_abs_diff_eq!(inc_std, *ext_batch.last().unwrap(), epsilon = 1e-6);
    }

    #[test]
    fn stddev_constant_is_zero() {
        let v = vec![5.0; 20];
        let result = stddev(&v, 10);
        for i in 9..20 {
            assert_abs_diff_eq!(result[i], 0.0, epsilon = 1e-9);
        }
    }

    // ── Correlation ─────────────────────────────────────────────────────

    #[test]
    fn correlation_perfect_positive() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0];
        let y = vec![2.0, 4.0, 6.0, 8.0, 10.0, 12.0]; // y = 2x
        let result = correlation(&x, &y, 3);
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        for i in 2..6 {
            assert_abs_diff_eq!(result[i], 1.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn correlation_perfect_negative() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let y = vec![9.0, 8.0, 7.0, 6.0, 5.0]; // y = -x + 10
        let result = correlation(&x, &y, 3);
        for i in 2..5 {
            assert_abs_diff_eq!(result[i], -1.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn correlation_zero_variance_is_nan() {
        let x = vec![5.0, 5.0, 5.0, 5.0];
        let y = vec![1.0, 2.0, 3.0, 4.0];
        let result = correlation(&x, &y, 3);
        for i in 2..4 {
            assert!(result[i].is_nan());
        }
    }

    #[test]
    fn correlation_inc_matches_batch() {
        let n = 40;
        let period = 14;
        let x: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0).collect();
        let y: Vec<f64> = (0..n).map(|i| 50.0 + (i as f64 * 0.3).cos() * 5.0).collect();

        let (batch, state) = correlation_with_state(&x, &y, period);
        assert_eq!(batch.len(), n);

        let new_x = 105.0;
        let new_y = 52.0;
        let old_x = x[n - period];
        let old_y = y[n - period];
        let (inc_corr, _new_state) = correlation_inc(new_x, new_y, old_x, old_y, &state, period);

        let mut ext_x = x.clone();
        let mut ext_y = y.clone();
        ext_x.push(new_x);
        ext_y.push(new_y);
        let (ext_batch, _) = correlation_with_state(&ext_x, &ext_y, period);
        assert_abs_diff_eq!(inc_corr, *ext_batch.last().unwrap(), epsilon = 1e-6);
    }

    #[test]
    fn correlation_inc_multi_step() {
        let n = 40;
        let period = 10;
        let all_x: Vec<f64> = (0..n + 5).map(|i| 100.0 + (i as f64 * 0.5).sin() * 8.0).collect();
        let all_y: Vec<f64> = (0..n + 5).map(|i| 200.0 + (i as f64 * 0.5).cos() * 12.0).collect();

        let (batch_init, mut state) = correlation_with_state(&all_x[..n], &all_y[..n], period);
        assert_eq!(batch_init.len(), n);

        for step in 0..5 {
            let idx = n + step;
            let old_x = all_x[idx - period];
            let old_y = all_y[idx - period];
            let (inc_corr, new_state) =
                correlation_inc(all_x[idx], all_y[idx], old_x, old_y, &state, period);

            let (full_batch, _) = correlation_with_state(&all_x[..=idx], &all_y[..=idx], period);
            assert_abs_diff_eq!(inc_corr, *full_batch.last().unwrap(), epsilon = 1e-6);

            state = new_state;
        }
    }

    // ── Slope ────────────────────────────────────────────────────────────

    #[test]
    fn slope_basic() {
        let v = vec![10.0, 12.0, 15.0, 13.0, 18.0];
        let result = slope(&v, 2);
        assert_eq!(result.len(), 5);
        assert_abs_diff_eq!(result[0], 0.0, epsilon = 1e-9); // warmup
        assert_abs_diff_eq!(result[1], 0.0, epsilon = 1e-9); // warmup
        assert_abs_diff_eq!(result[2], (15.0 - 10.0) / 2.0, epsilon = 1e-9); // 2.5
        assert_abs_diff_eq!(result[3], (13.0 - 12.0) / 2.0, epsilon = 1e-9); // 0.5
        assert_abs_diff_eq!(result[4], (18.0 - 15.0) / 2.0, epsilon = 1e-9); // 1.5
    }

    #[test]
    fn slope_inc_matches_batch() {
        let n = 40;
        let period = 5;
        let v: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.4).sin() * 8.0).collect();

        let (batch, _last, _lag) = slope_with_state(&v, period);
        assert_eq!(batch.len(), n);

        let new_val = 105.0;
        let old_val = v[n - period]; // value that was `period` bars ago
        let inc_slope = slope_inc(new_val, old_val, period);

        let mut ext = v.clone();
        ext.push(new_val);
        let full = slope(&ext, period);
        assert_abs_diff_eq!(inc_slope, *full.last().unwrap(), epsilon = 1e-9);
    }

    #[test]
    fn slope_flat_is_zero() {
        let v = vec![5.0; 20];
        let result = slope(&v, 10);
        for val in &result {
            assert_abs_diff_eq!(*val, 0.0, epsilon = 1e-9);
        }
    }

    // ── Percent Rank ─────────────────────────────────────────────────────

    #[test]
    fn percent_rank_basic() {
        // [1, 2, 3, 4, 5] with period 3
        let v = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = percent_rank(&v, 3);
        assert_eq!(result.len(), 5);
        // i=0: window=[1], len=1 → 50.0
        assert_abs_diff_eq!(result[0], 50.0, epsilon = 1e-9);
        // i=1: window=[1,2], current=2, count(< 2)=1, rank=1/2*100=50.0
        assert_abs_diff_eq!(result[1], 50.0, epsilon = 1e-9);
        // i=2: window=[1,2,3], current=3, count(< 3)=2, rank=2/3*100=66.67
        assert_abs_diff_eq!(result[2], 200.0 / 3.0, epsilon = 1e-9);
        // i=3: window=[2,3,4], current=4, count(< 4)=2, rank=2/3*100=66.67
        assert_abs_diff_eq!(result[3], 200.0 / 3.0, epsilon = 1e-9);
        // i=4: window=[3,4,5], current=5, count(< 5)=2, rank=2/3*100=66.67
        assert_abs_diff_eq!(result[4], 200.0 / 3.0, epsilon = 1e-9);
    }

    #[test]
    fn percent_rank_all_equal() {
        let v = vec![5.0; 10];
        let result = percent_rank(&v, 5);
        // All values equal → count(< 5.0) = 0 → rank = 0.0
        for i in 1..10 {
            assert_abs_diff_eq!(result[i], 0.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn percent_rank_inc_matches_batch() {
        let n = 40;
        let period = 10;
        let v: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.5).sin() * 8.0).collect();

        let (batch, window) = percent_rank_with_state(&v, period);
        assert_eq!(batch.len(), n);
        assert_eq!(window.len(), period);

        let new_val = 103.0;
        let (inc_rank, new_win) = percent_rank_inc(new_val, &window);

        let mut ext = v.clone();
        ext.push(new_val);
        let (ext_batch, ext_win) = percent_rank_with_state(&ext, period);
        assert_abs_diff_eq!(inc_rank, *ext_batch.last().unwrap(), epsilon = 1e-9);
        assert_eq!(new_win.len(), ext_win.len());
        for j in 0..new_win.len() {
            assert_abs_diff_eq!(new_win[j], ext_win[j], epsilon = 1e-9);
        }
    }

    #[test]
    fn percent_rank_inc_multi_step() {
        let n = 30;
        let period = 8;
        let all: Vec<f64> = (0..n + 5).map(|i| 50.0 + (i as f64 * 0.7).sin() * 15.0).collect();

        let (_batch, mut window) = percent_rank_with_state(&all[..n], period);

        for step in 0..5 {
            let idx = n + step;
            let (inc_rank, new_win) = percent_rank_inc(all[idx], &window);

            let full = percent_rank(&all[..=idx], period);
            assert_abs_diff_eq!(inc_rank, *full.last().unwrap(), epsilon = 1e-9);

            window = new_win;
        }
    }

    // ── Midpoint ──────────────────────────────────────────────────────

    #[test]
    fn midpoint_basic() {
        let v = vec![3.0, 1.0, 4.0, 1.0, 5.0, 2.0];
        let result = midpoint(&v, 3);
        assert_eq!(result.len(), 6);
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        // Bar 2: max(3,1,4)=4, min(3,1,4)=1, mid=2.5
        assert_abs_diff_eq!(result[2], 2.5, epsilon = 1e-9);
        // Bar 3: max(1,4,1)=4, min(1,4,1)=1, mid=2.5
        assert_abs_diff_eq!(result[3], 2.5, epsilon = 1e-9);
        // Bar 4: max(4,1,5)=5, min(4,1,5)=1, mid=3.0
        assert_abs_diff_eq!(result[4], 3.0, epsilon = 1e-9);
        // Bar 5: max(1,5,2)=5, min(1,5,2)=1, mid=3.0
        assert_abs_diff_eq!(result[5], 3.0, epsilon = 1e-9);
    }

    // ── Midprice ──────────────────────────────────────────────────────

    #[test]
    fn midprice_basic() {
        let highs = vec![10.0, 12.0, 11.0, 14.0, 13.0, 15.0];
        let lows  = vec![8.0,  9.0,  7.0,  10.0, 11.0, 12.0];
        let result = midprice(&highs, &lows, 3);
        assert_eq!(result.len(), 6);
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        // Bar 2: max(10,12,11)=12, min(8,9,7)=7, mid=9.5
        assert_abs_diff_eq!(result[2], 9.5, epsilon = 1e-9);
        // Bar 3: max(12,11,14)=14, min(9,7,10)=7, mid=10.5
        assert_abs_diff_eq!(result[3], 10.5, epsilon = 1e-9);
    }

    // ── Future Value ──────────────────────────────────────────────────

    #[test]
    fn future_value_basic() {
        // $1000 at 5% for 10 years
        let fv = future_value(1000.0, 0.05, 10);
        assert_abs_diff_eq!(fv, 1000.0 * 1.05_f64.powi(10), epsilon = 1e-6);
    }

    #[test]
    fn future_value_zero_rate() {
        let fv = future_value(1000.0, 0.0, 10);
        assert_abs_diff_eq!(fv, 1000.0, epsilon = 1e-9);
    }

    // ── NPER ──────────────────────────────────────────────────────────

    #[test]
    fn nper_basic() {
        // How many years to double at 7%?
        let n = nper(0.07, 1000.0, 2000.0);
        // ln(2) / ln(1.07) ≈ 10.245
        assert_abs_diff_eq!(n, (2.0_f64).ln() / (1.07_f64).ln(), epsilon = 1e-9);
    }

    #[test]
    fn nper_invalid_rate() {
        assert!(nper(0.0, 1000.0, 2000.0).is_nan());
        assert!(nper(-0.05, 1000.0, 2000.0).is_nan());
    }

    #[test]
    fn nper_roundtrip_with_fv() {
        let rate = 0.1;
        let pv = 500.0;
        let periods = 5;
        let fv = future_value(pv, rate, periods);
        let computed_periods = nper(rate, pv, fv);
        assert_abs_diff_eq!(computed_periods, periods as f64, epsilon = 1e-9);
    }
}
