# exec-18: Unified Agent Schema (Agno-inspired, Hindsight-coexistent)

**Datum:** 10.04.2026
**Status:** ⚠️ **OUTDATED (2026-04-20) — frozen at the "8 new tables planned" snapshot. Reality has moved on: 26 migrations shipped.**

---

## ⚠️ Outdated-Header (2026-04-20)

**Dieser spec ist veraltet.** Er wurde geschrieben als wir dachten "exec-18 fügt 8 neue Tabellen hinzu" — tatsächlich haben wir **26 alembic-migrations** gelandet (`001_audit_events` … `026_smart_routing_config`). Die "Phase 1–N: build these tables"-sections unten sind überholt.

**Wir machen es möglicherweise komplizierter als nötig** — statt in einem statischen doc die erwartete DB-struktur zu pflegen, sollten wir den **agno-index** (schema-introspection via `inspect()` aus agno cookbook) als authoritativen schema-check benutzen. Ground-truth ist die DB, nicht dieser spec.

**Konkret:**
- Neue tables → neue alembic-migration im owning-spec-slice (exec-hermes, exec-scheduler, exec-16, etc.), **nicht** hier neu planen
- Schema-check → agno's `introspect_schema` pattern aus `_ref/agno/cookbook/01_demo/agents/dash/tools/introspect.py` als matrix agent-tool einbauen
- exec-18 bleibt wertvoll für den **bounded-context-kontext** (warum `public` / `agent` / `ingestion` / `storage` / `matrix_crypto` getrennt sind) — aber nicht als laufende to-do-liste

**Open decision:** komplett archivieren mit §0-§1 als standalone ADR, oder diesen warning-header weitertragen? Aktuell: header bleibt bis konsolidierungs-entscheidung.

---

**Abhaengig von:** exec-11 (Memory Engine / Hindsight), exec-12 (Audit), exec-17 (Observability), `exec-world-model.md`, `exec-personal-kb.md`, `exec-context.md`
**Referenzen:**
- Agno Framework: https://github.com/agno-agi/agno (lokal als submodule: `_ref/agno`)
- Agno Docs: https://docs.agno.com
- **Agno schema-introspection tool**: `_ref/agno/cookbook/01_demo/agents/dash/tools/introspect.py` (runtime `inspect()` via SQLAlchemy — future matrix agent-tool)
- Hindsight: `_ref/hindsight/hindsight-api-slim/`
- Schema Ownership: `specs/17-schema-ownership.md` (siehe Phase 0 unten)
- Alembic migrations heute: `python-backend/alembic/versions/001–026` (26 migrations, nicht 8 wie §1 sagt)

---

## Phase 0: Vorarbeit — Schema Separation (aus exec-19 uebernommen)

exec-19 Stufe 3 (Files API) hat das erste dedizierte Schema `storage` eingefuehrt
fuer Go-owned Tabellen (aktuell `storage.artifact_metadata`, spaeter auch
`matrix_crypto.*`). Das begruendet die Bounded-Context-Regel die exec-18
weiterfuehrt:

**Schema pro Bounded Context:**
- `public` = Python Hindsight
- `agent` = Python Agent Service (bekommt in exec-18 die 8 neuen Tabellen)
- `ingestion` = Python Ingestion Worker
- `storage` = Go Appservice (Artifacts, Crypto, S3-Metadata)
- `personal_kb` (optional) = user-kuratierte Knowledgebase
- `world` (optional) = globale Evidence-/Claim-Metadaten
- `matrix_crypto` (optional) = Go Appservice (mautrix-go Olm Store)

**Doku:** `specs/17-schema-ownership.md` (geschrieben exec-19, 11.04.2026).

### Phase 0 Tasks

- [x] `storage` Schema existiert, `storage.artifact_metadata` live (exec-19 Stufe 3)
- [x] `pgxpool` native Postgres Layer (exec-19 Stufe 3.0 — Pattern etabliert,
  exec-18 Tabellen nutzen denselben Stack)
- [ ] **PG-level Permission Split (defense in depth)** — Go nutzt `matrix_go_user` mit
  `GRANT` nur auf `storage.*`, Python nutzt `matrix_py_user` mit `GRANT` auf
  `agent.*`, `ingestion.*`, `public.*`. Cross-schema writes sind damit physikalisch
  unmoeglich, nicht nur per Konvention.
  ```sql
  CREATE ROLE matrix_go_user LOGIN PASSWORD '...';
  CREATE ROLE matrix_py_user LOGIN PASSWORD '...';
  GRANT USAGE, CREATE ON SCHEMA storage TO matrix_go_user;
  GRANT ALL ON ALL TABLES IN SCHEMA storage TO matrix_go_user;
  GRANT USAGE, CREATE ON SCHEMA agent, ingestion, public TO matrix_py_user;
  GRANT ALL ON ALL TABLES IN SCHEMA agent, ingestion, public TO matrix_py_user;
  ```
  - [ ] Neue Env-Vars: `MATRIX_GO_DSN`, `MATRIX_PY_DSN`
  - [ ] `go-appservice/.env.development` + `python-backend/.env` anpassen
  - [ ] Migration script `scripts/pg-permission-split.sql`
  - [ ] Cold-Start Test: Go kann `agent.audit_events` NICHT mehr lesen (sollte "permission denied" kommen)
  - [ ] Wenn `personal_kb` / `world` aktiviert werden: Grants/Rollen explizit erweitern statt still `agent` mitzubenutzen
- [ ] **SQLite-Store entfernen** — `metadata_store.go` (SQLite) loeschen,
  `metadata_store_factory.go` loeschen, nur `PostgresMetadataStore` bleibt.
  Das macht den Code-Pfad eindeutig und passt zum Single-Schema-per-Service Modell.
- [ ] **Alle neuen exec-18 Tabellen im `agent` Schema** — nicht `public`. Alembic
  Migrations mit `op.create_table("sessions", ..., schema="agent")`.

---

## Referenz-Dateien (Volle Schema-Map mit Zweckbeschreibung)

Alle Dateien die fuer unsere Schema-Entscheidungen relevant sind. Nutzlich als
Lookup beim Implementieren einzelner Tabellen.

### Agno: `_ref/agno/libs/agno/agno/`

#### Database Adapters (pro Backend)

```
db/postgres/
  postgres.py                  — PostgresDb class, verwaltet SQLAlchemy Connection,
                                 _create_table() aus Schema dict, bulk CRUD methods
  async_postgres.py            — Async variant, identische API mit asyncpg
  schemas.py                   — ⭐ CORE REFERENCE (355 Zeilen)
                                 Alle TABLE_SCHEMA dicts: SESSION_TABLE_SCHEMA,
                                 MEMORY_TABLE_SCHEMA, EVAL_TABLE_SCHEMA, etc.
                                 PLUS get_table_schema_definition() factory
  utils.py                     — Connection string parsing, PG-spezifische helpers

db/mysql/
  mysql.py                     — MySQL Db class (gleiche API wie postgres.py)
  async_mysql.py               — Async via aiomysql
  schemas.py                   — Gleiche Schemas, Mapping zu MySQL-Typen (TEXT statt JSONB)
  utils.py

db/sqlite/
  sqlite.py                    — SQLite Db class (fuer Dev/Tests)
  schemas.py                   — Gleiche Schemas, SQLite-kompatibel
  utils.py

db/mongo/
  mongo.py                     — MongoDB Collection-based impl
  async_mongo.py               — Motor async driver
  schemas.py                   — BSON schemas (keine SQL)
  utils.py

db/dynamo/
  dynamo.py                    — AWS DynamoDB impl
  schemas.py                   — DynamoDB table definitions (PK/SK structure)
  utils.py

db/firestore/
  firestore.py                 — Google Firestore impl
  schemas.py                   — Firestore collection definitions
  utils.py

db/singlestore/                — SingleStore (MySQL-compatible analytics DB)
db/redis/                      — Redis (cache/ephemeral state)
db/surrealdb/                  — SurrealDB (multi-model DB)
db/gcs_json/                   — GCS JSON files (cheap storage)
db/json/                       — Local JSON files
db/in_memory/                  — In-memory dict (Tests)

db/base.py                     — ⭐ BaseDb abstract class — was alle DBs koennen muessen
                                 read_session, upsert_session, read_memory, etc.
db/filter_converter.py         — Converts Pydantic filters to SQL WHERE clauses
db/utils.py                    — Shared db utils (connection parsing, etc.)
```

