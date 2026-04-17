# Context Engineering -- Wer braucht wann welchen Kontext?

> **Stand:** 22. Februar 2026
> **Zweck:** Definiert die Context-Strategie fuer alle Consumer im System: Welche Memory-Schichten werden fuer welchen Query-Typ angezapft, wie wird Relevanz bewertet, wie werden Multi-Source-Ergebnisse gemerged, und wie wird das Token-Budget fuer LLM-Agents verwaltet.
> **Abgrenzung zu MEMORY_ARCHITECTURE.md:** Memory definiert *was wo gespeichert wird* (Infrastruktur, Schemas, Persistenz). Context Engineering definiert *was wann fuer wen zusammengestellt wird* (Policies, Scoring, Budgets). Memory ist die Bibliothek. Context Engineering ist der Bibliothekar.
> **Referenz-Dokumente:** [`MEMORY_ARCHITECTURE.md`](./MEMORY_ARCHITECTURE.md) (M1-M5, Zwei-Schichten-KG, Fast/Slow Lane), [`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) (Vier Agent-Rollen, Orchestration), [`AGENT_RUNTIME_ARCHITECTURE.md`](./AGENT_RUNTIME_ARCHITECTURE.md) (verbindliche Runtime-/Memory-Write-Policy), [`AGENT_SECURITY.md`](./AGENT_SECURITY.md) (Retrieval Broker, Capability Envelope), [`AGENT_HARNESS.md`](./AGENT_HARNESS.md) (Constrain/Inform/Verify/Correct), [`archive/KG_ONTOLOGY.md`](./archive/KG_ONTOLOGY.md) (Ontologie-Quellen; archivierte Referenz), [`GAME_THEORY.md`](./GAME_THEORY.md) (Krisenlogik, Strategeme), [`Advanced-architecture-for-the-future.md`](./Advanced-architecture-for-the-future.md) (RAG/Reasoning Patterns), [`RAG_GRAPHRAG_STRATEGY_2026.md`](./RAG_GRAPHRAG_STRATEGY_2026.md) (Dual Pipeline, Query-Modi, GraphRAG/UQ-Einsatzregeln), [`context_engineering_2.0_research.md`](./research/context_engineering_2.0_research.md) (CE 2.0 Research: DyCP, LLMLingua-2, RAG-Debatte, Self-Baking), [`EPISTEMIC.md`](./EPISTEMIC.md) (Verbindliche epistemische Systemregeln — dieses Dokument definiert WER WANN WAS bekommt, EPISTEMIC.md definiert die Regeln WAS als Truth/Belief/Scenario gilt und wie Merge/Promotion funktioniert), [`ENTROPY_NOVELTY.md`](./ENTROPY_NOVELTY.md) (Override-Cap, Decay, Contrarian Context Injection — direkte Erweiterungen fuer Sek. 4.3/4.4)
> **Primaer betroffen:** Python-Backend (Agent-Pipeline, Context Assembler), Frontend (User-KG Queries, Merge-Layer), Go Gateway (SSE Context-Updates)

---

## Inhaltsverzeichnis

1. [Warum ein eigenes Context-Dokument?](#1-warum-ein-eigenes-context-dokument)
2. [Context-Consumer und ihre Anforderungen](#2-context-consumer-und-ihre-anforderungen)
3. [Retrieval-Policies: Wer zapft welche Schicht an?](#3-retrieval-policies-wer-zapft-welche-schicht-an)
4. [Relevance-Scoring und Ranking](#4-relevance-scoring-und-ranking)
5. [Token-Budget-Management (LLM-spezifisch)](#5-token-budget-management-llm-spezifisch)
6. [Multi-Source Context Merging](#6-multi-source-context-merging)
7. [Context Freshness und Staleness](#7-context-freshness-und-staleness)
8. [Context pro Agent-Rolle](#8-context-pro-agent-rolle)
9. [Observability und Debugging](#9-observability-und-debugging)
10. [Offene Fragen](#10-offene-fragen)

---

## 1. Warum ein eigenes Context-Dokument?

`MEMORY_ARCHITECTURE.md` Sek. 5.5 (M5: Agent Working Memory) beschreibt den Context Assembler fuer LLM-Agents. Das reicht nicht, weil:

- **Vier Consumer, nicht einer.** Neben LLM-Agents brauchen auch die Frontend-UI, die Signal-Pipeline und der Merge-Layer (Frontend-KG + Backend-KG) kontextuelle Daten. Jeder hat andere Latenz-Anforderungen, andere Formate und andere Relevanz-Kriterien.
- **Context ist eine Runtime-Entscheidung.** Memory ist statisch konfiguriert (Redis TTL, KG-Schema, Episodic-Tabelle). Context wird zur Laufzeit dynamisch zusammengestellt -- abhaengig von der Query, dem User, dem Marktregime und der Verfuegbarkeit der Quellen.
- **Fehlerquelle Nr. 1 bei Agent-Systemen.** Die haeufigste Ursache fuer schlechte Agent-Ergebnisse ist nicht das Modell, sondern falscher oder fehlender Kontext. Dieses Dokument macht die Context-Strategie explizit und testbar.

### 1.1 Verbindliche Vorstufe: Persistence vor Retrieval

Context Assembly liest nicht direkt aus Source-Onboarding oder ungeprueften
Rohdownloads. Die Betriebsreihenfolge ist:

`source selection -> source onboarding -> fetch/cache/snapshot -> normalize -> retrieval/context`

Das heisst:

- Raw snapshots gehoeren zuerst in die Source-Persistence-Schicht.
- Der Context Assembler arbeitet auf normalisierten Fakten, Episoden,
  KG-Knoten und bewusst freigegebenen Vector-Dokumenten.
- Embeddings oder Retrieval aus unnormalisierten ZIP/CSV/XML/JSON-Rohdaten sind
  kein gueltiger Produktionspfad.

Owner dieser Vorstufen:

- `docs/specs/execution/source_persistence_snapshot_delta.md`
- `docs/specs/execution/vector_ingestion_delta.md`

---

## 2. Context-Consumer und ihre Anforderungen

Das System hat vier verschiedene Consumer die Kontext benoetigen. Jeder hat ein eigenes Profil:

| Consumer | Beschreibung | Latenz-Budget | Format | Typische Queries |
|---|---|---|---|---|
| **LLM-Agent** | Game Theory Scorer, BTE Extractor, Verifier, Synthesizer (`AGENT_ARCHITECTURE.md` Sek. 2) | ~500ms Assembly + LLM-Latenz | Token-String (Prompt) | "Analysiere dieses Event", "Extrahiere BTE-Marker" |
| **Frontend UI** | GeoMap Impact Panel, Portfolio Risk View, Signal Dashboard | <100ms | JSON via API / User-KG Query | "Welche Positionen sind betroffen?", "Aktuelle Alerts" |
| **Signal Pipeline** | Composite Scoring, Indicator Service, Soft-Signal Aggregation | <50ms | Strukturierte Daten (Python dicts / Redis) | "Regime-Kontext fuer Scoring", "Aktuelle Indikator-Werte" |
| **Merge-Layer** | Verbindet Frontend User-KG mit Backend Domain-KG (`MEMORY_ARCHITECTURE.md` Sek. 5.2) | <200ms | Hybrid (Graph-Result + Vector-Result + JSON) | "Mein Portfolio + Backend Kausalketten" |

### Consumer-Abhaengigkeiten

```
                    ┌──────────────┐
                    │  LLM-Agent   │
                    │  (500ms)     │
                    └──────┬───────┘
                           │ liest von
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ Backend-KG  │ │ Episodic    │ │ Vector Store│
    │ (M2a)       │ │ (M3)        │ │ (M4)        │
    └─────────────┘ └─────────────┘ └─────────────┘
           ▲                                ▲
           │                                │
    ┌──────┴───────┐                        │
    │ Merge-Layer  │────────────────────────┘
    │ (200ms)      │
    └──────┬───────┘
           │ liest von
    ┌──────▼───────┐
    │ Frontend-KG  │
    │ User (M2b)   │
    └──────┬───────┘
           │ liefert an
    ┌──────▼───────┐         ┌──────────────┐
    │ Frontend UI  │◄────────│ Redis Cache  │
    │ (<100ms)     │         │ (M1)         │
    └──────────────┘         └──────┬───────┘
                                    │ liefert an
                             ┌──────▼───────┐
                             │Signal Pipeline│
                             │ (<50ms)       │
                             └──────────────┘
```

---

## 3. Retrieval-Policies: Wer zapft welche Schicht an?

Nicht jeder Consumer braucht alle Memory-Schichten. Die Matrix definiert pro Query-Typ welche Schichten angezapft werden und in welcher Reihenfolge:

### 3.1 Query-Typ → Memory-Schicht Matrix

| Query-Typ | Working (M1) | KG Backend (M2a) | KG Frontend (M2b) | Episodic (M3) | Vector (M4) | Consumer |
|---|---|---|---|---|---|---|
| "Impact auf mein Portfolio?" | Aktuelle Preise | Kausalketten (Event→Region→Symbol) | Positionen, Alerts | Historische Parallelen | -- | Merge-Layer → UI |
| "Analysiere diesen Earnings Call" | -- | BTE-Marker Definitionen, Behavioral States | -- | Letzte Analyse desselben CEO | Aehnliche Calls (Embedding) | LLM-Agent |
| "Ist dieses Event kaufrelevant?" | Aktueller Preis, Regime | Strategem-Match, Region→Symbol | User-Alerts, Positionen | Score vs. Marktreaktion Historie | Aehnliche Events | LLM-Agent + Merge |
| "Dashboard-Refresh (GeoMap)" | Alle Geo-Caches | -- | Positionen, Alerts, Drawings | -- | -- | Frontend UI |
| "Composite Signal berechnen" | Indikator-Cache, Regime | -- | -- | Letzte Signal-Accuracy | -- | Signal Pipeline |
| "Candidate accept/reject?" | -- | Event-Kategorie→Strategem | User-Override-Historie | Vergangene Overrides fuer Region | -- | Merge-Layer → UI |
| "Profiling Update (Needs Map)" | -- | Needs-Typ Definitionen | -- | Historische Extractions (4-8 Calls) | -- | LLM-Agent |
| "Zentralbank-Rede analysieren" | -- | BTE-Marker + Central Bank Baseline | -- | Letzte Reden desselben Speakers | Aehnliche Reden (Embedding) | LLM-Agent |

### 3.2 Retrieval-Reihenfolge und Fallbacks

Fuer jeden Query-Typ gilt eine definierte Reihenfolge. Wenn eine Schicht nicht antwortet (Timeout, leer), greift der Fallback:

```
STANDARD-REIHENFOLGE (fuer LLM-Agent Queries):
  1. Working Memory (Redis M1)     → schnellste Schicht, immer zuerst
  2. KG Backend (M2a)              → strukturierte Fakten, deterministisch
  3. Episodic (M3)                 → Erfahrungswissen, bedingt relevant
  4. Vector Store (M4)             → semantische Aehnlichkeit, langsamste Schicht

FALLBACK-REGELN:
  - M1 nicht erreichbar → Direkt M2a (KG hat eigenen Cache)
  - M2a nicht erreichbar → LLM-Agent laeuft mit reduziertem Kontext
    → Flag: "NO_KG_CONTEXT" im Agent-Output (Confidence automatisch -0.2)
  - M3 leer (kein historischer Match) → Agent arbeitet ohne Episodic
    → Kein Flag (Episodic ist nice-to-have, nicht critical)
  - M4 nicht erreichbar → Kein semantischer Kontext
    → Flag: "NO_VECTOR_CONTEXT" (Confidence automatisch -0.1)
```

### 3.3 Frontend-spezifische Retrieval-Policy

```
FRONTEND UI QUERIES (< 100ms Budget):
  1. User-KG (M2b, lokal im Browser)  → sofort, kein Netzwerk
  2. Redis-Cache via API (M1)          → nur wenn User-KG nicht ausreicht
  3. NIEMALS direkt M2a/M3/M4          → nur ueber Merge-Layer

MERGE-LAYER QUERIES (< 200ms Budget):
  1. Frontend schickt Symbol-IDs an Backend
  2. Backend queried M2a (KG) + optional M3 (Episodic) + optional M4 (Vector)
  3. Backend liefert angereicherte Antwort zurueck
  4. Frontend merged mit User-KG Ergebnis
```

**Review-Ergaenzung (SOTA 2026, Empfehlung):**
- Fuer interaktive UI-Subfeatures kann optional ein **reactive client store layer** (z. B. TanStack-DB-Pilot) vor M1 gesetzt werden.
- Dieser Layer ist **additiv** und ersetzt weder M1 (shared cache) noch M2a/M3/M4 als backendseitige Kontextebenen.
- Production-Regel: Kein stiller Local-Fallback bei Kontext-Queries; degradierte Antworten muessen Flags tragen.

---

## 4. Relevance-Scoring und Ranking

Wenn mehrere Quellen Kontext liefern, braucht das System eine definierte Priorisierung. Nicht alles was verfuegbar ist, ist auch relevant.

### 4.1 Scoring-Dimensionen

Jedes Context-Fragment wird auf vier Dimensionen bewertet:

| Dimension | Gewichtung | Berechnung | Beispiel |
|---|---|---|---|
| **Freshness** | 0.30 | `1.0 - (age_hours / max_age_hours)`. Decay-Funktion, nicht linear: Events < 2h = 1.0, < 24h = 0.7, < 7d = 0.3, aelter = 0.1 | Iran-Event von vor 2h schlaegt eines von vor 2 Wochen |
| **User-Proximity** | 0.25 | Position im User-KG: `hat_position` = 1.0, `watchlist` = 0.7, `kein_bezug` = 0.2 | GLD in Portfolio > GLD auf Watchlist > GLD generell |
| **Confidence** | 0.25 | Aus KG-Edge-Confidence oder Episodic-Accuracy. Unter 0.5 wird nicht aufgenommen | KG-Edge "Iran→Oil" mit confidence 0.9 > "Iran→Tech" mit 0.4 |
| **Regime-Fit** | 0.20 | Passt der Kontext zum aktuellen Marktregime? risk_off → Flucht-Assets hoeher gewichten | Im risk_off-Regime: Gold-Kontext relevanter als Tech-Kontext |

### 4.2 Composite Relevance Score

```python
def relevance_score(fragment: ContextFragment, query: Query, user: UserContext) -> float:
    freshness = compute_freshness(fragment.timestamp, query.timestamp)
    proximity = compute_user_proximity(fragment.symbols, user.user_kg)
    confidence = fragment.confidence
    regime_fit = compute_regime_fit(fragment.symbols, user.current_regime)

    score = (
        0.30 * freshness +
        0.25 * proximity +
        0.25 * confidence +
        0.20 * regime_fit
    )

    return score
```

### 4.3 Cutoff- und Cap-Regeln

| Regel | Wert | Begruendung |
|---|---|---|
| **Minimum Relevance** | 0.3 | Fragmente unter 0.3 werden nicht in den Kontext aufgenommen |
| **Max Fragments pro Schicht** | M2a: 10, M3: 3, M4: 5 | Verhindert dass eine Schicht den Kontext dominiert |
| **Deduplication** | Symbol-basiert, mit Ausnahme | Wenn M2a und M4 beide "GLD" liefern, wird das M2a-Fragment (strukturiert) bevorzugt. **Ausnahme:** Wenn M4 eine andere Kausalkette liefert als M2a fuer dasselbe Symbol, werden beide aufgenommen (unterschiedliche Perspektiven) |
| **Diversity Floor** | Min **3** verschiedene Regionen/Sektoren in Top-10 | Verhindert Echo-Chamber-Effekt bei Kontext-Assembly |
| **Strategem-Diversitaet** | Min **2** verschiedene Strategem-Typen | Verhindert Strategem-Monokultur (immer dasselbe Muster matchen) |
| **Schwaches-Signal-Pflicht** | Min **1** Fragment mit Confidence 0.4-0.6 | Erzwingt Exposition gegenueber unsicheren aber potentiell wichtigen Signalen |

> **Entropy-Schutz (ENTROPY_NOVELTY.md Sek. 5.4):** Die Diversity Floor ist ein expliziter Anti-Collapse-Mechanismus. Ohne sie kann Feedback Amplification (Sek. 4.4) den Kontext auf wenige Regionen/Strategeme einengen. Die Erhoehung von 2→3 Regionen und die neuen Regeln fuer Strategem-Diversitaet und schwache Signale sichern eine Mindest-Novelty im System ab.

### 4.4 User-Feedback-Loop fuer Relevance

Relevance-Scoring ist nicht statisch. Es lernt aus User-Verhalten:

| Signal | Auswirkung | Speicherung |
|---|---|---|
| User rejected Candidate aus Region X (3x in Folge) | Region X Proximity-Score fuer diesen User: -0.15 | User-KG: `user_override` Edges |
| User akzeptiert Candidate aus Sektor Y | Sektor Y Proximity-Score: +0.1 | User-KG |
| User oeffnet Impact-Panel fuer Symbol Z haeufig | Symbol Z bekommt impliziten Proximity-Bonus | TanStack Query Access-Log (Client-Side) |
| Agent-Prediction war korrekt (Episodic Feedback) | Confidence der verwendeten KG-Edges steigt um 0.05 (Cap: 0.95) | Backend Episodic (M3) |

#### 4.4.1 Override-Cap und Decay (Entropy-Schutz)

> **Problem (ENTROPY_NOVELTY.md Sek. 4.2):** Ohne Begrenzung kann ein User durch wiederholte Rejections ganze Regionen/Sektoren aus seinem Kontext tilgen -- irreversibel. Das ist der staerkste Feedback-Amplifier im System und fuehrt direkt zu geographischer/sektoraler Dimensionalitaets-Kontraktion.

| Regel | Wert | Begruendung |
|---|---|---|
| **Max kumulativer Proximity-Shift pro Region** | **-0.30 Cap** | Verhindert vollstaendiges Ausblenden einer Region. Soft-Warning bei -0.20: "Du hast [Region]-Events stark runtergewichtet. Trotzdem informiert bleiben?" |
| **Max kumulativer Proximity-Shift pro Sektor** | **-0.30 Cap** | Analog fuer Sektoren |
| **Monatlicher Decay** | **+0.05 pro Monat** zurueck Richtung Neutral (0.0) | Alte Rejections verlieren ueber Zeit an Gewicht. Ein User der vor 6 Monaten MENA abgelehnt hat, bekommt langsam wieder MENA-Content. Erzwingt periodische Re-Exposition |
| **Transparency** | User sieht aktuelle Override-Status | Bei Cap: expliziter Hinweis im UI. Optional: "Override-History" im Settings-Panel |

**Implementation:**
```python
def apply_override(user_kg, region, shift):
    current = user_kg.get_override(region)
    new_val = max(current + shift, -0.30)  # Cap
    user_kg.set_override(region, new_val)
    if new_val <= -0.20:
        emit_warning(f"Region {region} stark runtergewichtet ({new_val:.2f})")

def monthly_decay(user_kg):
    for override in user_kg.get_all_overrides():
        if override.value < 0:
            override.value = min(override.value + 0.05, 0.0)  # Decay toward neutral
```

**Prioritaet:** HOCH. ~20 LoC, verhindert den schlimmsten Feedback-Loop im System.

---

## 5. Token-Budget-Management (LLM-spezifisch)

> Erweitert `MEMORY_ARCHITECTURE.md` Sek. 5.5 (M5). Dort ist die Grundstruktur definiert, hier die detaillierte Strategie.
>
> **Empirische Begruendung (CE 2.0 Research, Feb 2026):** Long-Context-Modelle (1M+ Tokens) machen RAG *nicht* obsolet. Studien zeigen: (1) Long-Context-Queries sind bis zu 1.250x teurer als gezieltes RAG bei 30-60s Latenz vs. ~1s. (2) "Context Rot": Modellqualitaet sinkt messbar ab ~32K Tokens (Distraction Ceiling). (3) "Lost in the Middle": Fakten in der Mitte langer Kontexte werden ignoriert (U-Kurven-Effekt). Unser Budget-Ansatz (6K-40K je Modell, Priority-Stack) ist daher korrekt und konservativ.
> Quellen: [Byteiota: RAG vs Long Context 2026](https://byteiota.com/rag-vs-long-context-2026-retrieval-debate/), [LightOn AI: RAG is Dead, Long Live RAG](https://www.lighton.ai/lighton-blogs/rag-is-dead-long-live-rag-retrieval-in-the-age-of-agents), [Stevens Online: Hidden Economics of AI Agents](https://online.stevens.edu/blog/hidden-economics-ai-agents-token-costs-latency/). Vollstaendige Analyse: [`context_engineering_2.0_research.md`](./research/context_engineering_2.0_research.md) Sek. 2.2.

### 5.1 Budget-Allokation nach Modell-Klasse

| Modell-Klasse | Total Budget | System | KG-Slice | Episodic | Vector/RAG | Current Input | Reserve |
|---|---|---|---|---|---|---|---|
| **Small** (8K Context) | 6000 Tokens | 400 | 600 | 300 | 500 | 3500 | 700 |
| **Medium** (32K Context) | 20000 Tokens | 500 | 1500 | 800 | 2000 | 12000 | 3200 |
| **Large** (128K Context) | 40000 Tokens | 500 | 3000 | 2000 | 5000 | 25000 | 4500 |

Reserve wird fuer den Output des LLM reserviert (Structured JSON, Explanations).

### 5.2 Dynamische Allokation

Nicht jede Query braucht alle Slots. Wenn ein Slot leer bleibt, wird das Budget umverteilt:

```python
def allocate_budget(model_class: str, available_context: dict) -> dict:
    base = BUDGET_TABLE[model_class]
    allocation = {}
    remaining = base["total"]

    remaining -= base["system"]
    allocation["system"] = base["system"]

    for slot in ["kg_slice", "episodic", "vector_rag", "current_input"]:
        if available_context.get(slot):
            actual_tokens = count_tokens(available_context[slot])
            used = min(actual_tokens, base[slot])
            allocation[slot] = used
            remaining -= used
        else:
            allocation[slot] = 0

    allocation["reserve"] = remaining
    return allocation
```

**Beispiel:** Query "Analysiere dieses Event" -- kein Episodic Match vorhanden:
- Episodic Budget (800 Tokens bei Medium) wird frei
- 400 gehen zu KG-Slice (mehr Fakten), 400 zu Vector/RAG (mehr aehnliche Events)

### 5.3 Kompressionsstrategien

Kompression erfolgt in zwei Phasen: **Pre-Processing** (bevor Kontext ins Budget gerechnet wird) und **Budget-Overflow** (wenn das Budget trotzdem ueberschritten wird).

#### Phase 1: Pre-Processing Kompression (immer aktiv)

Diese Schritte laufen *vor* der Budget-Allokation und reduzieren den Input bevor er Token-Budget kostet:

| Schritt | Methode | Was es tut | Einsparung | Quelle |
|---|---|---|---|---|
| **A** | **LLMLingua-2** | Kleines Hilfsmodell (z.B. XLM-RoBERTa) entscheidet Token-fuer-Token welche Tokens entfernt werden koennen ohne Bedeutungsaenderung. Laeuft auf Retrieved Docs (M4) und lange Episodic-Eintraege (M3) bevor sie ins Budget gerechnet werden. | 50-80% Token-Reduktion bei <5% Qualitaetsverlust | [LLMLingua-2](https://llmlingua.com/llmlingua2.html), [Microsoft Research](https://www.microsoft.com/en-us/research/project/llmlingua/) |
| **B** | **DyCP Segment-Pruning** | Bei langen Dialog-Historien oder Event-Ketten: KadaneDial-Algorithmus (Modifikation von Kadane's Maximum-Subarray) berechnet fuer jedes Segment einen Relevance-Score relativ zur aktuellen Query. Nur Segmente ueber Threshold werden behalten. | 40-70% bei langen Historien, 0% bei kurzen | [DyCP: Dynamic Context Pruning](https://arxiv.org/abs/2601.07994) |

```python
def pre_compress(fragments: list[ContextFragment], query: Query) -> list[ContextFragment]:
    compressed = []
    for f in fragments:
        if f.source in ("M4_vector", "M3_episodic") and f.token_count > 200:
            f.text = llmlingua2_compress(f.text, target_ratio=0.4)
            f.token_count = count_tokens(f.text)

        compressed.append(f)

    if query.has_dialog_history and total_tokens(compressed) > query.budget * 0.7:
        compressed = dycp_prune(compressed, query, threshold=0.3)

    return compressed
```

**Wann welche Methode:**
- **LLMLingua-2:** Immer auf M4-Results und M3-Eintraege > 200 Tokens. Billiger als ein Extra-LLM-Call, reduziert Fuelltext mathematisch.
- **DyCP:** Nur bei Dialog-/Event-Historien > 5 Eintraege ODER wenn Pre-Budget > 70% des Totals. Behaelt den logischen Faden durch Subarray-Scoring.

#### Phase 2: Budget-Overflow Kompression (bei Ueberschreitung)

Wenn nach Phase 1 der verfuegbare Kontext das Budget immer noch ueberschreitet, wird in dieser Reihenfolge komprimiert:

| Prioritaet | Strategie | Schicht | Einsparung |
|---|---|---|---|
| 1 | Vector-Results auf Top-3 → Top-1 reduzieren | M4 | ~60% des Vector-Budgets |
| 2 | Episodic auf letztes Matching-Event kuerzen | M3 | ~70% des Episodic-Budgets |
| 3 | KG-Slice auf Distanz ≤ 1 statt ≤ 2 | M2a | ~50% des KG-Budgets |
| 4 | Current Input chunken + LLM-Zusammenfassung | Input | Variabel, teuer (extra LLM-Call) |

**Niemals komprimiert:**
- System Prompt (fix, definiert Agent-Verhalten)
- Guard-Definitionen (DRS-Schwellwerte, Regeln)
- Reserve (Output-Budget)

### 5.3a Context Compaction (ReMe, OpenClaw, Self-Hosted)

**Compaction ≠ Kompression:** Compaction ist Summarisieren *plus* Rehydration – nach dem Summary werden aktuelle Dateien neu gelesen, Todos wiederhergestellt, eine Fortsetzungs-Anweisung injiziert. Claude Code/Codex nutzen drei Ebenen: Microcompaction (Tool-Outputs auf Disk), Auto-Compaction (bei Headroom-Unterschreitung), Manual Compaction (`/compact`).

**Open Source, ohne Cloud-API:**
- **ReMe** ([agentscope-ai/ReMe](https://github.com/agentscope-ai/ReMe), Apache 2.0): `compact_memory`, `compact_tool_result`, `memory_search`. `LLM_BASE_URL` auf Ollama = self-hosted.
- **OpenClaw** ([openclaw/openclaw](https://github.com/openclaw/openclaw), MIT): Built-in Compaction, `/compact` Befehl, Session-JSONL-Persistenz.
- **Context Gateway** ([Compresr-ai/Context-Gateway](https://github.com/Compresr-ai/Context-Gateway), Apache 2.0): Agentic Proxy mit History-Compaction.
- **ClawVault** ([Versatly/clawvault](https://github.com/Versatly/clawvault), OSS): Referenz fuer agentische Workspace-/Storage-Persistenz (Pattern-Fit, kein automatischer Runtime-Standard).

**Self-Hosted:** ReMe/OpenClaw brauchen ein LLM fuer Summarization – kein Cloud-API noetig, Ollama/vLLM/SGLang reicht. ClawVault ist eher Storage-/Workflow-Pattern als reiner Compactor. Siehe `MEMORY_ARCHITECTURE.md` Sek. 5.5.

### 5.4 Priority-Stack bei Ueberlauf

```
UNANTASTBAR (immer im Kontext):
  1. System Prompt (Agent-Rolle, Output-Format, Guards)
  2. Current Input (der zu analysierende Text/Event)

PRIORISIERT (in dieser Reihenfolge gekuerzt):
  3. KG-Slice (strukturierte Fakten -- hoch-informativ pro Token)
  4. Episodic Context (Erfahrungswissen -- nuetzlich aber nicht kritisch)
  5. Vector/RAG (semantisch aehnliche Dokumente -- nice-to-have)
```

**Platzierung im Prompt (Lost-in-the-Middle-Effekt):** Studien zeigen dass LLMs Fakten am Anfang und Ende des Kontexts besser verarbeiten als in der Mitte (U-Kurven-Effekt). Daher: System Prompt + KG-Slice an den Anfang, Current Input ans Ende. Vector/RAG und Episodic in die Mitte (am ehesten verzichtbar).

---

## 6. Multi-Source Context Merging

Die Zwei-Schichten-KG-Architektur (`MEMORY_ARCHITECTURE.md` Sek. 5.2) erfordert eine definierte Merge-Strategie wenn Frontend-KG und Backend-KG Ergebnisse kombiniert werden.

### 6.1 Merge-Semantiken

| Merge-Typ | Wann | Logik | Beispiel |
|---|---|---|---|
| **Intersection** | Impact-Analyse | Nur Symbole die in BEIDEN KGs matchen | User hat XOM + Backend sagt "Oil betroffen" → XOM ist betroffen |
| **Union** | Explorative Queries | Alles aus beiden KGs, dedupliziert | User fragt "Was passiert in MENA?" → Alle User-Positionen + alle Backend-Events |
| **Enrichment** | Detail-Abfragen | Frontend liefert IDs, Backend reichert an | User klickt auf Position XOM → Backend liefert Kausalketten, Strategem-Matches, Historie |

### 6.2 Merge-Pipeline

```
Frontend-KG Query (lokal, <1ms)
    │
    │ Ergebnis: { affected_symbols: ["XOM","GLD"], alerts: [...] }
    │
    ▼
Merge-Request an Backend API
    │
    │ Payload: { symbols: ["XOM","GLD"], query_type: "impact", event_id: "..." }
    │ (Nur Symbol-IDs, keine Portfolio-Groessen/Preise → Privacy)
    │
    ▼
Backend Context Assembly
    │
    ├── M2a Query: MATCH (e:GeoEvent {id:$eid})-[*1..3]->(s:Symbol)
    │   WHERE s.id IN ["XOM","GLD"]
    │   → Kausalketten mit Confidence
    │
    ├── M3 Query: SELECT * FROM analysis_log
    │   WHERE event_type = $type AND region = $region
    │   ORDER BY timestamp DESC LIMIT 3
    │   → Historische Parallelen
    │
    └── M4 Query (optional): Vector-Search fuer aehnliche Events
        → Top-3 semantisch aehnliche Events
    │
    ▼
Backend Merge + Ranking
    │
    │ Relevance-Scoring (Sek. 4) auf alle Fragmente
    │ Deduplizierung (Symbol-basiert)
    │ Format: JSON mit Kausalketten + Scores + Parallelen
    │
    ▼
Response an Frontend
    │
    ▼
Frontend Merge mit User-KG
    │
    │ Backend-Kausalketten + User-Portfolio-Daten
    │ → "XOM: exposed via Oil→Energy chain (confidence 0.85)"
    │ → "GLD: exposed via Iran→Gold→GLD (confidence 0.92)"
    │ → "Historisch: Aehnliches Event → GLD +2.3% in 24h"
    │
    ▼
UI Rendering (Impact Panel)
```

### 6.3 Conflict Resolution

| Konflikt | Regel | Beispiel |
|---|---|---|
| Frontend-KG sagt Symbol ist Sektor A, Backend-KG sagt Sektor B | **Backend gewinnt** (autoritativere Quelle) | User hat XOM als "commodity" getagged, Backend sagt "energy" → "energy" wird verwendet |
| Backend liefert Kausalkette, aber Confidence < 0.5 | **Kette wird angezeigt aber als "uncertain" markiert** | UI zeigt gestrichelte statt durchgezogene Linie |
| Episodic sagt "aehnliches Event → Markt +2%", aber KG sagt "Event-Kategorie ist risk_off" | **Beide werden angezeigt**, Entscheidung beim User | "Historisch: +2%. Aber: Event-Typ ist typischerweise risk_off" |
| Frontend-KG hat neuere Position-Daten als der letzte Backend-Sync | **Frontend gewinnt** (User-KG ist Source of Truth fuer User-Daten) | User hat gerade XOM verkauft, Backend weiss es noch nicht → XOM nicht als "betroffen" anzeigen |

### 6.4 Partial Availability (Graceful Degradation)

| Szenario | Verfuegbar | Degraded Behavior | User-Hinweis |
|---|---|---|---|
| Alles laeuft | M1, M2a, M2b, M3, M4 | Volle Funktionalitaet | -- |
| Backend offline | Nur M2b (User-KG) | Portfolio-Uebersicht ja, Impact-Analyse nein, keine Kausalketten | "Backend nicht erreichbar. Nur lokale Daten verfuegbar." |
| Redis offline | M2a, M2b, M3, M4 (kein M1) | Langsamere Queries (kein Cache), alles funktional | Invisible (User merkt nur Latenz) |
| Vector Store offline | M1, M2a, M2b, M3 (kein M4) | Keine semantische Suche, nur strukturierte KG-Queries | "Aehnliche Events nicht verfuegbar" |
| User-KG korrupt/leer | M1, M2a, M3, M4 (kein M2b) | Kein personalisierter Kontext, generische Impact-Analyse | "Dein lokaler Graph wird neu aufgebaut..." |

**Review-Ergaenzung (Phase-21 Hardening):**
- Dev/Test: lokale degradierbare Modi erlaubt.
- Staging/Prod: fail-fast fuer kritische Context-Pfade + klare Telemetrie (`fallback_active`, `degraded_context_flags`).

---

## 7. Context Freshness und Staleness

Kontext kann veralten. Ein Event von vor 2 Stunden ist anders relevant als eines von vor 2 Wochen. Das System braucht definierte Freshness-Policies.

**Fast Lane vs. Slow Lane:** Domain C (Live Events) nutzt TTL und Temporal Weight Decay; Domain A+B (Strategeme, BTE) sind statisch mit Confidence Decay. Details: [`MEMORY_ARCHITECTURE.md`](./MEMORY_ARCHITECTURE.md) Sek. 5.2 (Fast Lane vs. Slow Lane), Sek. 9.9 (Confidence Dampening).

### 7.1 TTL-Policies pro Context-Typ

| Context-Typ | Quelle | Max Age | Freshness-Decay | Invalidierung |
|---|---|---|---|---|
| Markt-Preise (Quotes) | Redis (M1) | 30s (intraday), 5min (daily) | Sofort stale nach TTL | TTL-Expiry |
| Indikator-Werte | Redis (M1) | 5min | Linear decay | TTL-Expiry + neuer Preis-Tick |
| Live Events (ACLED/GDELT) | Backend-KG (M2a) | 24h (frisch), 7d (relevant), 30d (archiv) | Exponential decay nach 24h | Neues Event in gleicher Region |
| KG Seed-Daten (Strategeme, BTE) | Backend-KG (M2a) | Unbegrenzt | Immer frisch (statisch) | Manuelles Seed-Update |
| Episodic (Agent-Analysen) | Postgres (M3) | 90d (aktiv), 1y (archiv) | Langsam (monatlich -0.05 Relevance) | -- |
| Vector Embeddings | FalkorDB Vector (M4) | Wie Quelldokument | Wie Quelldokument | Re-Embedding bei Source-Update |
| User-KG (Positionen, Alerts) | KuzuDB WASM (M2b) | Echtzeit (ist Source of Truth) | Immer frisch | User-Aktion (Trade, Alert-Edit) |

### 7.2 Proaktive Invalidierung via SSE

Nicht nur TTL-basiert, sondern event-getrieben:

```
Neues GeoEvent trifft ein (Backend)
    │
    ├── M1: Cache-Invalidierung fuer betroffene Regionen
    │
    ├── M2a: Event wird in KG eingefuegt, neue Edges berechnet
    │
    ├── SSE an alle verbundenen Frontends:
    │   {
    │     type: "kg_update",
    │     event_id: "evt_iran_sanc_20260222",
    │     affected_regions: ["mena"],
    │     affected_symbols: ["CL","GLD","USO"],
    │     invalidates: ["impact_cache_mena"]
    │   }
    │
    └── Frontend empfaengt SSE:
        ├── User-KG: Prueft ob User Positionen in affected_symbols hat
        ├── Wenn ja: Impact-Badge im UI aktualisieren
        └── Wenn User gerade Impact-Panel offen hat: Auto-Refresh
```

### 7.3 User-sichtbare Freshness

Transparenz ueber das Alter des Kontexts:

| UI-Element | Anzeige | Beispiel |
|---|---|---|
| Impact-Panel | Timestamp der letzten Datengrundlage | "Basierend auf Daten von 14:32 (vor 3 Min)" |
| Agent-Analyse | Timestamp des Context-Assembly | "Analyse vom 22.02.2026 14:35. Kontext: 12 Events, 3 historische Parallelen" |
| Stale-Warnung | Wenn Context-Alter > 2x TTL | Gelbes Banner: "Daten aelter als erwartet. Aktualisierung laeuft..." |

---

## 8. Context pro Agent-Rolle

Jede Agent-Rolle (`AGENT_ARCHITECTURE.md` Sek. 2) braucht anderen Kontext. Ein Extractor braucht keine Episodic-Daten, ein Synthesizer braucht keine rohen KG-Definitionen.

### 8.1 Role-Context Matrix

**Teil I: Pipeline-Agenten (AGENT_ARCHITECTURE.md Sek. 2)**

| Agent-Rolle | System Prompt | KG-Slice (M2a) | Episodic (M3) | Vector/RAG (M4) | Current Input | Besonderheit |
|---|---|---|---|---|---|---|
| **Extractor** | Marker-Definitionen, Output-Format | BTE-Marker-Schema (Codes, Punkte, Beschreibung) | -- | -- | Voller Text (Transcript/Event) | Bekommt KEINEN Episodic-Kontext (soll unbefangen extrahieren) |
| **Verifier** | Verifikations-Regeln, Reject-Kriterien | -- | -- | -- | Extractor-Output + Original-Text | Bekommt minimalen Kontext (soll nur pruefen, nicht interpretieren) |
| **Deterministic Guard** | -- (kein LLM) | DRS-Schwellwerte (hardcoded) | -- | -- | Verifizierte Marker (JSON) | **Kein LLM, kein Context Assembly noetig** |
| **Synthesizer** | Erklaer-Richtlinien, Zielgruppe | Strategem-Matches, Event-Kategorie | Letzte Analyse (gleicher Akteur/Region) | Top-3 aehnliche Events | Guard-Output (Scores, Flags) | Bekommt den reichsten Kontext (soll erklaeren und kontextualisieren) |

**Teil II: Orchestration- und erweiterte Agenten (AGENT_ARCHITECTURE.md Sek. 12-13)**

| Agent-Rolle | System Prompt | KG-Slice (M2a) | Episodic (M3) | Vector/RAG (M4) | Current Input | Besonderheit |
|---|---|---|---|---|---|---|
| **Router** | Routing-Regeln, Klassifikations-Schema | -- | -- | -- | User-Anfrage oder UIL-Trigger | **Regelbasiert (80%), SLM nur als Fallback.** Braucht kein Context Assembly -- arbeitet auf Raw Input. |
| **Planner** | Plan-Templates, DAG-Schema, Ressourcen-Limits | -- | Aehnliche Workflows (workflow_log, Top-3) | -- | RoutingDecision + Original-Anfrage + Ressourcen-Status | Episodic nur fuer Workflow-Erfahrung ("Dieses Pattern dauerte 2min, kostete $0.30"). Kein inhaltlicher Kontext (BTE-Marker etc.) -- der Planner braucht nicht zu wissen *was* analysiert wird, nur *wie* |
| **Orchestrator** | -- (primaer Code) | -- | -- | -- | ExecutionPlan (JSON DAG) | **Kein LLM fuer Normalfall.** Leichtgewichtiges LLM (SLM/Haiku) nur bei Fehler-Entscheidungen ("Step X timeout -- Fallback oder Abort?") |
| **Research Agent** | Such-Strategien, Quellen-Priorisierung, Output-Schema | Event-Kontext (Region, Akteure, Kategorie) | Aehnliche Research-Queries (research_log) | Breite semantische Suche (Top-5) | Forschungsfrage + Scope-Constraints | Breitester Kontext nach K. Synthesizer. Schreibt Ergebnisse zurueck in M3 (research_log) |
| **Knowledge Synthesizer** | Cross-Domain-Synthese-Richtlinien, Output-Schema mit Kausalketten | Strategem-Matches, Event-Kategorie, Akteur-Relationen | Letzte Analysen (gleicher Akteur/Region/Typ, Top-3) | Top-3 aehnliche Events | Guard-Output + Research-Ergebnisse + optional Audio-Analyse | **Reichster Kontext im System.** Erhaelt Outputs aller vorgelagerten Agents. Contrarian Context Injection (12%) gilt hier wie beim alten Synthesizer (Sek. 8.3) |
| **Evaluator** | Evaluations-Checkliste, Qualitaets-Schwellwerte | Fakten-Check (Causal Chains im KG verifizieren) | -- | -- | Synthese-Output (voller JSON) | Liest KG nur fuer Fakten-Validierung ("Existiert diese Kausalkette?"). Kein Episodic -- soll unabhaengig von Vergangenheit urteilen |
| **Monitor** | Schwellwerte, Alert-Templates | -- | Aggregierte Metriken (routing_log, workflow_log, evaluation_log) | -- | Letzte Monitoring-Ergebnisse (periodisch) | **Kein klassisches Context Assembly.** Arbeitet auf SQL-Aggregationen ueber M3. LLM nur fuer Alert-Formulierung |

### 8.2 Warum der Extractor keinen Episodic-Kontext bekommt

Wenn der Extractor weiss, dass ein CEO bei den letzten 3 Calls als "evasive" eingestuft wurde, entsteht ein **Confirmation Bias**: er sucht nach Markern die das bestaetigen. Das fuehrt zu False Positives.

Die Trennung ist bewusst:
- **Extractor:** Tabula rasa. Nur Marker-Definitionen + Rohdaten.
- **Synthesizer:** Voller Kontext. Interpretiert die Marker im historischen Zusammenhang.

Der Guard dazwischen ist deterministisch und nicht von Kontext beeinflusst. Dieses Design verhindert, dass Kontext-Bias die Score-Berechnung verfaelscht.

### 8.3 Context Assembly pro Rolle (Pseudocode)

```python
def assemble_context(role: AgentRole, task: AnalysisTask, user: UserContext) -> str:
    parts = []

    parts.append(SYSTEM_PROMPTS[role])

    if role == AgentRole.EXTRACTOR:
        parts.append(get_kg_slice(
            query="BTE-Marker Definitionen",
            max_tokens=600
        ))
        parts.append(task.raw_input)

    elif role == AgentRole.VERIFIER:
        parts.append(task.extractor_output)
        parts.append(task.raw_input[:2000])

    elif role == AgentRole.SYNTHESIZER:
        parts.append(get_kg_slice(
            query=f"Strategeme + Event-Kategorie fuer {task.event_type}",
            max_tokens=1500
        ))
        parts.append(get_episodic(
            actor=task.actor,
            region=task.region,
            max_results=3,
            max_tokens=800
        ))
        parts.append(get_vector_results(
            query=task.summary,
            top_k=3,
            max_tokens=1500
        ))
        parts.append(task.guard_output)

        if random.random() < 0.12:
            contrarian = get_contrarian_context(
                current_interpretation=task.primary_chain,
                episodic_store=M3,
                vector_store=M4,
                kg=M2a,
                max_tokens=400
            )
            parts.append(f"[CONTRARIAN PERSPECTIVE]: {contrarian}")

    # --- Teil II Rollen (AGENT_ARCHITECTURE.md Sek. 12-13) ---

    elif role == AgentRole.ROUTER:
        parts.append(task.raw_input)
        # Kein KG, kein Episodic, kein Vector.
        # Regelbasiert (80%) oder SLM auf Raw Input.

    elif role == AgentRole.PLANNER:
        parts.append(task.routing_decision)          # JSON RoutingDecision
        parts.append(task.raw_input)
        parts.append(json.dumps(task.resource_status))  # GPU-Auslastung, Budget
        parts.append(get_episodic(
            query="aehnliche Workflows",
            table="workflow_log",
            max_results=3,
            max_tokens=500
        ))

    elif role == AgentRole.RESEARCH_AGENT:
        parts.append(get_kg_slice(
            query=f"Kontext fuer {task.research_query}: Region, Akteure, Kategorie",
            max_tokens=1000
        ))
        parts.append(get_episodic(
            query=f"aehnliche Research-Queries: {task.research_query}",
            table="research_log",
            max_results=3,
            max_tokens=600
        ))
        parts.append(get_vector_results(
            query=task.research_query,
            top_k=5,
            max_tokens=2000
        ))
        parts.append(task.research_query)
        parts.append(json.dumps(task.scope_constraints))

    elif role == AgentRole.KNOWLEDGE_SYNTHESIZER:
        parts.append(get_kg_slice(
            query=f"Strategeme + Akteur-Relationen + Event-Kategorie fuer {task.event_type}",
            max_tokens=2000
        ))
        parts.append(get_episodic(
            actor=task.actor,
            region=task.region,
            max_results=3,
            max_tokens=800
        ))
        parts.append(get_vector_results(
            query=task.summary,
            top_k=3,
            max_tokens=1500
        ))
        parts.append(task.guard_output)
        if task.research_output:
            parts.append(json.dumps(task.research_output))
        if task.audio_output:
            parts.append(json.dumps(task.audio_output))

        if random.random() < 0.12:
            contrarian = get_contrarian_context(
                current_interpretation=task.primary_chain,
                episodic_store=M3, vector_store=M4, kg=M2a,
                max_tokens=400
            )
            parts.append(f"[CONTRARIAN PERSPECTIVE]: {contrarian}")

    elif role == AgentRole.EVALUATOR:
        parts.append(task.synthesis_output)           # Voller JSON-Output
        # KG nur fuer Fakten-Check (Kausalketten verifizieren)
        if task.synthesis_output.get("causal_chains"):
            for chain in task.synthesis_output["causal_chains"]:
                kg_check = verify_causal_chain_in_kg(chain, M2a)
                parts.append(json.dumps({"chain": chain, "exists_in_kg": kg_check}))

    elif role == AgentRole.MONITOR:
        # Kein klassisches Context Assembly -- arbeitet auf SQL-Aggregationen.
        # LLM nur fuer Alert-Text-Formulierung:
        parts.append(json.dumps(task.monitoring_metrics))
        parts.append(json.dumps(task.threshold_violations))

    return join_with_budget(parts, model_class=task.model_class)
```

---

## 9. Observability und Debugging

Context ist die haeufigste Fehlerquelle in Agent-Systemen. Deshalb braucht jede Agent-Entscheidung einen nachvollziehbaren Context-Trace.

### 9.1 Context Trace

Fuer jede Agent-Analyse wird der verwendete Kontext mitgeloggt -- nicht nur das Ergebnis (das macht Episodic/M3), sondern der **Input-Kontext**:

```python
@dataclass
class ContextTrace:
    trace_id: str                    # UUID, verlinkt mit Episodic analysis_log
    timestamp: datetime
    agent_role: str                  # "extractor", "verifier", "synthesizer"
    model_class: str                 # "small", "medium", "large"

    budget_total: int                # Total Token-Budget
    budget_used: int                 # Tatsaechlich verwendete Tokens

    kg_fragments: list[KGFragment]   # Welche KG-Nodes/Edges wurden geliefert?
    episodic_fragments: list[EpisodicFragment]
    vector_fragments: list[VectorFragment]

    relevance_scores: dict[str, float]  # Fragment-ID → Relevance Score
    excluded_fragments: list[str]       # Was wurde wegen Cutoff/Budget nicht aufgenommen

    freshness_report: dict[str, float]  # Schicht → Alter in Stunden
    degradation_flags: list[str]        # "NO_KG_CONTEXT", "NO_VECTOR_CONTEXT", etc.
```

### 9.2 Context Quality Metrics

Korrelation zwischen Context-Qualitaet und Agent-Accuracy (aus M3 Episodic ableitbar):

| Metrik | Berechnung | Nutzen |
|---|---|---|
| **Context Coverage** | Anteil der verfuegbaren Schichten die geliefert haben | "Analysen mit 4/4 Schichten haben 23% hoehere Accuracy" |
| **KG-Hit-Rate** | Anteil der Queries bei denen der KG relevante Nodes geliefert hat | Zeigt ob der KG gut genug befuellt ist |
| **Staleness-Impact** | Accuracy-Differenz zwischen Analysen mit frischem vs. veraltetem Kontext | Zeigt ob TTL-Policies richtig eingestellt sind |
| **Budget-Utilization** | `budget_used / budget_total` | Unter 50% = Kontext-Mangel. Ueber 95% = Kompression aktiv, potentiell Qualitaetsverlust |
| **Override-Korrelation** | Anteil der User-Overrides bei Analysen mit spezifischen Degradation-Flags | "Bei NO_KG_CONTEXT werden 40% mehr Candidates rejected" → KG ist kritisch |

### 9.3 Ablation Testing

Systematisches Testen: "Was passiert wenn wir eine Kontext-Schicht weglassen?"

```
ABLATION TESTS (periodisch, auf Batch historischer Analysen):

Test 1: Voller Kontext (Baseline)
  → Accuracy: 0.78, Override-Rate: 15%

Test 2: Ohne Episodic (M3)
  → Accuracy: 0.72 (-0.06), Override-Rate: 20% (+5pp)
  → Episodic ist nuetzlich aber nicht kritisch

Test 3: Ohne KG (M2a)
  → Accuracy: 0.58 (-0.20), Override-Rate: 38% (+23pp)
  → KG ist KRITISCH. Ohne KG sinkt Qualitaet massiv.

Test 4: Ohne Vector (M4)
  → Accuracy: 0.75 (-0.03), Override-Rate: 17% (+2pp)
  → Vector ist nice-to-have, nicht kritisch

KONSEQUENZ: KG-Ausfaelle muessen sofort gemeldet werden.
Vector-Ausfaelle sind tolerierbar.
```

### 9.4 Debug-Interface (Development Only)

Fuer Entwicklung und Tuning: ein Debug-Panel das den Context-Trace visualisiert.

```
┌──────────────────────────────────────────────────────────────┐
│  CONTEXT DEBUG: Analysis #evt_iran_sanc_20260222             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                              │
│  Agent: synthesizer | Model: medium (32K)                    │
│  Budget: 20000 | Used: 14200 (71%) | Compressed: No         │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  TOKEN ALLOCATION                                       │ │
│  │  ████████░░ System (500)                               │ │
│  │  ████████████████░░░░ KG-Slice (1200/1500)             │ │
│  │  ████████░░░░ Episodic (600/800)                       │ │
│  │  ████████████████████░░ Vector (1800/2000)             │ │
│  │  ██████████████████████████████████████ Input (7900)   │ │
│  │  ████████░░ Reserve (2200)                             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  KG Fragments (4):                                           │
│  [0.92] Iran→Oil→GLD (causal chain, confidence 0.89)        │
│  [0.85] Strat_28 match (Sanctions→Auf Dach locken)          │
│  [0.71] MENA→risk_off (region tendency)                      │
│  [0.42] Actor: US Treasury (akteur_typ: regierung)           │
│                                                              │
│  Episodic (2):                                               │
│  [0.88] 2025-11-15: Iran sanctions → GLD +2.3% (24h)        │
│  [0.62] 2025-08-03: MENA military → Oil +1.8% (48h)         │
│                                                              │
│  Vector (3):                                                 │
│  [0.81] evt_iran_sanctions_2025_11 (similarity: 0.89)        │
│  [0.74] evt_russia_sanctions_2024_03 (similarity: 0.76)      │
│  [0.55] evt_china_tariff_2025_06 (similarity: 0.61)          │
│                                                              │
│  Excluded (2 fragments below cutoff 0.3):                    │
│  [0.22] evt_mena_protest_2024_01                             │
│  [0.18] strat_12 (no regime fit)                             │
│                                                              │
│  Degradation: NONE | Freshness: All < 24h                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 10. Offene Fragen

### 10.1 Gewichtungen der Relevance-Dimensionen

Die Gewichtungen in Sek. 4.1 (Freshness 0.30, Proximity 0.25, Confidence 0.25, Regime-Fit 0.20) sind initiale Schaetzungen. Sie muessen empirisch validiert werden sobald Episodic-Daten (M3) vorliegen. Kandidat fuer A/B-Testing.

### 10.2 Merge-Latenz bei komplexen Queries

Die 200ms-Grenze fuer den Merge-Layer ist ambitioniert wenn M2a (KG) + M3 (Episodic) + M4 (Vector) alle angezapft werden. Moeglicherweise muessen M3 und M4 parallel statt sequentiell abgefragt werden. Haengt von der FalkorDB-Performance ab (KG + Vector in einer DB koennte schneller sein als getrennte Systeme).

### 10.3 Context-Trace Storage

Context-Traces (Sek. 9.1) koennen gross werden (14K+ Tokens pro Analyse). Storage-Strategie:
- Volle Traces nur fuer 30 Tage (Debugging)
- Aggregierte Metriken (Coverage, Utilization, Staleness) permanent (Monitoring)
- Oder: Traces nur bei Overrides/Fehlern speichern (kosteneffizient)

### 10.4 Frontend Context-Budget

Aktuell hat nur der LLM-Agent ein Token-Budget. Das Frontend hat keins weil es JSON statt Tokens bekommt. Aber: die Merge-Query kann bei grossen Portfolios (>100 Positionen) + vielen Events teure Responses liefern. Ein JSON-Size-Budget (z.B. max 50KB Response) koennte noetig werden.

### 10.5 Wann Regime-Kontext refreshen?

Der Regime-Detektor (risk_on/risk_off) wird fuer Regime-Fit-Scoring gebraucht (Sek. 4.1). Wie oft wird das Regime aktualisiert? Optionen:
- Bei jedem neuen GeoEvent (reaktiv, moeglicherweise zu haeufig)
- Alle 15 Minuten (periodisch, einfach)
- Bei signifikanten Marktbewegungen (VIX-Spike, etc.)

Abhaengig von der Game-Theory v2 Implementation.

---

## 11. Querverweise

| Dieses Dokument | Referenziertes Dokument | Verbindung |
|---|---|---|
| Sek. 2 (Consumer) | [`MEMORY_ARCHITECTURE.md`](./MEMORY_ARCHITECTURE.md) Sek. 2, 5 | Memory-Schichten (M1-M5) die der Context nutzt |
| Sek. 3 (Retrieval-Policies) | [`MEMORY_ARCHITECTURE.md`](./MEMORY_ARCHITECTURE.md) Sek. 5.2 | Zwei-Schichten-KG: M2a (Backend) + M2b (Frontend) |
| Sek. 5 (Token-Budget) | [`MEMORY_ARCHITECTURE.md`](./MEMORY_ARCHITECTURE.md) Sek. 5.5 | M5 Context Assembly Grundstruktur |
| Sek. 5.3 (Kompression: DyCP, LLMLingua-2) | [`context_engineering_2.0_research.md`](./research/context_engineering_2.0_research.md) Sek. 2.1 | CE 2.0 Research: Dynamische Kompressionsstrategien |
| Sek. 5 (RAG vs. Long Context) | [`context_engineering_2.0_research.md`](./research/context_engineering_2.0_research.md) Sek. 2.2 | CE 2.0 Research: Context Rot, Lost in Middle, 1250x Kosten |
| Sek. 3 + 5 + 6 (Routing/Assembly/Verify) | [`RAG_GRAPHRAG_STRATEGY_2026.md`](./RAG_GRAPHRAG_STRATEGY_2026.md) | Search/Compare/Verify/Global-Modi, Hybrid Retrieval und Rerank als Baseline |
| Sek. 6 (Merging) | [`MEMORY_ARCHITECTURE.md`](./MEMORY_ARCHITECTURE.md) Sek. 5.2, 7 | Sync-Strategie + Architektur-Diagramm |
| Sek. 1.1 (Persistence vor Retrieval) | [`specs/execution/source_persistence_snapshot_delta.md`](./specs/execution/source_persistence_snapshot_delta.md) | Raw snapshot/cache/normalize Grenze vor Context Assembly |
| Sek. 1.1 (Persistence vor Retrieval) | [`specs/execution/vector_ingestion_delta.md`](./specs/execution/vector_ingestion_delta.md) | Embedding-/Provenance-Vertrag fuer Retrieval-faehige Artefakte |
| Sek. 8 (Agent-Rollen, Teil I) | [`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 2 | Vier Pipeline-Agent-Rollen: Extractor, Verifier, Guard, Synthesizer |
| **Sek. 8 (Agent-Rollen, Teil II)** | **[`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 12-13** | **Sieben erweiterte Rollen: Router, Planner, Orchestrator, Research Agent, Knowledge Synthesizer, Evaluator, Monitor -- mit je eigener Context-Policy** |
| Sek. 8.2 (Extractor kein Episodic) | [`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 4 | BTE/DRS Extractor soll unbefangen arbeiten |
| **Sek. 8.3 (Assembly Pseudocode)** | **[`AGENT_RUNTIME_ARCHITECTURE.md`](./AGENT_RUNTIME_ARCHITECTURE.md) + [`AGENT_SECURITY.md`](./AGENT_SECURITY.md)** | **MemoryAccessPolicy, Policy-Tiers und Retrieval Broker steuern, welche Memory-Schichten pro Agent-Rolle erlaubt sind** |
| Sek. 4 (Relevance, Regime-Fit) | [`GAME_THEORY.md`](./GAME_THEORY.md) Sek. 3 | risk_on/risk_off Regime-Detektion |
| Sek. 4.4 (User-Feedback-Loop) | [`GEOMAP_OVERVIEW.md`](./specs/geo/GEOMAP_OVERVIEW.md) Sek. 5.4 | Candidate accept/reject Feedback |
| Sek. 7 (Freshness, SSE) | [`INDICATOR_ARCHITECTURE.md`](./INDICATOR_ARCHITECTURE.md) Sek. 0.3-0.7 | Redis TTL-Policies |
| Sek. 9 (Observability) | [`Advanced-architecture-for-the-future.md`](./Advanced-architecture-for-the-future.md) Sek. 4.7.1 | Concept Drift Detection |

---

## 12. Konsolidierungs-Addendum (Merge-aware Retrieval)

Dieses Addendum verankert die merge-aware Retrieval-Regeln aus der
KG-Merge-Konsolidierung im aktiven Context-Contract.

### 12.1 Merge-aware Query-Typen

Die folgenden Query-Typen sind als First-Class-Intent zu behandeln:

- `event_impact_for_user`
- `claim_evaluation_for_user`
- `historical_similarity_for_claim_or_event`
- `simulation_context_assembly`

### 12.2 Claim Evaluation Context

Bei `claim_evaluation_for_user` muss der Assembler mindestens getrennt liefern:

- `evidence_for`
- `evidence_against`
- `unresolved`
- `stale_evidence`

Und darf keine direkte Faktmutation aus der Evaluation ableiten.

### 12.3 Stale-Evidence- und Contradiction-Scoring

Zusatzmetriken fuer Ranking/Output:

- `stale_evidence_count`
- `contradiction_count`
- `contradiction_severity`
- `evidence_recency_score`

Output mit hoher Staleness oder Widerspruchsdichte wird nicht verworfen, sondern
explizit markiert und im UI als unsicher dargestellt.

### 12.4 Simulation-Context-Assembly

Simulation-Kontext wird aus getrennten Inputs gebaut:

- canonical context (`g:*`, `e:*`)
- user assumptions/claims (`c:*`, `u:*`)
- branch metadata (`s:*`)
- optional episodic parallels (`M3`)

Regel: Simulation bleibt branch-basiert; keine stillen Canonical-Schreibpfade.
