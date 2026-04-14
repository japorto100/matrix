// transforms.rs — OHLC transformations (non-indicator, non-pattern)
//
// WASM CANDIDATE: These transforms modify raw candle data for visual rendering.
// Running them client-side (WASM) saves server CPU — users' browsers do the work.
//
// kand-Blueprint pattern adopted:
//   batch fn()       — full series computation
//   fn _inc()        — incremental: prev_state + new_input -> new_value
//   fn _with_state() — batch + final state for _inc() bootstrap
//
// Functions: heikin_ashi, heikin_ashi_inc, heikin_ashi_with_state
// Ported: volume_candles, k_candles, carsi_candles (from patterns.py apply_chart_transform)
//
// Additional WASM candidates across modules (run client-side to save server CPU):
//   - patterns::cdl_* — single-bar pattern detection, no server state needed
//   - portfolio::returns — trivial price→returns transform
//   - stats::rolling_max/min — chart rendering (support/resistance lines)
//   - portfolio::portfolio_drawdown_series — equity curve overlay rendering
//
// See also: WASM candidate audit in rust_kand_evaluation_delta.md

// ── Heikin-Ashi ─────────────────────────────────────────────────────────────

/// Heikin-Ashi OHLC transform — smoothed candlesticks for trend clarity.
///
/// Returns `(ha_open, ha_high, ha_low, ha_close)` — each Vec<f64> with length = input length.
///
/// Formula:
/// ```text
/// HA_Close = (O + H + L + C) / 4
/// HA_Open  = (prev_HA_Open + prev_HA_Close) / 2    [first bar: (O + C) / 2]
/// HA_High  = max(H, HA_Open, HA_Close)
/// HA_Low   = min(L, HA_Open, HA_Close)
/// ```
pub fn heikin_ashi(
    opens: &[f64],
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let n = opens.len();
    if n == 0 {
        return (vec![], vec![], vec![], vec![]);
    }

    let mut ha_o = Vec::with_capacity(n);
    let mut ha_h = Vec::with_capacity(n);
    let mut ha_l = Vec::with_capacity(n);
    let mut ha_c = Vec::with_capacity(n);

    // First bar
    let c0 = (opens[0] + highs[0] + lows[0] + closes[0]) / 4.0;
    let o0 = (opens[0] + closes[0]) / 2.0;
    ha_o.push(o0);
    ha_h.push(highs[0]);
    ha_l.push(lows[0]);
    ha_c.push(c0);

    // Subsequent bars
    for i in 1..n {
        let (o, h, l, c) = heikin_ashi_inc(
            opens[i], highs[i], lows[i], closes[i],
            ha_o[i - 1], ha_c[i - 1],
        );
        ha_o.push(o);
        ha_h.push(h);
        ha_l.push(l);
        ha_c.push(c);
    }

    (ha_o, ha_h, ha_l, ha_c)
}

/// Heikin-Ashi with state — returns (ha_open, ha_high, ha_low, ha_close,
/// last_ha_open, last_ha_close) for bootstrapping `heikin_ashi_inc()`.
pub fn heikin_ashi_with_state(
    opens: &[f64],
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>, f64, f64) {
    let (ha_o, ha_h, ha_l, ha_c) = heikin_ashi(opens, highs, lows, closes);
    let last_o = ha_o.last().copied().unwrap_or(0.0);
    let last_c = ha_c.last().copied().unwrap_or(0.0);
    (ha_o, ha_h, ha_l, ha_c, last_o, last_c)
}

/// Incremental Heikin-Ashi — one new bar from current OHLC + previous HA state.
///
/// Returns `(ha_open, ha_high, ha_low, ha_close)`.
///
/// Bootstrap state from `heikin_ashi_with_state()`.
#[inline]
pub fn heikin_ashi_inc(
    open: f64,
    high: f64,
    low: f64,
    close: f64,
    prev_ha_open: f64,
    prev_ha_close: f64,
) -> (f64, f64, f64, f64) {
    let ha_close = (open + high + low + close) / 4.0;
    let ha_open = (prev_ha_open + prev_ha_close) / 2.0;
    let ha_high = high.max(ha_open).max(ha_close);
    let ha_low = low.min(ha_open).min(ha_close);
    (ha_open, ha_high, ha_low, ha_close)
}

