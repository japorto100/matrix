// backtest.rs — Backtesting and strategy validation
//
// Mirrors Python: indicator_engine/backtest.py
// Dependencies: trend (sma)

use crate::helper;
// Functions:
//   triple_barrier_labels — TP/SL/timeout labeling
//   sma_crossover_backtest — SMA crossover with transaction costs
//   parameter_sensitivity — multi-lookback sweep
//   walk_forward — rolling OOS validation
//
// Rayon candidate: parameter_sensitivity, walk_forward (independent iterations)

use super::trend::sma;

// ── Triple Barrier Labeling ───────────────────────────────────────────────

/// Triple barrier label.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BarrierLabel {
    TakeProfit,
    StopLoss,
    Timeout,
}

/// Triple barrier labeling — TP/SL/timeout for each entry point.
///
/// For each bar `i`, looks ahead up to `horizon` bars:
/// - If price reaches `entry * (1 + tp)` → TakeProfit
/// - If price reaches `entry * (1 - sl)` → StopLoss
/// - Otherwise → Timeout
///
/// Returns `n - horizon` labels.
pub fn triple_barrier_labels(
    closes: &[f64],
    horizon: usize,
    tp: f64,
    sl: f64,
) -> Vec<BarrierLabel> {
    let n = closes.len();
    if n <= horizon {
        return Vec::new();
    }
    let mut labels = Vec::with_capacity(n - horizon);
    for i in 0..(n - horizon) {
        let entry = closes[i];
        let up = entry * (1.0 + tp);
        let dn = entry * (1.0 - sl);
        let mut label = BarrierLabel::Timeout;
        for j in (i + 1)..=(i + horizon) {
            let px = closes[j];
            if px >= up {
                label = BarrierLabel::TakeProfit;
                break;
            }
            if px <= dn {
                label = BarrierLabel::StopLoss;
                break;
            }
        }
        labels.push(label);
    }
    labels
}

// ── SMA Crossover Backtest ────────────────────────────────────────────────

/// Backtest result.
#[derive(Debug, Clone)]
pub struct BacktestResult {
    pub strategy_returns: Vec<f64>,
    pub cumulative_return: f64,
    pub trade_count: usize,
}

/// Simple SMA crossover backtest with transaction costs.
///
/// Long when close > SMA, flat otherwise. Costs = slippage_bps + commission_bps.
pub fn sma_crossover_backtest(
    closes: &[f64],
    lookback: usize,
    slippage_bps: f64,
    commission_bps: f64,
) -> BacktestResult {
    if closes.len() < 2 {
        return BacktestResult {
            strategy_returns: Vec::new(),
            cumulative_return: 0.0,
            trade_count: 0,
        };
    }
    let ma = sma(closes, lookback);
    let cost = (slippage_bps + commission_bps) / 10_000.0;
    let n = closes.len();
    let mut rets = Vec::with_capacity(n - 1);
    let mut in_pos = false;

    for i in 1..n {
        if closes[i - 1] > ma[i - 1] {
            in_pos = true;
        } else if closes[i - 1] < ma[i - 1] {
            in_pos = false;
        }
        if in_pos && closes[i - 1] != 0.0 {
            let gross = (closes[i] - closes[i - 1]) / closes[i - 1];
            rets.push(gross - cost);
        } else {
            rets.push(0.0);
        }
    }

    let cumulative = rets.iter().fold(1.0_f64, |acc, &r| acc * (1.0 + r)) - 1.0;

    let mut trades = 0;
    if n > 2 {
        for i in 1..(n - 1) {
            if (closes[i] > ma[i]) != (closes[i - 1] > ma[i - 1]) {
                trades += 1;
            }
        }
    }

    BacktestResult {
        strategy_returns: rets,
        cumulative_return: cumulative,
        trade_count: trades,
    }
}

// ── Parameter Sensitivity ─────────────────────────────────────────────────

/// Parameter sensitivity result.
#[derive(Debug, Clone)]
pub struct SensitivityResult {
    pub by_lookback: Vec<(usize, f64)>,
    pub stability_score: f64,
}

