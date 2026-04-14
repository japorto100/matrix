// derivatives.rs — Options, DeFi, dark pool, and market microstructure
//
// Mirrors Python: indicator_engine/derivatives.py
// All functions are pure math — no external deps.
//
// kand-Blueprint: batch-only (no streaming use case for these).

// ── Dark Pool Signal ──────────────────────────────────────────────────────

/// Dark pool signal result.
#[derive(Debug, Clone, PartialEq)]
pub enum DarkPoolSignal {
    Accumulation,
    Distribution,
    Neutral,
}

/// Dark pool activity signal — accumulation/distribution based on DP ratio.
///
/// ratio > 0.45 → accumulation, < 0.15 → distribution, else neutral.
/// Confidence = |ratio - 0.30| / 0.30, clamped to [0, 1].
pub fn dark_pool_signal(lit_volume: f64, dark_pool_volume: f64) -> (f64, DarkPoolSignal, f64) {
    let total = lit_volume + dark_pool_volume;
    let ratio = if total > 0.0 {
        dark_pool_volume / total
    } else {
        0.0
    };
    let signal = if ratio > 0.45 {
        DarkPoolSignal::Accumulation
    } else if ratio < 0.15 {
        DarkPoolSignal::Distribution
    } else {
        DarkPoolSignal::Neutral
    };
    let confidence = ((ratio - 0.30).abs() / 0.30).min(1.0);
    (ratio, signal, confidence)
}

// ── GEX Profile ───────────────────────────────────────────────────────────

/// Gamma Exposure profile — net GEX per strike, call wall, put wall.
///
/// Returns `(net_gex, call_wall_strike, put_wall_strike)`.
pub fn gex_profile(
    strikes: &[f64],
    call_gamma: &[f64],
    put_gamma: &[f64],
) -> (Vec<f64>, f64, f64) {
    let n = strikes.len().min(call_gamma.len()).min(put_gamma.len());
    if n == 0 {
        return (Vec::new(), 0.0, 0.0);
    }
    let net: Vec<f64> = (0..n).map(|i| call_gamma[i] - put_gamma[i]).collect();

    let call_idx = (0..n)
        .max_by(|&a, &b| call_gamma[a].partial_cmp(&call_gamma[b]).unwrap_or(std::cmp::Ordering::Equal))
        .unwrap_or(0);
    let put_idx = (0..n)
        .max_by(|&a, &b| put_gamma[a].partial_cmp(&put_gamma[b]).unwrap_or(std::cmp::Ordering::Equal))
        .unwrap_or(0);

    (net, strikes[call_idx], strikes[put_idx])
}

// ── Expected Move ─────────────────────────────────────────────────────────

/// Expected move from implied volatility and time horizon.
///
/// Returns `(move_abs, upper, lower)`.
pub fn expected_move(spot: f64, iv_annual: f64, days: f64) -> (f64, f64, f64) {
    let t = days / 365.0;
    let mv = spot * iv_annual * t.sqrt();
    (mv, spot + mv, (spot - mv).max(0.0))
}

// ── Options Payoff ────────────────────────────────────────────────────────

/// Single options leg.
#[derive(Debug, Clone)]
pub struct OptionsLeg {
    pub strike: f64,
    pub premium: f64,
    pub quantity: f64,
    pub is_call: bool,
}

/// Options payoff calculator — max profit/loss and breakevens.
///
/// Returns `(max_profit, max_loss, breakevens)`.
pub fn options_payoff(legs: &[OptionsLeg], underlying_qty: f64) -> (f64, f64, Vec<f64>) {
    if legs.is_empty() {
        return (0.0, 0.0, Vec::new());
    }
    let min_s = legs.iter().map(|l| l.strike).fold(f64::INFINITY, f64::min) * 0.2;
    let max_s = legs.iter().map(|l| l.strike).fold(f64::NEG_INFINITY, f64::max) * 2.0;

    let grid: Vec<f64> = (0..=200)
        .map(|i| min_s + i as f64 * (max_s - min_s) / 200.0)
        .collect();

    let payoffs: Vec<f64> = grid
        .iter()
        .map(|&s| {
            legs.iter()
                .map(|leg| {
                    let intrinsic = if leg.is_call {
                        (s - leg.strike).max(0.0)
                    } else {
                        (leg.strike - s).max(0.0)
                    };
                    (intrinsic - leg.premium) * leg.quantity * underlying_qty
                })
                .sum()
        })
        .collect();

    let max_profit = payoffs.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let max_loss = payoffs.iter().cloned().fold(f64::INFINITY, f64::min);

    let mut breakevens = Vec::new();
    for i in 1..grid.len() {
        if payoffs[i - 1] == 0.0
            || payoffs[i] == 0.0
            || (payoffs[i - 1] < 0.0 && payoffs[i] > 0.0)
            || (payoffs[i - 1] > 0.0 && payoffs[i] < 0.0)
        {
            breakevens.push(grid[i]);
        }
        if breakevens.len() >= 4 {
            break;
        }
    }
    (max_profit, max_loss, breakevens)
}

// ── DeFi Stress ───────────────────────────────────────────────────────────

/// DeFi stress level.
#[derive(Debug, Clone, PartialEq)]
pub enum StressLevel {
    Low,
    Medium,
    High,
}

