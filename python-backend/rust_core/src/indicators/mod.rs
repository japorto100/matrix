// indicators/ — Category-based indicator modules.
//
// Module names mirror Python indicator_engine/ for 1:1 port mapping.
// After migration, each module exposes free functions (no traits).
// Multi-output indicators (MACD, BB, ADX, Ichimoku, Keltner) return tuples.

pub mod stats;              // Statistical primitives: sum, max, min, var, stddev, correl
pub mod trend;              // MA family + Ichimoku (= trend.py)
pub mod oscillators;        // RSI, MACD, Stoch, ADX + composite/heartbeat (= oscillators.py)
pub mod volatility;         // ATR, BB, Keltner (= volatility.py)
pub mod volume;             // VWAP, OBV, CMF (= volume.py)
pub mod portfolio;          // Drawdown, Sharpe, Kelly, Sortino, Returns, Winrate (= portfolio.py)
pub mod directional;        // DM system: +DM, -DM, +DI, -DI, DX (Wilder) (= oscillators.py DM family)
pub mod transforms;         // OHLC transforms: Heikin-Ashi (WASM candidate) (= patterns.py transforms)
pub mod patterns;           // Candlestick pattern detection: Doji, Hammer etc. (= patterns.py)
pub mod quant;              // Heuristic classifiers (= quant.py)
pub mod derivatives;        // Options, DeFi, dark pool (= derivatives.py)
pub mod rainbow;            // Kaabar Rainbow Collection (= rainbow.py)
pub mod regime_weighting;   // Regime-aware signal weighting (= regime_weighting.py)
pub mod backtest;           // Backtesting, triple barrier, walk-forward (= backtest.py)
pub mod composites;         // Cross-module composites: BB-Keltner Squeeze, ATR-RSI, BB-on-RSI, BB signals (= volatility.py composites)
pub mod regime;             // Volatility regime: suite, rule-based, Markov (= volatility.py regime section)
