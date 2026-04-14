// portfolio.rs — Portfolio analytics
//
// Migrated from lib.rs: drawdown, rolling_sharpe, kelly_fraction
// Added: returns, rolling_sortino, rolling_winrate

use crate::helper;
// kand-Blueprint pattern adopted:
//   batch fn()       — full series computation
//   fn _inc()        — incremental: prev_state + new_input -> new_value
//   fn _with_state() — batch that also returns final state for _inc() bootstrap
// kand existing (empty stubs): sharpe, sortino, winrate, ret, calmar

// ── Drawdown ───────────────────────────────────────────────────────────────────

/// Underwater (drawdown) curve: (equity[i] - running_max) / running_max.
/// Returns 0.0 at new highs, negative fractions in drawdown.
pub fn portfolio_drawdown_series_impl(equity: &[f64]) -> Vec<f64> {
    if equity.is_empty() {
        return Vec::new();
    }
    let mut out = Vec::with_capacity(equity.len());
    let mut running_max = equity[0];
    for &e in equity {
        if e > running_max {
            running_max = e;
        }
        let dd = if running_max > 0.0 {
            (e - running_max) / running_max
        } else {
            0.0
        };
        out.push(dd);
    }
    out
}

/// Drawdown with state — returns (series, running_max) for `drawdown_inc()`.
pub fn drawdown_with_state(equity: &[f64]) -> (Vec<f64>, f64) {
    let result = portfolio_drawdown_series_impl(equity);
    let running_max = if equity.is_empty() {
        0.0
    } else {
        equity.iter().copied().fold(equity[0], f64::max)
    };
    (result, running_max)
}

/// Incremental drawdown update.
///
/// Returns `(drawdown, new_running_max)`.
///
/// Bootstrap state from `drawdown_with_state()`.
#[inline]
pub fn drawdown_inc(equity_val: f64, prev_running_max: f64) -> (f64, f64) {
    let running_max = if equity_val > prev_running_max {
        equity_val
    } else {
        prev_running_max
    };
    let dd = if running_max > 0.0 {
        (equity_val - running_max) / running_max
    } else {
        0.0
    };
    (dd, running_max)
}

// ── Rolling Sharpe ─────────────────────────────────────────────────────────────

/// Rolling annualised Sharpe ratio. Returns NaN for positions before the first
/// full window. rf_daily = annual_rf / 252.
pub fn portfolio_rolling_sharpe_impl(returns: &[f64], window: usize, rf_daily: f64) -> Vec<f64> {
    let n = returns.len();
    let mut out = vec![f64::NAN; n];
    if window < 2 || n < window {
        return out;
    }
    let ann = 252.0_f64.sqrt();
    for i in (window - 1)..n {
        let slice = &returns[(i + 1 - window)..=i];
        let mean = slice.iter().sum::<f64>() / window as f64;
        let var = slice.iter().map(|r| (r - mean).powi(2)).sum::<f64>()
            / (window - 1) as f64;
        let std = var.sqrt();
        out[i] = if std > 1e-12 {
            (mean - rf_daily) / std * ann
        } else {
            0.0
        };
    }
    out
}

/// Rolling Sharpe with state — returns (series, last window of returns) for `sharpe_inc()`.
pub fn sharpe_with_state(
    returns: &[f64],
    window: usize,
    rf_daily: f64,
) -> (Vec<f64>, Vec<f64>) {
    let result = portfolio_rolling_sharpe_impl(returns, window, rf_daily);
    let win_start = returns.len().saturating_sub(window);
    let last_window = returns[win_start..].to_vec();
    (result, last_window)
}

/// Incremental rolling Sharpe update.
///
/// Slides the returns window by one (drops oldest, appends new return),
/// then computes the annualised Sharpe for the new window.
///
/// Returns `(sharpe, new_returns_window)`.
///
/// Bootstrap state from `sharpe_with_state()`.
pub fn sharpe_inc(
    new_return: f64,
    returns_window: &[f64],
    rf_daily: f64,
) -> (f64, Vec<f64>) {
    let window = returns_window.len();
    if window < 2 {
        return (0.0, returns_window.to_vec());
    }

    // Slide window
    let mut new_win: Vec<f64> = Vec::with_capacity(window);
    for v in &returns_window[1..] {
        new_win.push(*v);
    }
    new_win.push(new_return);

    let ann = 252.0_f64.sqrt();
    let mean = new_win.iter().sum::<f64>() / window as f64;
    let var = new_win.iter().map(|r| (r - mean).powi(2)).sum::<f64>() / (window - 1) as f64;
    let std = var.sqrt();
    let sharpe = if std > 1e-12 {
        (mean - rf_daily) / std * ann
    } else {
        0.0
    };

    (sharpe, new_win)
}

// ── Kelly Fraction ─────────────────────────────────────────────────────────────

/// Single-asset Kelly fraction: mu / sigma² (clamped to [-2, 2]).
pub fn portfolio_kelly_fraction_impl(returns: &[f64]) -> f64 {
    if returns.len() < 2 {
        return 0.0;
    }
    let n = returns.len() as f64;
    let mean = returns.iter().sum::<f64>() / n;
    let var = returns.iter().map(|r| (r - mean).powi(2)).sum::<f64>() / (n - 1.0);
    if var <= 1e-14 {
        return 0.0;
    }
    (mean / var).clamp(-2.0, 2.0)
}

/// Kelly with state — returns (kelly, sum, sum_sq, n) for `kelly_inc()`.
pub fn kelly_with_state(returns: &[f64]) -> (f64, f64, f64, usize) {
    let kelly = portfolio_kelly_fraction_impl(returns);
    let sum: f64 = returns.iter().sum();
    let sum_sq: f64 = returns.iter().map(|r| r * r).sum();
    (kelly, sum, sum_sq, returns.len())
}