#### Entity Dataclasses (DB-agnostic Python models)

```
db/schemas/
  __init__.py                  — Package exports
  memory.py                    — UserMemory dataclass (57 lines)
                                 Fields: memory, memory_id, topics, user_id,
                                 input, created_at, updated_at, feedback, agent_id, team_id
                                 __post_init__: normalisiert timestamps zu epoch
                                 to_dict/from_dict: serialization mit ISO datetime
  evals.py                     — EvalRunRecord (Pydantic, 34 lines)
                                 + EvalType enum (accuracy, agent_as_judge, performance, reliability)
                                 + EvalFilterType enum (agent, team, workflow)
                                 Fields: run_id, eval_type, eval_data, eval_input, name,
                                 agent_id, team_id, workflow_id, model_id, model_provider,
                                 evaluated_component_name
  knowledge.py                 — KnowledgeRow (Pydantic, 40 lines)
                                 Fields: id, name, description, metadata, type, size,
                                 linked_to, access_count, status, status_message,
                                 created_at, updated_at, external_id
                                 Auto-generates UUID if id is None
  approval.py                  — Approval dataclass (107 lines)
                                 Fields: id, run_id, session_id, status, source_type,
                                 approval_type, pause_type, tool_name, tool_args,
                                 expires_at, agent_id, team_id, workflow_id, user_id,
                                 schedule_id, schedule_run_id, source_name, requirements,
                                 context, resolution_data, resolved_by, resolved_at,
                                 created_at, updated_at, run_status
                                 Tracks run_status from associated run
  culture.py                   — CulturalKnowledge dataclass (120 lines, experimental)
                                 Fields: id, name, content, categories, notes, summary,
                                 metadata, input, created_at, updated_at, agent_id, team_id
  scheduler.py                 — Schedule + ScheduleRun dataclasses (151 lines)
                                 Schedule: id, name, cron_expr, endpoint, method, payload,
                                 timezone, timeout_seconds, max_retries, retry_delay_seconds,
                                 enabled, next_run_at, locked_by, locked_at
                                 ScheduleRun: id, schedule_id, attempt, triggered_at,
                                 completed_at, status, status_code, run_id, session_id,
                                 error, input, output, requirements
  metrics.py                   — (empty, metrics schema defined inline in postgres/schemas.py)
```

#### Session Models (Agent Runtime State)

```
session/
  __init__.py                  — Package exports
  agent.py                     — ⭐ AgentSession dataclass
                                 Fields: session_id, agent_id, team_id, user_id,
                                 workflow_id, session_data, metadata, agent_data,
                                 runs (List[RunOutput | TeamRunOutput]), summary,
                                 created_at, updated_at
                                 runs = Liste aller LLM-Runs in der Session
  team.py                      — TeamSession (Multi-agent teams)
  workflow.py                  — WorkflowSession (Step-based workflows)
  summary.py                   — SessionSummary dataclass (aggregierte Session-Zusammenfassung)
```

#### Tracing (OTel persistence)

```
tracing/
  __init__.py                  — Package exports
  schemas.py                   — ⭐ Trace + Span dataclasses (277 lines)
                                 Trace: trace_id, name, status, start_time, end_time,
                                 duration_ms, total_spans, error_count, run_id,
                                 session_id, user_id, agent_id, team_id, workflow_id
                                 Span: span_id, trace_id, parent_span_id, name,
                                 span_kind, status_code, status_message, start_time,
                                 end_time, duration_ms, attributes
                                 from_otel_span() — konvertiert OTel ReadableSpan zu Span
                                 create_trace_from_spans() — aggregiert spans zu trace
  exporter.py                  — OTel SpanExporter Implementation die in DB schreibt
  setup.py                     — TracerProvider init helpers
```

#### Evaluation

```
eval/
  accuracy.py                  — AccuracyEval: ground-truth comparison
  agent_as_judge.py            — AgentAsJudgeEval: LLM als Judge pattern
  performance.py               — PerformanceEval: latency, throughput, cost
  reliability.py               — ReliabilityEval: error rates, retries
  utils.py                     — Shared eval helpers (metrics calc)
```

#### Learning / Knowledge Stores

```
learn/
  schemas.py                   — Learning dataclasses (namespaced learnings)
  config.py                    — LearnConfig (toggle which store is active)
  curate.py                    — Curator: filters + prioritizes learnings
  machine.py                   — Learning state machine (draft → active → retired)
  utils.py
  stores/
    __init__.py                — Package exports
    protocol.py                — ⭐ Abstract store protocol (interface alle stores implementieren)
    decision_log.py            — DecisionLogStore: logged decisions
    entity_memory.py           — EntityMemoryStore: entity-scoped memory
    learned_knowledge.py       — LearnedKnowledgeStore: cross-session distilled knowledge
    session_context.py         — SessionContextStore: per-session context
    user_memory.py             — UserMemoryStore: per-user memory (analog Hindsight bank)
    user_profile.py            — UserProfileStore: user preferences + profile
```

#### Memory Manager (experimental)

```
memory/
  manager.py                   — Unified memory manager mit retain/recall API
                                 Abstraction ueber die verschiedenen Stores
```

#### Culture (experimental)

```
culture/
  manager.py                   — CulturalKnowledgeManager, verwaltet CulturalKnowledge
```

#### Metrics Aggregation

```
metrics.py                     — MetricsAggregator, aggregiert tagesweise/woechentlich
                                 Schreibt in metrics table via DB adapter
```

#### OS Routers (HTTP API Layer)

```
os/
  routers/
    evals/
      schemas.py               — Pydantic request/response fuer /evals endpoints
    session/
      session.py               — /sessions CRUD endpoints
```

#### Migrations (Agno version upgrades)

```
db/migrations/
  manager.py                   — MigrationManager: runs versioned migrations
  utils.py                     — Migration helpers
  v1_to_v2.py                  — v1 → v2 major version migration
  versions/
    v2_3_0.py                  — 2.3.0 schema changes
    v2_5_0.py                  — 2.5.0 schema changes
    v2_5_6.py                  — 2.5.6 schema changes
```

#### Development Docs

```
.cursorrules                   — Agno coding patterns (sync+async, no loops, etc.)
CLAUDE.md                      — ⭐ Instructions fuer Claude Code in Agno repo
                                 Key rules: sync+async variants, PostgreSQL prod,
                                 SQLite dev, start with single agent
AGENTS.md                      — Agent developer guide
cookbook/08_learning/          — ⭐ Golden standard example cookbook
specs/                         — Design docs (private symlink, may not exist)
docs/                          — Documentation (private symlink)
```

### Hindsight: `_ref/hindsight/hindsight-api-slim/`

#### Core Schema Files

```
hindsight_api/alembic/versions/
  5a366d414dce_initial_schema.py                            — ⭐ INITIAL SCHEMA (8 tables)
                                                              banks, documents, operations,
                                                              entities, memory_units,
                                                              entity_cooccurrences,
                                                              memory_links, chunks
                                                              Uses pgvector for embeddings
                                                              Supports pgvector/vchord/pgvectorscale
  a1b2c3d4e5f6_add_file_storage_table.py                    — file_storage: Optional blob cache
                                                              fuer grosse Dokumente/Bilder
  c2d3e4f5g6h7_add_audit_log_table.py                       — audit_log: Hindsight's eigene
                                                              Audit-Tabelle (getrennt von unserer)
  e4f5a6b7c8d9_add_webhooks_tables.py                       — webhooks + webhook_http_config:
                                                              Event webhooks fuer external systems
  h3c4d5e6f7g8_mental_models_v4.py                          — mental_models: Konsolidiertes Wissen
                                                              aus multiple memory_units (v4 schema)
  j5e6f7g8h9i0_mental_model_versions.py                     — mental_model_versions: History
                                                              der mental models
  n9i0j1k2l3m4_learnings_and_pinned_reflections.py          — ⭐ learnings: Hindsight's eigene
                                                              cross-session learnings
                                                              + pinned_reflections: manuell
                                                              gepinnte Reflection-Outputs
  o0j1k2l3m4n5_migrate_mental_models_data.py                — Data migration
  p1k2l3m4n5o6_new_knowledge_architecture.py                — directives: New knowledge arch
                                                              ersetzt teilweise mental_models

  (40+ weitere Migrations fuer Indizes, Performance-Tuning,
   retain params, temporal indexes, trgm, HNSW indexes, etc.)
```

