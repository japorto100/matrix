# exec-memory — Memory Architecture Evaluation & Evolution

> Status: Evaluation / laufend
> Erstellt: 2026-04-13
> Abhaengigkeiten: exec-11 (Hindsight Memory Engine), exec-15 (Memory Control UI), [`exec-context.md`](./exec-context.md) (Compaction-Trigger, Prompt-Caching, `merge.py`-Reihenfolge — **operativer Owner**), [`exec-world-model.md`](./exec-world-model.md) (globale Wissensseite), [`exec-personal-kb.md`](./exec-personal-kb.md) (user-kuratierte Knowledgebase)
> Referenzen (Code): `_ref/mempalace/` — Eval & Portierungs-Kandidaten (z. B. Dedup, Query-Sanitizer); `_ref/hindsight/` — produktive Engine; `_ref/supermemory/` — TBD. **Agno-Schema** (`_ref/agno/`) betrifft vor allem [`exec-18-unified-agent-schema.md`](./exec-18-unified-agent-schema.md), nicht dieses Exec.
> Papers (ArXiv kanonisch): **2512.12818** Hindsight; **2603.07670** Memory for Autonomous LLM Agents; PDFs unter `docs/` falls vorhanden
> Hauptprojekt-Docs (Source of Truth fuer bestehende Architektur):
>   - `main_docs/root/MEMORY_ARCHITECTURE.md` — M1-M5, Self-Baking, Confidence Dampening, MemoryAccessPolicy
>   - `main_docs/root/CONTEXT_ENGINEERING.md` — Token Budget, Relevance Scoring, Entropy-Schutz, Multi-Source Merging (mit [`exec-context.md`](./exec-context.md) zur Runtime aktualisieren)
>   - `main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` — Dual Pipeline, Hybrid Retrieval, UQ/Bayesian Confidence-Gates
>   - `main_docs/root/storage_layer.md` — SeaweedFS/Object Storage Entscheidung
>   - `main_docs/root/AGENT_ARCHITECTURE.md` — Agent-Rollen, Registry-Idee, Orchestration-Default
>   - `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md` — verbindliche Policy-Tiers und Memory-Write-Grenzen
>   - `main_docs/root/AGENT_SECURITY.md` — Capability Envelope, Retrieval Broker, Privacy/Deletion
>   - `main_docs/root/AGENT_HARNESS.md` — Constrain/Inform/Verify/Correct, Runtime-Governance

---

## 0. Kontext

Memory ist das kritischste Differenzierungsmerkmal unseres Agent-Systems.
Ohne persistentes Gedaechtnis startet jede Konversation bei Null — kein Lerneffekt,
keine Personalisierung, kein kumulatives Wissen ueber Maerkte/User/Strategien.

Dieses exec sammelt alle Memory-relevanten Evaluierungen, Vergleiche und
Architektur-Entscheidungen an einem Ort.

Nicht Owner fuer:

- globales World Model / Claim-Adjudication
- user-kuratierte Personal Knowledgebase

### 0a. Operative Leitregeln seit `memory_kg.md`

Dieses Exec ist ab jetzt explizit Owner fuer die **persoenliche Memory-Seite**:

- `Personal Raw Evidence`
- `Personal Derived Memory`
- Verbatim-/Retain-/Recall-Pfade dazwischen

Harte Regeln:

- User-Input startet als **Evidenzquelle**, nicht als `truth`
- User-Input startet auch **nicht automatisch** als `belief`
- Agent-Output ist ein **sekundaeres Artefakt**, keine primaere Evidenz
- `derived memory` darf nie alleine als Antwortschaetzchen existieren, sondern nur mit Evidence-/Source-Backlinks
- `Personal Knowledgebase` und `Global World Model` duerfen mit Memory **verlinkt** sein, sind aber keine Default-Write-Ziele dieses Execs

---

## 1. IST-Zustand: Unser Memory Stack

### Schichten (MEMORY_ARCHITECTURE.md Referenz)

| Schicht | Bezeichnung | Implementierung | Status |
|---------|-------------|-----------------|--------|
| M1 | Semantic Memory (KG) | `memory_engine/kg_store.py` — KuzuDB/FalkorDB geplant | Seed Data vorhanden (36 Stratagems, Regimes, Institutions) |
| M2a | Knowledge Graph | Geplant (KuzuDB WASM + Server) | Architektur definiert |
| M2b | User KG (Frontend) | Geplant | Architektur definiert |
| M3 | Episodic Memory | `memory_engine/episodic_store.py` (Legacy SQLite) → **Hindsight** | Hindsight Phase 1 implementiert |
| M4 | Vector Store | `memory_engine/vector_store.py` — ChromaDB/pgvector | Architektur definiert |
| M5 | Working Memory | `agent/working_memory.py` — Redis/Valkey Cache, per-entry keys, 30min TTL | Implementiert |

**Wichtig:** Diese Tabelle zeigt den breiteren historischen Stack.
Der **operative Fokus dieses Execs** liegt aber auf dem persoenlichen Memory-Pfad:

- rohe persoenliche Evidenz
- daraus abgeleitete persoenliche Learnings
- deren Speicherung, Recall, Promotion, Eval und Guardrails

Nicht Fokus dieses Execs:

- globale Welt-Claims als eigener Truth-Layer
- user-kuratierte Personal-Knowledgebase als eigener Artefakt-Layer

### Hindsight Memory Engine (exec-11)

Aktuelle Kern-Implementierung (`agent/memory/engine.py`):
- **4 Operationen:** Retain, Recall, Reflect, Consolidate
- **Slim Mode:** BYOE (Bring Your Own Embeddings/Reranker/DB)
- **PostgreSQL + pgvector** als Backend
- **LLM via LiteLLM** fuer Retain/Reflect
- **91.4% LongMemEval** (laut Hindsight-Docs)

**Hindsight Retain Pipeline** (aus `_ref/hindsight/hindsight-api-slim/hindsight_api/engine/retain/`):
- `orchestrator.py` → `fact_extraction.py` (LLM extrahiert Fakten)
- → `entity_processing.py` + `entity_resolver.py` (spaCy Entity Extraction + Disambiguation)
- → `embedding_processing.py` (Embeddings generieren)
- → `chunk_storage.py` + `fact_storage.py` (Persistierung in PostgreSQL)
- → `link_creation.py` (Entity Links, Semantic Links, Causal Links erstellen)

**Hindsight Search** (aus `engine/search/`):
- 4 parallele Strategien: Semantic, BM25, Graph (Link Expansion), Temporal
- `fusion.py` — Reciprocal Rank Fusion
- `reranking.py` — Cross-Encoder Reranking

**Hindsight Consolidation** (aus `engine/consolidation/`):
- Background Job nach Retain
- Erstellt **Observations** (auto-generiert, bottom-up) aus Fakten
- Unterschied zu **Mental Models** (user-defined, top-down via Reflect)
- Observations haben `proof_count` + `source_memory_ids`

**Hindsight Graph-Struktur** (aus `engine/search/link_expansion_retrieval.py`):
- 3 Link-Typen in `memory_links`:
  1. **Entity Links** — Self-Join ueber `unit_entities`, Score = COUNT(DISTINCT shared entities)
  2. **Semantic Links** — precomputed kNN (top-5 bei Insert, similarity >= 0.7), bidirektional
  3. **Causal Links** — causes/caused_by/enables/prevents, boosted Score (+1.0)
- **Temporal:** Memory-Unit-Level (wann Agent etwas gelernt hat), `event_date` pro Entity
- **Spreading Activation** mit Decay
- **KEIN Triple-Store** — Entity-Link-Graph in Postgres, keine Subject-Predicate-Object Triples

### Zusaetzliche Memory-Module

| Modul | Pfad | Funktion |
|-------|------|----------|
| Cache Coherence | `agent/memory/coherence.py` | Write-Ahead Log, Version Tracking, Conflict Detection fuer Multi-Agent Writes |
| Observation Skills | `agent/memory/observation_skills.py` | Agent-spezifische Beobachtungsmuster |
| Memory Client | `agent/memory_client.py` | Client fuer Memory Service |
| Memory Tool | `agent/tools/memory_tool.py` | Agent-Tool fuer Memory Zugriff |
| Memory Hindsight Tool | `agent/tools/memory_hindsight.py` | Direktes Hindsight-Tool |
| Context Relevance | `context/relevance.py` | Relevanz-Scoring fuer Memory-Recall |
| Token Budget | `context/token_budget.py` | Token-Budgetierung fuer Context Assembly |
| Self-Baking | Geplant (MEMORY_ARCHITECTURE.md 9.8) | High-Entropy → Low-Entropy Verdichtung |
| Confidence Dampening | Geplant (MEMORY_ARCHITECTURE.md 9.8) | Anti-Feedback-Loop Schutz fuer KG-Edges |

### Paper-Attribution

