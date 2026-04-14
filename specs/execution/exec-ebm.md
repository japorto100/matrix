# exec-ebm — Energy-Based Models fuer Agent Scoring & Game Theory

> Status: Evaluation / Prototyp-Phase
> Erstellt: 2026-04-13
> Abhaengigkeiten: exec-17 (Harness/Scorer), exec-10 (Multi-Agent), GAME_THEORY.md (Hauptprojekt)

---

## 0. Kontext

Energy-Based Models (EBMs) definieren eine lernbare Energy-Funktion ueber Datenkonfigurationen.
Niedrige Energie = hohe Wahrscheinlichkeit / Konsistenz. Hohe Energie = Anomalie / Divergenz.

**Kernproblem das EBMs loesen:** Unsere Multi-Agent Outputs (Analyst, Risk, Researcher etc.)
muessen aggregiert und kalibriert werden — ohne Ground-Truth-Labels. Transformer-Agents
generieren Einschaetzungen, aber wer hat recht? Statische `confidence_base` Werte
(seed_data.py) skalieren nicht.

---

## 1. Forschungsgrundlage

### Direkt anwendbar

| Paper | Relevanz | PDF |
|-------|----------|-----|
| Maymon et al. 2025 — "Unsupervised Ensemble Learning Through Deep EBMs" | Ensemble-Aggregation ohne Labels, implizite Reliability-Gewichte | `docs/Maymon2025_Unsupervised_Ensemble_Deep_EBM.pdf` |
| Blondel et al. 2025 — "Autoregressive LMs are Secretly EBMs" | LLM-Outputs SIND bereits Energy-Scores — extrahierbar ohne separates Training | `docs/Blondel2025_Autoregressive_LMs_Secretly_EBMs.pdf` |
| Rozemberczki 2021 — "Shapley Value of Classifiers in Ensemble Games" | Game-theoretische Agent-Contribution via Shapley Values | `docs/Rozemberczki2021_Shapley_Value_Ensemble_Games.pdf` |

### Referenz / Grundlagen

| Paper | Relevanz | Quelle |
|-------|----------|--------|
| Grathwohl et al. 2020 — "Your Classifier is Secretly an EBM" (JEM) | Kalibrierung + OOD-Detection nativ in EBMs | `docs/Grathwohl2020_JEM_Classifier_Secretly_EBM.pdf` |
| JEM++ (arxiv 2109.09032) | Stabilisiertes JEM-Training | arxiv |
| ST-JEM (arxiv 2303.04187) | Balanced positive/negative SGLD Sampling | arxiv |

### Curated Lists

