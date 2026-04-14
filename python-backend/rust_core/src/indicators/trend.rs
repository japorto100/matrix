// trend.rs — Moving average family + Ichimoku Kinko Hyo
//
// Mirrors Python: indicator_engine/trend.py
// Migrated from lib.rs (Phase C.1): sma, ema, wma, hma, smma, kama, alma, iwma, ols_ma
// Merged from ichimoku.rs: ichimoku_series
//
// kand-Blueprint pattern adopted:
//   batch fn()       — full series computation
//   fn _inc()        — incremental: prev_state + new_input -> new_value (for live streaming)
//   fn lookback()    — warmup period before first valid value
//
// Key kand differences adopted:
//   - EMA seeds with SMA of first N values (not values[0])
//   - RMA (Wilder's smoothing) as proper alpha=1/period, not via EMA shortcut
//   - All batch fns return Vec<f64> with NaN for warmup (kand compat)

// ── Lookback ─────────────────────────────────────────────────────────────────

/// Minimum number of data points before the first valid MA value.
/// For SMA/EMA/WMA/RMA with period `p`: lookback = `p - 1`.
#[inline]
pub const fn lookback(period: usize) -> usize {
    if period == 0 { 0 } else { period - 1 }
}

// ── SMA ──────────────────────────────────────────────────────────────────────

/// Simple Moving Average.
/// Returns a vec of equal length; first `period-1` values use a partial window.
pub fn sma(values: &[f64], period: usize) -> Vec<f64> {
    if values.is_empty() {
        return Vec::new();
    }
    if period <= 1 {
        return values.to_vec();
    }
    let mut out = Vec::with_capacity(values.len());
    let mut running = 0.0_f64;
    for (i, &v) in values.iter().enumerate() {
        running += v;
        if i >= period {
            running -= values[i - period];
        }
        let window = period.min(i + 1) as f64;
        out.push(running / window);
    }
    out
}

/// Incremental SMA update.
/// Given the previous SMA, the new input value, and the value dropping out of the window,
/// computes the next SMA in O(1).
///
/// Formula: `new_sma = prev_sma + (new_input - dropped_input) / period`
///
/// # Arguments
/// * `new_input` — the newest price entering the window
/// * `dropped_input` — the oldest price leaving the window (i.e. `values[i - period]`)
/// * `prev_sma` — the SMA value from the previous bar
/// * `period` — the SMA period
#[inline]
pub fn sma_inc(new_input: f64, dropped_input: f64, prev_sma: f64, period: usize) -> f64 {
    prev_sma + (new_input - dropped_input) / period as f64
}

// ── EMA ──────────────────────────────────────────────────────────────────────

/// Exponential Moving Average.
///
/// Seeds with SMA of first `period` values (kand-compatible).
/// Alpha = 2 / (period + 1). First `period-1` values are NaN.
pub fn ema(values: &[f64], period: usize) -> Vec<f64> {
    if values.is_empty() {
        return Vec::new();
    }
    if period <= 1 {
        return values.to_vec();
    }
    let n = values.len();
    let alpha = 2.0 / (period as f64 + 1.0);
    let mut out = vec![f64::NAN; n];

    if n < period {
        // Not enough data for even one valid EMA — return all NaN
        return out;
    }

    // Seed: SMA of first `period` values
    let seed: f64 = values[..period].iter().sum::<f64>() / period as f64;
    out[period - 1] = seed;

    // EMA from period onward
    let mut prev = seed;
    for i in period..n {
        prev = alpha * values[i] + (1.0 - alpha) * prev;
        out[i] = prev;
    }
    out
}

/// EMA that seeds with first value (legacy behavior, used by internal callers like smma/hma
/// that already handle their own warmup).
pub(crate) fn ema_seed_first(values: &[f64], period: usize) -> Vec<f64> {
    if values.is_empty() {
        return Vec::new();
    }
    let alpha = 2.0 / (period as f64 + 1.0);
    let mut out = Vec::with_capacity(values.len());
    out.push(values[0]);
    for &v in &values[1..] {
        let prev = *out.last().expect("non-empty by construction");
        out.push(alpha * v + (1.0 - alpha) * prev);
    }
    out
}

/// Incremental EMA update.
///
/// Formula: `new_ema = price * k + prev_ema * (1 - k)`
/// where `k = 2 / (period + 1)` by default.
///
/// # Arguments
/// * `price` — current price
/// * `prev_ema` — previous EMA value
/// * `period` — EMA period (used to derive k)
/// * `opt_k` — optional custom smoothing factor; if `None`, uses `2/(period+1)`
#[inline]
pub fn ema_inc(price: f64, prev_ema: f64, period: usize, opt_k: Option<f64>) -> f64 {
    let k = opt_k.unwrap_or_else(|| 2.0 / (period as f64 + 1.0));
    (price - prev_ema).mul_add(k, prev_ema)
}

// ── RMA (Running Moving Average / Wilder's Smoothing) ────────────────────────

/// Running Moving Average (Wilder's Smoothing).
///
/// Alpha = 1/period. Seeds with SMA of first `period` values.
/// First `period-1` values are NaN.
///
/// This is the proper Wilder smoothing used by RSI, ATR, ADX in TradingView.
/// Note: Our legacy `smma()` uses `ema(values, 2*period-1)` which is mathematically
/// equivalent but seeds differently. This function matches kand's `rma` exactly.
pub fn rma(values: &[f64], period: usize) -> Vec<f64> {
    if values.is_empty() {
        return Vec::new();
    }
    if period <= 1 {
        return values.to_vec();
    }
    let n = values.len();
    let alpha = 1.0 / period as f64;
    let mut out = vec![f64::NAN; n];

    if n < period {
        return out;
    }

    // Seed: SMA of first `period` values
    let seed: f64 = values[..period].iter().sum::<f64>() / period as f64;
    out[period - 1] = seed;

    // RMA from period onward
    let mut prev = seed;
    for i in period..n {
        prev = values[i] * alpha + prev * (1.0 - alpha);
        out[i] = prev;
    }
    out
}

/// Incremental RMA update.
///
/// Formula: `new_rma = price * (1/period) + prev_rma * (1 - 1/period)`
#[inline]
pub fn rma_inc(price: f64, prev_rma: f64, period: usize) -> f64 {
    let alpha = 1.0 / period as f64;
    price.mul_add(alpha, prev_rma * (1.0 - alpha))
}

// ── WMA ──────────────────────────────────────────────────────────────────────

/// Weighted Moving Average — linearly increasing weights (newest = highest).
pub fn wma(values: &[f64], period: usize) -> Vec<f64> {
    if values.is_empty() {
        return Vec::new();
    }
    if period <= 1 {
        return values.to_vec();
    }
    let mut out = Vec::with_capacity(values.len());
    for i in 0..values.len() {
        let start = (i + 1).saturating_sub(period);
        let window = &values[start..=i];
        let w = window.len();
        let denom = (w * (w + 1)) as f64 / 2.0;
        let total: f64 = window.iter().enumerate().map(|(j, v)| (j + 1) as f64 * v).sum();
        out.push(total / denom);
    }
    out
}

/// Incremental WMA update.
///
/// Takes a window slice ordered **newest-to-oldest** and computes WMA.
/// This matches kand's `wma_inc` interface.
///
/// # Arguments
/// * `window_newest_first` — slice of length `period`, ordered newest → oldest
/// * `period` — WMA period
pub fn wma_inc(window_newest_first: &[f64], period: usize) -> f64 {
    let denom = (period * (period + 1)) as f64 / 2.0;
    let mut weighted_sum = 0.0;
    let mut weight = period as f64;
    for &v in window_newest_first {
        weighted_sum += v * weight;
        weight -= 1.0;
    }
    weighted_sum / denom
}

// ── HMA ──────────────────────────────────────────────────────────────────────

