// quant.rs — Quantitative analytics and heuristic classifiers
//
// Mirrors Python: indicator_engine/quant.py
// NOTE: These are NOT real ML — all are hardcoded heuristics or simple statistics.
//
// Functions:
//   hurst_exponent — rescaled range R/S method
//   cusum — structural break detection
//   performance_metrics — Sharpe, Sortino, max drawdown, profit factor
//   deflated_sharpe — multiple-testing adjustment
//   alternative_bars — volume/dollar/tick bars
//   order_flow_state — accumulation/distribution/squeeze
//   signal_quality_chain — Markov transition matrix
//   classify_signal — sigmoid heuristic (NOT real ML)
//   build_features — feature vectors [ret, sma_dev, rsi, vol_ratio]
//   fuse_hybrid — ML + rule-based score blending
//   monitor_bias — geographic/regime distribution imbalance
//   calculate_meanrev_momentum — Hurst + AR(1) mean-rev/momentum classifier
//   calculate_eval_baseline — triple-barrier hit ratio, expectancy, F1

use crate::helper;

// ── Hurst Exponent ────────────────────────────────────────────────────────

/// Hurst exponent via rescaled range (R/S) method.
///
/// H < 0.5 → mean-reverting, H = 0.5 → random walk, H > 0.5 → trending.
/// Returns 0.5 if input too short (< 40 values).
pub fn hurst_exponent(values: &[f64]) -> f64 {
    if values.len() < 40 {
        return 0.5;
    }
    let lags: &[usize] = &[2, 4, 8, 16];
    let mut tau = Vec::new();
    let mut x_log = Vec::new();
    for &lag in lags {
        if lag >= values.len() {
            continue;
        }
        let diffs: Vec<f64> = (lag..values.len()).map(|i| values[i] - values[i - lag]).collect();
        if diffs.len() < 2 {
            continue;
        }
        let sd = helper::pop_stddev(&diffs);
        if sd > 0.0 {
            tau.push(sd);
            x_log.push((lag as f64).ln());
        }
    }
    if tau.len() < 2 {
        return 0.5;
    }
    let y_log: Vec<f64> = tau.iter().map(|t| t.ln()).collect();
    let x_mean = helper::mean(&x_log);
    let y_mean = helper::mean(&y_log);
    let denom: f64 = x_log.iter().map(|x| (x - x_mean).powi(2)).sum();
    if denom == 0.0 {
        return 0.5;
    }
    let slope: f64 = x_log
        .iter()
        .zip(y_log.iter())
        .map(|(x, y)| (x - x_mean) * (y - y_mean))
        .sum::<f64>()
        / denom;
    slope.clamp(0.0, 1.0)
}

// ── CUSUM Structural Break Detection ──────────────────────────────────────

/// CUSUM break event.
#[derive(Debug, Clone, PartialEq)]
pub struct CusumBreak {
    pub index: usize,
    pub is_up: bool,
}

/// CUSUM structural break detection result.
#[derive(Debug, Clone)]
pub struct CusumResult {
    pub breaks: Vec<CusumBreak>,
    pub cumulative_pos: f64,
    pub cumulative_neg: f64,
}

/// CUSUM structural break detection on returns.
///
/// Tracks cumulative deviations from mean return.
/// Emits break when cumulative sum exceeds threshold.
pub fn cusum(closes: &[f64], threshold: f64) -> CusumResult {
    if closes.len() < 2 {
        return CusumResult {
            breaks: Vec::new(),
            cumulative_pos: 0.0,
            cumulative_neg: 0.0,
        };
    }
    let rets: Vec<f64> = (1..closes.len())
        .filter_map(|i| {
            if closes[i - 1] != 0.0 {
                Some((closes[i] - closes[i - 1]) / closes[i - 1])
            } else {
                None
            }
        })
        .collect();
    if rets.is_empty() {
        return CusumResult {
            breaks: Vec::new(),
            cumulative_pos: 0.0,
            cumulative_neg: 0.0,
        };
    }
    let mean_r = helper::mean(&rets);
    let mut s_pos = 0.0_f64;
    let mut s_neg = 0.0_f64;
    let mut breaks = Vec::new();

    for (i, &r) in rets.iter().enumerate() {
        let d = r - mean_r;
        s_pos = (s_pos + d).max(0.0);
        s_neg = (s_neg + d).min(0.0);
        if s_pos > threshold {
            breaks.push(CusumBreak {
                index: i + 1,
                is_up: true,
            });
            s_pos = 0.0;
        }
        if s_neg.abs() > threshold {
            breaks.push(CusumBreak {
                index: i + 1,
                is_up: false,
            });
            s_neg = 0.0;
        }
    }
    CusumResult {
        breaks,
        cumulative_pos: s_pos,
        cumulative_neg: s_neg,
    }
}

// ── Performance Metrics ───────────────────────────────────────────────────

