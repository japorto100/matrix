// volume.rs — Volume-based indicators
//
// Migrated from lib.rs: vwap_series, obv_series, cmf_series
//
// kand-Blueprint pattern adopted:
//   batch fn()       — full series computation
//   fn _inc()        — incremental: prev_state + new_input -> new_value
//   fn _with_state() — batch that also returns final state for _inc() bootstrap
// kand new (future): AD, ADOSC, MFI

use crate::helper::typical_price;

// ── VWAP ───────────────────────────────────────────────────────────────────────

/// Session VWAP — cumulative(typical_price * vol) / cumulative(vol).
pub fn vwap_series(highs: &[f64], lows: &[f64], closes: &[f64], volumes: &[f64]) -> Vec<f64> {
    let n = closes.len();
    let mut out = Vec::with_capacity(n);
    let mut cum_tp_vol = 0.0_f64;
    let mut cum_vol = 0.0_f64;
    for i in 0..n {
        let tp = typical_price(highs[i], lows[i], closes[i]);
        cum_tp_vol += tp * volumes[i];
        cum_vol += volumes[i];
        out.push(if cum_vol < 1e-10 { closes[i] } else { cum_tp_vol / cum_vol });
    }
    out
}

/// VWAP with state — returns (series, cum_tp_vol, cum_vol) for `vwap_inc()`.
pub fn vwap_with_state(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    volumes: &[f64],
) -> (Vec<f64>, f64, f64) {
    let n = closes.len();
    let mut out = Vec::with_capacity(n);
    let mut cum_tp_vol = 0.0_f64;
    let mut cum_vol = 0.0_f64;
    for i in 0..n {
        let tp = typical_price(highs[i], lows[i], closes[i]);
        cum_tp_vol += tp * volumes[i];
        cum_vol += volumes[i];
        out.push(if cum_vol < 1e-10 { closes[i] } else { cum_tp_vol / cum_vol });
    }
    (out, cum_tp_vol, cum_vol)
}

/// Incremental VWAP update.
///
/// Adds one bar's typical_price * volume to the running sums.
/// Returns `(new_cum_tp_vol, new_cum_vol, vwap)`.
///
/// Bootstrap state from `vwap_with_state()`.
#[inline]
pub fn vwap_inc(
    high: f64,
    low: f64,
    close: f64,
    volume: f64,
    prev_cum_tp_vol: f64,
    prev_cum_vol: f64,
) -> (f64, f64, f64) {
    let tp = typical_price(high, low, close);
    let new_cum_tp_vol = prev_cum_tp_vol + tp * volume;
    let new_cum_vol = prev_cum_vol + volume;
    let vwap = if new_cum_vol < 1e-10 {
        close
    } else {
        new_cum_tp_vol / new_cum_vol
    };
    (new_cum_tp_vol, new_cum_vol, vwap)
}

// ── OBV ────────────────────────────────────────────────────────────────────────

/// On-Balance Volume — cumulative ±vol based on price direction.
pub fn obv_series(closes: &[f64], volumes: &[f64]) -> Vec<f64> {
    let n = closes.len();
    let mut out = Vec::with_capacity(n);
    let mut obv = 0.0_f64;
    out.push(obv);
    for i in 1..n {
        if closes[i] > closes[i - 1] {
            obv += volumes[i];
        } else if closes[i] < closes[i - 1] {
            obv -= volumes[i];
        }
        out.push(obv);
    }
    out
}

/// OBV with state — returns (series, last_obv) for `obv_inc()`.
pub fn obv_with_state(closes: &[f64], volumes: &[f64]) -> (Vec<f64>, f64) {
    let result = obv_series(closes, volumes);
    let last = *result.last().unwrap_or(&0.0);
    (result, last)
}

/// Incremental OBV update.
///
/// Formula:
/// - `curr_close > prev_close` → `prev_obv + volume`
/// - `curr_close < prev_close` → `prev_obv - volume`
/// - `curr_close == prev_close` → `prev_obv` (unchanged)
///
/// Bootstrap state from `obv_with_state()`.
#[inline]
pub fn obv_inc(curr_close: f64, prev_close: f64, volume: f64, prev_obv: f64) -> f64 {
    if curr_close > prev_close {
        prev_obv + volume
    } else if curr_close < prev_close {
        prev_obv - volume
    } else {
        prev_obv
    }
}

// ── CMF ────────────────────────────────────────────────────────────────────────

