---
title: Agent Runtime Event Recovery Gates
status: planned
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 033
---

# Gates

- G001 Every model/tool/memory/retrieval/subagent event has run and session
  identity.
- G002 Runtime events preserve tool_call_id where applicable.
- G003 Raw secrets, provider reasoning and oversized payloads are redacted or
  capped.
- G004 Subagent execution is fail-closed unless explicitly enabled.
- G005 Child runs cannot directly mutate shared memory, KG or schedule state.
- G006 Stale, timeout, killed and cancelled states are distinguishable.
- G007 Control operations return explicit supported/unsupported outcomes.
- G008 Meta-Harness can replay event streams without browser dependencies.