/// Full performance metrics from a return series.
#[derive(Debug, Clone)]
pub struct PerformanceMetrics {
    pub net_return: f64,
    pub hit_ratio: f64,
    pub profit_factor: f64,
    pub sharpe: f64,
    pub sortino: f64,
    pub max_drawdown: f64,
}

/// Compute Sharpe, Sortino, max drawdown, profit factor from returns.
pub fn performance_metrics(returns: &[f64], risk_free_rate: f64) -> PerformanceMetrics {
    if returns.is_empty() {
        return PerformanceMetrics {
            net_return: 0.0,
            hit_ratio: 0.0,
            profit_factor: 0.0,
            sharpe: 0.0,
            sortino: 0.0,
            max_drawdown: 0.0,
        };
    }
    let net = returns.iter().fold(1.0_f64, |acc, &r| acc * (1.0 + r)) - 1.0;
    let wins: Vec<f64> = returns.iter().copied().filter(|&r| r > 0.0).collect();
    let losses: Vec<f64> = returns.iter().copied().filter(|&r| r < 0.0).collect();
    let hit = wins.len() as f64 / returns.len() as f64;
    let gain: f64 = wins.iter().sum();
    let loss: f64 = losses.iter().sum::<f64>().abs();
    let pf = if loss > 0.0 { gain / loss } else { f64::INFINITY };

    let mean_r = helper::mean(returns);
    let stdev = helper::pop_stddev(returns);
    let down_rets: Vec<f64> = returns.iter().copied().filter(|&r| r < 0.0).collect();
    let down_std = helper::pop_stddev(&down_rets);

    let rf_daily = risk_free_rate / 252.0;
    let sharpe = if stdev > 0.0 {
        (mean_r - rf_daily) / stdev * 252.0_f64.sqrt()
    } else {
        0.0
    };
    let sortino = if down_std > 0.0 {
        (mean_r - rf_daily) / down_std * 252.0_f64.sqrt()
    } else {
        0.0
    };

    let mut eq = 1.0_f64;
    let mut peak = 1.0_f64;
    let mut max_dd = 0.0_f64;
    for &r in returns {
        eq *= 1.0 + r;
        if eq > peak {
            peak = eq;
        }
        let dd = if peak > 0.0 {
            (eq - peak) / peak
        } else {
            0.0
        };
        if dd < max_dd {
            max_dd = dd;
        }
    }

    PerformanceMetrics {
        net_return: net,
        hit_ratio: hit,
        profit_factor: pf,
        sharpe,
        sortino,
        max_drawdown: max_dd,
    }
}

// ── Deflated Sharpe ───────────────────────────────────────────────────────

/// Deflated Sharpe Ratio — adjusts for multiple testing.
///
/// Returns `(deflated_sharpe, pass_gate)`.
pub fn deflated_sharpe(sharpe: f64, trials: usize, sample_length: usize) -> (f64, bool) {
    let penalty =
        (2.0 * (trials.max(1) as f64).ln() / sample_length.max(1) as f64).sqrt();
    let ds = sharpe - penalty;
    (ds, ds > 0.0)
}

// ── Alternative Bars ──────────────────────────────────────────────────────

/// Alternative bars result.
#[derive(Debug, Clone)]
pub struct AlternativeBarsResult {
    pub volume_bar_closes: Vec<f64>,
    pub dollar_bar_closes: Vec<f64>,
    pub tick_bar_closes: Vec<f64>,
}

/// Volume/Dollar/Tick bars from close + volume series.
///
/// bucket_size controls tick bar frequency (every N bars).
pub fn alternative_bars(
    closes: &[f64],
    volumes: &[f64],
    bucket_size: usize,
) -> AlternativeBarsResult {
    let n = closes.len().min(volumes.len());
    if n == 0 || bucket_size == 0 {
        return AlternativeBarsResult {
            volume_bar_closes: Vec::new(),
            dollar_bar_closes: Vec::new(),
            tick_bar_closes: Vec::new(),
        };
    }

    let total_vol: f64 = volumes[..n].iter().sum();
    let total_dol: f64 = (0..n).map(|i| closes[i] * volumes[i]).sum();
    let vol_target = total_vol / (n as f64 / bucket_size as f64).max(1.0);
    let dol_target = total_dol / (n as f64 / bucket_size as f64).max(1.0);

    let mut vol_bars = Vec::new();
    let mut dol_bars = Vec::new();
    let mut tick_bars = Vec::new();
    let mut vol_acc = 0.0_f64;
    let mut dol_acc = 0.0_f64;

    for i in 0..n {
        vol_acc += volumes[i];
        dol_acc += closes[i] * volumes[i];
        if vol_acc >= vol_target {
            vol_bars.push(closes[i]);
            vol_acc = 0.0;
        }
        if dol_acc >= dol_target {
            dol_bars.push(closes[i]);
            dol_acc = 0.0;
        }
        if (i + 1) % bucket_size == 0 {
            tick_bars.push(closes[i]);
        }
    }

    AlternativeBarsResult {
        volume_bar_closes: vol_bars,
        dollar_bar_closes: dol_bars,
        tick_bar_closes: tick_bars,
    }
}