- **Meta-Harness Paper** (`docs/Meta-Harness-2603.28052v1.pdf`) → `agent/harness/` (config, proposer, evaluator, scorer, pareto)
- **MetaClaw** → `agent/skills/evolver.py` (Skill Generation Versioning Sec. 3.2, Deduplication)
- Das sind zwei verschiedene Papers/Module. Nicht verwechseln.

---

## 2. MemPalace — Vergleich mit Hindsight

**Referenz:** `_ref/mempalace/` (Git Submodul)
**Claim:** 96.6% LongMemEval R@5 (raw mode, zero API calls, lokal)

### Warum 96.6%?

MemPalace ist primaer ein **Retrieval-System ueber Verbatim-Daten**, kein klassisches Memory-System:
- Alles wird wortwoertlich gespeichert — kein LLM entscheidet was "wichtig" ist
- ChromaDB Default-Embeddings (all-MiniLM-L6-v2) indizieren alles
- Suche = Vector Similarity auf Roh-Chunks
- Informationsverlust durch LLM-Extraktion (wie bei Hindsight) entfaellt komplett
- Es ist primaer **Episodic/Longterm Konversations-Memory**

### Architektur-Vergleich

| Aspekt | Hindsight | MemPalace |
|--------|-----------|-----------|
| **Philosophie** | LLM-gestuetzte Extraktion (Retain entscheidet was wichtig ist) | Verbatim-Everything (alles speichern, Suche findet es) |
| **Benchmark** | 91.4% LongMemEval | 96.6% LongMemEval (raw mode) |
| **Storage** | PostgreSQL + pgvector | ChromaDB (pluggable backends) |
| **LLM-Bedarf** | Ja — Retain, Reflect, Consolidate brauchen LLM | Nein fuer Core — nur optional fuer Rerank |
| **Operationen** | Retain/Recall/Reflect/Consolidate | Mine → Store → Search (simpler) |
| **Kompression** | LLM-basierte Zusammenfassung via Consolidation | AAAK Dialect (experimentell, 84.2% — Regression vs raw) |
| **Struktur** | Flat Memory Banks | Palace-Metapher (Wings/Rooms/Drawers) |
| **Graph** | Impliziter Entity-Link-Graph (Co-Occurrence + Semantic kNN + Causal) in Postgres | Expliziter Triple-Store (Subject-Predicate-Object) mit `valid_from`/`valid_to` in SQLite |
| **Temporalitaet** | Memory-Unit-Level (wann Agent etwas gelernt hat) | Fakten-Level (wann Fakt in der Welt gueltig war/ist) mit `invalidate()` |
| **Coherence** | Wir haben eigenes `coherence.py` | Nicht vorhanden |
| **Multi-Agent** | Ja — coherence.py fuer parallele Writes | Nein — Single-User-Design |
| **Context Loading** | Recall gibt Ergebnis | 4-Layer Wake-up Stack (L0-L3, ~900 Tokens Startup) |
| **Dedup** | Nicht explizit | `dedup.py` vorhanden |
| **Repair** | Nicht explizit | `repair.py` + Consistency Checks |

### Enhancement vs. Ergaenzung — Modul-Mapping

| Unser Modul | MemPalace Aequivalent | Beziehung | MemPalace Pfad |
|-------------|----------------------|-----------|----------------|
| `agent/memory/engine.py` (Hindsight Retain/Recall) | `miner.py` + `convo_miner.py` + `searcher.py` | **Ergaenzung** — Verbatim Mining parallel zu LLM-Extraction | `mempalace/miner.py`, `mempalace/convo_miner.py`, `mempalace/searcher.py` |
| `memory_engine/kg_store.py` (Seed Triples) | `knowledge_graph.py` (Temporal Triple Store) | **Enhancement** — MemPalace hat temporal `valid_from`/`valid_to` + `invalidate()` | `mempalace/knowledge_graph.py` |
| `context/token_budget.py` | `layers.py` (L0-L3 Wake-up Stack) | **Enhancement** — gestaffelter Context-Aufbau statt flat Budget | `mempalace/layers.py` |
| `context/relevance.py` | `searcher.py` (Hybrid BM25 + Vector) | **Enhancement** — BM25 + Vector kombiniert statt nur Vector | `mempalace/searcher.py` |
| `agent/memory/coherence.py` | Nicht vorhanden | **Wir sind besser** — Multi-Agent Write Coherence | — |
| Hindsight Consolidation | Nicht vorhanden | **Wir sind besser** — aktive Wissens-Verdichtung | — |
| Hindsight Reflect | Nicht vorhanden | **Wir sind besser** — disposition-aware Reasoning | — |
| Nicht vorhanden | `dedup.py` | **Ergaenzung** — Deduplizierung fehlt bei uns | `mempalace/dedup.py` |
| Nicht vorhanden | `repair.py` | **Ergaenzung** — Palace Repair/Consistency Checks | `mempalace/repair.py` |
| Nicht vorhanden | `palace_graph.py` (Cross-Wing Tunnels) | **Ergaenzung** — Room-Traversal + Wing-Verbindungen | `mempalace/palace_graph.py` |
| Nicht vorhanden | `entity_detector.py` + `entity_registry.py` | **Ergaenzung** — Auto-Detect + Disambiguation (lokal, kein spaCy) | `mempalace/entity_detector.py`, `mempalace/entity_registry.py` |
| Nicht vorhanden | `query_sanitizer.py` | **Ergaenzung** — Prompt Contamination Prevention | `mempalace/query_sanitizer.py` |
| Nicht vorhanden | `normalize.py` | **Ergaenzung** — Transcript Format Detection | `mempalace/normalize.py` |
| Nicht vorhanden | `backends/base.py` (Pluggable Backend ABC) | **Ergaenzung** — Backend-Abstraktion fuer Storage Swap | `mempalace/backends/base.py` |

---

## 3. Architektur-Entscheidungen (13.04.2026)

### 3a. Chunking & Embedding Pipeline

**Zwei getrennte Pipelines:**

| Pipeline | Zweck | Chunking | Embedding |
|----------|-------|----------|-----------|
| **Document Ingestion** (`ingestion/`) | PDFs, Dokumente, Webseiten | Section-aware (`token_chunker.py`), RAPTOR Tree (aus paperwatcher portieren), Late Chunking (aus paperwatcher portieren) | pgvector |
| **Konversations-Memory** (Hindsight) | Agent-Konversationen, Fakten | Hindsight's eigene `chunk_storage.py` + `fact_extraction.py` | pgvector (via Hindsight) |

**Hindsight ist KEIN Document-Ingestion-System** — designed fuer Konversations-Fakten,
nicht fuer 50-seitige PDFs. Eigene Ingestion-Pipeline bleibt noetig.

**Noch aus Paperwatcher zu portieren:**
- `core/raptor_tree.py` — RAPTOR hierarchisches Embedding (bottom-up: Chunks → Cluster → Summaries)
- `ragbits_custom/addition/late_chunking/` — Late Chunking (Window Selector + Windowing)
- `core/hybrid_retriever.py` — Multi-hop RAG+KG+DocGraph Retriever
- `core/self_rag.py` — Self-RAG Post-Retrieval Verification
- `core/context_bubble.py` — Token-budgeted, diversity-gated Context Assembly
- `core/colpali_indexer.py` — Visual Indexing fuer Bilder/Charts (ColQwen2.5/mmE5)

### 3a-2. MemPalace Utilities vs. Paperwatcher/Ingestion — Vergleich fuer Document Pipeline

Einige MemPalace-Module koennen fuer die Document/Ingestion Pipeline nuetzlicher sein
als die bestehenden Paperwatcher-Aequivalente. Vergleich:

| Funktion | Unsere Ingestion | Paperwatcher | MemPalace | Bewertung |
|----------|-----------------|--------------|-----------|-----------|
| **Dedup** | `ingestion/tracking/dedup.py` — sha256 Hash (exakt, Document + Chunk Level) | DOI + Title-based Dedup in `core/service.py` | `mempalace/dedup.py` — Cosine Similarity Dedup (near-duplicate, threshold-basiert, 0.15-0.35) | **MemPalace besser** fuer semantische Near-Duplicates. Unsere sha256-Dedup faengt nur identische Texte, keine Paraphrasen. Beides kombinieren: sha256 fuer exakte + Cosine fuer near-duplicate. |
| **Repair / Consistency** | Nicht vorhanden | Nicht vorhanden | `mempalace/repair.py` — Scan corrupt entries, Prune, Rebuild HNSW Index | **MemPalace einzigartig** — Repair-Pattern auf pgvector uebertragen (Index Health Check, Vacuum, Re-Embed korrupte Eintraege) |
| **Input Normalization** | `ingestion/normalizers/` (Ordner existiert) | Format Detection in `core/doc_extractor/` | `mempalace/normalize.py` — Auto-Detection: Claude JSON, ChatGPT JSON, Claude Code JSONL, Codex JSONL, Slack JSON, Plain Text | **MemPalace besser** fuer Konversations-Formate. Paperwatcher besser fuer Paper/PDF-Formate. Komplementaer. |
| **Query Sanitization** | Nicht vorhanden | Nicht vorhanden | `mempalace/query_sanitizer.py` — Prompt Contamination Prevention (System Prompt aus Queries strippen, 89.8% → 1.0% Retrieval Failure ohne) | **MemPalace einzigartig** — kritisch fuer Agent-Retrieval. Agents prependen oft System Prompts an Search Queries. |
| **Entity Detection** | Nicht in Ingestion | ReLiK + GLiREL + GLiNER in `kg-module/` | `mempalace/entity_detector.py` + `entity_registry.py` — lokal, kein spaCy/ReLiK, Disambiguation by DOB/ID/Context | **Paperwatcher maechtiger** (ML-basiert), **MemPalace leichtgewichtiger** (regelbasiert, zero-dependency). Fuer Konversationen MemPalace, fuer Papers Paperwatcher. |
| **Spellcheck** | Nicht vorhanden | Nicht vorhanden | `mempalace/spellcheck.py` — Auto-correct User Messages | **MemPalace einzigartig** — nuetzlich fuer Chat-Input-Qualitaet |