/// Test strategy across multiple lookback periods.
///
/// Stability = 1 / (1 + stdev of cumulative returns).
pub fn parameter_sensitivity(
    closes: &[f64],
    lookbacks: &[usize],
    slippage_bps: f64,
    commission_bps: f64,
) -> SensitivityResult {
    let mut results = Vec::new();
    let mut vals = Vec::new();
    for &lb in lookbacks {
        if lb < 2 {
            continue;
        }
        let bt = sma_crossover_backtest(closes, lb, slippage_bps, commission_bps);
        results.push((lb, bt.cumulative_return));
        vals.push(bt.cumulative_return);
    }
    let stability = if vals.len() > 1 {
        1.0 / (1.0 + helper::pop_stddev(&vals))
    } else {
        if vals.is_empty() { 0.0 } else { 1.0 }
    };
    SensitivityResult {
        by_lookback: results,
        stability_score: stability,
    }
}

// ── Walk-Forward ──────────────────────────────────────────────────────────

/// Walk-forward result.
#[derive(Debug, Clone)]
pub struct WalkForwardResult {
    pub oos_scores: Vec<f64>,
    pub mean_oos_score: f64,
    pub stability_score: f64,
}

/// Walk-forward out-of-sample validation.
///
/// Rolls through data in train/test windows, computing OOS performance ratio.
pub fn walk_forward(
    closes: &[f64],
    train_window: usize,
    test_window: usize,
) -> WalkForwardResult {
    let n = closes.len();
    let mut scores = Vec::new();
    let mut i = 0;
    while i + train_window + test_window <= n {
        let train = &closes[i..i + train_window];
        let test = &closes[i + train_window..i + train_window + test_window];
        let train_lb = (train_window / 4).max(2).min(10);
        let test_lb = (test_window / 3).max(2).min(10);
        let train_bt = sma_crossover_backtest(train, train_lb, 0.0, 0.0);
        let test_bt = sma_crossover_backtest(test, test_lb, 0.0, 0.0);
        let base = train_bt.cumulative_return.abs() + 1e-9;
        scores.push(test_bt.cumulative_return / base);
        i += test_window;
    }
    if scores.is_empty() {
        return WalkForwardResult {
            oos_scores: Vec::new(),
            mean_oos_score: 0.0,
            stability_score: 0.0,
        };
    }
    let m = helper::mean(&scores);
    let stability = if scores.len() > 1 {
        1.0 / (1.0 + helper::pop_stddev(&scores))
    } else {
        1.0
    };
    WalkForwardResult {
        oos_scores: scores,
        mean_oos_score: m,
        stability_score: stability,
    }
}

// ── Strategy Metrics ─────────────────────────────────────────────────────

/// A single trade record for strategy evaluation.
#[derive(Debug, Clone)]
pub struct TradeRecord {
    pub entry: f64,
    pub exit: f64,
    pub quantity: f64,
    pub fee: f64,
    pub is_short: bool,
}

/// Aggregated strategy performance metrics.
#[derive(Debug, Clone)]
pub struct StrategyMetrics {
    pub net_return: f64,
    pub hit_ratio: f64,
    pub risk_reward_ratio: f64,
    pub expectancy: f64,
    pub profit_factor: f64,
    pub sharpe: f64,
    pub sortino: f64,
    pub average_win: f64,
    pub average_loss: f64,
    pub trade_count: usize,
}

