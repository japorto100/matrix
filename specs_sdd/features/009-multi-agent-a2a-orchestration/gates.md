---
title: Multi-Agent A2A Orchestration Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
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
- [ ] Delegation node sends to target.
- [ ] Target receives bounded task.
- [ ] Result returns to source.
- [ ] Logs/traces show both agents.

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

## G6 Paper-Derived Learning

- [ ] MetaClaw fast loop status verified.
- [ ] Trace2Skill consolidation verified or deferred.
- [ ] NLAH completion/file-backed-state verified or deferred.
- [ ] PRM/LoRA/OMLS remain disabled unless explicitly enabled.

## G7 Control UI

- [ ] Agents tab reflects backend or empty state.
- [ ] A2A tab reflects backend or empty state.
- [ ] Delegation log exists or is marked optional.