**Empfehlung:** Folgende MemPalace-Module fuer die Document/Ingestion Pipeline evaluieren:
1. **Cosine Dedup** — als Ergaenzung zu sha256-Dedup (near-duplicate Detection)
2. **Repair Pattern** — auf pgvector/Postgres uebertragen
3. **Query Sanitizer** — direkt in Retrieval-Pipeline einbauen (Agent-kritisch)
4. **Normalize** — fuer Konversations-Import (Claude/ChatGPT/Slack Exports)

### 3b. Storage-Entscheidung: PostgreSQL primaer, SeaweedFS als Cold

**Kein ChromaDB** — pgvector kann alles was ChromaDB kann, wir haben Postgres bereits.
SOTA 2026: Klare Tendenz zu Postgres-Konsolidierung (pgvector 0.8+ HNSW + Quantization).

**Option A (Primaer): Alles in PostgreSQL**

```
memory_units (Hindsight, existiert bereits)
├── fact_text        → extrahierter Fakt
├── embedding        → pgvector
├── entity_links     → Graph
└── metadata         → JSONB

verbatim_store (NEU)
├── raw_content      → TEXT (voller Originaltext)
├── embedding        → pgvector
├── source_meta      → JSONB (wing, room, session_id, timestamps)
└── memory_unit_id   → FK zu Hindsight (optional, Link Extrakt ↔ Original)
```

**Option B (Fallback): PostgreSQL + SeaweedFS fuer Tiered Storage**

### 3c. Tiered Storage — Hot/Warm/Cold

| Tier | Wo | Was | Zugriff |
|------|-----|-----|---------|
| **Hot** | PostgreSQL | Aktuelle Fakten (Hindsight), Working Memory (Valkey), letzte Verbatim-Chunks | ms, jeder Recall |
| **Warm** | PostgreSQL (markiert/partitioniert) | Aeltere Verbatim-Eintraege, historische Embeddings | ms, seltener abgefragt |
| **Cold** | SeaweedFS | Archivierte Konversationen, alte Session-Transkripte, Binary Blobs (PDFs, Audio) | 100ms+, nur Deep Search |

**Cold-Migration Bedingungen:**

1. **Alter:** Verbatim-Chunks > 90 Tage ohne Recall → Cold
2. **Recall-Frequenz:** 0 Recalls in letzten 30 Tagen → Cold-Kandidat
3. **Post-Consolidation:** Roh-Eintraege nachdem Hindsight Observation erstellt hat → Cold
4. **Session-Abschluss:** Transkripte nach 30 Tagen → Cold
5. **Groesse:** Eintraege > 50KB → direkt Cold

**Entscheidender Trick:** Embedding bleibt **IMMER** in PostgreSQL (pgvector).
Nur der TEXT wandert nach SeaweedFS. Suche findet den Eintrag weiterhin —
erst beim Anzeigen des vollen Textes wird SeaweedFS kontaktiert.
**Suchbarkeit bleibt Hot, nur der Payload wird Cold.**

Passt zu Self-Baking (MEMORY_ARCHITECTURE.md 9.8): High-Entropy Roh-Eintraege →
Low-Entropy Observations (Hot). Roh-Eintraege → Cold. Nichts geht verloren.

### 3d. KG-Strategie: Zwei komplementaere Graphen

| Graph | Typ | Wo | Zweck |
|-------|-----|-----|-------|
| **Hindsight Entity-Links** | Implizit (Co-Occurrence + Semantic kNN + Causal) | PostgreSQL `entity_links` | Implizite Beziehungen zwischen Memories |
| **Temporal Triple-Store** (MemPalace-Pattern) | Explizit (Subject-Predicate-Object + `valid_from`/`valid_to`) | PostgreSQL oder `memory_engine/kg_store.py` | Explizite zeitliche Fakten mit Invalidation |

Hindsight weiss *wann der Agent etwas gelernt hat*.
Temporal Triple-Store weiss *wann ein Fakt in der realen Welt gueltig war/ist*.

### 3e. Verbatim Capture — Wie MemPalace es macht (Referenz)

MemPalace speichert den **gesamten Gespraechsverlauf**, nicht nur Ausschnitte. Zwei Mechanismen:

1. **Batch Mining** (`mempalace mine <dir>`): Scannt Transcript-Files (JSONL, JSON, TXT),
   normalisiert Formate, chunked in Exchange-Pairs (~800 chars), indiziert verbatim in ChromaDB.
   Dedup via `file_already_mined()`.

2. **Hook-basierte Auto-Save** (waehrend der Session):
   - `mempal_save_hook.sh` (Stop Hook): Alle 15 User-Messages → blockiert Agent, fordert Save auf
   - `mempal_precompact_hook.sh` (PreCompact Hook): Feuert **direkt vor Compaction** — Emergency Save

**Kerninsight:** Compaction passiert im LLM-Context. Die Transcript-Datei auf der Platte bleibt
vollstaendig. MemPalace liest die volle Datei, nicht den compacted Context.

**Fuer uns uebertragbar:**
- Agent-Sessions als JSONL speichern (Audit Store tut das bereits teilweise)
- Batch-Mining in Verbatim Store (PostgreSQL `verbatim_store`)
- PreCompact-Hook als Sicherheitsnetz: Verbatim Retain triggern bevor Context schrumpft

### 3f. Compaction, Token-Caching & Prompt-Reihenfolge

**Operativer Owner:** [`exec-context.md`](./exec-context.md) — dort: modell-relative Schwellen (80/85/95%), **LiteLLM** / Provider **Prompt Caching**, **KV-Cache** (vLLM/SGLang/LMCache), Ziel-Reihenfolge fuer `context/merge.py`, SOTA-Referenzen (Stand 15.04.2026), Observability (`cached_tokens`), und Abgrenzung zu Memory-**Write**-Pfaden.

**Memory-Perspektive (kurz):** Compaction **verdichtet** den sichtbaren Chat im LLM-Fenster; ohne parallelen **Verbatim-/Hindsight-Write** gehen Details verloren (Paper **2603.07670** zu Drift / langer Kontext). Deshalb bleibt die Kette aus **§3e PreCompact / §3b Verbatim-Store** + Retain hier verbindlich; die **Trigger-Logik und Merge-Order** pflegen wir in **exec-context**.

**Kurzüberblick Schwellen:** bei ~80% Kontextnutzung Pre-Save (Verbatim/Session), bei ~85% Rolling Summary, bei ~95% Notfall-Modus — Details und Implementierungs-Checkliste → **exec-context** §6.

### 3g. Idealer Hybrid fuer **Personal Memory**

- **Write:** `Personal Raw Evidence` verbatim in `verbatim_store` (Postgres) + Extrakte/Observations in Hindsight (`Personal Derived Memory`) parallel
- **Pre-Compaction:** Bei 80% Context-Auslastung → Verbatim Retain triggern bevor Compaction Details loescht
- **Read:** Hindsight 4-Strategie-Fusion als Primaer fuer `derived`/semantische Learnings, Verbatim-Store als Fallback fuer exakten Belegtext
- **Memory-side Graph:** Hindsight Entity-Links / lokale Memory-Relationen sind ok; **globaler KG** bleibt eigener Owner in [`exec-world-model.md`](./exec-world-model.md)
- **Context Loading:** L0-L3 Layer-Konzept (MemPalace) fuer Token-Budget-bewusstes Priming — operative Ausgestaltung mit [`exec-context.md`](./exec-context.md)
- **Token Caching + Prompt-Reihenfolge + Compaction-Trigger:** [`exec-context.md`](./exec-context.md)
- **Compaction:** Verbatim vor Compaction gesichert; Schwellen modellrelativ — **exec-context**
- **Tiered Storage:** Hot (Postgres) → Warm (Postgres) → Cold (SeaweedFS)
- **Coherence:** Unser bestehendes `coherence.py` fuer Multi-Agent Writes
- **Nicht Default:** gespeicherte PDFs/Webclips/YouTube-Transcripts in denselben Memory-Write-Pfad pressen; das ist primaer [`exec-personal-kb.md`](./exec-personal-kb.md)

