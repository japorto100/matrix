# agent/memory — Hindsight-focused engine selector (LEGACY-ADJACENT)

Not the canonical runtime. The canonical runtime is
[`python-backend/memory_fusion/`](../../memory_fusion/README.md), which
unifies Hindsight **and** MemPalace.

## What lives here

- Engine-selector Auto-Retain / Auto-Recall scaffolding. Runtime engine is
  selectable via `AGENT_MEMORY_ENGINE` (default `hindsight`, alt
  `mempalace`).
- Hindsight-oriented building blocks used by the selector.
- Per-user bank isolation helpers.

## Relationship to the other memory dirs

| Dir | Status | Purpose |
|---|---|---|
| `python-backend/memory_fusion/` | **primary** | Unified Hindsight + MemPalace runtime. New code goes here. |
| `python-backend/agent/memory/` (**this**) | legacy-adjacent | Engine-selector predecessor. `memory_fusion` was derived as a copy of this tree. Some matrix call-sites still import from here — migration is in progress. |
| `python-backend/memory_engine/` | oldest | Low-level KG / Vector / Episodic primitives. |

## Migration direction

- Prefer `from memory_fusion import ...` for anything new.
- exec-hermes §3.2 will extract a shared `MemoryProvider` ABC from
  `memory_fusion`; `agent/memory/` is expected to be the migration source,
  not a long-term destination.
