// oscillators.rs — Momentum oscillators + composite signals
//
// Mirrors Python: indicator_engine/oscillators.py
// Migrated from lib.rs: rsi, macd_components, stochastic, wilder_sum, wilder_avg, adx_components
// Merged from composite.rs: composite_sma50_slope_norm_impl, calculate_heartbeat_impl
//
// kand-Blueprint pattern adopted:
//   batch fn()       — full series computation
//   fn _inc()        — incremental: prev_state + new_input -> new_value
// kand new (future): CCI, MOM, WILLR, Aroon, AroonOsc, ADXR, BOP, ROC

use crate::helper;

use super::stats::percent_rank;
use super::trend::{ema_seed_first as ema, ema_inc, sma};

// ── RSI ──────────────────────────────────────────────────────────────────────

/// Wilder RSI — SMA warmup for first `period` changes, then Wilder smoothing.
/// Returns vec of length `values.len()`, warmup values filled with 50.0.
pub fn rsi(values: &[f64], period: usize) -> Vec<f64> {
    if values.len() < 2 {
        return vec![50.0; values.len()];
    }
    let mut gains = vec![0.0_f64];
    let mut losses = vec![0.0_f64];
    for i in 1..values.len() {
        let delta = values[i] - values[i - 1];
        gains.push(if delta > 0.0 { delta } else { 0.0 });
        losses.push(if delta < 0.0 { -delta } else { 0.0 });
    }
    let n = gains.len();
    let mut out = vec![50.0_f64; n];
    if n <= period {
        return out;
    }
    let mut avg_gain: f64 = gains[1..=period].iter().sum::<f64>() / period as f64;
    let mut avg_loss: f64 = losses[1..=period].iter().sum::<f64>() / period as f64;
    out[period] = if avg_loss == 0.0 {
        100.0
    } else {
        100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    };
    let p = period as f64;
    for i in (period + 1)..n {
        avg_gain = (avg_gain * (p - 1.0) + gains[i]) / p;
        avg_loss = (avg_loss * (p - 1.0) + losses[i]) / p;
        out[i] = if avg_loss == 0.0 {
            100.0
        } else {
            100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
        };
    }
    out
}

/// RSI with state — same as `rsi()` but also returns final (avg_gain, avg_loss)
/// for use with `rsi_inc()`.
pub fn rsi_with_state(values: &[f64], period: usize) -> (Vec<f64>, f64, f64) {
    if values.len() < 2 {
        return (vec![50.0; values.len()], 0.0, 0.0);
    }
    let mut gains = vec![0.0_f64];
    let mut losses = vec![0.0_f64];
    for i in 1..values.len() {
        let delta = values[i] - values[i - 1];
        gains.push(if delta > 0.0 { delta } else { 0.0 });
        losses.push(if delta < 0.0 { -delta } else { 0.0 });
    }
    let n = gains.len();
    let mut out = vec![50.0_f64; n];
    if n <= period {
        return (out, 0.0, 0.0);
    }
    let mut avg_gain: f64 = gains[1..=period].iter().sum::<f64>() / period as f64;
    let mut avg_loss: f64 = losses[1..=period].iter().sum::<f64>() / period as f64;
    out[period] = if avg_loss == 0.0 {
        100.0
    } else {
        100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    };
    let p = period as f64;
    for i in (period + 1)..n {
        avg_gain = (avg_gain * (p - 1.0) + gains[i]) / p;
        avg_loss = (avg_loss * (p - 1.0) + losses[i]) / p;
        out[i] = if avg_loss == 0.0 {
            100.0
        } else {
            100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
        };
    }
    (out, avg_gain, avg_loss)
}

/// Incremental RSI update.
///
/// Given current + previous price and the previous avg_gain/avg_loss state,
/// returns `(new_rsi, new_avg_gain, new_avg_loss)` in O(1).
///
/// Bootstrap state from `rsi_with_state()` or by running batch RSI first.
///
/// Formula (Wilder smoothing):
/// ```text
/// avg_gain = (prev_avg_gain * (period-1) + curr_gain) / period
/// avg_loss = (prev_avg_loss * (period-1) + curr_loss) / period
/// RS = avg_gain / avg_loss
/// RSI = 100 - 100/(1+RS)
/// ```
#[inline]
pub fn rsi_inc(
    curr_price: f64,
    prev_price: f64,
    prev_avg_gain: f64,
    prev_avg_loss: f64,
    period: usize,
) -> (f64, f64, f64) {
    let diff = curr_price - prev_price;
    let (curr_gain, curr_loss) = if diff > 0.0 {
        (diff, 0.0)
    } else {
        (0.0, diff.abs())
    };
    let p = period as f64;
    let avg_gain = (prev_avg_gain * (p - 1.0) + curr_gain) / p;
    let avg_loss = (prev_avg_loss * (p - 1.0) + curr_loss) / p;
    let rsi_val = if avg_loss == 0.0 {
        100.0
    } else {
        let rs = avg_gain / avg_loss;
        100.0 - 100.0 / (1.0 + rs)
    };
    (rsi_val, avg_gain, avg_loss)
}

// ── MACD ─────────────────────────────────────────────────────────────────────

/// MACD — returns (macd_line, signal_line, histogram).
pub fn macd_components(
    closes: &[f64],
    fast: usize,
    slow: usize,
    signal: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let ema_fast = ema(closes, fast);
    let ema_slow = ema(closes, slow);
    let macd_line: Vec<f64> = ema_fast
        .iter()
        .zip(ema_slow.iter())
        .map(|(f, s)| f - s)
        .collect();
    let signal_line = ema(&macd_line, signal);
    let hist: Vec<f64> = macd_line
        .iter()
        .zip(signal_line.iter())
        .map(|(m, s)| m - s)
        .collect();
    (macd_line, signal_line, hist)
}

