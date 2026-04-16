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

### 4d. EvoSkill Evaluator-Stage Integration

**Status:** Nicht gebaut. EvoSkill's Stage 4 (Evaluator: Score Varianten gegen Validation-Set)
ist das fehlende Stueck zwischen unserem Proposer (Stage 2) und Frontier-Tracking (Stage 5).

Fuer Skills: `exec-skills.md §8b.3` (Composition A/B Eval) ist genau diese Evaluator-Stage.
Fuer Harness: `agent/harness/evaluator.py` existiert bereits (exec-17 Stufe 6.1).

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