/// Incremental Kelly fraction update (expanding window — all returns considered).
///
/// Uses running sum and sum of squares for O(1) mean/variance computation.
/// Returns `(kelly, new_sum, new_sum_sq, new_n)`.
///
/// Bootstrap state from `kelly_with_state()`.
pub fn kelly_inc(
    new_return: f64,
    prev_sum: f64,
    prev_sum_sq: f64,
    prev_n: usize,
) -> (f64, f64, f64, usize) {
    let new_sum = prev_sum + new_return;
    let new_sum_sq = prev_sum_sq + new_return * new_return;
    let new_n = prev_n + 1;

    if new_n < 2 {
        return (0.0, new_sum, new_sum_sq, new_n);
    }

    let n = new_n as f64;
    let mean = new_sum / n;
    // population variance from running sums, then Bessel correction
    let var = (new_sum_sq / n - mean * mean) * n / (n - 1.0);

    let kelly = if var <= 1e-14 {
        0.0
    } else {
        (mean / var).clamp(-2.0, 2.0)
    };

    (kelly, new_sum, new_sum_sq, new_n)
}

// ── Returns ──────────────────────────────────────────────────────────────────

/// Simple returns from prices: `ret[i] = (price[i] - price[i-1]) / price[i-1]`.
///
/// First element is 0.0 (no previous price).
pub fn returns(prices: &[f64]) -> Vec<f64> {
    if prices.is_empty() {
        return Vec::new();
    }
    let mut out = Vec::with_capacity(prices.len());
    out.push(0.0);
    for i in 1..prices.len() {
        let ret = if prices[i - 1].abs() > 1e-14 {
            (prices[i] - prices[i - 1]) / prices[i - 1]
        } else {
            0.0
        };
        out.push(ret);
    }
    out
}

/// Incremental return from two consecutive prices.
#[inline]
pub fn returns_inc(curr_price: f64, prev_price: f64) -> f64 {
    if prev_price.abs() > 1e-14 {
        (curr_price - prev_price) / prev_price
    } else {
        0.0
    }
}

// ── Rolling Sortino ──────────────────────────────────────────────────────────

/// Rolling annualised Sortino ratio.
///
/// Like Sharpe but uses only downside deviation (negative returns below target).
/// `target_daily` is the daily minimum acceptable return (usually 0.0 or rf_daily).
///
/// Returns NaN before the first full window.
pub fn rolling_sortino(returns: &[f64], window: usize, target_daily: f64) -> Vec<f64> {
    let n = returns.len();
    let mut out = vec![f64::NAN; n];
    if window < 2 || n < window {
        return out;
    }
    let ann = 252.0_f64.sqrt();
    for i in (window - 1)..n {
        let slice = &returns[(i + 1 - window)..=i];
        let mean = slice.iter().sum::<f64>() / window as f64;
        // Downside deviation: sqrt(mean of squared negative deviations)
        let downside_sq_sum: f64 = slice
            .iter()
            .map(|&r| {
                let diff = r - target_daily;
                if diff < 0.0 { diff * diff } else { 0.0 }
            })
            .sum();
        let downside_dev = (downside_sq_sum / window as f64).sqrt();
        out[i] = if downside_dev > 1e-12 {
            (mean - target_daily) / downside_dev * ann
        } else {
            0.0
        };
    }
    out
}

/// Rolling Sortino with state — returns (series, last window of returns)
/// for `sortino_inc()`.
pub fn sortino_with_state(
    returns: &[f64],
    window: usize,
    target_daily: f64,
) -> (Vec<f64>, Vec<f64>) {
    let result = rolling_sortino(returns, window, target_daily);
    let win_start = returns.len().saturating_sub(window);
    let last_window = returns[win_start..].to_vec();
    (result, last_window)
}

/// Incremental rolling Sortino update.
///
/// Slides the returns window by one (drops oldest, appends new return).
/// Returns `(sortino, new_returns_window)`.
///
/// Bootstrap state from `sortino_with_state()`.
pub fn sortino_inc(
    new_return: f64,
    returns_window: &[f64],
    target_daily: f64,
) -> (f64, Vec<f64>) {
    let window = returns_window.len();

    // Slide window
    let mut new_win: Vec<f64> = Vec::with_capacity(window);
    for v in &returns_window[1..] {
        new_win.push(*v);
    }
    new_win.push(new_return);

    let ann = 252.0_f64.sqrt();
    let mean = new_win.iter().sum::<f64>() / window as f64;
    let downside_sq_sum: f64 = new_win
        .iter()
        .map(|&r| {
            let diff = r - target_daily;
            if diff < 0.0 { diff * diff } else { 0.0 }
        })
        .sum();
    let downside_dev = (downside_sq_sum / window as f64).sqrt();
    let sortino = if downside_dev > 1e-12 {
        (mean - target_daily) / downside_dev * ann
    } else {
        0.0
    };

    (sortino, new_win)
}

// ── Rolling Winrate ──────────────────────────────────────────────────────────

/// Rolling win rate — fraction of positive returns in a rolling window.
///
/// Returns NaN before the first full window. Values in [0.0, 1.0].
pub fn rolling_winrate(returns: &[f64], window: usize) -> Vec<f64> {
    let n = returns.len();
    let mut out = vec![f64::NAN; n];
    if window == 0 || n < window {
        return out;
    }

    // Count wins in first window
    let mut wins: usize = returns[..window].iter().filter(|&&r| r > 0.0).count();
    out[window - 1] = wins as f64 / window as f64;

    // Slide window
    for i in window..n {
        // Remove oldest
        if returns[i - window] > 0.0 {
            wins -= 1;
        }
        // Add newest
        if returns[i] > 0.0 {
            wins += 1;
        }
        out[i] = wins as f64 / window as f64;
    }
    out
}

/// Rolling winrate with state — returns (series, last window of returns, wins_count)
/// for `winrate_inc()`.
pub fn winrate_with_state(returns: &[f64], window: usize) -> (Vec<f64>, Vec<f64>, usize) {
    let result = rolling_winrate(returns, window);
    let win_start = returns.len().saturating_sub(window);
    let last_window = returns[win_start..].to_vec();
    let wins = last_window.iter().filter(|&&r| r > 0.0).count();
    (result, last_window, wins)
}