#### Hindsight Python Code

```
hindsight_api/
  models.py                    — ⭐ Pydantic models fuer alle Entities
                                 (MemoryUnit, Bank, Entity, Document, etc.)
  migrations.py                — Auto-run migration logic (called on FastAPI startup)
  config.py                    — HindsightConfig (hierarchical: global → tenant → bank)
  main.py                      — FastAPI entrypoint, migrations laufen bei startup

  engine/
    memory_engine.py           — ⭐ MemoryEngine: main orchestrator
                                 retain(), recall(), reflect() methods
    llm_wrapper.py             — LLM abstraction (OpenAI, Anthropic, Gemini, Groq,
                                 MiniMax, Ollama, LM Studio, LiteLLM, Claude Code)
    embeddings.py              — Embedding gen (sentence-transformers local oder TEI)
    cross_encoder.py           — Reranking (local cross-encoder oder TEI)
    entity_resolver.py         — Entity extraction + canonical name normalization
    query_analyzer.py          — Query intent analysis fuer retrieval strategy

  retain/
    orchestrator.py            — Retain pipeline orchestration
    fact_extraction.py         — LLM-based fact extraction aus content
    link_utils.py              — Entity link creation + management

  search/
    retrieval.py               — Main retrieval orchestrator
                                 (4 parallel strategies: semantic, BM25, graph, temporal)
    graph_retrieval.py         — Graph retrieval abstract base
    link_expansion_retrieval.py — Link expansion graph retrieval
    fusion.py                  — Reciprocal Rank Fusion (RRF) combiner
    reranking.py               — Cross-encoder reranking

  api/
    http.py                    — FastAPI HTTP routers fuer REST endpoints
    mcp.py                     — Model Context Protocol server impl
```

#### Hindsight Integrations (Adapter fuer externe Frameworks)

```
hindsight-integrations/
  litellm/                     — LiteLLM adapter
  crewai/                      — CrewAI adapter
  langgraph/                   — ⭐ LangGraph adapter (RELEVANT: wir nutzen LangGraph)
  pydantic_ai/                 — Pydantic AI adapter
  ag2/                         — AG2 adapter
  claude_code/                 — Claude Code adapter
```

#### Hindsight Table Summary (nach allen Migrations)

**Core Tables (von initial_schema):**
- `banks` — Memory stores, 1 pro user/agent, mit disposition traits + background
- `documents` — Raw ingested content (source text before extraction)
- `operations` — Retain/recall operation log (audit trail)
- `entities` — Canonical entity names, mit trigram index
- `memory_units` — ⭐ Core memory facts mit pgvector embedding (384 dim)
  Fields: id, bank_id, text, embedding, context, event_date, occurred_start/end,
  mentioned_at, fact_type (world/experience/observation), confidence_score,
  access_count, text_signals, observation_scopes
- `entity_cooccurrences` — Edges im Entity-Graph
- `memory_links` — Links zwischen memory_units (graph edges)
- `chunks` — Content chunks mit embeddings (for document retrieval)

**Erweiterte Tables (spaetere Migrations):**
- `mental_models` — Consolidated knowledge (v4 schema)
- `mental_model_versions` — History of mental models
- `learnings` — ⭐ HINDSIGHT'S OWN cross-session learnings
- `pinned_reflections` — Manually pinned reflection outputs
- `directives` — New knowledge architecture entries
- `file_storage` — Optional blob cache
- `audit_log` — Hindsight's own audit (independent)
- `webhooks` + `webhook_http_config` — Event webhooks

#### Hindsight Benchmarks (Performance-Referenz)

```
hindsight-dev/benchmarks/
  run-longmemeval.sh           — LongMemEval benchmark (Hindsight: 91.4%)
  run-locomo.sh                — LocoMo benchmark
  run-consolidation.sh         — Consolidation latency benchmark
  run-retain-perf.sh           — Retain latency benchmark
```

### Matrix: Aktuelle Schema-Dateien (unsere)

```
python-backend/alembic/versions/
  001_audit_events.py          — exec-12 initial audit schema
                                 Fields: timestamp, action, user_id, thread_id,
                                 agent_class, agent_role, tool_name, input, output,
                                 duration_ms, success, error, metadata
  002_ingestion_jobs.py        — exec-15 D13 ingestion pipeline tracking
  003_chunk_hashes.py          — exec-15 D13 deduplication hashes
  004_agent_role_overrides.py  — exec-10 per-user role prompt overrides
  005_consent_overrides.py     — exec-12 consent policy overrides
  006_a2a_delegations.py       — exec-10 agent-to-agent delegation tracking
  007_audit_indexes.py         — exec-12 performance indexes fuer AuditTab queries
  008_skills_state.py          — exec-10 Trace2Skill generated skills state
  009_user_llm_settings.py     — exec-16 user LLM preferences + encrypted API keys
  010_audit_exec17_fields.py   — exec-17 iteration column + thread_timestamp index

python-backend/agent/audit/
  store.py                     — AuditStore ABC + JsonLinesAuditStore + PostgresAuditStore
  logger.py                    — audit_log() async + AuditAction StrEnum
```

---

## Warum

Unser aktuelles Schema ist fragmentiert. Wir haben:

| Bereich | Wo | Was fehlt |
|---------|-----|----------|
| **Audit Events** | `agent.audit_events` (exec-12) | Keine Aggregation, keine Session-Hierarchie |
| **Hindsight Memory** | `public.*` (banks, memory_units, entities) | Eigene Welt, kein Link zu Agent-Sessions |
| **Skills** | `agent.skills_state` (exec-10) | Nicht versioniert, keine Draft/Published Stages |
| **User LLM Settings** | `agent.user_llm_settings` (exec-16) | OK |
| **Consent** | `agent.consent_overrides` + `audit_events` | Aufgeteilt, expires_at fehlt, keine resolution_data |
| **Harness Candidates** | `data/harness/candidates/` (Filesystem, exec-17) | Nicht queryable, keine Pareto-Historie in DB |
| **OTel Traces** | OpenObserve (nicht Postgres, exec-17) | Fluechtig, nicht via SQL joinbar mit Audit |
| **Agent Sessions** | LangGraph Checkpoints (`agent.postgres_checkpoints`) | Minimal, nur LangGraph-interne State |
| **Scheduled Jobs** | Nicht vorhanden | Meta-Harness Loop Mode, periodische Proposer Runs |
| **Evaluation Runs** | Nicht vorhanden | Phase 6 Evaluator schreibt keine DB |
| **Metrics Aggregation** | Nicht vorhanden | Fuer Dashboards, Cost-Reports |

Die Agno-Analyse (`_ref/agno`) zeigt ein durchdachtes, zusammenhaengendes Schema mit **14 Tabellen**
die die meisten unserer Luecken direkt abdecken. Agno verfolgt den "AgentOS"-Ansatz: ein einheitlicher
DB-Layer fuer alle Agent-Concerns (Sessions, Memory, Evals, Traces, Components, Schedules, Approvals).

Gleichzeitig haben wir **Hindsight** als externes Memory-System mit eigenem Schema und eigenen
Alembic-Migrationen. Hindsight managed `banks`, `memory_units`, `entities`, `documents`,
`entity_cooccurrences`, `memory_links` selbstaendig in einem eigenen Schema-Namespace.

### Ziel

