# exec-harness — Agent Harness Optimization

> Status: Draft
> Erstellt: 2026-04-16
> Abhaengigkeiten: exec-17 (Stufe 5+6 = Implementierungsbasis), exec-18 (persistent Traces), exec-skills (Skills als ein Harness-Hebel), exec-context (Runtime-Assembly-Regeln), exec-world-model (globale Wissensseite), exec-personal-kb (user-kuratierte Knowledgebase)
> Referenzen:
>   - **Meta-Harness** (arxiv 2603.28052): [Paper](https://arxiv.org/abs/2603.28052) | [Artifact](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact) | [PDF](docs/Meta-Harness-2603.28052v1.pdf)
>   - **AutoResearch** (Karpathy): [GitHub](https://github.com/karpathy/autoresearch) | [AutoRAG Optimizer](https://github.com/yeyu2/Youtube_demos/tree/main/auto-rag-optimizer) (praktisches Beispiel fuer non-training Anwendung)
>   - **EvoSkill** (arxiv 2603.02766): [GitHub](https://github.com/sentient-agi/EvoSkill) — 5-Stage Loop, Evaluator-Pattern uebertragbar
>   - Agno Agent OS (`_ref/agno/`): `component_configs` mit `pareto_frontier` Flag als DB-Blueprint

---

## 0. Abgrenzung: Was ist ein Harness, was nicht?

**Harness** = der Code der den Agent umgibt und bestimmt WAS das LLM sieht und WIE es arbeitet.

| Harness (exec-harness) | NICHT Harness |
|---|---|
| System-Prompt-Aufbau + Prompt-Reihenfolge | LLM-Weights (Training = exec-skills Phase 4) |
| Memory-Config (welche Banks, wann Recall) | Memory-Engine selbst (exec-memory) |
| Tool-Selection (welche Tools aktiv) | Tool-Implementierung (einzelne Tools) |
| Skill-Loading-Strategie (General always-load vs retrieved) | Skill-Content (exec-skills) |
| Context-Management (Compaction, Token-Budget) | Context-Engine (exec-context) |
| Retrieval-Strategie (chunk_size, fusion_weights) | Retrieval-Engine (exec-memory) |
| Layer-/Consumer-Policy (welche Schicht fuer wen, in welcher Reihenfolge) | Claim-/KG-Adjudication selbst (exec-world-model) |
| Consent/Approval-Policy | Consent-Engine (exec-12) |

**Faustregel:** Wenn du es aendern kannst ohne Code in den Engine-Modulen zu editieren,
ist es ein Harness-Parameter. Wenn du Engine-Internals aendern musst, ist es nicht Harness.

Meta-Harness Paper (S. 1): *"Changing the harness around a fixed LLM can produce a 6x performance
gap on the same benchmark."*

---

## 1. Architektur: Zwei Optimierungsstufen

### Stufe A: AutoResearch-Pattern (Parameter-Sweep, isolierte Komponente)

**Was:** Optimiere EINE Komponente mit tunable Parameters und messbarer Metrik.
Keep/Discard-Loop, kein Trace-Zugang noetig.

**Wie (Karpathy-Pattern):**
```
1. Definiere Parameter-Space (z.B. chunk_size: [256,512,1024], top_k: [3,5,10])
2. LLM schlaegt naechste Config vor (basierend auf research_log.md History)
3. Laufe System mit Config → messe Metrik
4. Wenn besser → keep. Sonst → discard.
5. Repeat (~12 Experimente/Stunde)
```

**Anwendungen bei uns:**

| Komponente | Parameter | Metrik | Status |
|---|---|---|---|
| RAG/Retrieval | chunk_size, overlap, top_k, fusion_weights, embedding_model | Recall@k, Faithfulness (LLM-Judge) | Noch nicht gebaut |
| Skill Finder | BM25-k1/b, Dense-Threshold, RRF-k, max_tokens | Coverage-Score, Pass-Rate | Noch nicht gebaut |
| Skill Refiner | compose-temperature, max_tokens, system-prompt-Varianten | LLM-Judge Quality Score | Noch nicht gebaut |
| Coverage Gate | Threshold per Model | Pass-Rate mit/ohne Refinement | Defaults vorhanden, Tuning offen |
| Offline Refiner | num_synthetic_tasks, rewrite-temperature, prompt-Varianten | Before/After LLM-Judge Score | Noch nicht gebaut |

**Referenz-Implementation:** [AutoRAG Optimizer](https://github.com/yeyu2/Youtube_demos/tree/main/auto-rag-optimizer) —
zeigt den Loop auf RAG-Pipeline (0.36 → 0.75 ueber 20 Experimente, kostenguenstige OpenRouter-Models).

### Stufe B: Meta-Harness-Pattern (holistisch, trace-informed)

**Was:** Optimiere den GESAMTEN Agent-Harness. Proposer sieht Code + Traces + Prior-Candidates.
Multi-Objective (Pareto).

**Wie (Stanford-Pattern):**
```
1. Proposer (Coding-Agent, z.B. Claude Code) liest Filesystem:
   - Prior Harness Code (alle Candidates)
   - Execution Traces (OTel Spans, Audit Events)
   - Scores (Evaluator-Ergebnisse)
2. Proposer analysiert Failures kausal, schlaegt Code-Aenderungen vor
3. Evaluator laesst Agent gegen Search-Set laufen
4. Alle Logs (Code + Traces + Scores) → Filesystem/DB
5. Pareto-Frontier ueber (Accuracy × Context Cost) pflegen
6. Repeat
```

**Meta-Harness Kern-Ablation (Paper Table 3):**
| Input | Median Accuracy |
|---|---|
| Scores only | 34.6 |
| Scores + Summary | 34.9 |
| **Full Traces** | **50.0** |

→ **Trace-Zugang bringt +15pp.** Darum ist exec-18 (persistent `agent.traces` + `agent.spans`) der kritische Enabler.

---

## 2. IST-Zustand: Was haben wir bereits?

### Aus exec-17 Stufe 5+6 (implementiert):

| Modul | Pfad | Funktion |
|---|---|---|
| `config.py` | `agent/harness/config.py` | Serialize/Deserialize aktuelle Harness-Config |
| `scorer.py` | `agent/harness/scorer.py` | Quality-Scores aus Audit-Daten berechnen |
| `proposer.py` | `agent/harness/proposer.py` | LLM-Proposer: liest Traces → schlaegt Aenderungen vor. `propose_loop(iterations, candidates_per_iter)` CLI-faehig. |
| `evaluator.py` | `agent/harness/evaluator.py` | Agent-Variante gegen Search-Set laufen lassen |
| `pareto.py` | `agent/harness/pareto.py` | Non-dominated Sorting, `compute_pareto_frontier()` |
| MCP Tools (11) | `agent/mcp_traces.py` | `harness_config`, `harness_propose`, `harness_evaluate`, `harness_pareto`, `harness_loop`, etc. |
| Candidates | `data/harness/candidates/v{NNN}/` | Filesystem-gespeicherte Candidates (→ exec-18 migriert nach `agent.component_configs`) |
| Search-Set | `data/harness/search_set/queries.json` | Starter-Queries fuer Evaluator |

### Aus exec-18 (Tabellen gebaut 2026-04-16, Runtime-Integration ausstehend):

| Tabelle | Funktion fuer Harness | Status |
|---|---|---|
| `agent.sessions` | Session-Daten fuer Scorer-Aggregation | ✅ Tabelle + CRUD (`agent/sessions.py`) |
| `agent.traces` + `agent.spans` | **Persistente Traces** — der Meta-Harness Kern-Input | ✅ Tabellen da, ❌ PostgresSpanProcessor fehlt |
| `agent.components` + `component_configs` | Versionierte Harness-Configs mit `pareto_frontier` Flag | ✅ Tabellen da, ❌ Proposer-Integration fehlt |
| `agent.evals` | Evaluator-Ergebnisse persistent | ❌ Tabelle noch nicht gebaut (Migration 019) |
| `agent.metrics` | Daily Aggregation fuer Trend-Analyse | ❌ Tabelle noch nicht gebaut (Migration 020) |

### Aus exec-skills (relevant fuer Harness):

| Was | Verbindung |
|---|---|
| `agent/skills/pareto.py` | Pattern-Uebertrag von `agent/harness/pareto.py` — Skills-Pareto nutzt gleiche Non-dominated-Sorting-Logik |
| Trigger-Quality CLI | Misst ob Skill-Loading-Strategie funktioniert — Harness-Level-Signal |
| Coverage Gate | Harness-Entscheidung "refine oder nicht" — ein Harness-Parameter |
| Audit Events (SKILL_*) | Input fuer Harness-Proposer: wie gut funktioniert die aktuelle Skill-Strategie? |

---

## 3. AutoResearch vs Meta-Harness: Wann welches Pattern?

| | AutoResearch | Meta-Harness |
|---|---|---|
| **Scope** | Eine Komponente isoliert | Gesamter Agent-Harness |
| **Input** | Parameter + Score-History | Code + Traces + Scores + Prior-Candidates |
| **Proposer** | LLM (ein Call, config-JSON output) | Coding-Agent (Multi-Step, Tool-Zugang, File-Lesen) |
| **Objective** | Single (ein Score) | Multi (Pareto: Accuracy × Cost × Latency) |
| **Trace-Zugang** | Nein (nur Scores) | **Ja** — der Kernvorteil (+15pp laut Ablation) |
| **Aufwand** | Klein (orchestrator.py + evaluator.py + research_log.md) | Gross (Proposer als Agent, Filesystem-Management, Pareto) |
| **Wann nutzen** | Parameter wenige + unabhaengig (RAG-Settings, Thresholds) | Parameter interagieren + Changes haben komplexe Wechselwirkungen (Prompt-Edit bricht Memory-Pipeline) |

**Empfehlung:**
- Beginne mit **AutoResearch** fuer die 5 Komponenten-Parameter-Sweeps (§1 Tabelle)
- **Meta-Harness** (`agent/harness/`) fuer holistische Harness-Optimierung wenn exec-18 persistent Traces liefert
- Beide leben im selben Optimierungs-Ecosystem, unterschiedliche Granularitaet

---

## 4. Was fehlt (offene Punkte)

### 4a. AutoResearch Loop fuer Komponenten-Tuning

**Status:** Nicht gebaut. Pattern klar (Karpathy + YeYu Lab Demo).

**Aufwand:** ~200 LOC pro Komponente (orchestrator + evaluator + config space).

**Prioritaet:** Nach exec-18 persistent Traces (weil Traces die Metrik-Qualitaet erhoehen).
Alternativ: jetzt schon mit `agent.audit_events` als Metrik-Quelle starten (weniger reich, aber funktional).

**Referenz-Implementierung:** [AutoRAG Optimizer](https://github.com/yeyu2/Youtube_demos/tree/main/auto-rag-optimizer)
zeigt den kompletten Loop inkl. `research_log.md` + `config.json` + LLM-as-Judge Evaluator.

### 4b. exec-18 Persistent Traces (Enabler)

**Status:** Schema definiert (exec-18 Migration 014: `agent.traces` + `agent.spans`), noch nicht gebaut.

Ohne persistent Traces arbeitet der Harness-Proposer nur mit `agent.audit_events` — das reicht fuer
Basis-Analyse, aber Meta-Harness's Kern-Ablation zeigt dass **raw Traces der entscheidende Input** sind.

### 4c. Proposer → Candidates → DB (exec-18 Migration)

**Status:** Proposer schreibt aktuell ins Filesystem (`data/harness/candidates/v{NNN}/`).
exec-18 plant Migration nach `agent.component_configs` mit `pareto_frontier` Flag.

### 4d. EvoSkill Evaluator-Stage Integration — **expliziter Adoption-Plan**

**Status:** Evaluator-Code-Scaffold existiert (`agent/harness/evaluator.py`, exec-17 Stufe 6.1),
aber **läuft nicht end-to-end** in Production. Dieses Exec ist ab jetzt expliziter **Owner**
für die generische Evaluator-Machinery (nicht skill-spezifisch, nicht harness-spezifisch).

**Adoption-Entscheidung (2026-04-18):** **Pattern nachbauen, Code nicht forken.**
- EvoSkill (`_ref/EvoSkill/`, 91 Files, 629 gitnexus-nodes) ist klein genug, aber trading-spezifisch gescored (sealqa/dabstep/livecodebench). Forking bringt keinen langfristigen Vorteil.
- Stattdessen: EvoSkill-Patterns extrahieren, auf matrix-Substrate (Postgres `agent.evals`, `agent.component_configs`, LiteLLM) mappen.

#### 4d.1 File-Mapping — EvoSkill → matrix

| EvoSkill-Source (`_ref/EvoSkill/src/`) | Pattern extrahiert | matrix-Target | Status |
|---|---|---|---|
| `evaluation/evaluate.py` (`evaluate_agent_parallel`) | Async-parallel mit Semaphore + 17-min Timeout + RunCache | `agent/harness/evaluator.py` erweitern | Scaffold da, Async-Parallel fehlt |
| `cache/run_cache.py` | Git-tree-hash-basiertes Caching (re-eval vermeiden) | `agent/harness/evaluator_cache.py` **neu** (Content-Hash statt Git, wir persistieren Configs in DB nicht im Repo) | ❌ |
| `evaluation/reward.py` | Reward-Computation (numerisch + textuell) | In `agent/harness/scorer.py` bereits teilweise | Scoring vorhanden, Integration offen |
| `evaluation/eval_full.py` | End-to-End-Loop: load set → run variants → aggregate | `agent/harness/evaluator.py:run_full_eval()` **neu** | ❌ |
| `evaluation/sealqa_scorer.py` / `dabstep_scorer.py` | Domain-spezifische Scorer | `agent/harness/scorers/{skills,hermes_pattern,memory}.py` **neu** | ❌ — Split vorgesehen |
| `feedback_descent.py` (arxiv 2511.07919) | **NEU entdeckt**: Pairwise-Comparison statt absolute Scores, text-rationale-basiert | `agent/harness/feedback_descent.py` **optional neu** (§4d.4) | Prüfen |
| `schemas/proposer.py` + `skill_proposer.py` + `prompt_proposer.py` | Proposer-Varianten pro Domäne | `agent/harness/proposer.py` hat bereits Basis, weitere Varianten bei Bedarf | teilweise |
| `registry/manager.py` + `models.py` | Skill-Registry mit `generation` + `parent_skill_id` | bereits in `agent.agent_skills` Schema vorhanden | ✅ |
| `cli/main.py` + `scripts/run_loop.py` | CLI-Orchestrierung des 5-Stage-Loop | `agent/harness/proposer.py:propose_loop()` existiert | ✅ |
| `agent_profiles/` | Agent-Config pro Use-Case | `agent.component_configs` (exec-18) | ✅ |

#### 4d.2 Das 5-Stage-Loop-Mapping — wo wir stehen

| EvoSkill-Stage | matrix-Status |
|---|---|
| **Stage 1 — Base Agent** | ✅ LangGraph-Runner (`agent/graph/runner.py`) |
| **Stage 2 — Proposer** | ✅ `agent/harness/proposer.py` (exec-17 Stufe 5+6), schreibt Candidates in `agent.component_configs` |
| **Stage 3 — Generator** | ⚠️ teilweise — Candidate-Materialization als runnable Config fehlt |
| **Stage 4 — Evaluator** | ❌ **DAS IST DER GAP** — Scaffold da, Full-Loop nicht |
| **Stage 5 — Frontier** | ✅ `agent/harness/pareto.py` |

Dieser Abschnitt fokussiert auf **Stage 4 + Bridge Stage 3→4**.

#### 4d.3 Drei Konsumenten für denselben Evaluator

Der Evaluator ist **generisch** — drei Konsumenten mit unterschiedlichen Eval-Sets und Scorern:

| Konsument | Eval-Set-Source | Domain-Scorer | Exec-Owner für Eval-Set-Inhalt |
|---|---|---|---|
| **Harness-Candidate-Scoring** | `data/harness/search_set/queries.json` (exec-17) | generisch LLM-Judge + Pareto-Dimensionen (Accuracy × Cost × Latency × Grounding) | exec-harness (dieses Exec) |
| **Skill-A/B-Composition-Eval** | synthetische Trading-Queries (exec-skills §8b.3) | Skill-Compliance-Judge | **exec-skills §8b.3** (Input/Metriken), nutzt unseren Evaluator |
| **Hermes-Pattern-Benchmarks** (Hybrid-Architektur) | 5 Task-Typen aus exec-hermes §10 Sprint 4 | Latenz + LOC + Trace-Quality + Audit-Trail-Completeness | **exec-hermes §9.6 Phase 2**, nutzt unseren Evaluator |

**Architektonische Konsequenz:** `agent/harness/scorers/` wird neu eingeführt, domain-spezifisch geteilt, aber Evaluator-Machinery (Parallelism, Caching, Aggregation) ist shared.

#### 4d.4 Bonus: Feedback Descent (arxiv 2511.07919) — neu entdeckt

Beim Deep-Dive in `_ref/EvoSkill/src/feedback_descent.py` ist aufgefallen: EvoSkill **benutzt** Feedback Descent (arxiv **2511.07919**, Nov 2025) als alternative Optimierungs-Methode. Statt skalarer Rewards → **Pairwise-Comparison** mit Text-Rationale.

**Warum interessant für matrix:**
- Skalare LLM-Judge-Scores (0-5) sind verrauscht und modell-biased.
- Pairwise "A oder B besser + warum?" ist **empirisch stabiler** (hybrid cross-encoder-style reasoning).
- Rationale liefert qualitative Failure-Mode-Analyse, die der Proposer nutzen kann.

**Entscheidung:** Als **Option** in den Evaluator einbauen (Mode-Flag `scoring_mode: "absolute" | "pairwise"`). Nicht default, aber verfügbar. Datenaufwand ist doppelt so hoch (N×(N-1)/2 statt N Calls), lohnt nur bei kleinen Kandidaten-Sets (<10).

**Referenz:** https://arxiv.org/abs/2511.07919 — neu in §13 Referenzen zu ergänzen.

#### 4d.5 Sprint-Plan (Evaluator-Full-Loop)

**Sprint A (1 Woche)** — Scaffold vervollständigen
- [ ] `agent/harness/evaluator.py` — `evaluate_search_set()` async-parallel mit Semaphore + Timeout (EvoSkill-Pattern)
- [ ] `agent/harness/evaluator_cache.py` — Content-Hash-basiertes Caching (key = hash(config + query + model))
- [ ] `agent/harness/scorers/` — Ordner, Default-Scorer + Interface-ABC
- [ ] Smoke: 3 Candidates × 5 Queries × 2 Modelle läuft durch, persistent in `agent.evals` (exec-18 Migration 019)

**Sprint B (1 Woche)** — Domain-Scorer + Integration
- [ ] `agent/harness/scorers/harness_default.py` — Pareto-Dimensionen (accuracy, cost, latency, grounding)
- [ ] `agent/harness/scorers/skill_compliance.py` — für exec-skills §8b.3
- [ ] `agent/harness/scorers/hermes_pattern.py` — für exec-hermes §9.6 Hybrid-Benchmark
- [ ] Proposer-Loop-Integration: `propose_loop()` ruft echten Evaluator, nicht Mock

**Sprint C (Optional, 1 Woche)** — Feedback Descent
- [ ] `agent/harness/feedback_descent.py` — Pairwise-Comparison-Mode
- [ ] A/B-Eval zwischen absolute vs pairwise auf demselben Set, messen ob Signal-zu-Rausch besser

**Abnahme-Kriterien:**
- Pareto-Frontier bewegt sich nach 5+ echten Proposer-Iterationen (nicht Mock)
- Skill-A/B-Eval aus exec-skills §8b.3 läuft durch denselben Evaluator
- Hermes-Pattern-Benchmark aus exec-hermes §9.6 läuft durch denselben Evaluator
- `agent.evals` Tabelle (exec-18 Migration 019) existiert + wird befüllt

**Cross-Ref:**
- **Input/Metriken für Skill-Eval** → `exec-skills.md §8b.3`
- **Input/Metriken für Hermes-Pattern** → `exec-hermes.md §9.6 Phase 2 + §10 Sprint 4`
- **Tabelle `agent.evals`** → `exec-18.md` Migration 019 (noch zu erstellen)
- **Trace-Input (Meta-Harness-Pattern)** → `exec-17.md` Stufe 5+6 + exec-18 `agent.traces`

### 4e. Verbindung Skills ↔ Harness

Skills sind EIN Hebel den der Harness-Proposer nutzen kann. Aktuell sind Skills und Harness
getrennte Pipelines. Verbindung:

- Harness-Proposer liest Skill-Audit-Events (SKILL_FOUND/REFINED/USED) als Input
- Harness-Proposer kann vorschlagen: "Skill X hat hohe false-trigger-rate → Description aendern"
- Harness-Proposer kann vorschlagen: "Coverage-Threshold fuer Kimi von 4.5 auf 4.0 senken"
- **Aber:** Harness-Proposer editiert NICHT Skill-Content direkt — das macht der Skill-Refiner.
  Harness aendert die **Strategie** (wann laden, wie viele, welcher Mode), nicht den **Inhalt**.

### 4f. Layer-aware Harness (aus `memory_kg.md`)

Der Harness muss kuenftig nicht nur `memory on/off` tunen, sondern die
getrennten Schichten bewusst orchestrieren:

- `global world model`
- `personal memory`
- `personal knowledgebase`
- `context assembly`

Was hier Harness ist:

- Retrieval-Reihenfolge
- Gewichte / Caps / Thresholds
- Query-Mode-Routing
- Evidence-Join-Policy
- Degradation-Verhalten

Was **nicht** Harness ist:

- wie Claims intern validiert werden
- wie der KG intern gespeichert wird
- wie KB-Artefakte persistiert werden

Fehlende Arbeit:

- [~] Search-Set / Evaluator um Query-Typen erweitern: `world`, `personal_memory`, `personal_kb`, `mixed` — Personal-Memory-Smoke unterscheidet jetzt bereits `verbatim` / `derived` / `cross_session` / `forgetting`, layer-uebergreifendes Harness-Search-Set fehlt noch
- [ ] Harness-Configs um layer-aware Parameter erweitern: `world_enabled`, `kb_enabled`, `derived_first`, `evidence_join_required`, `max_items_per_layer`
- [ ] Retrieval-Order als optimierbaren Harness-Parameter modellieren statt fest im Code zu verstreuen
- [ ] `Personal Knowledgebase` als eigene Lane im Harness messen statt nur als Memory-Nebeneffekt

### 4g. Consumer-spezifische Harness-Configs

`memory_kg.md` trennt Consumer sauber:

- `LLM-Agent`
- `Frontend-UI`
- `Signal-/Scoring-Pipeline`
- `Merge-Layer`

Der Harness braucht dafuer nicht vier verschiedene Engines, aber
consumer-spezifische Konfigurationen.

Fehlende Arbeit:

- [ ] `component_configs` / HarnessConfig um `consumer_type` oder gleichwertige Policy-Dimension erweitern
- [ ] getrennte Eval-Sets fuer `LLM-Agent` vs `Frontend-/Merge-Layer` definieren
- [ ] Frontend-/Merge-nahe Harness-Varianten auf leichtere, user-owned Daten (`personal KB`) optimieren statt auf tiefen Runtime-Scan
- [ ] Signal-/Scoring-Harness explizit auf strukturierte Features statt freie Langkontext-Loops optimieren

### 4h. Degradation- und Policy-aware Evaluation

Bislang messen wir hauptsaechlich Qualitaet / Kosten / Traces.
Mit `memory_kg.md` kommen Policy-Gates dazu.

Fehlende Arbeit:

- [ ] Harness-Scorer um Policy-Verstoesse erweitern: `derived_without_evidence`, `world_without_provenance`, `silent_missing_layer_fallback`
- [ ] Degradation-Flags als Eval-Signal loggen: z. B. `NO_WORLD_KG`, `NO_PERSONAL_KB`, `WORLD_CLAIM_CONFLICT`
- [ ] Pareto-Betrachtung nicht nur `accuracy x cost x latency`, sondern mindestens optional auch `grounding/policy-compliance`

---

## 5. Abgrenzung zu anderen Execs

| Exec | Scope | Beziehung zu exec-harness |
|---|---|---|
| **exec-17** | Observability-Infrastruktur (OTel, Langfuse, Audit, MCP) + Harness Stufe 5+6 Implementation | exec-17 Stufe 5+6 ist die **Implementierungsbasis**. exec-harness ist das **Architektur- und Strategie-Dokument**. |
| **exec-18** | Unified Agent Schema (DB-Tabellen) | exec-18 liefert persistent Traces + component_configs — der **Daten-Layer** den der Harness-Proposer liest. |
| **exec-skills** | Skill Discovery, Refinement, Evolution | Skills sind ein **Harness-Hebel**. exec-skills managed Skill-Content + Retrieval, exec-harness managed die Strategie (wann/wie Skills eingesetzt werden). |
| **exec-memory** | Memory Architecture, Hindsight, Verbatim | Memory-Config ist ein Harness-Parameter. exec-memory baut die Engine, exec-harness tuned die Config. |
| **exec-world-model** | Global World Evidence, Claims, KG, Adjudication | Harness entscheidet, wann und wie die Welt-Schicht gezogen wird, aber nicht wie Claims intern validiert werden. |
| **exec-personal-kb** | Personal Knowledgebase, Capture, Curation, Retrieval | Harness entscheidet, wann die KB Lane fuer welchen Consumer genutzt wird, aber nicht wie die KB gespeichert/editiert wird. |
| **exec-context** | Prompt-Reihenfolge, Token-Budget, Caching | Context-Assembly ist Harness-Kernfunktion. exec-context definiert Regeln, exec-harness optimiert Parameter. |
| **exec-eval** | Evaluation Framework | Evaluator-Patterns aus exec-eval werden vom Harness-Loop genutzt. |

---

## 6. Verify-Gates

**Verifiziert (2026-04-16):**
- [x] exec-18 Tabellen `agent.sessions`, `agent.traces`, `agent.spans`, `agent.components`, `component_configs`, `component_links` existieren (Migrationen 016-018 durchgelaufen)
- [x] `agent/sessions.py` CRUD: create/update/get funktional (Smoke-Test)

**Verifiziert (2026-04-16, Stream 3 Wiring):**
- [x] Harness-Proposer liest Skill-Audit-Events: `_gather_context()` extrahiert SKILL_FOUND/REFINED/USED Events, aggregiert `by_action`, `recent_coverage_scores`, `recent_skill_ids`. Proposer-System-Prompt erweitert um "4. SKILL STRATEGY". Smoke: 15 Skill-Events korrekt aggregiert.
- [x] Proposer integriert Trigger-Quality: `compute_trigger_quality(days=30)` als `trigger_quality` Feld im Context. Smoke: `trigger_quality: True` (Daten vorhanden).
- [x] Harness-Scorer erweitert: `session_status` + `session_summary` aus `agent.sessions` (exec-18), `skills_loaded` Set + `skill_events` Count aus Audit-Events. Fallback auf thread_id wenn keine Session-Row.
- [x] Evaluator Search-Set von 5 auf 15 Queries erweitert: `expected_skills[]` pro Query, neue Kategorien `skill_retrieval`, `risk_assessment`. Abdeckung: simple_chat, simple_query, multi_tool, memory_recall, analysis, skill_retrieval, risk_assessment.

**Verifiziert (2026-04-16, Folge-Items):**
- [x] PostgresSpanProcessor in `agent/tracing.py` — persistiert OTel Spans → `agent.traces` + `agent.spans` parallel zu OpenObserve. Env `AGENT_PERSIST_TRACES=1` (default off). Fire-and-forget, async-safe. Upsert auf traces (root span creates, children update), ON CONFLICT DO NOTHING auf spans.
- [x] `agent/graph/runner.py:_run_graph()` — erstellt Session-Row via `create_session()` bei Agent-Start (`session_type='agent_chat'`, `bank_id='user-{user_id}'`), updated auf `completed`/`errored` mit Summary am Ende. Session-ID wird an `session_span()` durchgereicht.

**Noch offen:**
- [x] `component_configs` in DB — Proposer schreibt nach `agent.component_configs` (primary) + Filesystem (secondary). Env `HARNESS_SAVE_MODE=db|filesystem|both` (default `both`). `pareto.py:load_all_candidates()` merged DB + Filesystem dedupliziert. Verifiziert: 0 candidates korrekt geladen, kein Crash (2026-04-16).
- [ ] AutoResearch Loop fuer mindestens 1 Komponente (z.B. Finder top_k Sweep)
- [ ] `agent/harness/proposer.py propose_loop()` laeuft mit echtem LLM + echten Traces
- [ ] Pareto-Frontier nach 5+ Proposer-Iterationen zeigt sichtbare Verbesserung auf Search-Set
- [ ] Search-Set deckt `world` / `personal_memory` / `personal_kb` / `mixed` Queries ab
- [ ] Harness-Evals bestrafen `world` ohne Provenance und `derived` ohne Evidence-Join
- [ ] Consumer-spezifische Harness-Configs sind separat messbar

---

## 4f. Fitness-scoring via InsightsEngine (Phase-B P4 DONE)

**Status:** DONE — 2026-04-20.
**Cross-ref:** `exec-hermes.md §0` (insights.py row, dual-path), `exec-16.md §2.10`, plan `~/.claude/plans/ja-mach-explore-daf-r-glimmering-gizmo.md §P4`.

P4 adds `agent/billing/insights.py` (port of `_ref/hermes-agent/agent/insights.py`) with **dual-path architecture**:

- **Production billing-path** (owned by `exec-16.md §2.10`): REST endpoint `GET /api/v1/billing/insights?user_id=X&days=7` serves Control-UI dashboards
- **Meta-harness fitness-path** (owned here): `agent/harness/scorer.py` imports `InsightsEngine.cost_for_session(session_id)` to get `total_cost_usd` + `cost_per_task` as Pareto-fitness dimensions

**Important distinction (user emphasized):** `agent/harness/` is **meta-harness** (EvoSkill-style, optimizes the harness itself). It is NOT the "agent-harness" (production runtime — exec-16 billing). Both need cost-data, different aggregation semantics:

- Meta-harness: per-proposer-iteration cost, per-candidate-config cost — fitness signal for "which harness-variant is cheaper for same accuracy"
- Production billing: per-user-per-day cost — billing signal for "what does this user owe"

Same `CanonicalUsage` data, same `estimate_usage_cost()` function, different aggregation windows + surfaces.

**Replace hardcoded pricing in `scorer.py`:** `MODEL_COST_PER_MTOK` dict removed. `_estimate_cost(model, total_tokens)` now delegates to `estimate_usage_cost` from `agent/billing/usage_pricing.py`. Since audit-events only preserve `total_tokens` (not the input/output split), the scorer applies a 60/40 heuristic — exact costs are still available via `InsightsEngine.cost_for_session(session_id)` which aggregates spans directly. If LiteLLM has no data AND the model isn't in the snapshot, the scorer falls back to `DEFAULT_COST_PER_MTOK=3.0` for fitness-scoring continuity (production billing prefers `status='unknown'` instead).

---

## 4g. A/B Experiment Fitness Backfill (Phase-C DONE)

**Status:** DONE — 2026-04-20.
**Cross-ref:** `exec-hermes.md §0` (Hybrid Agno-Loop row), migration 025 `agent.ab_experiments`, `agent/runners/dispatcher.py`.

Phase-C ships the A/B dispatcher (SimpleLoop vs LangGraph). For any A/B experiment to yield a go/no-go decision we need a **quality signal** per turn — not just latency/cost/errors. This section documents how meta-harness provides that signal.

### 4g.1 Composite fitness scalar

`scorer.py::composite_fitness(score_dict) -> float` collapses the multi-dimensional score into a scalar in `[0, 1]` so SQL aggregation works:

| Dimension | Weight | Source |
|---|---|---|
| `tool_success_rate` | 0.30 | `tool_successes / tool_calls` (1.0 if no tool calls) |
| `completed` | 0.25 | `session_status == "completed"` (0.0 if "errored") |
| `turn_efficiency` | 0.20 | `1 / turns` |
| `memory_utilization` | 0.15 | 1.0 if any `memory_recall` audit events |
| `cost_inverse` | 0.10 | `1 / (1 + cost_usd)` — cheap = better |

Raw dimensions remain in the `score_session(thread_id)` return dict for anyone who wants per-axis Pareto analysis. The scalar is the convenience-path for SQL aggregation.

### 4g.2 Backfill contract

`scorer.py::backfill_ab_experiment_fitness(thread_id, fitness_score, eval_id, session_id)` UPDATEs `agent.ab_experiments.harness_fitness_score`. Matches on `thread_id` by default (scorer's natural key, set by the dispatcher at INSERT time) or on `session_id` when explicitly passed.

`score_session(thread_id)` dispatches the backfill via `asyncio.create_task` — fire-and-forget so scorer latency is unaffected. DB errors are caught and logged (fail-soft; missing harness_fitness_score is tolerated by the aggregation query).

### 4g.3 Decision query

Once data is flowing, the canonical A/B evaluation is:

```sql
SELECT variant,
       COUNT(*)                           AS n,
       AVG(harness_fitness_score)         AS mean_fitness,
       STDDEV(harness_fitness_score)      AS std_fitness,
       AVG(duration_ms)                   AS mean_latency_ms,
       AVG(cost_usd)                      AS mean_cost_usd,
       SUM(CASE WHEN fallback_triggered THEN 1 ELSE 0 END) AS fallbacks
FROM agent.ab_experiments
WHERE experiment_id = 'phase-c-hybrid-loop'
  AND finished_at IS NOT NULL
  AND harness_fitness_score IS NOT NULL
GROUP BY variant;
```

Statistical significance via Welch's t-test on `harness_fitness_score` between `variant='simple'` and `variant='langgraph'` rows once N > 100 per variant (Phase-D analysis task, not automated here).

### 4g.4 TODO — post-landing integration

- [x] **Scheduled scorer job — DONE 2026-04-20 (commit `f027e8f`).** Implemented in `exec-scheduler.md §8.1`. River `HarnessBackfillWorker` runs `*/15 * * * *` → `HarnessBackfillHTTPClient` → `POST /internal/harness/backfill` → polls `agent.ab_experiments` where `harness_fitness_score IS NULL AND finished_at IS NOT NULL`, calls `score_session(thread_id)`, returns `{scored, skipped}`. End-to-end Phase-C data flow active.
- [x] **Harness-run eval_id wiring** — ✅ **DONE 2026-04-23.** `score_session(thread_id, *, eval_id=None)`, `score_sessions(thread_ids, *, eval_id=None)`, `evaluate_single(..., eval_id=None)`, `evaluate_search_set(..., eval_id=None)` alle akzeptieren optional eval_id; `evaluate_search_set` auto-generiert `run-<uuid12>` wenn keine mitgegeben. `POST /internal/harness/backfill` akzeptiert optional JSON body `{"eval_id": "<id>"}`. River worker passt scheduled-backfill ohne body → NULL. 4 tests added.
- [ ] **Per-variant Pareto dashboards** — Control-UI panel that reads the decision query above and renders fitness vs. cost vs. latency per variant. Uses existing exec-17 Grafana/OpenObserve stack. *Frontend-Arbeit; braucht dev-stack.*
- [ ] **Fitness weights tuning** — the 30/25/20/15/10 split is an informed default, not empirically validated. Phase-D should let harness itself propose weight candidates and validate against held-out sessions.

---

## Changelog-append (Phase-B + Phase-C)

| Date | Change |
|---|---|
| 2026-04-20 | exec-hermes Phase-B P2 stub added: §4f (fitness via InsightsEngine, filled P4). Clarified meta-harness-vs-production-billing dual-path. |
| 2026-04-20 | **§4g added (Phase-C DONE):** A/B experiment fitness backfill. `composite_fitness` scalar + `backfill_ab_experiment_fitness` wired into `score_session`, fire-and-forget UPDATE on `agent.ab_experiments.harness_fitness_score`. Resolves Contrarian-CRITICAL-3: harness provides the user-satisfaction signal instead of self-built `suspected_retry` heuristic. TODOs: scheduled scorer job (NATS/pg_cron), eval_id wiring, Pareto dashboards, weights tuning. 12 new unit tests. |
| 2026-04-20 | **§4g.4 scheduled-scorer DONE** (commit `f027e8f`) — River worker in `go-appservice/internal/scheduler/` polls ab_experiments every 15 min + calls new `POST /internal/harness/backfill` Python endpoint. End-to-end Phase-C data flow active. Remaining TODOs: eval_id wiring, Pareto dashboards, fitness-weights tuning. |
| 2026-04-23 | **§4g.4 eval_id wiring DONE.** `score_session` / `score_sessions` / `evaluate_single` / `evaluate_search_set` + HTTP endpoint alle nehmen optional `eval_id` ent; `evaluate_search_set` auto-generiert `run-<uuid12>`. Scheduled River-worker backfill läuft ohne eval_id (column bleibt NULL für ad-hoc); explicit eval runs tag rows für Pareto-grouping. 4 new tests. Remaining §4g.4 TODOs: Pareto dashboards (frontend, braucht dev-stack), fitness-weights tuning (Phase-D research). |
| 2026-04-20 | **DSPy evaluation track opened** → `exec-14-DSPy.md` (Draft/Research). Matrix's `agent/harness/` macht konzeptionell was DSPy's GEPA/MIPRO SOTA macht (metric-driven LLM-program optimization, pareto-frontier-evolution). 5 foundation-papers in `docs/papers/`. Decision-path: replace custom harness-optimization durch DSPy (D-1), additiv (D-2), oder nur neue flows? sota-contrarian stakes=high gate bevor jede impl. |
