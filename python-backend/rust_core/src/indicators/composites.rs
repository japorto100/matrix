// composites.rs — Cross-module indicator composites + signal techniques
//
// Functions that combine primitives from multiple indicator modules.
// These live here (not in volatility/oscillators) to keep dependency direction clean.
//
// Python ref: volatility.py (squeeze, atr_rsi, bb_on_rsi, bb signals)
//             oscillators.py (K's Collection signals, Rob Booker, RSI techniques)
//
// kand-Blueprint pattern adopted:
//   batch fn()       — full series computation
//   fn _inc()        — incremental where practical

use super::oscillators::{macd_components, rsi, stochastic};
use super::trend::{ema_seed_first as ema, iwma, sma, wma};
use super::volatility::{atr, bb_bands_with_state, keltner_channels};

// ── BB-Keltner Squeeze (TTM Squeeze) ────────────────────────────────────────

/// TTM Squeeze: detects when Bollinger Bands are inside Keltner Channels.
///
/// Returns `(squeeze_on, momentum)`:
/// - `squeeze_on[i]` = true when BB is inside KC (low volatility compression)
/// - `momentum[i]` = close - avg(bb_mid, kc_mid) — directional bias
///
/// Python ref: `volatility.py::calculate_bollinger_keltner_squeeze()`.
pub fn bb_keltner_squeeze(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    bb_period: usize,
    bb_num_std: f64,
    kc_period: usize,
    kc_mult: f64,
) -> (Vec<bool>, Vec<f64>) {
    let n = closes.len();
    let (bb_upper, bb_mid, bb_lower, _, _) =
        bb_bands_with_state(closes, bb_period, bb_num_std);
    let (kc_upper, kc_mid, kc_lower) =
        keltner_channels(highs, lows, closes, kc_period, kc_period, kc_mult);

    let mut squeeze = Vec::with_capacity(n);
    let mut momentum = Vec::with_capacity(n);

    for i in 0..n {
        squeeze.push(bb_upper[i] <= kc_upper[i] && bb_lower[i] >= kc_lower[i]);
        momentum.push(closes[i] - (bb_mid[i] + kc_mid[i]) / 2.0);
    }

    (squeeze, momentum)
}

// ── ATR-RSI ─────────────────────────────────────────────────────────────────

/// ATR-adjusted RSI: gains/losses normalised by ATR for smoother volatile-market signal.
///
/// Instead of raw price deltas, uses `delta / ATR` before computing RSI-style
/// avg_gain / avg_loss ratio. Clamps output to [0, 100].
///
/// Python ref: `volatility.py::calculate_atr_rsi()`.
pub fn atr_rsi(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    rsi_period: usize,
    atr_period: usize,
) -> Vec<f64> {
    let n = closes.len();
    if n < 2 {
        return vec![50.0; n];
    }

    let atr_vals = atr(highs, lows, closes, atr_period);

    // Compute ATR-normalised gains and losses
    let mut gains = vec![0.0_f64; n];
    let mut losses = vec![0.0_f64; n];
    for i in 1..n {
        let delta = closes[i] - closes[i - 1];
        let atr_norm = atr_vals[i].max(1e-9);
        if delta > 0.0 {
            gains[i] = delta / atr_norm;
        } else {
            losses[i] = (-delta) / atr_norm;
        }
    }

    // SMA-based RSI on normalised series
    let avg_gain = sma(&gains, rsi_period);
    let avg_loss = sma(&losses, rsi_period);

    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        let g = avg_gain[i];
        let l = avg_loss[i];
        let val = if l < 1e-12 {
            100.0
        } else {
            100.0 - (100.0 / (1.0 + g / l))
        };
        out.push(val.clamp(0.0, 100.0));
    }
    out
}

// ── Bollinger on RSI ────────────────────────────────────────────────────────

/// Bollinger Bands applied to the RSI series (not to raw prices).
///
/// Returns `(upper, middle, lower)` where middle is the SMA of RSI values.
///
/// Python ref: `volatility.py::calculate_bollinger_on_rsi()`.
pub fn bb_on_rsi(
    closes: &[f64],
    rsi_period: usize,
    bb_period: usize,
    num_std: f64,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let rsi_vals = rsi(closes, rsi_period);
    let (upper, middle, lower, _, _) = bb_bands_with_state(&rsi_vals, bb_period, num_std);
    (upper, middle, lower)
}

// ── BB Signal Techniques (Kaabar 2026, Ch. 3) ───────────────────────────────

/// BB Conservative signal: "Return to Normality" — price re-enters bands from outside.
///
/// Output: +1.0 = bullish (re-enters from below lower), -1.0 = bearish (re-enters from above upper), 0.0 = neutral.
///
/// Python ref: `volatility.py::calculate_bb_conservative()`.
pub fn bb_conservative_signal(closes: &[f64], period: usize, num_std: f64) -> Vec<f64> {
    let n = closes.len();
    let (upper, mid, lower, _, _) = bb_bands_with_state(closes, period, num_std);
    let mut signals = vec![0.0; n];

    for i in 1..n {
        if closes[i] > lower[i] && closes[i] < mid[i] && closes[i - 1] <= lower[i - 1] {
            signals[i] = 1.0;
        } else if closes[i] < upper[i] && closes[i] > mid[i] && closes[i - 1] >= upper[i - 1]
        {
            signals[i] = -1.0;
        }
    }
    signals
}

/// BB Aggressive signal: contrarian mean-reversion entry when price pierces the band.
///
/// Output: +1.0 = bullish (pierces lower), -1.0 = bearish (pierces upper), 0.0 = neutral.
///
/// Python ref: `volatility.py::calculate_bb_aggressive()`.
pub fn bb_aggressive_signal(closes: &[f64], period: usize, num_std: f64) -> Vec<f64> {
    let n = closes.len();
    let (upper, _mid, lower, _, _) = bb_bands_with_state(closes, period, num_std);
    let mut signals = vec![0.0; n];

    for i in 1..n {
        if closes[i] < lower[i] && closes[i - 1] >= lower[i - 1] {
            signals[i] = 1.0;
        } else if closes[i] > upper[i] && closes[i - 1] <= upper[i - 1] {
            signals[i] = -1.0;
        }
    }
    signals
}

