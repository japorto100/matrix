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

## Entry points (ABC layer — exec-hermes §3.2, landed 2026-04-18)

- **`MemoryProvider`** (ABC) — pluggable backend contract. Any provider
  implements: `name`, `is_available`, `prefetch`, `sync_turn`, optional
  `on_pre_compress` (the ≥80% context-window hook), `on_session_end`,
  `system_prompt_block`.
- **`MemoryManager`** — coordinator for N providers. Fan-out for every
  lifecycle call with per-provider error isolation (one crashing provider
  cannot starve the rest).
- **`FusionProvider`** — concrete adapter over `FusionMemoryEngine`.
- **`auto_fusion_provider()`** — factory that builds a default provider from
  the env-configured engine.
- `get_memory_engine()`, `get_memory_provider()`, `get_bank_id()` — legacy
  factory helpers re-exported from `__init__.py`.

Future concrete providers (dedicated `HindsightProvider`, `MemPalaceProvider`,
`PersonalKBProvider`, `WorldModelProvider`) plug into the same ABC; no change
to `MemoryManager` is needed.

## Architecture: peer-service pattern (SOTA 2026)

matrix follows the 2026 hermes + OpenClaw "two-surface plugin model":

```
   python-backend/agent/ (harness)
         │  orchestrates
         ├──► memory_fusion.MemoryManager   (cross-session, retrieval-first)
         └──► context.ContextEngine         (in-session, compaction-first)
```

Important:

- **Memory and Context are peer services** coordinated by the agent harness.
  They do **not** call each other. The context engine owns threshold
  semantics; the harness consults it and then — if the threshold is crossed —
  invokes the memory manager's `on_pre_compress` hook.
- This mirrors the empirical convergence in 2026: hermes publishes one slot
  for memory plugins (cross-session) and a separate slot for context-engine
  plugins (in-session). The two slots deliberately don't overlap, so each
  can evolve independently.
- Error isolation is the registry's job (see `MemoryManager` fan-out logic),
  not the providers'.

**Explicitly avoid:** making `ContextEngine` hold a reference to
`MemoryManager`, or vice versa. That couples two independent evolution
paths and forces every context-engine change to consider memory semantics.
The harness is the only component that needs to know about both.

## Relationship to legacy `agent/memory/` migration

The ABC is the *bridge* that lets callers migrate to `memory_fusion` at
their own pace:

1. Call-sites that currently import `agent/memory/engine.py:get_memory_engine()`
   can move to `memory_fusion.memory_provider.auto_fusion_provider()` —
   same shape, uniform interface.
2. Tests build a `MemoryManager([stub_provider])` directly — no Postgres /
   palace needed for unit tests (see `tests/test_memory_provider.py`).
3. Once all callers are on the ABC, `agent/memory/` becomes deletable
   (planned as a follow-up archive step — see plan file).