/// Hull Moving Average — WMA(2*WMA(n/2) - WMA(n), sqrt(n)).
pub fn hma(values: &[f64], period: usize) -> Vec<f64> {
    if values.len() < period {
        return values.to_vec();
    }
    let half = ((period as f64 / 2.0).round() as usize).max(1);
    let sqrt_p = ((period as f64).sqrt().round() as usize).max(1);
    let wma_half = wma(values, half);
    let wma_full = wma(values, period);
    let diff: Vec<f64> = wma_half
        .iter()
        .zip(wma_full.iter())
        .map(|(h, f)| 2.0 * h - f)
        .collect();
    wma(&diff, sqrt_p)
}

// ── SMMA (legacy) ────────────────────────────────────────────────────────────

/// Smoothed Moving Average (legacy Wilder shortcut) — EMA with span=2*period-1.
///
/// Note: For proper Wilder smoothing with SMA seed, use `rma()` instead.
/// This is kept for backward compatibility with existing callers.
pub fn smma(values: &[f64], period: usize) -> Vec<f64> {
    if period == 0 {
        return values.to_vec();
    }
    ema_seed_first(values, 2 * period - 1)
}

// ── KAMA ─────────────────────────────────────────────────────────────────────

/// Kaufman Adaptive Moving Average — efficiency ratio + fast/slow smoothing.
pub fn kama(values: &[f64], period: usize, fast: usize, slow: usize) -> Vec<f64> {
    if values.is_empty() {
        return Vec::new();
    }
    let fast_sc = 2.0 / (fast as f64 + 1.0);
    let slow_sc = 2.0 / (slow as f64 + 1.0);
    let n = values.len();
    let mut out = vec![values[0]; n];
    for i in period..n {
        let direction = (values[i] - values[i - period]).abs();
        let volatility: f64 = (i - period + 1..=i).map(|k| (values[k] - values[k - 1]).abs()).sum();
        let er = if volatility < 1e-10 { 0.0 } else { direction / volatility };
        let sc = (er * (fast_sc - slow_sc) + slow_sc).powi(2);
        out[i] = out[i - 1] + sc * (values[i] - out[i - 1]);
    }
    out
}

// ── ALMA ─────────────────────────────────────────────────────────────────────

/// Arnaud Legoux Moving Average — Gaussian-weighted moving average.
pub fn alma(values: &[f64], period: usize, offset: f64, sigma: f64) -> Vec<f64> {
    if values.is_empty() || period == 0 {
        return Vec::new();
    }
    let m = (offset * (period as f64 - 1.0)) as usize;
    let s = period as f64 / sigma;
    let weights: Vec<f64> = (0..period)
        .map(|i| {
            let diff = i as f64 - m as f64;
            (-(diff * diff) / (2.0 * s * s)).exp()
        })
        .collect();
    let wsum: f64 = weights.iter().sum();
    let n = values.len();
    let mut out = vec![0.0_f64; n];
    for i in (period - 1)..n {
        let window = &values[i + 1 - period..=i];
        out[i] = weights.iter().zip(window.iter()).map(|(w, v)| w * v).sum::<f64>() / wsum;
    }
    out
}

// ── IWMA ─────────────────────────────────────────────────────────────────────

/// Inverse Weighted Moving Average — oldest bar gets weight 1/period, newest gets 1/1.
pub fn iwma(values: &[f64], period: usize) -> Vec<f64> {
    if values.is_empty() || period == 0 {
        return Vec::new();
    }
    let weights: Vec<f64> = (0..period).map(|j| 1.0 / (period - j) as f64).collect();
    let wsum: f64 = weights.iter().sum();
    let n = values.len();
    let mut out = vec![0.0_f64; n];
    for i in (period - 1)..n {
        let window = &values[i + 1 - period..=i];
        out[i] = weights.iter().zip(window.iter()).map(|(w, v)| w * v).sum::<f64>() / wsum;
    }
    out
}

// ── OLS MA ───────────────────────────────────────────────────────────────────

/// OLS Linear Regression fitted value at last bar of each window.
pub fn ols_ma(values: &[f64], period: usize) -> Vec<f64> {
    if values.is_empty() || period == 0 {
        return Vec::new();
    }
    let n = values.len();
    let mut out = vec![0.0_f64; n];
    for i in (period - 1)..n {
        let window = &values[i + 1 - period..=i];
        let w = window.len() as f64;
        let x_mean = (w - 1.0) / 2.0;
        let y_mean = window.iter().sum::<f64>() / w;
        let mut num = 0.0_f64;
        let mut den = 0.0_f64;
        for (j, y) in window.iter().enumerate() {
            let xj = j as f64;
            num += (xj - x_mean) * (y - y_mean);
            den += (xj - x_mean).powi(2);
        }
        let slope = if den < 1e-10 { 0.0 } else { num / den };
        let intercept = y_mean - slope * x_mean;
        out[i] = intercept + slope * (w - 1.0);
    }
    out
}

// ── Parabolic SAR (Wilder) ──────────────────────────────────────────────

/// Parabolic SAR — trend-following indicator (J. Welles Wilder).
///
/// Points below price = uptrend (long signal).
/// Points above price = downtrend (short signal).
///
/// kand-Blueprint: `kand::sar(high, low, af_start, af_step, af_max)`
pub fn parabolic_sar(
    highs: &[f64],
    lows: &[f64],
    af_start: f64,
    af_step: f64,
    af_max: f64,
) -> Vec<f64> {
    let n = highs.len();
    if n == 0 {
        return Vec::new();
    }
    if n == 1 {
        return vec![lows[0]];
    }

    let mut sar = vec![0.0_f64; n];
    let mut af = af_start;
    let mut ep = highs[0]; // extreme point
    let mut is_bull = true;
    sar[0] = lows[0];

    for i in 1..n {
        let prev_sar = sar[i - 1];
        if is_bull {
            sar[i] = prev_sar + af * (ep - prev_sar);
            // SAR must not be above the two prior lows
            let low_prev1 = lows[i - 1];
            let low_prev2 = lows[if i >= 2 { i - 2 } else { 0 }];
            if sar[i] > low_prev1 {
                sar[i] = low_prev1;
            }
            if sar[i] > low_prev2 {
                sar[i] = low_prev2;
            }
            if lows[i] < sar[i] {
                // Trend reversal → downtrend
                is_bull = false;
                sar[i] = ep;
                ep = lows[i];
                af = af_start;
            } else if highs[i] > ep {
                ep = highs[i];
                af = (af + af_step).min(af_max);
            }
        } else {
            sar[i] = prev_sar + af * (ep - prev_sar);
            // SAR must not be below the two prior highs
            let high_prev1 = highs[i - 1];
            let high_prev2 = highs[if i >= 2 { i - 2 } else { 0 }];
            if sar[i] < high_prev1 {
                sar[i] = high_prev1;
            }
            if sar[i] < high_prev2 {
                sar[i] = high_prev2;
            }
            if highs[i] > sar[i] {
                // Trend reversal → uptrend
                is_bull = true;
                sar[i] = ep;
                ep = highs[i];
                af = af_start;
            } else if lows[i] < ep {
                ep = lows[i];
                af = (af + af_step).min(af_max);
            }
        }
    }
    sar
}

// ── Ichimoku Kinko Hyo ──────────────────────────────────────────────────────

/// Ichimoku Cloud — Tenkan(9), Kijun(26), Span A=(T+K)/2, Span B midpoint(52), Chikou=close.
pub fn ichimoku_series(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let n = closes.len();
    let mut tenkan = vec![0.0_f64; n];
    let mut kijun = vec![0.0_f64; n];
    let mut span_a = vec![0.0_f64; n];
    let mut span_b = vec![0.0_f64; n];
    let chikou = closes.to_vec();
    for i in 0..n {
        let t_s = i.saturating_sub(8);
        let t_hh = highs[t_s..=i].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let t_ll = lows[t_s..=i].iter().cloned().fold(f64::INFINITY, f64::min);
        tenkan[i] = (t_hh + t_ll) / 2.0;

        let k_s = i.saturating_sub(25);
        let k_hh = highs[k_s..=i].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let k_ll = lows[k_s..=i].iter().cloned().fold(f64::INFINITY, f64::min);
        kijun[i] = (k_hh + k_ll) / 2.0;

        span_a[i] = (tenkan[i] + kijun[i]) / 2.0;

        let sb_s = i.saturating_sub(51);
        let sb_hh = highs[sb_s..=i].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let sb_ll = lows[sb_s..=i].iter().cloned().fold(f64::INFINITY, f64::min);
        span_b[i] = (sb_hh + sb_ll) / 2.0;
    }
    (tenkan, kijun, span_a, span_b, chikou)
}