/// MACD with state — same as `macd_components()` but also returns final
/// (fast_ema, slow_ema, signal_ema) for use with `macd_inc()`.
pub fn macd_with_state(
    closes: &[f64],
    fast: usize,
    slow: usize,
    signal: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>, f64, f64, f64) {
    let ema_fast = ema(closes, fast);
    let ema_slow = ema(closes, slow);
    let macd_line: Vec<f64> = ema_fast
        .iter()
        .zip(ema_slow.iter())
        .map(|(f, s)| f - s)
        .collect();
    let signal_line = ema(&macd_line, signal);
    let hist: Vec<f64> = macd_line
        .iter()
        .zip(signal_line.iter())
        .map(|(m, s)| m - s)
        .collect();
    let last_fast = *ema_fast.last().unwrap_or(&0.0);
    let last_slow = *ema_slow.last().unwrap_or(&0.0);
    let last_signal = *signal_line.last().unwrap_or(&0.0);
    (macd_line, signal_line, hist, last_fast, last_slow, last_signal)
}

/// Incremental MACD update.
///
/// Given a new price and previous EMA states, returns
/// `(macd_value, signal_value, histogram)` in O(1).
///
/// Bootstrap state from `macd_with_state()`.
///
/// Formula:
/// ```text
/// fast_ema  = ema_inc(price, prev_fast_ema, fast_period)
/// slow_ema  = ema_inc(price, prev_slow_ema, slow_period)
/// macd      = fast_ema - slow_ema
/// signal    = ema_inc(macd, prev_signal, signal_period)
/// histogram = macd - signal
/// ```
#[inline]
pub fn macd_inc(
    price: f64,
    prev_fast_ema: f64,
    prev_slow_ema: f64,
    prev_signal: f64,
    fast_period: usize,
    slow_period: usize,
    signal_period: usize,
) -> (f64, f64, f64) {
    let fast = ema_inc(price, prev_fast_ema, fast_period, None);
    let slow = ema_inc(price, prev_slow_ema, slow_period, None);
    let macd_val = fast - slow;
    let signal_val = ema_inc(macd_val, prev_signal, signal_period, None);
    let hist = macd_val - signal_val;
    (macd_val, signal_val, hist)
}

// ── Stochastic ───────────────────────────────────────────────────────────────

/// Stochastic Oscillator — returns (%K, %D).
pub fn stochastic(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    k_period: usize,
    d_period: usize,
) -> (Vec<f64>, Vec<f64>) {
    let n = closes.len();
    let mut k_vals = Vec::with_capacity(n);
    for i in 0..n {
        let start = (i + 1).saturating_sub(k_period);
        let highest_high = highs[start..=i]
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let lowest_low = lows[start..=i]
            .iter()
            .cloned()
            .fold(f64::INFINITY, f64::min);
        let denom = highest_high - lowest_low;
        let k = if denom < 1e-9 {
            50.0
        } else {
            (closes[i] - lowest_low) / denom * 100.0
        };
        k_vals.push(k);
    }
    let d_vals = sma(&k_vals, d_period);
    (k_vals, d_vals)
}

// Note: stochastic_inc is deferred — requires a rolling window of highs/lows
// which makes it stateful beyond a simple scalar. Will be added when the
// streaming chart engine needs it (Phase 20+).

// ── Wilder Sum/Avg ───────────────────────────────────────────────────────────

/// Wilder sum — exponentially-smoothed running sum.
pub fn wilder_sum(vals: &[f64], period: usize) -> Vec<f64> {
    let n = vals.len();
    if n < period {
        return vec![0.0; n];
    }
    let mut result = vec![0.0_f64; period - 1];
    let init: f64 = vals[..period].iter().sum();
    result.push(init);
    for i in period..n {
        let prev = *result.last().unwrap();
        result.push(helper::wilder_smooth(prev, vals[i], period));
    }
    result
}

/// Wilder average — Wilder sum / period.
pub fn wilder_avg(vals: &[f64], period: usize) -> Vec<f64> {
    let n = vals.len();
    if n < period {
        return vec![0.0; n];
    }
    let mut result = vec![0.0_f64; period - 1];
    let init: f64 = vals[..period].iter().sum::<f64>() / period as f64;
    result.push(init);
    for i in period..n {
        let prev = *result.last().unwrap();
        result.push(helper::wilder_avg_step(prev, vals[i], period));
    }
    result
}

/// Incremental Wilder average update.
///
/// Delegates to `helper::wilder_avg_step`.
#[inline]
pub fn wilder_avg_inc(new_value: f64, prev_avg: f64, period: usize) -> f64 {
    helper::wilder_avg_step(prev_avg, new_value, period)
}

// ── ADX ──────────────────────────────────────────────────────────────────────

/// ADX components — returns (ADX, DI+, DI-).
pub fn adx_components(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    period: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let n = closes.len();
    if n < 2 {
        return (vec![0.0; n], vec![0.0; n], vec![0.0; n]);
    }
    let mut tr = vec![0.0_f64];
    let mut dm_plus = vec![0.0_f64];
    let mut dm_minus = vec![0.0_f64];
    for i in 1..n {
        let h = highs[i];
        let l = lows[i];
        let prev_c = closes[i - 1];
        let prev_h = highs[i - 1];
        let prev_l = lows[i - 1];
        tr.push(f64::max(
            h - l,
            f64::max((h - prev_c).abs(), (l - prev_c).abs()),
        ));
        let up_move = h - prev_h;
        let down_move = prev_l - l;
        dm_plus.push(if up_move > down_move && up_move > 0.0 { up_move } else { 0.0 });
        dm_minus.push(if down_move > up_move && down_move > 0.0 { down_move } else { 0.0 });
    }
    let s_tr = wilder_sum(&tr, period);
    let s_dmp = wilder_sum(&dm_plus, period);
    let s_dmm = wilder_sum(&dm_minus, period);
    let mut di_plus = Vec::with_capacity(n);
    let mut di_minus = Vec::with_capacity(n);
    let mut dx = Vec::with_capacity(n);
    for i in 0..n {
        let tr_v = s_tr[i];
        let dip = if tr_v > 1e-9 { 100.0 * s_dmp[i] / tr_v } else { 0.0 };
        let dim = if tr_v > 1e-9 { 100.0 * s_dmm[i] / tr_v } else { 0.0 };
        di_plus.push(dip);
        di_minus.push(dim);
        let di_sum = dip + dim;
        dx.push(if di_sum > 1e-9 { 100.0 * (dip - dim).abs() / di_sum } else { 0.0 });
    }
    let adx_vals = wilder_avg(&dx, period);
    (adx_vals, di_plus, di_minus)
}