/// BB Trend-Friendly signal: Conservative signal + SMA trend filter.
///
/// Kaabar Ch.3: uses SMA with offset for trend confirmation.
/// Bullish: re-enters from below AND close > SMA(sma_period)[i - offset].
/// Bearish: re-enters from above AND close < SMA(sma_period)[i - offset].
///
/// Python ref: `volatility.py::calculate_bb_trend_friendly()`.
pub fn bb_trend_friendly_signal(
    closes: &[f64],
    bb_period: usize,
    num_std: f64,
    sma_period: usize,
    sma_offset: usize,
) -> Vec<f64> {
    let n = closes.len();
    let (upper, mid, lower, _, _) = bb_bands_with_state(closes, bb_period, num_std);
    let sma_trend = sma(closes, sma_period);
    let mut signals = vec![0.0; n];

    let start = sma_offset.max(1);
    for i in start..n {
        let sma_ref = if i >= sma_offset {
            sma_trend[i - sma_offset]
        } else {
            sma_trend[0]
        };

        if closes[i] > lower[i]
            && closes[i] < mid[i]
            && closes[i - 1] <= lower[i - 1]
            && closes[i] > sma_ref
        {
            signals[i] = 1.0;
        } else if closes[i] < upper[i]
            && closes[i] > mid[i]
            && closes[i - 1] >= upper[i - 1]
            && closes[i] < sma_ref
        {
            signals[i] = -1.0;
        }
    }
    signals
}

// ── K's Reversal I (Kaabar Ch.11) ───────────────────────────────────────────

/// K's Reversal I: BB(100) + MACD(12/26/9) crossover.
///
/// Bullish: low < BB lower AND high < BB mid AND MACD crosses above signal.
/// Bearish: high > BB upper AND low > BB mid AND MACD crosses below signal.
/// Signal fires on bar i+1 (confirmation bar).
///
/// Python ref: `oscillators.py::calculate_ks_collection()` → reversalI.
pub fn ks_reversal_i(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
) -> Vec<f64> {
    let n = closes.len();
    let (bb_upper, bb_mid, bb_lower, _, _) = bb_bands_with_state(closes, 100, 2.0);
    let (macd_line, signal_line, _) = macd_components(closes, 12, 26, 9);
    let mut signals = vec![0.0; n];

    for i in 1..n.saturating_sub(1) {
        if lows[i] < bb_lower[i]
            && highs[i] < bb_mid[i]
            && macd_line[i] > signal_line[i]
            && macd_line[i - 1] < signal_line[i - 1]
        {
            signals[i + 1] = 1.0;
        } else if highs[i] > bb_upper[i]
            && lows[i] > bb_mid[i]
            && macd_line[i] < signal_line[i]
            && macd_line[i - 1] > signal_line[i - 1]
        {
            signals[i + 1] = -1.0;
        }
    }
    signals
}

// ── K's Reversal II (Kaabar Ch.11) ──────────────────────────────────────────

/// K's Reversal II: SMA(13) + rolling 21-bar above-count.
///
/// Bullish: all 21 bars below SMA(13). Bearish: all 21 bars above SMA(13).
///
/// Python ref: `oscillators.py::calculate_ks_collection()` → reversalII.
pub fn ks_reversal_ii(closes: &[f64]) -> Vec<f64> {
    let n = closes.len();
    let sma_13 = sma(closes, 13);
    let mut signals = vec![0.0; n];

    for i in 20..n {
        let mut count_above = 0usize;
        for j in (i.saturating_sub(20))..=i {
            if closes[j] > sma_13[j] {
                count_above += 1;
            }
        }
        if count_above == 0 {
            signals[i] = 1.0; // all below SMA → oversold → bullish
        } else if count_above == 21 {
            signals[i] = -1.0; // all above SMA → overbought → bearish
        }
    }
    signals
}

// ── K's MARSI (Kaabar Ch.11) ────────────────────────────────────────────────

/// K's MARSI: RSI(20) applied to SMA(200). Signal fires on dwell-bar threshold crossings.
///
/// Bullish: MARSI > 2 after 3+ bars below 2.
/// Bearish: MARSI < 98 after 3+ bars above 98.
///
/// Python ref: `oscillators.py::calculate_ks_collection()` → marsiSignal.
pub fn ks_marsi_signal(closes: &[f64]) -> Vec<f64> {
    let n = closes.len();
    let sma_200 = sma(closes, 200);
    let marsi = rsi(&sma_200, 20);
    let mut signals = vec![0.0; n];

    for i in 3..n {
        if marsi[i] > 2.0
            && marsi[i - 1] < 2.0
            && marsi[i - 2] < 2.0
            && marsi[i - 3] < 2.0
        {
            signals[i] = 1.0;
        } else if marsi[i] < 98.0
            && marsi[i - 1] > 98.0
            && marsi[i - 2] > 98.0
            && marsi[i - 3] > 98.0
        {
            signals[i] = -1.0;
        }
    }
    signals
}

// ── K's Fibonacci MA (Kaabar Ch.11) ─────────────────────────────────────────

/// K's Fibonacci MA: average of 15 Fibonacci-period EMAs on highs and lows.
///
/// Returns `(fma_high, fma_mid, fma_low)`.
///
/// Python ref: `oscillators.py::calculate_ks_collection()` → fibonacciMA.
pub fn ks_fibonacci_ma(
    highs: &[f64],
    lows: &[f64],
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    const FIB_PERIODS: [usize; 15] = [
        2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597,
    ];
    let n = highs.len();
    let k = FIB_PERIODS.len() as f64;

    let ema_h: Vec<Vec<f64>> = FIB_PERIODS.iter().map(|&p| ema(highs, p)).collect();
    let ema_l: Vec<Vec<f64>> = FIB_PERIODS.iter().map(|&p| ema(lows, p)).collect();

    let mut fma_h = Vec::with_capacity(n);
    let mut fma_l = Vec::with_capacity(n);
    let mut fma_mid = Vec::with_capacity(n);

    for i in 0..n {
        let h_avg: f64 = ema_h.iter().map(|e| e[i]).sum::<f64>() / k;
        let l_avg: f64 = ema_l.iter().map(|e| e[i]).sum::<f64>() / k;
        fma_h.push(h_avg);
        fma_l.push(l_avg);
        fma_mid.push((h_avg + l_avg) / 2.0);
    }

    (fma_h, fma_mid, fma_l)
}