// ── Price Transforms ──────────────────────────────────────────────────────────
//
// Single-bar OHLC → derived price. Used by VWAP, CCI, MFI, MA variants.
// All are WASM candidates (trivial, no state).

/// Typical Price = (High + Low + Close) / 3.
///
/// Re-export from helper — canonical source for all modules.
#[inline]
pub fn typical_price(high: f64, low: f64, close: f64) -> f64 {
    crate::helper::typical_price(high, low, close)
}

/// Median Price = (High + Low) / 2.
///
/// Used by: median-based indicators, Ichimoku midpoint.
#[inline]
pub fn median_price(high: f64, low: f64) -> f64 {
    (high + low) / 2.0
}

/// Weighted Close Price = (High + Low + 2 * Close) / 4.
///
/// Gives extra weight to the close. Used by some MA and volatility variants.
#[inline]
pub fn weighted_close(high: f64, low: f64, close: f64) -> f64 {
    (high + low + 2.0 * close) / 4.0
}

/// Batch typical price series from OHLC arrays.
pub fn typical_price_series(
    highs: &[f64], lows: &[f64], closes: &[f64],
) -> Vec<f64> {
    let n = highs.len();
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        out.push(typical_price(highs[i], lows[i], closes[i]));
    }
    out
}

/// Batch median price series.
pub fn median_price_series(highs: &[f64], lows: &[f64]) -> Vec<f64> {
    let n = highs.len();
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        out.push(median_price(highs[i], lows[i]));
    }
    out
}

/// Batch weighted close series.
pub fn weighted_close_series(
    highs: &[f64], lows: &[f64], closes: &[f64],
) -> Vec<f64> {
    let n = highs.len();
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        out.push(weighted_close(highs[i], lows[i], closes[i]));
    }
    out
}

// ── Chart Transforms (Kaabar Ch.4) ──────────────────────────────────────────

/// Volume Candles — Kaabar Ch.4 tier classification.
///
/// Classifies each bar's volume into tiers 1–4 based on ratio to rolling
/// average volume (simple mean of the full series).
///
/// ```text
/// ratio = volume[i] / avg_volume
/// tier 4: ratio >= 2.00   (extreme)
/// tier 3: ratio >= 1.25   (high)
/// tier 2: ratio >= 0.75   (normal)
/// tier 1: ratio <  0.75   (low)
/// ```
pub fn volume_candles(volumes: &[f64]) -> Vec<u8> {
    let n = volumes.len();
    if n == 0 {
        return vec![];
    }
    let avg = volumes.iter().sum::<f64>() / n as f64;
    if avg == 0.0 {
        return vec![1u8; n];
    }
    volumes
        .iter()
        .map(|&v| {
            let ratio = v / avg;
            if ratio >= 2.0 {
                4
            } else if ratio >= 1.25 {
                3
            } else if ratio >= 0.75 {
                2
            } else {
                1
            }
        })
        .collect()
}

/// K's Candles (CCS) — Kaabar Ch.4.
///
/// Applies EMA(5) independently to each OHLC column, then derives:
/// - high = max(ema_o, ema_h, ema_l, ema_c)
/// - low  = min(ema_o, ema_h, ema_l, ema_c)
///
/// Returns `(k_open, k_high, k_low, k_close)`.
pub fn k_candles(
    opens: &[f64],
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let n = opens.len();
    if n == 0 {
        return (vec![], vec![], vec![], vec![]);
    }

    let ema_o = super::trend::ema(opens, 5);
    let ema_h = super::trend::ema(highs, 5);
    let ema_l = super::trend::ema(lows, 5);
    let ema_c = super::trend::ema(closes, 5);

    let mut k_o = Vec::with_capacity(n);
    let mut k_h = Vec::with_capacity(n);
    let mut k_l = Vec::with_capacity(n);
    let mut k_c = Vec::with_capacity(n);

    for i in 0..n {
        let o = ema_o[i];
        let h = ema_h[i];
        let l = ema_l[i];
        let c = ema_c[i];

        k_o.push(o);
        k_c.push(c);
        k_h.push(o.max(h).max(l).max(c));
        k_l.push(o.min(h).min(l).min(c));
    }

    (k_o, k_h, k_l, k_c)
}