### 3h. Memory-Grenzen und Default-Routing

| Artefakt | Default-Ziel | Owner dieses Execs? | Regel |
|---|---|---|---|
| Chatturn | `Personal Raw Evidence` | **Ja** | primaere Session-Evidenz |
| Tool-Output | `Personal Raw Evidence` | **Ja** | primaere Evidenz, spaeter evtl. `derived` |
| Session-Scratch-Note | `Personal Raw Evidence` | **Ja** | interaktionsnah, nicht kurationsnah |
| Observation / Preference / Mental Model | `Personal Derived Memory` | **Ja** | nur mit Evidence-Backlinks / Status |
| Gespeicherter Artikel / Webclip | `Personal Knowledgebase` | **Nein** | nur optionaler Bridge-Read fuer Memory |
| Private PDF | `Personal Knowledgebase` | **Nein** | Heavy Ingestion / KB first |
| YouTube / Podcast mit Transcript | `Personal Knowledgebase` | **Nein** | KB first, evtl. spaeter `derived` |
| Globale News / Filing / Marktbericht | `Global World Evidence` | **Nein** | gehoert nicht in Personal Memory |
| Welt-/Markt-Claim | `Global World KG` | **Nein** | eigener Truth-/Claim-Layer |

Praktische Folge:

- `memory_fusion` darf persoenliche rohe und abgeleitete Memory-Wege verbessern
- `memory_fusion` ist **nicht** die heimliche Sammelhalde fuer KB + World Model
- Bridges sind ok, stille Verschmelzung nicht

### 3i. Frontend-Kopplung: `control_ui` zuerst, Agent-Chat danach

Frontend-seitig haengt dieses Exec am staerksten an `control_ui`, nicht am
Agent-Chat:

- **kompakte Memory-Sicht:** `control-ui/src/features/memory/components/MemoryHealthCards.tsx`, `control-ui/src/features/memory/components/MemoryRuntimeInspector.tsx`
- **primaerer Runtime-/Prompt-Inspector:** `control-ui/src/features/control/components/ContextTab.tsx`
- **heutige BFFs:** `control-ui/src/app/api/memory/[...path]/route.ts`, `control-ui/src/app/api/control/[...path]/route.ts`

Aktueller Ist-Stand:

- `MemoryHealthCards` bleibt der kompakte, kompatible Memory-Health-Einstieg und
  zeigt ueber `MemoryRuntimeInspector` bereits `Latest Runtime`,
  `sourceLayerCounts`, `degradationFlags` und `contextBlocks`
- `ContextTab` ist jetzt die getrennte, kanonische Inspector-Sicht fuer
  Runtime-/Prompt-/World-Kontext und loest die Vermischung von Memory-Health und
  Context-Diagnostik auf
- vollstaendige Personal-KB-/World-Browser-Surfaces bleiben trotzdem noch
  Ausbauarbeit

Konsequenz:

- `exec-memory` muss den **Datenvertrag** fuer `source_layer`, `source_type`,
  `artifact_type`, `provenance_ref`, `grounding_status`, `status`, `freshness`
  liefern
- [`exec-15-memory-control-ui.md`](./exec-15-memory-control-ui.md) ist der
  primaere Frontend-Owner fuer die **detaillierte** Surfacing-/Inspector-Sicht
- Agent-Chat ist die **sekundaere**, kompaktere Laufzeit-Sicht auf denselben
  Vertrag

---

## 4. Weitere Memory-Systeme zum Vergleich

### Bereits in _ref/

| Projekt | Pfad | Beschreibung |
|---------|------|-------------|
| Hindsight | `_ref/hindsight/` | 4-Networks Memory Engine (aktuell integriert) |
| MemPalace | `_ref/mempalace/` | Verbatim Palace-Memory (96.6% LongMemEval) |
| supermemory | `_ref/supermemory/` | TBD — noch nicht evaluiert |

### Zu evaluieren (noch nicht in _ref)

| Projekt | Typ | Warum relevant |
|---------|-----|---------------|
| **Mem0** | Managed Memory Service | Self-improving memory, User/Agent/Session Scopes, Production-ready |
| **Letta (ex-MemGPT)** | OS fuer Stateful Agents | Memory-Tiers (Core/Archival/Recall), Self-Editing Memory — relevant fuer Hierarchical Virtual Context Luecke |

### Nicht mehr evaluieren (redundant mit Hindsight + FalkorDB)

| Projekt | Grund |
|---------|-------|
| ~~Zep / Graphiti~~ | Zu viel Ueberlappung mit Hindsight im Bereich temporal graph memory |
| ~~Cognee~~ | Zu viel Ueberlappung im Bereich graph+vector memory/knowledge engine |
| ~~LangMem~~ | Hindsight deckt Semantic Memory Extraction bereits ab |

---

## 5. Evaluierungsstrategie: Isoliert → Vergleich → Hybrid

**Entscheidung:** Zuerst isoliert evaluieren, DANN gezielt hybridisieren.
Nicht direkt hybridisieren — wir wissen nicht ob der Aufwand sich auf unseren Daten lohnt.

### 5a. Query-Typen fuer Memory-Evals (Pflicht, sonst Benchmark-Salat)

Memory-Evals in diesem Exec muessen mindestens diese Klassen trennen:

1. **Verbatim / Evidence Recall**
   - "Was genau wurde gesagt / geschrieben / beobachtet?"
2. **Derived / Preference / Observation Recall**
   - "Was weiss das System ueber wiederkehrende Praeferenzen / Learnings?"
3. **Cross-Session Coherence**
   - "Ist persoenliches Wissen ueber Sessions konsistent?"
4. **Forgetting / Conflict Handling**
   - "Wie geht das System mit veralteten oder widerspruechlichen persoenlichen Infos um?"

Nicht Teil des Kern-A/B in `exec-memory`, ausser explizit als Bridge-Test:

- globale World-Model-Fragen
- Personal-KB-Library-/Notebook-Fragen
- Claim-Adjudication fuer globale Wahrheiten

### Phase 1: Isolierter MemPalace Test (1-2 Tage)

`python-backend/experiments/mempalace/` Subfolder erstellen.
- 50-100 echte Agent-Sessions aus Audit-Daten einspeisen
- MemPalace gegen Trading-spezifische Fragen testen
- Messen: Recall-Qualitaet, Latenz, Storage-Groesse
- **Kritische Frage:** Gilt der 96.6%-Vorteil auf unseren Daten?
  LongMemEval ist konversations-lastig, unsere Daten haben Trading-Kontext,
  Zahlen, Zeitreihen — anderer Charakter.

### Phase 2: Hindsight Gegentest (1 Tag)