1. **Agno-inspiriertes Schema** fuer agent-spezifische Concerns (Sessions, Components, Traces, etc.)
2. **Hindsight bleibt unberuehrt** — wir nutzen Hindsight fuer Memory-Content (banks, memories, entities)
3. **Bridge-Schicht** zwischen Agent Sessions und Hindsight Memories (Link via session_id ↔ bank_id)
4. **Konsolidierung** bestehender agent.* Tables unter einheitlicher Struktur
5. **Versionierung** fuer Harness-Candidates (ersetzt Filesystem-Ansatz aus exec-17)

### Nicht-Ziel

- Agno als Dependency einbinden (zu grosser Umbau, LangGraph bleibt)
- Hindsight durch Agno-Memory ersetzen (Hindsight ist 91.4% LongMemEval, nicht aufgeben)
- Bestehende exec-12 audit_events loeschen (wir erweitern, nicht ersetzen)

---

## Ist-Zustand (Matrix aktuell)

### `agent.*` Schema (unser)

```
agent.audit_events          -- exec-12, 10 migrations
agent.ingestion_jobs        -- exec-15 D13
agent.chunk_hashes          -- exec-15 D13
agent.agent_role_overrides  -- exec-10 role customization
agent.consent_overrides     -- exec-12 consent
agent.a2a_delegations       -- exec-10 multi-agent
agent.skills_state          -- exec-10 Trace2Skill
agent.user_llm_settings     -- exec-16
agent.user_api_keys         -- exec-16
```

### `public.*` Schema (Hindsight)

```
banks                 -- 1 bank per user
memory_units          -- facts + vectors (pgvector)
documents             -- raw ingested content
entities              -- canonical entity names
entity_cooccurrences  -- entity graph edges
memory_links          -- memory-to-memory links
operations            -- retain/recall operation log
mental_models         -- consolidated mental models
mental_model_versions -- versioned mental models
learnings             -- cross-session learnings (Hindsight's own!)
pinned_reflections    -- pinned reflection outputs
directives            -- new knowledge architecture
file_storage          -- optional file blob cache
audit_log             -- Hindsight's own audit (separate from ours)
webhooks              -- event webhooks
```

