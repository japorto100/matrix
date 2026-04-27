# memory_engine — Phase-6 Memory-Primitives Foundation

Three canonical memory-representation stores. **Foundation layer**, not a
runtime. Higher-level code (`memory_fusion/`, `agent/control/*`,
`kg_pipeline/`) consumes these primitives — nothing runs here.

Not to be confused with:

- [`memory_fusion/`](../memory_fusion/README.md) — unified **conversation-
  memory runtime** (Hindsight + MemPalace) with its own internal vector
  stores (ChromaDB, Hindsight-embeddings).
- [`kg_pipeline/`](../kg_pipeline/README.md) — **KG-extraction ETL** that
  proposes claim candidates. Feature 017 global claims use
  `global_kg.py`/`global_kg_store.py`; legacy `kg_store.py` remains for the
  Control UI seed graph.

## Contents — the three canonical memory types

Classical cognitive-memory architectures (ACT-R, SOAR) distinguish
three primary memory representations. This module provides one store
per type:

| Memory type | Module | What it stores | Backends |
|---|---|---|---|
| **Declarative / structural** | [`kg_store.py`](kg_store.py) | Legacy/control graph nodes + edges (stratagems, regimes, institutions, transmission channels…) | Kuzu (default) · SQLite (degraded fallback) · FalkorDB (optional legacy) |
| **Global/domain KG claims** | [`global_kg.py`](global_kg.py), [`global_kg_store.py`](global_kg_store.py) | Bitemporal world/trading/geopolitical claims with evidence refs and NornicDB projection outbox | Postgres/pgvector · in-memory smoke |
| **Episodic / temporal** | [`episodic_store.py`](episodic_store.py) | Time-stamped event records per agent role | SQLite (current) |
| **Semantic / similarity** | [`vector_store.py`](vector_store.py) | Text chunks + embeddings for approximate-match retrieval | pgvector (primary) · in-memory (tests) |

Plus supporting modules:

- [`models.py`](models.py) — request/response dataclasses shared with
  consumers (`EpisodeCreateRequest`, `KGNodesResponse`, `VectorSearchResult`,
  …). Stable API surface — changes here ripple through `agent/control/*`.
- [`seed_data.py`](seed_data.py) — curated KG seed content (`STRATAGEMS`,
  `REGIMES`, `INSTITUTIONS`, `TRANSMISSION_CHANNELS`). Shipped with the
  package.
- [`pyproject.toml`](pyproject.toml) — the module is a **standalone package**,
  not strictly a subfolder. Versioned independently.

## Producer → Consumer map

```
                          ┌─────────────────────────┐
                          │      memory_engine/     │
                          │  ┌──────────────────┐   │
│  │  kg_store.py     │   │
│  │  global_kg*.py   │   │
                          │  │  vector_store.py │   │
                          │  │  episodic_store  │   │
                          │  └──────────────────┘   │
                          └───┬──────┬──────┬───────┘
                reads         │      │      │         reads
          ┌───────────────────┘      │      └────────────────────┐
          ▼                          ▼                           ▼
┌─────────────────┐       ┌─────────────────────┐     ┌─────────────────┐
│ agent/control/  │       │ kg_pipeline/sinks/  │     │ tests/ +        │
│  overview       │       │   (write kg_store — │     │ scripts/smoke_* │
│  kg_context     │       │   D17 decoupling:   │     │                 │
│  kg_crud        │       │   pipeline MAY      │     │                 │
│  memory         │       │   import            │     │                 │
│  context        │       │   memory_engine)    │     │                 │
└─────────────────┘       └─────────────────────┘     └─────────────────┘
```

`memory_fusion/` does **not** currently consume from `memory_engine` — it
maintains its own internal vector stores scoped to conversation memory
(Hindsight-embeddings, MemPalace-ChromaDB).  The two are peer subsystems.

## When to touch

- **Adding a new legacy/control KG backend driver** → `kg_store.py`.
- **Changing global KG claim semantics/projection** → `global_kg.py`,
  `global_kg_store.py` and Feature 017 specs.
- **Adding a new vector DB backend** (e.g. Milvus) → `vector_store.py`.
- **Adding a new episodic pattern** → `episodic_store.py`.
- **Seeding new canonical nodes** (new stratagem set etc.) → `seed_data.py`.

**Do NOT add** higher-level runtime behaviour here (recall/retain/fusion
/compaction hooks — those belong in `memory_fusion/`). Do NOT add
extraction logic here (that's `kg_pipeline/`).

## Naming note — why "memory_engine" is a misnomer

The module predates the current naming convention and has kept "engine"
for historical reasons. Strictly it's **three Stores + models + seed
data**, not an engine (no orchestration loop, no hook lifecycle).

A more honest name would be `memory_stores/` or `memory_primitives/`,
but renaming would ripple into ~9 consumer files plus the module's
own `pyproject.toml` package identity and `kg_pipeline/` D17 decoupling
docs. The blast radius is not justified by the naming-hygiene win.

**Recommendation:** keep the name, document the misnomer here, and
prefer `memory_fusion/` when new code is about *conversation memory*
behaviour (recall/retain/compress), not primitives.

## If you're considering deleting this module

Short answer: don't. Long answer:

- **kg_store** has an irreplaceable consumer (`kg_pipeline/sinks/`) and
  the entire `agent/control/kg_*.py` surface.
- **vector_store** is used by `scripts/smoke_pgvector.py` and
  `agent/control/*`. Moving it into `memory_fusion/` would conflate
  conversation-memory embeddings with control-UI semantic search — two
  different use-cases.
- **episodic_store** is consumed by `agent/control/episodes.py` for the
  Control-UI episode list. `memory_fusion/` doesn't touch it.

Only deletion candidate would be if we decided to push **all three stores**
into their respective domain owners (kg_store → kg_pipeline, vector →
dedicated `search/` module, episodic → memory_fusion or agent/sessions).
That's a multi-week refactor with uncertain payoff. Not recommended
without a concrete driver.

## Cross-ref

- exec-memory §1 (memory-stack IST-Zustand) — lists `memory_engine/kg_store.py`
  as the M1 Semantic Memory backend.
- exec-18 — persistent agent schema; `agent.sessions` + `agent.traces` are
  separate from `memory_engine`'s stores (different concern: agent run
  history vs memory-typed knowledge).
- exec-world-model — future KG owner; eventually the authoritative
  KG for global claims. `kg_store.py` then becomes more scoped to
  personal/local KG or gets a second backend.