/// Close Location Value for a single bar.
///
/// `CLV = ((close - low) - (high - close)) / (high - low)`
/// Returns 0.0 if high == low (flat bar).
#[inline]
pub fn clv(high: f64, low: f64, close: f64) -> f64 {
    let hl = high - low;
    if hl < 1e-10 {
        0.0
    } else {
        ((close - low) - (high - close)) / hl
    }
}

/// Chaikin Money Flow — rolling(CLV*vol, period) / rolling(vol, period).
pub fn cmf_series(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    volumes: &[f64],
    period: usize,
) -> Vec<f64> {
    let n = closes.len();
    let mut clv_vol: Vec<f64> = Vec::with_capacity(n);
    for i in 0..n {
        clv_vol.push(clv(highs[i], lows[i], closes[i]) * volumes[i]);
    }
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        let start = (i + 1).saturating_sub(period);
        let vol_sum: f64 = volumes[start..=i].iter().sum();
        let cv_sum: f64 = clv_vol[start..=i].iter().sum();
        out.push(if vol_sum < 1e-10 { 0.0 } else { cv_sum / vol_sum });
    }
    out
}

/// CMF with state — returns (series, last clv_vol window, last vol window) for `cmf_inc()`.
///
/// The windows are the last `period` values of clv*vol and volume respectively.
pub fn cmf_with_state(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    volumes: &[f64],
    period: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let n = closes.len();
    let mut clv_vol_all: Vec<f64> = Vec::with_capacity(n);
    for i in 0..n {
        clv_vol_all.push(clv(highs[i], lows[i], closes[i]) * volumes[i]);
    }
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        let start = (i + 1).saturating_sub(period);
        let vol_sum: f64 = volumes[start..=i].iter().sum();
        let cv_sum: f64 = clv_vol_all[start..=i].iter().sum();
        out.push(if vol_sum < 1e-10 { 0.0 } else { cv_sum / vol_sum });
    }

    // Return the last `period` values as the window state
    let window_start = n.saturating_sub(period);
    let clv_vol_window = clv_vol_all[window_start..].to_vec();
    let vol_window = volumes[window_start..].to_vec();

    (out, clv_vol_window, vol_window)
}

/// Incremental CMF update.
///
/// Slides the rolling window by one: drops the oldest clv*vol and vol,
/// adds the new ones, then recomputes CMF = sum(clv*vol) / sum(vol).
///
/// Returns `(cmf, new_clv_vol_window, new_vol_window)`.
///
/// # Arguments
/// * `high`, `low`, `close`, `volume` — newest bar
/// * `clv_vol_window` — previous window of clv*vol values (length == period)
/// * `vol_window` — previous window of volume values (length == period)
pub fn cmf_inc(
    high: f64,
    low: f64,
    close: f64,
    volume: f64,
    clv_vol_window: &[f64],
    vol_window: &[f64],
) -> (f64, Vec<f64>, Vec<f64>) {
    let new_clv_vol = clv(high, low, close) * volume;

    // Slide window: drop oldest (index 0), append new
    let mut new_cv_win: Vec<f64> = Vec::with_capacity(clv_vol_window.len());
    let mut new_vol_win: Vec<f64> = Vec::with_capacity(vol_window.len());

    for v in &clv_vol_window[1..] {
        new_cv_win.push(*v);
    }
    new_cv_win.push(new_clv_vol);

    for v in &vol_window[1..] {
        new_vol_win.push(*v);
    }
    new_vol_win.push(volume);

    let cv_sum: f64 = new_cv_win.iter().sum();
    let vol_sum: f64 = new_vol_win.iter().sum();
    let cmf_val = if vol_sum < 1e-10 { 0.0 } else { cv_sum / vol_sum };

    (cmf_val, new_cv_win, new_vol_win)
}

// ── Volume Profile ────────────────────────────────────────────────────────────

/// Volume Profile result with Point of Control and Value Area.
#[derive(Debug, Clone)]
pub struct VolumeProfileResult {
    /// Price level with highest volume concentration.
    pub poc_price: f64,
    /// Value Area upper bound (contains `va_pct` of total volume).
    pub va_high: f64,
    /// Value Area lower bound.
    pub va_low: f64,
    /// Volume per price bin: `(bin_low, bin_high, volume)`.
    pub histogram: Vec<(f64, f64, f64)>,
}

