// patterns.rs — Candlestick pattern detection + structural price patterns
//
// Mirrors Python: indicator_engine/patterns.py
//
// kand-Blueprint pattern adopted:
//   batch fn()   — detect across full series (returns Vec<i8>)
//   fn _inc()    — detect on single bar (returns i8)
//
// Signal values: 0 = no pattern, 1 = pattern detected (bullish), -1 = bearish
// Single-bar patterns: _inc IS the core logic, batch just iterates.
// Multi-bar patterns: batch only (need prior bar context).
//
// Single-bar:   cdl_doji, cdl_hammer, cdl_inverted_hammer,
//               cdl_dragonfly_doji, cdl_gravestone_doji, cdl_spinning_top
// Two-bar:      cdl_engulfing, cdl_piercing_line, cdl_dark_cloud_cover
// Three-bar:    cdl_morning_star, cdl_evening_star,
//               cdl_three_white_soldiers, cdl_three_black_crows
//
// Structural:   pivot_points (classic/fibonacci/camarilla),
//               zigzag, detect_swing_points, market_structure

use crate::helper::{real_body, upper_shadow, lower_shadow, candle_range as range};

// ── Doji ────────────────────────────────────────────────────────────────────

/// Doji pattern detection — single bar.
///
/// A Doji occurs when the real body is very small relative to the total range,
/// and the upper and lower shadows are roughly equal.
///
/// Returns 1 if Doji detected, 0 otherwise.
///
/// # Arguments
/// * `body_pct` — max body size as % of range (default: 5.0)
/// * `shadow_eq_pct` — max shadow difference as % (default: 100.0)
#[inline]
pub fn cdl_doji_inc(
    open: f64, high: f64, low: f64, close: f64,
    body_pct: f64, shadow_eq_pct: f64,
) -> i8 {
    let rng = range(high, low);
    if rng <= 0.0 {
        return 0;
    }
    let body = real_body(open, close);
    if body > rng * body_pct / 100.0 {
        return 0;
    }
    let up = upper_shadow(high, open, close);
    let dn = lower_shadow(low, open, close);

    // Shadow equality check (same logic as kand)
    let shadows_equal = if up > 0.0 && dn > 0.0 {
        let diff = ((up - dn).abs() / dn * 100.0).min((dn - up).abs() / up * 100.0);
        diff < shadow_eq_pct
    } else {
        false
    };

    if shadows_equal { 1 } else { 0 }
}

/// Doji pattern detection — full series.
pub fn cdl_doji(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
    body_pct: f64, shadow_eq_pct: f64,
) -> Vec<i8> {
    (0..opens.len())
        .map(|i| cdl_doji_inc(opens[i], highs[i], lows[i], closes[i], body_pct, shadow_eq_pct))
        .collect()
}

// ── Hammer ──────────────────────────────────────────────────────────────────

/// Hammer pattern detection — single bar.
///
/// A Hammer has a small real body at the top of the range with a long lower shadow
/// (at least `factor` × body). Bullish reversal signal.
///
/// Returns 1 if Hammer detected, 0 otherwise.
///
/// # Arguments
/// * `body_pct` — max body as % of range for "small body" (default: 35.0)
/// * `factor` — min ratio of lower shadow to body (default: 2.0)
#[inline]
pub fn cdl_hammer_inc(
    open: f64, high: f64, low: f64, close: f64,
    body_pct: f64, factor: f64,
) -> i8 {
    let rng = range(high, low);
    if rng <= 0.0 {
        return 0;
    }
    let body = real_body(open, close);
    if body <= 0.0 || body > rng * body_pct / 100.0 {
        return 0;
    }
    let up = upper_shadow(high, open, close);
    let dn = lower_shadow(low, open, close);

    // Hammer: long lower shadow, small upper shadow, body near top
    if dn >= factor * body && up <= body && open.min(close) > (high + low) / 2.0 {
        1
    } else {
        0
    }
}

/// Hammer pattern detection — full series.
pub fn cdl_hammer(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
    body_pct: f64, factor: f64,
) -> Vec<i8> {
    (0..opens.len())
        .map(|i| cdl_hammer_inc(opens[i], highs[i], lows[i], closes[i], body_pct, factor))
        .collect()
}

// ── Inverted Hammer ─────────────────────────────────────────────────────────

/// Inverted Hammer pattern detection — single bar.
///
/// An Inverted Hammer has a small real body at the bottom of the range with a
/// long upper shadow (at least `factor` × body). Bullish reversal signal.
///
/// Returns 1 if Inverted Hammer detected, 0 otherwise.
#[inline]
pub fn cdl_inverted_hammer_inc(
    open: f64, high: f64, low: f64, close: f64,
    body_pct: f64, factor: f64,
) -> i8 {
    let rng = range(high, low);
    if rng <= 0.0 {
        return 0;
    }
    let body = real_body(open, close);
    if body <= 0.0 || body > rng * body_pct / 100.0 {
        return 0;
    }
    let up = upper_shadow(high, open, close);
    let dn = lower_shadow(low, open, close);

    // Inverted Hammer: long upper shadow, small lower shadow, body near bottom
    if up >= factor * body && dn <= body && open.max(close) < (high + low) / 2.0 {
        1
    } else {
        0
    }
}

/// Inverted Hammer pattern detection — full series.
pub fn cdl_inverted_hammer(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
    body_pct: f64, factor: f64,
) -> Vec<i8> {
    (0..opens.len())
        .map(|i| cdl_inverted_hammer_inc(opens[i], highs[i], lows[i], closes[i], body_pct, factor))
        .collect()
}

// ── Dragonfly Doji ──────────────────────────────────────────────────────────

/// Dragonfly Doji pattern detection — single bar.
///
/// A Dragonfly Doji has a tiny body at the top with a long lower shadow and
/// virtually no upper shadow. Bullish reversal signal.
///
/// Returns 1 if detected, 0 otherwise.
///
/// # Arguments
/// * `body_pct` — max body as % of range (default: 5.0)
/// * `shadow_pct` — max upper shadow as % of range (default: 5.0)
#[inline]
pub fn cdl_dragonfly_doji_inc(
    open: f64, high: f64, low: f64, close: f64,
    body_pct: f64, shadow_pct: f64,
) -> i8 {
    let rng = range(high, low);
    if rng <= 0.0 {
        return 0;
    }
    let body = real_body(open, close);
    let up = upper_shadow(high, open, close);
    let dn = lower_shadow(low, open, close);

    // Doji body + no upper shadow + long lower shadow
    if body <= rng * body_pct / 100.0
        && up <= rng * shadow_pct / 100.0
        && dn > rng * 0.3  // lower shadow at least 30% of range
    {
        1
    } else {
        0
    }
}

/// Dragonfly Doji pattern detection — full series.
pub fn cdl_dragonfly_doji(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
    body_pct: f64, shadow_pct: f64,
) -> Vec<i8> {
    (0..opens.len())
        .map(|i| cdl_dragonfly_doji_inc(opens[i], highs[i], lows[i], closes[i], body_pct, shadow_pct))
        .collect()
}

// ── Gravestone Doji ─────────────────────────────────────────────────────────

/// Gravestone Doji pattern detection — single bar.
///
/// A Gravestone Doji has a tiny body at the bottom with a long upper shadow and
/// virtually no lower shadow. Bearish reversal signal.
///
/// Returns -1 if detected, 0 otherwise.
///
/// # Arguments
/// * `body_pct` — max body as % of range (default: 5.0)
/// * `shadow_pct` — max lower shadow as % of range (default: 5.0)
#[inline]
pub fn cdl_gravestone_doji_inc(
    open: f64, high: f64, low: f64, close: f64,
    body_pct: f64, shadow_pct: f64,
) -> i8 {
    let rng = range(high, low);
    if rng <= 0.0 {
        return 0;
    }
    let body = real_body(open, close);
    let up = upper_shadow(high, open, close);
    let dn = lower_shadow(low, open, close);

    // Doji body + no lower shadow + long upper shadow
    if body <= rng * body_pct / 100.0
        && dn <= rng * shadow_pct / 100.0
        && up > rng * 0.3  // upper shadow at least 30% of range
    {
        -1  // bearish signal
    } else {
        0
    }
}

/// Gravestone Doji pattern detection — full series.
pub fn cdl_gravestone_doji(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
    body_pct: f64, shadow_pct: f64,
) -> Vec<i8> {
    (0..opens.len())
        .map(|i| cdl_gravestone_doji_inc(opens[i], highs[i], lows[i], closes[i], body_pct, shadow_pct))
        .collect()
}

// ── Spinning Top ──────────────────────────────────────────────────────────

/// Spinning Top — small body with both shadows > 20% of range.
///
/// Returns 1 if detected (neutral indecision signal), 0 otherwise.
#[inline]
pub fn cdl_spinning_top_inc(open: f64, high: f64, low: f64, close: f64) -> i8 {
    let rng = range(high, low);
    if rng <= 0.0 {
        return 0;
    }
    let body = real_body(open, close);
    let body_ratio = body / rng;
    let up = upper_shadow(high, open, close);
    let dn = lower_shadow(low, open, close);
    if body_ratio > 0.15 && body_ratio <= 0.40 && dn > 0.2 * rng && up > 0.2 * rng {
        1
    } else {
        0
    }
}

/// Spinning Top — full series.
pub fn cdl_spinning_top(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
) -> Vec<i8> {
    (0..opens.len())
        .map(|i| cdl_spinning_top_inc(opens[i], highs[i], lows[i], closes[i]))
        .collect()
}

// ── Engulfing ─────────────────────────────────────────────────────────────

/// Bullish/Bearish Engulfing — two-bar pattern.
///
/// Returns +1 (bullish engulfing), -1 (bearish engulfing), 0 (none).
pub fn cdl_engulfing(
    opens: &[f64], _highs: &[f64], _lows: &[f64], closes: &[f64],
) -> Vec<i8> {
    let n = opens.len();
    let mut out = vec![0i8; n];
    for i in 1..n {
        let (co, cc) = (opens[i], closes[i]);
        let (po, pc) = (opens[i - 1], closes[i - 1]);
        // Bullish: current bullish engulfs prior bearish
        if cc > co && pc < po && cc >= po && co <= pc {
            out[i] = 1;
        }
        // Bearish: current bearish engulfs prior bullish
        else if cc < co && pc > po && co >= pc && cc <= po {
            out[i] = -1;
        }
    }
    out
}

// ── Piercing Line ─────────────────────────────────────────────────────────

/// Piercing Line — bullish two-bar reversal.
///
/// Prior bar bearish, current opens below prior low, closes above prior midpoint.
pub fn cdl_piercing_line(
    opens: &[f64], _highs: &[f64], lows: &[f64], closes: &[f64],
) -> Vec<i8> {
    let n = opens.len();
    let mut out = vec![0i8; n];
    for i in 1..n {
        let prev_bearish = closes[i - 1] < opens[i - 1];
        let cur_bullish = closes[i] > opens[i];
        if prev_bearish && cur_bullish {
            let prev_mid = (opens[i - 1] + closes[i - 1]) / 2.0;
            if opens[i] < lows[i - 1] && closes[i] > prev_mid {
                out[i] = 1;
            }
        }
    }
    out
}

// ── Dark Cloud Cover ──────────────────────────────────────────────────────

/// Dark Cloud Cover — bearish two-bar reversal.
///
/// Prior bar bullish, current opens above prior high, closes below prior midpoint.
pub fn cdl_dark_cloud_cover(
    opens: &[f64], highs: &[f64], _lows: &[f64], closes: &[f64],
) -> Vec<i8> {
    let n = opens.len();
    let mut out = vec![0i8; n];
    for i in 1..n {
        let prev_bullish = closes[i - 1] > opens[i - 1];
        let cur_bearish = closes[i] < opens[i];
        if prev_bullish && cur_bearish {
            let prev_mid = (opens[i - 1] + closes[i - 1]) / 2.0;
            if opens[i] > highs[i - 1] && closes[i] < prev_mid {
                out[i] = -1;
            }
        }
    }
    out
}

// ── Morning Star ──────────────────────────────────────────────────────────

/// Morning Star — bullish three-bar reversal.
///
/// Bar0 large bearish, Bar1 small body (indecision), Bar2 large bullish closing above Bar0 midpoint.
pub fn cdl_morning_star(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
) -> Vec<i8> {
    let n = opens.len();
    let mut out = vec![0i8; n];
    for i in 2..n {
        let b0_bear = closes[i - 2] < opens[i - 2];
        let b0_body = real_body(opens[i - 2], closes[i - 2]);
        let b0_range = range(highs[i - 2], lows[i - 2]).max(1e-9);
        let b1_body = real_body(opens[i - 1], closes[i - 1]);
        let b1_range = range(highs[i - 1], lows[i - 1]).max(1e-9);
        let b2_bull = closes[i] > opens[i];
        let b0_mid = (opens[i - 2] + closes[i - 2]) / 2.0;

        if b0_bear
            && b0_body >= 0.5 * b0_range
            && b1_body <= 0.3 * b1_range
            && b2_bull
            && closes[i] > b0_mid
        {
            out[i] = 1;
        }
    }
    out
}

