---
title: Multi-Agent and A2A Orchestration Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-30
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

- [x] T010 Verify `create_agent_graph()` compiles.
- T011 Verify LLM -> tool -> tool_execute -> LLM -> response graph path.
- T012 Verify approval interrupt/resume.
- [x] T013 Static-test max-iteration route to retain.
- T014 Verify legacy fallback status or remove from SDD if no longer exists.
- [x] T015 Verify six trading roles and role-specific tool filtering.
- T016 Verify orchestrator parallel analysis and sequential decision path live.
- [x] T017 Static-test Researcher/Trader/RiskManager completion contracts exist.
- [x] T018 Verify `create_orchestrator_graph()` compiles and aggregate node
  summarizes assistant analyses.
- T019 Implement async PostgreSQL checkpoint lifecycle or document
  intentional in-memory graph checkpointing.

## Skills / Learning

- T020 Verify 3-tier skill loading and override semantics.
- T021 Verify skill prompt injection by role/category.
- T022 Verify GitHub import and `.skill` archive install security checks.
- T023 Verify auto skill generation when enabled.
- T024 Verify deduplication by failure hash.
- T025 Verify temporal context injection.
- T026 Verify PRM/LoRA/OMLS disabled infrastructure instantiates without
  activating training.
- T027 Verify Trace2Skill consolidation graph or mark research/deferred.
- T028 Verify file-backed state recovery.

## A2A / Delegation

- [x] T030 Verify AgentCard JSON serializes for all six trading cards.
- [x] T031 Static-test A2A client sends message to local target URL and
  collects AI-SDK `text-delta.delta` response text.
- T032 Run A2A live delegation smoke via orchestrator and `a2a_node`.
- T033 Verify result returns to source agent and state/log records both
  agents.
- T034 Verify remote-agent ENV routing or mark remote A2A as deferred.

## Matrix / Per-User Routing

- [x] T040 Static-test Matrix mention reply identity path in Feature 006 bridge
  test; live Matrix mention routing remains pending.
- [x] T041 Decide default-agent routing convention for user DMs.
- [x] T042 Implement/verify username sanitization utility before trading-project
  registration hook depends on it.
- [x] T043 Verify per-user default model lookup.
- [x] T044 Design/verify per-user agent settings: prompt, memory scope, skills
  and tool allowlist.
- T045 Decide subagent visibility: invisible LangGraph nodes, Matrix
  identities or hybrid.
- [partial-static] T046 Add Matrix mention/thread/free-response routing gates from Hermes Matrix
  fixes: group messages require explicit mention/reply unless room is
  allowlisted, DMs route to default/target agent, and thread roots are
  preserved in delegated replies.
  - 2026-04-30: Python bridge now preserves Matrix event/thread metadata into
    Agent Chat context and fails closed on thread replies without a root. Go
    group-room allowlist/live Matrix behavior and delegated reply handoff
    remain open.

## Control UI / Observability

- T050 Verify Agents tab reflects configured agents.
- T051 Verify A2A tab shows AgentCards/status or actionable empty state.
- T052 Verify delegation log if enabled.
- T053 Cross-link trace/span requirements to Feature 014.

## Verify Gates

- Agent A delegates to Agent B live.
- [x] A2A client parses delegation result payload.
- [x] Base graph/orchestrator compile and role allowlists are statically tested.
- Matrix mention path works.
- Routing decision is observable.
- Paper-derived learning features have explicit status.