/// Volume Profile with Point of Control (POC) and Value Area.
///
/// Distributes volume proportionally across `num_bins` price bins based on
/// each bar's H-L overlap with the bin. TradingView defaults: num_bins=24, va_pct=0.70.
///
/// Python ref: `volume.py::volume_profile()`.
pub fn volume_profile(
    highs: &[f64],
    lows: &[f64],
    volumes: &[f64],
    num_bins: usize,
    va_pct: f64,
) -> VolumeProfileResult {
    let n = highs.len();
    let empty = VolumeProfileResult {
        poc_price: 0.0,
        va_high: 0.0,
        va_low: 0.0,
        histogram: Vec::new(),
    };

    if n == 0 || num_bins == 0 {
        return empty;
    }

    let price_min = lows.iter().cloned().fold(f64::INFINITY, f64::min);
    let price_max = highs.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let price_range = price_max - price_min;

    if price_range <= 0.0 {
        return VolumeProfileResult {
            poc_price: price_min,
            va_high: price_min,
            va_low: price_min,
            histogram: vec![(price_min, price_min, volumes.iter().sum())],
        };
    }

    let bin_size = price_range / num_bins as f64;
    let mut hist = vec![0.0_f64; num_bins];

    // Distribute volume proportionally by H-L overlap with each bin
    for i in 0..n {
        let bar_range = highs[i] - lows[i];
        for b in 0..num_bins {
            let bin_low = price_min + b as f64 * bin_size;
            let bin_high = bin_low + bin_size;
            let overlap = (highs[i].min(bin_high) - lows[i].max(bin_low)).max(0.0);
            let vol_fraction = if bar_range > 0.0 {
                overlap / bar_range
            } else if bin_low <= lows[i] && lows[i] < bin_high {
                1.0
            } else {
                0.0
            };
            hist[b] += volumes[i] * vol_fraction;
        }
    }

    // POC = bin with max volume
    let poc_bin = hist
        .iter()
        .enumerate()
        .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
        .map(|(i, _)| i)
        .unwrap_or(0);
    let poc_price = price_min + (poc_bin as f64 + 0.5) * bin_size;

    // Value Area — expand from POC until va_pct of total volume
    let total_vol: f64 = hist.iter().sum();
    let target_vol = total_vol * va_pct;
    let mut cumulative = hist[poc_bin];
    let mut lo_idx = poc_bin;
    let mut hi_idx = poc_bin;

    while cumulative < target_vol && (lo_idx > 0 || hi_idx < num_bins - 1) {
        let vol_below = if lo_idx > 0 { hist[lo_idx - 1] } else { 0.0 };
        let vol_above = if hi_idx < num_bins - 1 {
            hist[hi_idx + 1]
        } else {
            0.0
        };
        if vol_below >= vol_above && lo_idx > 0 {
            lo_idx -= 1;
            cumulative += hist[lo_idx];
        } else if hi_idx < num_bins - 1 {
            hi_idx += 1;
            cumulative += hist[hi_idx];
        } else if lo_idx > 0 {
            lo_idx -= 1;
            cumulative += hist[lo_idx];
        } else {
            break;
        }
    }

    let va_low = price_min + lo_idx as f64 * bin_size;
    let va_high = price_min + (hi_idx + 1) as f64 * bin_size;

    let histogram = (0..num_bins)
        .map(|b| {
            let bl = price_min + b as f64 * bin_size;
            let bh = bl + bin_size;
            (bl, bh, hist[b])
        })
        .collect();

    VolumeProfileResult {
        poc_price,
        va_high,
        va_low,
        histogram,
    }
}

// ── A/D Line ─────────────────────────────────────────────────────────────────

/// Accumulation/Distribution Line — cumulative money flow volume.
///
/// Money Flow Multiplier: `((Close - Low) - (High - Close)) / (High - Low)`
/// Money Flow Volume: `MFM * Volume`
/// AD[i] = AD[i-1] + MFV
///
/// Returns 0.0 for MFM when High == Low (flat bar).
pub fn ad_line(highs: &[f64], lows: &[f64], closes: &[f64], volumes: &[f64]) -> Vec<f64> {
    let n = closes.len();
    let mut out = Vec::with_capacity(n);
    let mut ad = 0.0_f64;
    for i in 0..n {
        let hl = highs[i] - lows[i];
        let mfm = if hl == 0.0 {
            0.0
        } else {
            ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
        };
        ad += mfm * volumes[i];
        out.push(ad);
    }
    out
}