- [awesome-ebm](https://github.com/yataobian/awesome-ebm) — Gesammeltes Forschungsmaterial (NeurIPS 2025, ICLR, ICML)
- [mini-ebm](https://github.com/yataobian/mini-ebm) — Minimale Lern-Implementierung (CD, DSM, NCE)
- [TorchEBM](https://github.com/soran-ghaderi/torchebm) — Produktionsnahe PyTorch Library (2025)

---

## 2. Was nuetzlich ist fuer TradeFusion

### 2a. Agent Ensemble Scoring (Hoch)

**Problem:** Multi-Agent Outputs ohne Ground Truth aggregieren.
**Loesung:** Energy-Funktion ueber Agent-Confidence-Vektoren.

```
Agent Outputs:     [Analyst: risk_off 0.72, Risk: risk_off 0.81, Researcher: neutral 0.55]
Energy Score:      E(config) = niedrig → hohe Konsistenz → hohe Gesamtkonfidenz
Divergenter Fall:  [Analyst: risk_on 0.70, Risk: risk_off 0.85, Researcher: risk_on 0.60]
Energy Score:      E(config) = hoch → Divergenz → Entropy-Signal
```

**Integration:** `agent/harness/energy_scorer.py` neben bestehendem `scorer.py` + `pareto.py`

### 2b. Implizite LLM Energy Scores (Hoch)

**Blondel 2025 Insight:** Autoregressive LMs berechnen bereits implizit Energy-Funktionen.
Die Log-Probabilities unserer Agent-LLM-Outputs SIND Energy-Scores.

**Praktisch:** Statt separates EBM trainieren → Log-Probs aus LLM-Responses extrahieren
und als Confidence-Signal nutzen. Zero additional training.

**Integration:** `agent/llm_client.py` — Log-Probs mitloggen, in Scorer einspeisen.

### 2c. Energy Commodity Markets (Hoch)

EBMs sind im Energy-Commodity-Bereich (Strom, Gas, Oel) bereits etabliert fuer:
- Forecasting mit Ensemble-Aggregation (W[EF]2M Framework)
- Multi-Stakeholder Risiko-Praeferenzen
- Day-ahead Market Prediction

**Fuer TradeFusion relevant weil:**
- Geopolitische Events → Energy Commodities ist ein Kern-Transmission-Channel
  (siehe `compute/geopolitical_soft_signals/game_theory.py`: TC_OIL_USD, TC_SANCTION_ENERGY)
- Energy-Markt-Volatilitaet ist direkter Input fuer Regime Detection
- OPEC+ Entscheidungen als Game-Theory Szenario modellierbar

### 2d. Shapley-basierte Agent Contribution (Mittel)

**Problem:** Welcher Agent traegt wie viel zum Gesamtergebnis bei?
**Loesung:** Shapley Values — fair, game-theoretisch fundiert.

Passt direkt in `agent/harness/pareto.py`:
- Aktuell: Pareto-Frontier ueber 4 Dimensionen (completion, turn_efficiency, tool_success, token_efficiency)
- Erweiterung: Shapley Value pro Agent-Rolle als 5. Dimension

### 2e. Regime Detection Referenz (Mittel)

Regime Detection laeuft in der Praxis primaer ueber **HMM (Hidden Markov Models) + Neural Nets**,
nicht ueber EBMs. Unser Hauptprojekt hat das bereits implementiert:

- `python-backend/compute/indicator_engine/regime_weighting.py` — SMA-Slope + ADX-basierte Regime-Erkennung (bullish/bearish/ranging)
- `python-backend/compute/geopolitical_soft_signals/game_theory.py` — Timeline-Regime-Bands (elevated/watch/calm)

EBMs koennen komplementaer zur HMM-basierten Regime Detection eingesetzt werden:
- HMM fuer State-Transitions (zeitlich)
- EBM fuer Anomalie-Scoring innerhalb eines Regimes (energetisch)

Siehe auch: arxiv 2407.19858 — "AI-Powered Energy Algorithmic Trading: Integrating HMM with Neural Networks"

---

## 3. Implementierungsplan

### Phase 1: Isolierter Prototyp (CPU-only)

```
python-backend/experiments/ebm/
├── energy_scorer_pure.py    ← Pure PyTorch (~80 Zeilen, MLP + Langevin + CD)
├── energy_scorer_torchebm.py ← TorchEBM Library Variante
├── data_loader.py           ← Liest Agent Audit Sessions (readonly)
├── train.py                 ← Training Loop (beide Varianten)
├── evaluate.py              ← Vergleich pure vs torchebm vs bestehender Scorer
└── README.md
```

**Beide Varianten parallel evaluieren:**

| Aspekt | Pure PyTorch | TorchEBM |
|--------|-------------|----------|
| Dependency | nur `torch` (~2GB) | `torch` + `torchebm` |
| Kontrolle | volle Kontrolle ueber Energy-Funktion | vorgefertigte CD/SM/NCE |
| Code | ~80 Zeilen | ~30 Zeilen |
| Lernwert | hoch — versteht man was passiert | mittel — Abstraktion |
| Produktion | leichtgewichtiger | mehr Features (MCMC, Flow) |

**Hardware:** CPU reicht voellig. Agent-Confidence-Vektoren sind 5-10 dimensional,
MLP mit wenigen hundert Parametern. Training in Sekunden.
GPU erst relevant ab >10k Datenpunkten pro Batch.

### Phase 2: Integration in Harness

```
agent/harness/
├── scorer.py          ← bestehend (regelbasiert)
├── pareto.py          ← bestehend (multi-objective)
├── energy_scorer.py   ← NEU: laed trainiertes .pt Modell, scored neue Sessions
└── shapley.py         ← NEU: Agent-Contribution Berechnung
```

### Phase 3: LLM Log-Prob Extraction

- `agent/llm_client.py` — Log-Probs aus Anthropic/OpenAI Responses extrahieren
- Kein Training noetig — direkte Nutzung als Energy-Signal
- Erfordert API-Parameter: `logprobs=true` (OpenAI), bei Anthropic ueber Token-Likelihood

### Phase 4: Game Theory Integration

- Energy-Funktion ueber Stratagem-Confidence-Vektoren (`memory_engine/seed_data.py`)
- Lernbare Gewichte statt statischer `confidence_base` Werte
- Monte-Carlo Energy Sampling fuer Szenario-Analyse (komplementaer zu bestehendem `run_monte_carlo_simulation`)

---

## 4. Paper-Abgleich: Memory for Autonomous Agents (2603.07670v1) — EBM-Relevante Punkte

| Paper-Abschnitt | Thema | EBM-Verbindung |
|-----------------|-------|---------------|
| **4.3** Self-Reinforcing Error / False Beliefs | Agent bestaetigt eigene falsche Schlussfolgerungen | EBM als Anomalie-Detektor: hohe Energie = Belief widerspricht Evidenz |
| **6.4** Uncertainty-aware Memory (Bayesian RAG) | Confidence-Level pro Fakt, Score = μ - λ·σ | EBM Energy als Uncertainty Proxy: hohe Energie = unsicherer Fakt. Alternative zu explizitem Bayesian Tracking. |
| **9.3** Trustworthy Reflection | Unvalidierte Reflexionen muessen verfallen | Energy Decay: Reflection-Energy steigt ueber Zeit wenn keine bestaetigende Evidenz kommt |
| **4.5** Policy-Learned Management | Memory Ops als RL-Policy (AgeMem) | EBM als Reward-Signal fuer RL: niedrige Energie der Memory-Konfiguration = gute Policy |

### Bayesian RAG + EBM Verbindung

Bayesian RAG (Frontiers in AI, 2025) definiert: **Score = μ - λ·σ** (Relevanz minus Unsicherheits-Penalty).
EBMs modellieren das implizit: die Energy-Funktion ueber Agent-Confidence-Vektoren IST ein
Uncertainty-Score. Niedrige Energie = konsistente Konfidenz = niedriges σ.

Fuer uns: EBM Energy als billigere Alternative zu Monte Carlo Dropout (Bayesian RAG braucht
mehrere Forward-Passes fuer σ-Schaetzung, EBM braucht einen).

---

## 5. Was NICHT mit EBMs gemacht werden soll

- **Regime Detection ersetzen** — HMM + ADX bleibt primaer, EBM nur komplementaer
- **LLM-Agent Reasoning ersetzen** — EBMs sind Scoring/Aggregation, kein Reasoning
- **Schwere GPU-Workloads** — kein Bild/Video/3D, nur numerische Vektoren
- **TorchEBM als harte Dependency** — evaluieren ja, festlegen nein

---

## 6. Naechste Schritte

- [ ] Phase 1: `experiments/ebm/` Ordner aufsetzen
- [ ] Pure PyTorch EBM Prototyp (energy_scorer_pure.py)
- [ ] TorchEBM Variante zum Vergleich (energy_scorer_torchebm.py)
- [ ] Audit-Daten Loader (aus bestehenden Harness Sessions)
- [ ] Vergleichs-Evaluation: EBM vs. bestehender Scorer vs. LLM Log-Probs
- [ ] Entscheid: pure vs. torchebm fuer Produktion
- [ ] Phase 2: Integration in agent/harness/
- [ ] Phase 3: LLM Log-Prob Extraction
- [ ] Phase 4: Game Theory lernbare Gewichte