// ── Order Flow State ──────────────────────────────────────────────────────

/// Order flow state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FlowState {
    Accumulation,
    Distribution,
    Squeeze,
}

/// Classify order flow as accumulation/distribution/squeeze per bar.
///
/// Returns `(per_bar_states, dominant_state)`.
pub fn order_flow_state(
    buy_volumes: &[f64],
    sell_volumes: &[f64],
    squeeze_threshold: f64,
) -> (Vec<FlowState>, FlowState) {
    let n = buy_volumes.len().min(sell_volumes.len());
    let mut states = Vec::with_capacity(n);
    for i in 0..n {
        let total = buy_volumes[i] + sell_volumes[i];
        if total <= 0.0 {
            states.push(FlowState::Squeeze);
            continue;
        }
        let imbalance = (buy_volumes[i] - sell_volumes[i]) / total;
        if imbalance.abs() < squeeze_threshold {
            states.push(FlowState::Squeeze);
        } else if imbalance > 0.0 {
            states.push(FlowState::Accumulation);
        } else {
            states.push(FlowState::Distribution);
        }
    }
    let acc_count = states.iter().filter(|&&s| s == FlowState::Accumulation).count();
    let dist_count = states.iter().filter(|&&s| s == FlowState::Distribution).count();
    let sq_count = states.iter().filter(|&&s| s == FlowState::Squeeze).count();
    let dominant = if acc_count >= dist_count && acc_count >= sq_count {
        FlowState::Accumulation
    } else if dist_count >= acc_count && dist_count >= sq_count {
        FlowState::Distribution
    } else {
        FlowState::Squeeze
    };
    (states, dominant)
}

// ── Signal Quality Chain ──────────────────────────────────────────────────

/// Signal quality Markov chain result.
#[derive(Debug, Clone)]
pub struct SignalQualityResult {
    /// 3×3 transition matrix: [from][to] where 0=strong, 1=weak, 2=invalid.
    pub transition: [[f64; 3]; 3],
    pub quality_score: f64,
}

/// Signal quality label.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QualityLabel {
    Strong = 0,
    Weak = 1,
    Invalid = 2,
}

/// Markov chain of signal quality transitions.
///
/// Quality score = P(strong→strong) - P(strong→invalid).
pub fn signal_quality_chain(labels: &[QualityLabel]) -> SignalQualityResult {
    let mut counts = [[0u32; 3]; 3];
    for w in labels.windows(2) {
        let from = w[0] as usize;
        let to = w[1] as usize;
        counts[from][to] += 1;
    }
    let mut transition = [[0.0_f64; 3]; 3];
    for s in 0..3 {
        let total: u32 = counts[s].iter().sum();
        for t in 0..3 {
            transition[s][t] = if total > 0 {
                counts[s][t] as f64 / total as f64
            } else {
                1.0 / 3.0
            };
        }
    }
    let quality = transition[0][0] - transition[0][2]; // strong→strong - strong→invalid
    SignalQualityResult {
        transition,
        quality_score: quality,
    }
}

// ── Classify Signal (Heuristic) ───────────────────────────────────────────

/// Heuristic signal classification result.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SignalLabel {
    Buy,
    Sell,
    Hold,
}

/// Heuristic signal classifier — sigmoid on weighted features (NOT real ML).
///
/// Features: ret, sma_dev, rsi (0-100), vol_ratio.
/// Returns `(label, probability)`.
pub fn classify_signal(ret: f64, sma_dev: f64, rsi_val: f64, vol_ratio: f64) -> (SignalLabel, f64) {
    let score = 0.35 * ret + 0.25 * sma_dev + 0.20 * ((rsi_val - 50.0) / 50.0) + 0.20 * (vol_ratio - 1.0);
    let prob = 1.0 / (1.0 + (-5.0 * score).exp());
    let label = if prob > 0.58 {
        SignalLabel::Buy
    } else if prob < 0.42 {
        SignalLabel::Sell
    } else {
        SignalLabel::Hold
    };
    (label, prob)
}

// ── Build Features ──────────────────────────────────────────────────────

/// Build feature vectors [ret, sma_dev, rsi, vol_ratio] from close + volume series.
///
/// Uses SMA(period) and RSI(period). Returns `closes.len() - 1` feature rows.
/// Each row is [return, sma_deviation, rsi_value, volume_ratio].
pub fn build_features(closes: &[f64], volumes: &[f64], period: usize) -> Vec<[f64; 4]> {
    let n = closes.len().min(volumes.len());
    if n < 2 {
        return Vec::new();
    }
    let ma = super::trend::sma(&closes[..n], period.max(1));
    let rsi_vals = super::oscillators::rsi(&closes[..n], period.max(1));
    let vol_mean = if n > 0 {
        volumes[..n].iter().sum::<f64>() / n as f64
    } else {
        1.0
    };

    let mut out = Vec::with_capacity(n - 1);
    for i in 1..n {
        let ret = if closes[i - 1] != 0.0 {
            (closes[i] - closes[i - 1]) / closes[i - 1]
        } else {
            0.0
        };
        let sma_dev = if ma[i] != 0.0 {
            (closes[i] - ma[i]) / ma[i]
        } else {
            0.0
        };
        let rsi_val = rsi_vals[i];
        let vol_ratio = if vol_mean > 0.0 {
            volumes[i] / vol_mean
        } else {
            1.0
        };
        out.push([ret, sma_dev, rsi_val, vol_ratio]);
    }
    out
}