/// Incremental rolling winrate update.
///
/// Returns `(winrate, new_window, new_wins_count)`.
///
/// Bootstrap state from `winrate_with_state()`.
#[inline]
pub fn winrate_inc(
    new_return: f64,
    returns_window: &[f64],
    prev_wins: usize,
) -> (f64, Vec<f64>, usize) {
    let window = returns_window.len();

    // Adjust wins: remove oldest, add newest
    let oldest = returns_window[0];
    let mut wins = prev_wins;
    if oldest > 0.0 {
        wins -= 1;
    }
    if new_return > 0.0 {
        wins += 1;
    }

    // Slide window
    let mut new_win: Vec<f64> = Vec::with_capacity(window);
    for v in &returns_window[1..] {
        new_win.push(*v);
    }
    new_win.push(new_return);

    let wr = wins as f64 / window as f64;
    (wr, new_win, wins)
}

// ── Rolling Metrics (combined) ──────────────────────────────────────────────

/// Combined rolling metrics: Sharpe, Sortino, Calmar from an equity curve.
///
/// Returns `(sharpes, sortinos, calmars)` — all NaN before first full window.
/// Mirrors Python: `portfolio_analytics.py::compute_rolling_metrics()`.
pub fn compute_rolling_metrics(
    equity: &[f64],
    window: usize,
    risk_free_annual: f64,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let n = equity.len();
    if n < 2 {
        return (Vec::new(), Vec::new(), Vec::new());
    }

    // Compute returns from equity
    let rets = returns(equity);

    let rf_daily = risk_free_annual / 252.0;
    let sharpes = portfolio_rolling_sharpe_impl(&rets, window, rf_daily);
    let sortinos = rolling_sortino(&rets, window, 0.0);

    // Rolling Calmar: annualised return / |max rolling drawdown|
    let mut calmars = vec![f64::NAN; n];
    if window >= 2 && n >= window {
        // Cumulative product of (1 + return)
        let mut cum = Vec::with_capacity(n);
        cum.push(1.0);
        for i in 1..n {
            cum.push(cum[i - 1] * (1.0 + rets[i]));
        }

        for i in (window - 1)..n {
            let start = i + 1 - window;
            let slice_rets = &rets[start..=i];
            let mean_ret = slice_rets.iter().sum::<f64>() / window as f64;
            let ann_return = mean_ret * 252.0;

            // Max drawdown in this window
            let mut peak = cum[start];
            let mut max_dd = 0.0_f64;
            for j in start..=i {
                if cum[j] > peak {
                    peak = cum[j];
                }
                let dd = if peak > 0.0 {
                    (cum[j] - peak) / peak
                } else {
                    0.0
                };
                if dd < max_dd {
                    max_dd = dd;
                }
            }

            calmars[i] = if max_dd.abs() > 1e-12 {
                ann_return / max_dd.abs()
            } else {
                0.0
            };
        }
    }

    (sharpes, sortinos, calmars)
}

// ── Drawdown Analysis ───────────────────────────────────────────────────────

/// A single drawdown period with depth and timing.
#[derive(Debug, Clone)]
pub struct DrawdownPeriod {
    /// Index where drawdown started (equity left the peak).
    pub start_idx: usize,
    /// Index of the trough (deepest point).
    pub trough_idx: usize,
    /// Index where equity recovered to peak (None if still in drawdown at end).
    pub end_idx: Option<usize>,
    /// Maximum depth (negative fraction, e.g. -0.25 = 25% drawdown).
    pub depth: f64,
    /// Duration in bars from start to end (or to last bar if open).
    pub duration_bars: usize,
    /// Recovery bars from trough to end (None if still in drawdown).
    pub recovery_bars: Option<usize>,
}

/// Full drawdown analysis result.
#[derive(Debug, Clone)]
pub struct DrawdownAnalysis {
    pub max_drawdown: f64,
    pub avg_drawdown: f64,
    pub underwater_curve: Vec<f64>,
    pub periods: Vec<DrawdownPeriod>,
}

/// Compute full drawdown analysis: underwater curve + period detection.
///
/// Mirrors Python: `portfolio_analytics.py::compute_drawdown_analysis()`.
pub fn compute_drawdown_analysis(equity: &[f64]) -> DrawdownAnalysis {
    let underwater = portfolio_drawdown_series_impl(equity);
    let n = underwater.len();

    if n < 2 {
        return DrawdownAnalysis {
            max_drawdown: 0.0,
            avg_drawdown: 0.0,
            underwater_curve: underwater,
            periods: Vec::new(),
        };
    }

    let max_dd = underwater.iter().cloned().fold(0.0_f64, f64::min);
    let neg_vals: Vec<f64> = underwater.iter().filter(|&&v| v < 0.0).copied().collect();
    let avg_dd = if neg_vals.is_empty() {
        0.0
    } else {
        neg_vals.iter().sum::<f64>() / neg_vals.len() as f64
    };

    // Identify distinct drawdown periods
    let mut periods = Vec::new();
    let mut in_dd = false;
    let mut start_idx = 0;
    let mut trough_idx = 0;
    let mut trough_val = 0.0_f64;

    for i in 0..n {
        if underwater[i] < 0.0 {
            if !in_dd {
                in_dd = true;
                start_idx = i;
                trough_idx = i;
                trough_val = underwater[i];
            } else if underwater[i] < trough_val {
                trough_idx = i;
                trough_val = underwater[i];
            }
        } else if in_dd {
            periods.push(DrawdownPeriod {
                start_idx,
                trough_idx,
                end_idx: Some(i),
                depth: trough_val,
                duration_bars: i - start_idx,
                recovery_bars: Some(i - trough_idx),
            });
            in_dd = false;
        }
    }

    // Open drawdown at end
    if in_dd {
        periods.push(DrawdownPeriod {
            start_idx,
            trough_idx,
            end_idx: None,
            depth: trough_val,
            duration_bars: n - 1 - start_idx,
            recovery_bars: None,
        });
    }

    // Sort by depth (worst first)
    periods.sort_by(|a, b| a.depth.partial_cmp(&b.depth).unwrap_or(std::cmp::Ordering::Equal));

    DrawdownAnalysis {
        max_drawdown: max_dd,
        avg_drawdown: avg_dd,
        underwater_curve: underwater,
        periods,
    }
}

