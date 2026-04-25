---
title: Multi-Agent and A2A Orchestration
status: implementation_done_live_verify_open
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 009
migrated_from:
  - specs/execution/exec-10-multi-agent.md
  - specs/execution/exec2-04-verify-gates.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
adrs: []
---

# Multi-Agent and A2A Orchestration

## Current State / Ist

LangGraph agent graph, trading roles, orchestrator, skills, middleware and A2A
foundations are implemented according to `exec-10`. The same file also records
that many verify gates remain open: LangGraph graph behavior, trading role
contracts, skills, A2A delegation, middleware, skill-management API, disabled RL
infrastructure and paper-insight features.

A2A specifically is still the hot unverified path. Later notes added
per-user/per-agent routing, dynamic reply identity and default-orchestrator
questions, but those are not yet a closed architecture.

## Target State / Soll

Agents can delegate through explicit A2A contracts, Matrix mentions route to
the right agent identity, per-user/per-role routing is observable, and
paper-derived learning/planning patterns are separated into implemented,
disabled infrastructure and research-only states.

## Subfeatures

- 009.1 LangGraph base agent loop
- 009.2 Trading-role orchestrator
- 009.3 Skills loading, import and evolution
- 009.4 A2A AgentCard, client and delegation node
- 009.5 Middleware and guardrails
- 009.6 Paper-derived skill learning and NLAH patterns
- 009.7 Per-user orchestrator and Matrix mention routing
- 009.8 Control UI Agents/A2A observability

## Gap

- A2A live smoke is the hot closure blocker.
- Matrix mention/default-agent routing needs a concrete end-state: body regex,
  DM-member resolution or orchestrator default.
- Per-user agent settings, system prompts, memory scopes, skill sets and
  tool-allowlists are still design/open implementation.
- NATS authorization from Feature 006 is required before strong agent isolation.
- MetaClaw-derived SkillEvolver is built, PRM/LoRA/OMLS are disabled
  infrastructure, Trace2Skill/NLAH additions need verify gates and research
  separation.
- Control UI A2A/Agents tabs need live backend state or explicit empty states.

## Verify

- [ ] Agent A delegates to Agent B via A2A/AgentCard path.
- [ ] Matrix mention reaches expected agent.
- [ ] Per-user routing is visible in logs/UI.
- [ ] Paper-derived features are verified, disabled or moved to research.

## Closeout Criteria

- A2A live test evidence exists.
- Paper/research ideas are moved to research if not implemented.