Gleiche Fragen, gleiche Sessions, aber ueber Hindsight Recall.
- Direkter A/B-Vergleich: Welche Frage-Typen beantwortet wer besser?
- Wo verliert Hindsight durch LLM-Extraktion? (z.B. "Was genau hat der Agent
  am 15. Maerz zu BRENT gesagt?" — Verbatim gewinnt hier wahrscheinlich)
- Wo gewinnt Hindsight? (z.B. "Welche Strategie empfiehlt der Agent fuer
  MENA-Events?" — Reflect/Consolidate verdichtet besser als Raw Search)

### Phase 3: Gezielt hybridisieren (nach Phase 1+2)

Erst wenn wir wissen WO MemPalace besser ist (welche Frage-Typen, welche Daten),
bauen wir den Hybrid:
- Verbatim-Store (`verbatim_store` Tabelle) als Fallback fuer Faelle wo
  Hindsight zu wenig zurueckgibt (niedriger Recall-Score)
- L0-L3 Layer-Konzept fuer Context Loading
- Temporal Triple-Store Pattern in `memory_engine/kg_store.py`
- Query Sanitizer in Retrieval-Pipeline
- Cosine Dedup als Ergaenzung zu sha256

**Zeitaufwand:** 3-4 Tage fuer Phase 1+2, bevor Architektur-Entscheidungen zementiert werden.

---

## 6. ChatGPT-Analyse: Hindsight vs Memory-Taxonomie (aus memory_chatgpt.txt)

Quelle: ChatGPT-Gespräch das Hindsight gegen das Paper "Memory for Autonomous LLM Agents"
(arxiv 2603.07670v1) einordnet. Archiviert: `docs/archive/memory_chatgpt.txt`

### Hindsight Einordnung in die 5 Memory-Familien

| Familie (aus Paper) | Hindsight-Abdeckung | Bewertung |
|---------------------|---------------------|-----------|
| Retrieval-augmented stores | **90-95%** | Haupttreffer: 4 Retrieval-Kanaele (semantic, BM25, graph, temporal), Fusion, Reranking |
| Reflective self-improvement | **75-85%** | Reflect-Operation mit Opinion Network, structured reflection |
| Context-resident compression | **25-35%** | Token-Budget fuer Recall-Output, aber kein promptinternes Compression-System |
| Hierarchical virtual context | **30-40%** | Mehrere Netzwerke + Budget, aber kein MemGPT-artiges Virtual-Memory-Paging |
| Policy-learned management | **5-10%** | Pipeline architektonisch festgelegt, kein RL-gelerntes Memory-Management |

### Hindsight in der 3D-Taxonomie

| Dimension | Einordnung |
|-----------|------------|
| **Temporal scope** | Stark Langzeit/Multi-Session, zeitbewusste Struktur |
| **Representational substrate** | Stark hybrid (Text + Embedding + Graph + Temporal Metadata) |
| **Control policy** | Ueberwiegend handdesignt/pipeline-basiert, nicht learned |

### Hindsight KG-Kritik

Hindsight kritisiert klassische KGs nicht weil Graphen schlecht waeren, sondern weil:
1. Klassische KGs **Evidenz, Erfahrung und Meinung vermischen** (keine epistemische Trennung)
2. Zu **statisch fuer Langzeit-Agent-Memory** (keine zeitliche Entwicklung)
3. Zu wenig auf **agent-optimiertes Retrieval** ausgelegt (nur eine Suchmethode)
4. Kein **"learning over time"** (Wissensspeicher, nicht lernendes Gedaechtnis)

### Architektur-Empfehlung (aus ChatGPT-Analyse)

**Klare Trennung zweier Rollen:**
- **Hindsight** = Agentengedaechtnis (persoenlich, temporal, reflektierend)
- **FalkorDB** = Globaler Unternehmensgraph (Beziehungen, Traversal, Enterprise-Wissen)

**Nicht zusaetzlich noetig:**
- **Graphiti** — zu viel Ueberlappung mit Hindsight im Bereich temporal graph memory
- **Cognee** — zu viel Ueberlappung im Bereich graph+vector memory/knowledge engine

**Faustregel:**
> Hindsight fuer Memory. FalkorDB fuer globalen Graph. Graphiti/Cognee nur statt Hindsight oder fuer sehr spezielle separate Pipelines.

### Luecken die wir schliessen muessen

Basierend auf der Taxonomie-Analyse fehlt Hindsight:
1. **Context-resident compression** (25-35%) → MemPalace L0-L3 Layer-Konzept adressiert das
2. **Hierarchical virtual context** (30-40%) → Tiered Storage (Hot/Warm/Cold) adressiert das teilweise
3. **Policy-learned management** (5-10%) → Langfristig: EBM-basiertes Scoring (exec-ebm) als Schritt Richtung learned policy
4. **Verbatim Storage** → MemPalace-Pattern adressiert den Informationsverlust bei LLM-Extraktion

---

## 7. Paper-Abgleich: "Memory for Autonomous LLM Agents" (2603.07670v1)

Systematischer Abgleich aller relevanten Abschnitte gegen unseren IST-Zustand.
User-Notizen archiviert: `docs/archive/memory_notes.txt`

### Kapitel 3: Taxonomie — Control Policy

| Stufe | Paper | Unser Status |
|-------|-------|-------------|
| Heuristic Control | Top-k, summarize every n turns, expire after d days | Teilweise — Token Budget, aber kein automatischer Expire |
| Prompted Self-Control | Memory Ops als Tool-Calls (MemGPT-Pattern) | **Ja** — `agent/tools/memory_tool.py`, `memory_hindsight.py` |
| Learned Control | RL-optimierte Memory Policy (AgeMem) | **Nein** — Pipeline architektonisch festgelegt. Langfrist: exec-skills Phase 4 |

### Kapitel 4: Core Mechanisms — Luecken

| Abschnitt | Thema | Haben wir? | Massnahme |
|-----------|-------|-----------|-----------|
| **4.1** Summarization Drift | Rolling Summaries verlieren seltene-aber-kritische Details | **Adressiert** durch Verbatim Store (Sek. 3b) | L0-L3 Layered Loading verhindert Attentional Dilution |
| **4.1** Quadratic Cost / Token Caching | Laengere Contexts = quadratisch teurer | **Teilweise** — `CONTEXT_ENGINEERING.md` Sek. 5 definiert Token-Budget-Management | KV-Cache Management evaluieren. Anthropic Prompt Caching nutzen. `context/token_budget.py` existiert bereits. |
| **4.2** Multi-Granularity Indexing | Fein (einzelne Saetze) vs. Grob (ganze Sessions) | **Nur eine Granularitaet** | RAPTOR (hierarchisch) aus Paperwatcher portieren |
| **4.2** Query Reformulation | Agent-Input ist oft schlechte Retrieval-Query | **Teilweise** — MemPalace Query Sanitizer + `CONTEXT_ENGINEERING.md` Sek. 4 (Relevance Scoring) | LLM-Query-Reformulation + Self-RAG Gate (retrieval ja/nein) fehlt. `RAG_GRAPHRAG_STRATEGY_2026.md` Sek. 3 (Contextual Retrieval+Rerank) als Referenz. |
| **4.3** Self-Reinforcing Error | Falsche Reflexionen werden nie korrigiert → Confirmation Bias | **Teilweise** — Confidence Dampening geplant (`CONTEXT_ENGINEERING.md` Sek. 4.4.1, `ENTROPY_NOVELTY.md` Sek. 4.4) | Reflection Grounding (Reflexion muss Episoden zitieren), Adversarial Probing, Periodic Expiration. Diversity Floor aus CONTEXT_ENGINEERING.md ist ein bestehender Anti-Collapse-Mechanismus. |
| **4.4** Silent Orchestration Failures | Memory-Paging-Fehler erzeugen kein Error-Signal | **Nicht adressiert** | Memory Operation Logs: jeder Read/Write/Delete mit Timestamp + Context. Memory Diffs zwischen Turns. |
| **4.4** Memory Regression Tests | Aenderungen am Memory-System (neues Embedding-Model) haben unvorhersagbare Effekte | **Nicht vorhanden** | Ground-Truth Annotations: "welche Memories sollen fuer welche Queries zurueckkommen" |

### Kapitel 5: Evaluation — Luecken

| Abschnitt | Thema | Haben wir? | Massnahme |
|-----------|-------|-----------|-----------|
| **5.2** MemoryArena Gap | Modelle mit perfektem Recall fallen bei agentischen Tasks auf 40-60% | **Nicht getestet** | Phase 1+2 Eval muss BEIDES testen: passive Recall UND aktive Decision-Making |
| **5.4** 4-Layer Metric Stack | Task Effectiveness + Memory Quality + Efficiency + Governance | **Nur Layer 1** (Task Success) | Layer 2 (Retrieval Precision/Recall), Layer 3 (Latenz, Token-Cost), Layer 4 (Privacy, Deletion) einbauen |
| **5.5** Evaluation must include Cost | Viele Benchmarks ignorieren operative Kosten | **Nicht adressiert** | Latenz + Token-Verbrauch pro Memory-Operation messen und reporten |
| **5.5** Nobody evaluates Forgetting | Selektives Vergessen wird fast nie getestet | **Nicht adressiert** | In Phase 1+2 Eval: Forgetting-Szenario einbauen (veraltete Fakten, korrigierte Infos) |
| **5.5** Cross-Session Coherence | Konsistenz ueber Sessions hinweg ist underexplored | **Teilweise** — coherence.py fuer Writes | Cross-Session Consistency Test: gleiche Frage in Session 1 vs. Session 10 |

### Kapitel 6: Application-Specific — Luecken

| Abschnitt | Thema | Haben wir? | Massnahme |
|-----------|-------|-----------|-----------|
| **6.1** Ebbinghaus Forgetting Curves | Haeufig abgerufene Memories verstaerkt, vernachlaessigte verblassen | **Nein** | Decay-Score als Alternative zu starrer 90-Tage Cold-Migration. `recall_count` + `last_recalled_at` auf Memory Units. Ebbinghaus-Formel: Retention = e^(-t/S) wobei S = Strength (steigt bei jedem Recall) |
| **6.3** Compositional Skill Reuse | Skills kreativ verketten fuer neue Probleme | **Teilweise** — Refiner kann kombinieren | → **exec-skills**: Skill Composition Framework langfristig |
| **6.4** Uncertainty-aware Memory | Confidence-Level pro Fakt, Bayesian Update bei neuen Beweisen | **Teilweise geplant** — `RAG_GRAPHRAG_STRATEGY_2026.md` Sek. 5 (UQ/Bayesian Confidence-Gates), `CONTEXT_ENGINEERING.md` Sek. 4.4.1 (Override-Cap, Decay) | Bayesian RAG Pattern: Score = μ - λ·σ. Verbindung zu exec-ebm (Energy als Uncertainty Proxy). UQ-Leitentscheidung existiert bereits in RAG-Strategie, muss auf Memory-Ebene uebertragen werden. |
| **6.5** Multi-Agent Access Control | Welcher Agent sieht welche Memories (ACL) | **Geplant** — `MEMORY_ARCHITECTURE.md` + `AGENT_RUNTIME_ARCHITECTURE.md` (Policy-Tiers) + `AGENT_SECURITY.md` (Retrieval Broker als Pflichtpfad) | Role-based Memory Access: PM sieht Summaries, Analyst sieht Details. Retrieval Broker aus AGENT_SECURITY.md ist der Enforcement-Punkt. Nicht implementiert. |
| **6.6** Schema Drift | API-Versionen in Memory versionieren | **Nicht adressiert** | → **exec-skills**: Tool-Use Memories brauchen API-Version-Tag. Invalide Records bei API-Aenderung markieren. |
| **6.8** Modular vs. Monolith | Kein einzelnes Memory-System fuer alle Domains | **Ja** — unser Hybrid-Ansatz (Hindsight + Verbatim + KG) ist modular | Bestaetigt unsere Architektur |

### Kapitel 7: Engineering — Luecken

| Abschnitt | Thema | Haben wir? | Massnahme |
|-----------|-------|-----------|-----------|
| **7.1** Write Path Quality | Filtering, Canonicalization, Dedup, Priority Scoring, Metadata Tagging | **Teilweise** — Dedup (sha256 + geplant Cosine) | Canonicalization fehlt (Datums-/Namens-Normalisierung). Priority Scoring fehlt (wichtigere Memories bevorzugt). Systematisches Metadata Tagging fehlt. |
| **7.3** Source Attribution | User Statement >> Agent Inference (hierarchische Vertrauenswuerdigkeit) | **Nicht adressiert** | `source_type` Feld auf Memory Units: 'user_statement', 'agent_inference', 'system_observation'. Recall bevorzugt User Statements. |
| **7.3** Contradiction Detection | Konflikte zwischen Memories erkennen und aufloesen | **Geplant** — Confidence Dampening | Explizite Contradiction Detection bei Retain: neuer Fakt vs. bestehende Fakten pruefen. |
| **7.4** Latency + Cost Optimization | Sub-second Responses, Async Writes, Progressive Retrieval, Dynamic Routing | **Nicht adressiert** | Async Writes: Memory speichern NACH Response. Progressive Retrieval: Antwort generieren waehrend Retrieval laeuft. Dynamic Routing: Skip Retrieval bei einfachen Fragen. **Kritisch fuer Production.** |
| **7.5** Privacy + Deletion | PII Redaction, Retention Policies, Auditable Deletion ueber alle Tiers | **Teilweise** — `AGENT_SECURITY.md` Sek. 5 (Agentic Storage Write-Grenzen) + Security Module | Memory-spezifische PII Detection. Deletion ueber alle Tiers (`storage_layer.md` definiert SeaweedFS-Lifecycle). Machine Unlearning wenn Memories Modellverhalten beeinflusst haben. |
| **7.6** Architecture Pattern | B (Context+Store) → C (Tiered+Learned Control) | **Bei B, planen C** | Paper empfiehlt: Start B, instrument thoroughly, graduate zu C bei empirischem Nachweis |
| **7.7** Memory Observability | Operation Logging, Replay Tools, Memory Diffs, Regression Tests | **Grossteils fehlend** | Memory Operation Log: jeder Read/Write/Update/Delete. Memory Diff: was aenderte sich zwischen Turns. Replay Tool: fehlgeschlagene Interaction mit modifiziertem Memory erneut ausfuehren. Continuous Improvement: welche Records werden nie gelesen? Welche Queries liefern leere Ergebnisse? |

### Kapitel 9: Open Challenges — Luecken und Chancen

| Abschnitt | Thema | Haben wir? | Massnahme |
|-----------|-------|-----------|-----------|
| **9.1** Dual-Buffer Consolidation | Hot Buffer (Probation) → Long-term nach Quality Check | **Aehnlich** — Tiered Storage | Expliziten Probation-Mechanismus hinzufuegen: neue Memories 24h in Hot Buffer, Promotion nach Re-Verification + Dedup + Importance Scoring |
| **9.2** Causal Annotation | Bei Memory Write den "causal parent" annotieren | **Teilweise** — Hindsight Causal Links | Systematisch bei jedem Retain: LLM annotiert geschaetzten Causal Parent. Causal Graph Traversal bei Retrieval neben Similarity Search. |
| **9.3** Trustworthy Reflection | Expiration Policies, Adversarial Probing, Uncertainty Decay | **Geplant** — Confidence Dampening, Cold Storage | Unvalidierte Reflexionen nach 30 Tagen ohne Bestaetigung: Confidence automatisch senken. Periodisch: Adversarial Counter-Examples gegen gespeicherte Beliefs testen. |
| **9.4** Learning to Forget | Selective Forgetting ≠ Cold Storage (archivieren ≠ vergessen) | **Nicht adressiert** | Fuer Privacy/Compliance: echtes Loeschen aus allen Tiers (inkl. Embeddings). Selective Forgetting Policy: welche Memories loeschen vs. archivieren? |
| **9.5** Multimodal Memory | Vision + Audio + Text fusioniert | **Nicht adressiert** | Relevant wenn Voice-Reports (exec-openworldlib Synthesis) oder Chart-Screenshots als Memory gespeichert werden. Cross-modal Retrieval: Chart-Memory via Text-Query finden. |
| **9.6** Multi-Agent Memory Governance | Access Control, Consensus Writes, Knowledge Transfer | **Teilweise** — coherence.py fuer Writes | Distributed Memory mit Merge-Semantik. Per-Agent Caches mit shared Backend. Verbindung zu 6.5 (ACL). |
| **9.7** Memory-Efficient Architectures | Sparse Retrieval, Compressed Session Vectors | **Nicht explizit** | Token Budget (context/token_budget.py) ist verwandt. Compressed Session Vectors als Alternative zu vollem Verbatim evaluieren. |
| **9.8** Ebbinghaus + Spreading Activation | Spaced Repetition, zeitbasierter Decay | **Teilweise** — Hindsight hat Spreading Activation | Ebbinghaus Decay fuer Cold-Migration (siehe 6.1). Spaced Repetition: wichtige Memories periodisch in Context bringen um Retention zu staerken. |
| **9.9** Foundation Model fuer Memory | Task-agnostischer Memory Controller | **Langfrist-Vision** | AgeMem als erster Schritt. Nicht aktuell priorisiert. |
| **9.10** Standardized Evaluation | GLUE-style Leaderboard, 4-Layer Metric Stack | **Nicht vorhanden** | Eigenes Eval-Harness fuer Phase 1+2 (Hindsight vs MemPalace) aufbauen mit allen 4 Layers. |

### Deine Blitzgedanken aus den Notizen

| Gedanke | Einordnung | Aktion |
|---------|-----------|--------|
| "Memory als eigenes Modul (raus aus Harness)?" | Paper 6.8 bestaetigt modular. Port 8093 schon reserviert. | Architektonisch sinnvoll fuer Production. Aktuell kein Blocker — Hindsight ist schon externes Package. |
| "System 3 Think — Trajectories simulieren gegen Entropy Collapse" | Neuro-symbolische Verifikation + Trajectory-Diversitaet. Verbindet exec-ebm (Energy ueber Trajectory-Konsistenz) + Entropy-Schutz + Game Theory Monte Carlo. | Eigenes Thema — nicht Memory-spezifisch. Parken als Forschungsrichtung. |
| "Ebbinghaus Forgetting Curves" | Paper 6.1 + 9.8. MemoryBank nutzt das bereits. | Decay-Score statt starrer 90-Tage-Regel fuer Cold-Migration (siehe 6.1 oben). |
| "Claude Code Scheduling Tasks" | Asynchrone Background Jobs fuer Memory Consolidation. | Bereits geplant: Consolidation Background Job, Cold-Migration Job. |
| "Backwards Reasoning fuer Geopolitik" | Historisches + elementares Wissen als Ausgangspunkt. | Relevant fuer Game Theory / KG. Causal Graph (9.2) ermoeglicht Rueckwaerts-Traversal. |
| "Verschiedene Evaluation Frameworks (Evaline?)" | Paper 5.4 empfiehlt 4-Layer Stack. MemoryArena fuer agentische Tasks. | Eigenes Eval-Harness aufbauen das alle 4 Layers abdeckt. |

---

## 8. Offene Punkte

1. **supermemory** evaluieren (bereits in _ref)
2. **Mem0** als Referenz pruefen (Self-improving Memory Pattern)
3. **Letta/MemGPT** fuer Hierarchical Virtual Context evaluieren
4. **Bayesian RAG** Paper (Frontiers in AI, 2025) genauer studieren — Uncertainty-aware Retrieval
5. **System 3 Think** als eigenes Forschungsthema formalisieren (Trajectory-Simulation + EBM + Game Theory)

6. **!! `agent.sessions` vs Hindsight `operations`/`banks` Abgleich !!**
   - exec-18 Migration 016 erstellt `agent.sessions` (Agent-Execution-Sessions mit status, thread_id, bank_id).
   - Hindsight hat eigene Tabellen: `banks` (per-user Memory-Store), `operations` (retain/recall Log).
   - **Frage:** Ist `agent.sessions` redundant mit Hindsight-Interna? Oder komplementaer?
   - **Aktuelle Einschaetzung:** Komplementaer — `agent.sessions` trackt *Agent-Execution*, Hindsight `operations` trackt *Memory-Ops*. Bridge: `agent.sessions.bank_id` → Hindsight `banks.id`.
   - **Aber:** Wenn `memory_fusion/` (cursor arbeitet dran) Hindsight + MemPalace fusioniert, muss geprueft werden ob die Session-Tabelle noch zum neuen Memory-Pfad passt oder angepasst werden muss.
   - **TODO:** Cursor-Instanz muss `agent.sessions` Schema-Kompatibilitaet mit memory_fusion abgleichen.

7. **!! api_version / Schema-Drift fuer Memory !!**
   - `api_version` existiert auf `agent.agent_skills` (exec-skills §6.6) — trackt welche Tool-API-Version ein Skill referenziert.
   - **Gleiche Logik braucht Memory:** Hindsight `memory_units` die Tool-Call-Patterns speichern (z.B. "Agent rief `market_data_fetch(symbol='BTCUSD')` auf") werden ungueltig wenn die Tool-API sich aendert.
   - **Loesung:** `api_version` Tag bei Hindsight Retain oder als Feld auf `memory_units`. Alte Records bei API-Aenderung als `stale` flaggen.
   - **Scope:** Nicht exec-memory allein — betrifft exec-18 (`component_configs.api_version`), exec-skills, und Hindsight. Vermerkt auch in exec-18 Verify-Punkte.

---

## 9. Naechste Schritte

**Phase 1+2 Eval (Prioritaet):**
- [ ] MemPalace isoliert testen: `python-backend/experiments/memory_eval/` (README + Protokoll) bzw. dedizierter Ordner unter `experiments/`
- [ ] Hindsight vs. MemPalace Benchmark auf eigenen Daten
- [ ] Eval-Harness mit 4-Layer Metric Stack (Task + Quality + Efficiency + Governance)
- [ ] MemoryArena-artige Tests: nicht nur Recall, sondern aktive Decision-Making
- [ ] Forgetting-Szenario testen (veraltete/korrigierte Fakten)
- [ ] Cost/Latenz pro Memory-Operation messen

**Architektur (nach Eval):**
- [x] `Personal Raw Evidence` als expliziten Write-Vertrag festziehen (`chat_turn`, `tool_output`, `scratch_note`) — aktuell im `memory_fusion` Retain-Pfad ueber `semantics.py`
- [x] `Personal Derived Memory` als expliziten Write-Vertrag festziehen (`observation`, `preference`, `mental_model`) — aktuell im `memory_fusion` Retain-Pfad ueber `semantics.py`
- [~] Promotion-Gates `raw -> derived` festziehen: keine Observation ohne Evidence-Backlinks / Provenance / Status — Backlinks/Provenance sind jetzt enforced, `status`/Promotion-Workflow noch offen
- [x] User-Input / Tool-Output / Agent-Output als `source_type` markieren (`user_input`, `tool_output`, `agent_output`, `system_observation`)
- [x] Agent-Output als sekundaeres Artefakt markieren, nicht still wie primaere Evidenz behandeln
- [x] Guardrail: `Personal Knowledgebase` bleibt separates Default-Ziel fuer kuratierte Artefakte (`exec-personal-kb`)
- [x] Guardrail: `Global World Evidence/KG` bleibt separates Default-Ziel fuer Weltwissen (`exec-world-model`)
- [ ] Verbatim-Store Schema Design (`verbatim_store` Tabelle)
- [ ] L0-L3 Layer-Konzept Prototype
- [ ] Ebbinghaus Decay-Score statt starre 90-Tage Cold-Migration
- [~] Source Attribution Feld auf Memory Units — aktuell als semantische Metadata im `memory_fusion` Pfad, noch nicht als explizites DB-/Schema-Feld
- [ ] Memory Operation Logging
- [ ] Query Reformulation + Self-RAG Gate
- [ ] MemoryAccessPolicy fuer `personal raw` vs `personal derived` vorbereiten (Read/Write pro Agent/Consumer)
- [ ] Context-/Prompt-Pfad — **nicht gelöscht**, Detail in [`exec-context.md`](./exec-context.md) §6–7 (eine Quelle statt Doppelpflege in exec-memory §3f):
  - [ ] Compaction-Trigger: Kontextfenster, Token-Count, **80 % Pre-Save**
  - [ ] LiteLLM (**provider-agnostisch**, aktuell v. a. **OpenRouter**-Upstreams): `llm_client` + ggf. Cache-Parameter
  - [ ] `context/merge.py`: statischer Prefix zuerst
  - [ ] Self-hosted optional: vLLM / SGLang / LMCache

**Portierung:**
- [ ] RAPTOR + Late Chunking aus Paperwatcher
- [ ] Temporal Triple-Store in `memory_engine/kg_store.py`
- [ ] Query Sanitizer aus MemPalace
- [ ] Cosine Dedup aus MemPalace

**Langfristig:**
- [ ] Latency-Optimierung (Async Writes, Progressive Retrieval, Dynamic Routing)
- [ ] Privacy/PII Deletion ueber alle Tiers
- [ ] Multi-Agent Memory ACL (MEMORY_ARCHITECTURE.md 15.1)
- [ ] Multimodal Memory (wenn Voice/Chart-Memory kommt)

**Verify / offene Punkte fuer aktuelle Umsetzung:**
- [x] `memory_ab` Persistenzpfad existiert (`agent/harness/evals_store.py`, `scripts/persist_memory_ab_eval.py`) und ist jetzt an file-basierte Hindsight-/MemPalace-Runs anschliessbar
- [x] Hindsight-Runner (`experiments/memory_eval/run_hindsight_eval.py`) und echter MemPalace-Runner auf Basis des Submoduls (`experiments/memory_eval/run_mempalace_eval.py`, `_ref/mempalace/`) existieren; Aggregation existiert (`experiments/memory_eval/aggregate_memory_ab.py`)
- [x] MemPalace ist als waehlbare Runtime-Engine im Python-Backend anschliessbar (`AGENT_MEMORY_ENGINE=mempalace`, `agent/memory/mempalace_engine.py`, `agent/memory/engine.py`)
- [x] Minimaler Linux/Podman-Stack fuer Memory-Evals ist separat beschrieben (`docker-compose.memory-eval.yml`, `experiments/memory_eval/STACKS.md`) statt den vollen DevStack zu erzwingen
- [x] Gemeinsamer Shared-Corpus-Pfad fuer `hindsight` / `mempalace` / `fusion` existiert (`experiments/memory_eval/load_benchmark_corpus.py`, `sample_shared_corpus.json`, `sample_shared_queries.json`, `aggregate_memory_suite.py`) und liefert kanonische `expected_refs`
- [x] `memory_fusion/` ist jetzt ein eigener Runtime-Umbaupfad auf Basis von `agent/memory` (`memory_fusion/engine.py`, `runtime_env.py`, `coherence.py`, `observation_skills.py`) und vermeidet produktive Runtime-Imports aus `_ref/mempalace`
- [x] `memory_fusion/` Read-/Retain-Pfad existiert (`memory_fusion/fusion_engine.py`, `summary_builder.py`, `experiments/memory_eval/run_fusion_eval.py`) und wurde auf Postgres mit dem Shared-Corpus verifiziert
- [x] Groesserer Langkontext-Smoke fuer `summary` / `verbatim` / `fusion` existiert (`experiments/memory_eval/run_long_context_smoke.py`) und ist lokal auf Postgres verifiziert; bei `summary_llm_provider=none` liefern aktuell alle drei Routen identische Metriken, waehrend der Harness fuer spaetere LLM-backed Summary-Runs vorbereitet ist
- [x] `memory_fusion` nutzt MemPalace-Konzepte produktiv im Postgres-Pfad: `query_sanitizer`, kanonische `source_ref`/`provenance_ref`, Method-of-Loci-Metadaten (`wing` / `room` / `hall` / `closet_id` / `drawer_id`) fuer Recall-Filter, verbatim evidence surfacing
- [x] Langkontext-Runner kann jetzt Ingest und Recall-only trennen (`--bank-id`, `--skip-retain`, `--session-count`, `--max-queries`, `--routes`) und der Recall-only-Reuse wurde lokal verifiziert
- [x] Echter Postgres-End-to-End-Smoke fuer Personal-Memory-Guardrails ist einmal gruen gelaufen und wird als Verify-Artefakt festgehalten (`python-backend/experiments/memory_eval/run_memory_fusion_e2e_smoke.py`; lokal verifiziert via `uv run python experiments/memory_eval/run_memory_fusion_e2e_smoke.py --out /tmp/memory-fusion-e2e-smoke.json --db-url postgresql://postgres:postgres@localhost:5433/hindsight_dev --cleanup`)
- [~] `control_ui` haengt jetzt an einem echten Memory-/Context-Inspector-Vertrag (`control-ui/src/features/memory/components/MemoryRuntimeInspector.tsx`, `control-ui/src/features/control/components/ContextTab.tsx`, `control-ui/src/app/api/memory/[...path]/route.ts`, `control-ui/src/app/api/control/[...path]/route.ts`, `python-backend/agent/control/memory.py`, `python-backend/agent/control/context.py`); dedizierte Personal-KB-/World-Detail-Surfaces bleiben noch offen
- [~] Cross-System-Ground-Truth fuer fehlende Public-Benchmark-Adapter ist vorbereitet (`prepare_convomem_adapter.py`, `prepare_memoryarena_adapter.py`), aber noch nicht an echte Public-Dataset-Downloads verdrahtet
- [x] Roher User-Input wird im produktiven `memory_fusion`-Pfad explizit als Evidenzquelle markiert, nicht als implizite Observation / Wahrheit
- [x] `derived memory`-Objekte tragen im `memory_fusion`-Pfad Evidence-/Source-Backlinks und surfacen nicht allein (`retain`, `recall`, `list_memory_units`, `list_documents`, `get_document`)
- [x] Gespeicherte PDFs / Webclips / Transcripts landen im `memory_fusion`-Default-Write-Pfad nicht still im Personal Memory, sondern werden als KB-Bridge-Ziel abgewiesen
- [x] Globales Weltwissen geht im `memory_fusion`-Default-Write-Pfad nicht ueber denselben Personal-Memory-Truth-Pfad
- [~] Memory-Evals trennen Verbatim-, Derived-, Cross-Session- und Forgetting-Fragen — aktuell im Langkontext-Smoke / `run_fusion_eval.py`, noch nicht als vollstaendige Suite ueber alle Eval-Pfade
- [ ] Kein produktiver Hybrid-Fallback aktiv, bis Eval auf echten Daten abgeschlossen ist
- [ ] Referenz-Papers sind ArXiv-kanonisch; lokale PDF-Pfade nur nutzen, wenn Artefakte im Clone wirklich vorhanden sind

---

## Known Issues & Future Architecture (2026-04-17 Addendum)

### Issue: MemPalace nutzt Filesystem statt Postgres

**Problem**: MemPalace als Memory-Engine aktuell auf Filesystem-basierte Storage (`MEMPALACE_PALACE_PATH=./data/memory/palace`) statt gemeinsam mit Hindsight in PostgreSQL.

**Warum ein Problem**:
- War ursprünglich **nicht das Ziel**. Memory-Layer sollte konsistent in einer relationalen Storage-Schicht sein (PostgreSQL mit pgvector).
- Inkonsistente Backup-Strategien: Hindsight über pg_dump, MemPalace nur über filesystem-snapshot.
- Keine ACID-Garantien bei parallelen Reads/Writes über die beiden Engines.
- Mempalace-Konzepte (Method-of-Loci, wing/room/hall Hierarchie) sind in `memory_fusion` bereits produktiv nach Postgres portiert — daher ist die Filesystem-MemPalace-Engine doppelt mit memory_fusion-Postgres-Pfad.

**Status**: 🚧 **NICHT weiter verfolgen** in aktueller Session-Scope. Dokumentiert für spätere Evaluation.

**Wenn später angegangen**:
- MemPalace-Engine refactoren auf PG (analog memory_fusion's erfolgreicher Portierung)
- Oder: MemPalace deprecaten zugunsten von memory_fusion (das MemPalace-Konzepte bereits nutzt)
- Filesystem-Pfad nur als ephemeral cache / snapshot-export behalten

### Future Option: Eigene Postgres-Instance für Memory-Layer

**Aktuelle Architecture** (2026-04-17):
```
postgres :5433 (hindsight_dev DB)
  ├─ public         (Hindsight — external package, vector-heavy)
  ├─ storage        (Go-appservice: artifact_metadata)
  ├─ matrix_crypto  (Go-appservice: Matrix E2EE)
  ├─ agent          (Python: audit, skills, sessions, ...)
  └─ ingestion      (Python: ingestion_jobs, chunk_hashes)
```

**Option für Skale**: Memory-Layer (Hindsight + eventuell Mempalace-DB-Migration) auf eigene Postgres-Instance ausziehen:

```
postgres-core :5433 (hindsight_dev)        postgres-memory :5434 (memory)
  ├─ storage                                 ├─ public (Hindsight pgvector)
  ├─ matrix_crypto                           ├─ memory_fusion (summary/verbatim)
  ├─ agent                                   └─ (later: mempalace DB-port)
  └─ ingestion
```

**Code-seitig bereits vorbereitet**:
```python
# memory_fusion/runtime_env.py:24
os.environ.setdefault("HINDSIGHT_API_DATABASE_URL", db_url)
```
Wenn `HINDSIGHT_API_DATABASE_URL` (separate URL) gesetzt → Hindsight nutzt eigene DB.
Wenn nicht → Fallback auf shared `HINDSIGHT_DB_URL`.

**Scale-Trigger für Migration**:
- >10k Memory-Conversations (~100k+ embedding-rows)
- Vector-search-Latency beeinträchtigt OLTP-Queries (cache-eviction)
- Differenzierte Backup-Strategie nötig (Memory append-only vs. transactional read-heavy)
- Multi-tenant-Isolation wird relevant

**Aktuell**: NICHT nötig bei Dev-/Solo-Scale. Vermerkt als Future-Option.

**Verantwortlichkeit**:
- Infrastructure-Changes in `docker-compose.yml` + `.env.development` (wenn aktiviert)
- Code-Change: nur `HINDSIGHT_API_DATABASE_URL` setzen — kein Refactor nötig
- Migration-Strategy: pg_dump Hindsight-tables + restore in neue DB

---

## 3h. Hindsight compression-fact-ingest + MemPalace pre_compression-archive (Phase-B P5 DONE)

**Status:** ABC + wiring DONE (2026-04-20); concrete MemPalace verbatim-archive + Hindsight fact-ingest implementations PENDING (exec-memory follow-up tickets).
**Cross-ref:** `exec-hermes.md §0` (context_compressor row), `exec-context.md §11`.

### 3h.1 ABC contract (shipped)

```python
class MemoryProvider(ABC):
    async def on_pre_compress(
        self,
        messages: list[dict[str, Any]],
        *,
        user_id: str,
        bank_id: str,
    ) -> str | None:
        """Fire at the ≥80% context-window threshold BEFORE compaction shrinks
        visible history. Providers persist verbatim content and MAY return
        a short digest snippet for post-compact re-injection. Default no-op.
        """
```

`MemoryManager.on_pre_compress` fans out over all available providers, swallows per-provider failures, and returns the list of non-None snippets. `agent/middleware/compression.py::notify_pre_compression` calls it under `asyncio.wait_for(..., timeout=0.5)` (configurable via `AGENT_PRE_COMPRESS_TIMEOUT_S`) — timeout or exception emits archive-miss and the LLM compression proceeds.

### 3h.2 Ordering contract (enforced by runner)

1. `runner._prepare_messages` classifies stage via `ContextEngine.stage_for`.
2. On `emergency`: runner emits span-event `pre_compression` (observational).
3. `compression.compress(...)` → `summarize_old_messages` → `notify_pre_compression(old_messages, ...)` (data-preserving consumers awaited with bounded timeout).
4. LLM summary call runs → replaces old messages.
5. Agent turn continues with compressed messages.

### 3h.3 Concrete-provider TODOs (NOT P5 scope)

- **MemPalace** — `on_pre_compress` persists the full pre-compaction message-list as a long-term retrievable raw log, keyed by `(user_id, bank_id, session_id, timestamp)`. Returns `None` (no post-compact digest needed — mempalace retrieval is surfaced through its own recall path).
- **Hindsight** — consumes the LLM-compression-summary output **after** step 4 as a fact-list ingest (post-compact hook, not `on_pre_compress` itself). Confidence-decay applies. This is a separate hook — `on_compression_complete(summary, ...)` — not yet added to the ABC.

The runner treats the returned snippet list as reserved for future re-injection; currently ignored. When concrete impls land, runner will splice the snippets back into the message-list post-compression.
