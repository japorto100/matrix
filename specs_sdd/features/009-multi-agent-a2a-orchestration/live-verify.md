---
title: Multi-Agent and A2A Orchestration Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 009
---

# Live Verify

## Source Checks

- [ ] `exec-10` verify gates are represented in SDD.
- [ ] MetaClaw/Trace2Skill/NLAH status split is represented.
- [ ] Phase 7 orchestrator/per-user routing open decisions are represented.
- [ ] Control UI A2A references from Feature 010 are linked.

## LangGraph / Roles

- [ ] Start Python agent runtime.
- [ ] Run simple graph path without tools.
- [ ] Run graph path with safe tool call.
- [ ] Trigger approval interrupt and resume.
- [ ] Run orchestrator role path and inspect role outputs.
- [ ] Confirm completion gate rejects malformed role output.

## A2A Delegation

- [ ] Start Python agent runtime.
- [ ] Fetch AgentCard for target agent.
- [ ] Ask source agent to delegate a bounded task.
- [ ] Confirm target agent receives task.
- [ ] Confirm result returns to source agent.
- [ ] Confirm trace/log identifies both agents.

## Skills / Learning

- [ ] Load global/team/personal skills.
- [ ] Import a safe SKILL.md from local/GitHub source.
- [ ] Install safe `.skill` archive.
- [ ] Trigger or simulate skill evolution when enabled.
- [ ] Confirm disabled PRM/RL settings do not start training.

## Matrix Mention Routing

- [ ] Send Matrix message mentioning a specific agent.
- [ ] Confirm Go extracts intended identity.
- [ ] Confirm Python bridge routes to expected agent.
- [ ] Confirm reply appears as expected agent identity.
- [ ] Confirm default-agent routing is either implemented or explicitly open.

## Control UI

- [ ] Agents tab shows configured agents.
- [ ] A2A tab shows current AgentCard/status or actionable empty state.

## Result

pending