/// ADX with state — returns (ADX, DI+, DI-, final smoothed +DM, -DM, TR, ADX)
/// for bootstrapping `adx_inc()`.
pub fn adx_with_state(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    period: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>, f64, f64, f64, f64) {
    let (adx_vals, di_plus, di_minus) = adx_components(highs, lows, closes, period);

    // Reconstruct final smoothed state from wilder_sum internals
    let n = closes.len();
    let mut tr = vec![0.0_f64];
    let mut dm_plus = vec![0.0_f64];
    let mut dm_minus = vec![0.0_f64];
    for i in 1..n {
        let h = highs[i];
        let l = lows[i];
        let prev_c = closes[i - 1];
        let prev_h = highs[i - 1];
        let prev_l = lows[i - 1];
        tr.push(f64::max(
            h - l,
            f64::max((h - prev_c).abs(), (l - prev_c).abs()),
        ));
        let up_move = h - prev_h;
        let down_move = prev_l - l;
        dm_plus.push(if up_move > down_move && up_move > 0.0 { up_move } else { 0.0 });
        dm_minus.push(if down_move > up_move && down_move > 0.0 { down_move } else { 0.0 });
    }
    let s_tr = wilder_sum(&tr, period);
    let s_dmp = wilder_sum(&dm_plus, period);
    let s_dmm = wilder_sum(&dm_minus, period);

    let last_s_tr = *s_tr.last().unwrap_or(&0.0);
    let last_s_dmp = *s_dmp.last().unwrap_or(&0.0);
    let last_s_dmm = *s_dmm.last().unwrap_or(&0.0);
    let last_adx = *adx_vals.last().unwrap_or(&0.0);

    (adx_vals, di_plus, di_minus, last_s_dmp, last_s_dmm, last_s_tr, last_adx)
}

/// Incremental ADX update.
///
/// Given current and previous OHLC bars plus smoothed DM/TR state,
/// returns `(new_adx, new_smoothed_plus_dm, new_smoothed_minus_dm, new_smoothed_tr)` in O(1).
///
/// Bootstrap state from `adx_with_state()`.
pub fn adx_inc(
    high: f64,
    low: f64,
    prev_high: f64,
    prev_low: f64,
    prev_close: f64,
    prev_adx: f64,
    prev_smoothed_plus_dm: f64,
    prev_smoothed_minus_dm: f64,
    prev_smoothed_tr: f64,
    period: usize,
) -> (f64, f64, f64, f64) {
    let p = period as f64;

    // True Range
    let tr = f64::max(
        high - low,
        f64::max((high - prev_close).abs(), (low - prev_close).abs()),
    );

    // Directional Movement
    let up_move = high - prev_high;
    let down_move = prev_low - low;
    let dm_plus = if up_move > down_move && up_move > 0.0 { up_move } else { 0.0 };
    let dm_minus = if down_move > up_move && down_move > 0.0 { down_move } else { 0.0 };

    // Wilder smoothing
    let new_s_tr = prev_smoothed_tr - prev_smoothed_tr / p + tr;
    let new_s_dmp = prev_smoothed_plus_dm - prev_smoothed_plus_dm / p + dm_plus;
    let new_s_dmm = prev_smoothed_minus_dm - prev_smoothed_minus_dm / p + dm_minus;

    // DI+, DI-
    let dip = if new_s_tr > 1e-9 { 100.0 * new_s_dmp / new_s_tr } else { 0.0 };
    let dim = if new_s_tr > 1e-9 { 100.0 * new_s_dmm / new_s_tr } else { 0.0 };

    // DX
    let di_sum = dip + dim;
    let dx = if di_sum > 1e-9 { 100.0 * (dip - dim).abs() / di_sum } else { 0.0 };

    // ADX (Wilder smoothing of DX)
    let new_adx = (prev_adx * (p - 1.0) + dx) / p;

    (new_adx, new_s_dmp, new_s_dmm, new_s_tr)
}

// ── Composite signals (project-specific) ────────────────────────────────────

/// SMA(50) slope + normalised slope + last SMA value.
pub fn composite_sma50_slope_norm_impl(closes: &[f64]) -> Result<(f64, f64, f64), &'static str> {
    if closes.len() < 2 {
        return Err("at least 2 close values required");
    }
    let sma50 = sma(closes, 50);
    let last_sma = *sma50.last().unwrap_or(&0.0);
    let slope_period = 5_usize.min(sma50.len().saturating_sub(1));
    let slope_value = if slope_period == 0 {
        0.0
    } else {
        last_sma - sma50[sma50.len() - 1 - slope_period]
    };
    let denom = last_sma.abs().max(1e-9);
    let slope_norm = slope_value / denom;
    Ok((slope_value, slope_norm, last_sma))
}

