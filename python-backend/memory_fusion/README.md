# memory_fusion — Unified Runtime (PRIMARY)

**This is the canonical memory runtime for matrix.** It unifies Hindsight and
MemPalace behind a single fusion engine.

## Relationship to the other memory dirs

| Dir | Status | Purpose |
|---|---|---|
| `python-backend/memory_fusion/` (**this**) | **primary** | Unified Hindsight + MemPalace. Summary/Fact paths from Hindsight are composed with a local MemPalace-inspired verbatim layer. New code and integrations should target this module. |
| `python-backend/agent/memory/` | legacy-adjacent | Hindsight-focused engine-selector (`AGENT_MEMORY_ENGINE=hindsight\|mempalace`). Predecessor of `memory_fusion`; the fusion engine was derived from a copy of it. Still referenced by some call-sites. |
| `python-backend/memory_engine/` | oldest | Phase-6 KG / Vector / Episodic store primitives. Building blocks that the higher-level engines above consume. |

## Entry points

- `FusionMemoryEngine` — the runtime class that composes the layers.
- `get_memory_engine()`, `get_memory_provider()`, `get_bank_id()` — factory
  helpers re-exported from `__init__.py`.

## exec-hermes §3.2 note

exec-hermes §3.2 (MemoryProvider ABC + MemoryManager) targets **this** module
— the planned refactor is to lift a shared `MemoryProvider` ABC out of the
fusion engine so that Hindsight, MemPalace, and future providers (PersonalKB,
WorldModel) plug in uniformly. The legacy `agent/memory/` selector is the
migration source, not the destination.