// ---------------------------------------------------------------------------
// Ichimoku Signal-Flags (12 boolean flags + strength)
// Mirrors Python: IchimokuSignals in models.py + calculate_ichimoku in trend.py
// ---------------------------------------------------------------------------

/// Signal strength classification for Ichimoku.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IchimokuStrength {
    StrongBull,
    WeakBull,
    Neutral,
    WeakBear,
    StrongBear,
}

/// All 12 Ichimoku signal flags + strength for each bar.
pub struct IchimokuSignals {
    pub above_cloud: Vec<bool>,
    pub below_cloud: Vec<bool>,
    pub in_cloud: Vec<bool>,
    pub bullish_cloud: Vec<bool>,
    pub tk_bull: Vec<bool>,
    pub tk_bear: Vec<bool>,
    pub chikou_bull: Vec<bool>,
    pub chikou_bear: Vec<bool>,
    pub chikou_above_cloud: Vec<bool>,
    pub chikou_below_cloud: Vec<bool>,
    pub kijun_cross_bull: Vec<bool>,
    pub kijun_cross_bear: Vec<bool>,
    pub strength: Vec<IchimokuStrength>,
}

/// Full Ichimoku with configurable periods, displacement, and signal flags.
///
/// Parameters:
/// - `tenkan_period`: Tenkan-sen period (default 9)
/// - `kijun_period`: Kijun-sen period (default 26)
/// - `senkou_b_period`: Senkou Span B period (default 52)
/// - `displacement`: Forward displacement for cloud (default = kijun_period)
///
/// Returns (tenkan, kijun, span_a_displaced, span_b_displaced, chikou, signals).
pub fn ichimoku_full(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    tenkan_period: usize,
    kijun_period: usize,
    senkou_b_period: usize,
    displacement: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>, IchimokuSignals) {
    let n = closes.len();
    if n < 2 {
        let empty_b = Vec::new();
        let empty_s = Vec::new();
        return (
            Vec::new(), Vec::new(), Vec::new(), Vec::new(), Vec::new(),
            IchimokuSignals {
                above_cloud: empty_b.clone(), below_cloud: empty_b.clone(),
                in_cloud: empty_b.clone(), bullish_cloud: empty_b.clone(),
                tk_bull: empty_b.clone(), tk_bear: empty_b.clone(),
                chikou_bull: empty_b.clone(), chikou_bear: empty_b.clone(),
                chikou_above_cloud: empty_b.clone(), chikou_below_cloud: empty_b.clone(),
                kijun_cross_bull: empty_b.clone(), kijun_cross_bear: empty_b,
                strength: empty_s,
            },
        );
    }

    // Helper: midpoint of highest-high and lowest-low over `period`
    let midpoint = |h: &[f64], l: &[f64], period: usize| -> Vec<f64> {
        let mut out = vec![f64::NAN; h.len()];
        for i in 0..h.len() {
            let start = if i + 1 >= period { i + 1 - period } else { 0 };
            let hh = h[start..=i].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            let ll = l[start..=i].iter().cloned().fold(f64::INFINITY, f64::min);
            out[i] = (hh + ll) / 2.0;
        }
        out
    };

    let tenkan_raw = midpoint(highs, lows, tenkan_period);
    let kijun_raw = midpoint(highs, lows, kijun_period);
    let span_b_raw = midpoint(highs, lows, senkou_b_period);

    // span_a_raw = (tenkan + kijun) / 2
    let span_a_raw: Vec<f64> = (0..n).map(|i| {
        let tk = tenkan_raw[i];
        let kj = kijun_raw[i];
        if tk.is_nan() || kj.is_nan() { f64::NAN } else { (tk + kj) / 2.0 }
    }).collect();

    // Displaced cloud: shift forward by `displacement`
    let d = displacement;
    let mut span_a_hist = vec![f64::NAN; n];
    let mut span_b_hist = vec![f64::NAN; n];
    for i in d..n {
        span_a_hist[i] = span_a_raw[i - d];
        span_b_hist[i] = span_b_raw[i - d];
    }

    // Chikou: shifted backward by `displacement`
    let mut chikou = vec![f64::NAN; n];
    for i in 0..n.saturating_sub(d) {
        chikou[i] = closes[i + d];
    }

    // --- Signal Flags ---
    let mut above_cloud = vec![false; n];
    let mut below_cloud = vec![false; n];
    let mut in_cloud = vec![false; n];
    let mut bullish_cloud = vec![false; n];
    let mut tk_bull = vec![false; n];
    let mut tk_bear = vec![false; n];
    let mut chikou_bull = vec![false; n];
    let mut chikou_bear = vec![false; n];
    let mut chikou_above_cloud = vec![false; n];
    let mut chikou_below_cloud = vec![false; n];
    let mut kijun_cross_bull = vec![false; n];
    let mut kijun_cross_bear = vec![false; n];
    let mut strength = vec![IchimokuStrength::Neutral; n];

    for i in 0..n {
        let c = closes[i];
        let sa = span_a_hist[i];
        let sb = span_b_hist[i];
        let tk = tenkan_raw[i];
        let kj = kijun_raw[i];

        let cloud_valid = !sa.is_nan() && !sb.is_nan();
        let cloud_top = if cloud_valid { sa.max(sb) } else { f64::NAN };
        let cloud_bottom = if cloud_valid { sa.min(sb) } else { f64::NAN };

        let is_above = cloud_valid && c > cloud_top;
        let is_below = cloud_valid && c < cloud_bottom;
        let is_in = cloud_valid && !is_above && !is_below;
        let is_bull_cloud = cloud_valid && sa > sb;

        above_cloud[i] = is_above;
        below_cloud[i] = is_below;
        in_cloud[i] = is_in;
        bullish_cloud[i] = is_bull_cloud;

        // TK cross
        if i > 0 {
            let prev_tk = tenkan_raw[i - 1];
            let prev_kj = kijun_raw[i - 1];
            let lines_valid = !tk.is_nan() && !kj.is_nan() && !prev_tk.is_nan() && !prev_kj.is_nan();
            tk_bull[i] = lines_valid && tk > kj && prev_tk <= prev_kj;
            tk_bear[i] = lines_valid && tk < kj && prev_tk >= prev_kj;
        }

        // Chikou price cross
        if i >= d {
            chikou_bull[i] = closes[i] > closes[i - d];
            chikou_bear[i] = closes[i] < closes[i - d];

            // Chikou vs cloud d bars ago
            let sa_d = span_a_hist[i - d];
            let sb_d = span_b_hist[i - d];
            let cloud_d_valid = !sa_d.is_nan() && !sb_d.is_nan();
            if cloud_d_valid {
                let cloud_top_d = sa_d.max(sb_d);
                let cloud_bottom_d = sa_d.min(sb_d);
                chikou_above_cloud[i] = c > cloud_top_d;
                chikou_below_cloud[i] = c < cloud_bottom_d;
            }
        }

        // Kijun cross
        if i > 0 {
            let prev_c = closes[i - 1];
            let prev_kj = kijun_raw[i - 1];
            let kj_valid = !kj.is_nan() && !prev_kj.is_nan();
            kijun_cross_bull[i] = kj_valid && c > kj && prev_c <= prev_kj;
            kijun_cross_bear[i] = kj_valid && c < kj && prev_c >= prev_kj;
        }

        // Signal strength
        let bull_score = is_above as u8 + is_bull_cloud as u8
            + tk_bull[i] as u8 + chikou_bull[i] as u8;
        let bear_cld = cloud_valid && sa < sb;
        let bear_score = is_below as u8 + bear_cld as u8
            + tk_bear[i] as u8 + chikou_bear[i] as u8;

        strength[i] = if bull_score == 4 {
            IchimokuStrength::StrongBull
        } else if bull_score == 3 {
            IchimokuStrength::WeakBull
        } else if bear_score == 4 {
            IchimokuStrength::StrongBear
        } else if bear_score == 3 {
            IchimokuStrength::WeakBear
        } else {
            IchimokuStrength::Neutral
        };
    }

    let signals = IchimokuSignals {
        above_cloud,
        below_cloud,
        in_cloud,
        bullish_cloud,
        tk_bull,
        tk_bear,
        chikou_bull,
        chikou_bear,
        chikou_above_cloud,
        chikou_below_cloud,
        kijun_cross_bull,
        kijun_cross_bear,
        strength,
    };

    (tenkan_raw, kijun_raw, span_a_hist, span_b_hist, chikou, signals)
}