/// Heartbeat score — swing regularity measure [0..1].
pub fn calculate_heartbeat_impl(
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
    sensitivity: f64,
) -> Result<f64, &'static str> {
    if closes.len() < 3 || highs.len() != closes.len() || lows.len() != closes.len() {
        return Err("closes/highs/lows must have same length >= 3");
    }
    let mut swings: Vec<(usize, f64)> = Vec::new();
    let threshold = sensitivity.abs().max(1e-6);
    for i in 1..(closes.len() - 1) {
        let prev = closes[i - 1];
        let curr = closes[i];
        let next = closes[i + 1];
        let is_turn = (curr > prev && curr > next) || (curr < prev && curr < next);
        if is_turn {
            let amplitude = (highs[i] - lows[i]).abs();
            if amplitude >= threshold {
                swings.push((i, curr));
            }
        }
    }
    if swings.len() < 4 {
        return Ok(0.0);
    }
    let mut periods = Vec::new();
    let mut amplitudes = Vec::new();
    for window in swings.windows(2) {
        let period = (window[1].0 as i64 - window[0].0 as i64).unsigned_abs() as f64;
        let amp = (window[1].1 - window[0].1).abs();
        if period > 0.0 {
            periods.push(period);
            amplitudes.push(amp);
        }
    }
    if periods.len() < 3 {
        return Ok(0.0);
    }
    let period_mean = periods.iter().sum::<f64>() / periods.len() as f64;
    let amp_mean = amplitudes.iter().sum::<f64>() / amplitudes.len() as f64;
    if period_mean <= 0.0 || amp_mean <= 0.0 {
        return Ok(0.0);
    }
    let period_var = periods
        .iter()
        .map(|value| {
            let delta = *value - period_mean;
            delta * delta
        })
        .sum::<f64>()
        / periods.len() as f64;
    let amp_var = amplitudes
        .iter()
        .map(|value| {
            let delta = *value - amp_mean;
            delta * delta
        })
        .sum::<f64>()
        / amplitudes.len() as f64;
    let period_cv = period_var.sqrt() / period_mean;
    let amp_cv = amp_var.sqrt() / amp_mean;
    let period_stability = (1.0 - period_cv).clamp(0.0, 1.0);
    let amp_stability = (1.0 - amp_cv).clamp(0.0, 1.0);
    Ok(((period_stability + amp_stability) / 2.0).clamp(0.0, 1.0))
}

// ── Connors RSI ─────────────────────────────────────────────────────────────

/// Connors RSI — composite of 3 components (Connors & Alvarez, 2012).
///
/// CRSI = (RSI(close, rsi_period) + RSI(streak, streak_period) + PercentRank(ROC1, pct_period)) / 3
///
/// Component 1: Standard Wilder RSI on close prices.
/// Component 2: RSI applied to consecutive up/down streak count.
/// Component 3: Percentile rank of 1-bar rate of change over pct_period bars.
///
/// Output: 0–100 scale.
///
/// Python ref: `oscillators.py::connors_rsi()`.
pub fn connors_rsi(
    closes: &[f64],
    rsi_period: usize,
    streak_period: usize,
    pct_period: usize,
) -> Vec<f64> {
    let n = closes.len();
    if n < 2 {
        return vec![50.0; n];
    }

    // Component 1: RSI on close
    let rsi_close = rsi(closes, rsi_period);

    // Component 2: streak → RSI of streak
    let mut streak = vec![0.0_f64; n];
    for i in 1..n {
        if closes[i] > closes[i - 1] {
            streak[i] = if streak[i - 1] >= 0.0 {
                streak[i - 1] + 1.0
            } else {
                1.0
            };
        } else if closes[i] < closes[i - 1] {
            streak[i] = if streak[i - 1] <= 0.0 {
                streak[i - 1] - 1.0
            } else {
                -1.0
            };
        }
        // equal → streak[i] stays 0.0
    }
    let rsi_streak = rsi(&streak, streak_period);

    // Component 3: percent rank of ROC-1
    let mut roc1 = vec![0.0_f64; n];
    for i in 1..n {
        if closes[i - 1].abs() > 1e-10 {
            roc1[i] = (closes[i] - closes[i - 1]) / closes[i - 1] * 100.0;
        }
    }
    let pct = percent_rank(&roc1, pct_period);

    // Final CRSI
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        out.push((rsi_close[i] + rsi_streak[i] + pct[i]) / 3.0);
    }
    out
}

// ── RSI² (K's RSI Squared) ─────────────────────────────────────────────────

/// RSI² — RSI of RSI. Applies RSI(outer_period) to the output of RSI(inner_period).
///
/// Amplifies momentum signal by double-smoothing.
/// Kaabar Ch.11: inner=14, outer=5.
///
/// Python ref: `oscillators.py::calculate_ks_collection()` → rsi_sq.
pub fn rsi_squared(closes: &[f64], inner_period: usize, outer_period: usize) -> Vec<f64> {
    let rsi_inner = rsi(closes, inner_period);
    rsi(&rsi_inner, outer_period)
}

// ── CCI ────────────────────────────────────────────────────────────────────

/// Commodity Channel Index.
///
/// Formula:
/// ```text
/// TP = (High + Low + Close) / 3
/// CCI = (TP - SMA(TP, period)) / (0.015 * MeanDeviation(TP, period))
/// ```
///
/// Returns vec of length `highs.len()`, warmup values filled with 0.0.
pub fn cci(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if n < period || period < 2 {
        return vec![0.0; n];
    }
    // Typical Price
    let tp: Vec<f64> = (0..n)
        .map(|i| helper::typical_price(highs[i], lows[i], closes[i]))
        .collect();
    let tp_sma = sma(&tp, period);
    let mut out = vec![0.0_f64; n];
    for i in (period - 1)..n {
        let sma_val = tp_sma[i];
        let mut mean_dev = 0.0_f64;
        for j in 0..period {
            mean_dev += (tp[i - j] - sma_val).abs();
        }
        mean_dev /= period as f64;
        out[i] = if mean_dev.abs() < 1e-15 {
            0.0
        } else {
            (tp[i] - sma_val) / (0.015 * mean_dev)
        };
    }
    out
}

/// Incremental CCI update.
///
/// Given a buffer of the last `period` typical prices (after removing the oldest
/// and appending the new TP), returns the new CCI value.
///
/// `prev_tp_buffer` must contain exactly `period` typical price values
/// (the most recent window). `new_tp` is the newest typical price that
/// replaced the oldest entry before calling.
#[inline]
pub fn cci_inc(prev_tp_buffer: &[f64], new_tp: f64, period: usize) -> f64 {
    let sma_val: f64 = prev_tp_buffer.iter().sum::<f64>() / period as f64;
    let mut mean_dev = 0.0_f64;
    for &tp in prev_tp_buffer {
        mean_dev += (tp - sma_val).abs();
    }
    mean_dev /= period as f64;
    if mean_dev.abs() < 1e-15 {
        0.0
    } else {
        (new_tp - sma_val) / (0.015 * mean_dev)
    }
}

// ── Williams %R ────────────────────────────────────────────────────────────