// ── Correlation Matrix ──────────────────────────────────────────────────────

/// Compute Pearson correlation matrix from multiple return series.
///
/// Input: `series[asset_idx][bar_idx]` — all series must be same length.
/// Returns `(correlation_matrix, diversification_score)`.
/// Diversification score = 1 - mean(|off-diagonal correlations|).
///
/// Mirrors Python: `portfolio_analytics.py::compute_correlations()` (math part).
pub fn compute_correlation_matrix(series: &[Vec<f64>]) -> (Vec<Vec<f64>>, f64) {
    let k = series.len();
    if k == 0 {
        return (Vec::new(), 0.0);
    }
    if k == 1 {
        return (vec![vec![1.0]], 0.0);
    }

    let n = series[0].len();
    // Compute means
    let means: Vec<f64> = series
        .iter()
        .map(|s| s.iter().sum::<f64>() / n.max(1) as f64)
        .collect();

    // Compute std devs
    let stds: Vec<f64> = series
        .iter()
        .zip(means.iter())
        .map(|(s, &m)| {
            let var = s.iter().map(|&v| (v - m).powi(2)).sum::<f64>() / (n.max(2) - 1) as f64;
            var.sqrt()
        })
        .collect();

    // Correlation matrix
    let mut corr = vec![vec![0.0; k]; k];
    for i in 0..k {
        corr[i][i] = 1.0;
        for j in (i + 1)..k {
            let cov: f64 = series[i]
                .iter()
                .zip(series[j].iter())
                .map(|(&a, &b)| (a - means[i]) * (b - means[j]))
                .sum::<f64>()
                / (n.max(2) - 1) as f64;
            let r = if stds[i] > 1e-12 && stds[j] > 1e-12 {
                cov / (stds[i] * stds[j])
            } else {
                0.0
            };
            corr[i][j] = r;
            corr[j][i] = r;
        }
    }

    // Diversification score = 1 - mean(|off-diagonal|)
    let mut off_diag_sum = 0.0;
    let mut off_diag_count = 0;
    for i in 0..k {
        for j in (i + 1)..k {
            off_diag_sum += corr[i][j].abs();
            off_diag_count += 1;
        }
    }
    let div_score = if off_diag_count > 0 {
        1.0 - off_diag_sum / off_diag_count as f64
    } else {
        0.0
    };

    (corr, div_score)
}

// ── HRP Weights ─────────────────────────────────────────────────────────────

/// Hierarchical Risk Parity weights via recursive bisection (Lopez de Prado).
///
/// Input: `returns[asset_idx][bar_idx]` — asset return series.
/// Returns weight per asset (sum = 1.0).
///
/// Uses single-linkage clustering on correlation-distance matrix,
/// then recursive bisection with inverse-variance portfolio sub-weights.
///
/// Mirrors Python: `portfolio_analytics.py::_hrp_weights()`.
pub fn hrp_weights(asset_returns: &[Vec<f64>]) -> Vec<f64> {
    let k = asset_returns.len();
    if k == 0 {
        return Vec::new();
    }
    if k == 1 {
        return vec![1.0];
    }

    let n = asset_returns[0].len();
    let (corr, _) = compute_correlation_matrix(asset_returns);

    // Covariance matrix
    let means: Vec<f64> = asset_returns
        .iter()
        .map(|s| s.iter().sum::<f64>() / n.max(1) as f64)
        .collect();
    let mut cov = vec![vec![0.0; k]; k];
    for i in 0..k {
        for j in i..k {
            let c: f64 = asset_returns[i]
                .iter()
                .zip(asset_returns[j].iter())
                .map(|(&a, &b)| (a - means[i]) * (b - means[j]))
                .sum::<f64>()
                / (n.max(2) - 1) as f64;
            cov[i][j] = c;
            cov[j][i] = c;
        }
    }

    // Distance matrix: sqrt(0.5 * (1 - corr))
    let mut dist = vec![vec![0.0; k]; k];
    for i in 0..k {
        for j in 0..k {
            dist[i][j] = (0.5 * (1.0 - corr[i][j])).max(0.0).sqrt();
        }
        dist[i][i] = 0.0;
    }

    // Single-linkage clustering → order (greedy nearest-neighbor chain)
    let order = single_linkage_order(&dist);

    // Recursive bisection
    let mut weights = vec![1.0_f64; k];

    fn ivp_var(cluster: &[usize], cov: &[Vec<f64>]) -> f64 {
        let m = cluster.len();
        if m == 0 {
            return 1.0;
        }
        // Inverse-variance portfolio variance
        let diag_inv: Vec<f64> = cluster
            .iter()
            .map(|&i| 1.0 / cov[i][i].max(1e-12))
            .collect();
        let sum_inv: f64 = diag_inv.iter().sum();
        let w: Vec<f64> = diag_inv.iter().map(|&d| d / sum_inv).collect();
        // w^T * Sigma * w
        let mut var = 0.0;
        for (ii, &ci) in cluster.iter().enumerate() {
            for (jj, &cj) in cluster.iter().enumerate() {
                var += w[ii] * w[jj] * cov[ci][cj];
            }
        }
        var
    }

    fn bisect(items: &[usize], weights: &mut [f64], cov: &[Vec<f64>]) {
        if items.len() <= 1 {
            return;
        }
        let mid = items.len() / 2;
        let (left, right) = items.split_at(mid);
        let var_l = ivp_var(left, cov);
        let var_r = ivp_var(right, cov);
        let alpha = 1.0 - var_l / (var_l + var_r + 1e-12);
        for &i in left {
            weights[i] *= alpha;
        }
        for &i in right {
            weights[i] *= 1.0 - alpha;
        }
        bisect(left, weights, cov);
        bisect(right, weights, cov);
    }

    bisect(&order, &mut weights, &cov);

    // Normalise
    let total: f64 = weights.iter().sum();
    if total > 0.0 {
        for w in &mut weights {
            *w /= total;
        }
    }

    weights
}

