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
  - 2026-04-30 static: `make_runtime_event()` now derives non-empty `run_id`
    and `session_id` from supplied session/thread identity, with event-id
    fallback for local provider-free runs. Scoped retrieval events now preserve
    thread/session identity in the event envelope before audit replay.
- [x] G002 Runtime events preserve tool_call_id where applicable.
  - 2026-04-30: `tool_node` runtime events include `tool_call_id` for started
    and result paths, and focused tests assert the id survives audit metadata.
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
  - 2026-04-30: confirmed session kill emits status `cancelled` with metadata
    `outcome=killed`, preserving a stable distinction without widening the
    global runtime-event status enum.
  - 2026-04-30: every new runtime event now gets a provider-agnostic
    `metadata.outcome` derived from status/name/reason unless the producer
    explicitly supplied one. Timeout and killed outcomes are preserved as
    first-class replay taxonomy values rather than inferred from UI labels.
- [partial-static] G007 Control operations return explicit supported/unsupported outcomes.
  - 2026-04-30: MCP and skill reload preview/confirm paths return explicit
    status plus cache-impact runtime events. Pause/kill/replay controls still
    need backend operation support.
  - 2026-04-30: Session status/kill/pause/replay endpoints now return explicit
    supported, confirmation-required or unsupported runtime events; durable
    pause/replay execution remains open.
- G008 Meta-Harness can replay event streams without browser dependencies.
  - 2026-04-30: provider-free routing contract includes
    `routing-runtime-event-replay-identity`, which validates the replay
    envelope and redaction policy without starting the frontend or a browser.
  - 2026-04-30: provider-free routing contract also includes
    `routing-runtime-event-kind-outcome-taxonomy`, validating event kind/name
    consistency and stable outcomes across LLM, tool, memory, subagent and
    control events.
