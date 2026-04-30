---
title: Multi-Agent A2A Orchestration Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-30
feature_id: 009
---

# Gates

## G1 LangGraph Base

- [x] Graph compiles.
- [ ] LLM/tool loop works.
- [ ] Approval interrupt/resume works.
- [x] Max-iteration routing decision is unit-tested.
- [ ] Legacy fallback/checkpointer status is clear for production persistence.

## G2 Trading Roles

- [x] Six roles exist.
- [x] Role prompts exist and orchestrator nodes compile.
- [x] Role-specific tool filtering works in `tool_node`.
- [x] Orchestrator compiles and aggregate node is unit-tested.
- [ ] Orchestrator parallel/aggregate/sequential path works live.
- [ ] Completion contracts are enforced, not only defined.

## G3 Skills

- [ ] Global/team/personal loading works.
- [ ] Override semantics work.
- [ ] Skill prompt injection works.
- [ ] GitHub import works with host/path validation.
- [ ] ZIP install blocks path traversal/symlinks/oversize.
- [ ] Skill evolution and dedup status is explicit.

## G4 A2A

- [x] AgentCards serialize for the six trading cards.
- [x] A2A client local HTTP call and SSE text parsing is unit-tested.
- [partial-static] Delegation node sends to target.
  - 2026-04-30: unit test verifies configured target URL is used only after
    depth gate permits it; live target smoke remains pending.
- [x] Target receives bounded task.
  - 2026-04-30: A2A context carries role, parent thread id, spawn depth,
    explicit-context-only memory scope and child tool policy.
- [partial-static] Result returns to source.
  - 2026-04-30: unit test verifies child result becomes source
    `final_response`; live orchestrator path remains pending.
- [partial-static] Logs/traces show both agents.
  - 2026-04-30: runtime events cover accepted/started/completed/failed/stale
    states and child task id/digest. Durable `a2a_delegations` logging remains
    pending.

## G4a Checkpointing

- [x] Local graph compile is not broken by `HINDSIGHT_DB_URL`.
- [ ] Async PostgreSQL saver lifecycle is implemented in the graph runner or
  explicitly deferred.

## G5 Matrix / Per-User Routing

- [ ] Mention resolves target agent in a live Matrix room.
- [x] Dynamic reply identity works in the Python bridge static test.
- [x] Default-user-agent routing decision is recorded.
- [x] Username sanitization utility exists before external registration use.
- [x] Per-user default model lookup is static-tested.
- [ ] Per-user agent routing/settings are visible.
- [ ] Group-room free-response behavior is allowlist-gated and does not create
  echo loops.
- [partial] Thread-root metadata survives Matrix mention/default-agent routing
  and any future delegate handoff. Python bridge preserves thread roots and
  rejects malformed thread replies; delegate handoff remains open.

## G6 Paper-Derived Learning

- [ ] MetaClaw fast loop status verified.
- [ ] Trace2Skill consolidation verified or deferred.
- [ ] NLAH completion/file-backed-state verified or deferred.
- [ ] PRM/LoRA/OMLS remain disabled unless explicitly enabled.

## G7 Control UI

- [ ] Agents tab reflects backend or empty state.
- [ ] A2A tab reflects backend or empty state.
- [ ] Delegation log exists or is marked optional.
