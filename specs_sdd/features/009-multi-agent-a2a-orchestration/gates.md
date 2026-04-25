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

- [ ] Graph compiles.
- [ ] LLM/tool loop works.
- [ ] Approval interrupt/resume works.
- [ ] Max iterations stop works.
- [ ] Legacy fallback status is clear.

## G2 Trading Roles

- [ ] Six roles exist.
- [ ] Role prompts are applied.
- [ ] Role-specific tool filtering works.
- [ ] Orchestrator parallel/aggregate/sequential path works.
- [ ] Completion contracts are enforced.

## G3 Skills

- [ ] Global/team/personal loading works.
- [ ] Override semantics work.
- [ ] Skill prompt injection works.
- [ ] GitHub import works with host/path validation.
- [ ] ZIP install blocks path traversal/symlinks/oversize.
- [ ] Skill evolution and dedup status is explicit.

## G4 A2A

- [ ] AgentCards serialize.
- [ ] A2A client local call works.
- [ ] Delegation node sends to target.
- [ ] Target receives bounded task.
- [ ] Result returns to source.
- [ ] Logs/traces show both agents.

## G5 Matrix / Per-User Routing

- [ ] Mention resolves target agent.
- [ ] Dynamic reply identity works.
- [ ] Default-user-agent routing decision is recorded.
- [ ] Username sanitization utility exists before external registration use.
- [ ] Per-user model/agent routing visible.

## G6 Paper-Derived Learning

- [ ] MetaClaw fast loop status verified.
- [ ] Trace2Skill consolidation verified or deferred.
- [ ] NLAH completion/file-backed-state verified or deferred.
- [ ] PRM/LoRA/OMLS remain disabled unless explicitly enabled.

## G7 Control UI

- [ ] Agents tab reflects backend or empty state.
- [ ] A2A tab reflects backend or empty state.
- [ ] Delegation log exists or is marked optional.
