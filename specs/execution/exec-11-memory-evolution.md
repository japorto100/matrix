# exec-11: Memory Engine (Hindsight Integration + Graphiti/Cognee)

**Datum:** 30.03.2026 (Update 31.03.2026)
**Status:** Geplant
**Abhaengig von:** exec-10 (Multi-Agent, LangGraph) ✅
**Referenz-Repos:** `_ref/hindsight` (MIT, 91.4% LongMemEval), `_ref/supermemory` (UI-Referenz)

---

## Kontext

### Warum Hindsight statt Supermemory
- Supermemory: Closed-Source, Self-Host nur via Cloudflare Workers + Enterprise Agreement
- Hindsight: MIT-lizenziert, 91.4% LongMemEval (#1 Open-Source), Python, PostgreSQL+pgvector
- Hindsight hat 4 Memory Networks (World, Experience, Opinion, Entity) — menschenaehnlich
- Repo geklont in `_ref/hindsight/` fuer Referenz

### Architektur-Entscheidung: Option A — pip Package + Extension Points
`hindsight-api-slim` als pip Package installiert (v0.4.21, MIT).
Nicht kopiert, sondern als Library genutzt — Updates via `uv sync`.

**Vorteil:** Kein Maintenance von 56K LOC, Updates via pip, Extension Points vorhanden.
**Erweiterbar via:**
- `GraphRetriever(ABC)` — eigene Graph-Strategien (z.B. GraphitiRetriever)
- `MemoryEngineInterface(ABC)` — eigene Engine-Implementation
- `providers/` — LiteLLM bereits integriert (`litellm_llm.py`)
- `storage/` — S3/GCS/Azure/PostgreSQL Backends

**Extras:**
- Base (installiert): Core Engine, externe Embeddings/Reranker via API
- `[local-ml]`: sentence-transformers + flashrank (lokal, ohne API-Calls) — optional
- `[embedded-db]`: pg0-embedded PostgreSQL — nicht noetig (eigene DB)
- `[all]`: local-ml + embedded-db — crasht auf Windows (mlx/Apple Silicon)

### 3-Layer Memory Architecture (aus exec-10 Recherche)
```
Layer 1: Working Memory (kurzfristig) — LangGraph AgentGraphState (bereits da)
Layer 2: Episodic Memory (mittelfristig) — Hindsight Engine (dieses Slice)
Layer 3: Semantic Memory (langfristig) — Graphiti/Cognee (dieses Slice)
```

### Bereits implementiert (exec-10)
- Skill-basiertes Memory (3-Tier: global/team/personal SKILL.md)
- Trajectory Logging + PRM Scoring
- Auto-Skill-Generation aus Failures (MetaClaw Pattern)
- Temporal Context Injection
- Working Memory M5 (Redis)

---

## Phase 1: Hindsight Memory Engine Integration

### 1.1 Package installiert
- [x] `hindsight-api-slim>=0.4.17` in pyproject.toml ✅ (31.03.2026)
  - `uv sync` erfolgreich (v0.4.21)
  - Base-Install (ohne [all] — mlx crasht auf Windows)
  - Dependency-Upgrades: fastapi>=0.120.3, uvicorn>=0.38.0, python-dotenv>=1.1.0
  - Import OK: MemoryEngine, GraphRetriever, MemoryEngineInterface

### 1.2 Core Engine Integration ✅ (31.03.2026)
- [x] `agent/memory/engine.py` — Singleton MemoryEngine mit lazy init
  - Nutzt unsere zentrale Config: AGENT_PROVIDER, ANTHROPIC_API_KEY, AGENT_UTILITY_MODEL
  - KEINE eigenen HINDSIGHT_API_* ENV vars — alles via Constructor-Parameter
  - Graceful: ohne PostgreSQL = Memory deaktiviert, Agent funktioniert weiter
  - DB URL: `HINDSIGHT_DB_URL` (unsere eigene Variable)
  - Bank-Strategie: 1 Bank pro User (`user_{user_id}`)
- [x] `agent/graph/nodes/memory_node.py` — Recall + Retain als LangGraph Nodes
  - `memory_recall_node`: VOR LLM-Call, holt Top-10 Memories, injiziert ins Prompt
  - `memory_retain_node`: NACH LLM-Call, extrahiert Fakten aus Conversation
- [x] `agent/graph/agent_graph.py` — Graph erweitert:
  - START → memory_recall → llm_call → [...] → memory_retain → END
- [x] `agent/tools/memory_hindsight.py` — 2 neue Tools (12 gesamt):
  - `memory_search`: Agent sucht aktiv nach Memories
  - `memory_add`: Agent speichert explizit Fakten
  - In ToolRegistry registriert, automatisch als MCP Tools exponiert
- [x] `agent/skills/global/memory-usage/SKILL.md` — Memory Skill (4 Skills gesamt)
  - Wann STORE, wann SEARCH, Best Practices, Anti-Patterns
- [x] `.env` aktualisiert: `HINDSIGHT_DB_URL` (auskommentiert = deaktiviert)
- [x] `bridge/config.py`: .env Pfad Fix (Code Review Issue #20)
- [x] `.env`: Matrix Bot Credentials entfernt (leer, Code Review Issue #1)

### 1.3 PostgreSQL + pgvector Setup ✅ (31.03.2026)
- [x] PostgreSQL 17 ZIP Binary in `tools/pgsql/` (Windows native, Port 5433)
- [x] pgvector v0.8.2 DLL installiert (`vector.dll` + Extension SQL Files)
- [x] `initdb` → `tools/pgsql-data/`, DB `hindsight_dev` erstellt
- [x] `CREATE EXTENSION vector` erfolgreich
- [x] `scripts/setup-postgres.ps1` — Einmaliges Setup-Script
- [x] `scripts/download-embeddings.py` — BAAI/bge-small-en-v1.5 + cross-encoder cached
- [x] devstack2: `pg_ctl.exe start` (Windows native, `-SkipPostgres` Flag)
- [x] docker-compose: pgvector/pgvector:pg17 Image (auskommentiert, Alternative)
- [x] `.env`: `HINDSIGHT_DB_URL=postgresql://postgres@localhost:5433/hindsight_dev`
- [x] `engine.py`: ENV-Bridging (unsere Config → Hindsight ENV vars via `setdefault`)
- [x] **Getestet:** MemoryEngine ACTIVE, Bank erstellt, Embedding-Index angelegt

### 1.4 Hindsight Built-in Features (kommen automatisch via pip Package)
Die folgenden Features sind **Teil von Hindsight** und brauchen keinen eigenen Code:
- [x] **5 Linking-Strategien:** Temporal, Semantic, Entity, Causal, Spreading Activation
  - Werden automatisch bei `retain_async()` erstellt
- [x] **4 Memory Networks:** World, Experience, Opinion, Entity
  - Gesteuert via `fact_type` Parameter bei Retain ("world"/"experience"/"opinion")
  - Entity Network: automatische Entity Resolution bei Retain
- [x] **Retain Pipeline:** LLM Fact Extraction → Entity Processing → Link Creation → DB Insert
- [x] **Recall Pipeline:** 4-Weg Parallel (Semantic + BM25 + Graph + Temporal) → RRF Fusion → Rerank
- [x] **Consolidation:** Observations aus Facts verdichten (Background Worker)
- [x] **Reflect:** Agentic Loop mit Tools (search, recall, expand, done)
- [x] **Alembic Migrationen:** Laufen automatisch bei `engine.initialize()` (`run_migrations=True`)
- [x] **Connection-Pool:** asyncpg Pool (konfigurierbar via HINDSIGHT_API_DB_POOL_*)

### 1.5 Alembic + Audit Logging ✅ (31.03.2026)
Eigenes Alembic fuer Agent-Tabellen (Schema: `agent`), getrennt von Hindsight (`public`):
- [x] `alembic.ini` + `alembic/env.py` — eigene Alembic Config
  - Schema: `agent` (Hindsight nutzt `public`)
  - DB URL aus `HINDSIGHT_DB_URL` (gleiche PG Instanz)
- [x] `alembic/versions/001_audit_events.py` — Erste Migration
  - `agent.audit_events` mit: user_id, thread_id, agent_class, agent_role, tool_name, input/output JSON
  - Indices auf user_id, thread_id, action, timestamp
- [x] `agent/audit/store.py` refactored:
  - Raw DDL entfernt, nutzt `agent.audit_events` (Alembic-managed)
  - +user_id, +agent_role Columns (Multi-User + Multi-Agent)
- [x] `psycopg[binary]>=3.2.0` aktiviert in pyproject.toml
- [x] Getestet: Migration + Write + Query funktionieren

### 1.6 Noch offen (braucht LLM API Key fuer volle Funktionalitaet)
- [ ] Retain testen: Conversation → Fakten extrahieren → DB (braucht ANTHROPIC_API_KEY)
- [ ] Recall testen: Query → 4-Weg Retrieval → Ergebnisse
- [ ] Reflect testen: Agentic Loop mit Memory-Tools
- [ ] Consolidation testen: Background Worker verdichtet Facts → Observations

### 1.7 Search + Retrieval (via Hindsight, kein eigener Code)
Hindsight's `recall_async()` macht automatisch:
- [ ] 4 parallele Retrieval-Strategien verifizieren:
  - Vector Search (pgvector Cosine Similarity)
  - Temporal Search (zeitbasiert)
  - Entity Search (Graph-Traversal)
  - Keyword Search (pg_trgm / BM25)
- [ ] Cross-Encoder Reranking (merged Results)
- [ ] Hybrid Search API: `search(query, user_id) → ranked memories`

---

## Phase 2: Graphiti / Cognee als Extension (spaeter)

Hindsight hat eigenen Knowledge Graph in PostgreSQL (entity_links, memory_links).
Graphiti/Cognee sind **ergaenzend**, nicht ersetzend. Integration via Extension Points:

### 2.1 Graphiti als Custom GraphRetriever
- [ ] `GraphitiRetriever(GraphRetriever)` implementieren
  - Hindsight's `GraphRetriever(ABC)` als Basis
  - Graphiti's temporale Graph-API als Backend
  - Registrieren als zusaetzliche Retrieval-Strategie
  - Cognee hat kuerzlich Graphiti Integration bekommen (temporale Graphs)

### 2.2 Cognee als Structured Knowledge Layer
- [ ] Cognee parallel zu Hindsight evaluieren
  - Cognee nutzt KuzuDB + LanceDB (kompatibel mit unserem bestehenden memory_engine/)
  - Plugin-basiert: `DataPoint` extends Pydantic → Graph/Vector Store Adapter
  - Ergaenzend: Cognee fuer strukturierte Fakten, Hindsight fuer episodisches Memory

### 2.3 Unified Search API
- [ ] Fusion-Layer der alle Memory-Backends abfragt:
  ```
  Agent Query → Unified Search
                  ├── Hindsight (Retain/Recall) → 4-Weg Retrieval
                  ├── Graphiti (optional) → Temporal Graph Queries
                  └── Cognee (optional) → Structured KG Queries
                → RRF Fusion → Reranked Results
  ```
- [ ] Reciprocal Rank Fusion (RRF) ueber alle Backends

---

## Phase 3: Agent Integration

### 3.1 Memory als LangGraph Node ✅ (31.03.2026)
- [x] `agent/graph/nodes/memory_node.py` — Recall + Retain Nodes
- [x] `agent/graph/agent_graph.py` — START → memory_recall → llm → ... → memory_retain → END
- [x] Vor LLM-Call: relevante Memories retrieven → ins Prompt injizieren
- [x] Nach LLM-Response: Conversation retainen (Hindsight extrahiert Fakten automatisch)
- [ ] Consolidation als Background-Worker (Hindsight Worker, noch nicht in devstack2)

### 3.2 Memory Tools ✅ (31.03.2026)
- [x] `agent/tools/memory_hindsight.py` — memory_search + memory_add (12 Tools gesamt)
- [x] In ToolRegistry registriert → automatisch als MCP Tools exponiert (exec-09)
- [x] `agent/skills/global/memory-usage/SKILL.md` — Skill erklaert wann Agent Memory nutzen soll

### 3.3 Memory Sharing zwischen Agents
- [ ] Shared Memory Store: alle Trading-Rollen nutzen gleiche Bank pro User
- [ ] Read/Write Permissions per Agent-Rolle (Tag-basiert via Hindsight Tags)
- [ ] Agent A findet RSI-Anomalie → speichert → Agent B findet es via Search

### 3.4 Memory Graph Visualisierung
- [ ] Memory-Graph in tldraw Canvas oder eigenes Panel
- [ ] Supermemory `memory-graph` React Component als UI-Referenz (`_ref/supermemory/packages/memory-graph/`)
- [ ] Nodes = Memories, Edges = Links (temporal/semantic/entity)
- [ ] User kann Memory-Graph explorieren, Memories pinnen/loeschen

---

## Phase 4: Self-Evolution (MetaClaw + Hindsight)

### Bereits in exec-10 implementiert:
- [x] Auto-Skill-Generation aus Failures (SkillEvolver)
- [x] 3-Tier Skill System (global/team/personal)
- [x] Trajectory Logging + PRM Scoring
- [x] RL Infrastructure (deaktiviert)

### Noch zu integrieren:
- [ ] **4.1:** Hindsight Consolidation als Skill-Quelle
  - Consolidierte Memories → generieren neue Skills automatisch
  - "User macht immer den gleichen Fehler bei Stop-Loss" → Skill
- [ ] **4.2:** Memory-basiertes Skill Retrieval
  - Statt nur Task-Description → auch Memory-Context fuer Skill-Matching
  - Agent erinnert sich an aehnliche Situationen → passende Skills
- [ ] **4.3:** User-Profile als Skill-Filter
  - User-Profil (Hindsight Opinion Network) → filtert relevante Skills
  - Swing-Trader bekommt andere Skills als Scalper

---

## Verify-Gates

### Gate 0: Infrastructure ✅
- [x] PostgreSQL 17 + pgvector 0.8.2 laeuft auf Port 5433
- [x] Hindsight MemoryEngine ACTIVE (Bank erstellt, Embedding-Index angelegt)
- [x] Embedding-Modell (BAAI/bge-small-en-v1.5) + Reranker cached
- [x] devstack2 startet PostgreSQL via `pg_ctl.exe`

### Gate 1: Memory Engine (braucht LLM API Key)
- [ ] Retain: `retain_async()` extrahiert Fakten aus Conversation
- [ ] Recall: `recall_async()` liefert relevante Memories (4-Weg)
- [ ] Entity Resolution: "EUR/USD" = "EURUSD" erkannt
- [ ] Consolidation: Observations aus Facts verdichtet
- [ ] Contradiction Detection: neues Fakt ersetzt altes

### Gate 2: Memory Networks (Teil von Retain/Recall)
- [ ] World: "Was ist EUR/USD?" → Fakt aus Memory
- [ ] Experience: "Wann habe ich zuletzt getradet?" → Zeitstempel
- [ ] Opinion: "Welche Strategie bevorzuge ich?" → Preference
- [ ] Entity: "Welche Assets korrelieren?" → Graph-Traversal

### Gate 3: Agent Integration
- [x] Memory Nodes im LangGraph (recall vor LLM, retain nach LLM)
- [x] memory_search + memory_add Tools registriert
- [x] Memory Skill geladen
- [ ] End-to-End: User fragt → Agent recalled Memories → antwortet → retains neue Fakten

### Gate 4: Audit + Alembic ✅
- [x] Eigenes Alembic im `agent` Schema (getrennt von Hindsight `public`)
- [x] `agent.audit_events` Tabelle erstellt (user_id + agent_role fuer Multi-User/Agent)
- [x] PostgresAuditStore nutzt Alembic-managed Tabelle (kein raw DDL)

### Gate 5: Visualisierung
- [ ] Memory Graph im UI sichtbar (Nodes + Edges)
- [ ] User kann Memories pinnen/loeschen

---

## Code Review Fixes (aus exec-10 uebertragen)

Offene Issues aus dem Python Backend Code Review (31.03.2026):

- [ ] **#2 Critical:** Cypher injection in `memory_engine/kg_store.py`
  - `seed()` baut Cypher via String-Formatting mit `.replace("'", "\\'")`
  - Fix: Parameterized Queries nutzen
- [x] **#4 Critical:** `shared.cache_adapter` ✅ (31.03.2026)
  - `cache_adapter.py` vom Hauptprojekt kopiert nach `shared/`
  - `shared/__init__.py` updated: exportiert `create_cache_adapter`, `TTL_INDICATOR`, `TTL_SNAPSHOT`
  - `working_memory.py` und `memory/app.py` importieren fehlerfrei
- [ ] **#9 High:** LanceDB `delete()` interpoliert doc_id in Filter-String
  - `memory_engine/vector_store.py:501`
  - Fix: Parameterized Delete oder ID sanitizen
- [ ] **#10 High:** `SQLiteKGStore.query()` akzeptiert Raw SQL von HTTP Endpoint
  - `memory/app.py:136` leitet `request.query` direkt durch
  - Fix: Query-Allowlist oder Endpoint entfernen
- [ ] **#13 Medium:** `MemorySaver` in LangGraph = in-memory only
  - Alle 3 Graphs nutzen MemorySaver → State verloren bei Restart
  - Fix: Persistent Checkpointer (PostgreSQL/Redis) fuer Prod
- [ ] **#17 Medium:** `EpisodicStore` nutzt sqlite3 ohne Thread-Safety
  - `check_same_thread=False` aber keine Locks
  - Fix: `aiosqlite` oder `asyncio.Lock` fuer Writes

---

## Phase 5: Evaluierung — Hauptprojekt Integration + UI

### 5.1 Supermemory UI evaluieren
- [ ] `_ref/supermemory/packages/memory-graph/` React Component analysieren
- [ ] Passt die Graph-Visualisierung zu unserem tldraw Canvas?
- [ ] Oder eigenes Memory-Panel (wie Supermemory Dashboard)?
- [ ] Memory-Graph Interaktionen: Zoom, Filter, Pin, Delete

### 5.2 Hauptprojekt Control Panel uebernehmen
- [ ] Control Panel aus `tradeview-fusion/` evaluieren
  - Settings, Agent Config, Skill Management UI
  - `/control` Route im Hauptprojekt
- [ ] Relevant fuer: Skill enable/disable, Memory Inspector, Agent-Rollen Config
- [ ] Was uebernehmen, was neu bauen?

### 5.3 Hauptprojekt Filesystem / File Execution
- [ ] File Execution Slices aus Hauptprojekt evaluieren
  - Code Execution (OpenSandbox, exec-12)
  - File Upload/Download Pipeline
  - Workspace/Project Filesystem
- [ ] Wie integriert sich File-Kontext mit Memory Engine?
  - Uploaded PDFs → Memory Engine (Retain → Chunks → Vector Store)
  - Code-Outputs → Experience Network
- [ ] Was muss von `tradeview-fusion/` uebernommen werden?

### 5.4 Memory + Content Ingestion (exec-05b Verbindung)
- [ ] Email/YouTube/RSS Ingestion (exec-05b) → Memory Engine als Storage
- [ ] Doomberg Newsletter → Retain → World Network
- [ ] YouTube Transcripts → Retain → Experience Network
- [ ] Unified Ingestion → Memory statt nur Vector DB

---

## Referenzen

- `_ref/hindsight/` — MIT, 91.4% LongMemEval, Python, PostgreSQL+pgvector
  - Core Engine: `hindsight-api-slim/hindsight_api/engine/`
  - Memory Engine: `engine/memory_engine.py`
  - Search: `engine/search/`
  - Consolidation: `engine/consolidation/`
  - Reflect: `engine/reflect/`
  - Retain: `engine/retain/`
- `_ref/supermemory/` — Closed-Source, aber UI-Referenz
  - Memory Graph Component: `packages/memory-graph/`
  - MCP Server: `apps/mcp/`
- Benchmarks: arxiv 2512.12818 (Hindsight Paper)
- Multi-Agent Memory: arxiv 2603.10062 (Architecture Perspective)
- Collaborative Memory: arxiv 2505.18279 (Dynamic Access Control)