/// Incremental A/D update.
///
/// Returns the new A/D value given the previous A/D and the latest bar.
#[inline]
pub fn ad_line_inc(prev_ad: f64, high: f64, low: f64, close: f64, volume: f64) -> f64 {
    let hl = high - low;
    let mfm = if hl == 0.0 {
        0.0
    } else {
        ((close - low) - (high - close)) / hl
    };
    prev_ad + mfm * volume
}

// ── A/D Oscillator ───────────────────────────────────────────────────────────

/// A/D Oscillator — `EMA(fast, AD) - EMA(slow, AD)`.
///
/// Computes the full A/D line, then applies fast and slow EMAs and returns
/// their difference. Output length equals the input length; early values
/// ramp up as the EMA seeds.
pub fn ad_osc(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    volumes: &[f64],
    fast_period: usize,
    slow_period: usize,
) -> Vec<f64> {
    let ad = ad_line(highs, lows, closes, volumes);
    let fast_ema = super::trend::ema(&ad, fast_period);
    let slow_ema = super::trend::ema(&ad, slow_period);
    let n = ad.len();
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        out.push(fast_ema[i] - slow_ema[i]);
    }
    out
}

// ── MFI ──────────────────────────────────────────────────────────────────────

/// Money Flow Index — RSI-style oscillator weighted by volume.
///
/// Typical Price = (H+L+C)/3
/// Raw Money Flow = TP * Volume
/// Positive MF = sum of RawMF where TP > prev_TP over period
/// Negative MF = sum of RawMF where TP <= prev_TP over period
/// MFI = 100 - 100/(1 + PosMF/NegMF)
///
/// Returns a Vec of length `n`. Values before index `period` are `f64::NAN`.
pub fn mfi(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    volumes: &[f64],
    period: usize,
) -> Vec<f64> {
    let n = closes.len();
    let mut out = vec![f64::NAN; n];

    if n == 0 || period < 2 || n <= period {
        return out;
    }

    // Compute typical prices and raw money flows
    let mut tp = Vec::with_capacity(n);
    let mut raw_mf = Vec::with_capacity(n);
    for i in 0..n {
        let t = typical_price(highs[i], lows[i], closes[i]);
        tp.push(t);
        raw_mf.push(t * volumes[i]);
    }

    // Calculate MFI for each valid position
    for i in period..n {
        let mut pos_flow = 0.0_f64;
        let mut neg_flow = 0.0_f64;

        for j in (i - period + 1)..=i {
            if tp[j] > tp[j - 1] {
                pos_flow += raw_mf[j];
            } else {
                neg_flow += raw_mf[j];
            }
        }

        let total = pos_flow + neg_flow;
        out[i] = if total < 1e-10 {
            0.0
        } else {
            100.0 * (pos_flow / total)
        };
    }

    out
}

// ── BOP ──────────────────────────────────────────────────────────────────────

/// Balance of Power: `(Close - Open) / (High - Low)`.
///
/// Returns 0.0 when High == Low (flat bar).
pub fn bop(opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64]) -> Vec<f64> {
    let n = closes.len();
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        let hl = highs[i] - lows[i];
        out.push(if hl == 0.0 {
            0.0
        } else {
            (closes[i] - opens[i]) / hl
        });
    }
    out
}