/// Single-linkage clustering → leaf order (greedy nearest-neighbor).
///
/// Returns ordered indices. Simple O(k³) implementation sufficient for ≤50 assets.
fn single_linkage_order(dist: &[Vec<f64>]) -> Vec<usize> {
    let k = dist.len();
    if k == 0 {
        return Vec::new();
    }

    // Agglomerative single-linkage: merge closest clusters
    let mut clusters: Vec<Vec<usize>> = (0..k).map(|i| vec![i]).collect();
    let mut active: Vec<bool> = vec![true; k];
    // Working distance matrix (mutable)
    let mut d: Vec<Vec<f64>> = dist.to_vec();

    for _ in 0..(k - 1) {
        // Find closest pair among active clusters
        let mut best_i = 0;
        let mut best_j = 1;
        let mut best_d = f64::INFINITY;
        for i in 0..clusters.len() {
            if !active[i] {
                continue;
            }
            for j in (i + 1)..clusters.len() {
                if !active[j] {
                    continue;
                }
                if d[i][j] < best_d {
                    best_d = d[i][j];
                    best_i = i;
                    best_j = j;
                }
            }
        }

        // Merge j into i
        let merged: Vec<usize> = clusters[best_j].clone();
        clusters[best_i].extend_from_slice(&merged);
        active[best_j] = false;

        // Update distances (single-linkage = min)
        for m in 0..clusters.len() {
            if !active[m] || m == best_i {
                continue;
            }
            let new_d = d[best_i][m].min(d[best_j][m]);
            d[best_i][m] = new_d;
            d[m][best_i] = new_d;
        }
    }

    // Find the one remaining active cluster
    for i in 0..clusters.len() {
        if active[i] {
            return clusters[i].clone();
        }
    }
    (0..k).collect()
}

// ── Beta ────────────────────────────────────────────────────────────────────

/// Beta — sensitivity of asset returns to market returns.
///
/// `beta = Cov(asset, market) / Var(market)`
///
/// Returns 0.0 if market variance ≈ 0.
pub fn beta(asset_returns: &[f64], market_returns: &[f64]) -> f64 {
    let n = asset_returns.len().min(market_returns.len());
    if n < 2 {
        return 0.0;
    }

    let nf = n as f64;
    let mean_a = asset_returns[..n].iter().sum::<f64>() / nf;
    let mean_m = market_returns[..n].iter().sum::<f64>() / nf;

    let mut cov = 0.0;
    let mut var_m = 0.0;
    for i in 0..n {
        let da = asset_returns[i] - mean_a;
        let dm = market_returns[i] - mean_m;
        cov += da * dm;
        var_m += dm * dm;
    }

    if var_m.abs() < 1e-14 {
        0.0
    } else {
        cov / var_m
    }
}

// ── Jensen's Alpha ─────────────────────────────────────────────────────────

/// Jensen's Alpha — excess return beyond CAPM prediction.
///
/// `alpha = mean(asset_returns) - (rf + beta * (mean(market_returns) - rf))`
pub fn jensens_alpha(asset_returns: &[f64], market_returns: &[f64], risk_free_rate: f64) -> f64 {
    let n = asset_returns.len().min(market_returns.len());
    if n < 2 {
        return 0.0;
    }

    let nf = n as f64;
    let mean_a = asset_returns[..n].iter().sum::<f64>() / nf;
    let mean_m = market_returns[..n].iter().sum::<f64>() / nf;
    let b = beta(asset_returns, market_returns);

    mean_a - (risk_free_rate + b * (mean_m - risk_free_rate))
}

// ── Calmar Ratio ──────────────────────────────────────────────────────────

