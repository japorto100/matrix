# memory_engine — Low-level KG / Vector / Episodic primitives (OLDEST)

Phase-6 foundation layer. Not the place for new agent-level memory
features — those belong in
[`python-backend/memory_fusion/`](../memory_fusion/README.md).

## What lives here

Primitives that higher-level engines (`memory_fusion`, `agent/memory`)
consume:

- Knowledge-graph store adapters
- Vector store adapters
- Episodic memory primitives

## Relationship to the other memory dirs

| Dir | Status | Purpose |
|---|---|---|
| `python-backend/memory_fusion/` | **primary** | Unified Hindsight + MemPalace runtime. Consumes primitives from here. |
| `python-backend/agent/memory/` | legacy-adjacent | Hindsight-focused engine-selector. Predecessor of `memory_fusion`. |
| `python-backend/memory_engine/` (**this**) | oldest | Building blocks — KG / Vector / Episodic stores. Not a runtime itself. |

## When to touch

- Adding a new vector-store backend, a new KG driver, or a new episodic-
  store pattern — land it here.
- Agent-level memory behaviour (recall, retain, fusion, compaction hooks) —
  that belongs in `memory_fusion`, not here.
