# Memory Architecture -- Ist-Zustand & Soll-Zustand

> **Stand:** 22. Februar 2026
> **Zweck:** Definiert das Gesamtbild fuer Caching, Persistenz, Wissensrepraesentation und Agent-Memory in TradeView Fusion. Von kurzfristigen TTL-Caches bis zu langfristigem Knowledge-Graph-basiertem Agentenwissen.
> **Referenz-Dokumente:** [`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md), [`GAME_THEORY.md`](./GAME_THEORY.md) (Sek. 8: Knowledge Graph), [`INDICATOR_ARCHITECTURE.md`](./INDICATOR_ARCHITECTURE.md) (Sek. 0.3-0.7: Cache-Strategie), [`Advanced-architecture-for-the-future.md`](./Advanced-architecture-for-the-future.md) (Sek. 7: RAG/Reasoning), [`RAG_GRAPHRAG_STRATEGY_2026.md`](./RAG_GRAPHRAG_STRATEGY_2026.md) (Dual Pipeline, Hybrid Retrieval, GraphRAG/UQ-Strategie), [`POLITICAL_ECONOMY_KNOWLEDGE.md`](./POLITICAL_ECONOMY_KNOWLEDGE.md) (Sek. 8: KG Domain D Seed-Schema), [`archive/KG_ONTOLOGY.md`](./archive/KG_ONTOLOGY.md) (formales Schema, Ontologie-Quellen; archivierte Referenz), [`geo/GEOMAP_ONTOLOGY_GRAPH_RUNTIME.md`](./geo/GEOMAP_ONTOLOGY_GRAPH_RUNTIME.md) (Geo-spezifischer Ontologie-/Graph-Owner fuer Search-Around, Tracks und Writeback), [`EPISTEMIC.md`](./EPISTEMIC.md) (Verbindliche epistemische Systemregeln: 6-Schichten-Wissensmodell, Truth/Belief/Scenario, Promotion Gates — dieses Dokument liefert die Speicher-Infrastruktur, EPISTEMIC.md die epistemischen Regeln darueber), [`ENTROPY_NOVELTY.md`](./ENTROPY_NOVELTY.md) (Entropie-Kollaps-Risiken fuer M3 Episodic Feedback und KG-Confidence)
> **Referenz-Buecher:**
> - "The Behavior Ops Manual" (Chase Hughes, 2022) -- BTE/DRS als strukturiertes Wissen im Knowledge Graph
> - "Die 36 Strategeme" (Prof. Rieck) -- Krisenlogik als relationales Wissen im Knowledge Graph
> - "GenAI and LLMs for Beyond 5G Networks" (Springer, 2026) -- RAG-Patterns, Agent Orchestration
> **Primaer betroffen:** Alle Services (Python, Go, TypeScript), Agent-Pipeline, Frontend

---

## Inhaltsverzeichnis

1. [Warum eine Memory-Architektur?](#1-warum-eine-memory-architektur)
2. [Das Drei-Schichten-Modell](#2-das-drei-schichten-modell)
3. [Ist-Zustand: Was existiert](#3-ist-zustand-was-existiert)
   - 3.1 [Working Memory (Kurzfristig)](#31-working-memory-kurzfristig)
   - 3.2 [Episodic Memory (Mittelfristig)](#32-episodic-memory-mittelfristig)
   - 3.3 [Semantic Memory (Langfristig)](#33-semantic-memory-langfristig)
4. [Ehrliche Bewertung: Luecken](#4-ehrliche-bewertung-luecken)
5. [Soll-Zustand: Stufenplan](#5-soll-zustand-stufenplan)
   - 5.1 [Stufe M1: Shared Cache Layer (Redis)](#51-stufe-m1-shared-cache-layer-redis)
   - 5.2 [Stufe M2: Knowledge Graph (Strukturiertes Wissen)](#52-stufe-m2-knowledge-graph-strukturiertes-wissen)
   - 5.3 [Stufe M3: Episodic Store (Agent-Erfahrung)](#53-stufe-m3-episodic-store-agent-erfahrung)
   - 5.4 [Stufe M4: Vector Store + RAG Pipeline](#54-stufe-m4-vector-store--rag-pipeline)
   - 5.5 [Stufe M5: Agent Working Memory (Context Management)](#55-stufe-m5-agent-working-memory-context-management)
6. [Knowledge Graph im Detail](#6-knowledge-graph-im-detail)
7. [Architektur-Ueberblick: Alle Schichten zusammen](#7-architektur-ueberblick-alle-schichten-zusammen)
8. [Querverweise](#8-querverweise)
9. [Offene Fragen](#9-offene-fragen)

---

## 1. Warum eine Memory-Architektur?

Das Projekt hat aktuell **keinen einheitlichen Umgang mit Wissen und Gedaechtnis**. Jeder Service hat seine eigene Ad-hoc-Loesung:

- TypeScript Bridges: `Map<string, CacheEntry>` mit TTL (vergessen alles bei Neustart)
- Python FinBERT: Thread-safe Dict mit FIFO-Eviction (isoliert, nicht teilbar)
- Go CrisisWatch: In-Memory + optionaler JSON-Persist (einziger der Neustarts ueberlebt)
- Prisma/SQLite: Strukturierte Persistenz, aber kein Wissensmodell
- LLM-Agenten: Existieren noch nicht, haben also kein Memory-Konzept

Das funktioniert fuer den aktuellen Stand. Aber sobald Agenten Entscheidungen treffen (ab `AGENT_ARCHITECTURE.md` Sek. 2), brauchen sie:
- **Wissen** (Was sind die BTE-Marker? Was bedeutet Strategem 6?)
- **Erfahrung** (Letzte Analyse von Iran-Sanktionen: Impact 0.7, Markt reagierte +2.3% auf GLD)
- **Kontext** (Aktueller Marktregime: risk_off. Letzte 5 Events im MENA-Raum)

Ohne definierte Memory-Architektur wird jeder Agent improvisieren -- und das fuehrt zu Inkonsistenz, Halluzination und fehlender Nachvollziehbarkeit.

---

## 2. Das Drei-Schichten-Modell

Inspiriert von menschlichem Gedaechtnis und gaengigen Agent-Memory-Frameworks:

```
┌──────────────────────────────────────────────────────────────┐
│                   AGENT / SERVICE                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  WORKING MEMORY (Sekunden - Minuten)                   │  │
│  │                                                        │  │
│  │  "Was passiert gerade?"                                │  │
│  │  - Aktueller Request-Kontext                          │  │
│  │  - LLM Context Window                                 │  │
│  │  - TTL-Caches (In-Memory, Redis)                      │  │
│  │  - Indicator-Ergebnisse (letzte Berechnung)           │  │
│  └────────────────────┬───────────────────────────────────┘  │
│                       │ liest / schreibt                     │
│  ┌────────────────────▼───────────────────────────────────┐  │
│  │  EPISODIC MEMORY (Stunden - Monate)                    │  │
│  │                                                        │  │
│  │  "Was ist frueher passiert?"                           │  │
│  │  - Vergangene Analysen + Ergebnisse                   │  │
│  │  - Event → Marktreaktion Korrelationen                │  │
│  │  - Profiling-Historie (BTE/DRS ueber Zeit)            │  │
│  │  - Agent-Entscheidungslog (warum Score X?)            │  │
│  │  - User Feedback (Override-Historie)                   │  │
│  └────────────────────┬───────────────────────────────────┘  │
│                       │ liest                                │
│  ┌────────────────────▼───────────────────────────────────┐  │
│  │  SEMANTIC MEMORY (Permanent)                           │  │
│  │                                                        │  │
│  │  "Was wissen wir grundsaetzlich?"                      │  │
│  │  - Knowledge Graph (Strategeme, BTE, Relationen)      │  │
│  │  - Region → Symbol Mapping                            │  │
│  │  - Akteur-Typen + typische Strategien                 │  │
│  │  - Domain-Ontologie (Sanktionen, Eskalation, ...)     │  │
│  │  - Buch-Wissen (Chase Hughes, Rieck, Keen)            │  │
│  │  - Vector Store (Embeddings von News, Reports)        │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Kernprinzip:** Jede Schicht hat andere Charakteristiken:

| Schicht | Lebensdauer | Zugriffsart | Daten-Typ | Technologie |
|---|---|---|---|---|
| Working | Sekunden-Minuten | Schnell, fluechtig | Berechnungsergebnisse, Request-State | In-Memory (Map/Redis) |
| Episodic | Stunden-Monate | Gezielt abrufbar | Vergangene Analysen, Feedback | PostgreSQL / SQLite |
| Semantic | Permanent | Strukturiert querybar | Fakten, Relationen, Ontologien | Knowledge Graph + Vector Store |

### 2.1 Epistemische Trennung (verbindlich)

Zusaetzlich zu Working / Episodic / Semantic Memory gilt projektweit eine zweite,
gleich wichtige Trennung:

- **truth** = kanonische oder stark verifizierte Fakten
- **belief** = plausibler, aber unsicherer Arbeitsstand
- **scenario** = hypothetische oder simulierte Pfade

Diese Ebenen duerfen nicht still vermischt werden.

Praktische Arbeitsregel:

- `semantic memory` darf truth und sauber markierte belief-Strukturen enthalten
- `episodic memory` speichert Verlauf, Overrides, Bewertungen und Agent-Erfahrung
- `scenario`-Artefakte bleiben standardmaessig ephemer oder klar getrennt von
  kanonischen Stores

Damit verhindern wir, dass Retrieval, Agenten oder Simulation spaeter faktische,
hypothetische und persoenliche Overlays in einen einzigen Wahrheitsraum
zusammenziehen.

---

## 3. Ist-Zustand: Was existiert

### 3.0 Cache-Adapter-Minimalvertrag (Python + Go)

**Implementierung:** `python-backend/services/_shared/cache_adapter.py`, `go-backend/internal/cache/adapter.go`

| Methode | Python | Go | Beschreibung |
|---------|--------|-----|--------------|
| `get(key)` | `async get(key: str) -> Optional[Any]` | `Get(ctx, key) ([]byte, bool)` | Wert abrufen, `None`/`false` bei Miss |
| `set(key, value, ttl)` | `async set(key, value, ttl_seconds=300)` | `Set(ctx, key, value, ttl)` | Wert mit TTL speichern |
| `delete(key)` | `async delete(key: str)` | `Delete(ctx, key)` | Key loeschen |
| `ping()` | `async ping() -> bool` | `Ping(ctx) error` | Health-Check |

**TTL-Konstanten:** `TTL_LIVE=300`, `TTL_INDICATOR=900`, `TTL_SNAPSHOT=3600` (Sekunden).

**Key-Namespace:** `tradeview:memory:kg:nodes:{type}:{limit}`, `tradeview:memory:kg:sync`, `tradeview:m1:{indicator}:{symbol}:{tf}`.

**Telemetrie (geplant):** `cache.provider`, `cache.hit_rate`, `cache.fallback_active`, `cache.errors` — noch nicht verbindlich in allen Handlern.

**Hinweis:** `scan-prefix`/`ttl` als separate Methode sind optional; LRU/Redis nutzen TTL beim `set`.

### 3.1 Working Memory (Kurzfristig)

**Status: Vorhanden, aber fragmentiert und nicht geteilt.**

| Komponente | Datei | TTL | Env-Override | Eviction |
|---|---|---|---|---|
| GeoContext Bridge Cache | `src/lib/server/geopolitical-context-bridge.ts` | 300s | `GEOPOLITICAL_CONTEXT_CACHE_MS` | Keine (waechst unbegrenzt) |
| GameTheory Bridge Cache | `src/lib/server/geopolitical-game-theory-bridge.ts` | 120s | `GEOPOLITICAL_GAMETHEORY_CACHE_MS` | Keine |
| ACLED Bridge Cache | `src/lib/server/geopolitical-acled-bridge.ts` | 60s | `GEOPOLITICAL_ACLED_CACHE_MS` | Keine |
| News Aggregator Cache | `src/lib/news/aggregator.ts` | 120s | `NEWS_CACHE_TTL_MS` | Keine |
| CrisisWatch Cache (Go) | `go-backend/internal/connectors/crisiswatch/client.go` | 300s | `CRISISWATCH_CACHE_TTL_MS` | TTL + JSON-File-Persist |
| FinBERT Score Cache (Python) | `python-backend/ml_ai/.../pipeline.py` | 600s | `FINBERT_HF_CACHE_TTL_MS` | FIFO (max 2000 Entries) |

**Probleme:**
- Jeder Cache ist prozess-lokal (`Map<>` in TS, `dict` in Python, `sync.RWMutex` in Go)
- Kein Cross-Service-Sharing: Python berechnet FinBERT-Score, TypeScript weiss nichts davon
- TS-Caches wachsen unbegrenzt (kein max-size, kein LRU)
- Alles ausser CrisisWatch geht bei Neustart verloren
- TanStack React Query ist installiert (`@tanstack/react-query@5.82`), aber **nirgends benutzt** -- fehlende Client-Side Cache-Schicht

**Was funktioniert:** Die TTL-Caches vermeiden redundante API-Calls innerhalb kurzer Zeitfenster. Fuer den aktuellen Single-User-Kontext reicht das.

### 3.2 Episodic Memory (Mittelfristig)

**Status: Teilweise vorhanden ueber Prisma/SQLite, aber nicht als "Memory" konzipiert.**

| Was gespeichert wird | Technologie | Datei | Zweck |
|---|---|---|---|
| Geopolitische Events | Prisma/SQLite + JSON-Fallback | `src/lib/server/geopolitical-events-store.ts` | Event-Historie fuer GeoMap |
| Geo Candidates | Prisma/SQLite + JSON-Fallback | `src/lib/server/geopolitical-candidates-store.ts` | Candidate Pipeline (accept/reject) |
| Geo Timeline | Prisma/SQLite + JSON-Fallback | `src/lib/server/geopolitical-timeline-store.ts` | Event-Chronologie |
| Geo Drawings | Prisma/SQLite + JSON-Fallback | `src/lib/server/geopolitical-drawings-store.ts` | User-Annotationen auf der Karte |
| Price Alerts | Prisma/SQLite + JSON-Fallback | `src/lib/server/price-alerts-store.ts` | User-Alerts |
| Paper Orders | Prisma/SQLite + JSON-Fallback | `src/lib/server/orders-store.ts` | Paper Trading |
| Portfolio Snapshots | Prisma/SQLite + JSON-Fallback | `src/lib/server/portfolio-history-store.ts` | Portfolio-Tracking |
| Trade Journal | Prisma/SQLite + JSON-Fallback | `src/lib/server/trade-journal-store.ts` | Manuelles Trading-Tagebuch |
| User Profile / Watchlists | Prisma/SQLite | `prisma/schema.prisma` | User-Daten |

**Was fehlt fuer echtes Episodic Memory:**
- **Keine Agent-Entscheidungslogs:** Warum hat der Game-Theory-Scorer 0.7 vergeben? Welche Faktoren trugen wie viel bei?
- **Keine Rueckkopplung:** Event X hatte Score 0.7 → GLD bewegte sich +2.3%. Dieses Wissen wird nirgends gespeichert oder genutzt.
- **Keine Profiling-Historie:** BTE/DRS-Scores ueber Zeit pro Person (`AGENT_ARCHITECTURE.md` Sek. 8) -- geplant, nicht implementiert.
- **Kein Override-Tracking mit Feedback-Loop:** Candidate accept/reject wird gespeichert, aber nicht systematisch ausgewertet (`GEOMAP_OVERVIEW.md` Sek. 5.4: "System erkennt eigene Schwaechen" -- Zukunft).

### 3.3 Semantic Memory (Langfristig)

**Status: Praktisch nicht vorhanden.**

| Was existiert | Was es ist | Was fehlt |
|---|---|---|
| `game_theory.py` RISK_OFF/ON Tokens | Hardcodierte Wortlisten | Keine Relationen, keine Semantik, kein Graph |
| Region-to-Symbol Mapping | Statisches Python-Dict | Kein Update-Mechanismus, keine Gewichtung |
| Country-to-Region Mapping | Statisches Python-Dict | Kein Kontext (historisch? aktuell?) |
| `chroma_data/chroma.sqlite3` (188 KB) | Leere ChromaDB-Datei | Kein Code referenziert sie. Vermutlich IDE-Artefakt |
| BTE-Marker-Tabelle in AGENT_ARCHITECTURE.md | Nur im Markdown-Dokument | Nicht maschinenlesbar, nicht querybar |
| 36 Strategeme in GAME_THEORY.md | Nur im Markdown-Dokument | Nicht maschinenlesbar, nicht querybar |

**Kernerkenntnis:** Das gesamte Domain-Wissen (BTE-Marker, Strategeme, Krisenlogik, Akteur-Typen, Eskalationsmuster) existiert **nur in Markdown-Dokumenten und Hardcoded-Dicts**. Kein Agent kann dieses Wissen programmatisch abfragen. Es gibt keinen Knowledge Graph, keinen Vector Store, kein RAG.

---

## 4. Ehrliche Bewertung: Luecken

| Luecke | Schweregrad | Betrifft Stufe | Auswirkung |
|---|---|---|---|
| **Kein Shared Cache (Redis)** | Hoch | M1 | Services duplizieren Arbeit, kein Cross-Service State |
| **Kein Knowledge Graph** | Hoch | M2 | Agenten haben kein strukturiertes Wissen, muessen alles aus Prompts lernen → Halluzination |
| **Kein Agent-Entscheidungslog** | Hoch | M3 | Keine Nachvollziehbarkeit, kein Lernen aus Fehlern |
| **Kein Vector Store / Embeddings** | Mittel | M4 | Kein semantisches Retrieval von News/Events/Reports |
| **Kein LLM Context Management** | Mittel | M5 | Noch keine LLM-Agenten implementiert, also noch nicht akut |
| **TanStack Query ungenutzt** | Niedrig | M1 | Frontend fetcht ohne Client-Side-Cache-Deduplication |
| **Unbegrenzte TS-Caches** | Niedrig | M1 | Memory Leak bei Langzeitbetrieb (theoretisch, praktisch irrelevant bei Neustarts) |

---

## 5. Soll-Zustand: Stufenplan

### 5.1 Stufe M1: Shared Cache Layer (Redis)

> **Frage:** "Wie vermeiden wir doppelte Berechnung zwischen Services?"

**Was gebaut wird:**
- Redis-Instanz in Docker Compose (Ergaenzung zu bestehendem Setup)
- Einheitliche Cache-Keys: `tv:{service}:{entity}:{params_hash}` (Pattern aus `INDICATOR_ARCHITECTURE.md` Sek. 0.3)
- TTL-Policies: Intraday 5min, Daily 30min, Backtests 1h
- Pub/Sub fuer Cross-Service Invalidierung

**Migration der bestehenden Caches:**

| Bestehend | Wird zu |
|---|---|
| TS `Map<string, CacheEntry>` | Redis GET/SET mit TTL (pro Bridge) |
| Python FinBERT Dict | Redis GET/SET mit TTL + max-entries via sorted set |
| Go CrisisWatch in-memory | Redis GET/SET (JSON-File-Persist wird Fallback) |
| Frontend (nichts) | TanStack React Query `useQuery()` mit `staleTime`/`gcTime` |

**Abhaengigkeit:** Keine. Kann sofort gebaut werden.

**Referenz:** `INDICATOR_ARCHITECTURE.md` Sek. 0.3-0.7 (detaillierte Redis-Key-Schemata und TTL-Policies)

### 5.2 Stufe M2: Knowledge Graph (Strukturiertes Wissen)

> **Frage:** "Wie geben wir Agenten strukturiertes, relationales Wissen?"

**Warum Knowledge Graph statt Vector DB:** Siehe `GAME_THEORY.md` Sek. 8 fuer die ausfuehrliche Begruendung. Kurzfassung:
- Strategem 6 (Cheap Talk) und Strategem 8 (Costly Signal) sind kontrastiv -- Similarity Search wuerde sie vermischen
- BTE-Marker haben exakte Punktwerte und Schwellwerte -- Fakten, keine Assoziationen
- Krisenlogik hat kausale Ketten -- ein Graph modelliert `Kipppunkt --[fuehrt_zu]--> Dammbruch`

**Formale Bestaetigung (CE 2.0 Research):** Das Paper "On the Theoretical Limitations of Embedding-Based Retrieval" ([arXiv:2508.21038](https://arxiv.org/abs/2508.21038)) beweist mathematisch dass Single-Vector-Embeddings bei komplexem Reasoning fundamental versagen -- insbesondere bei kontrastiven Aufgaben (exakt unser Strategem-6-vs-8 Problem) und Multi-Hop-Queries ("Was beeinflusst was beeinflusst mein Portfolio?"). In der CE 2.0 Terminologie heisst dieser Ansatz **GraphRAG**: Graph fuer Struktur + Vector fuer Semantik = Hybrid. Unsere FalkorDB-Architektur (KG + Built-in Vector Index) implementiert genau dieses Pattern. Die projektnahe Einordnung liegt in [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md).

#### Zwei-Schichten-KG-Architektur

Das KG-System ist zweistufig aufgebaut: ein **shared Backend-KG** (Domain-Wissen, alle User) und ein **per-User Frontend-KG** (persoenliches Wissen, im Browser). Die Trennung loest drei Probleme gleichzeitig:

1. **Latenz:** User-zentrische Queries ("Welche meiner Positionen sind betroffen?") werden in <1ms im Browser beantwortet, ohne API-Call.
2. **Privacy:** User-spezifische Beziehungsdaten (Portfolio-Struktur, Override-Patterns, Annotationen) verlassen den Browser nicht. Der Backend-KG sieht nur anonymisierte Merge-Queries (Symbol-IDs).
3. **Offline:** Der User-KG funktioniert ohne Backend. Portfolio-Graph, Trade-History, Karten-Annotationen -- alles lokal verfuegbar.

```
┌──────────────────────────────────────────────────────────────────┐
│  FRONTEND  Per-User KG (KuzuDB WASM, ~50-500 Nodes)             │
│                                                                  │
│  Portfolio, Watchlists, Alerts, Journal, Drawings, Overrides     │
│  + Subset des Domain-KG (Region→Symbol Mapping, ~50 Nodes)      │
│                                                                  │
│  Querybar via Cypher im Browser, persistiert in IndexedDB        │
└────────────────────────┬─────────────────────────────────────────┘
                         │ sync (SSE downstream, API-Merge upstream)
┌────────────────────────▼─────────────────────────────────────────┐
│  BACKEND  Shared Domain-KG (NetworkX → FalkorDB, ~200-1000 Nodes)│
│                                                                  │
│  Strategeme, Krisenphasen, BTE-Marker, Akteur-Typen,             │
│  Event-Entity-Graph (live), Region→Symbol Mapping (shared)       │
│  + Vector Index (FalkorDB built-in) fuer semantische Suche       │
└──────────────────────────────────────────────────────────────────┘
```

#### Fast Lane vs. Slow Lane (KG-Wachstum)

| Lane | Inhalt | Quelle | GraphMERT | TTL/Decay |
|------|--------|--------|-----------|-----------|
| **Fast Lane** | Domain C: Geo_Event, Actor, Commodity (Live) | ACLED, GDELT, CrisisWatch (Go) | Nein | TTL, probabilistisch, Temporal Weight Decay |
| **Slow Lane** | Domain A+B: Strategeme, BTE, Krisenphasen | Seed-Dateien, Buch-Extrakte | Ja (Batch-Refinement) | Kein TTL, Confidence Decay (Sek. 9.9) |

**User-KG (M2b):** Kein zweiter „Wahrheits-KG“, sondern **Overlay** ueber Backend. Enthaelt persoenliche Daten (Position, Alert, Overrides). Merge-Layer kombiniert beides; Backend bleibt Source of Truth fuer Domain-Fakten.

#### M2a: Backend Domain-KG (Shared, alle User)

**Was in den KG kommt (drei Domains):**

##### Domain A: Krisenlogik + Spieltheorie (aus GAME_THEORY.md)

```
Nodes:
  Strategem(id, name, typ, kosten, reversibilitaet, zusammenfassung)
  Krisenphase(id, name, typische_dauer, beschreibung)
  Event_Kategorie(id, name, risk_tendency)
  Akteur_Typ(id, name, typische_strategie)
  Signal_Typ(id: cheap_talk | costly_signal | ambiguous)

Edges:
  Strategem --[anwendbar_in]--> Krisenphase
  Strategem --[signal_typ]--> Signal_Typ
  Strategem --[fuehrt_zu]--> Strategem
  Strategem --[kontra]--> Strategem
  Event_Kategorie --[typisches_strategem]--> Strategem
  Akteur_Typ --[spielt_typischerweise]--> Strategem
  Akteur_Typ --[reagiert_auf]--> Event_Kategorie
```

**Quelle:** `docs/books/new/Die 36 Srategeme-ProfRick.md` -- manuell extrahiert und als KG-Seed strukturiert.

##### Domain B: Behavioral Analysis (aus AGENT_ARCHITECTURE.md)

```
Nodes:
  BTE_Marker(id, code, name, drs_punkte, beschreibung, extraktion_methode)
  Behavioral_State(id, name, drs_range_min, drs_range_max, beschreibung)
  Needs_Typ(id: significance | approval | acceptance | strength | pity | safety)
  Decision_Style(id: deviance | novelty | security | affiliation | structure | altruism)
  Influence_Tactic(id, name, beschreibung)

Edges:
  BTE_Marker --[indiziert]--> Behavioral_State
  Behavioral_State --[uebergang_zu {wahrscheinlichkeit}]--> Behavioral_State
  BTE_Marker --[kombination_mit]--> BTE_Marker (erhoehte DRS-Relevanz)
  Needs_Typ --[aeussert_sich_als]--> BTE_Marker
  Decision_Style --[korreliert_mit]--> Needs_Typ
  Influence_Tactic --[aeussert_sich_als]--> BTE_Marker
```

**Quelle:** `docs/books/new/The_Behavior_Ops_Manual_-_Chase_Hughes.md` -- BTE-Tabelle, DRS-Punktesystem, Needs Map, Decision Map (alle in `AGENT_ARCHITECTURE.md` Sek. 4, 8 dokumentiert).

##### Domain C: Live Event-Entity Graph

```
Nodes:
  Geo_Event(id, type, region, severity, timestamp, source)
  Actor(id, name, typ_ref → Akteur_Typ, land)
  Commodity(id, name, symbols[])

Edges:
  Geo_Event --[beteiligt]--> Actor
  Geo_Event --[in_region]--> Region
  Geo_Event --[beeinflusst {kanal, richtung, staerke}]--> Commodity
  Geo_Event --[eskaliert_zu]--> Geo_Event
  Actor --[allianz_mit]--> Actor
  Actor --[konflikt_mit]--> Actor
```

**Quelle:** ACLED, GDELT, CrisisWatch -- automatisch befuellt durch bestehende Connectors. Anders als Domain A+B (statisch, Seed-basiert) waechst Domain C kontinuierlich.

#### M2b: Frontend User-KG (Per-User, im Browser)

> **Encryption at Rest:** Der User-KG enthaelt finanziell sensitive Daten (Positionen, Entry-Preise, Groessen). KuzuDB WASM hat keine eingebaute Verschluesselung. Die gesamte IDBFS-Persistenz wird deshalb durch einen Encryption-Layer geschuetzt: WebAuthn PRF-derived Key (primary) oder Server-derived Key (fallback). Details: [`CLIENT_DATA_ENCRYPTION.md`](./specs/security/CLIENT_DATA_ENCRYPTION.md).

```
Nodes:
  Position(symbol_id, size, entry_price, sektor, asset_class)
  Watchlist_Item(symbol_id, gruppe, hinzugefuegt_am)
  Alert(id, symbol_id, condition, threshold, status)
  Journal_Entry(id, symbol_id, datum, richtung, outcome, tags[])
  Geo_Drawing(id, typ, region_id, notiz)
  User_Override(id, candidate_id, action: accept|reject|snooze, grund)

Edges:
  Position --[exposed_to]--> Region          (aus Backend Region→Symbol Mapping abgeleitet)
  Position --[korreliert_beobachtet]--> Position  (User-definiert oder aus Journal abgeleitet)
  Alert --[ueberwacht]--> Position
  Journal_Entry --[betraf]--> Position
  Journal_Entry --[waehrend]--> Geo_Event    (Kontext-Link zum Backend-KG)
  Geo_Drawing --[annotiert]--> Region
  User_Override --[betraf]--> Geo_Event      (Feedback-Link zum Backend-KG)
```

**Persistenz-Stack (von innen nach aussen):**

```
KuzuDB WASM (Klartext im Memory, Cypher Queries)
    │
    ▼ write / read
KGEncryptionLayer (AES-256-GCM)
    │  Key: PRF-derived (primary) oder Server-derived (fallback)
    │  Nonce: 12 Byte, pro Write zufaellig
    ▼
IndexedDB / IDBFS (verschluesselte Blobs)
    │  Zusaetzlich: Non-extractable CryptoKey (OS-Keychain)
    ▼
Disk (doppelt verschluesselt, nutzlos ohne Passkey/Auth)
```

**Sync-Strategie Frontend ↔ Backend:**

```
INITIAL LOAD (App-Start / Login):
  1. Auth: Passkey-Login → PRF-Seed oder Server-Key holen
  2. KG-Key ableiten (HKDF oder AES-KW-Unwrap)
  3. IndexedDB entschluesseln → KuzuDB WASM laden
  4. Backend → Frontend:
     - Region→Symbol Mapping Subset (~50 Nodes) aus Domain-KG
     - User-Daten aus Prisma (Positionen, Alerts, Journal)
     → Frontend aktualisiert User-KG

LAUFEND (SSE, bestehende Streaming-Architektur):
  Backend → Frontend:
    - Neue Event-Entity Links ("Iran-Sanctions → Region MENA")
    - KG-Schema-Updates (selten, nur bei Seed-Aenderungen)

MERGE-QUERIES (bei Bedarf, API-Call):
  Frontend → Backend:
    - "Mein Portfolio [Symbol-IDs] + Backend-KG: Impact-Analyse?"
    - Backend sieht nur Symbol-IDs, nicht Portfolio-Struktur/Groessen
  Backend → Frontend:
    - Angereicherte Antwort: Kausalketten, Strategem-Matches, historische Parallelen

PERSIST (periodisch / bei Aenderung):
  Frontend User-KG → verschluesselt in IndexedDB (ueberlebt Browser-Restart)
  Server-Backup: Verschluesselte KG-Kopie an Backend (fuer Key-Recovery)

LOGOUT / TAB-CLOSE:
  1. Letzte Aenderungen verschluesseln und in IndexedDB persistieren
  2. KG-Key aus Memory loeschen
  3. KuzuDB WASM Instance entladen
```

#### Technologie-Entscheidung

| Schicht | Prototyp | Produktion | Begruendung |
|---|---|---|---|
| **Backend Domain-KG** | NetworkX (Python in-memory) | **FalkorDB** | Redis-kompatibel (passt zu M1), Cypher-Query, **built-in Vector Index** (vereinfacht M4), Graph + Vector in einer DB |
| **Frontend User-KG** | KuzuDB WASM | KuzuDB WASM | Eingebetteter Graph im Browser, Cypher-Query, persistiert in IndexedDB, ~50-500 Nodes passt locker |

**Warum FalkorDB statt Neo4j (Backend):**
- Redis-Protokoll-kompatibel -- laesst sich neben dem M1-Redis betreiben oder sogar als Redis-Modul laden
- Built-in Vector Index -- Graph-Queries UND semantische Suche in einer DB, reduziert Infra-Komplexitaet (siehe M4)
- Cypher-kompatibel -- gleiche Query-Sprache wie KuzuDB WASM im Frontend
- Leichtgewichtiger als Neo4j, kein separater JVM-Prozess

**Warum KuzuDB WASM (Frontend):**
- Laeuft komplett im Browser, kein Server noetig
- Cypher-Query-Language (gleiche Sprache wie FalkorDB Backend → Code-Sharing moeglich)
- Persistent ueber IndexedDB (mit AES-256-GCM Encryption Layer, siehe [`CLIENT_DATA_ENCRYPTION.md`](./specs/security/CLIENT_DATA_ENCRYPTION.md))
- Inspiriert von [GitNexus](https://github.com/abhigyanpatwari/GitNexus)-Architektur (KuzuDB native CLI + KuzuDB WASM Web UI). Architektur-Referenz fuer Frontend User-KG; Schema anpassen (Trading/Geo statt Code)

**Empfehlung:** NetworkX-Prototyp in Python fuer Backend (laden aus YAML/JSON-Seed-Dateien). Parallel KuzuDB WASM im Frontend fuer User-KG. Backend-Migration zu FalkorDB wenn NetworkX-Prototyp validiert ist.

**Abhaengigkeit:** Unabhaengig von M1. Kann parallel gebaut werden. M2b (Frontend) ist unabhaengig von M2a (Backend) -- kann mit Dummy-Daten starten.

### 5.3 Stufe M3: Episodic Store (Agent-Erfahrung)

> **Frage:** "Was hat das System in der Vergangenheit getan und war es richtig?"

**Was gespeichert wird:**

```
analysis_log:
  id: uuid
  timestamp: datetime
  event_id: ref -> GeoEventRecord
  agent: "game_theory_scorer_v1" | "bte_extractor" | ...
  input_summary: { region, event_type, fatalities, keywords }
  output: { impact_score: 0.7, market_bias: "risk_off", confidence: 0.62 }
  reasoning: [ "fatalities_high +0.25", "kinetic_escalation +0.22", ... ]
  market_reaction: { symbol: "GLD", t+1h: +0.8%, t+24h: +2.3% }  # nachtraeglich befuellt
  user_feedback: { override: false }  # aus Candidate Pipeline
  accuracy_score: 0.75  # nachtraeglich berechnet
```

**Erweiterung fuer Orchestration-Layer (AGENT_ARCHITECTURE.md Teil II, Sek. 12-13):**

Die neuen Agent-Rollen (Router, Planner, Orchestrator, Research Agent, Knowledge Synthesizer, Evaluator, Monitor) erzeugen zusaetzliche Episodic-Eintraege:

```
routing_log:
  id: uuid
  timestamp: datetime
  request_summary: str               # Was der User/System angefragt hat
  routing_decision: RoutingDecision   # JSON: task_type, complexity, pipelines, model_tier
  planner_invoked: bool
  total_estimated_cost: float
  actual_cost: float                  # nachtraeglich befuellt
  actual_duration_ms: int             # nachtraeglich befuellt

workflow_log:
  id: uuid
  timestamp: datetime
  routing_log_id: ref -> routing_log
  execution_plan: ExecutionPlan       # JSON: Steps, DAG, Parallelisierung
  step_results: list[StepResult]      # Pro Step: Status, Dauer, Tokens, Kosten, Fehler
  workflow_status: "complete" | "failed" | "partial"
  partial_results_delivered: bool     # Wurden Partial Results via SSE gestreamt?

research_log:
  id: uuid
  timestamp: datetime
  workflow_log_id: ref -> workflow_log
  query: str
  sources_consulted: list[str]        # ["episodic_m3", "vector_m4", "sec_edgar", ...]
  findings_count: int
  gaps: list[str]                     # Was konnte nicht gefunden werden
  confidence: float

evaluation_log:
  id: uuid
  timestamp: datetime
  workflow_log_id: ref -> workflow_log
  quality_score: float
  issues_found: int
  corrections_applied: int
  recommendation: "publish" | "revise" | "flag_for_human"
```

**Nutzen der erweiterten Logs:**
- **Kosten-Tracking:** routing_log + workflow_log ermoeglicht Kosten-pro-Analyse und Kosten-pro-Agent Reporting (Monitor Agent, AGENT_ARCHITECTURE Sek. 13.4)
- **Planner-Optimierung:** Vergleich estimated_cost vs. actual_cost zeigt ob der Planner gut schaetzt
- **Research-Gap-Analyse:** research_log.gaps zeigt systematische Luecken in den Datenquellen
- **Evaluator-Kalibrierung:** evaluation_log vs. user_feedback (Override-Rate) zeigt ob der Evaluator gut kalibriert ist

**Wozu:** 
- Backtesting (`GAME_THEORY.md` Sek. 5.1): "Stimmen Scores mit Marktreaktionen ueberein?"
- Concept Drift Detection (`Advanced-architecture-for-the-future.md` Sek. 4.7.1): "Werden Override-Raten hoeher?"
- Agent Self-Improvement: "Bei MENA/Sanctions-Events bin ich systematisch zu konservativ"
- **Orchestration-Optimierung** (`AGENT_ARCHITECTURE.md` Sek. 12): "Welche Routing-Entscheidungen fuehren zu den besten Ergebnissen?"
- **Monitor-Metriken** (`AGENT_ARCHITECTURE.md` Sek. 13.4): Alle sieben Monitoring-Dimensionen (Entropy, Override-Rate, Rejection-Rate, Latenz, Kosten, Divergenz, Concept Drift) werden aus diesen Logs berechnet

**Technologie:** PostgreSQL (langfristig) oder SQLite-Erweiterung des bestehenden Prisma-Schemas (kurzfristig).

**Abhaengigkeit:** M1 (Redis) fuer effizientes Nachschlagen. Sinnvollerweise nach oder parallel zu Game Theory v2 (Backtesting). Orchestration-Logs (routing_log, workflow_log) kommen mit Phase 7b+ (AGENT_ARCHITECTURE Sek. 16).

### 5.4 Stufe M4: Vector Store + RAG Pipeline

> **Frage:** "Wie finden wir relevante Hintergrund-Information zu einem aktuellen Event?"

**Aladdin-Gap (Vector/RAG):** Vector Store für Recall, semantische Suche, Agent-Portfolio-Berichte. OSS-Optionen: ChromaDB, sentence-transformers (bereits in deps), Hybrid-Retrieval. Priorität: Niedrig. Siehe auch ai_retrieval_knowledge_infra_full.md §20 (LangChain, LlamaIndex).

**Was embedded wird:**

| Datentyp | Quelle | Update-Frequenz | Embedding-Modell |
|---|---|---|---|
| Geopolitische Events | ACLED, CrisisWatch, GDELT | Taeglich | `all-MiniLM-L6-v2` (Leichtgewicht) oder `bge-large-en-v1.5` |
| Nachrichten-Headlines | News Aggregator | Alle 2 Min | Gleich |
| BIS Zentralbank-Reden | BIS API | Wochentlich (Bulk-Archiv) | Gleich |
| Earnings Call Transcripts | EarningsCall.biz / SEC | Quartalsweise | Domain-spezifisch: `FinBERT` Embedding |
| Buch-Extrakte (Referenzwissen) | Lokale Markdown-Files | Einmalig + Updates | Gleich |
| News, Papers, OSINT (optional) | Diverse | Variabel | **MrBERT** (MRL: 128/512/1024 dims je nach Latenz-Budget) |

**MrBERT ([arXiv:2602.21379](https://arxiv.org/abs/2602.21379)):** Multilingual Encoder mit Matryoshka Representation Learning (MRL). Ermoeglicht dynamische Embedding-Dimensionen (z.B. 128 fuer schnelle Suche, 1024 fuer Re-Ranking) ohne Retraining. Domain-adaptiert fuer Legal/Biomed; fuer Finance/Geo eigener CPT-Schritt sinnvoll. HuggingFace: [BSC-LT/MrBERT](https://huggingface.co/BSC-LT/MrBERT) (Modellfamilie: MrBERT, MrBERT-biomed, MrBERT-legal, MrBERT-es, MrBERT-ca).

**RAG-Pipeline:**

```
User/Agent Query
    │
    ├─→ Knowledge Graph (M2): Strukturierte Fakten
    │     "Welche Strategeme passen zu Sanctions?"
    │     → Exakte Antwort via Graph-Query
    │
    ├─→ Vector Store (M4): Aehnliche Dokumente
    │     "Was passierte bei aehnlichen Iran-Sanktions-Events?"
    │     → Top-K aehnliche Events + Kontext
    │
    └─→ LLM Context Window (M5): Synthese
          KG-Fakten + Retrieved Documents + Aktueller Event
          → Strukturierte Analyse
```

**Technologie:** Durch die Wahl von **FalkorDB** in M2a entfaellt die Notwendigkeit eines separaten Vector Stores fuer den Backend. FalkorDB bietet einen built-in Vector Index, der Graph-Queries und semantische Suche in einer DB vereint. Das bedeutet:

- **Graph-Query:** `MATCH (e:Event)-[:in_region]->(r:Region {name:"MENA"}) RETURN e` (exakt, strukturiert)
- **Vector-Query:** `CALL db.idx.vector.queryNodes('event_embeddings', $embedding, 10)` (semantisch, aehnlich)
- **Hybrid:** Beide kombinierbar in einer Cypher-Query -- kein Glue-Code zwischen zwei Systemen

Die leere ChromaDB-Datei (`chroma_data/chroma.sqlite3`) wird nicht weiter verfolgt. Fuer den **Prototyp** (solange NetworkX das Backend-KG ist) kann ChromaDB als temporaerer Vector Store dienen, wird aber bei der FalkorDB-Migration obsolet.

| Phase | Graph | Vector | Systeme |
|---|---|---|---|
| Prototyp | NetworkX | ChromaDB (temporaer) | 2 separate |
| Produktion | FalkorDB | FalkorDB Vector Index | 1 unified |

Kein Pinecone/Weaviate (Cloud-Lock-in vermeiden).

#### Dokumenten-Import für RAG (MarkItDown)

**MarkItDown** (Microsoft, Apache 2.0) konvertiert PDF, DOCX, PPTX, XLSX, Bilder (OCR), Audio (Transkription) zu Markdown – token-effizient für LLMs. MCP-Server verfügbar.

- **Einsatz:** Research-Reports, PDF-Analysen, Excel-Daten vor Embedding
- **Quelle:** [microsoft/markitdown](https://github.com/microsoft/markitdown)

#### Agentic Storage Pattern (ClawVault)

**ClawVault** ist als Pattern-Referenz fuer agentische Workspace-Persistenz
interessant (zustandsbehaftete Arbeitsartefakte, Resume-orientierte Ablage),
aber kein direkter Runtime-Standard fuer den Produktkern.

- **Einsatz fuer uns:** Pattern-Quelle fuer versionierte Agent-Artefakte, nicht
  als blindes Framework-Adopt.
- **Fokus:** Write-Path-Disziplin (`draft/review/approved/published`),
  Auditierbarkeit, kontrollierte Persistenz.
- **Quelle:** [Versatly/clawvault](https://github.com/Versatly/clawvault)

**Abhaengigkeit:** M2a (Backend-KG) sollte vorher oder parallel stehen, damit RAG Fakten-Retrieval und Semantik-Retrieval trennen kann. LLM-Integration (M5) muss zumindest prototypisch vorhanden sein.

### 5.5 Stufe M5: Agent Working Memory (Context Management)

> **Frage:** "Wie managen wir was ein LLM-Agent gerade 'weiss' und was nicht?"

**Problem:** LLMs haben begrenzte Context Windows. Ein Agent der einen Earnings Call analysiert kann nicht gleichzeitig alle historischen Calls, alle BTE-Marker-Definitionen und den aktuellen Marktkontext im Window haben.

**Loesung: Dynamisches Context Assembly**

```
┌─────────────────────────────────────────────┐
│  CONTEXT ASSEMBLER                          │
│                                             │
│  Input: Task Description + Entity IDs       │
│                                             │
│  1. System Prompt (fix, ~500 Tokens)        │
│     - Agent-Rolle, Output-Format, Guards    │
│                                             │
│  2. KG-Slice (M2, ~500-1000 Tokens)         │
│     - Nur relevante Nodes/Edges             │
│     - "BTE-Marker fuer Evasive State"       │
│                                             │
│  3. Retrieved Context (M4, ~2000 Tokens)    │
│     - Top-3 aehnliche historische Events    │
│     - Relevante Buch-Passagen              │
│                                             │
│  4. Episodic Context (M3, ~500 Tokens)      │
│     - Letzte Analyse desselben Akteurs     │
│     - Letzte Analyse derselben Region      │
│                                             │
│  5. Current Input (~1000-5000 Tokens)        │
│     - Aktueller Text / Event / Transcript  │
│                                             │
│  = Assembled Context (4500-8000 Tokens)     │
│  → Passt in jedes moderne LLM              │
└─────────────────────────────────────────────┘
```

**Token-Budget pro Schicht:**

| Schicht | Max Tokens | Strategie bei Ueberschreitung |
|---|---|---|
| System Prompt | 500 | Fix, nicht komprimierbar |
| KG-Slice | 1000 | Nur Nodes mit Distanz <= 2 von Query |
| Retrieved Context | 2000 | Top-K mit Relevance Cutoff |
| Episodic Context | 500 | Nur letztes Matching-Event |
| Current Input | 5000 | Chunking + Zusammenfassung bei laengeren Texten |
| **Gesamt** | **9000** | Passt in 16K-128K Context Windows |

**Context Compaction (ReMe, OpenClaw):** Bei langen Agent-Sessions naehert sich der Kontext dem Limit. *Compaction* (nicht nur Kompression) = Summarisieren + Rehydration (Dateien neu lesen, Todos wiederherstellen, Fortsetzungs-Anweisung). **ReMe** ([agentscope-ai/ReMe](https://github.com/agentscope-ai/ReMe), Apache 2.0) bietet file-based (ReMeLight) und vector-based Memory mit `compact_memory`, `compact_tool_result`, `memory_search`. **Self-hosted:** ReMe/OpenClaw nutzen LLM fuer Summarization – `LLM_BASE_URL` auf Ollama (`http://localhost:11434`) = kein Cloud-API. Siehe `CONTEXT_ENGINEERING.md` Sek. 5.3a.

**Abhaengigkeit:** M2 + M3 + M4 muessen existieren. Das ist die letzte Stufe.

> **Erweiterung (AGENT_ARCHITECTURE.md Teil II):** Das obige Context Assembly beschreibt die vier Pipeline-Rollen (Extractor, Verifier, Guard, Synthesizer). Die erweiterten Agent-Rollen aus Sek. 12-13 haben eigene Memory-Zugriffsmuster:
>
> | Neue Agent-Rolle | M1 | M2a (KG) | M2b (User-KG) | M3 (Episodic) | M4 (Vector) | Schreibend M3 | Besonderheit |
> |---|---|---|---|---|---|---|---|
> | **Router** | Nein | Nein | Nein | Nein | Nein | Nein | Regelbasiert, kein Memory-Zugriff |
> | **Planner** | Ja (Kosten-Check) | Nein | Nein | Ja (aehnliche Workflows) | Nein | Nein | Liest M3 nur fuer Workflow-Erfahrung |
> | **Orchestrator** | Ja | Nein | Nein | Nein | Nein | Ja (workflow_log) | Schreibt Workflow-Trace in M3 |
> | **Research Agent** | Ja | Ja | Nein | Ja | Ja | Ja (research_log) | Vollzugriff M1-M4, schreibt Ergebnisse zurueck |
> | **Knowledge Synthesizer** | Ja | Ja | Nein* | Ja | Ja | Nein | Reichster Lese-Kontext, *User-KG nur mit Policy-Erlaubnis |
> | **Evaluator** | Nein | Ja (Causal-Chain Check) | Nein | Nein | Nein | Ja (evaluation_log) | Prueft Fakten gegen KG |
> | **Monitor** | Ja | Nein | Nein | Ja (Trends) | Nein | Nein | Liest M3-Aggregationen fuer Metriken |
>
> Die detaillierten Memory-Access-Policies sind Teil der Agent Registry (`MemoryAccessPolicy`, AGENT_ARCHITECTURE Sek. 15.1). Die Context-Assembly-Details pro Rolle finden sich in [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md) Sek. 8.

---

## 6. Knowledge Graph im Detail

> Zentrale Referenz fuer die KG-Architektur. Wird von `GAME_THEORY.md` Sek. 8 und `AGENT_ARCHITECTURE.md` referenziert.
> **Zwei-Schichten:** Backend Domain-KG (Sek. 6.1-6.3) ist shared fuer alle User. Frontend User-KG (Sek. 6.4) ist per-User im Browser.

### 6.1 Backend: Vollstaendiges Node-Schema

```yaml
nodes:
  # --- Domain A: Krisenlogik / Spieltheorie ---
  strategem:
    properties: [id, name, nummer, typ, kosten, reversibilitaet, zusammenfassung, buch_kapitel]
    beispiel: { id: "strat_6", name: "Im Osten laermen im Westen angreifen", nummer: 6, typ: "angriff", kosten: "niedrig", reversibilitaet: "ja", zusammenfassung: "Ablenkungsmanoever..." }

  krisenphase:
    properties: [id, name, typische_dauer_tage, beschreibung, volatilitaets_erwartung]
    beispiel: { id: "akut", name: "Akute Krise", typische_dauer_tage: "1-14", volatilitaets_erwartung: "hoch" }

  event_kategorie:
    properties: [id, name, risk_tendency, avg_impact_score, typische_regionen]
    beispiel: { id: "sanctions", name: "Sanctions", risk_tendency: "risk_off", avg_impact_score: 0.65 }

  akteur_typ:
    properties: [id, name, typische_zeithorizont, informationsvorteil]
    beispiel: { id: "zentralbank", name: "Zentralbank", typische_zeithorizont: "langfristig", informationsvorteil: "hoch" }

  signal_typ:
    properties: [id, name, glaubwuerdigkeit]
    werte: [cheap_talk, costly_signal, ambiguous]

  # --- Domain B: Behavioral Analysis ---
  bte_marker:
    properties: [id, code, name, drs_punkte, beschreibung, extraktion_methode, ist_deterministisch]
    beispiel: { id: "115_ne", code: "115", name: "Non-Contracting", drs_punkte: 4.0, extraktion_methode: "regex", ist_deterministisch: true }

  behavioral_state:
    properties: [id, name, drs_range_min, drs_range_max, farbe, beschreibung]
    beispiel: { id: "evasive", name: "Evasive", drs_range_min: 11, drs_range_max: 15, farbe: "#FF0000" }

  needs_typ:
    properties: [id, name, interne_frage, sprachliche_indikatoren, trading_relevanz]
    beispiel: { id: "significance", name: "Significance", interne_frage: "Sehen andere mich als wichtig genug?" }

  decision_style:
    properties: [id, name, frage, sprachliche_indikatoren, trading_relevanz]
    beispiel: { id: "deviance", name: "Deviance", frage: "Hebt mich das ab?" }

  # --- Domain C: Live Event-Entity Graph ---
  geo_event:
    properties: [id, type, region_id, severity, confidence, timestamp, source, embedding]
    beispiel: { id: "evt_20260222_ir_sanc", type: "sanctions", region_id: "mena", severity: 0.7, source: "acled" }

  actor:
    properties: [id, name, akteur_typ_ref, land, aktiv_seit]
    beispiel: { id: "act_us_treasury", name: "US Treasury", akteur_typ_ref: "regierung", land: "US" }

  commodity:
    properties: [id, name, symbols[], sektor]
    beispiel: { id: "crude_oil", name: "Crude Oil", symbols: ["CL", "USO", "BNO"], sektor: "energy" }

  # --- Domain: Geographie (shared, referenced by both Backend + Frontend) ---
  region:
    properties: [id, name, laender]
    beispiel: { id: "mena", name: "Middle East / North Africa", laender: ["IR","IQ","SY",...] }

  symbol:
    properties: [id, name, asset_class, sektor]
    beispiel: { id: "GLD", name: "Gold ETF", asset_class: "commodity", sektor: "precious_metals" }
```

### 6.2 Backend: Vollstaendiges Edge-Schema

```yaml
edges:
  # Strategem-Relationen
  anwendbar_in:      { from: strategem, to: krisenphase, properties: [wirksamkeit] }
  signal_typ:        { from: strategem, to: signal_typ }
  fuehrt_zu:         { from: strategem, to: strategem, properties: [wahrscheinlichkeit] }
  kontra:            { from: strategem, to: strategem }
  typisches_strategem: { from: event_kategorie, to: strategem, properties: [haeufigkeit] }

  # Akteur-Relationen
  spielt_typischerweise: { from: akteur_typ, to: strategem, properties: [kontext] }
  reagiert_auf:          { from: akteur_typ, to: event_kategorie, properties: [typische_reaktion] }
  handelt_symbol:        { from: akteur_typ, to: symbol, properties: [richtung] }

  # Behavioral-Relationen
  indiziert:           { from: bte_marker, to: behavioral_state }
  uebergang_zu:        { from: behavioral_state, to: behavioral_state, properties: [wahrscheinlichkeit, trigger] }
  kombination_mit:     { from: bte_marker, to: bte_marker, properties: [erhoehte_relevanz] }
  aeussert_sich_als:   { from: needs_typ, to: bte_marker }
  korreliert_mit:      { from: decision_style, to: needs_typ, properties: [staerke] }

  # Geographie
  betrifft_region: { from: event_kategorie, to: region, properties: [haeufigkeit] }
  region_mappt_zu: { from: region, to: symbol, properties: [gewichtung, kanal] }

  # Live Event-Entity (Domain C)
  event_beteiligt:     { from: geo_event, to: actor, properties: [rolle] }
  event_in_region:     { from: geo_event, to: region }
  event_beeinflusst:   { from: geo_event, to: commodity, properties: [kanal, richtung, staerke] }
  event_eskaliert_zu:  { from: geo_event, to: geo_event, properties: [zeitabstand_h] }
  actor_allianz:       { from: actor, to: actor, properties: [seit, kontext] }
  actor_konflikt:      { from: actor, to: actor, properties: [seit, kontext] }
  actor_ist_typ:       { from: actor, to: akteur_typ }
  commodity_hat_symbol: { from: commodity, to: symbol }

  # Exergie-Exposure (ENTROPY_NOVELTY.md Sek. 5.6, Keen/Ayres Paper)
  exergy_shock:        { from: geo_event, to: region, properties: [exergy_delta, channel, duration_estimate, keen_multiplier] }
  # exergy_delta: float (-1.0 bis +1.0, relativ zur regionalen Kapazitaet)
  # channel: string ("oil", "gas", "chips", "logistics", "grid", "water")
  # duration_estimate: string ("days", "weeks", "months", "structural")
  # keen_multiplier: float (Faktor um den Standard-Modelle den Impact unterschaetzen, typisch 2-6x)
```

### 6.3 Seed-Daten-Strategie

**Backend Domain-KG (statisch + live):**

| Domain | Quelle | Anzahl Nodes (geschaetzt) | Pflege |
|---|---|---|---|
| 36 Strategeme | `Die 36 Strategeme (Rieck)` | 36 + Relationen | Einmalig, statisch |
| Krisenphasen | Manuell (5-7 Phasen) | 7 | Selten, manuell |
| Event-Kategorien | ACLED-Codes + GDELT EventCodes | ~30 | Jaehrlich |
| Akteur-Typen | Manuell + COT-Kategorien | ~10 | Selten |
| BTE-Marker | `Behavior Ops Manual (Chase Hughes)` | ~25 | Statisch (Buch-basiert) |
| Behavioral States | `AGENT_ARCHITECTURE.md` Sek. 4.4 | 5 | Statisch |
| Needs/Decision | `AGENT_ARCHITECTURE.md` Sek. 8 | 12 | Statisch |
| Regionen | `game_theory.py` Mapping | ~15 | Gelegentlich |
| Symbole | Watchlist + Config | ~50 | User-abhaengig |
| **Live Events** | ACLED, GDELT, CrisisWatch Connectors | ~50-200 (rolling window) | Automatisch, taeglich |
| **Akteure** | Aus Events extrahiert + manuell | ~20-100 | Semi-automatisch |
| **Commodities** | Manuell + Symbol-Mapping | ~15 | Gelegentlich |

**Gesamt Backend:** ~300-500 Nodes (statisch) + ~50-200 Live-Nodes. Klein genug fuer NetworkX-Prototyp, skalierbar in FalkorDB.

**GraphMERT (Phase 2):** Nach initialem KG-Aufbau (IE-Pipeline: Entity Linking + Relation Extraction) kann GraphMERT als Batch-Job den Slow-Lane-KG refinieren: Tail-Prediction, strukturelle Validierung, FActScore-Verbesserung. Code: [jha-lab/graphmert_umls](https://github.com/jha-lab/graphmert_umls). Owner bleibt dieses Dokument; kein allgemeiner `references/projects/evaluate.md`-Kandidat mehr.

**IE-Pipeline (Entity Linking, Relation Extraction):** Fuer spaetere Erweiterung: ReLiK (Entity Linking + Relation Extraction), SapBERT (biomed/UMLS), Fin-E5 (Finance-Embeddings, FinMTEB). Bei Konkretisierung der IE-Pipeline in REFERENCE_PROJECTS ergaenzen.

**Ontologie-Quellen:** Formales Schema (Klassen, IDs, Relationen) aus FIBO, Wikidata, GLEIF LEI, OpenFIGI, OpenSanctions. Domain-Docs (`GAME_THEORY.md`, `POLITICAL_ECONOMY_KNOWLEDGE.md`) liefern Semantik, nicht das Schema. Details: [`archive/KG_ONTOLOGY.md`](./archive/KG_ONTOLOGY.md).

### 6.4 Frontend: User-KG Node- und Edge-Schema

> Per-User Graph im Browser (KuzuDB WASM). Wird bei App-Start aus Prisma-Daten + Backend-Subset aufgebaut.

```yaml
nodes:
  # --- User-spezifische Entities ---
  position:
    properties: [symbol_id, size, entry_price, sektor, asset_class, offen_seit]
    beispiel: { symbol_id: "XOM", size: 50, entry_price: 112.30, sektor: "energy", offen_seit: "2026-01-15" }

  watchlist_item:
    properties: [symbol_id, gruppe, hinzugefuegt_am]
    beispiel: { symbol_id: "AAPL", gruppe: "tech_watch", hinzugefuegt_am: "2026-02-01" }

  alert:
    properties: [id, symbol_id, condition, threshold, status, erstellt_am]
    beispiel: { id: "alert_1", symbol_id: "GLD", condition: "crosses_above", threshold: 2100, status: "active" }

  journal_entry:
    properties: [id, symbol_id, datum, richtung, outcome_pct, tags[], notiz]
    beispiel: { id: "je_42", symbol_id: "XOM", datum: "2026-02-10", richtung: "long", outcome_pct: 3.2, tags: ["energy","geopolitik"] }

  geo_drawing:
    properties: [id, typ, region_id, notiz, erstellt_am]
    beispiel: { id: "draw_7", typ: "polygon", region_id: "mena", notiz: "Eskalationszone beobachten" }

  user_override:
    properties: [id, candidate_id, action, grund, timestamp]
    beispiel: { id: "ov_3", candidate_id: "cand_iran_22", action: "reject", grund: "false positive" }

  # --- Subset aus Backend (read-only im Frontend, via Sync) ---
  region:
    properties: [id, name]    # Lightweight-Kopie, ohne laender-Array

  symbol:
    properties: [id, name, asset_class, sektor]

edges:
  # User-Portfolio-Relationen
  position_exposed_to:    { from: position, to: region, properties: [kanal] }
  position_korreliert:    { from: position, to: position, properties: [beobachtet_am, notiz] }
  alert_ueberwacht:       { from: alert, to: position }

  # Journal-Relationen
  journal_betraf:         { from: journal_entry, to: position }
  journal_waehrend:       { from: journal_entry, to: geo_event_ref, properties: [event_id] }
  journal_tag_cluster:    { from: journal_entry, to: journal_entry, properties: [shared_tag] }

  # Annotation-Relationen
  drawing_annotiert:      { from: geo_drawing, to: region }
  override_betraf_event:  { from: user_override, to: geo_event_ref, properties: [event_id] }

  # Watchlist-Relationen
  watchlist_beobachtet:   { from: watchlist_item, to: symbol }
```

**Gesamt Frontend:** ~50-500 Nodes pro User. Kein Performance-Problem fuer KuzuDB WASM.

**Hinweis zu `geo_event_ref`:** Das Frontend speichert keine vollen Event-Nodes, sondern nur Referenz-IDs (`event_id`). Bei Bedarf wird der volle Event-Kontext ueber eine Merge-Query vom Backend-KG geholt. Das haelt den Frontend-KG schlank und vermeidet Daten-Duplikation.

---

## 7. Architektur-Ueberblick: Alle Schichten zusammen

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                           │
│                                                                      │
│  TanStack Query ──────── Client-Side Cache (staleTime, gcTime)      │
│  Zustand ─────────────── UI State (nicht persistent)                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  USER-KG (KuzuDB WASM, per-User)                     ← M2b   │  │
│  │                                                               │  │
│  │  Portfolio ── Positionen, Alerts, Watchlists                  │  │
│  │  Journal ──── Trade-Eintraege, Tags, Outcomes                 │  │
│  │  Geo ──────── Drawings, Overrides, Annotationen               │  │
│  │  Sync-Subset: Region→Symbol Mapping (read-only aus Backend)   │  │
│  │                                                               │  │
│  │  Persist: IndexedDB (ueberlebt Browser-Restart)               │  │
│  └──────────────────────────┬─────────────────────────────────────┘  │
│                              │                                       │
│  fetch /api/* ───────────────┤ SSE ↓ (Event-Updates, KG-Sync)       │
│  Merge-Queries ──────────────┘ API ↑ (Impact-Anfragen)              │
└──────────────────────────────────────────────────────────────────────┘
                                                                  │
┌─────────────────────────────────────────────────────────────────│────┐
│                   API LAYER (Next.js Routes)                    │    │
│                                                                 │    │
│  TS Bridges ─────── Redis (M1) ← statt Map<>                   │    │
│  Merge-Endpoint ─── Frontend-KG + Backend-KG Queries verbinden  │    │
│                        │                                         │    │
│                        │ pub/sub                                 │    │
│                        ▼                                         │    │
│  ┌─────────────────────────────────────┐                        │    │
│  │  GO GATEWAY (Port 8080)             │                        │    │
│  │                                     │                        │    │
│  │  Redis Client ─── Shared Cache      │                        │    │
│  │  HTTP → Python Services             │                        │    │
│  └──────────────────┬──────────────────┘                        │    │
│                     │                                            │    │
│  ┌──────────────────▼──────────────────────────────────────┐    │    │
│  │  PYTHON SERVICES                                        │    │    │
│  │                                                         │    │    │
│  │  ┌─────────────────┐  ┌──────────────────┐             │    │    │
│  │  │ Game Theory v1  │  │ Soft Signals     │             │    │    │
│  │  │ (Port 8092)     │  │ (Port 8091)      │             │    │    │
│  │  └────────┬────────┘  └────────┬─────────┘             │    │    │
│  │           │                    │                        │    │    │
│  │           └────────┬───────────┘                        │    │    │
│  │                    │                                     │    │    │
│  │                    ▼                                     │    │    │
│  │  ┌────────────────────────────────────────────────┐    │    │    │
│  │  │  MEMORY LAYER                                  │    │    │    │
│  │  │                                                │    │    │    │
│  │  │  Redis ──────── Working Memory                 │ M1 │    │    │
│  │  │  FalkorDB ───── Domain-KG + Vector Index       │ M2a│    │    │
│  │  │                 (Prototyp: NetworkX + ChromaDB) │    │    │    │
│  │  │  Postgres ───── Episodic Memory                │ M3 │    │    │
│  │  │  Assembler ──── Context Window                 │ M5 │    │    │
│  │  │                                                │    │    │    │
│  │  └────────────────────────────────────────────────┘    │    │    │
│  └─────────────────────────────────────────────────────────┘    │    │
└──────────────────────────────────────────────────────────────────┘    │
```

**Datenfluss bei einer typischen Merge-Query:**

```
User klickt auf Iran-Sanctions Event in GeoMap
    │
    ├─→ Frontend User-KG (lokal, <1ms):
    │     MATCH (p:Position)-[:exposed_to]->(r:Region {id:"mena"}) RETURN p
    │     → User hat XOM, CVX, GLD (Energie + Gold exposed)
    │
    ├─→ Backend Domain-KG (API-Call, ~50ms):
    │     MATCH (e:GeoEvent {id:"evt_iran_sanc"})-[:beeinflusst]->(c:Commodity)-[:hat_symbol]->(s:Symbol)
    │     → Iran-Sanctions → Crude Oil → CL, USO; → Gold → GLD
    │     + Strategem-Match: Strat 28 (Auf das Dach locken, Leiter wegziehen)
    │     + Vector-Search: Top-3 aehnliche historische Sanktions-Events
    │
    └─→ Merge im Frontend:
          User-Positionen ∩ Backend-Impact = XOM (Energie), GLD (Gold) sind betroffen
          → Personalisierte Impact-Anzeige mit Strategem-Kontext + historischen Parallelen
```

---

## 8. Querverweise

| Dieses Dokument | Bestehendes Dokument | Verbindung |
|---|---|---|
| Sek. 3.1 (Working Memory) | [`INDICATOR_ARCHITECTURE.md`](./INDICATOR_ARCHITECTURE.md) Sek. 0.3-0.7 | Redis Cache Key Schema + TTL Policies |
| Sek. 5.2 + 6 (Knowledge Graph) | [`GAME_THEORY.md`](./GAME_THEORY.md) Sek. 8 | KG-Begruendung (Vector DB vs. KG) + Strategeme-Schema |
| Sek. 5.2 + 6 (Knowledge Graph) | [`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 4, 8 | BTE/DRS-Marker + Needs/Decision Map als KG-Nodes |
| Sek. 5.3 (Episodic) | [`GAME_THEORY.md`](./GAME_THEORY.md) Sek. 5.1 | Backtesting = erste Episodic-Memory-Nutzung |
| Sek. 5.3 (Episodic) | [`Advanced-architecture-for-the-future.md`](./Advanced-architecture-for-the-future.md) Sek. 4.7.1 | Concept Drift Detection via Override-Tracking |
| Sek. 5.3 (Episodic) | [`GEOMAP_OVERVIEW.md`](./specs/geo/GEOMAP_OVERVIEW.md) Sek. 5.4 | Candidate accept/reject Feedback Loop |
| Sek. 5.4 (Vector Store) | [`Advanced-architecture-for-the-future.md`](./Advanced-architecture-for-the-future.md) Sek. 7 | RAG fuer Trading-Knowledge |
| Sek. 5.2 + 5.4 (Hybrid Retrieval) | [`RAG_GRAPHRAG_STRATEGY_2026.md`](./RAG_GRAPHRAG_STRATEGY_2026.md) | Decision-Matrix fuer Vector/KG/SQL, Rerank-Baseline, GraphRAG-Differenzierung |
| Sek. 10.6 (Source Persistence) | [`specs/execution/source_persistence_snapshot_delta.md`](./specs/execution/source_persistence_snapshot_delta.md) | Raw snapshot/cache/normalize Grenze vor Memory-Ingestion |
| Sek. 10.6 (Vector Ingestion) | [`specs/execution/vector_ingestion_delta.md`](./specs/execution/vector_ingestion_delta.md) | Embedding-/Provenance-Vertrag fuer Retrieval-faehige Artefakte |
| Sek. 5.5 (Working Memory) | [`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 2 | Vier Pipeline-Agent-Rollen brauchen Context Assembly |
| **Sek. 5.3 (M3 Erweiterung)** | **[`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 12-13** | **routing_log, workflow_log, research_log, evaluation_log fuer Orchestration-Layer + neue Rollen** |
| **Sek. 5.5 (M5 Erweiterung)** | **[`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 15.1** | **MemoryAccessPolicy in Agent Registry steuert welcher Agent welche Memory-Schichten lesen/schreiben darf** |
| **Sek. 5.5 (M5 Erweiterung)** | **[`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 13.4** | **Monitor Agent aggregiert M3-Logs fuer sieben Monitoring-Dimensionen (Entropy, Override-Rate, etc.)** |
| Sek. 7 (Architektur) | [`RUST_LANGUAGE_IMPLEMENTATION.md`](./RUST_LANGUAGE_IMPLEMENTATION.md) Sek. 5b | redb OHLCV-Cache (Rust-spezifisch, komplementaer zu Redis) |
| Sek. 5.2 M2b (Frontend User-KG) | [`GEOMAP_OVERVIEW.md`](./specs/geo/GEOMAP_OVERVIEW.md) Sek. 35.8 | TS In-Memory Entity Graph → wird durch KuzuDB WASM User-KG ersetzt |
| Sek. 5.2 + 6 (KG Gesamtbild, Geo-Spezialisierung) | [`geo/GEOMAP_ONTOLOGY_GRAPH_RUNTIME.md`](./geo/GEOMAP_ONTOLOGY_GRAPH_RUNTIME.md) | Geo-Ontologie/Graph/Search-Around/Track/Writeback werden als Geo-Owner auf derselben KG-Gesamtarchitektur gefuehrt (nicht isoliert) |
| Sek. 5.2 M2b (Encryption) | [`CLIENT_DATA_ENCRYPTION.md`](./specs/security/CLIENT_DATA_ENCRYPTION.md) | Client-Side Data Encryption: WebAuthn PRF + Server-Fallback, AES-256-GCM auf IDBFS |
| Sek. 5.2 (GraphRAG, Embedding Limits) | [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md) + zitierte CE-2.0-Papers | CE 2.0 Validierung: Formaler Beweis KG > Vector, GraphRAG Terminologie |
| Sek. 9.8 (Self-Baking) | [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md) | CE 2.0 Konzept: Episodic→Semantic Verdichtung |
| Sek. 9.7 (Memory vs. Context) | [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md) | Context Assembly, Retrieval-Policies, Token-Budgets (separates Dokument) |

---

## 9. Offene Fragen

### 9.1 SQLite → PostgreSQL: Wann migrieren?

Aktuell: Prisma/SQLite reicht fuer Single-User. PostgreSQL wird noetig sobald:
- Mehrere User gleichzeitig (Multi-Tenancy)
- Episodic Memory Queries (Aggregationen, Zeitreihen-Analyse)
- Full-Text-Search auf Events/Transcripts

**Empfehlung:** Bei M3 (Episodic Store) auf PostgreSQL wechseln. Prisma unterstuetzt beide -- Migration ist Schema-Change + Connection-String.
**Review-Ergaenzung:** PostgreSQL als zentrales SoR (tenanting via `user_id`/`profile_key`) priorisieren; "pro User eigene DB" nur bei harten Isolationsanforderungen.

### 9.2 KG-Technologie: NetworkX → FalkorDB (Backend) + KuzuDB WASM (Frontend) ✅ Entschieden

**Backend:** NetworkX bleibt Prototyp. Produktions-Migration geht zu **FalkorDB** (nicht Neo4j). Begruendung:
- Redis-Protokoll-kompatibel (passt zu M1-Infrastruktur)
- Built-in Vector Index (Graph + Vector in einer DB → M4 wird vereinfacht)
- Cypher-kompatibel, leichtgewichtiger als Neo4j (kein JVM)
- Migrations-Trigger: >1000 Nodes ODER Bedarf an persistenten Queries ODER Vector-Search noetig

**Frontend:** KuzuDB WASM fuer den per-User Knowledge Graph im Browser. Cypher-kompatibel (Code-Sharing mit Backend-Queries moeglich). Persistiert ueber IndexedDB.

Siehe Sek. 5.2 fuer die vollstaendige Zwei-Schichten-Architektur.

### 9.3 Vector Store: In FalkorDB integriert ✅ Entschieden

Separate Vector DB (ChromaDB/Qdrant) wird langfristig nicht benoetigt. FalkorDB bietet einen built-in Vector Index, der Graph-Queries und semantische Suche in einer DB vereint. Fuer den **Prototyp** (solange NetworkX das Backend ist) kann ChromaDB als temporaerer Vector Store dienen. Bei FalkorDB-Migration wird ChromaDB obsolet. Siehe Sek. 5.4.

### 9.4 Redis: Managed vs. Self-Hosted

Entwicklung: Docker Redis (kein Overhead). Produktion: Abhaengig von Deployment-Strategie (noch nicht definiert).

**Review-Ergaenzung (SOTA 2026, Empfehlung):**
- Primärpfad: Redis oder Valkey als shared hot cache.
- No-Docker Dev-Fallback zulassen:
  1. nativer lokaler Service (Redis/Valkey Binary), oder
  2. in-process Cache + optional persistenter local Adapter (SQLite/redb).
- Staging/Prod: externer Cache verpflichtend, in-process nur kontrollierte Notfall-Degradation.
- Konfigurationsziel: `CACHE_PROVIDER=redis|valkey|local`.

### 9.5 Stufenplan-Reihenfolge

**Empfohlene Reihenfolge:** M1 → M2a → M2b → M3 → M4 → M5

M1 (Redis) ist Infrastruktur-Grundlage. M2a (Backend-KG) und M2b (Frontend User-KG) sind unabhaengig voneinander und von M1 -- koennen parallel gebaut werden. M2b kann mit Dummy-Daten starten, bevor der Backend-KG existiert. M3 braucht M1. M4 wird bei FalkorDB-Migration in M2a absorbiert. M5 braucht alles andere.

**Alternativ (wenn Agenten Prioritaet haben):** M2a → M5 (minimal) → M1 → M2b → M3. Backend-KG zuerst, dann minimales Context Assembly fuer erste Agent-Prototypen, dann Infra und Frontend-KG nachholen.

**Parallelisierung:** M2a (NetworkX-Prototyp) und M2b (KuzuDB WASM) haben keine Abhaengigkeit zueinander. Ein Entwickler kann am Backend-KG arbeiten waehrend ein anderer den Frontend User-KG baut.

### 9.6 Wie passt Game Theory v2 (Backtesting) hier rein?

v2 (Backtesting, `GAME_THEORY.md` Sek. 5.1) ist der **empirische Checkpoint** der die Memory-Architektur treibt:
- v2 erzeugt die ersten Episodic-Memory-Eintraege (Score → Marktreaktion)
- v2 zeigt ob der KG-basierte Scoring besser ist als die Heuristik
- v2 liefert Ground-Truth fuer Vector-Store-Relevance

**Empfehlung:** v2 (Backtesting) und M2a (KG-Prototyp) koennen zeitgleich laufen. v2 benutzt noch die alte Heuristik, M2a baut parallel den KG auf. Zusammenfuehrung in v3.

### 9.7 Abgrenzung: Memory vs. Context

Memory (dieses Dokument) definiert **was gespeichert wird und wo**. Context Engineering (→ [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md)) definiert **was wann fuer wen zusammengestellt wird**. M5 (Context Assembly) ist die Bruecke: es liest aus allen Memory-Schichten und baut daraus den passenden Kontext fuer einen spezifischen Agent/User/Query. Die vollstaendige Context-Strategie -- Retrieval-Policies, Relevance-Scoring, Token-Budgets, Freshness, Multi-Source-Merging -- gehoert in das separate CONTEXT_ENGINEERING.md.

### 9.8 Self-Baking: Episodic (M3) → Semantic (M2a) Verdichtung ✅ Konzept definiert

> **Offene Frage aus 9.6:** "Wie fliesst Episodic-Wissen zurueck in den Knowledge Graph?"
> **Konzept aus CE 2.0 Research:** "Self-Baking" = automatische Verdichtung von rohem Kontext (High-Entropy) in abstrakteres, kompakteres Wissen (Low-Entropy). Quelle: [Context Engineering 2.0](https://arxiv.org/abs/2510.26493); projektnahe Ableitungen dazu stehen in [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md).

**Problem:** Episodic Memory (M3) sammelt Roh-Eintraege (`analysis_log`: Event → Score → Marktreaktion → Override ja/nein). Diese Eintraege sind wertvoll fuer Debugging und Nachvollziehbarkeit, aber zu granular fuer den KG. Ein Agent der "Wie gut sind wir bei MENA-Events?" fragen will, muesste 500+ Episodic-Eintraege durchsuchen statt eine aggregierte Antwort aus dem KG zu bekommen.

**Loesung: Periodischer Baking-Job (M3 → M2a)**

Ein Hintergrund-Job der periodisch Episodic-Eintraege aggregiert und als neue KG-Edges/-Properties in M2a schreibt:

```
┌─────────────────────────────────────────────────────────┐
│  EPISODIC (M3)                                          │
│                                                         │
│  analysis_log Eintraege (roh, granular):                │
│  - evt_iran_01: Score 0.7, GLD +2.3%, Override: nein   │
│  - evt_iran_02: Score 0.6, GLD +0.8%, Override: ja     │
│  - evt_mena_03: Score 0.8, OIL +3.1%, Override: nein   │
│  - ... (500+ Eintraege)                                 │
│                                                         │
└───────────────────────┬─────────────────────────────────┘
                        │ Baking-Job (periodisch)
                        ▼
┌─────────────────────────────────────────────────────────┐
│  DOMAIN-KG (M2a) -- neue/aktualisierte Edges            │
│                                                         │
│  (Region:MENA)-[:accuracy_stats {                       │
│    avg_score: 0.72,                                     │
│    override_rate: 0.15,                                 │
│    avg_market_reaction: +2.1%,                          │
│    sample_size: 47,                                     │
│    last_baked: "2026-02-22T14:00:00Z"                   │
│  }]->(Agent:GameTheoryScorer)                           │
│                                                         │
│  (Symbol:GLD)-[:prediction_bias {                       │
│    direction: "zu_konservativ",                         │
│    avg_delta: -0.8%,                                    │
│    sample_size: 23,                                     │
│    last_baked: "2026-02-22T14:00:00Z"                   │
│  }]->(Region:MENA)                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 9.9 Rollenabgrenzung der Speicherschichten (Review-Klarstellung)

- **Postgres:** System of Record fuer persistente Kerndaten + episodic memory.
- **Redis/Valkey:** shared hot cache / short-lived working memory.
- **redb (Rust):** spezialisierter OHLCV/read-through cache im Python-Rust Pfad.
- **Nicht-Ziel:** redb oder Local-Fallbacks als allgemeiner SoR-Ersatz.

**Baking-Regeln:**

| Aggregation | Trigger | KG-Output | Beispiel |
|---|---|---|---|
| Region-Accuracy | ≥ 20 Episodic-Eintraege fuer Region X | `accuracy_stats` Edge | "MENA: 72% avg Score, 15% Override-Rate" |
| Symbol-Prediction-Bias | ≥ 10 Eintraege fuer Symbol Y | `prediction_bias` Edge | "GLD bei MENA-Events: systematisch 0.8% zu konservativ" |
| Strategem-Effectiveness | ≥ 5 Eintraege mit Strategem Z | `strategem_accuracy` Property | "Strategem 28 matcht in 80% korrekt" |
| Override-Pattern | ≥ 3 konsekutive Overrides gleicher Richtung | `override_pattern` Edge | "User ueberschreibt MENA-Scores systematisch nach oben" |

**Frequenz:** Taeglich (Cronjob), oder nach jeder Backtesting-Runde (v2). Kein Real-Time-Bedarf -- Aggregationen aendern sich langsam.

**Was NICHT gebacken wird:**
- Einzelne Episodic-Eintraege bleiben in M3 (Debugging, Audit Trail)
- Baking ist additiv: Neue Edges/Properties werden geschrieben, alte Episodic-Daten nicht geloescht
- Confidence der gebackenen Edges = `sample_size / (sample_size + 10)` (asymptotisch gegen 1.0, konservativ bei wenigen Samples)

**Abhaengigkeit:** M3 (Episodic Store) muss existieren. Erster sinnvoller Einsatz nach Game Theory v2 Backtesting (Sek. 9.6), das die ersten substantiellen Episodic-Eintraege erzeugt.

#### Confidence Dampening Regeln (Entropy-Schutz)

> **Problem (ENTROPY_NOVELTY.md Sek. 4.4):** Ohne Begrenzung werden KG-Edges zur Self-Fulfilling Prophecy: Hohe Confidence → oeftere Aufnahme in Kontext → oeftere Bestaetigung → noch hoehere Confidence. Alternative Kausalketten verblassen.

| Regel | Aktuell | Neu | Begruendung |
|---|---|---|---|
| **Confidence-Increment (korrekte Prediction)** | +0.05 unbegrenzt | **+0.05, Hard Cap bei 0.95** | Kein Edge darf 1.0 erreichen -- das waere absolute Gewissheit. 0.95 laesst Raum fuer Ueberraschungen |
| **Confidence-Decrement (falsche Prediction)** | Nicht definiert | **-0.08** | Asymmetrisch: Fehler reduzieren Confidence schneller als Erfolge sie aufbauen. Verhindert "too confident to challenge" |
| **Baseline Decay (monatlich)** | Nicht definiert | **-0.02/Monat auf alle Edges** | Erzwingt periodische Re-Validierung. Edge mit 0.90 ohne neue Predictions sinkt in 5 Monaten auf 0.80. Strukturelle Edges (z.B. "Oel→Energie") koennen via `is_structural: true` Flag vom Decay ausgenommen werden |
| **Minimum Confidence** | Nicht definiert | **0.10** | Edges unter 0.10 werden nicht geloescht, aber aus Context-Assembly ausgeschlossen (koennen durch neue Validierung wieder steigen) |

**SOTA-Prinzip:** Kanten werden nicht geloescht, sondern per Decay heruntergewichtet. Queries filtern dynamisch nach `confidence` und `timestamp`. Ermoeglicht historische Abfragen („Was war 2024 relevant?“) und vermeidet Informationsverlust.

**Implementation:**
```python
def update_confidence(edge, prediction_correct: bool):
    if prediction_correct:
        edge.confidence = min(edge.confidence + 0.05, 0.95)
    else:
        edge.confidence = max(edge.confidence - 0.08, 0.10)

def monthly_confidence_decay(kg):
    for edge in kg.all_edges():
        if not edge.is_structural:
            edge.confidence = max(edge.confidence - 0.02, 0.10)
```

**Differenzierung nach Edge-Typ (Sek. 9.5 Offene Frage aus ENTROPY_NOVELTY):**
- **Strukturelle Edges** (z.B. `region_mappt_zu`, `commodity_hat_symbol`): Kein Decay, aber Cap bei 0.95
- **Event-basierte Edges** (z.B. `event_beeinflusst`, `actor_konflikt`): Voller Decay (-0.02/Monat)
- **Strategem-Edges** (z.B. `typisches_strategem`, `anwendbar_in`): Halber Decay (-0.01/Monat, da Strategeme langlebiger sind als Events)

**Prioritaet:** HOCH. ~30 LoC, drei einfache Regeln die den KG vor Selbstverstaerkung schuetzen.

---

## 10. Phase-6 Entscheidungen (verbindlich)

### 10.1 ADR: DB-Topologie

**Entscheidung:** Zentrales PostgreSQL mit Tenanting ist der Standardpfad.

- Tenant-Schnitt ueber `user_id` und `profile_key`
- Kein "Postgres pro User" als Default
- SQLite bleibt lokaler Dev-/Bootstrap-Pfad

### 10.2 Verbindliche Speicherrollen

| Speicher | Rolle | Nicht-Ziel |
|---|---|---|
| **Postgres** | System of Record fuer persistente Domaindaten + episodic memory | Kein hot-cache Ersatz |
| **Redis/Valkey** | shared hot cache / working memory mit TTL | Kein langfristiger SoR |
| **redb** | spezialisierter OHLCV/read-through cache im Python-Rust Pfad | Kein allgemeiner Domain-Store |

### 10.3 Cache Provider Strategie (No-Docker kompatibel)

Verbindliche Provider-Auswahl:

```bash
CACHE_PROVIDER=redis|valkey|local
```

- `redis` / `valkey`: Standard in staging/prod
- `local`: nur Dev/Test (explizit degradierter Modus)

### 10.4 Memory-Ownership-Matrix

| Datentyp | Read-Owner | Write-Owner | Source of Truth |
|---|---|---|---|
| Portfolio/Orders/Journal Domaindaten | Go + Next read models | Go mutating APIs | Postgres (prod) / SQLite (local dev) |
| Geo Candidate/Review/Contradiction | Go/UIL APIs | Go/UIL | Go-owned stores + DB |
| Market hot snapshots | Go/Python services | Go/Python cache writers | Redis/Valkey (ephemeral) |
| OHLCV cache artifacts | Python-Rust bridge | Python-Rust bridge | redb (cache only) |
| Agent episodes / workflow logs | Agent services | Agent services | Postgres |
| KG domain facts | Memory services | Memory services | FalkorDB (target) |
| User KG local graph | Frontend (per user) | Frontend (per user) | IndexedDB (encrypted) + optional backup |

### 10.5 CacheAdapter Minimalvertrag

Verbindliches Adapter-Interface (provider-unabhaengig):

```ts
interface CacheAdapter {
  get<T>(key: string): Promise<T | null>;
  set<T>(key: string, value: T, ttlSeconds?: number): Promise<void>;
  del(key: string): Promise<void>;
  ttl(key: string): Promise<number | null>;
  scanPrefix?(prefix: string): Promise<string[]>;
}
```

Pflicht-Telemetrie:

- `cache.provider`
- `cache.hit_rate`
- `cache.fallback_active`
- `cache.errors`

### 10.6 Source Persistence und Vector-Ingestion (verbindliche Abgrenzung)

Memory baut nicht direkt auf ungefilterten Quellen-Rohdaten auf. Dazwischen
liegt eine eigenstaendige Persistence-Stufe:

`source selection -> source onboarding -> fetch/cache/snapshot -> normalize -> memory/vector ingestion`

Arbeitsregel:

- **Raw snapshots** aus `file-snapshot` Quellen gehoeren in den Object Store und
  in einen relationalen Snapshot-Index, nicht direkt in Semantic Memory.
- **API-hot caches** bleiben Working-Memory-/Latency-Layer und werden nicht
  still zum Source of Truth.
- **Vector Ingestion** ist ein downstream consumer normalisierter Artefakte.
  Embeddings duerfen nicht direkt aus ungeprueften ZIP/CSV/XML/JSON-Rohdaten
  entstehen.
- **Semantic Memory** konsumiert entweder strukturierte, normalisierte Fakten
  fuer KG-/Truth-Knoten oder provenance-markierte Textsegmente fuer Retrieval.

Owner fuer diese Zwischenstufen:

- Rohsnapshot-/Persistenzvertrag:
  `docs/specs/execution/source_persistence_snapshot_delta.md`
- Vector-/Embedding-Vertrag:
  `docs/specs/execution/vector_ingestion_delta.md`

---

## 11. Konsolidierungs-Addendum (Merge / Ontologie / Branching)

Dieses Addendum zieht die verbindlichen Kernpunkte aus dem frueheren
`KG_MERGE_AND_OVERLAY_ARCHITECTURE.md` und `KG_ONTOLOGY.md` in die aktive
Memory-Spec.

### 11.1 Overlay ist kein zweiter Truth-KG

- Global Canonical Graph bleibt Domain-Truth.
- User Overlay Graph bleibt privat, local-first und user-owned.
- Merge erfolgt auf Query-Ebene; keine physische DB-Fusion.

### 11.2 Claim/Evidence/Stance als M2/M3-Bruecke

Subjektive oder zeitlich fragile Inhalte werden als Claim-/Evidence-/Stance-
Objekte modelliert, nicht als direkte faktische Kanten im Canonical Graph.

- Claim: These/Interpretation mit Zeitfenster und Confidence
- Evidence: Quelle/Signal/Artefakt als Beleg
- Stance: relationale Einordnung (supports/opposes/refines/hedges)

### 11.3 Namespace- und ID-Regeln

Verbindliche Namespaces fuer Schichttrennung:

- `g:` canonical
- `e:` event
- `u:` user overlay
- `c:` claim/stance
- `x:` evidence
- `s:` simulation branch
- `m:` semantic memory

Canonical-ID-Prioritaet:

1. LEI/FIGI/ISIN/Wikidata QID/formale IDs
2. deterministische interne IDs
3. keine user-generierten Zufalls-IDs fuer globale Fakten

### 11.4 Simulation Branches als separater Layer

Simulation produziert Branch-Artefakte (`s:*`) und darf den Canonical Graph
nicht direkt mutieren.

Persistierbar:

- branch metadata
- outputs/summaries
- optional extrahierte claims/evidence

Nicht als canonical fact persistierbar:

- hypothetische truths/states/edges

### 11.5 User-zentrierter Merge-Query-Ablauf

1. Frontend fragt lokalen Overlay Graph (Positionen/Watchitems/Claims).
2. Frontend sendet minimale IDs/Handles an Merge-Endpoint.
3. Backend liefert Domain-Antwort (KG + optional episodic/vector context).
4. Frontend fusioniert Ergebnis typisiert fuer personalisierte Sicht.

### 11.6 Ontologiequellen fuer M2

Formale Schemaquellen:

- FIBO
- Wikidata
- GLEIF LEI
- OpenFIGI
- OpenSanctions

Domain-Dokumente liefern Semantik, nicht das formale Schema.