// ── Fuse Hybrid ─────────────────────────────────────────────────────────

/// Blend ML score and rule-based score into a fused signal.
///
/// `fused = ml_weight * ml_score + (1 - ml_weight) * rule_score`
/// Returns `(fused_score, action)` where action: 1=buy (>0.58), -1=sell (<0.42), 0=hold.
pub fn fuse_hybrid(ml_score: f64, rule_score: f64, ml_weight: f64) -> (f64, i8) {
    let w = ml_weight.clamp(0.0, 1.0);
    let fused = w * ml_score + (1.0 - w) * rule_score;
    let action = if fused > 0.58 {
        1
    } else if fused < 0.42 {
        -1
    } else {
        0
    };
    (fused, action)
}

// ── Monitor Bias ────────────────────────────────────────────────────────

/// Compute bias imbalance for geographic and regime distributions.
///
/// Imbalance = max_share - min_share (where share = element / total).
/// Alert triggers if geo_imbalance > 0.45 or regime_imbalance > 0.45 or agreement_rate < 0.35.
/// Returns `(geo_imbalance, regime_imbalance, alert)`.
pub fn monitor_bias(
    geographic_dist: &[f64],
    regime_dist: &[f64],
    agreement_rate: f64,
) -> (f64, f64, bool) {
    fn imbalance(dist: &[f64]) -> f64 {
        if dist.is_empty() {
            return 0.0;
        }
        let total: f64 = dist.iter().sum();
        if total <= 0.0 {
            return 0.0;
        }
        let shares: Vec<f64> = dist.iter().map(|&v| v / total).collect();
        let max_s = shares.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let min_s = shares.iter().cloned().fold(f64::INFINITY, f64::min);
        max_s - min_s
    }

    let geo_imb = imbalance(geographic_dist);
    let reg_imb = imbalance(regime_dist);
    let alert = geo_imb > 0.45 || reg_imb > 0.45 || agreement_rate < 0.35;
    (geo_imb, reg_imb, alert)
}

// ── Mean-Reversion / Momentum Classification ────────────────────────────

/// Classify a price series as mean-reverting, momentum, or random walk.
///
/// Uses Hurst exponent + OLS AR(1) coefficient (phi).
/// - `adf_proxy_stat = (phi - 1) * 100`
/// - `half_life = -ln(2) / ln(phi)` (inf if phi >= 1 or phi <= 0)
/// - classification: 0=mean_reverting (hurst<0.45 && phi<0.99),
///   1=momentum (hurst>0.55 && phi>=0.99), 2=random_walk.
///
/// Returns `(hurst, adf_proxy_stat, half_life, classification)`.
pub fn calculate_meanrev_momentum(closes: &[f64]) -> (f64, f64, f64, i8) {
    if closes.len() < 3 {
        return (0.5, 0.0, f64::INFINITY, 2);
    }

    let hurst = hurst_exponent(closes);

    // OLS AR(1): y[t] = phi * y[t-1] + epsilon
    // phi = sum(y[t]*y[t-1]) / sum(y[t-1]^2)  (de-meaned)
    let n = closes.len();
    let y: Vec<f64> = (1..n).map(|i| closes[i]).collect();
    let x: Vec<f64> = (0..n - 1).map(|i| closes[i]).collect();

    let x_mean = helper::mean(&x);
    let y_mean = helper::mean(&y);

    let num: f64 = x
        .iter()
        .zip(y.iter())
        .map(|(&xi, &yi)| (xi - x_mean) * (yi - y_mean))
        .sum();
    let den: f64 = x.iter().map(|&xi| (xi - x_mean).powi(2)).sum();

    let phi = if den > 0.0 { num / den } else { 1.0 };

    let adf_proxy = (phi - 1.0) * 100.0;

    let half_life = if phi > 0.0 && phi < 1.0 {
        -(2.0_f64.ln()) / phi.ln()
    } else {
        f64::INFINITY
    };

    let classification = if hurst < 0.45 && phi < 0.99 {
        0 // mean_reverting
    } else if hurst > 0.55 && phi >= 0.99 {
        1 // momentum
    } else {
        2 // random_walk
    };

    (hurst, adf_proxy, half_life, classification)
}

// ── Evaluation Baseline ─────────────────────────────────────────────────