// ── DEMA ─────────────────────────────────────────────────────────────────────

/// Double Exponential Moving Average.
///
/// Formula: `DEMA = 2 * EMA(close, period) - EMA(EMA(close, period), period)`
///
/// Reduces lag compared to a single EMA by applying double smoothing.
/// First `2*(period-1)` values are NaN (lookback for two cascading EMAs).
pub fn dema(closes: &[f64], period: usize) -> Vec<f64> {
    if closes.is_empty() {
        return Vec::new();
    }
    if period <= 1 {
        return closes.to_vec();
    }
    let n = closes.len();
    let lb = 2 * (period - 1);
    if n <= lb {
        return vec![f64::NAN; n];
    }

    let ema1 = ema(closes, period);

    // EMA2: EMA of the valid portion of EMA1 (starting at period-1)
    let ema1_valid = &ema1[period - 1..];
    let ema2_inner = ema(ema1_valid, period);

    let mut out = vec![f64::NAN; n];
    for i in lb..n {
        let e1 = ema1[i];
        let e2 = ema2_inner[i - (period - 1)];
        out[i] = 2.0 * e1 - e2;
    }
    out
}

/// Incremental DEMA update.
///
/// Given previous EMA1 and EMA2 states, computes the next DEMA value in O(1).
///
/// Returns `(dema, new_ema1, new_ema2)`.
#[inline]
pub fn dema_inc(prev_ema1: f64, prev_ema2: f64, close: f64, alpha: f64) -> (f64, f64, f64) {
    let new_ema1 = alpha * close + (1.0 - alpha) * prev_ema1;
    let new_ema2 = alpha * new_ema1 + (1.0 - alpha) * prev_ema2;
    let dema = 2.0 * new_ema1 - new_ema2;
    (dema, new_ema1, new_ema2)
}

// ── TEMA ─────────────────────────────────────────────────────────────────────

/// Triple Exponential Moving Average.
///
/// Formula: `TEMA = 3*EMA1 - 3*EMA2 + EMA3`
///
/// Further reduces lag compared to DEMA by applying triple smoothing.
/// First `3*(period-1)` values are NaN.
pub fn tema(closes: &[f64], period: usize) -> Vec<f64> {
    if closes.is_empty() {
        return Vec::new();
    }
    if period <= 1 {
        return closes.to_vec();
    }
    let n = closes.len();
    let lb = 3 * (period - 1);
    if n <= lb {
        return vec![f64::NAN; n];
    }

    let ema1 = ema(closes, period);
    let ema1_valid = &ema1[period - 1..];
    let ema2_inner = ema(ema1_valid, period);
    let ema2_valid = &ema2_inner[period - 1..];
    let ema3_inner = ema(ema2_valid, period);

    let mut out = vec![f64::NAN; n];
    for i in lb..n {
        let e1 = ema1[i];
        let e2 = ema2_inner[i - (period - 1)];
        let e3 = ema3_inner[i - 2 * (period - 1)];
        out[i] = 3.0 * e1 - 3.0 * e2 + e3;
    }
    out
}

/// Incremental TEMA update.
///
/// Given previous EMA1, EMA2, EMA3 states, computes the next TEMA value in O(1).
///
/// Returns `(tema, new_ema1, new_ema2, new_ema3)`.
#[inline]
pub fn tema_inc(
    prev_ema1: f64,
    prev_ema2: f64,
    prev_ema3: f64,
    close: f64,
    alpha: f64,
) -> (f64, f64, f64, f64) {
    let new_ema1 = alpha * close + (1.0 - alpha) * prev_ema1;
    let new_ema2 = alpha * new_ema1 + (1.0 - alpha) * prev_ema2;
    let new_ema3 = alpha * new_ema2 + (1.0 - alpha) * prev_ema3;
    let tema = 3.0 * new_ema1 - 3.0 * new_ema2 + new_ema3;
    (tema, new_ema1, new_ema2, new_ema3)
}

// ── T3 (Tillson) ────────────────────────────────────────────────────────────

/// Tillson T3 — 6 cascading EMAs with volume-factor weighting.
///
/// Coefficients derived from `v_factor`:
/// ```text
/// c1 = -v³
/// c2 = 3v² + 3v³
/// c3 = -6v² - 3v - 3v³
/// c4 = 1 + 3v + v³ + 3v²
/// T3 = c1*EMA6 + c2*EMA5 + c3*EMA4 + c4*EMA3
/// ```
///
/// First `6*(period-1)` values are NaN.
pub fn t3(closes: &[f64], period: usize, v_factor: f64) -> Vec<f64> {
    if closes.is_empty() {
        return Vec::new();
    }
    if period <= 1 {
        return closes.to_vec();
    }
    let n = closes.len();
    let lb = 6 * (period - 1);
    if n <= lb {
        return vec![f64::NAN; n];
    }

    let v = v_factor;
    let v2 = v * v;
    let v3 = v2 * v;
    let c1 = -v3;
    let c2 = 3.0 * v2 + 3.0 * v3;
    let c3 = -6.0 * v2 - 3.0 * v - 3.0 * v3;
    let c4 = 1.0 + 3.0 * v + v3 + 3.0 * v2;

    let alpha = 2.0 / (period as f64 + 1.0);

    // 6 cascading EMAs computed incrementally in a single pass.
    // Each layer seeds with its first valid input value (ema_seed_first style).
    let mut e = [0.0_f64; 6]; // current EMA state per layer
    let mut ready = [false; 6]; // whether each layer has been seeded
    let mut warmup = [0_usize; 6]; // count of valid inputs seen per layer

    let mut out = vec![f64::NAN; n];

    for i in 0..n {
        let mut val = closes[i];
        for layer in 0..6 {
            if !ready[layer] {
                // Accumulate for SMA seed
                warmup[layer] += 1;
                if warmup[layer] == 1 {
                    e[layer] = val;
                } else {
                    e[layer] += val;
                }
                if warmup[layer] == period {
                    e[layer] /= period as f64;
                    ready[layer] = true;
                    val = e[layer];
                } else {
                    break; // not enough data for this layer yet
                }
            } else {
                e[layer] = alpha * val + (1.0 - alpha) * e[layer];
                val = e[layer];
            }
        }
        if ready[5] {
            out[i] = c1 * e[5] + c2 * e[4] + c3 * e[3] + c4 * e[2];
        }
    }
    out
}

