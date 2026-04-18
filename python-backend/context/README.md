# context — Context Engineering Primitives (Phase 10b)

Operative owner per `specs/execution/exec-context.md`. Holds the rules for
**when** compaction-related events fire and **how** the final prompt is
assembled. Does **not** own persistence — that's `memory_fusion/`.

## Modules

| File | Purpose |
|---|---|
| `context_engine.py` | **ABC** + `DefaultContextEngine` (80/85/95 thresholds per exec-context §6.1). Classifies current context-window fill into `ContextStage.{normal, pre_save, compaction, emergency}` and exposes predicate helpers (`should_verbatim_retain`, `should_compact`, `should_emergency_compact`). |
| `merge.py` | Multi-source retrieval-fragment merge (KG / vector / episodic) ranked by policy. Referenced in exec-context §5 as `context/merge.py`. |
| `policy.py` | Retrieval policy — freshness, provenance, trust-level gating. Source layer for degradation flags (`NO_KG_CONTEXT`, `NO_PERSONAL_MEMORY`, etc.). |
| `relevance.py` | 4-dimension relevance score (freshness × proximity × confidence × regime-fit). |
| `token_budget.py` | Per-layer token allocator. |

## Entry points

- **`ContextEngine`** (ABC) — abstract base for all context engines.
- **`DefaultContextEngine`** — 2026-04-18 canonical 80/85/95 thresholds.
- **`ContextStage`** enum — drives harness dispatch.
- Existing Phase-10b functions (`merge_fragments`, `allocate_budget`,
  `relevance_score`, `apply_context_policy`) remain exported.

## Architecture: peer-service pattern (SOTA 2026)

matrix follows the 2026 hermes + OpenClaw "two-surface plugin model":

```
   python-backend/agent/ (harness)
         │  orchestrates
         ├──► context.ContextEngine         (in-session, compaction-first)
         └──► memory_fusion.MemoryManager   (cross-session, retrieval-first)
```

### Contract boundaries

- **`ContextEngine` owns threshold semantics** (when to pre-save, compact,
  emergency-compact). It does **not** persist anything itself — it only
  decides whether "now" is the moment to trigger a lifecycle event.
- **`memory_fusion.MemoryProvider` owns persistence** (verbatim retain,
  recall, turn sync). It does **not** know what the current context
  window looks like or when compaction would kick in.
- **The agent harness** (`python-backend/agent/graph/runner.py`,
  `llm_node.py`, etc.) is the only component that holds references to
  both and mediates between them.

### Wiring shape (agent harness side)

```python
from context import DefaultContextEngine
from memory_fusion.memory_provider import auto_fusion_provider, MemoryManager

engine = DefaultContextEngine()                          # per-request is fine
fusion = await auto_fusion_provider(system_block=...)
providers = [fusion] if fusion else []
manager = MemoryManager(providers)

# per-turn boundary:
if engine.should_verbatim_retain(tokens=token_usage, window=context_window):
    await manager.on_pre_compress(
        messages, user_id=user_id, bank_id=bank_id,
    )
if engine.should_compact(tokens=token_usage, window=context_window):
    messages = rolling_summary(messages)  # compactor in context/merge.py (TBD)
```

**Explicitly avoid:** making `ContextEngine` hold a reference to
`MemoryManager`, or vice versa. That couples two independent evolution
paths and forces every context-engine change to consider memory semantics.
The harness is the only component that needs to know about both.

## References

- `specs/execution/exec-context.md` — operative owner of threshold semantics,
  prompt-order (§5), compaction-trigger rules (§6).
- `specs/execution/exec-memory.md` §3e / §3f — verbatim-capture pattern, the
  `on_pre_compress` hook rationale.
- `specs/execution/exec-hermes.md` §3.1 / §3.2 — porting provenance.
- `main_docs/root/CONTEXT_ENGINEERING.md` — token budget, relevance scoring,
  multi-source merging conceptual doc.

## Relationship to the other context-adjacent locations

- `python-backend/agent/context.py` — `AgentExecutionContext` dataclass
  (per-request immutable state). Different concern from this module (data
  container vs orchestration rules).
- `python-backend/agent/context_assembler.py` — concrete retrieval-fragment
  assembler (KG / episodic / vector). Consumes this module's `policy.py` +
  `merge.py` + `relevance.py`. Phase-10a.4.
- `python-backend/agent/control/context_runtime.py` — control-UI facing
  context-inspector. Consumes this module + `memory_fusion`.