// ── Rob Booker Reversal (Kaabar Ch.12) ──────────────────────────────────────

/// Rob Booker Reversal: MACD zero-cross confirmed by extreme Stochastic.
///
/// Bullish: MACD crosses above 0 AND %K(70,10,10) < stoch_lower.
/// Bearish: MACD crosses below 0 AND %K(70,10,10) > stoch_upper.
///
/// Python ref: `oscillators.py::calculate_rob_booker_reversal()`.
pub fn rob_booker_reversal(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    stoch_k_period: usize,
    stoch_smooth_k: usize,
    macd_fast: usize,
    macd_slow: usize,
    macd_signal: usize,
    stoch_lower: f64,
    stoch_upper: f64,
) -> Vec<f64> {
    let n = closes.len();
    let (macd_line, _, _) = macd_components(closes, macd_fast, macd_slow, macd_signal);

    // Stochastic with custom params — compute raw %K then smooth
    let (raw_k, _) = stochastic(highs, lows, closes, stoch_k_period, 1);
    let smooth_k = sma(&raw_k, stoch_smooth_k);

    let mut signals = vec![0.0; n];
    for i in 1..n {
        let cross_up = macd_line[i] > 0.0 && macd_line[i - 1] <= 0.0;
        let cross_down = macd_line[i] < 0.0 && macd_line[i - 1] >= 0.0;
        if cross_up && smooth_k[i] < stoch_lower {
            signals[i] = 1.0;
        } else if cross_down && smooth_k[i] > stoch_upper {
            signals[i] = -1.0;
        }
    }
    signals
}

// ── Cross-Asset RSI Convergence (Kaabar Ch.6) ───────────────────────────────

/// RSI convergence across inversely-correlated assets.
///
/// Bullish: primary RSI < lower (oversold) AND inverse RSI > upper (overbought).
/// Bearish: primary RSI > upper AND inverse RSI < lower.
///
/// Python ref: `oscillators.py::calculate_cross_asset_convergence()`.
pub fn cross_asset_rsi_convergence(
    primary_closes: &[f64],
    inverse_closes: &[f64],
    rsi_period: usize,
    lower: f64,
    upper: f64,
) -> Vec<f64> {
    let p_rsi = rsi(primary_closes, rsi_period);
    let i_rsi = rsi(inverse_closes, rsi_period);
    let n = p_rsi.len().min(i_rsi.len());

    let mut signals = vec![0.0; n];
    for i in 0..n {
        if p_rsi[i] < lower && i_rsi[i] > upper {
            signals[i] = 1.0;
        } else if p_rsi[i] > upper && i_rsi[i] < lower {
            signals[i] = -1.0;
        }
    }
    signals
}

// ── RSI V-Technique (Kaabar Ch.3) ───────────────────────────────────────────

/// RSI V-Technique: V-shaped bounce from extreme zone.
///
/// Bullish: RSI dips below lower, exits while still < 50.
/// Bearish: RSI spikes above upper, drops while still > 50.
///
/// Python ref: `oscillators.py::calculate_rsi_v_technique()`.
pub fn rsi_v_technique(
    closes: &[f64],
    rsi_period: usize,
    lower: f64,
    upper: f64,
) -> Vec<f64> {
    let n = closes.len();
    let rs = rsi(closes, rsi_period);
    let mut signals = vec![0.0; n];

    for i in 2..n {
        // V-bounce: was above lower → dipped below → exited back (still < 50)
        if rs[i] > lower && rs[i] < 50.0 && rs[i - 1] < lower && rs[i - 2] > lower {
            signals[i] = 1.0;
        }
        // Lambda: was below upper → spiked above → dropped back (still > 50)
        else if rs[i] < upper && rs[i] > 50.0 && rs[i - 1] > upper && rs[i - 2] < upper {
            signals[i] = -1.0;
        }
    }
    signals
}

// ── RSI DCC — Double Conservative Confirmation (Kaabar Ch.3) ────────────────

/// RSI DCC: both RSI(fast) and RSI(slow) cross threshold on same bar (±tolerance).
///
/// Kaabar: "A personal favorite of mine, despite having significantly less frequency."
///
/// Python ref: `oscillators.py::calculate_rsi_dcc()`.
pub fn rsi_dcc(
    closes: &[f64],
    fast_period: usize,
    slow_period: usize,
    lower: f64,
    upper: f64,
    tolerance: usize,
) -> Vec<f64> {
    let n = closes.len();
    let rs_fast = rsi(closes, fast_period);
    let rs_slow = rsi(closes, slow_period);
    let mut signals = vec![0.0; n];

    for i in 1..n {
        // Fast RSI crosses above lower
        let fast_bull = rs_fast[i] > lower && rs_fast[i - 1] <= lower;
        if fast_bull {
            let slow_bull = (i.saturating_sub(tolerance)..=(i + tolerance).min(n - 1)).any(|j| {
                j >= 1 && rs_slow[j] > lower && rs_slow[j - 1] <= lower
            });
            if slow_bull {
                signals[i] = 1.0;
                continue;
            }
        }

        // Fast RSI crosses below upper
        let fast_bear = rs_fast[i] < upper && rs_fast[i - 1] >= upper;
        if fast_bear {
            let slow_bear = (i.saturating_sub(tolerance)..=(i + tolerance).min(n - 1)).any(|j| {
                j >= 1 && rs_slow[j] < upper && rs_slow[j - 1] >= upper
            });
            if slow_bear {
                signals[i] = -1.0;
            }
        }
    }
    signals
}

// ── RSI MA Cross (Kaabar Ch.3) ──────────────────────────────────────────────