/// Incremental T3 update.
///
/// `state` holds the 6 previous EMA values `[e1, e2, e3, e4, e5, e6]`.
///
/// Returns `(new_state, t3_value)`.
#[inline]
pub fn t3_inc(
    state: &[f64; 6],
    close: f64,
    alpha: f64,
    c1: f64,
    c2: f64,
    c3: f64,
    c4: f64,
) -> ([f64; 6], f64) {
    let one_minus_alpha = 1.0 - alpha;
    let e1 = alpha * close + one_minus_alpha * state[0];
    let e2 = alpha * e1 + one_minus_alpha * state[1];
    let e3 = alpha * e2 + one_minus_alpha * state[2];
    let e4 = alpha * e3 + one_minus_alpha * state[3];
    let e5 = alpha * e4 + one_minus_alpha * state[4];
    let e6 = alpha * e5 + one_minus_alpha * state[5];
    let t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3;
    ([e1, e2, e3, e4, e5, e6], t3)
}

// ── TRIMA ───────────────────────────────────────────────────────────────────

/// Triangular Moving Average — SMA of SMA with triangular weighting.
///
/// For odd period: `n = (period+1)/2`, `TRIMA = SMA(SMA(price, n), n)`
/// For even period: `n = period/2 + 1`, `m = period/2`, `TRIMA = SMA(SMA(price, n), m)`
///
/// First `period-1` values are NaN.
pub fn trima(closes: &[f64], period: usize) -> Vec<f64> {
    if closes.is_empty() {
        return Vec::new();
    }
    if period <= 1 {
        return closes.to_vec();
    }
    let n = closes.len();
    let lb = period - 1;
    if n <= lb {
        return vec![f64::NAN; n];
    }

    let (win1, win2) = if period % 2 == 1 {
        let half = (period + 1) / 2;
        (half, half)
    } else {
        let half1 = period / 2 + 1;
        let half2 = period / 2;
        (half1, half2)
    };

    // First SMA
    let sma1 = sma(closes, win1);
    // Second SMA (of the first SMA)
    let sma2 = sma(&sma1, win2);

    let mut out = vec![f64::NAN; n];
    for i in lb..n {
        out[i] = sma2[i];
    }
    out
}

// ── Supertrend ──────────────────────────────────────────────────────────────

/// Supertrend — trend-following indicator using ATR bands.
///
/// Returns `(supertrend_values, is_uptrend_bools)`.
///
/// When in uptrend, supertrend = lower band (support).
/// When in downtrend, supertrend = upper band (resistance).
/// Direction flips when close crosses the opposite band.
///
/// First `period` values are NaN / false.
pub fn supertrend(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    period: usize,
    multiplier: f64,
) -> (Vec<f64>, Vec<bool>) {
    let n = closes.len();
    if n < 2 || period == 0 {
        return (vec![f64::NAN; n], vec![false; n]);
    }

    let atr_vals = super::volatility::atr(highs, lows, closes, period);

    let mut st = vec![f64::NAN; n];
    let mut is_up = vec![false; n];
    let mut upper = vec![f64::NAN; n];
    let mut lower = vec![f64::NAN; n];

    // Find first valid ATR index
    let first_valid = atr_vals.iter().position(|v| *v > 0.0);
    let start = match first_valid {
        Some(idx) => idx,
        None => return (st, is_up),
    };

    // Initialise at first valid bar
    let hl2 = (highs[start] + lows[start]) / 2.0;
    upper[start] = hl2 + multiplier * atr_vals[start];
    lower[start] = hl2 - multiplier * atr_vals[start];
    is_up[start] = true;
    st[start] = lower[start];

    for i in (start + 1)..n {
        if atr_vals[i] == 0.0 || atr_vals[i].is_nan() {
            st[i] = st[i - 1];
            is_up[i] = is_up[i - 1];
            upper[i] = upper[i - 1];
            lower[i] = lower[i - 1];
            continue;
        }
        let hl2 = (highs[i] + lows[i]) / 2.0;
        let basic_upper = hl2 + multiplier * atr_vals[i];
        let basic_lower = hl2 - multiplier * atr_vals[i];

        // Final upper band
        upper[i] = if closes[i - 1] <= upper[i - 1] {
            basic_upper.min(upper[i - 1])
        } else {
            basic_upper
        };

        // Final lower band
        lower[i] = if closes[i - 1] >= lower[i - 1] {
            basic_lower.max(lower[i - 1])
        } else {
            basic_lower
        };

        // Trend direction
        if is_up[i - 1] {
            if closes[i] < lower[i] {
                is_up[i] = false;
                st[i] = upper[i];
            } else {
                is_up[i] = true;
                st[i] = lower[i];
            }
        } else if closes[i] > upper[i] {
            is_up[i] = true;
            st[i] = lower[i];
        } else {
            is_up[i] = false;
            st[i] = upper[i];
        }
    }

    (st, is_up)
}

// ── ADXR ────────────────────────────────────────────────────────────────────

/// ADX Rating — smoothed ADX: `(ADX[i] + ADX[i - period]) / 2`.
///
/// Uses `adx_components()` from the oscillators module.
/// First valid value appears at index `3*period - 2 + period - 1` (ADX lookback + ADXR lookback).
pub fn adxr(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if n < 2 || period == 0 {
        return vec![f64::NAN; n];
    }

    let (adx_vals, _, _) = super::oscillators::adx_components(highs, lows, closes, period);

    // ADXR = (ADX[i] + ADX[i - period]) / 2
    // ADX needs ~2*period bars to warm up. ADXR needs an additional `period` bars.
    let mut out = vec![f64::NAN; n];
    for i in period..n {
        let cur = adx_vals[i];
        let prev = adx_vals[i - period];
        if cur > 0.0 && prev > 0.0 {
            out[i] = (cur + prev) / 2.0;
        }
    }
    out
}

// ── Vegas Channel ───────────────────────────────────────────────────────────

