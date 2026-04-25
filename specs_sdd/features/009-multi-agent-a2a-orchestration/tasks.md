---
title: Multi-Agent and A2A Orchestration Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 009
migrated_from:
  - specs/execution/exec-10-multi-agent.md
---

# Tasks

## Migration / SDD

- [x] T001 Summarize implemented LangGraph/trading roles/skills/A2A phases.
- [x] T002 Preserve paper sources: MetaClaw, Trace2Skill, NLAH, Hermes
  multi-agent patterns.
- [x] T003 Split implemented, disabled and research-only learning features.
- [x] T004 Preserve Phase 7 orchestrator/per-user routing open decisions.

## LangGraph / Roles

- [ ] T010 Verify `create_agent_graph()` compiles.
- [ ] T011 Verify LLM -> tool -> tool_execute -> LLM -> response graph path.
- [ ] T012 Verify approval interrupt/resume.
- [ ] T013 Verify max-iteration stop.
- [ ] T014 Verify legacy fallback status or remove from SDD if no longer exists.
- [ ] T015 Verify six trading roles and role-specific tool filtering.
- [ ] T016 Verify orchestrator parallel analysis and sequential decision path.
- [ ] T017 Verify Researcher/Trader/RiskManager completion contracts.

## Skills / Learning

- [ ] T020 Verify 3-tier skill loading and override semantics.
- [ ] T021 Verify skill prompt injection by role/category.
- [ ] T022 Verify GitHub import and `.skill` archive install security checks.
- [ ] T023 Verify auto skill generation when enabled.
- [ ] T024 Verify deduplication by failure hash.
- [ ] T025 Verify temporal context injection.
- [ ] T026 Verify PRM/LoRA/OMLS disabled infrastructure instantiates without
  activating training.
- [ ] T027 Verify Trace2Skill consolidation graph or mark research/deferred.
- [ ] T028 Verify file-backed state recovery.

## A2A / Delegation

- [ ] T030 Verify AgentCard JSON serializes for all six roles.
- [ ] T031 Verify A2A client sends message to local target agent.
- [ ] T032 Run A2A live delegation smoke via orchestrator and `a2a_node`.
- [ ] T033 Verify result returns to source agent and state/log records both
  agents.
- [ ] T034 Verify remote-agent ENV routing or mark remote A2A as deferred.

## Matrix / Per-User Routing

- [ ] T040 Verify Matrix mention routes to expected `target_agent`.
- [ ] T041 Decide default-agent routing convention for user DMs.
- [ ] T042 Implement/verify username sanitization utility before trading-project
  registration hook depends on it.
- [ ] T043 Verify per-user default model lookup.
- [ ] T044 Design/verify per-user agent settings: prompt, memory scope, skills
  and tool allowlist.
- [ ] T045 Decide subagent visibility: invisible LangGraph nodes, Matrix
  identities or hybrid.

## Control UI / Observability

- [ ] T050 Verify Agents tab reflects configured agents.
- [ ] T051 Verify A2A tab shows AgentCards/status or actionable empty state.
- [ ] T052 Verify delegation log if enabled.
- [ ] T053 Cross-link trace/span requirements to Feature 014.

## Verify Gates

- [ ] Agent A delegates to Agent B.
- [ ] Delegation result returns to caller.
- [ ] Matrix mention path works.
- [ ] Routing decision is observable.
- [ ] Paper-derived learning features have explicit status.