/// Williams %R — momentum oscillator measuring overbought/oversold levels.
///
/// Formula:
/// ```text
/// %R = (HighestHigh - Close) / (HighestHigh - LowestLow) * -100
/// ```
///
/// Range: -100 (oversold) to 0 (overbought).
/// Returns vec of length `closes.len()`, warmup values filled with -50.0.
pub fn willr(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if n < period || period < 2 {
        return vec![-50.0; n];
    }
    let mut out = vec![-50.0_f64; n];
    for i in (period - 1)..n {
        let start = i + 1 - period;
        let highest = highs[start..=i]
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let lowest = lows[start..=i]
            .iter()
            .cloned()
            .fold(f64::INFINITY, f64::min);
        let denom = highest - lowest;
        out[i] = if denom < 1e-9 {
            0.0
        } else {
            (highest - closes[i]) / denom * -100.0
        };
    }
    out
}

/// Incremental Williams %R update.
///
/// Given rolling high/low buffers of the last `period` bars,
/// returns the new Williams %R value.
#[inline]
pub fn willr_inc(high_buffer: &[f64], low_buffer: &[f64], close: f64, _period: usize) -> f64 {
    let highest = high_buffer
        .iter()
        .cloned()
        .fold(f64::NEG_INFINITY, f64::max);
    let lowest = low_buffer
        .iter()
        .cloned()
        .fold(f64::INFINITY, f64::min);
    let denom = highest - lowest;
    if denom < 1e-9 {
        0.0
    } else {
        (highest - close) / denom * -100.0
    }
}

// ── Aroon ──────────────────────────────────────────────────────────────────

/// Aroon indicator — returns (aroon_up, aroon_down).
///
/// Formula:
/// ```text
/// Aroon Up   = ((period - bars_since_highest_high) / period) * 100
/// Aroon Down = ((period - bars_since_lowest_low)   / period) * 100
/// ```
///
/// Returns vecs of length `highs.len()`, warmup values filled with 0.0.
pub fn aroon(highs: &[f64], lows: &[f64], period: usize) -> (Vec<f64>, Vec<f64>) {
    let n = highs.len();
    if n <= period || period < 2 {
        return (vec![0.0; n], vec![0.0; n]);
    }
    let mut up = vec![0.0_f64; n];
    let mut down = vec![0.0_f64; n];
    let p = period as f64;
    for i in period..n {
        // Look at window [i-period..=i] which is period+1 bars
        let start = i - period;
        let mut highest_idx = start;
        let mut lowest_idx = start;
        for j in start..=i {
            if highs[j] >= highs[highest_idx] {
                highest_idx = j;
            }
            if lows[j] <= lows[lowest_idx] {
                lowest_idx = j;
            }
        }
        let bars_since_high = (i - highest_idx) as f64;
        let bars_since_low = (i - lowest_idx) as f64;
        up[i] = ((p - bars_since_high) / p) * 100.0;
        down[i] = ((p - bars_since_low) / p) * 100.0;
    }
    (up, down)
}

// ── Aroon Oscillator ───────────────────────────────────────────────────────

/// Aroon Oscillator — `Aroon Up - Aroon Down`.
///
/// Range: -100 to +100. Positive values indicate bullish trend.
pub fn aroon_osc(highs: &[f64], lows: &[f64], period: usize) -> Vec<f64> {
    let (up, down) = aroon(highs, lows, period);
    up.iter().zip(down.iter()).map(|(u, d)| u - d).collect()
}

// ── TRIX ───────────────────────────────────────────────────────────────────

/// TRIX — rate of change of triple-smoothed EMA.
///
/// Formula:
/// ```text
/// EMA1 = EMA(close, period)
/// EMA2 = EMA(EMA1, period)
/// EMA3 = EMA(EMA2, period)
/// TRIX = (EMA3[i] - EMA3[i-1]) / EMA3[i-1] * 100
/// ```
///
/// Returns vec of length `closes.len()`, warmup values filled with 0.0.
pub fn trix(closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if period < 2 {
        return vec![0.0; n];
    }
    let ema1 = ema(closes, period);
    let ema2 = ema(&ema1, period);
    let ema3 = ema(&ema2, period);
    let mut out = vec![0.0_f64; n];
    for i in 1..n {
        if ema3[i - 1].abs() > 1e-15 {
            out[i] = (ema3[i] - ema3[i - 1]) / ema3[i - 1] * 100.0;
        }
    }
    out
}

// ── Momentum ───────────────────────────────────────────────────────────────

/// Momentum — simple price difference over `period` bars.
///
/// Formula: `MOM[i] = close[i] - close[i - period]`
///
/// Returns vec of length `closes.len()`, warmup values filled with 0.0.
pub fn momentum(closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if n <= period {
        return vec![0.0; n];
    }
    let mut out = vec![0.0_f64; n];
    for i in period..n {
        out[i] = closes[i] - closes[i - period];
    }
    out
}

/// Incremental momentum update.
#[inline]
pub fn momentum_inc(prev_close_n_ago: f64, current_close: f64) -> f64 {
    current_close - prev_close_n_ago
}

// ── ROC ────────────────────────────────────────────────────────────────────

/// Rate of Change — percentage price change over `period` bars.
///
/// Formula: `ROC[i] = ((close[i] - close[i-period]) / close[i-period]) * 100`
///
/// Returns vec of length `closes.len()`, warmup values filled with 0.0.
pub fn roc(closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if n <= period {
        return vec![0.0; n];
    }
    let mut out = vec![0.0_f64; n];
    for i in period..n {
        let prev = closes[i - period];
        if prev.abs() > 1e-15 {
            out[i] = (closes[i] - prev) / prev * 100.0;
        }
    }
    out
}

// ── ROCP ───────────────────────────────────────────────────────────────────

/// Rate of Change Percentage — like ROC but without *100.
///
/// Formula: `ROCP[i] = (close[i] - close[i-period]) / close[i-period]`
///
/// Returns vec of length `closes.len()`, warmup values filled with 0.0.
pub fn rocp(closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if n <= period {
        return vec![0.0; n];
    }
    let mut out = vec![0.0_f64; n];
    for i in period..n {
        let prev = closes[i - period];
        if prev.abs() > 1e-15 {
            out[i] = (closes[i] - prev) / prev;
        }
    }
    out
}