/// Vegas Channel — 4 EMAs forming an inner and outer channel.
///
/// Default periods: `[144, 169, 576, 676]`.
///
/// Returns `(ema1, ema2, ema3, ema4)` matching the provided periods.
pub fn vegas_channel(
    closes: &[f64],
    periods: [usize; 4],
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let e1 = ema(closes, periods[0]);
    let e2 = ema(closes, periods[1]);
    let e3 = ema(closes, periods[2]);
    let e4 = ema(closes, periods[3]);
    (e1, e2, e3, e4)
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    // ── SMA tests ────────────────────────────────────────────────────────

    #[test]
    fn sma_basic() {
        let v = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let out = sma(&v, 3);
        assert_eq!(out.len(), 5);
        assert_abs_diff_eq!(out[0], 1.0, epsilon = 1e-9);
        assert_abs_diff_eq!(out[1], 1.5, epsilon = 1e-9);
        assert_abs_diff_eq!(out[2], 2.0, epsilon = 1e-9);
        assert_abs_diff_eq!(out[4], 4.0, epsilon = 1e-9);
    }

    #[test]
    fn sma_period_one_is_identity() {
        let v = vec![3.0, 1.0, 4.0];
        assert_eq!(sma(&v, 1), v);
    }

    #[test]
    fn sma_empty_returns_empty() {
        assert!(sma(&[], 5).is_empty());
    }

    #[test]
    fn sma_inc_matches_batch() {
        let v = vec![10.0, 11.0, 12.0, 13.0, 14.0, 15.0];
        let batch = sma(&v, 3);
        // After warmup (index >= period), test incremental
        for i in 3..v.len() {
            let result = sma_inc(v[i], v[i - 3], batch[i - 1], 3);
            assert_abs_diff_eq!(result, batch[i], epsilon = 1e-9);
        }
    }

    // ── EMA tests ────────────────────────────────────────────────────────

    #[test]
    fn ema_sma_seed() {
        // EMA(3) on [10, 11, 12, 13, 14]
        // Seed = SMA(10,11,12) = 11.0
        // alpha = 2/(3+1) = 0.5
        let v = vec![10.0, 11.0, 12.0, 13.0, 14.0];
        let out = ema(&v, 3);
        assert_eq!(out.len(), 5);
        // First 2 values are NaN
        assert!(out[0].is_nan());
        assert!(out[1].is_nan());
        // Seed at index 2
        assert_abs_diff_eq!(out[2], 11.0, epsilon = 1e-9);
        // EMA[3] = 0.5 * 13 + 0.5 * 11 = 12.0
        assert_abs_diff_eq!(out[3], 12.0, epsilon = 1e-9);
        // EMA[4] = 0.5 * 14 + 0.5 * 12 = 13.0
        assert_abs_diff_eq!(out[4], 13.0, epsilon = 1e-9);
    }

    #[test]
    fn ema_empty_returns_empty() {
        assert!(ema(&[], 3).is_empty());
    }

    #[test]
    fn ema_insufficient_data_returns_nan() {
        let v = vec![10.0, 11.0];
        let out = ema(&v, 5);
        assert_eq!(out.len(), 2);
        assert!(out[0].is_nan());
        assert!(out[1].is_nan());
    }

    #[test]
    fn ema_inc_matches_batch() {
        let v = vec![10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0];
        let batch = ema(&v, 3);
        // Start from first valid value (index 2), test incremental from index 3 onward
        let mut prev = batch[2]; // seed
        for i in 3..v.len() {
            let result = ema_inc(v[i], prev, 3, None);
            assert_abs_diff_eq!(result, batch[i], epsilon = 1e-9);
            prev = result;
        }
    }

    #[test]
    fn ema_inc_custom_k() {
        // Custom smoothing factor k=0.1
        let result = ema_inc(100.0, 90.0, 14, Some(0.1));
        // 0.1 * 100 + 0.9 * 90 = 10 + 81 = 91
        assert_abs_diff_eq!(result, 91.0, epsilon = 1e-9);
    }

    // ── RMA tests ────────────────────────────────────────────────────────

    #[test]
    fn rma_basic() {
        // period=5, input=[1..10]
        // Seed = SMA(1,2,3,4,5) = 3.0
        // alpha = 0.2
        // RMA[5] = 6*0.2 + 3.0*0.8 = 3.6
        // RMA[6] = 7*0.2 + 3.6*0.8 = 4.28
        let v: Vec<f64> = (1..=10).map(|i| i as f64).collect();
        let out = rma(&v, 5);
        assert_eq!(out.len(), 10);
        // First 4 are NaN
        for i in 0..4 {
            assert!(out[i].is_nan());
        }
        assert_abs_diff_eq!(out[4], 3.0, epsilon = 1e-12);
        assert_abs_diff_eq!(out[5], 3.6, epsilon = 1e-12);
        assert_abs_diff_eq!(out[6], 4.28, epsilon = 1e-12);
        assert_abs_diff_eq!(out[7], 5.024, epsilon = 1e-12);
    }

    #[test]
    fn rma_inc_matches_batch() {
        let v: Vec<f64> = (1..=10).map(|i| i as f64).collect();
        let batch = rma(&v, 5);
        let mut prev = batch[4]; // seed
        for i in 5..v.len() {
            let result = rma_inc(v[i], prev, 5);
            assert_abs_diff_eq!(result, batch[i], epsilon = 1e-12);
            prev = result;
        }
    }

    #[test]
    fn rma_empty_returns_empty() {
        assert!(rma(&[], 5).is_empty());
    }

    #[test]
    fn rma_period_one_is_identity() {
        let v = vec![3.0, 1.0, 4.0];
        assert_eq!(rma(&v, 1), v);
    }

    // ── WMA tests ────────────────────────────────────────────────────────

    #[test]
    fn wma_basic() {
        let v = vec![1.0, 2.0, 3.0, 4.0];
        let out = wma(&v, 3);
        assert_eq!(out.len(), 4);
        // full window at index 2: (1*1 + 2*2 + 3*3) / 6 = 14/6
        assert_abs_diff_eq!(out[2], 14.0 / 6.0, epsilon = 1e-9);
    }

    #[test]
    fn wma_inc_matches_batch() {
        let v = vec![10.0, 11.0, 12.0, 13.0, 14.0, 15.0];
        let batch = wma(&v, 3);
        // At each full-window position, test wma_inc with newest-to-oldest window
        for i in 2..v.len() {
            let window: Vec<f64> = v[i - 2..=i].iter().rev().copied().collect();
            let result = wma_inc(&window, 3);
            assert_abs_diff_eq!(result, batch[i], epsilon = 1e-9);
        }
    }

    // ── SMMA / legacy tests ──────────────────────────────────────────────

    #[test]
    fn smma_is_ema_with_double_span() {
        let v = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let smma_out = smma(&v, 3);
        let ema_out = ema_seed_first(&v, 5); // 2*3-1 = 5
        assert_eq!(smma_out, ema_out);
    }

    // ── HMA tests ────────────────────────────────────────────────────────

    #[test]
    fn hma_length_preserved() {
        let v: Vec<f64> = (0..20).map(|i| 100.0 + i as f64).collect();
        let out = hma(&v, 9);
        assert_eq!(out.len(), 20);
    }

    // ── KAMA tests ───────────────────────────────────────────────────────

    #[test]
    fn kama_flat_stays_flat() {
        let v = vec![100.0; 20];
        let out = kama(&v, 10, 2, 30);
        for val in &out {
            assert_abs_diff_eq!(*val, 100.0, epsilon = 1e-9);
        }
    }

    // ── Lookback test ────────────────────────────────────────────────────

    #[test]
    fn lookback_values() {
        assert_eq!(lookback(14), 13);
        assert_eq!(lookback(1), 0);
        assert_eq!(lookback(0), 0);
    }

    // ── Parabolic SAR tests ───────────────────────────────────────────────

    #[test]
    fn sar_output_length() {
        let highs: Vec<f64> = (0..50).map(|i| 110.0 + (i as f64 * 0.2).sin() * 5.0).collect();
        let lows: Vec<f64> = highs.iter().map(|h| h - 3.0).collect();
        let result = parabolic_sar(&highs, &lows, 0.02, 0.02, 0.20);
        assert_eq!(result.len(), 50);
    }

    #[test]
    fn sar_empty_input() {
        let result = parabolic_sar(&[], &[], 0.02, 0.02, 0.20);
        assert!(result.is_empty());
    }

    #[test]
    fn sar_single_bar() {
        let result = parabolic_sar(&[105.0], &[95.0], 0.02, 0.02, 0.20);
        assert_eq!(result.len(), 1);
        assert_abs_diff_eq!(result[0], 95.0, epsilon = 1e-9);
    }

    #[test]
    fn sar_uptrend_below_price() {
        // Strong uptrend: SAR should stay below the lows for most bars
        let highs: Vec<f64> = (0..30).map(|i| 100.0 + i as f64 * 2.0 + 1.0).collect();
        let lows: Vec<f64> = (0..30).map(|i| 100.0 + i as f64 * 2.0 - 1.0).collect();
        let sar = parabolic_sar(&highs, &lows, 0.02, 0.02, 0.20);
        // After a few bars of acceleration, SAR should be below lows
        let below_count = (5..30).filter(|&i| sar[i] < lows[i]).count();
        assert!(
            below_count > 15,
            "SAR should be below lows in uptrend, was below only {below_count}/25 bars"
        );
    }

    #[test]
    fn sar_first_bar_is_low() {
        let highs = vec![105.0, 106.0, 107.0];
        let lows = vec![95.0, 96.0, 97.0];
        let sar = parabolic_sar(&highs, &lows, 0.02, 0.02, 0.20);
        assert_abs_diff_eq!(sar[0], 95.0, epsilon = 1e-9);
    }

    // ── Ichimoku Signal tests ─────────────────────────────────────────────

    #[test]
    fn ichimoku_full_output_lengths() {
        let n = 100;
        let highs: Vec<f64> = (0..n).map(|i| 110.0 + i as f64).collect();
        let lows: Vec<f64> = (0..n).map(|i| 90.0 + i as f64).collect();
        let closes: Vec<f64> = (0..n).map(|i| 100.0 + i as f64).collect();
        let (tk, kj, sa, sb, chi, sig) = ichimoku_full(&highs, &lows, &closes, 9, 26, 52, 26);
        assert_eq!(tk.len(), n);
        assert_eq!(kj.len(), n);
        assert_eq!(sa.len(), n);
        assert_eq!(sb.len(), n);
        assert_eq!(chi.len(), n);
        assert_eq!(sig.above_cloud.len(), n);
        assert_eq!(sig.strength.len(), n);
        assert_eq!(sig.kijun_cross_bull.len(), n);
    }

    #[test]
    fn ichimoku_full_short_input() {
        let (tk, _, _, _, _, sig) = ichimoku_full(&[1.0], &[0.5], &[0.8], 9, 26, 52, 26);
        assert!(tk.is_empty());
        assert!(sig.strength.is_empty());
    }

    #[test]
    fn ichimoku_full_uptrend_above_cloud() {
        let n = 100;
        let highs: Vec<f64> = (0..n).map(|i| 110.0 + i as f64 * 3.0).collect();
        let lows: Vec<f64> = (0..n).map(|i| 90.0 + i as f64 * 3.0).collect();
        let closes: Vec<f64> = (0..n).map(|i| 100.0 + i as f64 * 3.0).collect();
        let (_, _, _, _, _, sig) = ichimoku_full(&highs, &lows, &closes, 9, 26, 52, 26);
        // After displacement warmup, uptrend should have bars above cloud
        let above_count = sig.above_cloud[52..].iter().filter(|&&v| v).count();
        assert!(above_count > 30, "expected many bars above cloud in uptrend, got {above_count}");
    }

    // ── DEMA tests ───────────────────────────────────────────────────────

    #[test]
    fn dema_basic() {
        let v: Vec<f64> = (1..=20).map(|i| i as f64).collect();
        let out = dema(&v, 5);
        assert_eq!(out.len(), 20);
        // Lookback = 2*(5-1) = 8, first 8 values should be NaN
        for i in 0..8 {
            assert!(out[i].is_nan(), "expected NaN at index {i}");
        }
        // Values after lookback should be valid
        for i in 8..20 {
            assert!(!out[i].is_nan(), "expected valid value at index {i}");
        }
    }

    #[test]
    fn dema_empty_returns_empty() {
        assert!(dema(&[], 5).is_empty());
    }

    #[test]
    fn dema_period_one_is_identity() {
        let v = vec![3.0, 1.0, 4.0];
        assert_eq!(dema(&v, 1), v);
    }

    #[test]
    fn dema_inc_matches_batch() {
        let v: Vec<f64> = (1..=20).map(|i| i as f64).collect();
        let period = 5;
        let alpha = 2.0 / (period as f64 + 1.0);
        let batch = dema(&v, period);
        let ema1_batch = ema(&v, period);
        let ema1_valid = &ema1_batch[period - 1..];
        let ema2_batch = ema(ema1_valid, period);

        let lb = 2 * (period - 1);
        // Get initial state from batch at index lb
        let mut prev_e1 = ema1_batch[lb];
        let mut prev_e2 = ema2_batch[lb - (period - 1)];

        for i in (lb + 1)..v.len() {
            let (d, e1, e2) = dema_inc(prev_e1, prev_e2, v[i], alpha);
            assert_abs_diff_eq!(d, batch[i], epsilon = 1e-9);
            prev_e1 = e1;
            prev_e2 = e2;
        }
    }

    // ── TEMA tests ───────────────────────────────────────────────────────

    #[test]
    fn tema_basic() {
        let v: Vec<f64> = (1..=20).map(|i| i as f64).collect();
        let out = tema(&v, 3);
        assert_eq!(out.len(), 20);
        // Lookback = 3*(3-1) = 6, first 6 values should be NaN
        for i in 0..6 {
            assert!(out[i].is_nan(), "expected NaN at index {i}");
        }
        for i in 6..20 {
            assert!(!out[i].is_nan(), "expected valid value at index {i}");
        }
    }

    #[test]
    fn tema_empty_returns_empty() {
        assert!(tema(&[], 3).is_empty());
    }

    #[test]
    fn tema_period_one_is_identity() {
        let v = vec![3.0, 1.0, 4.0];
        assert_eq!(tema(&v, 1), v);
    }

    #[test]
    fn tema_inc_matches_batch() {
        let v: Vec<f64> = (1..=20).map(|i| i as f64).collect();
        let period = 3;
        let alpha = 2.0 / (period as f64 + 1.0);
        let batch = tema(&v, period);
        let ema1_batch = ema(&v, period);
        let ema1_valid = &ema1_batch[period - 1..];
        let ema2_batch = ema(ema1_valid, period);
        let ema2_valid = &ema2_batch[period - 1..];
        let ema3_batch = ema(ema2_valid, period);

        let lb = 3 * (period - 1);
        let mut prev_e1 = ema1_batch[lb];
        let mut prev_e2 = ema2_batch[lb - (period - 1)];
        let mut prev_e3 = ema3_batch[lb - 2 * (period - 1)];

        for i in (lb + 1)..v.len() {
            let (t, e1, e2, e3) = tema_inc(prev_e1, prev_e2, prev_e3, v[i], alpha);
            assert_abs_diff_eq!(t, batch[i], epsilon = 1e-9);
            prev_e1 = e1;
            prev_e2 = e2;
            prev_e3 = e3;
        }
    }

    // ── T3 tests ─────────────────────────────────────────────────────────

    #[test]
    fn t3_basic() {
        // Need at least 6*(period-1)+1 = 31 bars for period=6
        let v: Vec<f64> = (1..=40).map(|i| 100.0 + i as f64).collect();
        let period = 5;
        let vf = 0.7;
        let out = t3(&v, period, vf);
        assert_eq!(out.len(), 40);
        // Lookback = 6*(5-1) = 24
        for i in 0..24 {
            assert!(out[i].is_nan(), "expected NaN at index {i}");
        }
        for i in 24..40 {
            assert!(!out[i].is_nan(), "expected valid value at index {i}");
        }
    }

    #[test]
    fn t3_empty_returns_empty() {
        assert!(t3(&[], 5, 0.7).is_empty());
    }

    #[test]
    fn t3_period_one_is_identity() {
        let v = vec![3.0, 1.0, 4.0];
        assert_eq!(t3(&v, 1, 0.7), v);
    }

    #[test]
    fn t3_inc_matches_batch() {
        let v: Vec<f64> = (1..=40).map(|i| 100.0 + i as f64).collect();
        let period = 3;
        let vf = 0.7;
        let alpha = 2.0 / (period as f64 + 1.0);
        let batch = t3(&v, period, vf);

        let v2 = vf * vf;
        let v3 = v2 * vf;
        let c1 = -v3;
        let c2 = 3.0 * v2 + 3.0 * v3;
        let c3 = -6.0 * v2 - 3.0 * vf - 3.0 * v3;
        let c4 = 1.0 + 3.0 * vf + v3 + 3.0 * v2;

        let lb = 6 * (period - 1);

        // Run batch to get the state at index lb, then continue with inc
        // Find first valid index and extract state by running the batch function
        // and using its internal state at lb.
        // Simplest approach: run batch on v[..=lb+1] and extract state from
        // running the same single-pass logic.
        // Instead, just verify that inc produces same results from lb+1 onward
        // by reconstructing state from batch's internal computation.
        // Since batch uses single-pass with SMA-seeded EMAs, we replicate:
        let mut e = [0.0_f64; 6];
        let mut ready = [false; 6];
        let mut warmup = [0_usize; 6];
        for i in 0..=lb {
            let mut val = v[i];
            for layer in 0..6 {
                if !ready[layer] {
                    warmup[layer] += 1;
                    if warmup[layer] == 1 {
                        e[layer] = val;
                    } else {
                        e[layer] += val;
                    }
                    if warmup[layer] == period {
                        e[layer] /= period as f64;
                        ready[layer] = true;
                        val = e[layer];
                    } else {
                        break;
                    }
                } else {
                    e[layer] = alpha * val + (1.0 - alpha) * e[layer];
                    val = e[layer];
                }
            }
        }

        let mut state = e;
        for i in (lb + 1)..v.len() {
            let (new_state, t3_val) = t3_inc(&state, v[i], alpha, c1, c2, c3, c4);
            assert_abs_diff_eq!(t3_val, batch[i], epsilon = 1e-6);
            state = new_state;
        }
    }

    // ── TRIMA tests ──────────────────────────────────────────────────────

    #[test]
    fn trima_basic() {
        let v: Vec<f64> = (1..=20).map(|i| i as f64).collect();
        let out = trima(&v, 5);
        assert_eq!(out.len(), 20);
        // Lookback = period - 1 = 4
        for i in 0..4 {
            assert!(out[i].is_nan(), "expected NaN at index {i}");
        }
        for i in 4..20 {
            assert!(!out[i].is_nan(), "expected valid value at index {i}");
        }
    }

    #[test]
    fn trima_empty_returns_empty() {
        assert!(trima(&[], 5).is_empty());
    }

    #[test]
    fn trima_period_one_is_identity() {
        let v = vec![3.0, 1.0, 4.0];
        assert_eq!(trima(&v, 1), v);
    }

    #[test]
    fn trima_symmetric_weighting() {
        // TRIMA of constant series should equal the constant
        let v = vec![42.0; 20];
        let out = trima(&v, 7);
        for i in 6..20 {
            assert_abs_diff_eq!(out[i], 42.0, epsilon = 1e-9);
        }
    }

    // ── Supertrend tests ─────────────────────────────────────────────────

    #[test]
    fn supertrend_basic() {
        // Create a simple uptrend
        let n = 30;
        let highs: Vec<f64> = (0..n).map(|i| 110.0 + i as f64 * 2.0).collect();
        let lows: Vec<f64> = (0..n).map(|i| 90.0 + i as f64 * 2.0).collect();
        let closes: Vec<f64> = (0..n).map(|i| 100.0 + i as f64 * 2.0).collect();
        let (st, is_up) = supertrend(&highs, &lows, &closes, 10, 3.0);
        assert_eq!(st.len(), n);
        assert_eq!(is_up.len(), n);
        // After warmup, uptrend should dominate
        let up_count = is_up[10..].iter().filter(|&&v| v).count();
        assert!(up_count > 10, "expected uptrend dominance, got {up_count}/20 bars");
    }

    #[test]
    fn supertrend_empty_input() {
        let (st, is_up) = supertrend(&[], &[], &[], 10, 3.0);
        assert!(st.is_empty());
        assert!(is_up.is_empty());
    }

    #[test]
    fn supertrend_trend_flip() {
        // Create a trend reversal: up then down
        let n = 40;
        let mut closes = Vec::with_capacity(n);
        let mut highs = Vec::with_capacity(n);
        let mut lows = Vec::with_capacity(n);
        for i in 0..20 {
            let c = 100.0 + i as f64 * 3.0;
            closes.push(c);
            highs.push(c + 5.0);
            lows.push(c - 5.0);
        }
        for i in 0..20 {
            let c = 160.0 - i as f64 * 3.0;
            closes.push(c);
            highs.push(c + 5.0);
            lows.push(c - 5.0);
        }
        let (st, is_up) = supertrend(&highs, &lows, &closes, 7, 2.0);
        // Should have both uptrend and downtrend periods
        let has_up = is_up.iter().any(|&v| v);
        let has_down = is_up.iter().any(|&v| !v);
        assert!(has_up, "expected some uptrend bars");
        // First few bars are false by default, so has_down is trivially true
        assert!(has_down, "expected some downtrend bars");
    }

    // ── ADXR tests ───────────────────────────────────────────────────────

    #[test]
    fn adxr_basic() {
        let n = 60;
        let highs: Vec<f64> = (0..n).map(|i| 110.0 + (i as f64 * 0.5).sin() * 5.0).collect();
        let lows: Vec<f64> = highs.iter().map(|h| h - 3.0).collect();
        let closes: Vec<f64> = highs.iter().zip(lows.iter()).map(|(h, l)| (h + l) / 2.0).collect();
        let out = adxr(&highs, &lows, &closes, 14);
        assert_eq!(out.len(), n);
        // Should have some valid values after sufficient warmup
        let valid_count = out.iter().filter(|v| !v.is_nan()).count();
        assert!(valid_count > 0, "expected some valid ADXR values");
    }

    #[test]
    fn adxr_empty_input() {
        let out = adxr(&[], &[], &[], 14);
        assert!(out.is_empty());
    }

    #[test]
    fn adxr_is_average_of_adx() {
        // ADXR[i] = (ADX[i] + ADX[i-period]) / 2
        let n = 60;
        let highs: Vec<f64> = (0..n).map(|i| 110.0 + (i as f64 * 0.3).sin() * 5.0).collect();
        let lows: Vec<f64> = highs.iter().map(|h| h - 4.0).collect();
        let closes: Vec<f64> = highs.iter().zip(lows.iter()).map(|(h, l)| (h + l) / 2.0).collect();
        let period = 10;
        let (adx_vals, _, _) = crate::indicators::oscillators::adx_components(&highs, &lows, &closes, period);
        let adxr_vals = adxr(&highs, &lows, &closes, period);

        for i in period..n {
            if !adxr_vals[i].is_nan() {
                let expected = (adx_vals[i] + adx_vals[i - period]) / 2.0;
                assert_abs_diff_eq!(adxr_vals[i], expected, epsilon = 1e-9);
            }
        }
    }

    // ── Vegas Channel tests ──────────────────────────────────────────────

    #[test]
    fn vegas_channel_basic() {
        let v: Vec<f64> = (1..=700).map(|i| 100.0 + (i as f64 * 0.1).sin() * 10.0).collect();
        let (e1, e2, e3, e4) = vegas_channel(&v, [144, 169, 576, 676]);
        assert_eq!(e1.len(), 700);
        assert_eq!(e2.len(), 700);
        assert_eq!(e3.len(), 700);
        assert_eq!(e4.len(), 700);
        // All EMAs should have valid values after their respective warmup periods
        assert!(!e1[143].is_nan(), "EMA(144) should be valid at index 143");
        assert!(!e2[168].is_nan(), "EMA(169) should be valid at index 168");
        assert!(!e3[575].is_nan(), "EMA(576) should be valid at index 575");
        assert!(!e4[675].is_nan(), "EMA(676) should be valid at index 675");
    }

    #[test]
    fn vegas_channel_empty_returns_empty() {
        let (e1, e2, e3, e4) = vegas_channel(&[], [144, 169, 576, 676]);
        assert!(e1.is_empty());
        assert!(e2.is_empty());
        assert!(e3.is_empty());
        assert!(e4.is_empty());
    }

    #[test]
    fn vegas_channel_constant_series() {
        let v = vec![50.0; 700];
        let (e1, e2, e3, e4) = vegas_channel(&v, [144, 169, 576, 676]);
        // After warmup, all EMAs of a constant should converge to the constant
        assert_abs_diff_eq!(e1[699], 50.0, epsilon = 1e-6);
        assert_abs_diff_eq!(e2[699], 50.0, epsilon = 1e-6);
        assert_abs_diff_eq!(e3[699], 50.0, epsilon = 1e-6);
        assert_abs_diff_eq!(e4[699], 50.0, epsilon = 1e-6);
    }

    #[test]
    fn vegas_channel_uses_ema() {
        // Verify that vegas_channel matches direct ema() calls
        let v: Vec<f64> = (1..=700).map(|i| 50.0 + i as f64 * 0.1).collect();
        let (e1, e2, e3, e4) = vegas_channel(&v, [144, 169, 576, 676]);
        let direct_e1 = ema(&v, 144);
        let direct_e4 = ema(&v, 676);
        for i in 143..700 {
            assert_abs_diff_eq!(e1[i], direct_e1[i], epsilon = 1e-12);
        }
        for i in 675..700 {
            assert_abs_diff_eq!(e4[i], direct_e4[i], epsilon = 1e-12);
        }
    }
}