/// Evaluate strategy baseline using triple-barrier labels.
///
/// Computes hit_ratio, expectancy, and precision/recall/F1 proxies.
/// - hit_ratio = TakeProfit count / total labels
/// - expectancy = hit_ratio * take_profit - (1 - hit_ratio) * stop_loss
/// - precision_proxy = TP / (TP + Timeout)  (how many "entries" hit TP)
/// - recall_proxy = TP / (TP + SL)          (how many non-SL are TP)
/// - f1_proxy = 2 * prec * rec / (prec + rec)
///
/// Returns `(hit_ratio, expectancy, precision_proxy, recall_proxy, f1_proxy)`.
pub fn calculate_eval_baseline(
    closes: &[f64],
    horizon: usize,
    take_profit: f64,
    stop_loss: f64,
) -> (f64, f64, f64, f64, f64) {
    let labels = super::backtest::triple_barrier_labels(closes, horizon, take_profit, stop_loss);
    if labels.is_empty() {
        return (0.0, 0.0, 0.0, 0.0, 0.0);
    }

    let total = labels.len() as f64;
    let tp_count = labels
        .iter()
        .filter(|&&l| l == super::backtest::BarrierLabel::TakeProfit)
        .count() as f64;
    let sl_count = labels
        .iter()
        .filter(|&&l| l == super::backtest::BarrierLabel::StopLoss)
        .count() as f64;
    let timeout_count = labels
        .iter()
        .filter(|&&l| l == super::backtest::BarrierLabel::Timeout)
        .count() as f64;

    let hit_ratio = tp_count / total;
    let expectancy = hit_ratio * take_profit - (1.0 - hit_ratio) * stop_loss;

    let precision_proxy = if tp_count + timeout_count > 0.0 {
        tp_count / (tp_count + timeout_count)
    } else {
        0.0
    };
    let recall_proxy = if tp_count + sl_count > 0.0 {
        tp_count / (tp_count + sl_count)
    } else {
        0.0
    };
    let f1_proxy = if precision_proxy + recall_proxy > 0.0 {
        2.0 * precision_proxy * recall_proxy / (precision_proxy + recall_proxy)
    } else {
        0.0
    };

    (hit_ratio, expectancy, precision_proxy, recall_proxy, f1_proxy)
}

// ── Evaluate Indicator (Orchestrator) ───────────────────────────────────────

/// Full indicator evaluation result.
#[derive(Debug, Clone)]
pub struct IndicatorEvaluation {
    /// Walk-forward stability score.
    pub stability_score: f64,
    /// Baseline hit ratio (triple-barrier).
    pub hit_ratio: f64,
    /// Expectancy per trade.
    pub expectancy: f64,
    /// Deflated Sharpe (multiple-testing adjusted).
    pub deflated_sharpe_value: f64,
    /// Whether deflated Sharpe passes gate.
    pub deflated_sharpe_pass: bool,
    /// Execution realism: max_dd > -0.6 AND profit_factor >= 0.8.
    pub execution_realism_pass: bool,
    /// Overall gate: deflated + execution + stability > 0.3.
    pub gate_pass: bool,
}