/// Incremental BOP for a single bar.
#[inline]
pub fn bop_inc(open: f64, high: f64, low: f64, close: f64) -> f64 {
    let hl = high - low;
    if hl == 0.0 {
        0.0
    } else {
        (close - open) / hl
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    // ── Helper: generate synthetic OHLCV ────────────────────────────────

    fn synthetic_ohlcv(n: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
        let mut highs = Vec::with_capacity(n);
        let mut lows = Vec::with_capacity(n);
        let mut closes = Vec::with_capacity(n);
        let mut volumes = Vec::with_capacity(n);
        for i in 0..n {
            let base = 100.0 + (i as f64 * 0.3).sin() * 10.0;
            highs.push(base + 3.0);
            lows.push(base - 3.0);
            closes.push(base + 0.5);
            volumes.push(1000.0 + (i as f64 * 0.7).cos() * 500.0);
        }
        (highs, lows, closes, volumes)
    }

    // ── VWAP ────────────────────────────────────────────────────────────

    #[test]
    fn vwap_basic_length() {
        let (h, l, c, v) = synthetic_ohlcv(50);
        let result = vwap_series(&h, &l, &c, &v);
        assert_eq!(result.len(), 50);
        // All VWAP values should be positive for positive prices
        for val in &result {
            assert!(*val > 0.0);
        }
    }

    #[test]
    fn vwap_inc_matches_batch() {
        let n = 50;
        let (h, l, c, v) = synthetic_ohlcv(n);

        let (batch, cum_tp_vol, cum_vol) = vwap_with_state(&h, &l, &c, &v);
        assert_eq!(batch.len(), n);

        // Extend by one bar
        let new_h = 115.0;
        let new_l = 109.0;
        let new_c = 112.0;
        let new_v = 1500.0;
        let (inc_cum_tp_vol, inc_cum_vol, inc_vwap) =
            vwap_inc(new_h, new_l, new_c, new_v, cum_tp_vol, cum_vol);

        // Verify against full batch with extended series
        let mut ext_h = h.clone();
        let mut ext_l = l.clone();
        let mut ext_c = c.clone();
        let mut ext_v = v.clone();
        ext_h.push(new_h);
        ext_l.push(new_l);
        ext_c.push(new_c);
        ext_v.push(new_v);
        let (ext_batch, ext_cum_tp_vol, ext_cum_vol) =
            vwap_with_state(&ext_h, &ext_l, &ext_c, &ext_v);

        assert_abs_diff_eq!(inc_vwap, *ext_batch.last().unwrap(), epsilon = 1e-9);
        assert_abs_diff_eq!(inc_cum_tp_vol, ext_cum_tp_vol, epsilon = 1e-6);
        assert_abs_diff_eq!(inc_cum_vol, ext_cum_vol, epsilon = 1e-6);
    }

    #[test]
    fn vwap_zero_volume() {
        // Zero volume → VWAP falls back to close
        let h = vec![110.0];
        let l = vec![90.0];
        let c = vec![100.0];
        let v = vec![0.0];
        let result = vwap_series(&h, &l, &c, &v);
        assert_abs_diff_eq!(result[0], 100.0, epsilon = 1e-9);
    }

    // ── OBV ─────────────────────────────────────────────────────────────

    #[test]
    fn obv_basic() {
        let closes = vec![100.0, 105.0, 103.0, 108.0, 108.0];
        let volumes = vec![1000.0, 2000.0, 1500.0, 3000.0, 1000.0];
        let result = obv_series(&closes, &volumes);
        assert_eq!(result.len(), 5);
        assert_abs_diff_eq!(result[0], 0.0, epsilon = 1e-9);
        // 105 > 100 → +2000
        assert_abs_diff_eq!(result[1], 2000.0, epsilon = 1e-9);
        // 103 < 105 → -1500
        assert_abs_diff_eq!(result[2], 500.0, epsilon = 1e-9);
        // 108 > 103 → +3000
        assert_abs_diff_eq!(result[3], 3500.0, epsilon = 1e-9);
        // 108 == 108 → unchanged
        assert_abs_diff_eq!(result[4], 3500.0, epsilon = 1e-9);
    }

    #[test]
    fn obv_inc_matches_batch() {
        let n = 50;
        let (_, _, closes, volumes) = synthetic_ohlcv(n);

        let (batch, last_obv) = obv_with_state(&closes, &volumes);
        assert_eq!(batch.len(), n);

        // Extend by one bar (price goes up)
        let new_close = closes[n - 1] + 5.0;
        let new_vol = 2000.0;
        let prev_close = closes[n - 1];
        let inc_obv = obv_inc(new_close, prev_close, new_vol, last_obv);

        // Verify against full batch with extended series
        let mut ext_c = closes.clone();
        let mut ext_v = volumes.clone();
        ext_c.push(new_close);
        ext_v.push(new_vol);
        let (ext_batch, _ext_last) = obv_with_state(&ext_c, &ext_v);

        assert_abs_diff_eq!(inc_obv, *ext_batch.last().unwrap(), epsilon = 1e-9);
    }

    #[test]
    fn obv_inc_directions() {
        // Up: prev_obv + vol
        assert_abs_diff_eq!(obv_inc(105.0, 100.0, 1000.0, 5000.0), 6000.0, epsilon = 1e-9);
        // Down: prev_obv - vol
        assert_abs_diff_eq!(obv_inc(95.0, 100.0, 1000.0, 5000.0), 4000.0, epsilon = 1e-9);
        // Flat: prev_obv unchanged
        assert_abs_diff_eq!(obv_inc(100.0, 100.0, 1000.0, 5000.0), 5000.0, epsilon = 1e-9);
    }

    // ── CLV ─────────────────────────────────────────────────────────────

    #[test]
    fn clv_known_values() {
        // Close at high → CLV = 1.0
        assert_abs_diff_eq!(clv(110.0, 90.0, 110.0), 1.0, epsilon = 1e-9);
        // Close at low → CLV = -1.0
        assert_abs_diff_eq!(clv(110.0, 90.0, 90.0), -1.0, epsilon = 1e-9);
        // Close at midpoint → CLV = 0.0
        assert_abs_diff_eq!(clv(110.0, 90.0, 100.0), 0.0, epsilon = 1e-9);
        // Flat bar → CLV = 0.0
        assert_abs_diff_eq!(clv(100.0, 100.0, 100.0), 0.0, epsilon = 1e-9);
    }

    // ── CMF ─────────────────────────────────────────────────────────────

    #[test]
    fn cmf_basic_length() {
        let (h, l, c, v) = synthetic_ohlcv(50);
        let result = cmf_series(&h, &l, &c, &v, 20);
        assert_eq!(result.len(), 50);
        // CMF should be bounded (roughly -1..1 for normal data)
        for val in &result {
            assert!(*val >= -5.0 && *val <= 5.0);
        }
    }

    #[test]
    fn cmf_inc_matches_batch() {
        let n = 50;
        let period = 20;
        let (h, l, c, v) = synthetic_ohlcv(n);

        let (batch, clv_vol_win, vol_win) = cmf_with_state(&h, &l, &c, &v, period);
        assert_eq!(batch.len(), n);
        assert_eq!(clv_vol_win.len(), period);
        assert_eq!(vol_win.len(), period);

        // Extend by one bar
        let new_h = 115.0;
        let new_l = 109.0;
        let new_c = 112.0;
        let new_v = 1500.0;
        let (inc_cmf, new_cv_win, new_vol_win) =
            cmf_inc(new_h, new_l, new_c, new_v, &clv_vol_win, &vol_win);

        // Verify against full batch with extended series
        let mut ext_h = h.clone();
        let mut ext_l = l.clone();
        let mut ext_c = c.clone();
        let mut ext_v = v.clone();
        ext_h.push(new_h);
        ext_l.push(new_l);
        ext_c.push(new_c);
        ext_v.push(new_v);
        let (ext_batch, ext_cv_win, ext_vol_win) =
            cmf_with_state(&ext_h, &ext_l, &ext_c, &ext_v, period);

        assert_abs_diff_eq!(inc_cmf, *ext_batch.last().unwrap(), epsilon = 1e-9);

        // Verify window state carries forward correctly
        assert_eq!(new_cv_win.len(), ext_cv_win.len());
        assert_eq!(new_vol_win.len(), ext_vol_win.len());
        for j in 0..new_cv_win.len() {
            assert_abs_diff_eq!(new_cv_win[j], ext_cv_win[j], epsilon = 1e-9);
            assert_abs_diff_eq!(new_vol_win[j], ext_vol_win[j], epsilon = 1e-9);
        }
    }

    // ── Volume Profile ─────────────────────────────────────────────────

    #[test]
    fn volume_profile_basic() {
        let highs = vec![110.0, 112.0, 108.0, 115.0, 111.0];
        let lows = vec![90.0, 95.0, 85.0, 100.0, 95.0];
        let vols = vec![1000.0, 1500.0, 800.0, 2000.0, 1200.0];
        let result = volume_profile(&highs, &lows, &vols, 10, 0.70);

        assert_eq!(result.histogram.len(), 10);
        assert!(result.poc_price > 85.0 && result.poc_price < 115.0);
        assert!(result.va_low <= result.poc_price);
        assert!(result.va_high >= result.poc_price);
    }

    #[test]
    fn volume_profile_empty() {
        let result = volume_profile(&[], &[], &[], 10, 0.70);
        assert_eq!(result.histogram.len(), 0);
        assert_abs_diff_eq!(result.poc_price, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn volume_profile_constant_price() {
        let highs = vec![100.0; 10];
        let lows = vec![100.0; 10];
        let vols = vec![500.0; 10];
        let result = volume_profile(&highs, &lows, &vols, 5, 0.70);
        assert_abs_diff_eq!(result.poc_price, 100.0, epsilon = 1e-9);
    }

    #[test]
    fn volume_profile_histogram_sums_to_total() {
        let (h, l, _, v) = synthetic_ohlcv(50);
        let result = volume_profile(&h, &l, &v, 24, 0.70);
        let hist_sum: f64 = result.histogram.iter().map(|(_, _, vol)| vol).sum();
        let total_vol: f64 = v.iter().sum();
        // Volume is redistributed proportionally — should sum to total
        assert_abs_diff_eq!(hist_sum, total_vol, epsilon = 0.1);
    }

    #[test]
    fn volume_profile_va_contains_poc() {
        let (h, l, _, v) = synthetic_ohlcv(100);
        let result = volume_profile(&h, &l, &v, 24, 0.70);
        assert!(result.va_low <= result.poc_price, "VA low should be <= POC");
        assert!(result.va_high >= result.poc_price, "VA high should be >= POC");
    }

    #[test]
    fn cmf_inc_multi_step() {
        // Run inc 5 times sequentially and verify each step
        let n = 50;
        let period = 20;
        let (h, l, c, v) = synthetic_ohlcv(n + 5);

        let (batch_init, mut cv_win, mut vol_win) =
            cmf_with_state(&h[..n], &l[..n], &c[..n], &v[..n], period);
        assert_eq!(batch_init.len(), n);

        for step in 0..5 {
            let idx = n + step;
            let (inc_cmf, new_cv_win, new_vol_win) =
                cmf_inc(h[idx], l[idx], c[idx], v[idx], &cv_win, &vol_win);

            // Compare against batch up to idx+1
            let (full_batch, _, _) =
                cmf_with_state(&h[..=idx], &l[..=idx], &c[..=idx], &v[..=idx], period);
            assert_abs_diff_eq!(
                inc_cmf,
                *full_batch.last().unwrap(),
                epsilon = 1e-9
            );

            cv_win = new_cv_win;
            vol_win = new_vol_win;
        }
    }

    // ── A/D Line ─────────────────────────────────────────────────────────

    #[test]
    fn ad_line_basic() {
        let highs = vec![10.0, 12.0, 15.0];
        let lows = vec![8.0, 9.0, 11.0];
        let closes = vec![9.0, 11.0, 13.0];
        let volumes = vec![100.0, 150.0, 200.0];
        let result = ad_line(&highs, &lows, &closes, &volumes);
        assert_eq!(result.len(), 3);
        // Bar 0: MFM = ((9-8)-(10-9))/(10-8) = 0/2 = 0.0, AD = 0
        assert_abs_diff_eq!(result[0], 0.0, epsilon = 1e-9);
        // Bar 1: MFM = ((11-9)-(12-11))/(12-9) = 1/3, MFV = 1/3*150 = 50, AD = 50
        assert_abs_diff_eq!(result[1], 50.0, epsilon = 1e-9);
        // Bar 2: MFM = ((13-11)-(15-13))/(15-11) = 0/4 = 0.0, AD = 50
        assert_abs_diff_eq!(result[2], 50.0, epsilon = 1e-9);
    }

    #[test]
    fn ad_line_flat_bar() {
        // High == Low → MFM = 0
        let highs = vec![100.0];
        let lows = vec![100.0];
        let closes = vec![100.0];
        let volumes = vec![5000.0];
        let result = ad_line(&highs, &lows, &closes, &volumes);
        assert_abs_diff_eq!(result[0], 0.0, epsilon = 1e-9);
    }

    #[test]
    fn ad_line_inc_matches_batch() {
        let n = 50;
        let (h, l, c, v) = synthetic_ohlcv(n);
        let batch = ad_line(&h, &l, &c, &v);
        let prev_ad = batch[n - 1];

        let new_h = 115.0;
        let new_l = 109.0;
        let new_c = 112.0;
        let new_v = 1500.0;
        let inc_ad = ad_line_inc(prev_ad, new_h, new_l, new_c, new_v);

        let mut ext_h = h.clone();
        let mut ext_l = l.clone();
        let mut ext_c = c.clone();
        let mut ext_v = v.clone();
        ext_h.push(new_h);
        ext_l.push(new_l);
        ext_c.push(new_c);
        ext_v.push(new_v);
        let ext_batch = ad_line(&ext_h, &ext_l, &ext_c, &ext_v);

        assert_abs_diff_eq!(inc_ad, *ext_batch.last().unwrap(), epsilon = 1e-9);
    }

    // ── A/D Oscillator ──────────────────────────────────────────────────

    #[test]
    fn ad_osc_basic_length() {
        let (h, l, c, v) = synthetic_ohlcv(50);
        let result = ad_osc(&h, &l, &c, &v, 3, 10);
        assert_eq!(result.len(), 50);
    }

    #[test]
    fn ad_osc_equals_ema_diff() {
        let (h, l, c, v) = synthetic_ohlcv(30);
        let ad = ad_line(&h, &l, &c, &v);
        let fast = super::super::trend::ema(&ad, 3);
        let slow = super::super::trend::ema(&ad, 10);
        let osc = ad_osc(&h, &l, &c, &v, 3, 10);
        for i in 0..30 {
            if osc[i].is_nan() || fast[i].is_nan() || slow[i].is_nan() {
                continue;
            }
            assert_abs_diff_eq!(osc[i], fast[i] - slow[i], epsilon = 1e-9);
        }
    }

    // ── MFI ─────────────────────────────────────────────────────────────

    #[test]
    fn mfi_basic_length() {
        let (h, l, c, v) = synthetic_ohlcv(50);
        let result = mfi(&h, &l, &c, &v, 14);
        assert_eq!(result.len(), 50);
        // First `period` values should be NaN
        for i in 0..14 {
            assert!(result[i].is_nan(), "MFI[{}] should be NaN", i);
        }
        // Valid values should be in [0, 100]
        for i in 14..50 {
            assert!(
                result[i] >= 0.0 && result[i] <= 100.0,
                "MFI[{}] = {} out of range",
                i,
                result[i]
            );
        }
    }

    #[test]
    fn mfi_known_values() {
        // All-up scenario: every TP rises → all positive flow → MFI should be 100
        let highs = vec![10.0, 11.0, 12.0, 13.0, 14.0];
        let lows = vec![8.0, 9.0, 10.0, 11.0, 12.0];
        let closes = vec![9.0, 10.0, 11.0, 12.0, 13.0];
        let volumes = vec![100.0, 100.0, 100.0, 100.0, 100.0];
        let result = mfi(&highs, &lows, &closes, &volumes, 3);
        // MFI at index 3 and 4 should be 100 (all positive flow)
        assert_abs_diff_eq!(result[3], 100.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[4], 100.0, epsilon = 1e-9);
    }

    #[test]
    fn mfi_insufficient_data() {
        let h = vec![10.0, 11.0];
        let l = vec![8.0, 9.0];
        let c = vec![9.0, 10.0];
        let v = vec![100.0, 100.0];
        let result = mfi(&h, &l, &c, &v, 14);
        // All NaN when n <= period
        for val in &result {
            assert!(val.is_nan());
        }
    }

    // ── BOP ─────────────────────────────────────────────────────────────

    #[test]
    fn bop_basic() {
        let opens = vec![10.0, 11.0, 12.0];
        let highs = vec![12.0, 13.0, 14.0];
        let lows = vec![8.0, 9.0, 10.0];
        let closes = vec![11.0, 12.0, 13.0];
        let result = bop(&opens, &highs, &lows, &closes);
        assert_eq!(result.len(), 3);
        // (11-10)/(12-8) = 1/4 = 0.25
        assert_abs_diff_eq!(result[0], 0.25, epsilon = 1e-9);
        // (12-11)/(13-9) = 1/4 = 0.25
        assert_abs_diff_eq!(result[1], 0.25, epsilon = 1e-9);
        // (13-12)/(14-10) = 1/4 = 0.25
        assert_abs_diff_eq!(result[2], 0.25, epsilon = 1e-9);
    }

    #[test]
    fn bop_flat_bar() {
        // High == Low → 0.0
        assert_abs_diff_eq!(bop_inc(100.0, 100.0, 100.0, 100.0), 0.0, epsilon = 1e-9);
    }

    #[test]
    fn bop_inc_matches_batch() {
        let opens = vec![10.0, 11.0, 12.0, 13.0, 14.0];
        let highs = vec![12.0, 13.0, 14.0, 15.0, 16.0];
        let lows = vec![8.0, 9.0, 10.0, 11.0, 12.0];
        let closes = vec![11.0, 12.0, 13.0, 14.0, 15.0];
        let batch = bop(&opens, &highs, &lows, &closes);
        for i in 0..5 {
            let inc = bop_inc(opens[i], highs[i], lows[i], closes[i]);
            assert_abs_diff_eq!(inc, batch[i], epsilon = 1e-9);
        }
    }

    #[test]
    fn bop_bearish_bar() {
        // Close below open → negative BOP
        // (90 - 100) / (110 - 80) = -10/30 = -0.333...
        assert_abs_diff_eq!(bop_inc(100.0, 110.0, 80.0, 90.0), -10.0 / 30.0, epsilon = 1e-9);
    }
}
