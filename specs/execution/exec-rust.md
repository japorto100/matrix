# exec-rust — Rust Indicator Core & Compute Integration

> Status: Portiert / Integration geplant
> Erstellt: 2026-04-13
> Quelle: `D:\tradingview-clones\tradeview-fusion\python-backend\`
> Referenz: Finished Execution Slices (siehe Sektion 3)

---

## 0. Kontext

Die Indikator-Engine und der Rust-Core wurden aus dem TradeFusion-Hauptprojekt
nach Matrix portiert, da der Agent-Service zunehmend Zugriff auf technische
Indikatoren, Regime Detection und quantitative Berechnungen braucht.

**Portierte Module:**

| Modul | Pfad in Matrix | Inhalt |
|-------|----------------|--------|
| Compute (Python) | `python-backend/compute/` | Indicator Engine, Geopolitical Soft Signals, Game Theory |
| Rust Core | `python-backend/rust_core/` | Rust-Indikatoren (231 Funktionen), PyO3 Bridge, Tonic gRPC, WASM |

---

## 1. Compute — Python Indicator Engine

### indicator_engine/

| Datei | Funktion |
|-------|----------|
| `app.py` | FastAPI Endpoints |
| `trend.py` | SMA, EMA, DEMA, TEMA, HMA, Ichimoku |
| `oscillators.py` | RSI, MACD, Stochastic, CCI, Williams %R |
| `volatility.py` | ATR, Bollinger Bands, Keltner |
| `volume.py` | VWAP, OBV, MFI, AD Line |
| `patterns.py` | Candlestick, Fibonacci, Harmonic, Elliott |
| `portfolio.py` | Sharpe, Sortino, Max Drawdown, HRP |
| `portfolio_analytics.py` | Erweiterte Portfolio-Metriken |
| `backtest.py` | Walk-Forward Backtesting |
| `derivatives.py` | Options/Derivatives Berechnungen |
| `quant.py` | Quantitative Evaluation Framework |
| `rainbow.py` | Rainbow Indicators + Confluence |
| `regime_weighting.py` | SMA-Slope + ADX Regime Detection (bullish/bearish/ranging) |
| `rust_bridge.py` | PyO3 Bridge zu rust_core |
| `models.py` | Pydantic Models (80+ Typen) |

### geopolitical_soft_signals/

| Datei | Funktion |
|-------|----------|
| `game_theory.py` | Impact Scoring, Nash Equilibria, Transmission Paths, Monte Carlo, Stratagem Matching, Timeline Regimes |
| `pipeline.py` | News Cluster (HDBSCAN/TF-IDF), Social Surge, Narrative Shift (JS-Divergence), FinBERT Sentiment, Ingest Classification |

---

## 2. Rust Core

### Architektur

```
rust_core/
├── src/
│   ├── lib.rs              ← PyO3 Exports
│   ├── indicators/         ← 231 Funktionen (trend, oscillators, volume, volatility, patterns, regime, portfolio, quant, composites, stats, rainbow, backtest, transforms)
│   ├── config.rs
│   ├── error.rs
│   ├── helper.rs           ← 145 LOC shared helpers
│   └── ohlcv_cache.rs      ← redb OHLCV Cache
├── kand-rs/                ← WASM Build fuer Frontend _inc() Offloading
├── proto/                  ← Protobuf Definitions (94 RPCs, ~170 Messages)
├── Cargo.toml
└── rust-toolchain.toml
```

### Key Facts

- **231 Rust-Funktionen** — 100% Pure-Math Paritaet mit Python
- **PyO3 Bridge** — `calculate_indicators_batch` als Hauptendpoint, `py.detach()` fuer GIL-Release
- **Tonic gRPC** — Go → gRPC → Tonic(rust_core) fuer Hot-Path
- **WASM** — `kand-rs/kand-wasm/` fuer Frontend Incremental Indicators
- **374 Tests** — alle gruen (Stand Hauptprojekt)

### Fuer Agent-Tools relevant

Agents koennen ueber Tools folgende Berechnungen anfordern:
- Technische Indikatoren (alle 231 Funktionen)
- Regime Detection (`regime_weighting.rs`)
- Portfolio Analytics (Sharpe, Drawdown, HRP, Correlation Matrix)
- Backtesting (Walk-Forward + Deflated Sharpe)
- Composite Signals (Swarm Validation, K's Collection)

---

## 3. Referenz: Finished Execution Slices (Hauptprojekt)

Quelle: `D:\tradingview-clones\tradeview-fusion\docs\specs\execution\finished\`

| Slice | Relevanz fuer Matrix |
|-------|---------------------|
| **rust_indicator_migration_delta.md** | HOCH — Vollstaendige Python→Rust Migration (Rev. 9), 374 Tests, Helper-Konsolidierung, Tonic-Architektur, Proto-Schema |
| **indicator_delta.md** | HOCH — IST-Zustand aller Indikatoren (Python vs. Rust), Lueckenliste, Book-Referenzen |
| **python_runtime_eval_delta.md** | MITTEL — PyO3 allow_threads, Python 3.13t nogil Eval, Granian vs. uvicorn Benchmarks |
| **go_concurrency_llm_routing_delta.md** | MITTEL — Go Gateway Concurrency-Fixes, LiteLLM Routing (relevant wenn Matrix Go-Gateway nutzt) |
| **source_selection_delta.md** | NIEDRIG — Quellenauswahl/Tiering fuer Datenquellen |
| **service_config_consolidation_delta.md** | NIEDRIG — Gateway-URL Konsolidierung (Next.js spezifisch) |
| **frontend_enhancement_delta.md** | NIEDRIG — Frontend spezifisch |
| **frontend_intelligence_calendar_delta.md** | NIEDRIG — Frontend Calendar Widget |

---

## 4. Boundary Decision: Was gehoert in Rust, was bleibt Python

### Bereits in Rust (portiert im Hauptprojekt)

| Modul | Rust-Status | Bemerkung |
|-------|-------------|-----------|
| Regime Detection | `regime_weighting.rs` existiert (Rev. 5) | detect_regime, apply_regime_weight, regime_weight_patterns — 1:1 Port |
| Monte Carlo Simulation | In rust_core | Pure Math Tight-Loop, klarer Rust-Kandidat |
| Alle 231 Indikatoren | Vollstaendig | 100% Paritaet, 374 Tests |
| Portfolio Analytics | Vollstaendig | Sharpe, Drawdown, HRP, Correlation, Beta, Calmar |
| Backtesting | Vollstaendig | Walk-Forward + Deflated Sharpe |

### Bleibt in Python — Game Theory

`game_theory.py` ist **kein Rust-Kandidat** weil:

1. **String-Heavy** — Token-Matching (RISK_OFF_TOKENS, HAWKISH_TOKENS), Country/Region Mapping,
   normalize_text(). Kein numerisches Bottleneck.
2. **Heuristik-basiert** — `_score_event()` macht 5-6 if/elif Checks und addiert Floats.
   Laeuft in Mikrosekunden, Rust-Overhead (Compile, FFI) uebersteigt den Gewinn.
3. **Nash Solver trivial** — Brute-Force bei 2-8 Spielern mit wenigen Outcomes.
   Erst bei groesseren Spielraeumen (>1000 Outcomes) waere Rust relevant,
   dann aber besser ein dedizierter Solver (Lemke-Howson).
4. **Schnelle Iteration noetig** — Heuristiken, Tokens, Regionen aendern sich oft.
   Python-Iteration >> Rust-Compile-Cycle.
5. **ML-Oekosystem** — pipeline.py nutzt sentence-transformers, HDBSCAN, TF-IDF,
   FinBERT API. Das lebt im Python-Ecosystem.

### Bleibt in Python — Soft Signals Pipeline

`pipeline.py` ist ML-Pipeline-Code: Clustering, Sentiment, NLP.
Gehoert in Python, keine Diskussion.

### Grenzziehung (Leitregel aus Hauptprojekt)

```
Rust  = Hot-Path numerische Berechnungen (Indikatoren, Portfolio-Math, Backtesting, Monte Carlo)
Python = ML-Pipeline, LLM-Integration, Heuristiken, alles was sich schnell aendern muss
Go     = Gateway, Routing, Concurrency, NATS
```

---

## 5. Integration in Matrix Agent

### Phase 1: Compute als Agent Tool

- [ ] `agent/tools/compute_tool.py` — Agent kann Indikatoren berechnen lassen
- [ ] Regime Detection als Input fuer Agent-Entscheidungen
- [ ] Game Theory Impact Scoring als Agent-Tool exponieren

### Phase 2: Rust Core als gRPC Service

- [ ] Tonic gRPC Server aufsetzen (Proto-Schema existiert bereits)
- [ ] Agent → gRPC → rust_core fuer latenz-kritische Berechnungen
- [ ] Alternativ: PyO3 direkt wenn kein Go-Gateway

### Phase 3: WASM fuer Agent-Chat Frontend

- [ ] `kand-rs/kand-wasm/` in agent-chat fuer Echtzeit-Chart-Indikatoren
- [ ] Incremental `_inc()` Funktionen fuer Streaming-Daten

---

## 5. Abhaengigkeiten

- exec-ebm: EBM Energy Scorer nutzt Regime Detection aus compute + Game Theory Confidence-Vektoren
- exec-10 (Multi-Agent): Agent-Tools greifen auf Compute/Rust zu
- exec-17 (Harness): Scorer Erweiterung um Compute-basierte Metriken