/// RSI MA Cross: RSI crosses above/below SMA(RSI) while in extreme zone.
///
/// Bullish: RSI crosses above SMA(RSI) while RSI < lower.
/// Bearish: RSI crosses below SMA(RSI) while RSI > upper.
///
/// Python ref: `oscillators.py::calculate_rsi_ma_cross()`.
pub fn rsi_ma_cross(
    closes: &[f64],
    rsi_period: usize,
    sma_period: usize,
    lower: f64,
    upper: f64,
) -> Vec<f64> {
    let n = closes.len();
    let rs = rsi(closes, rsi_period);
    let rs_sma = sma(&rs, sma_period);
    let mut signals = vec![0.0; n];

    for i in 1..n {
        if rs[i] > rs_sma[i] && rs[i - 1] <= rs_sma[i - 1] && rs[i] < lower {
            signals[i] = 1.0;
        } else if rs[i] < rs_sma[i] && rs[i - 1] >= rs_sma[i - 1] && rs[i] > upper {
            signals[i] = -1.0;
        }
    }
    signals
}

// ── WMA / IWMA Cross (Kaabar Ch.3) ────────────────────────────────────────

/// WMA/IWMA single-parameter cross signal (Kaabar Ch.3).
///
/// WMA is recent-biased, IWMA is history-biased. Using the same period removes
/// one parameter while creating a meaningful divergence signal.
///
/// Returns +1.0 when WMA crosses above IWMA (bullish),
/// -1.0 when WMA crosses below IWMA (bearish), 0.0 otherwise.
///
/// Python ref: `trend.py::calculate_wma_iwma_cross()`.
pub fn wma_iwma_cross(closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    if n < 2 {
        return vec![0.0; n];
    }
    let wma_vals = wma(closes, period);
    let iwma_vals = iwma(closes, period);
    let mut signals = vec![0.0_f64; n];
    for i in 1..n {
        if wma_vals[i] > iwma_vals[i] && wma_vals[i - 1] <= iwma_vals[i - 1] {
            signals[i] = 1.0;
        } else if wma_vals[i] < iwma_vals[i] && wma_vals[i - 1] >= iwma_vals[i - 1] {
            signals[i] = -1.0;
        }
    }
    signals
}

// ── K's Collection Aggregator (Kaabar Ch.11) ─────────────────────────────────

/// K's Collection — all 6 K's indicators aggregated in one call.
///
/// Returns individual signal arrays + continuous oscillators.
/// Mirrors Python: `oscillators.py::calculate_ks_collection()`.
#[derive(Debug, Clone)]
pub struct KsCollection {
    /// K's Reversal I signals (-1/0/+1).
    pub reversal_i: Vec<f64>,
    /// K's Reversal II signals (-1/0/+1).
    pub reversal_ii: Vec<f64>,
    /// K's ATR-adjusted RSI (continuous 0-100).
    pub atr_adjusted_rsi: Vec<f64>,
    /// K's RSI² — RSI(5) of RSI(14) (continuous 0-100).
    pub rsi_squared: Vec<f64>,
    /// K's MARSI values (continuous 0-100).
    pub marsi_values: Vec<f64>,
    /// K's MARSI signals (-1/0/+1).
    pub marsi_signals: Vec<f64>,
    /// Fibonacci MA high band.
    pub fma_high: Vec<f64>,
    /// Fibonacci MA mid (average of high/low).
    pub fma_mid: Vec<f64>,
    /// Fibonacci MA low band.
    pub fma_low: Vec<f64>,
}

/// Calculate all K's Collection indicators in one call.
///
/// Combines: `ks_reversal_i`, `ks_reversal_ii`, `ks_marsi_signal`, `ks_fibonacci_ma`
/// plus ATR-RSI and RSI² which are simple compositions of existing primitives.
pub fn calculate_ks_collection(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
) -> KsCollection {
    // K's Reversal I & II
    let reversal_i = ks_reversal_i(highs, lows, closes);
    let reversal_ii = ks_reversal_ii(closes);

    // K's ATR-adjusted RSI: RSI(13) * ATR(5) → RSI(13)
    let rsi_13 = rsi(closes, 13);
    let atr_5 = atr(highs, lows, closes, 5);
    let rsi_x_atr: Vec<f64> = rsi_13
        .iter()
        .zip(atr_5.iter())
        .map(|(&r, &a)| r * a)
        .collect();
    let atr_adjusted_rsi = rsi(&rsi_x_atr, 13);

    // K's RSI²: RSI(14, close) → RSI(5, rsi14)
    let rsi_14 = rsi(closes, 14);
    let rsi_squared = rsi(&rsi_14, 5);

    // K's MARSI
    let marsi_signals = ks_marsi_signal(closes);
    let sma_200 = sma(closes, 200);
    let marsi_values = rsi(&sma_200, 20);

    // K's Fibonacci MA
    let (fma_high, fma_mid, fma_low) = ks_fibonacci_ma(highs, lows);

    KsCollection {
        reversal_i,
        reversal_ii,
        atr_adjusted_rsi,
        rsi_squared,
        marsi_values,
        marsi_signals,
        fma_high,
        fma_mid,
        fma_low,
    }
}

// ── Composite Signal (Multi-Factor) ──────────────────────────────────────────

/// Composite signal result.
#[derive(Debug, Clone)]
pub struct CompositeSignalResult {
    /// Signal direction: 1=buy, -1=sell, 0=neutral.
    pub signal: i8,
    /// Overall confidence 0.0-1.0.
    pub confidence: f64,
    /// SMA50 slope score (0-1).
    pub sma_score: f64,
    /// SMA50 slope direction: 1=rising, -1=falling, 0=flat.
    pub sma_direction: i8,
    /// SMA50 normalised slope value.
    pub slope_norm: f64,
    /// Heartbeat score (0-1).
    pub heartbeat_score: f64,
    /// Volume power score (0-1).
    pub volume_score: f64,
    /// Relative volume (latest / avg).
    pub rvol: f64,
}