// ── Evening Star ──────────────────────────────────────────────────────────

/// Evening Star — bearish three-bar reversal.
pub fn cdl_evening_star(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
) -> Vec<i8> {
    let n = opens.len();
    let mut out = vec![0i8; n];
    for i in 2..n {
        let b0_bull = closes[i - 2] > opens[i - 2];
        let b0_body = real_body(opens[i - 2], closes[i - 2]);
        let b0_range = range(highs[i - 2], lows[i - 2]).max(1e-9);
        let b1_body = real_body(opens[i - 1], closes[i - 1]);
        let b1_range = range(highs[i - 1], lows[i - 1]).max(1e-9);
        let b2_bear = closes[i] < opens[i];
        let b0_mid = (opens[i - 2] + closes[i - 2]) / 2.0;

        if b0_bull
            && b0_body >= 0.5 * b0_range
            && b1_body <= 0.3 * b1_range
            && b2_bear
            && closes[i] < b0_mid
        {
            out[i] = -1;
        }
    }
    out
}

// ── Three White Soldiers ──────────────────────────────────────────────────

/// Three White Soldiers — bullish three-bar continuation.
///
/// Three consecutive bullish bars with progressive higher closes and opens.
pub fn cdl_three_white_soldiers(
    opens: &[f64], _highs: &[f64], _lows: &[f64], closes: &[f64],
) -> Vec<i8> {
    let n = opens.len();
    let mut out = vec![0i8; n];
    for i in 2..n {
        let all_bull = closes[i - 2] > opens[i - 2]
            && closes[i - 1] > opens[i - 1]
            && closes[i] > opens[i];
        let rising_closes = closes[i - 1] > closes[i - 2] && closes[i] > closes[i - 1];
        let rising_opens = opens[i - 1] > opens[i - 2] && opens[i] > opens[i - 1];
        if all_bull && rising_closes && rising_opens {
            out[i] = 1;
        }
    }
    out
}

// ── Three Black Crows ─────────────────────────────────────────────────────

/// Three Black Crows — bearish three-bar continuation.
pub fn cdl_three_black_crows(
    opens: &[f64], _highs: &[f64], _lows: &[f64], closes: &[f64],
) -> Vec<i8> {
    let n = opens.len();
    let mut out = vec![0i8; n];
    for i in 2..n {
        let all_bear = closes[i - 2] < opens[i - 2]
            && closes[i - 1] < opens[i - 1]
            && closes[i] < opens[i];
        let falling_closes = closes[i - 1] < closes[i - 2] && closes[i] < closes[i - 1];
        let falling_opens = opens[i - 1] < opens[i - 2] && opens[i] < opens[i - 1];
        if all_bear && falling_closes && falling_opens {
            out[i] = -1;
        }
    }
    out
}

// ══════════════════════════════════════════════════════════════════════════
// Pivot Points
// ══════════════════════════════════════════════════════════════════════════

/// Pivot point levels (PP + support/resistance levels).
#[derive(Debug, Clone)]
pub struct PivotLevels {
    pub pp: f64,
    pub levels: Vec<(String, f64)>,
}

/// Classic (Standard) Pivot Points from prior session H/L/C.
pub fn pivot_points_classic(prev_high: f64, prev_low: f64, prev_close: f64) -> PivotLevels {
    let pp = (prev_high + prev_low + prev_close) / 3.0;
    PivotLevels {
        pp,
        levels: vec![
            ("r1".into(), 2.0 * pp - prev_low),
            ("r2".into(), pp + (prev_high - prev_low)),
            ("r3".into(), prev_high + 2.0 * (pp - prev_low)),
            ("s1".into(), 2.0 * pp - prev_high),
            ("s2".into(), pp - (prev_high - prev_low)),
            ("s3".into(), prev_low - 2.0 * (prev_high - pp)),
        ],
    }
}

/// Fibonacci Pivot Points — PP + Fib retracements of prior range.
pub fn pivot_points_fibonacci(prev_high: f64, prev_low: f64, prev_close: f64) -> PivotLevels {
    let pp = (prev_high + prev_low + prev_close) / 3.0;
    let r = prev_high - prev_low;
    PivotLevels {
        pp,
        levels: vec![
            ("r1".into(), pp + 0.382 * r),
            ("r2".into(), pp + 0.618 * r),
            ("r3".into(), pp + r),
            ("s1".into(), pp - 0.382 * r),
            ("s2".into(), pp - 0.618 * r),
            ("s3".into(), pp - r),
        ],
    }
}

/// Camarilla Pivot Points — Close-anchored with 1.1/N multipliers.
pub fn pivot_points_camarilla(prev_high: f64, prev_low: f64, prev_close: f64) -> PivotLevels {
    let r = prev_high - prev_low;
    PivotLevels {
        pp: (prev_high + prev_low + prev_close) / 3.0,
        levels: vec![
            ("h1".into(), prev_close + r * 1.1 / 12.0),
            ("h2".into(), prev_close + r * 1.1 / 6.0),
            ("h3".into(), prev_close + r * 1.1 / 4.0),
            ("h4".into(), prev_close + r * 1.1 / 2.0),
            ("l1".into(), prev_close - r * 1.1 / 12.0),
            ("l2".into(), prev_close - r * 1.1 / 6.0),
            ("l3".into(), prev_close - r * 1.1 / 4.0),
            ("l4".into(), prev_close - r * 1.1 / 2.0),
        ],
    }
}

// ══════════════════════════════════════════════════════════════════════════
// ZigZag
// ══════════════════════════════════════════════════════════════════════════

/// ZigZag pivot point.
#[derive(Debug, Clone)]
pub struct ZigZagPivot {
    pub index: usize,
    pub price: f64,
    pub is_high: bool,
}

/// ZigZag — percentage-based reversal detection (TradingView standard).
///
/// Connects significant turning points where price reverses by at least `deviation`%.
/// Default: deviation = 5.0 (5%).
pub fn zigzag(highs: &[f64], lows: &[f64], deviation: f64) -> Vec<ZigZagPivot> {
    let n = highs.len();
    if n < 2 {
        return Vec::new();
    }
    let threshold = deviation / 100.0;
    let mut pivots = Vec::new();

    let mut last_is_high = true;
    let mut last_price = highs[0];
    let mut last_idx = 0;

    for i in 1..n {
        if last_is_high {
            if highs[i] > last_price {
                last_price = highs[i];
                last_idx = i;
            } else if lows[i] < last_price * (1.0 - threshold) {
                pivots.push(ZigZagPivot {
                    index: last_idx,
                    price: last_price,
                    is_high: true,
                });
                last_is_high = false;
                last_price = lows[i];
                last_idx = i;
            }
        } else {
            if lows[i] < last_price {
                last_price = lows[i];
                last_idx = i;
            } else if highs[i] > last_price * (1.0 + threshold) {
                pivots.push(ZigZagPivot {
                    index: last_idx,
                    price: last_price,
                    is_high: false,
                });
                last_is_high = true;
                last_price = highs[i];
                last_idx = i;
            }
        }
    }
    // Emit last tentative pivot
    pivots.push(ZigZagPivot {
        index: last_idx,
        price: last_price,
        is_high: last_is_high,
    });
    pivots
}

// ══════════════════════════════════════════════════════════════════════════
// Swing Point Detection + Market Structure
// ══════════════════════════════════════════════════════════════════════════

/// Swing point.
#[derive(Debug, Clone)]
pub struct SwingPoint {
    pub index: usize,
    pub price: f64,
    pub is_high: bool,
}

/// Detect confirmed swing highs and lows using N-bar lookback/lookahead.
///
/// A bar at index i is a swing high if `high[i] >= max(high[i-N..i+N])`.
/// TradingView default: lookback=2 (5-bar window).
pub fn detect_swing_points(highs: &[f64], lows: &[f64], lookback: usize) -> Vec<SwingPoint> {
    let n = highs.len();
    if n <= 2 * lookback {
        return Vec::new();
    }
    let mut swings = Vec::new();

    for i in lookback..(n - lookback) {
        // Check swing high
        let mut is_sh = true;
        for j in (i - lookback)..=(i + lookback) {
            if j != i && highs[j] > highs[i] {
                is_sh = false;
                break;
            }
        }
        if is_sh {
            swings.push(SwingPoint {
                index: i,
                price: highs[i],
                is_high: true,
            });
        }

        // Check swing low
        let mut is_sl = true;
        for j in (i - lookback)..=(i + lookback) {
            if j != i && lows[j] < lows[i] {
                is_sl = false;
                break;
            }
        }
        if is_sl {
            swings.push(SwingPoint {
                index: i,
                price: lows[i],
                is_high: false,
            });
        }
    }
    // Sort by index (already mostly sorted, but swing high + low at same index)
    swings.sort_by_key(|s| s.index);
    swings
}

/// Market structure label.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StructureLabel {
    HH,  // Higher High
    LH,  // Lower High
    EH,  // Equal High
    HL,  // Higher Low
    LL,  // Lower Low
    EL,  // Equal Low
    SH,  // First Swing High
    SL,  // First Swing Low
}

/// Labeled swing point with market structure label.
#[derive(Debug, Clone)]
pub struct LabeledSwing {
    pub index: usize,
    pub price: f64,
    pub is_high: bool,
    pub label: StructureLabel,
}

/// Market Structure — label swing points as HH/HL/LH/LL.
pub fn market_structure(highs: &[f64], lows: &[f64], lookback: usize) -> Vec<LabeledSwing> {
    let swings = detect_swing_points(highs, lows, lookback);
    let mut last_sh: Option<f64> = None;
    let mut last_sl: Option<f64> = None;
    let mut labeled = Vec::with_capacity(swings.len());

    for s in &swings {
        if s.is_high {
            let label = match last_sh {
                None => StructureLabel::SH,
                Some(prev) => {
                    if s.price > prev {
                        StructureLabel::HH
                    } else if s.price < prev {
                        StructureLabel::LH
                    } else {
                        StructureLabel::EH
                    }
                }
            };
            last_sh = Some(s.price);
            labeled.push(LabeledSwing {
                index: s.index,
                price: s.price,
                is_high: true,
                label,
            });
        } else {
            let label = match last_sl {
                None => StructureLabel::SL,
                Some(prev) => {
                    if s.price > prev {
                        StructureLabel::HL
                    } else if s.price < prev {
                        StructureLabel::LL
                    } else {
                        StructureLabel::EL
                    }
                }
            };
            last_sl = Some(s.price);
            labeled.push(LabeledSwing {
                index: s.index,
                price: s.price,
                is_high: false,
                label,
            });
        }
    }
    labeled
}

/// Determine trend from market structure labels.
///
/// Returns "bullish" (HH+HL), "bearish" (LH+LL), or "ranging".
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MarketTrend {
    Bullish,
    Bearish,
    Ranging,
}

pub fn market_structure_trend(labeled: &[LabeledSwing]) -> MarketTrend {
    if labeled.len() < 2 {
        return MarketTrend::Ranging;
    }
    let mut last_high_label: Option<StructureLabel> = None;
    let mut last_low_label: Option<StructureLabel> = None;

    for lb in labeled.iter().rev() {
        if lb.is_high && last_high_label.is_none() {
            last_high_label = Some(lb.label);
        } else if !lb.is_high && last_low_label.is_none() {
            last_low_label = Some(lb.label);
        }
        if last_high_label.is_some() && last_low_label.is_some() {
            break;
        }
    }

    match (last_high_label, last_low_label) {
        (Some(StructureLabel::HH), Some(StructureLabel::HL)) => MarketTrend::Bullish,
        (Some(StructureLabel::LH), Some(StructureLabel::LL)) => MarketTrend::Bearish,
        _ => MarketTrend::Ranging,
    }
}

// ══════════════════════════════════════════════════════════════════════════
// Higher-level pattern structures + builders
// ══════════════════════════════════════════════════════════════════════════

/// Direction of a detected pattern.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PatternDirection {
    Bullish,
    Bearish,
    Neutral,
}

