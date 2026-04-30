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
  - 2026-04-30 partial: scoped RAG/KG audit rows preserve thread/session when
    callers provide them. Full run/session identity across every event producer
    remains open.
  - 2026-04-30 partial: memory audit rows preserve thread id and runtime
    envelope metadata for recall/retain replay.
- G002 Runtime events preserve tool_call_id where applicable.
- [x] G003 Raw secrets, provider reasoning and oversized payloads are redacted
  or capped.
  - 2026-04-30: runtime event payloads use the shared redaction contract, and
    Ops read-model tests assert nested secrets are redacted before UI exposure.
- [x] G004 Subagent execution is fail-closed unless explicitly enabled.
  - 2026-04-30: `a2a_delegate_node` default path blocks before client
    creation and records `a2a_delegation_spawn_depth_blocked`.
- [x] G005 Child runs cannot directly mutate shared memory, KG or schedule state.
  - 2026-04-30: child tool policy blocks memory-write, schedule/send,
    recursive delegation and code/sandbox execution by default.
- [partial-static] G006 Stale, timeout, killed and cancelled states are distinguishable.
  - 2026-04-30: A2A timeout maps to stale runtime event plus
    `a2a_delegation_timeout`; kill/cancel still need Control operation support.
  - 2026-04-30: memory retain timeout maps to `memory.retain.timeout`,
    status `stale` and degradation flag `memory_retain_timeout`.
- G007 Control operations return explicit supported/unsupported outcomes.
- G008 Meta-Harness can replay event streams without browser dependencies.