Das heisst Hindsight hat **auch** ein `learnings` Konzept (aber anders als Agno's).
Wir sollten das nicht duplizieren.

---

## Architektur: Drei Schema-Layer

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Hindsight Memory (public.*)                       │
│  Managed by Hindsight via automatic Alembic migrations       │
│  - Factual knowledge (memory_units, entities, links)         │
│  - Mental models + versions                                  │
│  - Operation log, learnings (Hindsight-specific)             │
│  DO NOT TOUCH THIS SCHEMA                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼ linked via bank_id
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Agent Runtime (agent.*)                           │
│  Managed by matrix Alembic migrations                        │
│  Extended per exec-18 to include Agno-inspired tables        │
│  - sessions, runs, traces, spans                             │
│  - components, component_configs, component_links            │
│  - evals, metrics                                            │
│  - schedules, schedule_runs, approvals                       │
│  - BRIDGE: session_memories (Layer2 → Layer1)                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼ references
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Existing Legacy (agent.*)                         │
│  Kept for backwards compat, may be migrated over time        │
│  - audit_events (exec-12) → partially superseded by traces/spans │
│  - skills_state → superseded by components/component_configs  │
│  - consent_overrides → superseded by approvals               │
└─────────────────────────────────────────────────────────────┘
```

---

## Schema-Mapping: Agno → Matrix

### Direkt uebernehmen (1:1 aus Agno)

| Agno Tabelle | Matrix Tabelle (neu) | Zweck | Migration |
|--------------|----------------------|-------|-----------|
| sessions | `agent.sessions` | Session mit runs JSONB, summary, metadata | 011 |
| evals | `agent.evals` | Evaluation Runs | 012 |
| metrics | `agent.metrics` | Daily/Weekly Aggregation | 013 |
| traces | `agent.traces` | OTel traces root (persistent) | 014 |
| spans | `agent.spans` | OTel spans mit parent-child FK | 014 |
| components | `agent.components` | Agent/Role Definitionen | 015 |
| component_configs | `agent.component_configs` | Versionierte Configs | 015 |
| component_links | `agent.component_links` | Tool/Memory Zuordnung | 015 |
| schedules | `agent.schedules` | Cron Jobs | 016 |
| schedule_runs | `agent.schedule_runs` | Run History | 016 |
| approvals | `agent.approvals` | HITL Approval Workflow | 017 |

### NICHT uebernehmen (Hindsight macht das)

| Agno Tabelle | Warum nicht | Ersatz |
|--------------|-------------|--------|
| memories | Hindsight hat `memory_units` + `entities` + links | Nutze Hindsight |
| knowledge | Hindsight hat `documents` + `directives` | Nutze Hindsight |
| learnings | Hindsight hat eigene `learnings` (cross-session) | Nutze Hindsight |
| culture | Nicht relevant, experimental | Skip |
| versions | Alembic trackt das schon | Skip |

### Bridge (neu, nicht aus Agno)

| Tabelle | Zweck | Migration |
|---------|-------|-----------|
| `agent.session_memories` | Link zwischen agent.sessions und Hindsight memory_units | 018 |

Diese Bridge erlaubt Queries wie:
- "Welche Memories wurden in Session X erinnert/erstellt?"
- "In welchen Sessions wurde dieses Memory verwendet?"
- "Zeige alle Sessions mit Memory-Recall-Failures"

---

## Detaillierte Tabellen-Definitionen

### 011: `agent.sessions`

Basierend auf Agno SESSION_TABLE_SCHEMA + AgentSession dataclass.

```python
op.create_table(
    "sessions",
    sa.Column("session_id", sa.Text, primary_key=True),
    sa.Column("session_type", sa.Text, nullable=False),  # "agent_chat" | "matrix_mention" | "api"
    sa.Column("agent_id", sa.Text, nullable=True),  # TradingRole.value
    sa.Column("user_id", sa.Text, nullable=True),
    sa.Column("thread_id", sa.Text, nullable=True, index=True),  # legacy thread_id compat
    sa.Column("bank_id", sa.Text, nullable=True, index=True),  # Hindsight bank reference
    sa.Column("session_data", postgresql.JSONB, nullable=True),  # prompt, temp, model choice
    sa.Column("agent_data", postgresql.JSONB, nullable=True),    # role config snapshot
    sa.Column("metadata", postgresql.JSONB, nullable=True),
    sa.Column("runs", postgresql.JSONB, nullable=True),          # list of RunOutput-like dicts
    sa.Column("summary", postgresql.JSONB, nullable=True),       # SessionSummary
    sa.Column("status", sa.Text, nullable=False, server_default="active"),
    # active | completed | errored | timeout
    sa.Column("started_at", sa.BigInteger, nullable=False, index=True),
    sa.Column("completed_at", sa.BigInteger, nullable=True),
    sa.Column("created_at", sa.BigInteger, nullable=False, index=True),
    sa.Column("updated_at", sa.BigInteger, nullable=True),
    schema="agent",
)
op.create_index("ix_sessions_thread_id", "sessions", ["thread_id"], schema="agent")
op.create_index("ix_sessions_user_id", "sessions", ["user_id"], schema="agent")
op.create_index("ix_sessions_type_status", "sessions", ["session_type", "status"], schema="agent")
```

**Anpassungen vs. Agno:**
- Hinzugefuegt: `thread_id` (legacy compat mit exec-17 runner.py)
- Hinzugefuegt: `bank_id` (Hindsight bridge)
- Hinzugefuegt: `status` field (Agno hat das nicht explizit)
- Hinzugefuegt: `started_at` + `completed_at` (Agno hat nur created_at)
- Entfernt: `team_id`, `workflow_id` (wir haben keine Teams/Workflows)

### 012: `agent.evals`

Basierend auf Agno EVAL_TABLE_SCHEMA + EvalRunRecord.

```python
op.create_table(
    "evals",
    sa.Column("run_id", sa.Text, primary_key=True),
    sa.Column("eval_type", sa.Text, nullable=False),
    # accuracy | agent_as_judge | performance | reliability | harness_score
    sa.Column("eval_data", postgresql.JSONB, nullable=False),   # results
    sa.Column("eval_input", postgresql.JSONB, nullable=False),  # the test queries
    sa.Column("name", sa.Text, nullable=True),
    sa.Column("agent_id", sa.Text, nullable=True),
    sa.Column("model_id", sa.Text, nullable=True),
    sa.Column("model_provider", sa.Text, nullable=True),
    sa.Column("component_id", sa.Text, nullable=True, index=True),  # FK to components
    sa.Column("component_version", sa.Integer, nullable=True),
    sa.Column("evaluated_component_name", sa.Text, nullable=True),
    sa.Column("created_at", sa.BigInteger, nullable=False, index=True),
    sa.Column("updated_at", sa.BigInteger, nullable=True),
    sa.ForeignKeyConstraint(
        ["component_id", "component_version"],
        ["agent.component_configs.component_id", "agent.component_configs.version"],
        ondelete="SET NULL",
    ),
    schema="agent",
)
```

**Anpassungen vs. Agno:**
- `eval_type` erweitert um `harness_score` fuer exec-17 Phase 5
- FK zu `component_configs` (Agno hat keinen FK)
- Link zur Meta-Harness Pareto-Frontier via component_version

### 013: `agent.metrics`

Basierend auf Agno METRICS_TABLE_SCHEMA.

```python
op.create_table(
    "metrics",
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("agent_runs_count", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("agent_sessions_count", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("users_count", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("token_metrics", postgresql.JSONB, nullable=False, server_default="{}"),
    # {"prompt": int, "completion": int, "cached": int, "total": int}
    sa.Column("model_metrics", postgresql.JSONB, nullable=False, server_default="{}"),
    # {"claude-sonnet-4-6": {"runs": int, "tokens": int, "cost_usd": float}, ...}
    sa.Column("tool_metrics", postgresql.JSONB, nullable=False, server_default="{}"),
    # {"market_data_fetch": {"calls": int, "errors": int, "avg_ms": float}, ...}
    sa.Column("memory_metrics", postgresql.JSONB, nullable=False, server_default="{}"),
    # {"recalls": int, "retains": int, "conflicts": int, "avg_facts": float}
    sa.Column("date", sa.Date, nullable=False, index=True),
    sa.Column("aggregation_period", sa.Text, nullable=False),  # daily | weekly | monthly
    sa.Column("created_at", sa.BigInteger, nullable=False),
    sa.Column("updated_at", sa.BigInteger, nullable=True),
    sa.Column("completed", sa.Boolean, nullable=False, server_default="false"),
    sa.UniqueConstraint("date", "aggregation_period", name="uq_metrics_date_period"),
    schema="agent",
)
```

**Anpassungen vs. Agno:**
- Entfernt: team_runs_count, workflow_runs_count, team_sessions_count, workflow_sessions_count
- Hinzugefuegt: `tool_metrics` (tool call aggregation)
- Hinzugefuegt: `memory_metrics` (hindsight recall/retain counts)

Aggregation-Worker (Cron): Aggregiert aus `audit_events` + `traces` + `sessions` nach Tag.

### 014: `agent.traces` + `agent.spans`

Basierend auf Agno TRACE_TABLE_SCHEMA + _get_span_table_schema.

```python
op.create_table(
    "traces",
    sa.Column("trace_id", sa.Text, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("status", sa.Text, nullable=False, index=True),  # ok | error | timeout
    sa.Column("start_time", sa.Text, nullable=False, index=True),  # ISO 8601
    sa.Column("end_time", sa.Text, nullable=False),
    sa.Column("duration_ms", sa.BigInteger, nullable=False),
    sa.Column("run_id", sa.Text, nullable=True, index=True),
    sa.Column("session_id", sa.Text, nullable=True, index=True),  # FK to sessions
    sa.Column("user_id", sa.Text, nullable=True, index=True),
    sa.Column("agent_id", sa.Text, nullable=True, index=True),
    sa.Column("created_at", sa.Text, nullable=False, index=True),
    sa.ForeignKeyConstraint(
        ["session_id"],
        ["agent.sessions.session_id"],
        ondelete="CASCADE",
    ),
    schema="agent",
)

op.create_table(
    "spans",
    sa.Column("span_id", sa.Text, primary_key=True),
    sa.Column("trace_id", sa.Text, nullable=False, index=True),
    sa.Column("parent_span_id", sa.Text, nullable=True, index=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("span_kind", sa.Text, nullable=False),
    # agent.session | agent.turn | agent.tool_call | agent.memory
    sa.Column("status_code", sa.Text, nullable=False),
    sa.Column("status_message", sa.Text, nullable=True),
    sa.Column("start_time", sa.Text, nullable=False, index=True),
    sa.Column("end_time", sa.Text, nullable=False),
    sa.Column("duration_ms", sa.BigInteger, nullable=False),
    sa.Column("attributes", postgresql.JSONB, nullable=True),
    # {tool.name, tool.success, llm.prompt_tokens, memory.results, ...}
    sa.Column("events", postgresql.JSONB, nullable=True),
    # [{name: "prompt", body: "...", timestamp: "..."}, ...]
    sa.Column("created_at", sa.Text, nullable=False, index=True),
    sa.ForeignKeyConstraint(
        ["trace_id"],
        ["agent.traces.trace_id"],
        ondelete="CASCADE",
    ),
    schema="agent",
)
op.create_index("ix_spans_trace_parent", "spans", ["trace_id", "parent_span_id"], schema="agent")
```

**Kritischer Unterschied zu OTel/OpenObserve:**
- OpenObserve ist fluechtig (nach Retention-Periode weg)
- `agent.traces` + `agent.spans` sind persistent in unserer DB
- Beide koexistieren — OTel exportiert zu OpenObserve UND agent.traces (via OTel SpanProcessor)
- Das ermoeglicht SQL-Joins: `sessions JOIN traces JOIN spans` fuer Harness-Analysis

### 015: `agent.components` + `component_configs` + `component_links`

**Das ist der Kern der Meta-Harness Integration.** Ersetzt das Filesystem-basierte `data/harness/candidates/`.

```python
op.create_table(
    "components",
    sa.Column("component_id", sa.Text, primary_key=True),
    sa.Column("component_type", sa.Text, nullable=False, index=True),
    # agent | tool | memory_config | skill | prompt_template
    sa.Column("name", sa.Text, nullable=True, index=True),
    sa.Column("description", sa.Text, nullable=True),
    sa.Column("current_version", sa.Integer, nullable=True, index=True),
    sa.Column("metadata", postgresql.JSONB, nullable=True),
    sa.Column("created_at", sa.BigInteger, nullable=False, index=True),
    sa.Column("updated_at", sa.BigInteger, nullable=True),
    sa.Column("deleted_at", sa.BigInteger, nullable=True),  # soft delete
    schema="agent",
)

op.create_table(
    "component_configs",
    sa.Column("component_id", sa.Text, nullable=False),
    sa.Column("version", sa.Integer, nullable=False),
    sa.Column("label", sa.Text, nullable=True),  # "stable" | "v1.2.0" | "pre-refactor"
    sa.Column("stage", sa.Text, nullable=False, server_default="draft", index=True),
    # draft | published | archived
    sa.Column("config", postgresql.JSONB, nullable=False),
    # Fuer agent: {system_prompt, tools_allowed, memory_config, consent_config}
    sa.Column("notes", sa.Text, nullable=True),
    # Proposer analysis from exec-17 Phase 5
    sa.Column("parent_version", sa.Integer, nullable=True),  # evolution lineage
    sa.Column("proposer_model", sa.Text, nullable=True),  # welches LLM hat's vorgeschlagen
    sa.Column("pareto_frontier", sa.Boolean, nullable=False, server_default="false"),
    sa.Column("created_at", sa.BigInteger, nullable=False, index=True),
    sa.Column("updated_at", sa.BigInteger, nullable=True),
    sa.Column("deleted_at", sa.BigInteger, nullable=True),
    sa.PrimaryKeyConstraint("component_id", "version"),
    sa.ForeignKeyConstraint(
        ["component_id"],
        ["agent.components.component_id"],
        ondelete="CASCADE",
    ),
    schema="agent",
)

op.create_table(
    "component_links",
    sa.Column("parent_component_id", sa.Text, nullable=False),
    sa.Column("parent_version", sa.Integer, nullable=False),
    sa.Column("link_kind", sa.Text, nullable=False, index=True),
    # uses_tool | uses_memory_bank | inherits_from | references_skill
    sa.Column("link_key", sa.Text, nullable=False),
    sa.Column("child_component_id", sa.Text, nullable=False),
    sa.Column("child_version", sa.Integer, nullable=True),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("meta", postgresql.JSONB, nullable=True),
    sa.Column("created_at", sa.BigInteger, nullable=True, index=True),
    sa.Column("updated_at", sa.BigInteger, nullable=True),
    sa.PrimaryKeyConstraint("parent_component_id", "parent_version", "link_kind", "link_key"),
    sa.ForeignKeyConstraint(
        ["parent_component_id", "parent_version"],
        ["agent.component_configs.component_id", "agent.component_configs.version"],
        ondelete="CASCADE",
    ),
    sa.ForeignKeyConstraint(
        ["child_component_id"],
        ["agent.components.component_id"],
        ondelete="CASCADE",
    ),
    schema="agent",
)
```

**Anpassungen vs. Agno:**
- Hinzugefuegt: `parent_version` (evolution lineage, welche Version basiert auf welcher)
- Hinzugefuegt: `proposer_model` (welches LLM hat den Config-Vorschlag gemacht)
- Hinzugefuegt: `pareto_frontier` (Flag: ist dieser Candidate Pareto-optimal?)

**Meta-Harness Integration:**

`data/harness/candidates/v001/` Filesystem wird ersetzt durch:
```sql
INSERT INTO agent.components (component_id, component_type, name, ...)
VALUES ('trading.technical_analyst', 'agent', 'Technical Analyst', ...);

INSERT INTO agent.component_configs (component_id, version, label, stage, config, ...)
VALUES ('trading.technical_analyst', 1, 'v001', 'published',
        '{"system_prompt": "...", "tools_allowed": [...]}'::jsonb, ...);

-- Proposer generiert v002 als draft
INSERT INTO agent.component_configs (component_id, version, label, stage, config, parent_version, proposer_model)
VALUES ('trading.technical_analyst', 2, 'v002-pareto-attempt', 'draft',
        '{...}'::jsonb, 1, 'claude-sonnet-4-6');
```

Evaluator laeuft v002 gegen search set:
```sql
INSERT INTO agent.evals (run_id, eval_type, eval_data, component_id, component_version, ...)
VALUES (uuid(), 'harness_score',
        '{"completion_rate": 0.92, "avg_turns": 2.5, ...}'::jsonb,
        'trading.technical_analyst', 2, ...);
```

Pareto-Frontier wird via SQL computed:
```sql
UPDATE agent.component_configs
SET pareto_frontier = true
WHERE (component_id, version) IN (
    -- SELECT non-dominated candidates
    ...
);
```

### 016: `agent.schedules` + `schedule_runs`

1:1 aus Agno (fuer Proposer Cron Mode aus exec-17 Phase 6).

### 017: `agent.approvals`

Basierend auf Agno APPROVAL_TABLE_SCHEMA — ersetzt Teile von `consent_overrides` + `audit_events` CONSENT_DECISION Events.

```python
op.create_table(
    "approvals",
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("run_id", sa.Text, nullable=False, index=True),
    sa.Column("session_id", sa.Text, nullable=False, index=True),
    sa.Column("status", sa.Text, nullable=False, index=True),
    # pending | approved | rejected | expired | cancelled
    sa.Column("source_type", sa.Text, nullable=False, index=True),  # agent | team | workflow
    sa.Column("approval_type", sa.Text, nullable=True, index=True),  # required | audit
    sa.Column("pause_type", sa.Text, nullable=False, index=True),
    # confirmation | user_input | external_execution
    sa.Column("tool_name", sa.Text, nullable=True),
    sa.Column("tool_args", postgresql.JSONB, nullable=True),
    sa.Column("expires_at", sa.BigInteger, nullable=True),
    sa.Column("agent_id", sa.Text, nullable=True, index=True),
    sa.Column("user_id", sa.Text, nullable=True, index=True),
    sa.Column("schedule_id", sa.Text, nullable=True, index=True),
    sa.Column("schedule_run_id", sa.Text, nullable=True, index=True),
    sa.Column("source_name", sa.Text, nullable=True),
    sa.Column("requirements", postgresql.JSONB, nullable=True),
    sa.Column("context", postgresql.JSONB, nullable=True),
    sa.Column("resolution_data", postgresql.JSONB, nullable=True),
    sa.Column("resolved_by", sa.Text, nullable=True),
    sa.Column("resolved_at", sa.BigInteger, nullable=True),
    sa.Column("created_at", sa.BigInteger, nullable=False, index=True),
    sa.Column("updated_at", sa.BigInteger, nullable=True),
    sa.Column("run_status", sa.Text, nullable=True, index=True),
    sa.ForeignKeyConstraint(
        ["session_id"],
        ["agent.sessions.session_id"],
        ondelete="CASCADE",
    ),
    schema="agent",
)
```

### 018: `agent.session_memories` (Bridge zu Hindsight)

Eigene Tabelle, nicht aus Agno, verknuepft unsere `agent.sessions` mit Hindsight `memory_units`.

```python
op.create_table(
    "session_memories",
    sa.Column("id", sa.Text, primary_key=True),  # uuid
    sa.Column("session_id", sa.Text, nullable=False, index=True),
    sa.Column("bank_id", sa.Text, nullable=False, index=True),  # hindsight bank
    sa.Column("memory_unit_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
    # Hindsight memory_units.id (nicht als FK weil Hindsight owned schema public.*)
    sa.Column("interaction_type", sa.Text, nullable=False, index=True),
    # recalled | retained | conflicted
    sa.Column("turn_number", sa.Integer, nullable=True),  # welchen Turn betrifft es
    sa.Column("relevance_score", sa.Float, nullable=True),
    sa.Column("metadata", postgresql.JSONB, nullable=True),
    sa.Column("created_at", sa.BigInteger, nullable=False, index=True),
    sa.ForeignKeyConstraint(
        ["session_id"],
        ["agent.sessions.session_id"],
        ondelete="CASCADE",
    ),
    schema="agent",
)
op.create_index(
    "ix_session_memories_bank_memory",
    "session_memories",
    ["bank_id", "memory_unit_id"],
    schema="agent",
)
```

**Warum keine FK zu Hindsight?**
- Hindsight managed `public.memory_units` selbst
- Cross-schema FKs in Postgres sind moeglich aber zerstoeren die Schema-Isolation
- Wir speichern die UUID als String und validieren zur Laufzeit

### 019: `personal_kb.*` (optionaler Bounded Context, Owner: `exec-personal-kb`)

`memory_kg.md` trennt klar:

- `personal memory` = interaktionsnah
- `personal knowledgebase` = kurationsnah

Wenn wir diese Schicht produktiv persistent machen, braucht sie einen eigenen
Bounded Context statt still in `agent` oder `public` aufzugehen.

Minimaler Schema-Vorschlag:

- `personal_kb.items` — gespeicherte Artefakte (`note`, `link`, `pdf`, `video`, `transcript`, `bookmark`)
- `personal_kb.annotations` — Highlights, Notes, Pins, Labels
- `personal_kb.links` — leichte Links zu Entities / World Evidence / Memory
- `personal_kb.import_jobs` — Markdown-/PKM-/Bookmark-Importe

Wichtige Felder fuer `items`:

- `id`
- `user_id`
- `artifact_type`
- `title`
- `source_uri`
- `storage_ref`
- `transcript_ref`
- `metadata`
- `created_at`
- `updated_at`
- `saved_at`
- `saved_from`
- `status`

Wichtige Regel:

- `personal_kb` ist System-of-record fuer bewusst gespeicherte User-Artefakte
- Links zu `memory` oder `world` sind Bridges, nicht zweite Wahrheiten

### 020: `world.*` (optionaler Bounded Context, Owner: `exec-world-model`)

`memory_kg.md` trennt klar:

- `global world evidence`
- `claim layer`
- `global world KG`

Selbst wenn der spaetere KG in FalkorDB / Kuzu / Hybrid landet, brauchen wir
fuer Postgres-nahe Metadaten und Auditing eine klare Welt-Seite.

Minimaler Schema-Vorschlag:

- `world.sources` — Quelle / Publisher / Feed / Snapshot-Metadaten
- `world.evidence_items` — extrahierte Evidenz-Einheiten
- `world.claims` — Claims mit Status / Freshness / Provenance-Qualitaet
- `world.claim_evidence` — Support-/Contradiction-Links zwischen Claim und Evidence

Wichtige Felder fuer `claims`:

- `id`
- `claim_text`
- `claim_type`
- `status`
- `support_count`
- `conflict_count`
- `freshness_score`
- `source_quality_prior`
- `entity_link_quality`
- `contradiction_risk`
- `metadata`
- `created_at`
- `updated_at`

Wichtige Regel:

- `world.claims` ist nicht identisch mit dem spaeteren Graph-of-record
- relationale Metadaten + KG + Vector koennen koexistieren, Rollen bleiben getrennt

---

## Migration Sequenz

| Nr | Migration | Depends On | Kritisch? |
|----|-----------|-----------|-----------|
| 011 | `sessions` | 010 | Ja — Grundlage fuer alles |
| 012 | `evals` | 011 | Nein — kann spaeter |
| 013 | `metrics` | 011 | Nein — aggregated data |
| 014 | `traces` + `spans` | 011 | Ja — exec-17 persistence |
| 015 | `components` + `component_configs` + `component_links` | 011 | Ja — exec-17 Phase 5/6 |
| 016 | `schedules` + `schedule_runs` | 011 | Nein — Cron mode |
| 017 | `approvals` | 011 | Nein — erweitert exec-12 |
| 018 | `session_memories` | 011 | Nein — Hindsight bridge |
| 019 | `personal_kb.items` + `annotations` + `links` + `import_jobs` | 011 / Storage-Entscheidungen | Nein — Phase 2/3 |
| 020 | `world.sources` + `evidence_items` + `claims` + `claim_evidence` | 011 / Ingestion-Entscheidungen | Nein — Phase 3 |

---

## Backwards Compatibility

### `audit_events` vs `traces/spans`

**Uebergangsstrategie:**
1. Beide schreiben parallel (audit_events bleibt, traces/spans neu)
2. Neue Queries nutzen traces/spans (reichere Daten, FK zu sessions)
3. `audit_events` wird fuer Compliance/Audit weitergefuehrt
4. Spaeter: `audit_events` kann via View auf `traces/spans` reduziert werden

**Kein Delete, keine Migration von Daten.**

### `skills_state` vs `components`

**Uebergangsstrategie:**
1. `skills_state` bleibt fuer exec-10 Trace2Skill
2. Neue Skills auch als `components` mit `component_type='skill'` registriert
3. Migration-Script: Bestehende skills_state → components + component_configs (optional, Phase 2)

### `consent_overrides` vs `approvals`

**Uebergangsstrategie:**
1. `consent_overrides` bleibt fuer statische Policies
2. `approvals` ist fuer Runtime-Approval-Requests mit expiration
3. `approval_node.py` schreibt in beide

### Harness Filesystem → DB

**exec-17 Phase 5/6 nutzt `data/harness/candidates/v{NNN}/`. Migration:**
1. Script liest alle `config.json` + `proposal.json` + `scores.json`
2. INSERT in `components` + `component_configs` + `evals`
3. Alte Dateien bleiben als Backup
4. `harness/proposer.py` schreibt neue Varianten direkt in DB

---

## Agent Code Changes

### `agent/sessions.py` (neu)

Abstraction layer ueber `agent.sessions` table:
- `create_session(user_id, source, agent_id) -> session_id`
- `update_session(session_id, summary, status, ...)`
- `link_memory(session_id, memory_unit_id, interaction_type)`
- `get_session(session_id) -> Session`

### `agent/graph/runner.py` (erweitern)

```python
async def _run_graph(ctx, messages, system_prompt):
    # exec-18: Create session row at start
    from agent.sessions import create_session, update_session
    session = await create_session(
        user_id=ctx.user_id,
        session_type="agent_chat",
        agent_id=ctx.agent_id,
        bank_id=f"user-{ctx.user_id}",  # hindsight bank
    )
    ctx.session_id = session.session_id

    with session_span(session.session_id, ctx.user_id, "agent_chat", "default") as span:
        try:
            result = await graph.ainvoke(initial_state, config=config)
            await update_session(
                session.session_id,
                status="completed",
                summary={"total_turns": result.get("iteration", 0), ...},
            )
        except Exception as e:
            await update_session(session.session_id, status="errored")
            raise
```

### `agent/tracing.py` (erweitern)

Zusaetzlicher OTel SpanProcessor der in `agent.traces` + `agent.spans` schreibt:

```python
class PostgresSpanProcessor(SpanProcessor):
    def on_end(self, span):
        # INSERT INTO agent.spans (span_id, trace_id, ..., attributes, events)
        # VALUES (...)
        ...
```

So fliessen OTel Spans **gleichzeitig** nach OpenObserve UND Postgres.

### `agent/harness/config.py` (erweitern)

```python
async def save_config_to_db(config: HarnessConfig, component_id: str) -> int:
    """Save a HarnessConfig as component_configs row. Returns version number."""
    # SELECT MAX(version) FROM agent.component_configs WHERE component_id = ?
    # INSERT INTO agent.component_configs (component_id, version+1, stage='draft', config, ...)
    ...

async def load_pareto_frontier() -> list[HarnessConfig]:
    """Load all Pareto-optimal component configs from DB."""
    # SELECT * FROM agent.component_configs WHERE pareto_frontier = true
    ...
```

### `agent/harness/evaluator.py` (erweitern)

```python
async def evaluate_search_set(component_id: str, version: int) -> dict:
    # Run agent with specified component config
    # INSERT result into agent.evals
    ...
```

---

## MCP Trace Server Anpassungen (exec-17 Phase 4)

`agent/mcp_traces.py` Tools koennen jetzt direkt aus Postgres queryen statt nur aus audit_events:

```python
@trace_mcp.tool(name="trace_detail")
async def trace_detail(session_id: str) -> str:
    """Get full trace: session + runs + spans + memory links."""
    sql = """
        SELECT s.*, t.trace_id, t.name, sp.*, sm.memory_unit_id
        FROM agent.sessions s
        LEFT JOIN agent.traces t ON t.session_id = s.session_id
        LEFT JOIN agent.spans sp ON sp.trace_id = t.trace_id
        LEFT JOIN agent.session_memories sm ON sm.session_id = s.session_id
        WHERE s.session_id = %(session_id)s
        ORDER BY sp.start_time
    """
    ...
```

---

## Zusammenfassung: Was, Wann, Warum

**WICHTIG — Nummern-Mapping:** Spec-Nummern 011-018 sind VERALTET. Tatsaechliche Alembic-Nummern 011-014 waren schon belegt (selected_models, default_mode, utility_models, agent_skills). Reale Migrationen:

| Spec-Nr | Reale Nr | Was | Status (2026-04-16) |
|---------|----------|-----|---------------------|
| — | **014** agent_skills | Skills DB Schema | ✅ gebaut + verifiziert |
| — | **015** skill_extensions | skill_type + assets JSONB (ALTER TABLE) | ✅ gebaut + verifiziert |
| 011 | **016** sessions | `agent.sessions` + `agent/sessions.py` CRUD | ✅ gebaut + verifiziert |
| 014 | **017** traces_spans | `agent.traces` + `agent.spans` | ✅ Tabellen gebaut, PostgresSpanProcessor TODO |
| 015 | **018** components | `agent.components` + `component_configs` + `component_links` | ✅ Tabellen gebaut, Proposer-Integration TODO |
| 012 | **019** (geplant) | `agent.evals` | noch nicht gebaut |
| 013 | **020** (geplant) | `agent.metrics` | noch nicht gebaut |
| 017 | **021** (geplant) | `agent.approvals` | noch nicht gebaut |
| 018 | **022** (geplant) | `agent.session_memories` (Hindsight Bridge) | noch nicht gebaut |
| 016 | **023** (geplant) | `agent.schedules` + `schedule_runs` | noch nicht gebaut |
| 019 | **024** (geplant) | `personal_kb.*` | noch nicht gebaut |
| 020 | **025** (geplant) | `world.*` | noch nicht gebaut |

**Gebaut (Phase 1, 2026-04-16):** 014 + 015 + 016 + 017 + 018
**Naechster Schritt:** PostgresSpanProcessor (017 Runtime-Integration), Proposer→component_configs (018 Integration), evals (019)
**Spaeter:** 020-025

---

## Ergaenzung (Plan 2026-04): `agent_skills` + Memory-A/B in `agent.evals`

**Zweck:** [`exec-skills.md`](./exec-skills.md) und [`exec-memory.md`](./exec-memory.md) ohne neue „Wahrheit“ duplizieren — hier nur **Schema-Entwurf**, Migration wenn Persistenz gewuenscht. **Agno-Referenz:** `_ref/agno/libs/agno/agno/db/postgres/schemas.py` (Patterns, nicht 1:1 kopieren).

### `agent.agent_skills` + `user_skill_preferences` (Entwurf)

Align mit exec-skills §3a: Spalten `id`, `name`, `description`, `content`, `tier`, `owner_id`, `generation`, `parent_skill_id`, `success_count`, `usage_count`, `enabled`, `api_version` (Schema-Drift), Timestamps. Zweite Tabelle: User-Deaktivierung pro Skill (`user_id`, `skill_id`, `disabled`).

- **Umsetzung (Matrix python-backend):** Alembic **`014_agent_skills.py`** — `agent.agent_skills` + `agent.user_skill_preferences` (`schema="agent"`). Loader bleibt bis Seed filesystem-basiert; nach `alembic upgrade head` DB bereit.
- **Beziehung zu `components`:** optional Skills zusaetzlich als `component_type='skill'` (exec-18 Open Questions Punkt 4) — Policy vor Migration festlegen.
- **Runtime-Pfad:** `agent/skills/store_db.py` + `scripts/seed_agent_skills.py`; **Alembic erstellt nur Tabellen**. Runtime-Zugriff, Seed und spaeteres Umschalten `filesystem|db|hybrid` passieren bewusst ausserhalb der Migration.

### `agent.evals` — `eval_type` Erweiterung `memory_ab`

Fuer MemPalace-vs-Hindsight-Vergleiche (gleiche Queries, zwei Pipelines):

- **`eval_type`:** `memory_ab` (oder `memory_retrieval_ab`)
- **`eval_input` (JSONB):** z. B. `{ "corpus_id": "...", "queries": ["q1", ...], "pipelines": ["hindsight", "mempalace"] }`
- **`eval_data` (JSONB):** Metriken pro Pipeline — R@k, Latenz, Token-Kosten, Fehlerquote

Keine neue Tabelle noetig solange ein Run = eine Zeile in `evals` reicht.

---

## Verify / offene Punkte (Plan 2026-04)

- [ ] Alembic `014_agent_skills.py` gegen echte DB verifizieren
- [ ] Entscheiden, ob `agent.agent_skills` zusaetzlich einen Unique-Constraint auf (`name`,`tier`,`owner_id`) braucht
- [ ] Entscheiden, ob Skills parallel als `components` registriert werden oder bewusst getrennt bleiben
- [ ] `memory_ab` Write-/Aggregation-Pfad existiert (`agent/harness/evals_store.py`, `scripts/persist_memory_ab_eval.py`, `experiments/memory_eval/aggregate_memory_ab.py`); Hindsight-Runner existiert, echter MemPalace-Runner / Evaluator-Kopplung noch offen
- [ ] Entscheiden, ob `personal_kb` ein eigenes Postgres-Schema wird oder nur logisch ueber Artefaktstores modelliert wird
- [ ] Entscheiden, wie stark `world.claims` relationale Metadaten vs. Graph-of-record nur spiegeln statt doppeln
- [ ] `component_configs` / HarnessConfig auf `consumer_type` / layer-aware Policies pruefen (siehe `exec-harness.md`)
- [ ] **API-Version / Schema-Drift breit:** `api_version` existiert auf `agent_skills` (exec-skills §6.6). Gleiche Logik sollte auf `component_configs` (Harness-Configs referenzieren Tool-APIs), und auf Hindsight Memory-Units (gespeicherte Tool-Call-Patterns mit alter API ungueltig). Aktuell nur Skills-Scope; breitere Umsetzung nach exec-18 Tabellen.

---

## Open Questions

1. **Schreibt `PostgresSpanProcessor` blocking oder async?**
   - Agno macht es async via Background Task Queue
   - OTel BatchSpanProcessor ist schon async
   - Wir nutzen den gleichen Pattern

2. **Retention fuer `traces`/`spans`?**
   - OpenObserve hat automatische Retention
   - Postgres nicht — wir brauchen Cron (nightly delete > 90 days?)
   - `metrics` Aggregation kann vor Delete laufen

3. **Wie weit Agnos Component-Konzept fuehren?**
   - Agnos `components` sind Agent-Instances mit Versionen
   - Wir koennten auch Tools als Components speichern (tool_id + version)
   - Oder bleiben bei Tools in `ToolRegistry` Code + nur Agent Configs als Components

4. **Migration der exec-10 `skills_state` Daten?**
   - Skills sind auch Components (type='skill')
   - Script oder manueller Cutover?

5. **Bank-ID Convention fuer Hindsight Integration?**
   - Aktuell: `user-{user_id}`
   - Pro Role? `user-{user_id}-{role}` (wie in Hindsight-Docs vorgesehen?)
   - Muss mit Hindsight-Integrations Team abgestimmt werden

6. **Wie weit ziehen wir Bounded Contexts physisch durch?**
   - `personal_kb` / `world` nur logisch?
   - oder echte Schemas ab Migration 019/020?
   - Entscheidung haengt an Ownership, Privacy und Infra-Komplexitaet

---

## Verify-Gates

**Verifiziert (2026-04-16):**
- [x] Migrationen 014-018 laufen durch ohne Fehler (podman PG 5433/hindsight_dev)
- [x] `agent.sessions` CRUD: `create_session()` → status='active', `update_session()` → status='completed' + summary JSONB, `get_session()` → dict zurueck. Smoke-Test bestanden.
- [x] 16 Tabellen im `agent` Schema nach 018 (agent_skills, sessions, traces, spans, components, component_configs, component_links, + 9 bestehende)
- [x] Hindsight Schema unveraendert (public.* nicht beruehrt)
- [x] `audit_events` laufen weiter (SKILL_* Events parallel zu neuen Tabellen)

**Noch offen:**
- [x] PostgresSpanProcessor in `agent/tracing.py` gebaut — `AGENT_PERSIST_TRACES=1` exportiert OTel Spans → `agent.traces` + `agent.spans` (2026-04-16)
- [x] `agent/graph/runner.py:_run_graph()` erstellt Session-Row via `create_session()` bei Start, updated `completed`/`errored` am Ende (2026-04-16)
- [x] Proposer legt Component Config als `draft` in `agent.component_configs` an. Env `HARNESS_SAVE_MODE=db|filesystem|both` (default both). `pareto.py` merged DB+FS dedupliziert. (2026-04-16)
- [ ] Evaluator speichert Ergebnis in `agent.evals` (Migration 019 noch nicht gebaut)
- [ ] Pareto-Frontier Flag auf component_configs wird korrekt gesetzt
- [ ] MCP Trace Tools liefern reichere Daten (Session + Trace + Spans + Memory)
- [ ] `personal_kb`-Persistenz landet nicht still in `agent.sessions` oder Hindsight-Banken
- [ ] `world`-Claims/Evidence sind von Personal Memory physisch oder mindestens logisch getrennt
- [ ] !! `agent.sessions` vs Hindsight `operations`/`banks` Abgleich — siehe exec-memory §8.6