/// A single detected pattern with metadata.
#[derive(Debug, Clone)]
pub struct PatternData {
    pub pattern_type: &'static str,
    pub direction: PatternDirection,
    pub start_idx: usize,
    pub end_idx: usize,
    pub confidence: f64,
    /// Numeric details (ratios, levels, etc.)
    pub details: Vec<(&'static str, f64)>,
}

/// Result from a pattern builder function.
#[derive(Debug, Clone)]
pub struct PatternResult {
    pub patterns: Vec<PatternData>,
    pub scanned_bars: usize,
}

/// Fibonacci retracement level.
#[derive(Debug, Clone, Copy)]
pub struct FibLevel {
    pub ratio: f64,
    pub price: f64,
}

/// Result from fibonacci_levels().
#[derive(Debug, Clone)]
pub struct FibResult {
    pub anchor_high: f64,
    pub anchor_low: f64,
    pub levels: Vec<FibLevel>,
}

/// Standard Fibonacci ratios used across pattern detection.
const FIB_RATIOS: [f64; 13] = [
    0.236, 0.382, 0.5, 0.618, 0.786, 0.886, 1.0, 1.13, 1.272, 1.618, 2.0, 2.24, 2.618,
];

/// Confluence zone — cluster of overlapping Fibonacci levels.
#[derive(Debug, Clone)]
pub struct ConfluenceZone {
    pub price_center: f64,
    pub price_low: f64,
    pub price_high: f64,
    pub strength: usize,
    pub ratios: Vec<f64>,
}

/// Result from fibonacci_confluence().
#[derive(Debug, Clone)]
pub struct FibConfluenceResult {
    pub zones: Vec<ConfluenceZone>,
    pub total_levels: usize,
}

// ── Fibonacci ─────────────────────────────────────────────────────────────

/// Compute Fibonacci retracement levels from an anchor high/low.
///
/// If swing points are provided, uses the last two; otherwise falls back
/// to the global high/low of the series.
pub fn fibonacci_levels(highs: &[f64], lows: &[f64], lookback: usize) -> FibResult {
    let swings = detect_swing_points(highs, lows, lookback);
    let (anchor_high, anchor_low) = if swings.len() >= 2 {
        let s1 = &swings[swings.len() - 2];
        let s2 = &swings[swings.len() - 1];
        let h = s1.price.max(s2.price);
        let l = s1.price.min(s2.price);
        (h, l)
    } else {
        let h = highs.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let l = lows.iter().cloned().fold(f64::INFINITY, f64::min);
        (h, l)
    };
    let span = anchor_high - anchor_low;
    let levels = FIB_RATIOS
        .iter()
        .map(|&r| FibLevel {
            ratio: r,
            price: anchor_high - span * r,
        })
        .collect();
    FibResult {
        anchor_high,
        anchor_low,
        levels,
    }
}

/// Detect Fibonacci level clusters across multiple swing pairs.
///
/// Groups levels within `threshold_pct` (fraction, e.g. 0.02 = 2%) of each other
/// into confluence zones, sorted by strength (number of overlapping levels).
pub fn fibonacci_confluence(
    highs: &[f64],
    lows: &[f64],
    lookback: usize,
    num_swings: usize,
    threshold_pct: f64,
) -> FibConfluenceResult {
    let swings = detect_swing_points(highs, lows, lookback);
    let mut all_levels: Vec<FibLevel> = Vec::new();
    let num_pairs = num_swings.min(swings.len().saturating_sub(1));
    let start = swings.len().saturating_sub(1).saturating_sub(num_pairs);
    for i in start..swings.len().saturating_sub(1) {
        let h = swings[i].price.max(swings[i + 1].price);
        let l = swings[i].price.min(swings[i + 1].price);
        let span = h - l;
        for &r in &FIB_RATIOS {
            all_levels.push(FibLevel {
                ratio: r,
                price: h - span * r,
            });
        }
    }
    if all_levels.is_empty() {
        return FibConfluenceResult {
            zones: Vec::new(),
            total_levels: 0,
        };
    }
    all_levels.sort_by(|a, b| a.price.partial_cmp(&b.price).unwrap_or(std::cmp::Ordering::Equal));
    let total = all_levels.len();
    let mut zones: Vec<ConfluenceZone> = Vec::new();
    let mut i = 0;
    while i < all_levels.len() {
        let ref_price = all_levels[i].price;
        let mut cluster_ratios = vec![all_levels[i].ratio];
        let mut j = i + 1;
        while j < all_levels.len() {
            let diff = (all_levels[j].price - ref_price).abs();
            if diff / ref_price.abs().max(1e-9) <= threshold_pct {
                cluster_ratios.push(all_levels[j].ratio);
                j += 1;
            } else {
                break;
            }
        }
        if cluster_ratios.len() >= 2 {
            let prices: Vec<f64> = all_levels[i..j].iter().map(|l| l.price).collect();
            let sum: f64 = prices.iter().sum();
            let center = sum / prices.len() as f64;
            let lo = prices.iter().cloned().fold(f64::INFINITY, f64::min);
            let hi = prices.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            zones.push(ConfluenceZone {
                price_center: center,
                price_low: lo,
                price_high: hi,
                strength: cluster_ratios.len(),
                ratios: cluster_ratios,
            });
        }
        i = if j > i + 1 { j } else { i + 1 };
    }
    zones.sort_by(|a, b| b.strength.cmp(&a.strength));
    FibConfluenceResult {
        zones,
        total_levels: total,
    }
}

// ── Harmonic Patterns (XABCD) ─────────────────────────────────────────────

/// Check if value is within [lo - tol, hi + tol].
#[inline]
fn in_fib_range(v: f64, lo: f64, hi: f64, tol: f64) -> bool {
    v >= lo - tol && v <= hi + tol
}

/// Detect XABCD harmonic patterns (Gartley, Bat, Butterfly, Crab) + FEIW + ABCD.
///
/// Uses swing points to find 5-pivot (XABCD) and 4-pivot (ABCD) structures,
/// then validates Fibonacci ratio relationships.
pub fn build_harmonic_patterns(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    lookback: usize,
) -> PatternResult {
    let n = highs.len();
    let swings = detect_swing_points(highs, lows, lookback);
    let mut patterns: Vec<PatternData> = Vec::new();
    let tol = 0.05;

    // XABCD patterns (need 5 pivots)
    if swings.len() >= 5 {
        for idx in 0..swings.len() - 4 {
            let x = &swings[idx];
            let a = &swings[idx + 1];
            let b = &swings[idx + 2];
            let c = &swings[idx + 3];
            let d = &swings[idx + 4];
            let xa = (a.price - x.price).abs();
            let ab = (b.price - a.price).abs();
            let bc = (c.price - b.price).abs();
            let cd = (d.price - c.price).abs();
            if xa < 1e-9 || ab < 1e-9 || bc < 1e-9 {
                continue;
            }
            let ab_xa = ab / xa;
            let bc_ab = bc / ab;
            let cd_bc = cd / bc;
            let ad_xa = (d.price - a.price).abs() / xa;
            let direction = if d.is_high {
                PatternDirection::Bearish
            } else {
                PatternDirection::Bullish
            };

            // Gartley: AB/XA ≈ 0.618, AD/XA ≈ 0.786
            if in_fib_range(ab_xa, 0.618, 0.618, tol)
                && in_fib_range(bc_ab, 0.382, 0.886, tol)
                && in_fib_range(cd_bc, 1.272, 1.618, tol)
                && in_fib_range(ad_xa, 0.786, 0.786, tol)
            {
                patterns.push(PatternData {
                    pattern_type: "gartley",
                    direction,
                    start_idx: x.index,
                    end_idx: d.index,
                    confidence: 0.78,
                    details: vec![
                        ("ab_xa", ab_xa),
                        ("bc_ab", bc_ab),
                        ("cd_bc", cd_bc),
                        ("ad_xa", ad_xa),
                    ],
                });
            }
            // Bat: AB/XA ≈ 0.382-0.50, AD/XA ≈ 0.886
            if in_fib_range(ab_xa, 0.382, 0.50, tol)
                && in_fib_range(bc_ab, 0.382, 0.886, tol)
                && in_fib_range(cd_bc, 1.618, 2.618, tol)
                && in_fib_range(ad_xa, 0.886, 0.886, tol)
            {
                patterns.push(PatternData {
                    pattern_type: "bat",
                    direction,
                    start_idx: x.index,
                    end_idx: d.index,
                    confidence: 0.76,
                    details: vec![
                        ("ab_xa", ab_xa),
                        ("bc_ab", bc_ab),
                        ("cd_bc", cd_bc),
                        ("ad_xa", ad_xa),
                    ],
                });
            }
            // Butterfly: AB/XA ≈ 0.786, AD/XA ≈ 1.272-1.618
            if in_fib_range(ab_xa, 0.786, 0.786, tol)
                && in_fib_range(bc_ab, 0.382, 0.886, tol)
                && in_fib_range(cd_bc, 1.618, 2.618, tol)
                && in_fib_range(ad_xa, 1.272, 1.618, tol)
            {
                patterns.push(PatternData {
                    pattern_type: "butterfly",
                    direction,
                    start_idx: x.index,
                    end_idx: d.index,
                    confidence: 0.74,
                    details: vec![
                        ("ab_xa", ab_xa),
                        ("bc_ab", bc_ab),
                        ("cd_bc", cd_bc),
                        ("ad_xa", ad_xa),
                    ],
                });
            }
            // Crab: AB/XA ≈ 0.382-0.618, AD/XA ≈ 1.618
            if in_fib_range(ab_xa, 0.382, 0.618, tol)
                && in_fib_range(bc_ab, 0.382, 0.886, tol)
                && in_fib_range(cd_bc, 2.24, 3.618, tol)
                && in_fib_range(ad_xa, 1.618, 1.618, tol)
            {
                patterns.push(PatternData {
                    pattern_type: "crab",
                    direction,
                    start_idx: x.index,
                    end_idx: d.index,
                    confidence: 0.72,
                    details: vec![
                        ("ab_xa", ab_xa),
                        ("bc_ab", bc_ab),
                        ("cd_bc", cd_bc),
                        ("ad_xa", ad_xa),
                    ],
                });
            }
        }
    }

    // FEIW: failed breakout/breakdown (3 pivots)
    let feiw_targets: [f64; 8] = [0.382, 0.5, 0.618, 0.786, 0.886, 1.0, 1.272, 1.618];
    if swings.len() >= 3 && !closes.is_empty() {
        let last_close = closes[closes.len() - 1];
        for idx in 0..swings.len() - 2 {
            let p1 = &swings[idx];
            let p2 = &swings[idx + 1];
            let p3 = &swings[idx + 2];
            let ab = (p2.price - p1.price).abs();
            let ac = (p3.price - p1.price).abs();
            let ac_ab = if ab > 1e-9 { ac / ab } else { 0.0 };
            let fib_dist = feiw_targets
                .iter()
                .map(|&f| (ac_ab - f).abs())
                .fold(f64::INFINITY, f64::min);
            if fib_dist > 0.10 {
                continue;
            }
            if p1.is_high && p3.is_high && p3.price > p1.price && last_close < p1.price {
                patterns.push(PatternData {
                    pattern_type: "feiw_failed_breakout",
                    direction: PatternDirection::Bearish,
                    start_idx: p1.index,
                    end_idx: p3.index,
                    confidence: 0.65,
                    details: vec![
                        ("prior_extreme", p1.price),
                        ("breakout_level", p3.price),
                        ("ac_ab_ratio", ac_ab),
                    ],
                });
                break;
            }
            if !p1.is_high && !p3.is_high && p3.price < p1.price && last_close > p1.price {
                patterns.push(PatternData {
                    pattern_type: "feiw_failed_breakdown",
                    direction: PatternDirection::Bullish,
                    start_idx: p1.index,
                    end_idx: p3.index,
                    confidence: 0.65,
                    details: vec![
                        ("prior_extreme", p1.price),
                        ("breakdown_level", p3.price),
                        ("ac_ab_ratio", ac_ab),
                    ],
                });
                break;
            }
        }
    }

    // Legacy ABCD (4-pivot)
    if swings.len() >= 4 {
        let len = swings.len();
        let a = &swings[len - 4];
        let b = &swings[len - 3];
        let c = &swings[len - 2];
        let d = &swings[len - 1];
        let ab = (b.price - a.price).abs();
        let bc = (c.price - b.price).abs();
        let cd = (d.price - c.price).abs();
        if ab > 0.0 && bc > 0.0 {
            let bc_ab = bc / ab;
            let cd_bc = cd / bc;
            if (0.55..=0.78).contains(&bc_ab) && (1.13..=1.9).contains(&cd_bc) {
                let direction = if d.is_high {
                    PatternDirection::Bearish
                } else {
                    PatternDirection::Bullish
                };
                patterns.push(PatternData {
                    pattern_type: "abcd",
                    direction,
                    start_idx: a.index,
                    end_idx: d.index,
                    confidence: 0.74,
                    details: vec![("bc_ab", bc_ab), ("cd_bc", cd_bc)],
                });
            }
        }
    }

    PatternResult {
        scanned_bars: n,
        patterns,
    }
}

// ── TD Timing Patterns ────────────────────────────────────────────────────

/// TD Setup 9 + TDST levels + Countdown 13 + Fibonacci Timing.
///
/// Implements Tom DeMark's Sequential indicator:
/// - Setup: 9 consecutive closes above/below the close 4 bars earlier
/// - TDST: support/resistance level from the setup range
/// - Countdown: 13 bars where close compares to high/low 2 bars earlier
/// - Fibonacci Timing: 8 consecutive bars with close[i] < close[i-5] < close[i-21]
pub fn build_td_timing_patterns(
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
) -> PatternResult {
    let n = closes.len();
    let mut patterns: Vec<PatternData> = Vec::new();
    let mut bull_count: usize = 0;
    let mut bear_count: usize = 0;

    struct Countdown {
        kind_bull: bool,
        start_idx: usize,
        count: usize,
    }
    let mut active_cds: Vec<Countdown> = Vec::new();

    for i in 4..n {
        if closes[i] < closes[i - 4] {
            bull_count += 1;
            bear_count = 0;
        } else if closes[i] > closes[i - 4] {
            bear_count += 1;
            bull_count = 0;
        } else {
            bull_count = 0;
            bear_count = 0;
        }

        // Bullish Setup 9
        if bull_count == 9 {
            let setup_start = i - 8;
            let tdst = closes[setup_start..=i]
                .iter()
                .cloned()
                .fold(f64::INFINITY, f64::min);
            // Perfection: low of bar 8 or 9 < low of bar 6 AND bar 7
            let b6_low = lows[setup_start + 5];
            let b7_low = lows[setup_start + 6];
            let b8_low = lows[setup_start + 7];
            let b9_low = lows[i];
            let perfected = (b8_low < b6_low && b8_low < b7_low)
                || (b9_low < b6_low && b9_low < b7_low);
            patterns.push(PatternData {
                pattern_type: if perfected {
                    "td_setup_9_bullish_perfected"
                } else {
                    "td_setup_9_bullish"
                },
                direction: PatternDirection::Bullish,
                start_idx: setup_start,
                end_idx: i,
                confidence: if perfected { 0.80 } else { 0.73 },
                details: vec![("tdst_level", tdst), ("perfected", if perfected { 1.0 } else { 0.0 })],
            });
            patterns.push(PatternData {
                pattern_type: "tdst_support",
                direction: PatternDirection::Bullish,
                start_idx: setup_start,
                end_idx: i,
                confidence: 0.70,
                details: vec![("level", tdst)],
            });
            active_cds.push(Countdown {
                kind_bull: true,
                start_idx: i,
                count: 0,
            });
            bull_count = 0;
        }

        // Bearish Setup 9
        if bear_count == 9 {
            let setup_start = i - 8;
            let tdst = closes[setup_start..=i]
                .iter()
                .cloned()
                .fold(f64::NEG_INFINITY, f64::max);
            let b6_high = highs[setup_start + 5];
            let b7_high = highs[setup_start + 6];
            let b8_high = highs[setup_start + 7];
            let b9_high = highs[i];
            let perfected = (b8_high > b6_high && b8_high > b7_high)
                || (b9_high > b6_high && b9_high > b7_high);
            patterns.push(PatternData {
                pattern_type: if perfected {
                    "td_setup_9_bearish_perfected"
                } else {
                    "td_setup_9_bearish"
                },
                direction: PatternDirection::Bearish,
                start_idx: setup_start,
                end_idx: i,
                confidence: if perfected { 0.80 } else { 0.73 },
                details: vec![("tdst_level", tdst), ("perfected", if perfected { 1.0 } else { 0.0 })],
            });
            patterns.push(PatternData {
                pattern_type: "tdst_resistance",
                direction: PatternDirection::Bearish,
                start_idx: setup_start,
                end_idx: i,
                confidence: 0.70,
                details: vec![("level", tdst)],
            });
            active_cds.push(Countdown {
                kind_bull: false,
                start_idx: i,
                count: 0,
            });
            bear_count = 0;
        }

        // TD Countdown 13
        if i >= 2 {
            let mut completed_indices = Vec::new();
            for (ci, cd) in active_cds.iter_mut().enumerate() {
                if i <= cd.start_idx {
                    continue;
                }
                if cd.kind_bull {
                    if closes[i] >= highs[i - 2] {
                        cd.count += 1;
                    }
                } else if closes[i] <= lows[i - 2] {
                    cd.count += 1;
                }
                if cd.count >= 13 {
                    let dir = if cd.kind_bull {
                        PatternDirection::Bullish
                    } else {
                        PatternDirection::Bearish
                    };
                    patterns.push(PatternData {
                        pattern_type: if cd.kind_bull {
                            "td_countdown_13_bullish"
                        } else {
                            "td_countdown_13_bearish"
                        },
                        direction: dir,
                        start_idx: cd.start_idx,
                        end_idx: i,
                        confidence: 0.76,
                        details: vec![],
                    });
                    completed_indices.push(ci);
                }
            }
            for &ci in completed_indices.iter().rev() {
                active_cds.remove(ci);
            }
        }
    }

    // Fibonacci Timing Pattern (Kaabar Ch.9)
    if n > 21 {
        let mut fib_bull: usize = 0;
        let mut fib_bear: usize = 0;
        for i in 21..n {
            let c = closes[i];
            let c5 = closes[i - 5];
            let c21 = closes[i - 21];
            if c < c5 && c5 < c21 {
                fib_bull += 1;
                fib_bear = 0;
            } else if c > c5 && c5 > c21 {
                fib_bear += 1;
                fib_bull = 0;
            } else {
                fib_bull = 0;
                fib_bear = 0;
            }
            if fib_bull == 8 {
                patterns.push(PatternData {
                    pattern_type: "fibonacci_timing",
                    direction: PatternDirection::Bullish,
                    start_idx: i - 7,
                    end_idx: i,
                    confidence: 0.71,
                    details: vec![],
                });
                fib_bull = 0;
            }
            if fib_bear == 8 {
                patterns.push(PatternData {
                    pattern_type: "fibonacci_timing",
                    direction: PatternDirection::Bearish,
                    start_idx: i - 7,
                    end_idx: i,
                    confidence: 0.71,
                    details: vec![],
                });
                fib_bear = 0;
            }
        }
    }

    PatternResult {
        scanned_bars: n,
        patterns,
    }
}

// ── Elliott Wave Patterns ─────────────────────────────────────────────────

/// Elliott 5-3 wave pattern with R1-R7 rule validation.
///
/// Rules (Frost & Prechter):
///   R1  — W2 retraces ≤ 100% of W1
///   R1b — W2 retraces 38.2-78.6% of W1
///   R2  — W3 extends beyond W1
///   R3  — W3 is not shortest of W1, W3, W5
///   R4  — W4 does not enter W1 price territory (cardinal, must pass)
///   R5  — W3 ≥ 1.272× W1
///   R5b — W3 ≤ 4.236× W1
///   R6  — ABC correction retraces 38.2-78.6% of impulse
///   R7  — W5 within 0.382-2.618× W1
///
/// Requires 8 swing points (5 impulse + 3 correction).
pub fn build_elliott_wave_patterns(
    highs: &[f64],
    lows: &[f64],
    lookback: usize,
) -> PatternResult {
    let n = highs.len();
    let swings = detect_swing_points(highs, lows, lookback);
    let mut patterns: Vec<PatternData> = Vec::new();

    if swings.len() >= 8 {
        let wave = &swings[swings.len() - 8..];
        let impulse = &wave[..5];
        let correction = &wave[5..];

        let w1 = (impulse[1].price - impulse[0].price).abs();
        let w2 = (impulse[2].price - impulse[1].price).abs();
        let w3 = (impulse[3].price - impulse[2].price).abs();
        let w4 = (impulse[4].price - impulse[3].price).abs();
        let w5 = w4; // W5 approximated as last segment in 5-pivot scheme
        let impulse_span = (impulse[4].price - impulse[0].price).abs();
        let correction_span = (correction[correction.len() - 1].price - correction[0].price).abs();
        let bullish = impulse[4].price > impulse[0].price;

        // R4 gate: cardinal rule — W4 must not overlap W1 territory
        let r4_pass = if bullish {
            impulse[3].price > impulse[0].price
        } else {
            impulse[3].price < impulse[0].price
        };

        if r4_pass {
            let mut rules: Vec<&'static str> = vec!["R4_w4_no_overlap"];

            if w1 > 0.0 && w2 <= w1 {
                rules.push("R1_w2_retrace_valid");
            }
            if w1 > 0.0 && (0.382..=0.786).contains(&(w2 / w1)) {
                rules.push("R1b_w2_fib_quality");
            }
            if w3 > w1 {
                rules.push("R2_w3_gt_w1");
            }
            if w3 >= w1.min(w5) {
                rules.push("R3_w3_not_shortest");
            }
            if w1 > 0.0 && w3 >= 1.272 * w1 {
                rules.push("R5_w3_fib_ext");
            }
            if w1 > 0.0 && w3 <= 4.236 * w1 {
                rules.push("R5b_w3_upper_bound");
            }
            if impulse_span > 0.0 {
                let ratio = correction_span / impulse_span;
                if (0.382..=0.786).contains(&ratio) {
                    rules.push("R6_correction_fib");
                }
            }
            if w1 > 0.0 && (0.382..=2.618).contains(&(w5 / w1)) {
                rules.push("R7_w5_reasonable");
            }

            let confidence = (rules.len() as f64 * 0.10).min(1.0);
            let direction = if bullish {
                PatternDirection::Bullish
            } else {
                PatternDirection::Bearish
            };

            let mut details: Vec<(&'static str, f64)> = vec![
                ("w1", w1),
                ("w2", w2),
                ("w3", w3),
                ("w4", w4),
                ("w5", w5),
                ("rules_passed", rules.len() as f64),
            ];
            if w1 > 0.0 {
                details.push(("w2_w1", w2 / w1));
                details.push(("w3_w1", w3 / w1));
                details.push(("w5_w1", w5 / w1));
            }
            if impulse_span > 0.0 {
                details.push(("correction_retrace", correction_span / impulse_span));
            }

            patterns.push(PatternData {
                pattern_type: "elliott_5_3",
                direction,
                start_idx: wave[0].index,
                end_idx: wave[wave.len() - 1].index,
                confidence,
                details,
            });
        }
    }

    PatternResult {
        scanned_bars: n,
        patterns,
    }
}

// ── Price Patterns (Double Top/Bottom, H&S) ──────────────────────────────

/// Detect structural price patterns: Double Top/Bottom, Head & Shoulders.
///
/// Uses swing points for structural detection. `threshold` is the maximum
/// price difference ratio for matching peaks/troughs (e.g. 0.03 = 3%).
pub fn build_price_patterns(
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    lookback: usize,
    threshold: f64,
) -> PatternResult {
    let n = highs.len();
    let swings = detect_swing_points(highs, lows, lookback);
    let mut patterns: Vec<PatternData> = Vec::new();

    // Double Top / Bottom (pivot-based, 3 pivots)
    if swings.len() >= 3 {
        let len = swings.len();
        let p1 = &swings[len - 3];
        let neckline_p = &swings[len - 2];
        let p3 = &swings[len - 1];
        let price_diff = (p3.price - p1.price).abs() / p1.price.abs().max(1e-9);
        let neckline = neckline_p.price;

        if p1.is_high && p3.is_high && price_diff <= threshold {
            // Double Top — check neckline breakout
            let p3_idx = p3.index;
            let confirmed = closes[p3_idx..]
                .iter()
                .any(|&c| c < neckline);
            patterns.push(PatternData {
                pattern_type: "double_top",
                direction: PatternDirection::Bearish,
                start_idx: p1.index,
                end_idx: p3.index,
                confidence: if confirmed { 0.78 } else { 0.55 },
                details: vec![
                    ("price_diff", price_diff),
                    ("neckline", neckline),
                    ("confirmed", if confirmed { 1.0 } else { 0.0 }),
                ],
            });
        }
        if !p1.is_high && !p3.is_high && price_diff <= threshold {
            let p3_idx = p3.index;
            let confirmed = closes[p3_idx..]
                .iter()
                .any(|&c| c > neckline);
            patterns.push(PatternData {
                pattern_type: "double_bottom",
                direction: PatternDirection::Bullish,
                start_idx: p1.index,
                end_idx: p3.index,
                confidence: if confirmed { 0.78 } else { 0.55 },
                details: vec![
                    ("price_diff", price_diff),
                    ("neckline", neckline),
                    ("confirmed", if confirmed { 1.0 } else { 0.0 }),
                ],
            });
        }
    }

    // Head & Shoulders / Inverse H&S (5 pivots)
    if swings.len() >= 5 {
        for idx in 0..swings.len() - 4 {
            let ls = &swings[idx];
            let lv = &swings[idx + 1];
            let h = &swings[idx + 2];
            let rv = &swings[idx + 3];
            let rs = &swings[idx + 4];

            // Regular H&S: high-low-HIGH-low-high
            if ls.is_high && !lv.is_high && h.is_high && !rv.is_high && rs.is_high {
                let shoulder_diff =
                    (rs.price - ls.price).abs() / ls.price.abs().max(1e-9);
                let neckline_diff =
                    (rv.price - lv.price).abs() / lv.price.abs().max(1e-9);
                if h.price > ls.price
                    && h.price > rs.price
                    && shoulder_diff <= threshold * 2.0
                    && neckline_diff <= threshold * 2.0
                {
                    let neckline_mid = (lv.price + rv.price) / 2.0;
                    let head_height = h.price - neckline_mid;
                    let target = neckline_mid - head_height;
                    patterns.push(PatternData {
                        pattern_type: "head_and_shoulders",
                        direction: PatternDirection::Bearish,
                        start_idx: ls.index,
                        end_idx: rs.index,
                        confidence: 0.72,
                        details: vec![
                            ("neckline_level", neckline_mid),
                            ("target_price", target),
                            ("shoulder_diff", shoulder_diff),
                        ],
                    });
                }
            }

            // Inverse H&S: low-high-LOW-high-low
            if !ls.is_high && lv.is_high && !h.is_high && rv.is_high && !rs.is_high {
                let shoulder_diff =
                    (rs.price - ls.price).abs() / ls.price.abs().max(1e-9);
                let neckline_diff =
                    (rv.price - lv.price).abs() / lv.price.abs().max(1e-9);
                if h.price < ls.price
                    && h.price < rs.price
                    && shoulder_diff <= threshold * 2.0
                    && neckline_diff <= threshold * 2.0
                {
                    let neckline_mid = (lv.price + rv.price) / 2.0;
                    let head_depth = neckline_mid - h.price;
                    let target = neckline_mid + head_depth;
                    patterns.push(PatternData {
                        pattern_type: "inverse_head_and_shoulders",
                        direction: PatternDirection::Bullish,
                        start_idx: ls.index,
                        end_idx: rs.index,
                        confidence: 0.72,
                        details: vec![
                            ("neckline_level", neckline_mid),
                            ("target_price", target),
                            ("shoulder_diff", shoulder_diff),
                        ],
                    });
                }
            }
        }
    }

    PatternResult {
        scanned_bars: n,
        patterns,
    }
}

// ---------------------------------------------------------------------------
// build_candlestick_patterns — aggregates all cdl_* primitives + Kaabar Ch.7
// Mirrors Python: build_candlestick_patterns() in patterns.py
// Cross-module deps: oscillators::rsi, volatility::atr
// ---------------------------------------------------------------------------

/// Aggregate candlestick pattern scanner.
///
/// Runs every single-bar, two-bar, and three-bar candlestick primitive plus
/// the six Kaabar Ch.7 patterns (Bottle, Double Trouble, Extreme Euphoria,
/// R-Pattern, Hidden Shovel, Absolute U-Turn) over the OHLCV data.
pub fn build_candlestick_patterns(
    opens: &[f64],
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    lookback: usize,
) -> PatternResult {
    let n = opens.len().min(highs.len()).min(lows.len()).min(closes.len());
    if n < 2 {
        return PatternResult { scanned_bars: n, patterns: vec![] };
    }
    let start = if lookback > 0 && lookback < n { n - lookback } else { 0 };
    let mut patterns: Vec<PatternData> = Vec::new();

    // --- Single-bar and two-bar patterns (index >= start+1) ---
    for i in (start + 1)..n {
        let (o, h, l, c) = (opens[i], highs[i], lows[i], closes[i]);
        let (po, ph, pl, pc) = (opens[i - 1], highs[i - 1], lows[i - 1], closes[i - 1]);
        let body = (c - o).abs();
        let range = (h - l).max(1e-9);
        let upper_wick = h - o.max(c);
        let lower_wick = o.min(c) - l;
        let body_ratio = body / range;

        // Doji variants
        if body_ratio <= 0.15 {
            if lower_wick > 2.0 * body && upper_wick < 0.1 * range {
                patterns.push(PatternData {
                    pattern_type: "dragonfly_doji",
                    direction: PatternDirection::Bullish,
                    start_idx: i, end_idx: i, confidence: 0.65,
                    details: vec![("body_ratio", body_ratio)],
                });
            } else if upper_wick > 2.0 * body && lower_wick < 0.1 * range {
                patterns.push(PatternData {
                    pattern_type: "gravestone_doji",
                    direction: PatternDirection::Bearish,
                    start_idx: i, end_idx: i, confidence: 0.65,
                    details: vec![("body_ratio", body_ratio)],
                });
            } else {
                patterns.push(PatternData {
                    pattern_type: "doji",
                    direction: PatternDirection::Neutral,
                    start_idx: i, end_idx: i, confidence: 0.64,
                    details: vec![("body_ratio", body_ratio)],
                });
            }
        }

        // Spinning Top
        if body_ratio > 0.15 && body_ratio <= 0.40
            && lower_wick > 0.2 * range && upper_wick > 0.2 * range
        {
            patterns.push(PatternData {
                pattern_type: "spinning_top",
                direction: PatternDirection::Neutral,
                start_idx: i, end_idx: i, confidence: 0.50,
                details: vec![("body_ratio", body_ratio)],
            });
        }

        // Bullish Engulfing
        if c > o && pc < po && c >= po && o <= pc {
            patterns.push(PatternData {
                pattern_type: "bullish_engulfing",
                direction: PatternDirection::Bullish,
                start_idx: i - 1, end_idx: i, confidence: 0.69,
                details: vec![],
            });
        }
        // Bearish Engulfing
        if c < o && pc > po && o >= pc && c <= po {
            patterns.push(PatternData {
                pattern_type: "bearish_engulfing",
                direction: PatternDirection::Bearish,
                start_idx: i - 1, end_idx: i, confidence: 0.69,
                details: vec![],
            });
        }

        // Hammer
        if lower_wick > body * 2.0 && c > o {
            patterns.push(PatternData {
                pattern_type: "hammer",
                direction: PatternDirection::Bullish,
                start_idx: i, end_idx: i, confidence: 0.62,
                details: vec![],
            });
        }
        // Shooting Star
        if upper_wick > body * 2.0 && c < o {
            patterns.push(PatternData {
                pattern_type: "shooting_star",
                direction: PatternDirection::Bearish,
                start_idx: i, end_idx: i, confidence: 0.62,
                details: vec![],
            });
        }

        // Piercing Line
        let prev_bearish = pc < po;
        let cur_bullish = c > o;
        if prev_bearish && cur_bullish {
            let prev_mid = (po + pc) / 2.0;
            if o < pl && c > prev_mid {
                patterns.push(PatternData {
                    pattern_type: "piercing_line",
                    direction: PatternDirection::Bullish,
                    start_idx: i - 1, end_idx: i, confidence: 0.67,
                    details: vec![],
                });
            }
        }

        // Dark Cloud Cover
        let prev_bullish = pc > po;
        let cur_bearish = c < o;
        if prev_bullish && cur_bearish {
            let prev_mid = (po + pc) / 2.0;
            if o > ph && c < prev_mid {
                patterns.push(PatternData {
                    pattern_type: "dark_cloud_cover",
                    direction: PatternDirection::Bearish,
                    start_idx: i - 1, end_idx: i, confidence: 0.67,
                    details: vec![],
                });
            }
        }
    }

    // --- Three-bar patterns ---
    for i in (start + 2)..n {
        let b0_body = (closes[i - 2] - opens[i - 2]).abs();
        let b0_range = (highs[i - 2] - lows[i - 2]).max(1e-9);
        let b1_body = (closes[i - 1] - opens[i - 1]).abs();
        let b1_range = (highs[i - 1] - lows[i - 1]).max(1e-9);
        let b2_body = (closes[i] - opens[i]).abs();

        let b0_bear = closes[i - 2] < opens[i - 2];
        let b0_bull = closes[i - 2] > opens[i - 2];
        let b1_small = b1_body <= 0.3 * b1_range;
        let b2_bull = closes[i] > opens[i];
        let b2_bear = closes[i] < opens[i];
        let b0_mid = (opens[i - 2] + closes[i - 2]) / 2.0;

        // Morning Star
        if b0_bear && b0_body >= 0.5 * b0_range && b1_small && b2_bull && closes[i] > b0_mid {
            patterns.push(PatternData {
                pattern_type: "morning_star",
                direction: PatternDirection::Bullish,
                start_idx: i - 2, end_idx: i, confidence: 0.75,
                details: vec![],
            });
        }

        // Evening Star
        if b0_bull && b0_body >= 0.5 * b0_range && b1_small && b2_bear && closes[i] < b0_mid {
            patterns.push(PatternData {
                pattern_type: "evening_star",
                direction: PatternDirection::Bearish,
                start_idx: i - 2, end_idx: i, confidence: 0.75,
                details: vec![],
            });
        }

        // Three White Soldiers
        let b1_bull = closes[i - 1] > opens[i - 1];
        if b0_bull && b1_bull && b2_bull
            && closes[i - 1] > closes[i - 2] && closes[i] > closes[i - 1]
            && opens[i - 1] > opens[i - 2] && opens[i] > opens[i - 1]
            && closes[i] >= opens[i] + 0.7 * b2_body
        {
            patterns.push(PatternData {
                pattern_type: "three_white_soldiers",
                direction: PatternDirection::Bullish,
                start_idx: i - 2, end_idx: i, confidence: 0.72,
                details: vec![],
            });
        }

        // Three Black Crows
        let b1_bear = closes[i - 1] < opens[i - 1];
        if b0_bear && b1_bear && b2_bear
            && closes[i - 1] < closes[i - 2] && closes[i] < closes[i - 1]
            && opens[i - 1] < opens[i - 2] && opens[i] < opens[i - 1]
            && closes[i] <= opens[i] - 0.7 * b2_body
        {
            patterns.push(PatternData {
                pattern_type: "three_black_crows",
                direction: PatternDirection::Bearish,
                start_idx: i - 2, end_idx: i, confidence: 0.72,
                details: vec![],
            });
        }

        // Bottle — Kaabar Ch.7: 2-bar momentum continuation (uses i-1, i)
        let wick_tol = 0.02 * (highs[i] - lows[i]).max(1e-9);
        let b1_bull_f = closes[i - 1] > opens[i - 1];
        let b1_bear_f = closes[i - 1] < opens[i - 1];
        let b2_bull_f = closes[i] > opens[i];
        let b2_bear_f = closes[i] < opens[i];
        if b1_bull_f && b2_bull_f {
            let no_lower_wick = (opens[i] - lows[i]) <= wick_tol;
            let gap_lower = opens[i] < closes[i - 1];
            if no_lower_wick && gap_lower {
                patterns.push(PatternData {
                    pattern_type: "bottle",
                    direction: PatternDirection::Bullish,
                    start_idx: i - 1, end_idx: i, confidence: 0.62,
                    details: vec![],
                });
            }
        }
        if b1_bear_f && b2_bear_f {
            let no_upper_wick = (highs[i] - opens[i]) <= wick_tol;
            let gap_higher = opens[i] > closes[i - 1];
            if no_upper_wick && gap_higher {
                patterns.push(PatternData {
                    pattern_type: "bottle",
                    direction: PatternDirection::Bearish,
                    start_idx: i - 1, end_idx: i, confidence: 0.62,
                    details: vec![],
                });
            }
        }
    }

    // --- Double Trouble — Kaabar Ch.7: ATR-filtered 2-bar momentum ---
    let atr_values = super::volatility::atr(highs, lows, closes, 14);
    for i in (start + 1)..n {
        let cur_body = (closes[i] - opens[i]).abs();
        let prev_atr = if i > 0 { atr_values[i - 1] } else { 0.0 };
        if prev_atr <= 0.0 { continue; }
        let cur_bull = closes[i] > opens[i];
        let prev_bull = closes[i - 1] > opens[i - 1];
        let cur_bear = closes[i] < opens[i];
        let prev_bear = closes[i - 1] < opens[i - 1];
        if cur_bull && prev_bull && closes[i] > closes[i - 1] && cur_body > 2.0 * prev_atr {
            patterns.push(PatternData {
                pattern_type: "double_trouble",
                direction: PatternDirection::Bullish,
                start_idx: i - 1, end_idx: i, confidence: 0.68,
                details: vec![("body_atr_ratio", cur_body / prev_atr)],
            });
        } else if cur_bear && prev_bear && closes[i] < closes[i - 1] && cur_body > 2.0 * prev_atr {
            patterns.push(PatternData {
                pattern_type: "double_trouble",
                direction: PatternDirection::Bearish,
                start_idx: i - 1, end_idx: i, confidence: 0.68,
                details: vec![("body_atr_ratio", cur_body / prev_atr)],
            });
        }
    }

    // --- Extreme Euphoria — Kaabar Ch.7: 5-bar exhaustion reversal ---
    if n >= 5 {
        for i in (start.max(4))..n {
            let bodies: Vec<f64> = (0..5).map(|k| (closes[i - 4 + k] - opens[i - 4 + k]).abs()).collect();
            let all_bearish = (0..5).all(|k| closes[i - 4 + k] < opens[i - 4 + k]);
            let all_bullish = (0..5).all(|k| closes[i - 4 + k] > opens[i - 4 + k]);
            let increasing = bodies[4] > bodies[3] && bodies[3] > bodies[2];
            if all_bearish && increasing {
                patterns.push(PatternData {
                    pattern_type: "extreme_euphoria",
                    direction: PatternDirection::Bullish,
                    start_idx: i - 4, end_idx: i, confidence: 0.63,
                    details: vec![
                        ("body_3", bodies[2]), ("body_4", bodies[3]), ("body_5", bodies[4]),
                    ],
                });
            } else if all_bullish && increasing {
                patterns.push(PatternData {
                    pattern_type: "extreme_euphoria",
                    direction: PatternDirection::Bearish,
                    start_idx: i - 4, end_idx: i, confidence: 0.63,
                    details: vec![
                        ("body_3", bodies[2]), ("body_4", bodies[3]), ("body_5", bodies[4]),
                    ],
                });
            }
        }
    }

    // --- R-Pattern — Kaabar Ch.7: 4-bar RSI-filtered reversal ---
    let rsi_close = super::oscillators::rsi(closes, 14);
    if n >= 4 {
        for i in (start.max(3))..n {
            let rsi_val = rsi_close[i];
            // Bullish R: V-shape lows, rising closes, RSI < 50
            let v_lows = lows[i - 2] < lows[i - 3] && lows[i - 1] > lows[i - 2] && lows[i] > lows[i - 1];
            let rising_closes = closes[i - 2] > closes[i - 3] && closes[i - 1] > closes[i - 2] && closes[i] > closes[i - 1];
            if v_lows && rising_closes && rsi_val < 50.0 {
                patterns.push(PatternData {
                    pattern_type: "r_pattern",
                    direction: PatternDirection::Bullish,
                    start_idx: i - 3, end_idx: i, confidence: 0.70,
                    details: vec![("rsi", rsi_val)],
                });
            }
            // Bearish R: inverse V highs, falling closes, RSI > 50
            let v_highs = highs[i - 2] > highs[i - 3] && highs[i - 1] < highs[i - 2] && highs[i] < highs[i - 1];
            let falling_closes = closes[i - 2] < closes[i - 3] && closes[i - 1] < closes[i - 2] && closes[i] < closes[i - 1];
            if v_highs && falling_closes && rsi_val > 50.0 {
                patterns.push(PatternData {
                    pattern_type: "r_pattern",
                    direction: PatternDirection::Bearish,
                    start_idx: i - 3, end_idx: i, confidence: 0.70,
                    details: vec![("rsi", rsi_val)],
                });
            }
        }
    }

    // --- Hidden Shovel — Kaabar Ch.7: CARSI pattern ---
    let rsi_open = super::oscillators::rsi(opens, 14);
    let rsi_high = super::oscillators::rsi(highs, 14);
    let rsi_low = super::oscillators::rsi(lows, 14);
    // rsi_close already computed above
    for i in (start + 1)..n {
        let (ro, rh, rl, rc) = (rsi_open[i], rsi_high[i], rsi_low[i], rsi_close[i]);
        let rl_prev = rsi_low[i - 1];
        let rh_prev = rsi_high[i - 1];
        // Bullish Hidden Shovel
        if rl < 30.0 && ro > 30.0 && rh > 30.0 && rc > 30.0 && rl_prev > 30.0 {
            patterns.push(PatternData {
                pattern_type: "hidden_shovel",
                direction: PatternDirection::Bullish,
                start_idx: i - 1, end_idx: i, confidence: 0.66,
                details: vec![("rsi_low", rl), ("rsi_close", rc)],
            });
        }
        // Bearish Hidden Shovel
        if rh > 70.0 && ro < 70.0 && rl < 70.0 && rc < 70.0 && rh_prev < 70.0 {
            patterns.push(PatternData {
                pattern_type: "hidden_shovel",
                direction: PatternDirection::Bearish,
                start_idx: i - 1, end_idx: i, confidence: 0.66,
                details: vec![("rsi_high", rh), ("rsi_close", rc)],
            });
        }
    }

    // --- Absolute U-Turn — Kaabar Ch.7: CARSI pattern ---
    if n >= 6 {
        for i in (start.max(5))..n {
            if rsi_low[i] > 20.0 && (1..=5).all(|k| rsi_low[i - k] < 20.0) {
                patterns.push(PatternData {
                    pattern_type: "absolute_u_turn",
                    direction: PatternDirection::Bullish,
                    start_idx: i - 5, end_idx: i, confidence: 0.72,
                    details: vec![("rsi_low_current", rsi_low[i])],
                });
            }
            if rsi_high[i] < 80.0 && (1..=5).all(|k| rsi_high[i - k] > 80.0) {
                patterns.push(PatternData {
                    pattern_type: "absolute_u_turn",
                    direction: PatternDirection::Bearish,
                    start_idx: i - 5, end_idx: i, confidence: 0.72,
                    details: vec![("rsi_high_current", rsi_high[i])],
                });
            }
        }
    }

    // Cap at 50 results (same as Python)
    patterns.truncate(50);
    PatternResult {
        scanned_bars: n,
        patterns,
    }
}

// ── Rolling Window Swing Detection ──────────────────────────────────────────

/// Rolling window swing detection with boundary pivots and deduplication.
///
/// For each bar in `window..(n-window)`, checks if it is a local extremum
/// within the full `2*window+1` neighbourhood. Also emits boundary pivots
/// at index 0 and n-1 using partial windows. Consecutive same-direction
/// pivots are deduplicated by keeping the more extreme value.
pub fn detect_swings(highs: &[f64], lows: &[f64], window: usize) -> Vec<SwingPoint> {
    let n = highs.len();
    if n == 0 {
        return Vec::new();
    }
    if n == 1 {
        return vec![SwingPoint { index: 0, price: highs[0], is_high: true }];
    }

    let mut raw: Vec<SwingPoint> = Vec::new();

    // Interior points
    for i in window..(n.saturating_sub(window)) {
        let lo = if i >= window { i - window } else { 0 };
        let hi = (i + window).min(n - 1);

        // Check swing high: highs[i] must be strictly greater than all surrounding highs
        let mut is_high = true;
        for j in lo..=hi {
            if j != i && highs[j] >= highs[i] {
                is_high = false;
                break;
            }
        }

        // Check swing low: lows[i] must be strictly less than all surrounding lows
        let mut is_low = true;
        for j in lo..=hi {
            if j != i && lows[j] <= lows[i] {
                is_low = false;
                break;
            }
        }

        if is_high {
            raw.push(SwingPoint { index: i, price: highs[i], is_high: true });
        }
        if is_low {
            raw.push(SwingPoint { index: i, price: lows[i], is_high: false });
        }
    }

    // Boundary pivots (index 0 and n-1) with partial windows
    // Index 0
    {
        let end = window.min(n - 1);
        let mut is_high = true;
        let mut is_low = true;
        for j in 1..=end {
            if highs[j] >= highs[0] { is_high = false; }
            if lows[j] <= lows[0] { is_low = false; }
        }
        if is_high {
            raw.push(SwingPoint { index: 0, price: highs[0], is_high: true });
        }
        if is_low {
            raw.push(SwingPoint { index: 0, price: lows[0], is_high: false });
        }
    }
    // Index n-1
    if n > 1 {
        let start = if n - 1 >= window { n - 1 - window } else { 0 };
        let mut is_high = true;
        let mut is_low = true;
        for j in start..(n - 1) {
            if highs[j] >= highs[n - 1] { is_high = false; }
            if lows[j] <= lows[n - 1] { is_low = false; }
        }
        if is_high {
            raw.push(SwingPoint { index: n - 1, price: highs[n - 1], is_high: true });
        }
        if is_low {
            raw.push(SwingPoint { index: n - 1, price: lows[n - 1], is_high: false });
        }
    }

    // Sort by index
    raw.sort_by_key(|s| s.index);

    // Dedup: consecutive same-direction pivots keep the more extreme one
    let mut result: Vec<SwingPoint> = Vec::with_capacity(raw.len());
    for sp in raw {
        if let Some(last) = result.last_mut() {
            if last.is_high == sp.is_high {
                // Same direction — keep more extreme
                if sp.is_high {
                    if sp.price > last.price {
                        *last = sp;
                    }
                } else if sp.price < last.price {
                    *last = sp;
                }
                continue;
            }
        }
        result.push(sp);
    }
    result
}

// ── 3-Bar Close-Based Turning Pivots ────────────────────────────────────────

/// 3-bar close-based reversal detection.
///
/// For each bar `i` in `1..(n-1)`:
/// - High pivot if `(close[i] >= close[i-1] && close[i] > close[i+1])` OR
///   `(close[i] > close[i-1] && close[i] >= close[i+1])`.
/// - Low pivot uses mirror logic.
/// Boundary points at index 0 and n-1 are always included.
/// Price = highs[i] for high pivots, lows[i] for low pivots.
/// Consecutive same-direction pivots are deduplicated (keep more extreme).
pub fn detect_close_turning_pivots(
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
) -> Vec<SwingPoint> {
    let n = closes.len();
    if n == 0 {
        return Vec::new();
    }
    if n == 1 {
        return vec![SwingPoint { index: 0, price: highs[0], is_high: true }];
    }

    let mut raw: Vec<SwingPoint> = Vec::new();

    // Boundary: index 0
    raw.push(SwingPoint { index: 0, price: highs[0], is_high: true });

    // Interior 3-bar detection
    for i in 1..(n - 1) {
        let prev = closes[i - 1];
        let curr = closes[i];
        let next = closes[i + 1];

        // High pivot
        let is_high = (curr >= prev && curr > next) || (curr > prev && curr >= next);
        // Low pivot
        let is_low = (curr <= prev && curr < next) || (curr < prev && curr <= next);

        if is_high {
            raw.push(SwingPoint { index: i, price: highs[i], is_high: true });
        }
        if is_low {
            raw.push(SwingPoint { index: i, price: lows[i], is_high: false });
        }
    }

    // Boundary: index n-1
    raw.push(SwingPoint { index: n - 1, price: lows[n - 1], is_high: false });

    // Dedup: consecutive same-direction pivots keep the more extreme one
    let mut result: Vec<SwingPoint> = Vec::with_capacity(raw.len());
    for sp in raw {
        if let Some(last) = result.last_mut() {
            if last.is_high == sp.is_high {
                if sp.is_high {
                    if sp.price > last.price {
                        *last = sp;
                    }
                } else if sp.price < last.price {
                    *last = sp;
                }
                continue;
            }
        }
        result.push(sp);
    }
    result
}

// ── Marubozu ──────────────────────────────────────────────────────────────────

/// Marubozu pattern detection — single bar.
///
/// A Marubozu is a strong candle with minimal shadows — body takes up most of the range.
///
/// Returns 1.0 if bullish (close > open), -1.0 if bearish (close < open), 0.0 if no pattern.
///
/// # Arguments
/// * `body_pct` — minimum body/range ratio to qualify (e.g. 0.95)
#[inline]
pub fn cdl_marubozu_inc(
    open: f64, high: f64, low: f64, close: f64,
    body_pct: f64,
) -> f64 {
    let rng = range(high, low);
    if rng <= 0.0 {
        return 0.0;
    }
    let body = real_body(open, close);
    if body / rng >= body_pct {
        if close > open { 1.0 } else { -1.0 }
    } else {
        0.0
    }
}

/// Marubozu pattern detection — full series.
pub fn cdl_marubozu(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
    body_pct: f64,
) -> Vec<f64> {
    (0..opens.len())
        .map(|i| cdl_marubozu_inc(opens[i], highs[i], lows[i], closes[i], body_pct))
        .collect()
}

// ── Long Shadow ──────────────────────────────────────────────────────────────

/// Long shadow pattern detection — single bar.
///
/// Detects candles with a long shadow relative to the body.
/// The body must be small relative to the total range, and the dominant shadow
/// must be at least `shadow_ratio` times the body size.
///
/// Returns 1.0 if long lower shadow (bullish), -1.0 if long upper shadow (bearish), 0.0 none.
///
/// # Arguments
/// * `shadow_ratio` — minimum max_shadow/body ratio (e.g. 2.0)
#[inline]
pub fn cdl_long_shadow_inc(
    open: f64, high: f64, low: f64, close: f64,
    shadow_ratio: f64,
) -> f64 {
    let rng = range(high, low);
    if rng <= 0.0 {
        return 0.0;
    }
    let body = real_body(open, close);
    if body < 1e-14 {
        return 0.0;
    }
    let up = upper_shadow(high, open, close);
    let dn = lower_shadow(low, open, close);
    let max_shadow = up.max(dn);

    // Body must be small relative to range (less than half)
    if body > rng * 0.5 {
        return 0.0;
    }

    if max_shadow / body >= shadow_ratio {
        if dn > up { 1.0 } else { -1.0 }
    } else {
        0.0
    }
}

/// Long shadow pattern detection — full series.
pub fn cdl_long_shadow(
    opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64],
    shadow_ratio: f64,
) -> Vec<f64> {
    (0..opens.len())
        .map(|i| cdl_long_shadow_inc(opens[i], highs[i], lows[i], closes[i], shadow_ratio))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    // ── Doji ───────────────────────────────────────────────────────────

    #[test]
    fn doji_perfect() {
        // Perfect doji: open == close, equal shadows
        let signal = cdl_doji_inc(100.0, 105.0, 95.0, 100.0, 5.0, 100.0);
        assert_eq!(signal, 1);
    }

    #[test]
    fn doji_not_doji() {
        // Large body — not a doji
        let signal = cdl_doji_inc(95.0, 105.0, 94.0, 104.0, 5.0, 100.0);
        assert_eq!(signal, 0);
    }

    #[test]
    fn doji_batch_matches_inc() {
        let opens = vec![100.0, 95.0, 100.0, 98.0];
        let highs = vec![105.0, 105.0, 110.0, 102.0];
        let lows = vec![95.0, 94.0, 90.0, 97.5];
        let closes = vec![100.0, 104.0, 100.5, 98.1];

        let batch = cdl_doji(&opens, &highs, &lows, &closes, 5.0, 100.0);
        for i in 0..opens.len() {
            let inc = cdl_doji_inc(opens[i], highs[i], lows[i], closes[i], 5.0, 100.0);
            assert_eq!(batch[i], inc, "mismatch at bar {i}");
        }
    }

    // ── Hammer ─────────────────────────────────────────────────────────

    #[test]
    fn hammer_classic() {
        // Small body at top, long lower shadow
        // O=102, H=103, L=95, C=103 → body=1, upper=0, lower=7
        let signal = cdl_hammer_inc(102.0, 103.0, 95.0, 103.0, 35.0, 2.0);
        assert_eq!(signal, 1);
    }

    #[test]
    fn hammer_not_hammer_large_upper() {
        // Upper shadow too large
        let signal = cdl_hammer_inc(100.0, 110.0, 95.0, 101.0, 35.0, 2.0);
        assert_eq!(signal, 0);
    }

    #[test]
    fn hammer_batch_matches_inc() {
        let opens = vec![102.0, 100.0, 99.0, 101.0];
        let highs = vec![103.0, 110.0, 100.0, 102.0];
        let lows = vec![95.0, 95.0, 92.0, 94.0];
        let closes = vec![103.0, 101.0, 99.5, 101.5];

        let batch = cdl_hammer(&opens, &highs, &lows, &closes, 35.0, 2.0);
        for i in 0..opens.len() {
            let inc = cdl_hammer_inc(opens[i], highs[i], lows[i], closes[i], 35.0, 2.0);
            assert_eq!(batch[i], inc, "mismatch at bar {i}");
        }
    }

    // ── Inverted Hammer ────────────────────────────────────────────────

    #[test]
    fn inverted_hammer_classic() {
        // Small body at bottom, long upper shadow
        // O=96, H=105, L=95, C=96 → body=0 (not valid — need body > 0)
        // Use: O=95.5, H=105, L=95, C=96 → body=0.5, upper=9, lower=0.5
        // body_pct check: 0.5 / 10 * 100 = 5% < 35% ✓
        // upper >= factor * body: 9 >= 2*0.5 = 1 ✓
        // lower <= body: 0.5 <= 0.5 ✓
        // max(O,C) < midpoint: 96 < 100 ✓
        let signal = cdl_inverted_hammer_inc(95.5, 105.0, 95.0, 96.0, 35.0, 2.0);
        assert_eq!(signal, 1);
    }

    #[test]
    fn inverted_hammer_body_at_top() {
        // Body at the top — should not trigger
        let signal = cdl_inverted_hammer_inc(104.0, 105.0, 95.0, 103.0, 35.0, 2.0);
        assert_eq!(signal, 0);
    }

    #[test]
    fn inverted_hammer_batch_matches_inc() {
        let opens = vec![95.5, 104.0, 96.0, 97.0];
        let highs = vec![105.0, 105.0, 106.0, 108.0];
        let lows = vec![95.0, 95.0, 95.5, 96.5];
        let closes = vec![96.0, 103.0, 96.5, 97.5];

        let batch = cdl_inverted_hammer(&opens, &highs, &lows, &closes, 35.0, 2.0);
        for i in 0..opens.len() {
            let inc = cdl_inverted_hammer_inc(opens[i], highs[i], lows[i], closes[i], 35.0, 2.0);
            assert_eq!(batch[i], inc, "mismatch at bar {i}");
        }
    }

    // ── Dragonfly Doji ─────────────────────────────────────────────────

    #[test]
    fn dragonfly_doji_classic() {
        // Tiny body at top, no upper shadow, long lower shadow
        // O=100.0, H=100.2, L=93.0, C=100.0 → range=7.2, body=0, up=0.2, dn=7
        let signal = cdl_dragonfly_doji_inc(100.0, 100.2, 93.0, 100.0, 5.0, 5.0);
        assert_eq!(signal, 1);
    }

    #[test]
    fn dragonfly_doji_not_dragonfly() {
        // Long upper shadow — not a dragonfly
        let signal = cdl_dragonfly_doji_inc(100.0, 108.0, 95.0, 100.0, 5.0, 5.0);
        assert_eq!(signal, 0);
    }

    #[test]
    fn dragonfly_doji_batch_matches_inc() {
        let opens = vec![100.0, 100.0, 98.0, 99.0];
        let highs = vec![100.2, 108.0, 98.5, 99.3];
        let lows = vec![93.0, 95.0, 91.0, 95.0];
        let closes = vec![100.0, 100.0, 98.2, 99.1];

        let batch = cdl_dragonfly_doji(&opens, &highs, &lows, &closes, 5.0, 5.0);
        for i in 0..opens.len() {
            let inc = cdl_dragonfly_doji_inc(opens[i], highs[i], lows[i], closes[i], 5.0, 5.0);
            assert_eq!(batch[i], inc, "mismatch at bar {i}");
        }
    }

    // ── Gravestone Doji ────────────────────────────────────────────────

    #[test]
    fn gravestone_doji_classic() {
        // Tiny body at bottom, no lower shadow, long upper shadow
        // O=95.0, H=102.0, L=94.8, C=95.0 → range=7.2, body=0, dn=0.2, up=7
        let signal = cdl_gravestone_doji_inc(95.0, 102.0, 94.8, 95.0, 5.0, 5.0);
        assert_eq!(signal, -1);
    }

    #[test]
    fn gravestone_doji_not_gravestone() {
        // Long lower shadow — not a gravestone
        let signal = cdl_gravestone_doji_inc(100.0, 108.0, 92.0, 100.0, 5.0, 5.0);
        assert_eq!(signal, 0);
    }

    #[test]
    fn gravestone_doji_batch_matches_inc() {
        let opens = vec![95.0, 100.0, 96.0, 98.0];
        let highs = vec![102.0, 108.0, 103.0, 105.0];
        let lows = vec![94.8, 92.0, 95.5, 97.5];
        let closes = vec![95.0, 100.0, 96.2, 98.1];

        let batch = cdl_gravestone_doji(&opens, &highs, &lows, &closes, 5.0, 5.0);
        for i in 0..opens.len() {
            let inc = cdl_gravestone_doji_inc(opens[i], highs[i], lows[i], closes[i], 5.0, 5.0);
            assert_eq!(batch[i], inc, "mismatch at bar {i}");
        }
    }

    // ── Edge cases ─────────────────────────────────────────────────────

    #[test]
    fn flat_bar_no_pattern() {
        // Zero range → no pattern possible
        assert_eq!(cdl_doji_inc(100.0, 100.0, 100.0, 100.0, 5.0, 100.0), 0);
        assert_eq!(cdl_hammer_inc(100.0, 100.0, 100.0, 100.0, 35.0, 2.0), 0);
        assert_eq!(cdl_inverted_hammer_inc(100.0, 100.0, 100.0, 100.0, 35.0, 2.0), 0);
        assert_eq!(cdl_dragonfly_doji_inc(100.0, 100.0, 100.0, 100.0, 5.0, 5.0), 0);
        assert_eq!(cdl_gravestone_doji_inc(100.0, 100.0, 100.0, 100.0, 5.0, 5.0), 0);
    }

    // ── Spinning Top ──────────────────────────────────────────────────

    #[test]
    fn spinning_top_detected() {
        // body ~25% of range, both shadows > 20%
        // O=98, H=105, L=95, C=101 → range=10, body=3 (30%), upper=4 (40%), lower=3 (30%)
        let signal = cdl_spinning_top_inc(98.0, 105.0, 95.0, 101.0);
        assert_eq!(signal, 1);
    }

    #[test]
    fn spinning_top_not_detected() {
        // Large body, no shadows
        let signal = cdl_spinning_top_inc(95.0, 105.0, 95.0, 105.0);
        assert_eq!(signal, 0);
    }

    // ── Engulfing ─────────────────────────────────────────────────────

    #[test]
    fn bullish_engulfing() {
        let opens = vec![105.0, 98.0];
        let highs = vec![106.0, 107.0];
        let lows = vec![99.0, 97.0];
        let closes = vec![100.0, 106.0]; // prev bearish, cur bullish engulfs
        let result = cdl_engulfing(&opens, &highs, &lows, &closes);
        assert_eq!(result[1], 1);
    }

    #[test]
    fn bearish_engulfing() {
        let opens = vec![95.0, 107.0];
        let highs = vec![106.0, 108.0];
        let lows = vec![94.0, 93.0];
        let closes = vec![105.0, 94.0]; // prev bullish, cur bearish engulfs
        let result = cdl_engulfing(&opens, &highs, &lows, &closes);
        assert_eq!(result[1], -1);
    }

    // ── Piercing Line ─────────────────────────────────────────────────

    #[test]
    fn piercing_line_detected() {
        // Prev: bearish (O=105, C=100), Cur: opens below prev low, closes above prev mid
        let opens = vec![105.0, 94.0];
        let highs = vec![106.0, 104.0];
        let lows = vec![99.0, 93.0];
        let closes = vec![100.0, 103.0]; // prev mid = 102.5, close > 102.5 ✓
        let result = cdl_piercing_line(&opens, &highs, &lows, &closes);
        assert_eq!(result[1], 1);
    }

    // ── Dark Cloud Cover ──────────────────────────────────────────────

    #[test]
    fn dark_cloud_detected() {
        // Prev: bullish (O=95, C=105), Cur: opens above prev high, closes below prev mid
        let opens = vec![95.0, 107.0];
        let highs = vec![106.0, 108.0];
        let lows = vec![94.0, 98.0];
        let closes = vec![105.0, 99.0]; // prev mid = 100, close < 100 ✓
        let result = cdl_dark_cloud_cover(&opens, &highs, &lows, &closes);
        assert_eq!(result[1], -1);
    }

    // ── Morning Star ──────────────────────────────────────────────────

    #[test]
    fn morning_star_detected() {
        // Bar0: large bearish, Bar1: small body, Bar2: large bullish above Bar0 mid
        let opens = vec![110.0, 100.5, 101.0];
        let highs = vec![111.0, 101.0, 108.0];
        let lows = vec![99.0, 99.5, 100.5];
        let closes = vec![100.0, 100.8, 107.0]; // b0 mid=105, b2 close=107 > 105 ✓
        let result = cdl_morning_star(&opens, &highs, &lows, &closes);
        assert_eq!(result[2], 1);
    }

    // ── Evening Star ──────────────────────────────────────────────────

    #[test]
    fn evening_star_detected() {
        let opens = vec![95.0, 106.0, 105.0];
        let highs = vec![107.0, 107.0, 106.0];
        let lows = vec![94.0, 105.5, 97.0];
        let closes = vec![106.0, 106.2, 98.0]; // b0 mid=100.5, b2 close=98 < 100.5 ✓
        let result = cdl_evening_star(&opens, &highs, &lows, &closes);
        assert_eq!(result[2], -1);
    }

    // ── Three White Soldiers ──────────────────────────────────────────

    #[test]
    fn three_white_soldiers_detected() {
        let opens = vec![100.0, 102.0, 104.0];
        let highs = vec![103.0, 105.0, 107.0];
        let lows = vec![99.0, 101.0, 103.0];
        let closes = vec![102.0, 104.0, 106.0];
        let result = cdl_three_white_soldiers(&opens, &highs, &lows, &closes);
        assert_eq!(result[2], 1);
    }

    // ── Three Black Crows ─────────────────────────────────────────────

    #[test]
    fn three_black_crows_detected() {
        let opens = vec![106.0, 104.0, 102.0];
        let highs = vec![107.0, 105.0, 103.0];
        let lows = vec![103.0, 101.0, 99.0];
        let closes = vec![104.0, 102.0, 100.0];
        let result = cdl_three_black_crows(&opens, &highs, &lows, &closes);
        assert_eq!(result[2], -1);
    }

    // ── Pivot Points ──────────────────────────────────────────────────

    #[test]
    fn pivot_classic_known_values() {
        let pp = pivot_points_classic(110.0, 90.0, 100.0);
        assert_abs_diff_eq!(pp.pp, 100.0, epsilon = 1e-9);
        // R1 = 2*100 - 90 = 110
        let r1 = pp.levels.iter().find(|(k, _)| k == "r1").unwrap().1;
        assert_abs_diff_eq!(r1, 110.0, epsilon = 1e-9);
        // S1 = 2*100 - 110 = 90
        let s1 = pp.levels.iter().find(|(k, _)| k == "s1").unwrap().1;
        assert_abs_diff_eq!(s1, 90.0, epsilon = 1e-9);
    }

    #[test]
    fn pivot_fibonacci_r1_s1_symmetric() {
        let pp = pivot_points_fibonacci(110.0, 90.0, 100.0);
        let r1 = pp.levels.iter().find(|(k, _)| k == "r1").unwrap().1;
        let s1 = pp.levels.iter().find(|(k, _)| k == "s1").unwrap().1;
        // R1 - PP == PP - S1 (symmetric around PP)
        assert_abs_diff_eq!(r1 - pp.pp, pp.pp - s1, epsilon = 1e-9);
    }

    #[test]
    fn pivot_camarilla_levels_count() {
        let pp = pivot_points_camarilla(110.0, 90.0, 100.0);
        assert_eq!(pp.levels.len(), 8); // h1-h4 + l1-l4
    }

    // ── ZigZag ────────────────────────────────────────────────────────

    #[test]
    fn zigzag_basic() {
        // Clear up-down-up pattern
        let highs = vec![105.0, 110.0, 115.0, 108.0, 102.0, 100.0, 105.0, 112.0, 118.0];
        let lows = vec![95.0, 100.0, 105.0, 100.0, 95.0, 90.0, 95.0, 102.0, 108.0];
        let pivots = zigzag(&highs, &lows, 5.0);
        assert!(!pivots.is_empty(), "should detect pivots");
    }

    #[test]
    fn zigzag_short_input() {
        let pivots = zigzag(&[100.0], &[95.0], 5.0);
        assert!(pivots.is_empty());
    }

    #[test]
    fn zigzag_alternates_high_low() {
        let highs: Vec<f64> = (0..50).map(|i| 100.0 + (i as f64 * 0.5).sin() * 20.0).collect();
        let lows: Vec<f64> = highs.iter().map(|h| h - 5.0).collect();
        let pivots = zigzag(&highs, &lows, 5.0);
        // Consecutive pivots should alternate high/low
        for w in pivots.windows(2) {
            assert_ne!(w[0].is_high, w[1].is_high, "pivots should alternate");
        }
    }

    // ── Swing Points ──────────────────────────────────────────────────

    #[test]
    fn swing_points_basic() {
        // Clear swing at index 5 (high) and index 10 (low)
        let mut highs = vec![100.0; 20];
        let mut lows = vec![95.0; 20];
        highs[5] = 120.0; // swing high
        lows[10] = 80.0;  // swing low
        let swings = detect_swing_points(&highs, &lows, 2);
        let sh: Vec<_> = swings.iter().filter(|s| s.is_high).collect();
        let sl: Vec<_> = swings.iter().filter(|s| !s.is_high).collect();
        assert!(sh.iter().any(|s| s.index == 5), "should detect swing high at 5");
        assert!(sl.iter().any(|s| s.index == 10), "should detect swing low at 10");
    }

    #[test]
    fn swing_points_short_input() {
        let swings = detect_swing_points(&[100.0, 101.0], &[99.0, 100.0], 2);
        assert!(swings.is_empty()); // too short for lookback=2
    }

    // ── Market Structure ──────────────────────────────────────────────

    #[test]
    fn market_structure_uptrend() {
        // Clear uptrend: gradually rising with distinct swing points
        // Use unique values to avoid ambiguous swing detection
        let highs: Vec<f64> = (0..30)
            .map(|i| {
                let base = 100.0 + i as f64 * 0.5;
                match i {
                    5 => 115.0,   // swing high 1
                    15 => 120.0,  // swing high 2 (HH)
                    25 => 125.0,  // swing high 3 (HH)
                    _ => base,
                }
            })
            .collect();
        let lows: Vec<f64> = (0..30)
            .map(|i| {
                let base = 95.0 + i as f64 * 0.5;
                match i {
                    10 => 90.0,   // swing low 1
                    20 => 92.0,   // swing low 2 (HL)
                    _ => base,
                }
            })
            .collect();

        let labeled = market_structure(&highs, &lows, 2);
        // At minimum, verify we detected swing points and got a trend
        assert!(!labeled.is_empty(), "should detect swing points in uptrend");
        // Check that the last high label is HH (Higher High)
        let last_high = labeled.iter().rev().find(|l| l.is_high);
        if let Some(lh) = last_high {
            assert_eq!(lh.label, StructureLabel::HH, "last high should be HH");
        }
    }

    #[test]
    fn market_structure_short_input() {
        let labeled = market_structure(&[100.0, 101.0], &[99.0, 100.0], 2);
        let trend = market_structure_trend(&labeled);
        assert_eq!(trend, MarketTrend::Ranging);
    }

    // ── detect_swings ──────────────────────────────────────────────────────

    #[test]
    fn detect_swings_basic() {
        // V-shape: high in the middle
        let highs = vec![100.0, 105.0, 110.0, 105.0, 100.0];
        let lows  = vec![98.0,  103.0, 108.0, 103.0, 98.0];
        let swings = detect_swings(&highs, &lows, 1);
        // Should find a swing high at index 2
        assert!(swings.iter().any(|s| s.is_high && s.index == 2));
    }

    #[test]
    fn detect_swings_empty() {
        let swings = detect_swings(&[], &[], 2);
        assert!(swings.is_empty());
    }

    #[test]
    fn detect_swings_single() {
        let swings = detect_swings(&[100.0], &[99.0], 2);
        assert_eq!(swings.len(), 1);
        assert!(swings[0].is_high);
    }

    #[test]
    fn detect_swings_dedup_consecutive_highs() {
        // Two consecutive highs — only the higher one should survive
        let highs = vec![100.0, 112.0, 110.0, 95.0, 100.0];
        let lows  = vec![98.0,  109.0, 108.0, 93.0, 98.0];
        let swings = detect_swings(&highs, &lows, 1);
        // No two consecutive is_high=true entries
        for w in swings.windows(2) {
            assert!(!(w[0].is_high && w[1].is_high),
                "consecutive highs should be deduplicated");
        }
    }

    // ── detect_close_turning_pivots ────────────────────────────────────────

    #[test]
    fn close_turning_pivots_basic() {
        let closes = vec![100.0, 105.0, 102.0, 98.0, 101.0];
        let highs  = vec![101.0, 106.0, 103.0, 99.0, 102.0];
        let lows   = vec![99.0,  104.0, 101.0, 97.0, 100.0];
        let pivots = detect_close_turning_pivots(&closes, &highs, &lows);
        // Should find a high pivot at index 1 (105 > 100 and 105 > 102)
        assert!(pivots.iter().any(|s| s.is_high && s.index == 1));
        // Should find a low pivot at index 3 (98 < 102 and 98 < 101)
        assert!(pivots.iter().any(|s| !s.is_high && s.index == 3));
    }

    #[test]
    fn close_turning_pivots_empty() {
        let pivots = detect_close_turning_pivots(&[], &[], &[]);
        assert!(pivots.is_empty());
    }

    #[test]
    fn close_turning_pivots_boundaries() {
        // With 3 bars: boundary high at 0 may dedup with interior high at 1.
        // Check that both boundary indices are represented somewhere in output.
        let closes = vec![100.0, 105.0, 102.0];
        let highs  = vec![101.0, 106.0, 103.0];
        let lows   = vec![99.0,  104.0, 101.0];
        let pivots = detect_close_turning_pivots(&closes, &highs, &lows);
        // At minimum: a high pivot (from boundary 0 or interior 1) and
        // the boundary low at n-1 should survive dedup
        assert!(pivots.iter().any(|s| s.is_high), "should have at least one high pivot");
        assert!(pivots.last().map_or(false, |s| !s.is_high), "last pivot should be low boundary");
    }

    #[test]
    fn close_turning_pivots_dedup() {
        let closes = vec![100.0, 105.0, 106.0, 102.0, 99.0];
        let highs  = vec![101.0, 106.0, 107.0, 103.0, 100.0];
        let lows   = vec![99.0,  104.0, 105.0, 101.0, 98.0];
        let pivots = detect_close_turning_pivots(&closes, &highs, &lows);
        // No two consecutive same-direction pivots
        for w in pivots.windows(2) {
            assert!(!(w[0].is_high == w[1].is_high),
                "consecutive same-direction pivots should be deduplicated");
        }
    }

    // ── Marubozu ──────────────────────────────────────────────────────

    #[test]
    fn marubozu_bullish() {
        // body = |110 - 100| = 10, range = 110.1 - 99.9 = 10.2, ratio = 10/10.2 ≈ 0.98
        let signal = cdl_marubozu_inc(100.0, 110.1, 99.9, 110.0, 0.95);
        assert_abs_diff_eq!(signal, 1.0, epsilon = 1e-9);
    }

    #[test]
    fn marubozu_bearish() {
        // body = |90 - 100| = 10, range = 100.1 - 89.9 = 10.2, ratio ≈ 0.98
        let signal = cdl_marubozu_inc(100.0, 100.1, 89.9, 90.0, 0.95);
        assert_abs_diff_eq!(signal, -1.0, epsilon = 1e-9);
    }

    #[test]
    fn marubozu_not_enough_body() {
        // body = 5, range = 20, ratio = 0.25 — not a marubozu
        let signal = cdl_marubozu_inc(100.0, 110.0, 90.0, 105.0, 0.95);
        assert_abs_diff_eq!(signal, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn marubozu_batch() {
        let opens  = vec![100.0, 100.0, 100.0];
        let highs  = vec![110.1, 100.1, 110.0];
        let lows   = vec![99.9,  89.9,  90.0];
        let closes = vec![110.0, 90.0,  105.0];
        let result = cdl_marubozu(&opens, &highs, &lows, &closes, 0.95);
        assert_abs_diff_eq!(result[0], 1.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[1], -1.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[2], 0.0, epsilon = 1e-9);
    }

    // ── Long Shadow ──────────────────────────────────────────────────

    #[test]
    fn long_shadow_bullish_lower() {
        // Small body at top, long lower shadow
        // body = |101 - 100| = 1, range = 101 - 90 = 11, body/range = 0.09
        // lower = 100 - 90 = 10, upper = 101 - 101 = 0
        // max_shadow/body = 10/1 = 10 >= 2.0
        let signal = cdl_long_shadow_inc(100.0, 101.0, 90.0, 101.0, 2.0);
        assert_abs_diff_eq!(signal, 1.0, epsilon = 1e-9);
    }

    #[test]
    fn long_shadow_bearish_upper() {
        // Small body at bottom, long upper shadow
        // body = |101 - 100| = 1, range = 110 - 100 = 10, body/range = 0.1
        // upper = 110 - 101 = 9, lower = 100 - 100 = 0
        // max_shadow/body = 9/1 = 9 >= 2.0
        let signal = cdl_long_shadow_inc(101.0, 110.0, 100.0, 100.0, 2.0);
        assert_abs_diff_eq!(signal, -1.0, epsilon = 1e-9);
    }

    #[test]
    fn long_shadow_no_signal_large_body() {
        // Body takes up most of range — no long shadow
        // body = 9, range = 10, body/range = 0.9 > 0.5
        let signal = cdl_long_shadow_inc(100.0, 110.0, 100.0, 109.0, 2.0);
        assert_abs_diff_eq!(signal, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn long_shadow_batch() {
        let opens  = vec![100.0, 101.0, 100.0];
        let highs  = vec![101.0, 110.0, 110.0];
        let lows   = vec![90.0,  100.0, 100.0];
        let closes = vec![101.0, 100.0, 109.0];
        let result = cdl_long_shadow(&opens, &highs, &lows, &closes, 2.0);
        assert_abs_diff_eq!(result[0], 1.0, epsilon = 1e-9);   // bullish lower shadow
        assert_abs_diff_eq!(result[1], -1.0, epsilon = 1e-9);  // bearish upper shadow
        assert_abs_diff_eq!(result[2], 0.0, epsilon = 1e-9);   // large body, no signal
    }
}