// ── ROCR ──────────────────────────────────────────────────────────────────

/// Rate of Change Ratio — `close[i] / close[i-period]`.
///
/// Returns vec of length `closes.len()`, warmup values filled with 0.0.
pub fn rocr(closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if n <= period {
        return vec![0.0; n];
    }
    let mut out = vec![0.0_f64; n];
    for i in period..n {
        let prev = closes[i - period];
        if prev.abs() > 1e-15 {
            out[i] = closes[i] / prev;
        }
    }
    out
}

// ── ROCR100 ───────────────────────────────────────────────────────────────

/// Rate of Change Ratio × 100 — `(close[i] / close[i-period]) * 100`.
///
/// Returns vec of length `closes.len()`, warmup values filled with 0.0.
pub fn rocr100(closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if n <= period {
        return vec![0.0; n];
    }
    let mut out = vec![0.0_f64; n];
    for i in period..n {
        let prev = closes[i - period];
        if prev.abs() > 1e-15 {
            out[i] = closes[i] / prev * 100.0;
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    // ── RSI _inc tests ───────────────────────────────────────────────────

    #[test]
    fn rsi_inc_matches_batch() {
        let v: Vec<f64> = (0..50).map(|i| 100.0 + (i as f64 * 0.7).sin() * 10.0).collect();
        let (batch, final_ag, final_al) = rsi_with_state(&v, 14);

        // Simulate incremental from period onward
        // First, get avg_gain/avg_loss at index=period by re-running
        let (_, mut ag, mut al) = rsi_with_state(&v[..15], 14);
        let mut prev_price = v[14];

        for i in 15..v.len() {
            let (rsi_val, new_ag, new_al) = rsi_inc(v[i], prev_price, ag, al, 14);
            assert_abs_diff_eq!(rsi_val, batch[i], epsilon = 1e-6);
            ag = new_ag;
            al = new_al;
            prev_price = v[i];
        }

        // Final state should match
        assert_abs_diff_eq!(ag, final_ag, epsilon = 1e-9);
        assert_abs_diff_eq!(al, final_al, epsilon = 1e-9);
    }

    #[test]
    fn rsi_inc_all_gains() {
        // Monotonically rising → RSI should be 100
        let (rsi_val, ag, al) = rsi_inc(110.0, 100.0, 5.0, 0.0, 14);
        assert_abs_diff_eq!(rsi_val, 100.0, epsilon = 1e-9);
        assert!(ag > 0.0);
        assert_abs_diff_eq!(al, 0.0, epsilon = 1e-9);
    }

    // ── MACD _inc tests ──────────────────────────────────────────────────

    #[test]
    fn macd_inc_matches_batch() {
        let v: Vec<f64> = (0..80).map(|i| 100.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let (batch_macd, batch_signal, batch_hist, last_fast, last_slow, last_signal) =
            macd_with_state(&v, 12, 26, 9);

        // Batch vectors should have correct length
        assert_eq!(batch_macd.len(), 80);
        assert_eq!(batch_signal.len(), 80);
        assert_eq!(batch_hist.len(), 80);

        // Histogram = MACD - Signal at every point
        for i in 0..80 {
            assert_abs_diff_eq!(batch_hist[i], batch_macd[i] - batch_signal[i], epsilon = 1e-9);
        }

        // Now add one more price and compare inc vs extended batch
        let new_price = 103.5;
        let (m, s, h) = macd_inc(new_price, last_fast, last_slow, last_signal, 12, 26, 9);

        let mut extended = v.clone();
        extended.push(new_price);
        let (ext_macd, ext_signal, ext_hist) = macd_components(&extended, 12, 26, 9);

        assert_abs_diff_eq!(m, *ext_macd.last().unwrap(), epsilon = 1e-6);
        assert_abs_diff_eq!(s, *ext_signal.last().unwrap(), epsilon = 1e-6);
        assert_abs_diff_eq!(h, *ext_hist.last().unwrap(), epsilon = 1e-6);
    }

    // ── ADX _inc tests ───────────────────────────────────────────────────

    #[test]
    fn adx_inc_matches_batch() {
        // Generate realistic OHLC data
        let n = 60;
        let mut highs = Vec::with_capacity(n);
        let mut lows = Vec::with_capacity(n);
        let mut closes = Vec::with_capacity(n);
        for i in 0..n {
            let base = 100.0 + (i as f64 * 0.2).sin() * 10.0;
            highs.push(base + 2.0);
            lows.push(base - 2.0);
            closes.push(base + 0.5);
        }

        let (batch_adx, batch_dip, batch_dim, last_dmp, last_dmm, last_tr, last_adx) =
            adx_with_state(&highs, &lows, &closes, 14);

        // Batch should have correct length and valid ADX values after warmup
        assert_eq!(batch_adx.len(), n);
        assert_eq!(batch_dip.len(), n);
        assert_eq!(batch_dim.len(), n);
        // ADX after warmup should be non-negative
        for &v in &batch_adx[28..] {
            assert!(v >= 0.0, "ADX should be non-negative, got {v}");
        }

        // Add one more bar and verify inc produces sane values
        let new_h = 112.0;
        let new_l = 108.0;
        let new_c = 110.0;
        let (new_adx, new_dmp, new_dmm, new_tr) = adx_inc(
            new_h, new_l,
            *highs.last().unwrap(), *lows.last().unwrap(), *closes.last().unwrap(),
            last_adx, last_dmp, last_dmm, last_tr,
            14,
        );

        // Verify against full batch with extended series
        let mut ext_h = highs.clone();
        let mut ext_l = lows.clone();
        let mut ext_c = closes.clone();
        ext_h.push(new_h);
        ext_l.push(new_l);
        ext_c.push(new_c);
        let (ext_adx, _, _) = adx_components(&ext_h, &ext_l, &ext_c, 14);

        // ADX from inc should match extended batch
        assert_abs_diff_eq!(new_adx, *ext_adx.last().unwrap(), epsilon = 1e-6);
        assert!(new_dmp >= 0.0);
        assert!(new_dmm >= 0.0);
        assert!(new_tr > 0.0);
    }

    // ── Wilder avg _inc test ─────────────────────────────────────────────

    // ── Connors RSI tests ──────────────────────────────────────────────

    #[test]
    fn connors_rsi_output_length() {
        let v: Vec<f64> = (0..120).map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0).collect();
        let result = connors_rsi(&v, 3, 2, 100);
        assert_eq!(result.len(), 120);
    }

    #[test]
    fn connors_rsi_bounded_0_100() {
        let v: Vec<f64> = (0..120).map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0).collect();
        let result = connors_rsi(&v, 3, 2, 100);
        for (i, &val) in result.iter().enumerate() {
            assert!(
                val >= 0.0 && val <= 100.0,
                "bar {i}: CRSI={val} out of [0,100]"
            );
        }
    }

    #[test]
    fn connors_rsi_short_input() {
        let result = connors_rsi(&[100.0], 3, 2, 100);
        assert_eq!(result.len(), 1);
        assert_abs_diff_eq!(result[0], 50.0, epsilon = 1e-9);
    }

    // ── RSI² tests ───────────────────────────────────────────────────────

    #[test]
    fn rsi_squared_output_length() {
        let v: Vec<f64> = (0..50).map(|i| 100.0 + (i as f64 * 0.5).sin() * 5.0).collect();
        let result = rsi_squared(&v, 14, 5);
        assert_eq!(result.len(), 50);
    }

    #[test]
    fn rsi_squared_bounded() {
        let v: Vec<f64> = (0..80).map(|i| 100.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let result = rsi_squared(&v, 14, 5);
        for &val in &result {
            assert!(val >= 0.0 && val <= 100.0, "RSI² out of range: {val}");
        }
    }

    // ── Wilder avg _inc test ─────────────────────────────────────────────

    #[test]
    fn wilder_avg_inc_matches_batch() {
        let v: Vec<f64> = (0..30).map(|i| 10.0 + i as f64).collect();
        let batch = wilder_avg(&v, 14);

        // After warmup, test incremental
        let mut prev = batch[13]; // first valid value
        for i in 14..v.len() {
            let result = wilder_avg_inc(v[i], prev, 14);
            assert_abs_diff_eq!(result, batch[i], epsilon = 1e-9);
            prev = result;
        }
    }

    // ── CCI tests ─────────────────────────────────────────────────────────

    #[test]
    fn cci_output_length() {
        let h: Vec<f64> = (0..30).map(|i| 102.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let l: Vec<f64> = (0..30).map(|i| 98.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let c: Vec<f64> = (0..30).map(|i| 100.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let result = cci(&h, &l, &c, 14);
        assert_eq!(result.len(), 30);
    }

    #[test]
    fn cci_inc_matches_batch() {
        let n = 40;
        let h: Vec<f64> = (0..n).map(|i| 102.0 + (i as f64 * 0.5).sin() * 5.0).collect();
        let l: Vec<f64> = (0..n).map(|i| 98.0 + (i as f64 * 0.5).sin() * 5.0).collect();
        let c: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.5).sin() * 5.0).collect();
        let period = 14;
        let batch = cci(&h, &l, &c, period);

        // Build TP buffer and verify incremental at the last bar
        let tp: Vec<f64> = (0..n).map(|i| (h[i] + l[i] + c[i]) / 3.0).collect();
        let last = n - 1;
        let buffer = &tp[(last + 1 - period)..=last];
        let inc_val = cci_inc(buffer, tp[last], period);
        assert_abs_diff_eq!(inc_val, batch[last], epsilon = 1e-6);
    }

    // ── Williams %R tests ─────────────────────────────────────────────────

    #[test]
    fn willr_output_length() {
        let h: Vec<f64> = (0..30).map(|i| 102.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let l: Vec<f64> = (0..30).map(|i| 98.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let c: Vec<f64> = (0..30).map(|i| 100.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let result = willr(&h, &l, &c, 14);
        assert_eq!(result.len(), 30);
    }

    #[test]
    fn willr_bounded() {
        let h: Vec<f64> = (0..60).map(|i| 102.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let l: Vec<f64> = (0..60).map(|i| 96.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let c: Vec<f64> = (0..60).map(|i| 100.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let result = willr(&h, &l, &c, 14);
        for &val in &result[13..] {
            assert!(
                val >= -100.0 && val <= 0.0,
                "Williams %R out of range: {val}"
            );
        }
    }

    #[test]
    fn willr_inc_matches_batch() {
        let n = 40;
        let h: Vec<f64> = (0..n).map(|i| 102.0 + (i as f64 * 0.5).sin() * 5.0).collect();
        let l: Vec<f64> = (0..n).map(|i| 96.0 + (i as f64 * 0.5).sin() * 5.0).collect();
        let c: Vec<f64> = (0..n).map(|i| 100.0 + (i as f64 * 0.5).sin() * 5.0).collect();
        let period = 14;
        let batch = willr(&h, &l, &c, period);

        let last = n - 1;
        let start = last + 1 - period;
        let h_buf = &h[start..=last];
        let l_buf = &l[start..=last];
        let inc_val = willr_inc(h_buf, l_buf, c[last], period);
        assert_abs_diff_eq!(inc_val, batch[last], epsilon = 1e-6);
    }

    // ── Aroon tests ───────────────────────────────────────────────────────

    #[test]
    fn aroon_output_length() {
        let h: Vec<f64> = (0..30).map(|i| 102.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let l: Vec<f64> = (0..30).map(|i| 98.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let (up, down) = aroon(&h, &l, 14);
        assert_eq!(up.len(), 30);
        assert_eq!(down.len(), 30);
    }

    #[test]
    fn aroon_bounded_0_100() {
        let h: Vec<f64> = (0..60).map(|i| 102.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let l: Vec<f64> = (0..60).map(|i| 96.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let (up, down) = aroon(&h, &l, 14);
        for i in 14..60 {
            assert!(up[i] >= 0.0 && up[i] <= 100.0, "Aroon Up out of range at {i}: {}", up[i]);
            assert!(down[i] >= 0.0 && down[i] <= 100.0, "Aroon Down out of range at {i}: {}", down[i]);
        }
    }

    // ── Aroon Oscillator tests ────────────────────────────────────────────

    #[test]
    fn aroon_osc_equals_up_minus_down() {
        let h: Vec<f64> = (0..60).map(|i| 102.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let l: Vec<f64> = (0..60).map(|i| 96.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let (up, down) = aroon(&h, &l, 14);
        let osc = aroon_osc(&h, &l, 14);
        assert_eq!(osc.len(), 60);
        for i in 0..60 {
            assert_abs_diff_eq!(osc[i], up[i] - down[i], epsilon = 1e-9);
        }
    }

    #[test]
    fn aroon_osc_bounded() {
        let h: Vec<f64> = (0..60).map(|i| 102.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let l: Vec<f64> = (0..60).map(|i| 96.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let osc = aroon_osc(&h, &l, 14);
        for i in 14..60 {
            assert!(
                osc[i] >= -100.0 && osc[i] <= 100.0,
                "Aroon Osc out of range at {i}: {}",
                osc[i]
            );
        }
    }

    // ── TRIX tests ────────────────────────────────────────────────────────

    #[test]
    fn trix_output_length() {
        let v: Vec<f64> = (0..60).map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0).collect();
        let result = trix(&v, 5);
        assert_eq!(result.len(), 60);
    }

    #[test]
    fn trix_warmup_near_zero() {
        // First few values should be 0.0 or very small (warmup region)
        let v: Vec<f64> = (0..60).map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0).collect();
        let result = trix(&v, 5);
        assert_abs_diff_eq!(result[0], 0.0, epsilon = 1e-9);
    }

    // ── Momentum tests ───────────────────────────────────────────────────

    #[test]
    fn momentum_output_length() {
        let v: Vec<f64> = (0..30).map(|i| 100.0 + i as f64).collect();
        let result = momentum(&v, 10);
        assert_eq!(result.len(), 30);
    }

    #[test]
    fn momentum_linear_prices() {
        // Linear prices → constant momentum
        let v: Vec<f64> = (0..20).map(|i| 100.0 + 2.0 * i as f64).collect();
        let result = momentum(&v, 5);
        for i in 5..20 {
            assert_abs_diff_eq!(result[i], 10.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn momentum_inc_matches_batch() {
        let v: Vec<f64> = (0..30).map(|i| 100.0 + (i as f64 * 0.5).sin() * 10.0).collect();
        let period = 10;
        let batch = momentum(&v, period);
        for i in period..v.len() {
            let inc_val = momentum_inc(v[i - period], v[i]);
            assert_abs_diff_eq!(inc_val, batch[i], epsilon = 1e-9);
        }
    }

    // ── ROC tests ─────────────────────────────────────────────────────────

    #[test]
    fn roc_output_length() {
        let v: Vec<f64> = (0..30).map(|i| 100.0 + i as f64).collect();
        let result = roc(&v, 10);
        assert_eq!(result.len(), 30);
    }

    #[test]
    fn roc_known_value() {
        // 110 vs 100 → ROC = 10%
        let v = vec![100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0];
        let result = roc(&v, 10);
        assert_abs_diff_eq!(result[10], 10.0, epsilon = 1e-9);
    }

    #[test]
    fn roc_warmup_zero() {
        let v: Vec<f64> = (0..20).map(|i| 100.0 + i as f64).collect();
        let result = roc(&v, 5);
        for i in 0..5 {
            assert_abs_diff_eq!(result[i], 0.0, epsilon = 1e-9);
        }
    }

    // ── ROCP tests ────────────────────────────────────────────────────────

    #[test]
    fn rocp_output_length() {
        let v: Vec<f64> = (0..30).map(|i| 100.0 + i as f64).collect();
        let result = rocp(&v, 10);
        assert_eq!(result.len(), 30);
    }

    #[test]
    fn rocp_is_roc_divided_by_100() {
        let v: Vec<f64> = (0..30).map(|i| 100.0 + (i as f64 * 0.4).sin() * 8.0).collect();
        let roc_vals = roc(&v, 10);
        let rocp_vals = rocp(&v, 10);
        for i in 10..30 {
            assert_abs_diff_eq!(rocp_vals[i], roc_vals[i] / 100.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn rocp_known_value() {
        // 110 vs 100 → ROCP = 0.1
        let v = vec![100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0];
        let result = rocp(&v, 10);
        assert_abs_diff_eq!(result[10], 0.1, epsilon = 1e-9);
    }

    // ── ROCR tests ──────────────────────────────────────────────────────

    #[test]
    fn rocr_known_value() {
        // 110 / 100 = 1.1
        let v = vec![100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0];
        let result = rocr(&v, 10);
        assert_abs_diff_eq!(result[10], 1.1, epsilon = 1e-9);
    }

    #[test]
    fn rocr_warmup_is_zero() {
        let v: Vec<f64> = (0..20).map(|i| 100.0 + i as f64).collect();
        let result = rocr(&v, 5);
        for i in 0..5 {
            assert_eq!(result[i], 0.0);
        }
    }

    // ── ROCR100 tests ───────────────────────────────────────────────────

    #[test]
    fn rocr100_known_value() {
        // (110 / 100) * 100 = 110.0
        let v = vec![100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0];
        let result = rocr100(&v, 10);
        assert_abs_diff_eq!(result[10], 110.0, epsilon = 1e-9);
    }

    #[test]
    fn rocr100_is_rocr_times_100() {
        let v: Vec<f64> = (0..30).map(|i| 100.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let rocr_vals = rocr(&v, 10);
        let rocr100_vals = rocr100(&v, 10);
        for i in 10..30 {
            assert_abs_diff_eq!(rocr100_vals[i], rocr_vals[i] * 100.0, epsilon = 1e-9);
        }
    }
}