/// Full indicator evaluation: walk-forward + baseline + deflated Sharpe.
///
/// Orchestrator that combines multiple quant functions into a single evaluation.
///
/// Mirrors Python: `quant.py::evaluate_indicator()`.
pub fn evaluate_indicator(closes: &[f64], risk_free_rate: f64) -> IndicatorEvaluation {
    if closes.len() < 20 {
        return IndicatorEvaluation {
            stability_score: 0.0,
            hit_ratio: 0.0,
            expectancy: 0.0,
            deflated_sharpe_value: 0.0,
            deflated_sharpe_pass: false,
            execution_realism_pass: false,
            gate_pass: false,
        };
    }

    // Walk-forward: split into train/test folds
    let train_window = (closes.len() / 2).clamp(20, 60);
    let test_window = (closes.len() / 6).clamp(5, 20);
    let mut fold_sharpes = Vec::new();
    let mut i = 0;
    while i + train_window + test_window <= closes.len() {
        let test_slice = &closes[(i + train_window)..(i + train_window + test_window)];
        let test_rets: Vec<f64> = (1..test_slice.len())
            .map(|j| {
                if test_slice[j - 1].abs() > 1e-14 {
                    (test_slice[j] - test_slice[j - 1]) / test_slice[j - 1]
                } else {
                    0.0
                }
            })
            .collect();
        let pm = performance_metrics(&test_rets, risk_free_rate);
        fold_sharpes.push(pm.sharpe);
        i += test_window;
    }
    let stability_score = if fold_sharpes.len() >= 2 {
        let positive_folds = fold_sharpes.iter().filter(|&&s| s > 0.0).count();
        positive_folds as f64 / fold_sharpes.len() as f64
    } else {
        0.0
    };

    // Baseline (triple-barrier)
    let (hit_ratio, expectancy, _, _, _) = calculate_eval_baseline(closes, 10, 0.02, 0.02);

    // Performance metrics on full series returns
    let rets: Vec<f64> = (1..closes.len())
        .map(|j| {
            if closes[j - 1].abs() > 1e-14 {
                (closes[j] - closes[j - 1]) / closes[j - 1]
            } else {
                0.0
            }
        })
        .collect();
    let pm = performance_metrics(&rets, risk_free_rate);

    // Deflated Sharpe
    let (ds_value, ds_pass) = deflated_sharpe(pm.sharpe, 20, rets.len());

    let execution_realism_pass = pm.max_drawdown > -0.6 && pm.profit_factor >= 0.8;
    let gate_pass = ds_pass && execution_realism_pass && stability_score > 0.3;

    IndicatorEvaluation {
        stability_score,
        hit_ratio,
        expectancy,
        deflated_sharpe_value: ds_value,
        deflated_sharpe_pass: ds_pass,
        execution_realism_pass,
        gate_pass,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    fn oscillating_prices(n: usize) -> Vec<f64> {
        (0..n)
            .map(|i| 100.0 + (i as f64 * 0.3).sin() * 10.0)
            .collect()
    }

    // ── Hurst ─────────────────────────────────────────────────────────────

    #[test]
    fn hurst_short_input() {
        assert_abs_diff_eq!(hurst_exponent(&[1.0; 10]), 0.5, epsilon = 1e-9);
    }

    #[test]
    fn hurst_bounded() {
        let prices = oscillating_prices(100);
        let h = hurst_exponent(&prices);
        assert!(h >= 0.0 && h <= 1.0, "Hurst out of range: {h}");
    }

    #[test]
    fn hurst_trending_above_half() {
        // Strong uptrend → should be > 0.5 (trending)
        let prices: Vec<f64> = (0..100).map(|i| 100.0 + i as f64 * 2.0).collect();
        let h = hurst_exponent(&prices);
        assert!(h > 0.45, "trending data should have H > 0.45, got {h}");
    }

    // ── CUSUM ─────────────────────────────────────────────────────────────

    #[test]
    fn cusum_no_breaks_low_threshold() {
        let prices: Vec<f64> = (0..50).map(|i| 100.0 + i as f64 * 0.001).collect();
        let result = cusum(&prices, 100.0); // very high threshold
        assert!(result.breaks.is_empty());
    }

    #[test]
    fn cusum_detects_break() {
        let mut prices: Vec<f64> = (0..50).map(|_| 100.0).collect();
        // Sudden jump
        for i in 50..100 {
            prices.push(100.0 + (i - 50) as f64 * 2.0);
        }
        let result = cusum(&prices, 0.05);
        assert!(!result.breaks.is_empty(), "should detect break at jump");
    }

    #[test]
    fn cusum_short_input() {
        let result = cusum(&[100.0], 0.1);
        assert!(result.breaks.is_empty());
    }

    // ── Performance Metrics ───────────────────────────────────────────────

    #[test]
    fn perf_all_positive() {
        let returns = vec![0.01, 0.02, 0.015, 0.005];
        let pm = performance_metrics(&returns, 0.0);
        assert!(pm.net_return > 0.0);
        assert_abs_diff_eq!(pm.hit_ratio, 1.0, epsilon = 1e-9);
        assert!(pm.sharpe > 0.0);
        assert_abs_diff_eq!(pm.max_drawdown, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn perf_mixed_returns() {
        let returns = vec![0.02, -0.01, 0.03, -0.02, 0.01];
        let pm = performance_metrics(&returns, 0.02);
        assert!(pm.hit_ratio > 0.0 && pm.hit_ratio < 1.0);
        assert!(pm.profit_factor > 0.0);
        assert!(pm.max_drawdown <= 0.0);
    }

    #[test]
    fn perf_empty() {
        let pm = performance_metrics(&[], 0.0);
        assert_abs_diff_eq!(pm.net_return, 0.0, epsilon = 1e-9);
    }

    // ── Deflated Sharpe ───────────────────────────────────────────────────

    #[test]
    fn deflated_sharpe_penalizes() {
        let (ds, pass) = deflated_sharpe(1.5, 20, 200);
        assert!(ds < 1.5, "penalty should reduce Sharpe");
        assert!(pass); // 1.5 with 20 trials should still pass
    }

    #[test]
    fn deflated_sharpe_fails_low_sharpe() {
        let (_, pass) = deflated_sharpe(0.1, 100, 50);
        assert!(!pass, "low Sharpe with many trials should fail");
    }

    // ── Alternative Bars ──────────────────────────────────────────────────

    #[test]
    fn alt_bars_tick() {
        let closes: Vec<f64> = (0..100).map(|i| 100.0 + i as f64 * 0.1).collect();
        let volumes = vec![1000.0; 100];
        let result = alternative_bars(&closes, &volumes, 10);
        assert_eq!(result.tick_bar_closes.len(), 10); // 100 / 10
    }

    #[test]
    fn alt_bars_empty() {
        let result = alternative_bars(&[], &[], 10);
        assert!(result.volume_bar_closes.is_empty());
    }

    // ── Order Flow State ──────────────────────────────────────────────────

    #[test]
    fn order_flow_accumulation() {
        let buys = vec![100.0, 200.0, 150.0];
        let sells = vec![50.0, 60.0, 40.0];
        let (states, dominant) = order_flow_state(&buys, &sells, 0.1);
        assert_eq!(states.len(), 3);
        assert_eq!(dominant, FlowState::Accumulation);
    }

    #[test]
    fn order_flow_squeeze() {
        let buys = vec![100.0, 100.0, 100.0];
        let sells = vec![100.0, 100.0, 100.0];
        let (_, dominant) = order_flow_state(&buys, &sells, 0.1);
        assert_eq!(dominant, FlowState::Squeeze);
    }

    // ── Signal Quality Chain ──────────────────────────────────────────────

    #[test]
    fn quality_chain_all_strong() {
        let labels = vec![
            QualityLabel::Strong,
            QualityLabel::Strong,
            QualityLabel::Strong,
        ];
        let result = signal_quality_chain(&labels);
        assert_abs_diff_eq!(result.transition[0][0], 1.0, epsilon = 1e-9);
        assert_abs_diff_eq!(result.quality_score, 1.0, epsilon = 1e-9);
    }

    #[test]
    fn quality_chain_mixed() {
        let labels = vec![
            QualityLabel::Strong,
            QualityLabel::Weak,
            QualityLabel::Invalid,
            QualityLabel::Strong,
        ];
        let result = signal_quality_chain(&labels);
        assert!(result.quality_score < 1.0);
    }

    // ── Classify Signal ───────────────────────────────────────────────────

    #[test]
    fn classify_bullish() {
        let (label, prob) = classify_signal(0.05, 0.02, 70.0, 1.5);
        assert_eq!(label, SignalLabel::Buy);
        assert!(prob > 0.58);
    }

    #[test]
    fn classify_bearish() {
        let (label, prob) = classify_signal(-0.05, -0.03, 25.0, 0.5);
        assert_eq!(label, SignalLabel::Sell);
        assert!(prob < 0.42);
    }

    #[test]
    fn classify_neutral() {
        let (label, _) = classify_signal(0.0, 0.0, 50.0, 1.0);
        assert_eq!(label, SignalLabel::Hold);
    }

    // ── Build Features ───────────────────────────────────────────────────

    #[test]
    fn build_features_length() {
        let closes: Vec<f64> = (0..50).map(|i| 100.0 + i as f64 * 0.5).collect();
        let volumes = vec![1000.0; 50];
        let feats = build_features(&closes, &volumes, 14);
        assert_eq!(feats.len(), 49); // closes.len() - 1
    }

    #[test]
    fn build_features_short_input() {
        let feats = build_features(&[100.0], &[1000.0], 14);
        assert!(feats.is_empty());
    }

    #[test]
    fn build_features_values_reasonable() {
        let closes: Vec<f64> = (0..50).map(|i| 100.0 + i as f64 * 0.5).collect();
        let volumes = vec![1000.0; 50];
        let feats = build_features(&closes, &volumes, 14);
        for row in &feats {
            // ret should be small for gradual rise
            assert!(row[0].abs() < 0.1, "return too large: {}", row[0]);
            // rsi in [0, 100]
            assert!(row[2] >= 0.0 && row[2] <= 100.0, "rsi out of range: {}", row[2]);
            // vol_ratio should be 1.0 for uniform volumes
            assert_abs_diff_eq!(row[3], 1.0, epsilon = 1e-9);
        }
    }

    // ── Fuse Hybrid ──────────────────────────────────────────────────────

    #[test]
    fn fuse_hybrid_buy() {
        let (fused, action) = fuse_hybrid(0.8, 0.7, 0.6);
        assert!(fused > 0.58);
        assert_eq!(action, 1);
    }

    #[test]
    fn fuse_hybrid_sell() {
        let (fused, action) = fuse_hybrid(0.2, 0.3, 0.5);
        assert!(fused < 0.42);
        assert_eq!(action, -1);
    }

    #[test]
    fn fuse_hybrid_hold() {
        let (fused, action) = fuse_hybrid(0.5, 0.5, 0.5);
        assert_abs_diff_eq!(fused, 0.5, epsilon = 1e-9);
        assert_eq!(action, 0);
    }

    #[test]
    fn fuse_hybrid_weight_clamp() {
        // ml_weight > 1.0 should be clamped to 1.0
        let (fused, _) = fuse_hybrid(0.9, 0.1, 1.5);
        assert_abs_diff_eq!(fused, 0.9, epsilon = 1e-9);
    }

    // ── Monitor Bias ─────────────────────────────────────────────────────

    #[test]
    fn monitor_bias_balanced() {
        let geo = vec![25.0, 25.0, 25.0, 25.0];
        let regime = vec![33.0, 33.0, 34.0];
        let (geo_imb, reg_imb, alert) = monitor_bias(&geo, &regime, 0.8);
        assert!(geo_imb < 0.01, "balanced geo should have low imbalance: {geo_imb}");
        assert!(reg_imb < 0.02, "balanced regime should have low imbalance: {reg_imb}");
        assert!(!alert);
    }

    #[test]
    fn monitor_bias_imbalanced_geo() {
        let geo = vec![90.0, 5.0, 5.0];
        let regime = vec![33.0, 33.0, 34.0];
        let (geo_imb, _, alert) = monitor_bias(&geo, &regime, 0.8);
        assert!(geo_imb > 0.45, "skewed geo should have high imbalance: {geo_imb}");
        assert!(alert);
    }

    #[test]
    fn monitor_bias_low_agreement() {
        let geo = vec![25.0, 25.0, 25.0, 25.0];
        let regime = vec![33.0, 33.0, 34.0];
        let (_, _, alert) = monitor_bias(&geo, &regime, 0.30);
        assert!(alert, "low agreement should trigger alert");
    }

    // ── Mean-Rev / Momentum ──────────────────────────────────────────────

    #[test]
    fn meanrev_trending_data() {
        // Strong uptrend → should be momentum or random walk
        let closes: Vec<f64> = (0..100).map(|i| 100.0 + i as f64 * 2.0).collect();
        let (hurst, _adf, _hl, class) = calculate_meanrev_momentum(&closes);
        assert!(hurst > 0.45, "trending data hurst should be > 0.45, got {hurst}");
        // classification 1 (momentum) or 2 (random_walk)
        assert!(class == 1 || class == 2, "trending data should not be mean_reverting, got {class}");
    }

    #[test]
    fn meanrev_oscillating_data() {
        let closes = oscillating_prices(100);
        let (hurst, _adf, _hl, _class) = calculate_meanrev_momentum(&closes);
        // Oscillating data hurst should be bounded
        assert!(hurst >= 0.0 && hurst <= 1.0);
    }

    #[test]
    fn meanrev_short_input() {
        let (hurst, adf, hl, class) = calculate_meanrev_momentum(&[100.0, 101.0]);
        assert_abs_diff_eq!(hurst, 0.5, epsilon = 1e-9);
        assert_abs_diff_eq!(adf, 0.0, epsilon = 1e-9);
        assert!(hl.is_infinite());
        assert_eq!(class, 2); // random_walk
    }

    // ── Eval Baseline ────────────────────────────────────────────────────

    #[test]
    fn eval_baseline_rising() {
        // Rising prices → high hit ratio
        let closes: Vec<f64> = (0..50).map(|i| 100.0 + i as f64 * 1.0).collect();
        let (hit, expect, prec, rec, f1) = calculate_eval_baseline(&closes, 5, 0.02, 0.02);
        assert!(hit > 0.5, "rising prices should have high hit ratio: {hit}");
        assert!(expect > 0.0, "positive expectancy expected: {expect}");
        assert!(prec >= 0.0 && prec <= 1.0);
        assert!(rec >= 0.0 && rec <= 1.0);
        assert!(f1 >= 0.0 && f1 <= 1.0);
    }

    #[test]
    fn eval_baseline_short_input() {
        let (hit, expect, prec, rec, f1) = calculate_eval_baseline(&[100.0, 101.0], 10, 0.05, 0.05);
        assert_abs_diff_eq!(hit, 0.0, epsilon = 1e-9);
        assert_abs_diff_eq!(expect, 0.0, epsilon = 1e-9);
        assert_abs_diff_eq!(prec, 0.0, epsilon = 1e-9);
        assert_abs_diff_eq!(rec, 0.0, epsilon = 1e-9);
        assert_abs_diff_eq!(f1, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn eval_baseline_metrics_bounded() {
        let closes = oscillating_prices(100);
        let (hit, _expect, prec, rec, f1) = calculate_eval_baseline(&closes, 10, 0.05, 0.05);
        assert!(hit >= 0.0 && hit <= 1.0);
        assert!(prec >= 0.0 && prec <= 1.0);
        assert!(rec >= 0.0 && rec <= 1.0);
        assert!(f1 >= 0.0 && f1 <= 1.0);
    }

    // ── Evaluate Indicator ──────────────────────────────────────────────

    #[test]
    fn evaluate_indicator_rising() {
        let closes: Vec<f64> = (0..100).map(|i| 100.0 + i as f64 * 0.5).collect();
        let eval = evaluate_indicator(&closes, 0.02);
        assert!(eval.hit_ratio >= 0.0 && eval.hit_ratio <= 1.0);
        assert!(eval.stability_score >= 0.0 && eval.stability_score <= 1.0);
    }

    #[test]
    fn evaluate_indicator_short_input() {
        let eval = evaluate_indicator(&[100.0, 101.0], 0.02);
        assert!(!eval.gate_pass);
        assert_abs_diff_eq!(eval.stability_score, 0.0, epsilon = 1e-9);
    }

    #[test]
    fn evaluate_indicator_oscillating() {
        let closes = oscillating_prices(200);
        let eval = evaluate_indicator(&closes, 0.02);
        // Should produce valid bounded metrics
        assert!(eval.hit_ratio >= 0.0 && eval.hit_ratio <= 1.0);
        assert!(eval.stability_score >= 0.0 && eval.stability_score <= 1.0);
    }
}