/// DeFi stress index — TVL change + funding rate + OI change.
///
/// Returns `(stress_score, level)`.
pub fn defi_stress(tvl_change_pct: f64, funding_rate: f64, oi_change_pct: f64) -> (f64, StressLevel) {
    let score = 0.4 * tvl_change_pct.abs() + 0.3 * funding_rate.abs() * 100.0 + 0.3 * oi_change_pct.abs();
    let level = if score > 25.0 {
        StressLevel::High
    } else if score > 10.0 {
        StressLevel::Medium
    } else {
        StressLevel::Low
    };
    (score, level)
}

// ── Oracle Crosscheck ─────────────────────────────────────────────────────

/// Oracle price divergence check — Web2 vs on-chain price.
///
/// Returns `(divergence_pct, disagreement, severity)`.
pub fn oracle_crosscheck(
    web2_price: f64,
    oracle_price: f64,
    threshold_pct: f64,
) -> (f64, bool, StressLevel) {
    let div = if oracle_price != 0.0 {
        (web2_price - oracle_price).abs() / oracle_price
    } else {
        0.0
    };
    let disagreement = div > threshold_pct;
    let severity = if div > threshold_pct * 3.0 {
        StressLevel::High
    } else if div > threshold_pct * 1.5 {
        StressLevel::Medium
    } else {
        StressLevel::Low
    };
    (div, disagreement, severity)
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    #[test]
    fn dark_pool_accumulation() {
        let (ratio, signal, _conf) = dark_pool_signal(55.0, 45.0);
        // ratio = 45/100 = 0.45 → NOT > 0.45, so neutral
        assert_abs_diff_eq!(ratio, 0.45, epsilon = 1e-9);
        // Need > 0.45 for accumulation
        let (_, signal2, _) = dark_pool_signal(50.0, 55.0);
        assert_eq!(signal2, DarkPoolSignal::Accumulation);
        assert_eq!(signal, DarkPoolSignal::Neutral);
    }

    #[test]
    fn dark_pool_distribution() {
        let (_, signal, _) = dark_pool_signal(90.0, 10.0);
        assert_eq!(signal, DarkPoolSignal::Distribution);
    }

    #[test]
    fn dark_pool_zero_volume() {
        let (ratio, signal, _) = dark_pool_signal(0.0, 0.0);
        assert_abs_diff_eq!(ratio, 0.0, epsilon = 1e-9);
        assert_eq!(signal, DarkPoolSignal::Distribution);
    }

    #[test]
    fn gex_profile_basic() {
        let strikes = vec![100.0, 105.0, 110.0];
        let call_g = vec![0.5, 1.0, 0.3];
        let put_g = vec![0.8, 0.2, 0.6];
        let (net, call_wall, put_wall) = gex_profile(&strikes, &call_g, &put_g);
        assert_eq!(net.len(), 3);
        assert_abs_diff_eq!(net[0], -0.3, epsilon = 1e-9);
        assert_abs_diff_eq!(call_wall, 105.0, epsilon = 1e-9); // max call_gamma at idx 1
        assert_abs_diff_eq!(put_wall, 100.0, epsilon = 1e-9); // max put_gamma at idx 0
    }

    #[test]
    fn gex_profile_empty() {
        let (net, _, _) = gex_profile(&[], &[], &[]);
        assert!(net.is_empty());
    }

    #[test]
    fn expected_move_basic() {
        let (mv, upper, lower) = expected_move(100.0, 0.30, 30.0);
        // 100 * 0.30 * sqrt(30/365) ≈ 8.60
        assert!(mv > 8.0 && mv < 9.5);
        assert_abs_diff_eq!(upper, 100.0 + mv, epsilon = 1e-9);
        assert_abs_diff_eq!(lower, 100.0 - mv, epsilon = 1e-9);
    }

    #[test]
    fn expected_move_lower_clamped() {
        let (_, _, lower) = expected_move(5.0, 2.0, 365.0);
        assert!(lower >= 0.0);
    }

    #[test]
    fn options_payoff_single_call() {
        let legs = vec![OptionsLeg {
            strike: 100.0,
            premium: 5.0,
            quantity: 1.0,
            is_call: true,
        }];
        let (max_profit, max_loss, _) = options_payoff(&legs, 1.0);
        assert!(max_profit > 0.0);
        assert!(max_loss < 0.0);
    }

    #[test]
    fn options_payoff_empty() {
        let (mp, ml, be) = options_payoff(&[], 1.0);
        assert_abs_diff_eq!(mp, 0.0, epsilon = 1e-9);
        assert_abs_diff_eq!(ml, 0.0, epsilon = 1e-9);
        assert!(be.is_empty());
    }

    #[test]
    fn defi_stress_high() {
        let (score, level) = defi_stress(30.0, 0.5, 20.0);
        assert!(score > 25.0);
        assert_eq!(level, StressLevel::High);
    }

    #[test]
    fn defi_stress_low() {
        let (score, level) = defi_stress(1.0, 0.01, 2.0);
        assert!(score < 10.0);
        assert_eq!(level, StressLevel::Low);
    }

    #[test]
    fn oracle_crosscheck_disagreement() {
        let (div, disagree, sev) = oracle_crosscheck(105.0, 100.0, 0.03);
        assert_abs_diff_eq!(div, 0.05, epsilon = 1e-9);
        assert!(disagree);
        assert_eq!(sev, StressLevel::Medium); // 0.05 > 0.03*1.5=0.045 but < 0.03*3=0.09
    }

    #[test]
    fn oracle_crosscheck_agreement() {
        let (_, disagree, _) = oracle_crosscheck(100.0, 100.0, 0.03);
        assert!(!disagree);
    }
}