/// Build composite signal from SMA slope + heartbeat + volume power.
///
/// Mirrors Python: `oscillators.py::build_composite_signal()`.
pub fn build_composite_signal(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    volumes: &[f64],
    volume_spike_threshold: f64,
    heartbeat_threshold: f64,
) -> CompositeSignalResult {
    let n = closes.len();
    if n < 2 {
        return CompositeSignalResult {
            signal: 0,
            confidence: 0.0,
            sma_score: 0.0,
            sma_direction: 0,
            slope_norm: 0.0,
            heartbeat_score: 0.0,
            volume_score: 0.0,
            rvol: 1.0,
        };
    }

    // SMA50 slope
    let sma50 = sma(closes, 50);
    let slope_period = 5.min(sma50.len().saturating_sub(1));
    let slope_value = if slope_period > 0 {
        sma50[sma50.len() - 1] - sma50[sma50.len() - 1 - slope_period]
    } else {
        0.0
    };
    let last_sma = sma50[sma50.len() - 1];
    let slope_norm_val = if last_sma.abs() > 1e-9 {
        slope_value / last_sma
    } else {
        0.0
    };
    let sma_score = (slope_norm_val.abs() * 180.0).clamp(0.0, 1.0);
    let sma_direction = if slope_value > 0.0 {
        1
    } else if slope_value < 0.0 {
        -1
    } else {
        0
    };

    // Heartbeat score (uses existing heartbeat_impl from oscillators)
    let heartbeat = super::oscillators::calculate_heartbeat_impl(closes, highs, lows, 0.0)
        .unwrap_or(0.0);

    // Volume power: RVOL + OBV slope + CMF
    let vol_period = 20.min(volumes.len());
    let latest_vol = *volumes.last().unwrap_or(&0.0);
    let avg_vol = if vol_period > 0 {
        volumes[volumes.len() - vol_period..].iter().sum::<f64>() / vol_period as f64
    } else {
        1.0
    };
    let rvol = if avg_vol > 0.0 {
        latest_vol / avg_vol
    } else {
        1.0
    };

    // OBV slope (last 5 bars)
    let obv_vals = super::volume::obv_series(closes, volumes);
    let obv_slope = if obv_vals.len() >= 5 {
        obv_vals[obv_vals.len() - 1] - obv_vals[obv_vals.len() - 5]
    } else if obv_vals.len() >= 2 {
        obv_vals[obv_vals.len() - 1] - obv_vals[0]
    } else {
        0.0
    };

    // CMF
    let cmf_period = 20.min(n);
    let cmf_vals = super::volume::cmf_series(highs, lows, closes, volumes, cmf_period);
    let latest_cmf = *cmf_vals.last().unwrap_or(&0.0);

    let mut volume_score: f64 = 0.0;
    if rvol >= volume_spike_threshold {
        volume_score += 0.45;
    }
    if obv_slope > 0.0 {
        volume_score += 0.3;
    }
    if latest_cmf > 0.0 {
        volume_score += 0.25;
    }
    volume_score = volume_score.clamp(0.0, 1.0);

    // Signal
    let signal = if slope_value > 0.0
        && heartbeat >= heartbeat_threshold
        && volume_score >= 0.55
    {
        1 // buy
    } else if slope_value < 0.0
        && heartbeat >= heartbeat_threshold
        && volume_score >= 0.55
    {
        -1 // sell
    } else {
        0 // neutral
    };

    let confidence = ((sma_score + heartbeat + volume_score) / 3.0).clamp(0.0, 1.0);

    CompositeSignalResult {
        signal,
        confidence,
        sma_score,
        sma_direction,
        slope_norm: slope_norm_val,
        heartbeat_score: heartbeat,
        volume_score,
        rvol,
    }
}

// ── Swarm Validation (Kaabar Ch.4/9/11) ──────────────────────────────────────

/// Swarm signal entry — pattern detected on 1-3 chart systems.
#[derive(Debug, Clone)]
pub struct SwarmSignal {
    /// Pattern type identifier.
    pub pattern_type: &'static str,
    /// 1=bullish, -1=bearish, 0=neutral.
    pub direction: i8,
    /// Start bar index.
    pub start_idx: usize,
    /// End bar index.
    pub end_idx: usize,
    /// Fraction of chart systems where pattern fired (0.33, 0.67, 1.0).
    pub swarming_ratio: f64,
    /// Which chart systems fired: "standard", "heikin_ashi", "k_candles".
    pub fired_on: Vec<&'static str>,
    /// Original confidence × swarming_ratio.
    pub confidence: f64,
}

/// Swarm validation result.
#[derive(Debug, Clone)]
pub struct SwarmResult {
    pub signals: Vec<SwarmSignal>,
    pub total_signals: usize,
    pub fully_swarmed: usize,
}