/// Calmar Ratio — annualized return / |max drawdown|.
///
/// Returns 0.0 if max drawdown ≈ 0.
pub fn calmar_ratio(returns: &[f64]) -> f64 {
    if returns.len() < 2 {
        return 0.0;
    }

    let ann_return = helper::mean(returns) * 252.0;

    // Build equity curve from returns
    let mut equity = Vec::with_capacity(returns.len() + 1);
    equity.push(1.0);
    for &r in returns {
        let prev = *equity.last().unwrap();
        equity.push(prev * (1.0 + r));
    }

    let dd = portfolio_drawdown_series_impl(&equity);
    let max_dd = dd.iter().cloned().fold(0.0_f64, f64::min);

    if max_dd.abs() < 1e-14 {
        0.0
    } else {
        ann_return / max_dd.abs()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    // ── Drawdown ────────────────────────────────────────────────────────

    #[test]
    fn drawdown_basic() {
        let equity = vec![100.0, 110.0, 105.0, 120.0, 90.0];
        let result = portfolio_drawdown_series_impl(&equity);
        assert_eq!(result.len(), 5);
        assert_abs_diff_eq!(result[0], 0.0, epsilon = 1e-9); // first = peak
        assert_abs_diff_eq!(result[1], 0.0, epsilon = 1e-9); // new high
        // 105 vs peak 110 → (105-110)/110 = -0.04545...
        assert_abs_diff_eq!(result[2], -5.0 / 110.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[3], 0.0, epsilon = 1e-9); // new high
        // 90 vs peak 120 → (90-120)/120 = -0.25
        assert_abs_diff_eq!(result[4], -0.25, epsilon = 1e-9);
    }

    #[test]
    fn drawdown_inc_matches_batch() {
        let equity = vec![100.0, 110.0, 105.0, 120.0, 90.0, 115.0];
        let n = 5;

        let (batch, running_max) = drawdown_with_state(&equity[..n]);
        assert_eq!(batch.len(), n);

        // Extend by one
        let (inc_dd, new_max) = drawdown_inc(equity[n], running_max);

        let (ext_batch, ext_max) = drawdown_with_state(&equity);
        assert_abs_diff_eq!(inc_dd, *ext_batch.last().unwrap(), epsilon = 1e-9);
        assert_abs_diff_eq!(new_max, ext_max, epsilon = 1e-9);
    }

    #[test]
    fn drawdown_inc_multi_step() {
        let equity = vec![100.0, 110.0, 105.0, 120.0, 90.0, 115.0, 130.0, 125.0];
        let init_len = 4;

        let (batch_init, mut running_max) = drawdown_with_state(&equity[..init_len]);
        assert_eq!(batch_init.len(), init_len);

        for step in init_len..equity.len() {
            let (inc_dd, new_max) = drawdown_inc(equity[step], running_max);

            let (full_batch, _) = drawdown_with_state(&equity[..=step]);
            assert_abs_diff_eq!(inc_dd, *full_batch.last().unwrap(), epsilon = 1e-9);

            running_max = new_max;
        }
    }

    // ── Rolling Sharpe ──────────────────────────────────────────────────

    #[test]
    fn sharpe_basic() {
        // Constant returns → std = 0 → sharpe = 0
        let returns = vec![0.01; 30];
        let result = portfolio_rolling_sharpe_impl(&returns, 20, 0.0);
        assert_eq!(result.len(), 30);
        assert!(result[18].is_nan()); // before full window
        assert_abs_diff_eq!(result[19], 0.0, epsilon = 1e-9); // zero std
    }

    #[test]
    fn sharpe_inc_matches_batch() {
        let n = 50;
        let window = 20;
        let rf = 0.0001;
        let returns: Vec<f64> = (0..n).map(|i| 0.01 * (i as f64 * 0.5).sin()).collect();

        let (batch, ret_window) = sharpe_with_state(&returns, window, rf);
        assert_eq!(batch.len(), n);
        assert_eq!(ret_window.len(), window);

        // Extend by one
        let new_ret = 0.005;
        let (inc_sharpe, new_win) = sharpe_inc(new_ret, &ret_window, rf);

        let mut ext_returns = returns.clone();
        ext_returns.push(new_ret);
        let (ext_batch, _) = sharpe_with_state(&ext_returns, window, rf);

        assert_abs_diff_eq!(inc_sharpe, *ext_batch.last().unwrap(), epsilon = 1e-6);
        assert_eq!(new_win.len(), window);
    }

    #[test]
    fn sharpe_inc_multi_step() {
        let n = 50;
        let window = 20;
        let rf = 0.0;
        let all_returns: Vec<f64> = (0..n + 5)
            .map(|i| 0.02 * (i as f64 * 0.3).sin())
            .collect();

        let (batch_init, mut ret_win) = sharpe_with_state(&all_returns[..n], window, rf);
        assert_eq!(batch_init.len(), n);

        for step in 0..5 {
            let idx = n + step;
            let (inc_sharpe, new_win) = sharpe_inc(all_returns[idx], &ret_win, rf);

            let (full_batch, _) = sharpe_with_state(&all_returns[..=idx], window, rf);
            assert_abs_diff_eq!(inc_sharpe, *full_batch.last().unwrap(), epsilon = 1e-6);

            ret_win = new_win;
        }
    }

    // ── Kelly Fraction ──────────────────────────────────────────────────

    #[test]
    fn kelly_basic() {
        let returns = vec![0.05, -0.02, 0.03, 0.04, -0.01, 0.02];
        let kelly = portfolio_kelly_fraction_impl(&returns);
        // Positive edge → positive Kelly
        assert!(kelly > 0.0);
        assert!(kelly <= 2.0);
    }

    #[test]
    fn kelly_inc_matches_batch() {
        let returns = vec![0.05, -0.02, 0.03, 0.04, -0.01, 0.02, 0.01, -0.03];
        let n = 6;

        let (batch_kelly, sum, sum_sq, count) = kelly_with_state(&returns[..n]);
        assert!(batch_kelly != 0.0); // should have positive edge

        // Add two more returns incrementally
        let (inc_kelly_1, sum1, sum_sq1, n1) = kelly_inc(returns[n], sum, sum_sq, count);
        let (inc_kelly_2, _sum2, _sum_sq2, _n2) = kelly_inc(returns[n + 1], sum1, sum_sq1, n1);

        // Compare against batch on full series
        let full_kelly = portfolio_kelly_fraction_impl(&returns);
        assert_abs_diff_eq!(inc_kelly_2, full_kelly, epsilon = 1e-9);

        // Also verify intermediate step
        let mid_kelly = portfolio_kelly_fraction_impl(&returns[..n + 1]);
        assert_abs_diff_eq!(inc_kelly_1, mid_kelly, epsilon = 1e-9);
    }

    #[test]
    fn kelly_inc_from_scratch() {
        // Build up Kelly from zero by adding returns one at a time
        let rets = vec![0.05, -0.02, 0.03, 0.04, -0.01];
        let mut sum = 0.0;
        let mut sum_sq = 0.0;
        let mut n = 0;
        let mut kelly;

        for (i, &r) in rets.iter().enumerate() {
            let result = kelly_inc(r, sum, sum_sq, n);
            kelly = result.0;
            sum = result.1;
            sum_sq = result.2;
            n = result.3;

            // Compare against batch up to this point
            let batch_kelly = portfolio_kelly_fraction_impl(&rets[..=i]);
            assert_abs_diff_eq!(kelly, batch_kelly, epsilon = 1e-9);
        }
    }

    // ── Returns ────────────────────────────────────────────────────────

    #[test]
    fn returns_basic() {
        let prices = vec![100.0, 110.0, 105.0, 120.0];
        let result = returns(&prices);
        assert_eq!(result.len(), 4);
        assert_abs_diff_eq!(result[0], 0.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[1], 0.1, epsilon = 1e-9); // 10/100
        assert_abs_diff_eq!(result[2], -5.0 / 110.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result[3], 15.0 / 105.0, epsilon = 1e-9);
    }

    #[test]
    fn returns_inc_matches_batch() {
        let prices = vec![100.0, 110.0, 105.0, 120.0, 115.0];
        let batch = returns(&prices);
        for i in 1..prices.len() {
            let inc = returns_inc(prices[i], prices[i - 1]);
            assert_abs_diff_eq!(inc, batch[i], epsilon = 1e-9);
        }
    }

    // ── Rolling Sortino ────────────────────────────────────────────────

    #[test]
    fn sortino_basic() {
        // All positive returns → no downside → sortino = 0
        let rets = vec![0.01; 30];
        let result = rolling_sortino(&rets, 20, 0.0);
        assert_eq!(result.len(), 30);
        assert!(result[18].is_nan()); // before full window
        assert_abs_diff_eq!(result[19], 0.0, epsilon = 1e-9); // zero downside
    }

    #[test]
    fn sortino_inc_matches_batch() {
        let n = 50;
        let window = 20;
        let target = 0.0;
        let rets: Vec<f64> = (0..n).map(|i| 0.01 * (i as f64 * 0.5).sin()).collect();

        let (batch, ret_win) = sortino_with_state(&rets, window, target);
        assert_eq!(batch.len(), n);
        assert_eq!(ret_win.len(), window);

        let new_ret = -0.005;
        let (inc_sortino, new_win) = sortino_inc(new_ret, &ret_win, target);

        let mut ext = rets.clone();
        ext.push(new_ret);
        let (ext_batch, _) = sortino_with_state(&ext, window, target);

        assert_abs_diff_eq!(inc_sortino, *ext_batch.last().unwrap(), epsilon = 1e-6);
        assert_eq!(new_win.len(), window);
    }

    #[test]
    fn sortino_inc_multi_step() {
        let n = 50;
        let window = 20;
        let target = 0.0;
        let all_rets: Vec<f64> = (0..n + 5)
            .map(|i| 0.02 * (i as f64 * 0.3).sin())
            .collect();

        let (batch_init, mut ret_win) = sortino_with_state(&all_rets[..n], window, target);
        assert_eq!(batch_init.len(), n);

        for step in 0..5 {
            let idx = n + step;
            let (inc_sortino, new_win) = sortino_inc(all_rets[idx], &ret_win, target);

            let (full_batch, _) = sortino_with_state(&all_rets[..=idx], window, target);
            assert_abs_diff_eq!(inc_sortino, *full_batch.last().unwrap(), epsilon = 1e-6);

            ret_win = new_win;
        }
    }

    // ── Rolling Winrate ────────────────────────────────────────────────

    #[test]
    fn winrate_basic() {
        let rets = vec![0.05, -0.02, 0.03, 0.04, -0.01, 0.02, -0.03, 0.01, 0.06, -0.04];
        let result = rolling_winrate(&rets, 5);
        assert_eq!(result.len(), 10);
        // First 4 are NaN
        for i in 0..4 {
            assert!(result[i].is_nan());
        }
        // Window [0..5]: 3 positive (0.05, 0.03, 0.04) out of 5
        assert_abs_diff_eq!(result[4], 3.0 / 5.0, epsilon = 1e-9);
    }

    #[test]
    fn winrate_inc_matches_batch() {
        let rets = vec![0.05, -0.02, 0.03, 0.04, -0.01, 0.02, -0.03, 0.01, 0.06, -0.04];
        let window = 5;
        let n = 8;

        let (batch, ret_win, wins) = winrate_with_state(&rets[..n], window);
        assert_eq!(batch.len(), n);

        // Add two more returns
        let (wr1, win1, wins1) = winrate_inc(rets[n], &ret_win, wins);
        let (wr2, win2, wins2) = winrate_inc(rets[n + 1], &win1, wins1);

        let full = rolling_winrate(&rets, window);
        assert_abs_diff_eq!(wr1, full[n], epsilon = 1e-9);
        assert_abs_diff_eq!(wr2, full[n + 1], epsilon = 1e-9);
        assert_eq!(win2.len(), window);
        // wins2 should match manual count of last window (rets[5..10])
        let manual_wins = rets[5..10].iter().filter(|&&r| r > 0.0).count();
        assert_eq!(wins2, manual_wins);
    }

    #[test]
    fn winrate_all_wins() {
        let rets = vec![0.01; 10];
        let result = rolling_winrate(&rets, 5);
        for i in 4..10 {
            assert_abs_diff_eq!(result[i], 1.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn winrate_all_losses() {
        let rets = vec![-0.01; 10];
        let result = rolling_winrate(&rets, 5);
        for i in 4..10 {
            assert_abs_diff_eq!(result[i], 0.0, epsilon = 1e-9);
        }
    }

    // ── Rolling Metrics (combined) ────────────────────────────────────

    #[test]
    fn rolling_metrics_basic() {
        let equity: Vec<f64> = (0..60).map(|i| 100.0 + i as f64 * 0.5 + (i as f64 * 0.2).sin() * 3.0).collect();
        let (sharpes, sortinos, calmars) = compute_rolling_metrics(&equity, 20, 0.0);
        assert_eq!(sharpes.len(), equity.len());
        assert_eq!(sortinos.len(), equity.len());
        assert_eq!(calmars.len(), equity.len());
        // First 20 should be NaN
        assert!(sharpes[18].is_nan());
        // After window: should have valid values
        assert!(sharpes[25].is_finite());
    }

    // ── Drawdown Analysis ─────────────────────────────────────────────

    #[test]
    fn drawdown_analysis_basic() {
        let equity = vec![100.0, 110.0, 105.0, 120.0, 90.0, 95.0, 130.0, 125.0];
        let result = compute_drawdown_analysis(&equity);
        assert!(result.max_drawdown < 0.0);
        assert!(result.max_drawdown <= -0.20); // 90 vs 120 = -25%
        assert!(!result.periods.is_empty());
    }

    #[test]
    fn drawdown_analysis_no_drawdown() {
        let equity = vec![100.0, 110.0, 120.0, 130.0];
        let result = compute_drawdown_analysis(&equity);
        assert_abs_diff_eq!(result.max_drawdown, 0.0, epsilon = 1e-9);
        assert!(result.periods.is_empty());
    }

    // ── Correlations ──────────────────────────────────────────────────

    #[test]
    fn correlations_identity() {
        let series = vec![
            vec![1.0, 2.0, 3.0, 4.0, 5.0],
            vec![1.0, 2.0, 3.0, 4.0, 5.0],
        ];
        let (matrix, div_score) = compute_correlation_matrix(&series);
        assert_eq!(matrix.len(), 2);
        assert_abs_diff_eq!(matrix[0][0], 1.0, epsilon = 1e-6);
        assert_abs_diff_eq!(matrix[0][1], 1.0, epsilon = 1e-6);
        assert_abs_diff_eq!(div_score, 0.0, epsilon = 1e-6); // perfectly correlated
    }

    #[test]
    fn correlations_inverse() {
        let series = vec![
            vec![1.0, 2.0, 3.0, 4.0, 5.0],
            vec![5.0, 4.0, 3.0, 2.0, 1.0],
        ];
        let (matrix, div_score) = compute_correlation_matrix(&series);
        assert_abs_diff_eq!(matrix[0][1], -1.0, epsilon = 1e-6);
        assert_abs_diff_eq!(div_score, 0.0, epsilon = 1e-6); // 1 - |(-1)| = 0
    }

    // ── HRP Weights ───────────────────────────────────────────────────

    #[test]
    fn hrp_weights_basic() {
        // 3 assets, simple correlation structure
        let returns = vec![
            vec![0.01, -0.02, 0.03, 0.01, -0.01, 0.02, -0.01, 0.03, 0.01, -0.02],
            vec![0.02, -0.01, 0.01, 0.02, -0.02, 0.01, -0.02, 0.01, 0.02, -0.01],
            vec![-0.01, 0.03, -0.02, 0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02],
        ];
        let weights = hrp_weights(&returns);
        assert_eq!(weights.len(), 3);
        let sum: f64 = weights.iter().sum();
        assert_abs_diff_eq!(sum, 1.0, epsilon = 1e-6);
        for &w in &weights {
            assert!(w > 0.0 && w < 1.0);
        }
    }

    #[test]
    fn hrp_weights_single_asset() {
        let returns = vec![vec![0.01, -0.02, 0.03]];
        let weights = hrp_weights(&returns);
        assert_eq!(weights.len(), 1);
        assert_abs_diff_eq!(weights[0], 1.0, epsilon = 1e-9);
    }

    // ── Beta ──────────────────────────────────────────────────────────

    #[test]
    fn beta_market_is_self() {
        // Beta of market against itself = 1.0
        let rets = vec![0.01, -0.02, 0.03, 0.01, -0.01, 0.02];
        let b = beta(&rets, &rets);
        assert_abs_diff_eq!(b, 1.0, epsilon = 1e-9);
    }

    #[test]
    fn beta_double_leverage() {
        // If asset = 2 * market, beta should be 2.0
        let market = vec![0.01, -0.02, 0.03, 0.01, -0.01, 0.02];
        let asset: Vec<f64> = market.iter().map(|&r| 2.0 * r).collect();
        let b = beta(&asset, &market);
        assert_abs_diff_eq!(b, 2.0, epsilon = 1e-9);
    }

    #[test]
    fn beta_zero_variance_market() {
        let market = vec![0.01; 10];
        let asset = vec![0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.01, -0.01, 0.03, 0.02];
        let b = beta(&asset, &market);
        assert_abs_diff_eq!(b, 0.0, epsilon = 1e-9);
    }

    // ── Jensen's Alpha ────────────────────────────────────────────────

    #[test]
    fn jensens_alpha_perfect_capm() {
        // If asset perfectly follows CAPM: alpha = 0
        let market = vec![0.01, -0.02, 0.03, 0.01, -0.01, 0.02, -0.01, 0.03, 0.01, -0.02];
        let rf = 0.0;
        // asset = rf + 1.0 * (market - rf) = market → alpha = 0
        let alpha = jensens_alpha(&market, &market, rf);
        assert_abs_diff_eq!(alpha, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn jensens_alpha_positive_skill() {
        // Asset consistently outperforms market prediction
        let market = vec![0.01, -0.02, 0.03, 0.01, -0.01, 0.02];
        let asset: Vec<f64> = market.iter().map(|&r| r + 0.005).collect();
        let alpha = jensens_alpha(&asset, &market, 0.0);
        // alpha should be close to 0.005 (the consistent excess)
        assert!(alpha > 0.004);
        assert!(alpha < 0.006);
    }

    // ── Calmar Ratio ──────────────────────────────────────────────────

    #[test]
    fn calmar_ratio_all_positive() {
        // All positive returns → no drawdown → calmar = 0
        let rets = vec![0.01; 20];
        let calmar = calmar_ratio(&rets);
        assert_abs_diff_eq!(calmar, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn calmar_ratio_mixed() {
        // Mix of positive and negative returns
        let rets = vec![0.05, -0.03, 0.02, -0.04, 0.06, -0.02, 0.03, -0.01, 0.04, -0.05];
        let calmar = calmar_ratio(&rets);
        // mean > 0, there is drawdown → calmar should be positive and finite
        let mean_ret = rets.iter().sum::<f64>() / rets.len() as f64;
        assert!(mean_ret > 0.0, "mean should be positive for this test");
        assert!(calmar > 0.0, "calmar should be positive when mean > 0 and drawdown exists");
        assert!(calmar.is_finite());
    }

    #[test]
    fn calmar_ratio_too_short() {
        let rets = vec![0.01];
        assert_abs_diff_eq!(calmar_ratio(&rets), 0.0, epsilon = 1e-9);
    }
}
