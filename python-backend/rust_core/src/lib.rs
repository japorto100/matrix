use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::HashMap;

pub mod error;
pub mod helper;
pub mod indicators;
mod config;
mod ohlcv_cache;

// ── Indicator imports from category modules ──────────────────────────────────
use crate::indicators::trend::{sma, ema, wma, hma, smma, kama, alma, iwma, ols_ma, ichimoku_series};
use crate::indicators::oscillators::{rsi, macd_components, stochastic, adx_components, composite_sma50_slope_norm_impl, calculate_heartbeat_impl};
use crate::indicators::volatility::{atr, bb_bandwidth, bb_percent_b, keltner_channels};
use crate::indicators::volume::{vwap_series, obv_series, cmf_series};
use crate::indicators::portfolio::{
    portfolio_drawdown_series_impl, portfolio_rolling_sharpe_impl, portfolio_kelly_fraction_impl,
};

// ── Batch indicator dispatch ─────────────────────────────────────────────────

fn calculate_indicators_batch_impl(
    _timestamps: &[i64],
    _opens: &[f64],
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    volumes: &[f64],
    indicators: &[String],
) -> Result<HashMap<String, Vec<f64>>, &'static str> {
    let len = closes.len();
    if len == 0 {
        return Ok(HashMap::new());
    }
    if volumes.len() != len {
        return Err("volumes length must match closes");
    }

    let mut out: HashMap<String, Vec<f64>> = HashMap::new();
    for indicator in indicators {
        let key = indicator.trim().to_lowercase();
        if let Some(period_str) = key.strip_prefix("sma_") {
            let period = period_str.parse::<usize>().unwrap_or(1).max(1);
            out.insert(indicator.clone(), sma(closes, period));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("ema_") {
            let period = period_str.parse::<usize>().unwrap_or(1).max(1);
            out.insert(indicator.clone(), ema(closes, period));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("rsi_") {
            let period = period_str.parse::<usize>().unwrap_or(14).max(1);
            out.insert(indicator.clone(), rsi(closes, period));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("rvol_") {
            let period = period_str.parse::<usize>().unwrap_or(20).max(1);
            let baseline = sma(volumes, period);
            let mut series = Vec::with_capacity(len);
            for i in 0..len {
                let denom = baseline[i].abs().max(1e-9);
                series.push(volumes[i] / denom);
            }
            out.insert(indicator.clone(), series);
            continue;
        }
        if let Some(period_str) = key.strip_prefix("atr_") {
            let period = period_str.parse::<usize>().unwrap_or(14).max(1);
            if highs.len() == len && lows.len() == len {
                out.insert(indicator.clone(), atr(highs, lows, closes, period));
            }
            continue;
        }
        if let Some(period_str) = key.strip_prefix("bb_bw_") {
            let period = period_str.parse::<usize>().unwrap_or(20).max(2);
            out.insert(indicator.clone(), bb_bandwidth(closes, period, 2.0));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("bb_pctb_") {
            let period = period_str.parse::<usize>().unwrap_or(20).max(2);
            out.insert(indicator.clone(), bb_percent_b(closes, period, 2.0));
            continue;
        }
        if key == "close" {
            out.insert(indicator.clone(), closes.to_vec());
            continue;
        }
        if let Some(period_str) = key.strip_prefix("wma_") {
            let period = period_str.parse::<usize>().unwrap_or(1).max(1);
            out.insert(indicator.clone(), wma(closes, period));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("hma_") {
            let period = period_str.parse::<usize>().unwrap_or(9).max(1);
            out.insert(indicator.clone(), hma(closes, period));
            continue;
        }
        // macd — inserts macd_line, macd_signal, macd_hist
        if key == "macd" || key.starts_with("macd_") {
            let (line, sig, hist) = macd_components(closes, 12, 26, 9);
            out.insert("macd_line".to_string(), line);
            out.insert("macd_signal".to_string(), sig);
            out.insert("macd_hist".to_string(), hist);
            continue;
        }
        // stoch_N — inserts stoch_k_N, stoch_d_N
        if let Some(period_str) = key.strip_prefix("stoch_") {
            let period = period_str.parse::<usize>().unwrap_or(14).max(1);
            if highs.len() == len && lows.len() == len {
                let (k, d) = stochastic(highs, lows, closes, period, 3);
                out.insert(format!("stoch_k_{period}"), k);
                out.insert(format!("stoch_d_{period}"), d);
            }
            continue;
        }
        // adx_N — inserts adx_N, di_plus_N, di_minus_N
        if let Some(period_str) = key.strip_prefix("adx_") {
            let period = period_str.parse::<usize>().unwrap_or(14).max(1);
            if highs.len() == len && lows.len() == len {
                let (adx_v, dip, dim) = adx_components(highs, lows, closes, period);
                out.insert(format!("adx_{period}"), adx_v);
                out.insert(format!("di_plus_{period}"), dip);
                out.insert(format!("di_minus_{period}"), dim);
            }
            continue;
        }
        if let Some(period_str) = key.strip_prefix("smma_") {
            let period = period_str.parse::<usize>().unwrap_or(14).max(1);
            out.insert(indicator.clone(), smma(closes, period));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("kama_") {
            let period = period_str.parse::<usize>().unwrap_or(10).max(1);
            out.insert(indicator.clone(), kama(closes, period, 2, 30));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("alma_") {
            let period = period_str.parse::<usize>().unwrap_or(9).max(1);
            out.insert(indicator.clone(), alma(closes, period, 0.85, 6.0));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("iwma_") {
            let period = period_str.parse::<usize>().unwrap_or(10).max(1);
            out.insert(indicator.clone(), iwma(closes, period));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("ols_") {
            let period = period_str.parse::<usize>().unwrap_or(14).max(1);
            out.insert(indicator.clone(), ols_ma(closes, period));
            continue;
        }
        if key == "ichimoku" {
            if highs.len() == len && lows.len() == len {
                let (tenkan, kijun, span_a, span_b, chikou) = ichimoku_series(highs, lows, closes);
                out.insert("ichimoku_tenkan".to_string(), tenkan);
                out.insert("ichimoku_kijun".to_string(), kijun);
                out.insert("ichimoku_span_a".to_string(), span_a);
                out.insert("ichimoku_span_b".to_string(), span_b);
                out.insert("ichimoku_chikou".to_string(), chikou);
            }
            continue;
        }
        if key == "vwap" {
            if highs.len() == len && lows.len() == len {
                out.insert(indicator.clone(), vwap_series(highs, lows, closes, volumes));
            }
            continue;
        }
        if let Some(period_str) = key.strip_prefix("keltner_") {
            let period = period_str.parse::<usize>().unwrap_or(20).max(1);
            if highs.len() == len && lows.len() == len {
                let (upper, mid, lower) = keltner_channels(highs, lows, closes, period, period, 1.5);
                out.insert(format!("keltner_upper_{period}"), upper);
                out.insert(format!("keltner_mid_{period}"), mid);
                out.insert(format!("keltner_lower_{period}"), lower);
            }
            continue;
        }
        if key == "obv" {
            out.insert(indicator.clone(), obv_series(closes, volumes));
            continue;
        }
        if let Some(period_str) = key.strip_prefix("cmf_") {
            let period = period_str.parse::<usize>().unwrap_or(20).max(1);
            if highs.len() == len && lows.len() == len {
                out.insert(indicator.clone(), cmf_series(highs, lows, closes, volumes, period));
            }
            continue;
        }
    }
    Ok(out)
}

// ── PyO3 wrappers ────────────────────────────────────────────────────────────

#[pyfunction]
fn composite_sma50_slope_norm(py: Python<'_>, closes: Vec<f64>) -> PyResult<(f64, f64, f64)> {
    py.detach(move || composite_sma50_slope_norm_impl(&closes))
        .map_err(|msg| PyValueError::new_err(msg.to_string()))
}

#[pyfunction]
fn calculate_heartbeat(
    py: Python<'_>,
    closes: Vec<f64>,
    highs: Vec<f64>,
    lows: Vec<f64>,
    sensitivity: f64,
) -> PyResult<f64> {
    py.detach(move || calculate_heartbeat_impl(&closes, &highs, &lows, sensitivity))
        .map_err(|msg| PyValueError::new_err(msg.to_string()))
}

#[pyfunction]
fn calculate_indicators_batch(
    py: Python<'_>,
    timestamps: Vec<i64>,
    opens: Vec<f64>,
    highs: Vec<f64>,
    lows: Vec<f64>,
    closes: Vec<f64>,
    volumes: Vec<f64>,
    indicators: Vec<String>,
) -> PyResult<HashMap<String, Vec<f64>>> {
    py.detach(move || {
        calculate_indicators_batch_impl(
            &timestamps,
            &opens,
            &highs,
            &lows,
            &closes,
            &volumes,
            &indicators,
        )
    })
    .map_err(|msg| PyValueError::new_err(msg.to_string()))
}

#[pyfunction]
fn redb_cache_set(
    py: Python<'_>,
    path: String,
    key: String,
    payload_json: String,
    ttl_ms: u64,
) -> PyResult<()> {
    py.detach(move || ohlcv_cache::cache_set(&path, &key, &payload_json, ttl_ms))
        .map_err(|msg| PyValueError::new_err(msg.to_string()))
}

#[pyfunction]
fn redb_cache_get(
    py: Python<'_>,
    path: String,
    key: String,
    now_ms: Option<u64>,
) -> PyResult<Option<String>> {
    py.detach(move || ohlcv_cache::cache_get(&path, &key, now_ms))
        .map_err(|msg| PyValueError::new_err(msg.to_string()))
}

// ── Agent Hotpath Helpers (private, not exported) ─────────────────────────────

fn contains_whole_word(haystack: &str, needle: &str) -> bool {
    if needle.is_empty() {
        return false;
    }
    let h = haystack.as_bytes();
    let n = needle.as_bytes();
    let nlen = n.len();
    if h.len() < nlen {
        return false;
    }
    for i in 0..=(h.len() - nlen) {
        if &h[i..i + nlen] == n {
            let before_ok = i == 0 || !h[i - 1].is_ascii_alphanumeric() && h[i - 1] != b'_';
            let after_ok =
                i + nlen >= h.len() || !h[i + nlen].is_ascii_alphanumeric() && h[i + nlen] != b'_';
            if before_ok && after_ok {
                return true;
            }
        }
    }
    false
}

fn normalize_content_hash(content: &str) -> String {
    let joined = content
        .to_lowercase()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");
    joined.chars().take(64).collect()
}

fn tokenize_words(text: &str) -> Vec<String> {
    text.to_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .collect()
}

// ── Agent Hotpath Impl Functions ───────────────────────────────────────────────

fn extract_entities_from_text_impl(text: &str) -> String {
    let mut entities: Vec<serde_json::Value> = Vec::new();

    for word in text.split_whitespace() {
        let clean = word.trim_matches(|c: char| c == ',' || c == '.' || c == '!' || c == '?');
        if let Some(ticker) = clean.strip_prefix('$') {
            if ticker.len() >= 2
                && ticker.len() <= 6
                && ticker.chars().all(|c| c.is_ascii_uppercase())
            {
                entities.push(serde_json::json!({"type": "ticker", "value": ticker}));
            }
        } else if clean.contains('/') {
            let mut parts = clean.splitn(2, '/');
            if let (Some(base), Some(quote)) = (parts.next(), parts.next()) {
                if base.len() >= 2
                    && base.len() <= 6
                    && quote.len() >= 2
                    && quote.len() <= 6
                    && base.chars().all(|c| c.is_ascii_uppercase())
                    && quote.chars().all(|c| c.is_ascii_uppercase())
                {
                    entities.push(serde_json::json!({"type": "ticker", "value": clean}));
                }
            }
        }
    }

    let text_lower = text.to_lowercase();

    const COUNTRIES: &[&str] = &[
        "usa", "china", "europe", "germany", "france", "japan", "russia", "india",
        "brazil", "canada", "australia", "switzerland", "israel", "iran", "ukraine",
        "taiwan", "singapore",
    ];
    for country in COUNTRIES {
        if contains_whole_word(&text_lower, country) {
            entities.push(serde_json::json!({"type": "country", "value": *country}));
        }
    }

    const METRICS: &[&str] = &[
        "rsi", "macd", "atr", "ema", "sma", "vwap", "adx", "roc", "inflation", "gdp",
        "cpi", "ppi", "pce", "unemployment", "nfp", "fomc", "yield", "spread",
        "volatility", "correlation", "volume",
    ];
    for metric in METRICS {
        if contains_whole_word(&text_lower, metric) {
            entities.push(serde_json::json!({"type": "metric", "value": *metric}));
        }
    }

    const ASSET_CLASSES: &[&str] = &[
        "crypto", "forex", "equities", "bonds", "commodities", "futures", "options",
        "etf", "reit", "rates",
    ];
    for asset in ASSET_CLASSES {
        if contains_whole_word(&text_lower, asset) {
            entities.push(serde_json::json!({"type": "asset_class", "value": *asset}));
        }
    }

    serde_json::to_string(&entities).unwrap_or_else(|_| "[]".to_string())
}

fn dedup_context_fragments_impl(fragments_json: &str, _threshold: f64) -> Result<String, String> {
    let mut fragments: Vec<serde_json::Value> =
        serde_json::from_str(fragments_json).map_err(|e| format!("invalid JSON: {e}"))?;

    fragments.sort_by(|a, b| {
        let ra = a.get("relevance_f64").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let rb = b.get("relevance_f64").and_then(|v| v.as_f64()).unwrap_or(0.0);
        rb.partial_cmp(&ra).unwrap_or(std::cmp::Ordering::Equal)
    });

    let mut seen = std::collections::HashSet::<String>::new();
    let mut result: Vec<serde_json::Value> = Vec::with_capacity(fragments.len());

    for fragment in fragments {
        let content_str = fragment
            .get("content_str")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let hash = normalize_content_hash(content_str);
        if seen.insert(hash) {
            result.push(fragment);
        }
    }

    serde_json::to_string(&result).map_err(|e| format!("serialization error: {e}"))
}

fn score_tools_for_query_impl(
    query: &str,
    tool_names: &[String],
    tool_descriptions: &[String],
) -> Vec<f64> {
    let query_tokens = tokenize_words(query);
    let total = query_tokens.len();
    let query_lower = query.to_lowercase();

    tool_names
        .iter()
        .zip(tool_descriptions.iter())
        .map(|(name, desc)| {
            if total == 0 {
                return 0.0;
            }
            let desc_tokens = tokenize_words(desc);
            let matched = query_tokens
                .iter()
                .filter(|qt| desc_tokens.contains(qt))
                .count();
            let mut score = matched as f64 / total as f64;

            let name_lower = name.to_lowercase();
            if !name_lower.is_empty() && query_lower.contains(name_lower.as_str()) {
                score += 0.25;
            }
            score.clamp(0.0, 1.0)
        })
        .collect()
}

// ── Agent Hotpath PyO3 Wrappers ────────────────────────────────────────────────

#[pyfunction]
fn extract_entities_from_text(py: Python<'_>, text: String) -> PyResult<String> {
    Ok(py.detach(move || extract_entities_from_text_impl(&text)))
}

#[pyfunction]
fn dedup_context_fragments(
    py: Python<'_>,
    fragments_json: String,
    threshold: f64,
) -> PyResult<String> {
    py.detach(move || dedup_context_fragments_impl(&fragments_json, threshold))
        .map_err(|msg| PyValueError::new_err(msg))
}

#[pyfunction]
fn score_tools_for_query(
    py: Python<'_>,
    query: String,
    tool_names: Vec<String>,
    tool_descriptions: Vec<String>,
) -> PyResult<Vec<f64>> {
    Ok(py.detach(move || {
        score_tools_for_query_impl(&query, &tool_names, &tool_descriptions)
    }))
}

// ── Portfolio Analytics PyO3 Wrappers ────────────────────────────────────────

#[pyfunction]
fn portfolio_drawdown_series(py: Python<'_>, equity: Vec<f64>) -> PyResult<Vec<f64>> {
    Ok(py.detach(move || portfolio_drawdown_series_impl(&equity)))
}

#[pyfunction]
fn portfolio_rolling_sharpe(
    py: Python<'_>,
    returns: Vec<f64>,
    window: usize,
    rf_daily: f64,
) -> PyResult<Vec<f64>> {
    Ok(py.detach(move || portfolio_rolling_sharpe_impl(&returns, window, rf_daily)))
}

#[pyfunction]
fn portfolio_kelly_fraction(py: Python<'_>, returns: Vec<f64>) -> PyResult<f64> {
    Ok(py.detach(move || portfolio_kelly_fraction_impl(&returns)))
}

// ── Module registration ──────────────────────────────────────────────────────

#[pymodule]
fn tradeviewfusion_rust_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(composite_sma50_slope_norm, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_heartbeat, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_indicators_batch, m)?)?;
    m.add_function(wrap_pyfunction!(redb_cache_set, m)?)?;
    m.add_function(wrap_pyfunction!(redb_cache_get, m)?)?;
    m.add_function(wrap_pyfunction!(extract_entities_from_text, m)?)?;
    m.add_function(wrap_pyfunction!(dedup_context_fragments, m)?)?;
    m.add_function(wrap_pyfunction!(score_tools_for_query, m)?)?;
    m.add_function(wrap_pyfunction!(portfolio_drawdown_series, m)?)?;
    m.add_function(wrap_pyfunction!(portfolio_rolling_sharpe, m)?)?;
    m.add_function(wrap_pyfunction!(portfolio_kelly_fraction, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_abs_diff_eq;

    #[test]
    fn test_sma_basic() {
        let values = vec![1.0, 2.0, 3.0, 4.0];
        let got = sma(&values, 2);
        assert_eq!(got.len(), 4);
        assert_abs_diff_eq!(got[0], 1.0, epsilon = 1e-12);
        assert_abs_diff_eq!(got[1], 1.5, epsilon = 1e-12);
        assert_abs_diff_eq!(got[2], 2.5, epsilon = 1e-12);
        assert_abs_diff_eq!(got[3], 3.5, epsilon = 1e-12);
    }

    #[test]
    fn test_composite_slope_norm_impl() {
        let mut closes = Vec::new();
        for i in 0..80 {
            closes.push(100.0 + (i as f64 * 0.5));
        }
        let (slope_value, slope_norm, last_sma) =
            composite_sma50_slope_norm_impl(&closes).expect("slope calc should work");
        assert!(last_sma > 0.0);
        assert!(slope_value > 0.0);
        assert!(slope_norm > 0.0);
    }

    #[test]
    fn test_calculate_heartbeat_impl_returns_bounded_score() {
        let mut closes = Vec::new();
        let mut highs = Vec::new();
        let mut lows = Vec::new();
        for i in 0..200 {
            let x = i as f64 / 5.0;
            let c = 100.0 + x.sin() * 2.0 + (i as f64 * 0.01);
            closes.push(c);
            highs.push(c + 0.3);
            lows.push(c - 0.3);
        }
        let score = calculate_heartbeat_impl(&closes, &highs, &lows, 0.05).expect("heartbeat");
        assert!((0.0..=1.0).contains(&score));
    }

    #[test]
    fn test_calculate_indicators_batch_impl_basic() {
        let closes = vec![1.0, 2.0, 3.0, 4.0];
        let volumes = vec![10.0, 20.0, 30.0, 40.0];
        let out = calculate_indicators_batch_impl(
            &[],
            &[],
            &[],
            &[],
            &closes,
            &volumes,
            &[
                "sma_2".to_string(),
                "rvol_2".to_string(),
                "close".to_string(),
            ],
        )
        .expect("batch");
        assert!(out.contains_key("sma_2"));
        assert!(out.contains_key("rvol_2"));
        assert!(out.contains_key("close"));
        assert_eq!(out["close"], closes);
    }

    #[test]
    fn test_rsi_flat_series_is_neutral() {
        // All same price → no gains or losses.
        // Pre-warmup (indices 0..period-1): initialised to 50.0 (neutral/undefined).
        // From index `period` onwards: avg_loss==0 → RSI = 100.0 (no selling pressure).
        let period = 14;
        let values = vec![10.0; 20];
        let got = rsi(&values, period);
        assert_eq!(got.len(), 20);
        for v in got.iter().take(period) {
            assert_abs_diff_eq!(*v, 50.0, epsilon = 1e-9);
        }
        for v in got.iter().skip(period) {
            assert_abs_diff_eq!(*v, 100.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn test_rsi_rising_series_above_50() {
        let values: Vec<f64> = (0..50).map(|i| 100.0 + i as f64).collect();
        let got = rsi(&values, 14);
        for v in got.iter().skip(14) {
            assert!(*v > 50.0, "RSI should be > 50 in rising market, got {v}");
        }
    }

    #[test]
    fn test_atr_constant_candles_equals_zero() {
        let n = 30;
        let highs = vec![100.0; n];
        let lows = vec![100.0; n];
        let closes = vec![100.0; n];
        let got = atr(&highs, &lows, &closes, 14);
        assert_eq!(got.len(), n);
        for v in &got {
            assert_abs_diff_eq!(*v, 0.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn test_atr_known_value() {
        // Bar0: H=105 L=95 C=100 → no prev close, tr=0 (first bar)
        // Bar1: H=108 L=97 C=105 → tr = max(11, |108-100|, |97-100|) = max(11,8,3) = 11
        // Bar2: H=110 L=100 C=108 → tr = max(10, |110-105|, |100-105|) = max(10,5,5) = 10
        // ATR(2) uses Wilder's EMA: span = 2*period-1 = 3, alpha = 2/(3+1) = 0.5
        // EMA[0] = 0
        // EMA[1] = 0 * 0.5 + 11 * 0.5 = 5.5
        // EMA[2] = 5.5 * 0.5 + 10 * 0.5 = 7.75
        let highs = vec![105.0, 108.0, 110.0];
        let lows = vec![95.0, 97.0, 100.0];
        let closes = vec![100.0, 105.0, 108.0];
        let got = atr(&highs, &lows, &closes, 2);
        assert_eq!(got.len(), 3);
        assert_abs_diff_eq!(got[0], 0.0, epsilon = 1e-9);
        assert_abs_diff_eq!(got[1], 5.5, epsilon = 1e-9);
        assert_abs_diff_eq!(got[2], 7.75, epsilon = 1e-9);
    }

    #[test]
    fn test_bb_bandwidth_constant_is_zero() {
        let values = vec![50.0; 30];
        let got = bb_bandwidth(&values, 20, 2.0);
        assert_eq!(got.len(), 30);
        for v in &got {
            assert_abs_diff_eq!(*v, 0.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn test_bb_bandwidth_positive() {
        let values: Vec<f64> = (0..40).map(|i| 100.0 + (i as f64 * 0.1)).collect();
        let got = bb_bandwidth(&values, 20, 2.0);
        assert!(got.iter().skip(20).all(|v| *v >= 0.0));
    }

    #[test]
    fn test_bb_percent_b_at_midband_is_half() {
        let values = vec![100.0; 30];
        let got = bb_percent_b(&values, 20, 2.0);
        for v in &got {
            assert_abs_diff_eq!(*v, 0.5, epsilon = 1e-9);
        }
    }

    #[test]
    fn test_wma_period2_manual() {
        let values = vec![10.0, 20.0, 30.0];
        let got = wma(&values, 2);
        assert_abs_diff_eq!(got[1], (10.0 * 1.0 + 20.0 * 2.0) / 3.0, epsilon = 1e-9);
        assert_abs_diff_eq!(got[2], (20.0 * 1.0 + 30.0 * 2.0) / 3.0, epsilon = 1e-9);
    }

    #[test]
    fn test_wma_rising_above_sma() {
        let values: Vec<f64> = (0..20).map(|i| i as f64).collect();
        let w = wma(&values, 5);
        let s = sma(&values, 5);
        for i in 5..20 {
            assert!(w[i] >= s[i], "WMA should be >= SMA for rising series at idx {i}");
        }
    }

    #[test]
    fn test_hma_length_preserved() {
        let values: Vec<f64> = (0..20).map(|i| 100.0 + i as f64).collect();
        let got = hma(&values, 9);
        assert_eq!(got.len(), 20);
    }

    #[test]
    fn test_hma_uptrend_rising_tail() {
        let values: Vec<f64> = (0..30).map(|i| 10.0 + i as f64).collect();
        let got = hma(&values, 9);
        let n = got.len();
        assert!(
            got[n - 1] > got[n - 2],
            "HMA tail should be rising in a pure uptrend"
        );
    }

    #[test]
    fn test_macd_hist_is_line_minus_signal() {
        let values: Vec<f64> = (0..50).map(|i| 100.0 + i as f64 * 0.5).collect();
        let (line, sig, hist) = macd_components(&values, 12, 26, 9);
        for i in 0..hist.len() {
            assert_abs_diff_eq!(hist[i], line[i] - sig[i], epsilon = 1e-12);
        }
    }

    #[test]
    fn test_macd_uptrend_positive_line() {
        let values: Vec<f64> = (0..80).map(|i| 100.0 + i as f64).collect();
        let (line, _, _) = macd_components(&values, 12, 26, 9);
        for v in line.iter().skip(30) {
            assert!(*v > 0.0, "MACD line should be positive in strong uptrend, got {v}");
        }
    }

    #[test]
    fn test_stochastic_flat_is_50() {
        let n = 20;
        let closes = vec![50.0; n];
        let highs = vec![50.0; n];
        let lows = vec![50.0; n];
        let (k, d) = stochastic(&highs, &lows, &closes, 14, 3);
        assert_eq!(k.len(), n);
        for v in &k {
            assert_abs_diff_eq!(*v, 50.0, epsilon = 1e-9);
        }
        for v in &d {
            assert_abs_diff_eq!(*v, 50.0, epsilon = 1e-9);
        }
    }

    #[test]
    fn test_stochastic_uptrend_k_near_100() {
        let n = 30;
        let closes: Vec<f64> = (0..n).map(|i| 100.0 + i as f64).collect();
        let highs: Vec<f64> = closes.iter().map(|c| c + 0.5).collect();
        let lows: Vec<f64> = closes.iter().map(|c| c - 0.5).collect();
        let (k, _) = stochastic(&highs, &lows, &closes, 14, 3);
        for v in k.iter().skip(14) {
            assert!(*v > 80.0, "Stochastic %K should be near 100 in uptrend, got {v}");
        }
    }

    #[test]
    fn test_batch_ema_rsi_atr_bb() {
        let n = 50;
        let closes: Vec<f64> = (0..n).map(|i| 100.0 + i as f64 * 0.5).collect();
        let highs: Vec<f64> = closes.iter().map(|c| c + 1.0).collect();
        let lows: Vec<f64> = closes.iter().map(|c| c - 1.0).collect();
        let volumes = vec![1000.0_f64; n];
        let timestamps: Vec<i64> = (0..n as i64).collect();

        let out = calculate_indicators_batch_impl(
            &timestamps,
            &[],
            &highs,
            &lows,
            &closes,
            &volumes,
            &[
                "ema_10".to_string(),
                "rsi_14".to_string(),
                "atr_14".to_string(),
                "bb_bw_20".to_string(),
                "bb_pctb_20".to_string(),
            ],
        )
        .expect("batch ok");

        assert_eq!(out["ema_10"].len(), n);
        assert_eq!(out["rsi_14"].len(), n);
        assert_eq!(out["atr_14"].len(), n);
        assert_eq!(out["bb_bw_20"].len(), n);
        assert_eq!(out["bb_pctb_20"].len(), n);

        // ATR for H=c+1, L=c-1: TR[0]=0, TR[i≥1]=2.
        // EMA span = 2*14-1 = 27, alpha = 1/14. Convergence to 2.0 is slow:
        // at n=19: ATR ≈ 1.51 (within ±0.5). Use skip(19) to avoid pre-convergence values.
        for v in out["atr_14"].iter().skip(19) {
            assert_abs_diff_eq!(*v, 2.0, epsilon = 0.5);
        }
        // RSI all rising → should be > 50
        for v in out["rsi_14"].iter().skip(14) {
            assert!(*v > 50.0, "RSI should be > 50 in rising market");
        }
    }

    #[test]
    fn test_portfolio_drawdown_series_known_values() {
        let equity = vec![100.0, 90.0, 80.0, 100.0, 90.0];
        let dd = portfolio_drawdown_series_impl(&equity);
        assert_eq!(dd.len(), 5);
        assert_abs_diff_eq!(dd[0], 0.0, epsilon = 1e-10);
        assert_abs_diff_eq!(dd[1], -0.1, epsilon = 1e-10);
        assert_abs_diff_eq!(dd[2], -0.2, epsilon = 1e-10);
        assert_abs_diff_eq!(dd[3], 0.0, epsilon = 1e-10);
        assert_abs_diff_eq!(dd[4], -0.1, epsilon = 1e-10);
    }

    #[test]
    fn test_portfolio_drawdown_series_monotone_rise() {
        let equity: Vec<f64> = (1..=10).map(|i| i as f64 * 10.0).collect();
        let dd = portfolio_drawdown_series_impl(&equity);
        for v in &dd {
            assert_abs_diff_eq!(*v, 0.0, epsilon = 1e-10);
        }
    }

    #[test]
    fn test_portfolio_rolling_sharpe_nan_warmup() {
        let returns = vec![0.01; 50];
        let out = portfolio_rolling_sharpe_impl(&returns, 20, 0.0);
        assert_eq!(out.len(), 50);
        for v in &out[..19] {
            assert!(v.is_nan(), "pre-window should be NaN");
        }
        for v in &out[19..] {
            assert!(!v.is_nan(), "post-window should be valid");
        }
    }

    #[test]
    fn test_portfolio_rolling_sharpe_constant_returns_zero_std() {
        let returns = vec![0.01; 30];
        let out = portfolio_rolling_sharpe_impl(&returns, 10, 0.0);
        for v in &out[9..] {
            assert_abs_diff_eq!(*v, 0.0, epsilon = 1e-6);
        }
    }

    #[test]
    fn test_portfolio_kelly_fraction_positive_edge() {
        let returns = vec![0.05, -0.02, 0.03, -0.01, 0.04, -0.03, 0.02];
        let kelly = portfolio_kelly_fraction_impl(&returns);
        assert!(kelly > 0.0, "positive-edge returns should yield positive Kelly: {kelly}");
    }

    #[test]
    fn test_portfolio_kelly_fraction_mixed_returns() {
        let returns: Vec<f64> = (-10..=10).map(|i| i as f64 / 100.0).collect();
        let kelly = portfolio_kelly_fraction_impl(&returns);
        assert!(kelly.abs() < 0.5, "near-symmetric should yield small Kelly: {kelly}");
    }

    #[test]
    fn test_extract_entities_from_text_dollar_ticker() {
        let result = extract_entities_from_text_impl("Check $AAPL and $BTC for moves");
        assert!(result.contains("AAPL"));
        assert!(result.contains("BTC"));
    }

    #[test]
    fn test_extract_entities_from_text_ticker_slash() {
        let result = extract_entities_from_text_impl("BTC/USDT is surging");
        assert!(result.contains("BTC/USDT"));
    }

    #[test]
    fn test_extract_entities_from_text_metric() {
        let result = extract_entities_from_text_impl("The RSI and MACD look good for Japan equities");
        assert!(result.contains("rsi"));
        assert!(result.contains("macd"));
        assert!(result.contains("japan"));
        assert!(result.contains("equities"));
    }

    #[test]
    fn test_normalize_content_hash_dedup() {
        let a = normalize_content_hash("  Hello   World  ");
        let b = normalize_content_hash("hello world");
        assert_eq!(a, b);
    }

    #[test]
    fn test_tokenize_words_basic() {
        let tokens = tokenize_words("Hello, world! Test-case_123");
        assert_eq!(tokens, vec!["hello", "world", "test", "case", "123"]);
    }

    #[test]
    fn test_score_tools_clamped_0_1() {
        let scores = score_tools_for_query_impl(
            "analyze crypto market",
            &["crypto_analyzer".to_string()],
            &["analyzes crypto and forex markets".to_string()],
        );
        assert_eq!(scores.len(), 1);
        assert!((0.0..=1.0).contains(&scores[0]));
    }

    #[test]
    fn test_score_tools_for_query_basic() {
        let names = vec!["tool_a".to_string(), "tool_b".to_string()];
        let descs = vec![
            "analyze crypto markets with rsi".to_string(),
            "generate reports for equities".to_string(),
        ];
        let scores = score_tools_for_query_impl("analyze rsi crypto", &names, &descs);
        assert_eq!(scores.len(), 2);
        assert!(scores[0] > scores[1], "tool_a should score higher for crypto+rsi query");
    }

    #[test]
    fn test_score_tools_for_query_name_boost() {
        let names = vec!["rsi_tool".to_string(), "other".to_string()];
        let descs = vec![
            "technical indicator".to_string(),
            "technical indicator".to_string(),
        ];
        let scores = score_tools_for_query_impl("rsi_tool analysis", &names, &descs);
        assert!(scores[0] > scores[1], "name-match should boost score");
    }
}