/// Run pattern detection on Standard + Heikin-Ashi + K's CCS, return swarmed signals.
///
/// Kaabar: "The interesting part is where you consider the signal only when it's
/// visible across all three candlestick systems."
///
/// `pattern_type`: "candlestick", "timing", or "price"
///
/// Mirrors Python: `helpers.py::swarm_validate()`.
pub fn swarm_validate(
    opens: &[f64],
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    lookback: usize,
) -> SwarmResult {
    use super::patterns::{build_candlestick_patterns, PatternDirection};
    use super::transforms::{heikin_ashi, k_candles};

    // 1. Standard chart
    let std_result = build_candlestick_patterns(opens, highs, lows, closes, lookback);

    // 2. Heikin-Ashi transform
    let (ha_o, ha_h, ha_l, ha_c) = heikin_ashi(opens, highs, lows, closes);
    let ha_result = build_candlestick_patterns(&ha_o, &ha_h, &ha_l, &ha_c, lookback);

    // 3. K's CCS transform (EMA(5) smoothed)
    let (k_o, k_h, k_l, k_c) = k_candles(opens, highs, lows, closes);
    let k_result = build_candlestick_patterns(&k_o, &k_h, &k_l, &k_c, lookback);

    // Collect all patterns keyed by (pattern_type, direction, start_idx, end_idx)
    let mut pattern_map: std::collections::HashMap<
        (&'static str, i8, usize, usize),
        (Vec<&'static str>, f64),
    > = std::collections::HashMap::new();

    let dir_to_i8 = |d: PatternDirection| -> i8 {
        match d {
            PatternDirection::Bullish => 1,
            PatternDirection::Bearish => -1,
            PatternDirection::Neutral => 0,
        }
    };

    for (sys_name, result) in [
        ("standard", &std_result),
        ("heikin_ashi", &ha_result),
        ("k_candles", &k_result),
    ] {
        for p in &result.patterns {
            let key = (p.pattern_type, dir_to_i8(p.direction), p.start_idx, p.end_idx);
            let entry = pattern_map.entry(key).or_insert_with(|| (Vec::new(), p.confidence));
            entry.0.push(sys_name);
        }
    }

    // Build swarmed signals
    let mut signals: Vec<SwarmSignal> = pattern_map
        .into_iter()
        .map(|((pt, dir, si, ei), (fired_on, conf))| {
            let ratio = fired_on.len() as f64 / 3.0;
            SwarmSignal {
                pattern_type: pt,
                direction: dir,
                start_idx: si,
                end_idx: ei,
                swarming_ratio: (ratio * 100.0).round() / 100.0,
                fired_on,
                confidence: (conf * ratio * 10000.0).round() / 10000.0,
            }
        })
        .collect();

    // Sort by swarming_ratio descending
    signals.sort_by(|a, b| b.swarming_ratio.partial_cmp(&a.swarming_ratio).unwrap_or(std::cmp::Ordering::Equal));

    let fully_swarmed = signals.iter().filter(|s| s.swarming_ratio >= 1.0).count();
    let total = signals.len();

    SwarmResult {
        signals,
        total_signals: total,
        fully_swarmed,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    // Helper: generate synthetic OHLCV-ish data
    fn synth_data(n: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
        let mut highs = Vec::with_capacity(n);
        let mut lows = Vec::with_capacity(n);
        let mut closes = Vec::with_capacity(n);
        for i in 0..n {
            let base = 100.0 + (i as f64 * 0.3).sin() * 10.0;
            highs.push(base + 3.0);
            lows.push(base - 3.0);
            closes.push(base + 0.5);
        }
        (highs, lows, closes)
    }

    // ── BB-Keltner Squeeze ────────────────────────────────────────────────

    #[test]
    fn squeeze_output_lengths() {
        let (h, l, c) = synth_data(50);
        let (squeeze, momentum) = bb_keltner_squeeze(&h, &l, &c, 20, 2.0, 20, 1.5);
        assert_eq!(squeeze.len(), 50);
        assert_eq!(momentum.len(), 50);
    }

    #[test]
    fn squeeze_constant_input() {
        // Constant prices → BB collapses to zero width → always inside KC → always squeeze
        let h = vec![100.0; 40];
        let l = vec![100.0; 40];
        let c = vec![100.0; 40];
        let (squeeze, _) = bb_keltner_squeeze(&h, &l, &c, 20, 2.0, 20, 1.5);
        // After warmup, constant data should produce squeeze (BB width = 0)
        for &s in &squeeze[20..] {
            assert!(s, "constant input should produce squeeze");
        }
    }

    // ── ATR-RSI ───────────────────────────────────────────────────────────

    #[test]
    fn atr_rsi_output_length() {
        let (h, l, c) = synth_data(50);
        let result = atr_rsi(&h, &l, &c, 14, 14);
        assert_eq!(result.len(), 50);
    }

    #[test]
    fn atr_rsi_clamped_0_100() {
        let (h, l, c) = synth_data(80);
        let result = atr_rsi(&h, &l, &c, 14, 14);
        for &v in &result {
            assert!(v >= 0.0 && v <= 100.0, "ATR-RSI out of range: {v}");
        }
    }

    #[test]
    fn atr_rsi_short_input() {
        let result = atr_rsi(&[100.0], &[99.0], &[99.5], 14, 14);
        assert_eq!(result.len(), 1);
        assert_abs_diff_eq!(result[0], 50.0, epsilon = 1e-9);
    }

    // ── BB on RSI ─────────────────────────────────────────────────────────

    #[test]
    fn bb_on_rsi_output_lengths() {
        let (_, _, c) = synth_data(50);
        let (upper, middle, lower) = bb_on_rsi(&c, 14, 20, 2.0);
        assert_eq!(upper.len(), 50);
        assert_eq!(middle.len(), 50);
        assert_eq!(lower.len(), 50);
    }

    #[test]
    fn bb_on_rsi_upper_ge_lower() {
        let (_, _, c) = synth_data(60);
        let (upper, _, lower) = bb_on_rsi(&c, 14, 20, 2.0);
        for i in 0..60 {
            assert!(upper[i] >= lower[i], "bar {i}: upper < lower");
        }
    }

    // ── BB Conservative ───────────────────────────────────────────────────

    #[test]
    fn bb_conservative_output_length() {
        let (_, _, c) = synth_data(50);
        let signals = bb_conservative_signal(&c, 20, 2.0);
        assert_eq!(signals.len(), 50);
    }

    #[test]
    fn bb_conservative_values() {
        let (_, _, c) = synth_data(80);
        let signals = bb_conservative_signal(&c, 20, 2.0);
        for &s in &signals {
            assert!(
                s == 0.0 || s == 1.0 || s == -1.0,
                "signal must be -1, 0, or 1, got {s}"
            );
        }
    }

    // ── BB Aggressive ─────────────────────────────────────────────────────

    #[test]
    fn bb_aggressive_output_length() {
        let (_, _, c) = synth_data(50);
        let signals = bb_aggressive_signal(&c, 20, 2.0);
        assert_eq!(signals.len(), 50);
    }

    #[test]
    fn bb_aggressive_values() {
        let (_, _, c) = synth_data(80);
        let signals = bb_aggressive_signal(&c, 20, 2.0);
        for &s in &signals {
            assert!(
                s == 0.0 || s == 1.0 || s == -1.0,
                "signal must be -1, 0, or 1, got {s}"
            );
        }
    }

    // ── BB Trend-Friendly ─────────────────────────────────────────────────

    #[test]
    fn bb_trend_friendly_output_length() {
        let (_, _, c) = synth_data(120);
        let signals = bb_trend_friendly_signal(&c, 20, 2.0, 100, 10);
        assert_eq!(signals.len(), 120);
    }

    #[test]
    fn bb_trend_friendly_values() {
        let (_, _, c) = synth_data(120);
        let signals = bb_trend_friendly_signal(&c, 20, 2.0, 100, 10);
        for &s in &signals {
            assert!(
                s == 0.0 || s == 1.0 || s == -1.0,
                "signal must be -1, 0, or 1, got {s}"
            );
        }
    }

    #[test]
    fn bb_trend_friendly_first_bar_zero() {
        let (_, _, c) = synth_data(120);
        let signals = bb_trend_friendly_signal(&c, 20, 2.0, 100, 10);
        assert_abs_diff_eq!(signals[0], 0.0, epsilon = 1e-9);
    }

    // ── K's Reversal I ────────────────────────────────────────────────────

    #[test]
    fn ks_reversal_i_output_length() {
        let (h, l, c) = synth_data(120);
        let signals = ks_reversal_i(&h, &l, &c);
        assert_eq!(signals.len(), 120);
    }

    #[test]
    fn ks_reversal_i_valid_signals() {
        let (h, l, c) = synth_data(120);
        let signals = ks_reversal_i(&h, &l, &c);
        for &s in &signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "got {s}");
        }
    }

    // ── K's Reversal II ───────────────────────────────────────────────────

    #[test]
    fn ks_reversal_ii_output_length() {
        let (_, _, c) = synth_data(50);
        let signals = ks_reversal_ii(&c);
        assert_eq!(signals.len(), 50);
    }

    #[test]
    fn ks_reversal_ii_valid_signals() {
        let (_, _, c) = synth_data(80);
        let signals = ks_reversal_ii(&c);
        for &s in &signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "got {s}");
        }
    }

    // ── K's MARSI ─────────────────────────────────────────────────────────

    #[test]
    fn ks_marsi_signal_output_length() {
        let (_, _, c) = synth_data(250);
        let signals = ks_marsi_signal(&c);
        assert_eq!(signals.len(), 250);
    }

    #[test]
    fn ks_marsi_signal_valid_values() {
        let (_, _, c) = synth_data(250);
        let signals = ks_marsi_signal(&c);
        for &s in &signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "got {s}");
        }
    }

    // ── K's Fibonacci MA ──────────────────────────────────────────────────

    #[test]
    fn ks_fibonacci_ma_output_lengths() {
        let (h, l, _) = synth_data(50);
        let (fma_h, fma_mid, fma_l) = ks_fibonacci_ma(&h, &l);
        assert_eq!(fma_h.len(), 50);
        assert_eq!(fma_mid.len(), 50);
        assert_eq!(fma_l.len(), 50);
    }

    #[test]
    fn ks_fibonacci_ma_high_ge_low() {
        let (h, l, _) = synth_data(100);
        let (fma_h, _, fma_l) = ks_fibonacci_ma(&h, &l);
        for i in 0..100 {
            assert!(fma_h[i] >= fma_l[i], "bar {i}: fma_h < fma_l");
        }
    }

    // ── Rob Booker Reversal ───────────────────────────────────────────────

    #[test]
    fn rob_booker_output_length() {
        let (h, l, c) = synth_data(100);
        let signals = rob_booker_reversal(&h, &l, &c, 70, 10, 12, 26, 9, 30.0, 70.0);
        assert_eq!(signals.len(), 100);
    }

    #[test]
    fn rob_booker_valid_signals() {
        let (h, l, c) = synth_data(100);
        let signals = rob_booker_reversal(&h, &l, &c, 70, 10, 12, 26, 9, 30.0, 70.0);
        for &s in &signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "got {s}");
        }
    }

    // ── Cross-Asset RSI Convergence ───────────────────────────────────────

    #[test]
    fn cross_asset_output_length() {
        let primary: Vec<f64> = (0..80).map(|i| 100.0 + i as f64 * 0.5).collect();
        let inverse: Vec<f64> = (0..80).map(|i| 100.0 - i as f64 * 0.5).collect();
        let signals = cross_asset_rsi_convergence(&primary, &inverse, 14, 30.0, 70.0);
        assert_eq!(signals.len(), 80);
    }

    #[test]
    fn cross_asset_valid_signals() {
        let primary: Vec<f64> = (0..80).map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0).collect();
        let inverse: Vec<f64> = (0..80).map(|i| 100.0 - (i as f64 * 0.3).sin() * 10.0).collect();
        let signals = cross_asset_rsi_convergence(&primary, &inverse, 14, 30.0, 70.0);
        for &s in &signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "got {s}");
        }
    }

    // ── RSI V-Technique ───────────────────────────────────────────────────

    #[test]
    fn rsi_v_output_length() {
        let (_, _, c) = synth_data(80);
        let signals = rsi_v_technique(&c, 5, 15.0, 85.0);
        assert_eq!(signals.len(), 80);
    }

    #[test]
    fn rsi_v_valid_signals() {
        let (_, _, c) = synth_data(80);
        let signals = rsi_v_technique(&c, 5, 15.0, 85.0);
        for &s in &signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "got {s}");
        }
    }

    // ── RSI DCC ───────────────────────────────────────────────────────────

    #[test]
    fn rsi_dcc_output_length() {
        let (_, _, c) = synth_data(80);
        let signals = rsi_dcc(&c, 13, 34, 30.0, 70.0, 2);
        assert_eq!(signals.len(), 80);
    }

    #[test]
    fn rsi_dcc_valid_signals() {
        let (_, _, c) = synth_data(80);
        let signals = rsi_dcc(&c, 13, 34, 30.0, 70.0, 2);
        for &s in &signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "got {s}");
        }
    }

    // ── RSI MA Cross ──────────────────────────────────────────────────────

    #[test]
    fn rsi_ma_cross_output_length() {
        let (_, _, c) = synth_data(80);
        let signals = rsi_ma_cross(&c, 14, 10, 30.0, 70.0);
        assert_eq!(signals.len(), 80);
    }

    #[test]
    fn rsi_ma_cross_valid_signals() {
        let (_, _, c) = synth_data(80);
        let signals = rsi_ma_cross(&c, 14, 10, 30.0, 70.0);
        for &s in &signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "got {s}");
        }
    }

    // ── WMA/IWMA Cross ────────────────────────────────────────────────────

    #[test]
    fn wma_iwma_cross_output_length() {
        let (_, _, c) = synth_data(50);
        let signals = wma_iwma_cross(&c, 10);
        assert_eq!(signals.len(), 50);
    }

    #[test]
    fn wma_iwma_cross_valid_signals() {
        let (_, _, c) = synth_data(100);
        let signals = wma_iwma_cross(&c, 10);
        for &s in &signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "got {s}");
        }
    }

    #[test]
    fn wma_iwma_cross_first_bar_zero() {
        let (_, _, c) = synth_data(50);
        let signals = wma_iwma_cross(&c, 10);
        assert_abs_diff_eq!(signals[0], 0.0, epsilon = 1e-9);
    }

    #[test]
    fn wma_iwma_cross_short_input() {
        let signals = wma_iwma_cross(&[100.0], 10);
        assert_eq!(signals.len(), 1);
        assert_abs_diff_eq!(signals[0], 0.0, epsilon = 1e-9);
    }

    // ── K's Collection ─────────────────────────────────────────────────────

    #[test]
    fn ks_collection_output_lengths() {
        let (h, l, c) = synth_data(250);
        let ks = calculate_ks_collection(&h, &l, &c);
        assert_eq!(ks.reversal_i.len(), 250);
        assert_eq!(ks.reversal_ii.len(), 250);
        assert_eq!(ks.atr_adjusted_rsi.len(), 250);
        assert_eq!(ks.rsi_squared.len(), 250);
        assert_eq!(ks.marsi_values.len(), 250);
        assert_eq!(ks.marsi_signals.len(), 250);
        assert_eq!(ks.fma_high.len(), 250);
        assert_eq!(ks.fma_mid.len(), 250);
        assert_eq!(ks.fma_low.len(), 250);
    }

    #[test]
    fn ks_collection_signals_valid() {
        let (h, l, c) = synth_data(250);
        let ks = calculate_ks_collection(&h, &l, &c);
        for &s in &ks.reversal_i {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "rev_i got {s}");
        }
        for &s in &ks.reversal_ii {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "rev_ii got {s}");
        }
        for &s in &ks.marsi_signals {
            assert!(s == 0.0 || s == 1.0 || s == -1.0, "marsi_sig got {s}");
        }
    }

    #[test]
    fn ks_collection_oscillators_bounded() {
        let (h, l, c) = synth_data(250);
        let ks = calculate_ks_collection(&h, &l, &c);
        for &v in &ks.atr_adjusted_rsi {
            assert!(v >= 0.0 && v <= 100.0, "atr_rsi out of range: {v}");
        }
        for &v in &ks.rsi_squared {
            assert!(v >= 0.0 && v <= 100.0, "rsi² out of range: {v}");
        }
    }

    // ── Composite Signal ──────────────────────────────────────────────────

    #[test]
    fn composite_signal_basic() {
        let (h, l, c) = synth_data(100);
        let v = vec![1000.0; 100];
        let result = build_composite_signal(&h, &l, &c, &v, 1.5, 0.3);
        assert!(result.signal == 1 || result.signal == -1 || result.signal == 0);
        assert!(result.confidence >= 0.0 && result.confidence <= 1.0);
        assert!(result.sma_score >= 0.0 && result.sma_score <= 1.0);
        assert!(result.volume_score >= 0.0 && result.volume_score <= 1.0);
        assert!(result.rvol > 0.0);
    }

    #[test]
    fn composite_signal_short_input() {
        let result = build_composite_signal(&[100.0], &[99.0], &[99.5], &[1000.0], 1.5, 0.3);
        assert_eq!(result.signal, 0);
        assert_abs_diff_eq!(result.confidence, 0.0, epsilon = 1e-9);
    }

    // ── Swarm Validation ──────────────────────────────────────────────────

    fn synth_ohlcv(n: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
        let mut opens = Vec::with_capacity(n);
        let mut highs = Vec::with_capacity(n);
        let mut lows = Vec::with_capacity(n);
        let mut closes = Vec::with_capacity(n);
        let volumes = vec![1000.0; n];
        for i in 0..n {
            let base = 100.0 + (i as f64 * 0.3).sin() * 10.0;
            opens.push(base - 0.5);
            highs.push(base + 3.0);
            lows.push(base - 3.0);
            closes.push(base + 0.5);
        }
        (opens, highs, lows, closes, volumes)
    }

    #[test]
    fn swarm_validate_returns_result() {
        let (o, h, l, c, _v) = synth_ohlcv(100);
        let result = swarm_validate(&o, &h, &l, &c, 100);
        // Should produce some signals (may be 0 if no patterns detected)
        assert!(result.total_signals >= 0);
        assert!(result.fully_swarmed <= result.total_signals);
    }

    #[test]
    fn swarm_validate_swarming_ratio_bounded() {
        let (o, h, l, c, _v) = synth_ohlcv(200);
        let result = swarm_validate(&o, &h, &l, &c, 200);
        for signal in &result.signals {
            assert!(signal.swarming_ratio >= 0.0 && signal.swarming_ratio <= 1.0,
                "swarming_ratio out of range: {}", signal.swarming_ratio);
            assert!(!signal.fired_on.is_empty());
            assert!(signal.direction == 1 || signal.direction == -1 || signal.direction == 0);
        }
    }

    #[test]
    fn swarm_validate_sorted_descending() {
        let (o, h, l, c, _v) = synth_ohlcv(150);
        let result = swarm_validate(&o, &h, &l, &c, 150);
        for w in result.signals.windows(2) {
            assert!(w[0].swarming_ratio >= w[1].swarming_ratio,
                "signals not sorted: {} < {}", w[0].swarming_ratio, w[1].swarming_ratio);
        }
    }
}