/// CARSI Candles — Kaabar Ch.4.
///
/// Applies RSI(14) independently to each OHLC column, then derives:
/// - open  = rsi_open
/// - close = rsi_close
/// - high  = max(rsi_o, rsi_h, rsi_l, rsi_c)
/// - low   = min(rsi_o, rsi_h, rsi_l, rsi_c)
///
/// Returns `(carsi_open, carsi_high, carsi_low, carsi_close)`.
pub fn carsi_candles(
    opens: &[f64],
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let n = opens.len();
    if n == 0 {
        return (vec![], vec![], vec![], vec![]);
    }

    let rsi_o = super::oscillators::rsi(opens, 14);
    let rsi_h = super::oscillators::rsi(highs, 14);
    let rsi_l = super::oscillators::rsi(lows, 14);
    let rsi_c = super::oscillators::rsi(closes, 14);

    let mut c_o = Vec::with_capacity(n);
    let mut c_h = Vec::with_capacity(n);
    let mut c_l = Vec::with_capacity(n);
    let mut c_c = Vec::with_capacity(n);

    for i in 0..n {
        let ro = rsi_o[i];
        let rh = rsi_h[i];
        let rl = rsi_l[i];
        let rc = rsi_c[i];

        c_o.push(ro);
        c_c.push(rc);
        c_h.push(ro.max(rh).max(rl).max(rc));
        c_l.push(ro.min(rh).min(rl).min(rc));
    }

    (c_o, c_h, c_l, c_c)
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    fn gen_ohlc(n: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
        let mut opens = Vec::with_capacity(n);
        let mut highs = Vec::with_capacity(n);
        let mut lows = Vec::with_capacity(n);
        let mut closes = Vec::with_capacity(n);
        for i in 0..n {
            let base = 100.0 + (i as f64 * 0.3).sin() * 8.0;
            opens.push(base);
            highs.push(base + 3.0 + (i as f64 * 0.7).sin().abs());
            lows.push(base - 3.0 - (i as f64 * 0.5).sin().abs());
            closes.push(base + (i as f64 * 0.4).sin() * 2.0);
        }
        (opens, highs, lows, closes)
    }

    #[test]
    fn heikin_ashi_basic() {
        let (opens, highs, lows, closes) = gen_ohlc(20);
        let (ha_o, ha_h, ha_l, ha_c) = heikin_ashi(&opens, &highs, &lows, &closes);
        assert_eq!(ha_o.len(), 20);
        assert_eq!(ha_h.len(), 20);
        assert_eq!(ha_l.len(), 20);
        assert_eq!(ha_c.len(), 20);

        // First bar: HA_Open = (O + C) / 2
        assert_abs_diff_eq!(ha_o[0], (opens[0] + closes[0]) / 2.0, epsilon = 1e-9);
        // First bar: HA_Close = (O + H + L + C) / 4
        assert_abs_diff_eq!(
            ha_c[0],
            (opens[0] + highs[0] + lows[0] + closes[0]) / 4.0,
            epsilon = 1e-9
        );
        // HA_High >= HA_Open and HA_High >= HA_Close
        for i in 0..20 {
            assert!(ha_h[i] >= ha_o[i], "HA_High < HA_Open at {i}");
            assert!(ha_h[i] >= ha_c[i], "HA_High < HA_Close at {i}");
            assert!(ha_l[i] <= ha_o[i], "HA_Low > HA_Open at {i}");
            assert!(ha_l[i] <= ha_c[i], "HA_Low > HA_Close at {i}");
        }
    }

    #[test]
    fn heikin_ashi_known_values() {
        // From kand test data
        let opens = vec![10.0, 10.5, 11.2, 10.8, 11.5];
        let highs = vec![11.0, 11.5, 11.8, 11.3, 12.0];
        let lows = vec![9.5, 10.2, 10.8, 10.5, 11.3];
        let closes = vec![10.8, 11.3, 11.5, 11.0, 11.8];

        let (ha_o, ha_h, ha_l, ha_c) = heikin_ashi(&opens, &highs, &lows, &closes);

        // Bar 0
        assert_abs_diff_eq!(ha_o[0], 10.4, epsilon = 1e-4);
        assert_abs_diff_eq!(ha_c[0], 10.325, epsilon = 1e-4);
        assert_abs_diff_eq!(ha_h[0], 11.0, epsilon = 1e-4);
        assert_abs_diff_eq!(ha_l[0], 9.5, epsilon = 1e-4);

        // Bar 1
        assert_abs_diff_eq!(ha_o[1], 10.3625, epsilon = 1e-4);
        assert_abs_diff_eq!(ha_c[1], 10.875, epsilon = 1e-4);
        assert_abs_diff_eq!(ha_h[1], 11.5, epsilon = 1e-4);
        assert_abs_diff_eq!(ha_l[1], 10.2, epsilon = 1e-4);
    }

    #[test]
    fn heikin_ashi_inc_matches_batch() {
        let (opens, highs, lows, closes) = gen_ohlc(30);
        let n = 25;
        let (batch_o, batch_h, batch_l, batch_c, last_o, last_c) =
            heikin_ashi_with_state(&opens[..n], &highs[..n], &lows[..n], &closes[..n]);
        assert_eq!(batch_o.len(), n);
        assert_eq!(batch_h.len(), n);
        assert_eq!(batch_l.len(), n);
        assert_eq!(batch_c.len(), n);

        // Extend by one bar
        let (inc_o, inc_h, inc_l, inc_c) =
            heikin_ashi_inc(opens[n], highs[n], lows[n], closes[n], last_o, last_c);

        // Compare against full batch
        let (full_o, full_h, full_l, full_c) =
            heikin_ashi(&opens[..=n], &highs[..=n], &lows[..=n], &closes[..=n]);
        assert_abs_diff_eq!(inc_o, *full_o.last().unwrap(), epsilon = 1e-9);
        assert_abs_diff_eq!(inc_h, *full_h.last().unwrap(), epsilon = 1e-9);
        assert_abs_diff_eq!(inc_l, *full_l.last().unwrap(), epsilon = 1e-9);
        assert_abs_diff_eq!(inc_c, *full_c.last().unwrap(), epsilon = 1e-9);
    }

    #[test]
    fn heikin_ashi_inc_multi_step() {
        let (opens, highs, lows, closes) = gen_ohlc(40);
        let init_len = 15;
        let (batch_o, batch_h, batch_l, batch_c, mut prev_o, mut prev_c) =
            heikin_ashi_with_state(
                &opens[..init_len], &highs[..init_len],
                &lows[..init_len], &closes[..init_len],
            );
        assert_eq!(batch_o.len(), init_len);
        assert_eq!(batch_h.len(), init_len);
        assert_eq!(batch_l.len(), init_len);
        assert_eq!(batch_c.len(), init_len);

        for step in init_len..40 {
            let (inc_o, inc_h, inc_l, inc_c) =
                heikin_ashi_inc(opens[step], highs[step], lows[step], closes[step], prev_o, prev_c);

            let (full_o, full_h, full_l, full_c) =
                heikin_ashi(&opens[..=step], &highs[..=step], &lows[..=step], &closes[..=step]);
            assert_abs_diff_eq!(inc_o, *full_o.last().unwrap(), epsilon = 1e-9);
            assert_abs_diff_eq!(inc_h, *full_h.last().unwrap(), epsilon = 1e-9);
            assert_abs_diff_eq!(inc_l, *full_l.last().unwrap(), epsilon = 1e-9);
            assert_abs_diff_eq!(inc_c, *full_c.last().unwrap(), epsilon = 1e-9);

            prev_o = inc_o;
            prev_c = inc_c;
        }
    }

    #[test]
    fn heikin_ashi_empty() {
        let (ha_o, ha_h, ha_l, ha_c) = heikin_ashi(&[], &[], &[], &[]);
        assert!(ha_o.is_empty());
        assert!(ha_h.is_empty());
        assert!(ha_l.is_empty());
        assert!(ha_c.is_empty());
    }

    #[test]
    fn heikin_ashi_single_bar() {
        let (ha_o, ha_h, ha_l, ha_c) = heikin_ashi(&[100.0], &[105.0], &[95.0], &[102.0]);
        assert_eq!(ha_o.len(), 1);
        assert_abs_diff_eq!(ha_o[0], (100.0 + 102.0) / 2.0, epsilon = 1e-9);
        assert_abs_diff_eq!(ha_c[0], (100.0 + 105.0 + 95.0 + 102.0) / 4.0, epsilon = 1e-9);
        assert_abs_diff_eq!(ha_h[0], 105.0, epsilon = 1e-9);
        assert_abs_diff_eq!(ha_l[0], 95.0, epsilon = 1e-9);
    }

    // ── Price Transforms ─────────────────────────────────────────────────

    #[test]
    fn typical_price_known() {
        // H=105, L=95, C=102 → (105+95+102)/3 = 100.6667
        assert_abs_diff_eq!(typical_price(105.0, 95.0, 102.0), 302.0 / 3.0, epsilon = 1e-9);
    }

    #[test]
    fn median_price_known() {
        assert_abs_diff_eq!(median_price(105.0, 95.0), 100.0, epsilon = 1e-9);
    }

    #[test]
    fn weighted_close_known() {
        // H=105, L=95, C=102 → (105+95+204)/4 = 101.0
        assert_abs_diff_eq!(weighted_close(105.0, 95.0, 102.0), 101.0, epsilon = 1e-9);
    }

    #[test]
    fn price_transform_series_lengths() {
        let h = vec![105.0, 110.0, 108.0];
        let l = vec![95.0, 100.0, 98.0];
        let c = vec![102.0, 107.0, 103.0];
        assert_eq!(typical_price_series(&h, &l, &c).len(), 3);
        assert_eq!(median_price_series(&h, &l).len(), 3);
        assert_eq!(weighted_close_series(&h, &l, &c).len(), 3);
    }

    // ── Volume Candles ──────────────────────────────────────────────────

    #[test]
    fn volume_candles_empty() {
        assert!(volume_candles(&[]).is_empty());
    }

    #[test]
    fn volume_candles_tiers() {
        // avg = 100.0
        let vols = vec![50.0, 75.0, 100.0, 125.0, 200.0, 250.0, 10.0, 90.0];
        let avg = vols.iter().sum::<f64>() / vols.len() as f64;
        let tiers = volume_candles(&vols);
        assert_eq!(tiers.len(), vols.len());
        for (i, &t) in tiers.iter().enumerate() {
            let ratio = vols[i] / avg;
            let expected = if ratio >= 2.0 {
                4
            } else if ratio >= 1.25 {
                3
            } else if ratio >= 0.75 {
                2
            } else {
                1
            };
            assert_eq!(t, expected, "tier mismatch at index {i}, ratio={ratio:.3}");
        }
    }

    #[test]
    fn volume_candles_all_zero() {
        let tiers = volume_candles(&[0.0, 0.0, 0.0]);
        assert_eq!(tiers, vec![1, 1, 1]);
    }

    // ── K's Candles ─────────────────────────────────────────────────────

    #[test]
    fn k_candles_empty() {
        let (o, h, l, c) = k_candles(&[], &[], &[], &[]);
        assert!(o.is_empty());
        assert!(h.is_empty());
        assert!(l.is_empty());
        assert!(c.is_empty());
    }

    #[test]
    fn k_candles_length() {
        let (opens, highs, lows, closes) = gen_ohlc(30);
        let (ko, kh, kl, kc) = k_candles(&opens, &highs, &lows, &closes);
        assert_eq!(ko.len(), 30);
        assert_eq!(kh.len(), 30);
        assert_eq!(kl.len(), 30);
        assert_eq!(kc.len(), 30);
    }

    #[test]
    fn k_candles_high_ge_low() {
        let (opens, highs, lows, closes) = gen_ohlc(30);
        let (ko, kh, kl, kc) = k_candles(&opens, &highs, &lows, &closes);
        // After EMA warmup (first 4 bars are NaN for period=5), check invariants
        for i in 4..30 {
            assert!(
                kh[i] >= kl[i],
                "k_high < k_low at {i}: h={}, l={}",
                kh[i],
                kl[i]
            );
            assert!(kh[i] >= ko[i], "k_high < k_open at {i}");
            assert!(kh[i] >= kc[i], "k_high < k_close at {i}");
            assert!(kl[i] <= ko[i], "k_low > k_open at {i}");
            assert!(kl[i] <= kc[i], "k_low > k_close at {i}");
        }
    }

    #[test]
    fn k_candles_short_input() {
        // Fewer bars than EMA period — should not panic
        let (opens, highs, lows, closes) = gen_ohlc(3);
        let (ko, kh, kl, kc) = k_candles(&opens, &highs, &lows, &closes);
        assert_eq!(ko.len(), 3);
        assert_eq!(kh.len(), 3);
        assert_eq!(kl.len(), 3);
        assert_eq!(kc.len(), 3);
    }

    // ── CARSI Candles ───────────────────────────────────────────────────

    #[test]
    fn carsi_candles_empty() {
        let (o, h, l, c) = carsi_candles(&[], &[], &[], &[]);
        assert!(o.is_empty());
        assert!(h.is_empty());
        assert!(l.is_empty());
        assert!(c.is_empty());
    }

    #[test]
    fn carsi_candles_length() {
        let (opens, highs, lows, closes) = gen_ohlc(40);
        let (co, ch, cl, cc) = carsi_candles(&opens, &highs, &lows, &closes);
        assert_eq!(co.len(), 40);
        assert_eq!(ch.len(), 40);
        assert_eq!(cl.len(), 40);
        assert_eq!(cc.len(), 40);
    }

    #[test]
    fn carsi_candles_high_ge_low() {
        let (opens, highs, lows, closes) = gen_ohlc(40);
        let (co, ch, cl, cc) = carsi_candles(&opens, &highs, &lows, &closes);
        for i in 0..40 {
            assert!(
                ch[i] >= cl[i],
                "carsi_high < carsi_low at {i}: h={}, l={}",
                ch[i],
                cl[i]
            );
            assert!(ch[i] >= co[i], "carsi_high < carsi_open at {i}");
            assert!(ch[i] >= cc[i], "carsi_high < carsi_close at {i}");
            assert!(cl[i] <= co[i], "carsi_low > carsi_open at {i}");
            assert!(cl[i] <= cc[i], "carsi_low > carsi_close at {i}");
        }
    }

    #[test]
    fn carsi_candles_short_input() {
        // Fewer bars than RSI period — should not panic
        let (opens, highs, lows, closes) = gen_ohlc(5);
        let (co, ch, cl, cc) = carsi_candles(&opens, &highs, &lows, &closes);
        assert_eq!(co.len(), 5);
        assert_eq!(ch.len(), 5);
        assert_eq!(cl.len(), 5);
        assert_eq!(cc.len(), 5);
    }

    #[test]
    fn carsi_candles_rsi_range() {
        // RSI output should be in [0, 100] range
        let (opens, highs, lows, closes) = gen_ohlc(50);
        let (co, ch, cl, cc) = carsi_candles(&opens, &highs, &lows, &closes);
        for i in 0..50 {
            assert!(co[i] >= 0.0 && co[i] <= 100.0, "carsi_open out of range at {i}");
            assert!(ch[i] >= 0.0 && ch[i] <= 100.0, "carsi_high out of range at {i}");
            assert!(cl[i] >= 0.0 && cl[i] <= 100.0, "carsi_low out of range at {i}");
            assert!(cc[i] >= 0.0 && cc[i] <= 100.0, "carsi_close out of range at {i}");
        }
    }
}