/// Compute comprehensive strategy metrics from a list of trades.
///
/// PnL per trade: gross = (exit - entry) * quantity (negated if short), minus fee.
/// Returns are pnl / base where base = entry * quantity.
/// Sharpe = (mean_return - risk_free_rate) / stdev.
/// Sortino = (mean_return - risk_free_rate) / downside_stdev (only negative returns).
pub fn build_strategy_metrics(trades: &[TradeRecord], risk_free_rate: f64) -> StrategyMetrics {
    let empty = StrategyMetrics {
        net_return: 0.0,
        hit_ratio: 0.0,
        risk_reward_ratio: 0.0,
        expectancy: 0.0,
        profit_factor: 0.0,
        sharpe: 0.0,
        sortino: 0.0,
        average_win: 0.0,
        average_loss: 0.0,
        trade_count: 0,
    };
    if trades.is_empty() {
        return empty;
    }

    let mut pnls = Vec::with_capacity(trades.len());
    let mut returns = Vec::with_capacity(trades.len());

    for t in trades {
        let gross = if t.is_short {
            (t.entry - t.exit) * t.quantity
        } else {
            (t.exit - t.entry) * t.quantity
        };
        let pnl = gross - t.fee;
        pnls.push(pnl);

        let base = t.entry * t.quantity;
        if base.abs() > 1e-15 {
            returns.push(pnl / base);
        } else {
            returns.push(0.0);
        }
    }

    let trade_count = trades.len();
    let net_return: f64 = pnls.iter().sum();

    // Split wins and losses
    let mut gross_profit = 0.0_f64;
    let mut gross_loss = 0.0_f64;
    let mut win_count = 0usize;
    let mut win_sum = 0.0_f64;
    let mut loss_sum = 0.0_f64;

    for &pnl in &pnls {
        if pnl > 0.0 {
            win_count += 1;
            win_sum += pnl;
            gross_profit += pnl;
        } else if pnl < 0.0 {
            loss_sum += pnl.abs();
            gross_loss += pnl.abs();
        }
    }

    let loss_count = trade_count - win_count;
    let hit_ratio = win_count as f64 / trade_count as f64;
    let average_win = if win_count > 0 { win_sum / win_count as f64 } else { 0.0 };
    let average_loss = if loss_count > 0 { loss_sum / loss_count as f64 } else { 0.0 };

    let risk_reward_ratio = if average_loss > 1e-15 { average_win / average_loss } else { 0.0 };
    let expectancy = hit_ratio * average_win - (1.0 - hit_ratio) * average_loss;
    let profit_factor = if gross_loss > 1e-15 { gross_profit / gross_loss } else { 0.0 };

    // Sharpe ratio
    let mean_ret = helper::mean(&returns);
    let stdev = helper::pop_stddev(&returns);
    let sharpe = if stdev > 1e-15 { (mean_ret - risk_free_rate) / stdev } else { 0.0 };

    // Sortino ratio (downside deviation uses only negative returns)
    let downside_var = returns
        .iter()
        .map(|r| if *r < 0.0 { r.powi(2) } else { 0.0 })
        .sum::<f64>()
        / returns.len() as f64;
    let downside_stdev = downside_var.sqrt();
    let sortino = if downside_stdev > 1e-15 {
        (mean_ret - risk_free_rate) / downside_stdev
    } else {
        0.0
    };

    StrategyMetrics {
        net_return,
        hit_ratio,
        risk_reward_ratio,
        expectancy,
        profit_factor,
        sharpe,
        sortino,
        average_win,
        average_loss,
        trade_count,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    fn rising_prices(n: usize) -> Vec<f64> {
        (0..n).map(|i| 100.0 + i as f64 * 0.5).collect()
    }

    fn oscillating_prices(n: usize) -> Vec<f64> {
        (0..n)
            .map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0)
            .collect()
    }

    // ── Triple Barrier ────────────────────────────────────────────────────

    #[test]
    fn barrier_labels_rising() {
        let prices = rising_prices(20);
        let labels = triple_barrier_labels(&prices, 5, 0.01, 0.01);
        // Rising prices → mostly TakeProfit
        let tp_count = labels.iter().filter(|&&l| l == BarrierLabel::TakeProfit).count();
        assert!(tp_count > labels.len() / 2, "expected mostly TP in uptrend");
    }

    #[test]
    fn barrier_labels_length() {
        let prices = oscillating_prices(50);
        let labels = triple_barrier_labels(&prices, 10, 0.05, 0.05);
        assert_eq!(labels.len(), 40); // n - horizon
    }

    #[test]
    fn barrier_labels_empty_short_input() {
        let labels = triple_barrier_labels(&[100.0, 101.0], 5, 0.01, 0.01);
        assert!(labels.is_empty());
    }

    // ── SMA Crossover ─────────────────────────────────────────────────────

    #[test]
    fn backtest_rising_positive_return() {
        let prices = rising_prices(50);
        let result = sma_crossover_backtest(&prices, 5, 0.0, 0.0);
        assert!(!result.strategy_returns.is_empty());
        assert!(result.cumulative_return > 0.0, "rising prices should be positive");
    }

    #[test]
    fn backtest_with_costs() {
        let prices = rising_prices(50);
        let no_cost = sma_crossover_backtest(&prices, 5, 0.0, 0.0);
        let with_cost = sma_crossover_backtest(&prices, 5, 10.0, 10.0);
        assert!(with_cost.cumulative_return < no_cost.cumulative_return);
    }

    #[test]
    fn backtest_short_input() {
        let result = sma_crossover_backtest(&[100.0], 5, 0.0, 0.0);
        assert!(result.strategy_returns.is_empty());
        assert_abs_diff_eq!(result.cumulative_return, 0.0, epsilon = 1e-9);
    }

    // ── Parameter Sensitivity ─────────────────────────────────────────────

    #[test]
    fn sensitivity_multiple_lookbacks() {
        let prices = oscillating_prices(100);
        let result = parameter_sensitivity(&prices, &[5, 10, 20], 0.0, 0.0);
        assert_eq!(result.by_lookback.len(), 3);
        assert!(result.stability_score > 0.0 && result.stability_score <= 1.0);
    }

    #[test]
    fn sensitivity_skips_small_lookback() {
        let prices = oscillating_prices(50);
        let result = parameter_sensitivity(&prices, &[0, 1, 5], 0.0, 0.0);
        assert_eq!(result.by_lookback.len(), 1); // only lb=5
    }

    // ── Walk-Forward ──────────────────────────────────────────────────────

    #[test]
    fn walk_forward_basic() {
        let prices = oscillating_prices(200);
        let result = walk_forward(&prices, 50, 20);
        assert!(!result.oos_scores.is_empty());
        assert!(result.stability_score > 0.0);
    }

    #[test]
    fn walk_forward_too_short() {
        let prices = oscillating_prices(10);
        let result = walk_forward(&prices, 50, 20);
        assert!(result.oos_scores.is_empty());
        assert_abs_diff_eq!(result.mean_oos_score, 0.0, epsilon = 1e-9);
    }

    // ── Strategy Metrics ─────────────────────────────────────────────────

    fn sample_trades() -> Vec<TradeRecord> {
        vec![
            TradeRecord { entry: 100.0, exit: 110.0, quantity: 10.0, fee: 5.0, is_short: false },
            TradeRecord { entry: 100.0, exit: 95.0,  quantity: 10.0, fee: 5.0, is_short: false },
            TradeRecord { entry: 100.0, exit: 108.0, quantity: 10.0, fee: 5.0, is_short: false },
            TradeRecord { entry: 100.0, exit: 92.0,  quantity: 10.0, fee: 5.0, is_short: false },
        ]
    }

    #[test]
    fn strategy_metrics_basic() {
        let trades = sample_trades();
        let m = build_strategy_metrics(&trades, 0.0);
        assert_eq!(m.trade_count, 4);
        // Two wins (pnl: 95, 75), two losses (pnl: -55, -85)
        assert_eq!((m.hit_ratio * 100.0).round(), 50.0);
        assert!(m.average_win > 0.0);
        assert!(m.average_loss > 0.0);
        assert!(m.risk_reward_ratio > 0.0);
        // Net return = 95 + (-55) + 75 + (-85) = 30
        assert_abs_diff_eq!(m.net_return, 30.0, epsilon = 1e-9);
    }

    #[test]
    fn strategy_metrics_empty() {
        let m = build_strategy_metrics(&[], 0.0);
        assert_eq!(m.trade_count, 0);
        assert_abs_diff_eq!(m.net_return, 0.0, epsilon = 1e-9);
        assert_abs_diff_eq!(m.sharpe, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn strategy_metrics_all_wins() {
        let trades = vec![
            TradeRecord { entry: 100.0, exit: 110.0, quantity: 1.0, fee: 0.0, is_short: false },
            TradeRecord { entry: 100.0, exit: 120.0, quantity: 1.0, fee: 0.0, is_short: false },
        ];
        let m = build_strategy_metrics(&trades, 0.0);
        assert_abs_diff_eq!(m.hit_ratio, 1.0, epsilon = 1e-9);
        assert_abs_diff_eq!(m.average_loss, 0.0, epsilon = 1e-9);
        // profit_factor = 0 when no losses (division guard)
        assert_abs_diff_eq!(m.profit_factor, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn strategy_metrics_short_trades() {
        let trades = vec![
            TradeRecord { entry: 100.0, exit: 90.0, quantity: 10.0, fee: 0.0, is_short: true },
        ];
        let m = build_strategy_metrics(&trades, 0.0);
        // Short: pnl = (100-90)*10 = 100
        assert_abs_diff_eq!(m.net_return, 100.0, epsilon = 1e-9);
        assert_abs_diff_eq!(m.hit_ratio, 1.0, epsilon = 1e-9);
    }

    #[test]
    fn strategy_metrics_sharpe_nonzero() {
        let trades = sample_trades();
        let m = build_strategy_metrics(&trades, 0.0);
        // With mixed wins/losses, stdev > 0 so sharpe should be computable
        // Just check it's finite
        assert!(m.sharpe.is_finite());
        assert!(m.sortino.is_finite());
    }
}
