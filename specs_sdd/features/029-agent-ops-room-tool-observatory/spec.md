---
title: Agent Ops Room Tool Observatory
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 029
---

# Agent Ops Room Tool Observatory

## Current State / Ist

Control UI and observability exist, but multi-agent/tool activity is still
mostly tables, traces and logs. The Z_ Hermes/Claw3D note points at a useful
pattern: a spatial or operational room can compress agent status, blockers,
tool activity and approvals into a human-readable control surface.

## Target State / Soll

Feature 029 creates an ops-room/observatory surface for agent work:

- live sessions, agents, tools, approvals, memory and retrieval events;
- status lanes such as active, waiting, blocked, failed, needs approval;
- optional spatial/3D visualization only after a dense 2D surface works;
- replay from Feature 014 traces and Feature 016 Meta-Harness artifacts;
- Matrix room integration for human handoff and approval events.

## Boundaries

- Feature 010 owns general Control UI shell.
- Feature 014 owns tracing/eval data.
- Feature 016 owns Meta-Harness optimization evidence.
- Feature 020 owns harness/subagent routing.
- Feature 024 owns MCP catalog policy.

Feature 029 owns operational visualization and live agent-room workflows.

## Closeout Criteria

- Ops room shows live and replayed agent/tool state.
- Approval/blocker state is visible without reading raw logs.
- Tool catalog risk from Feature 024 is visible in context.
- Meta-Harness runs can be replayed as operational timelines.
- 3D/spatial UI remains optional and gated by usability/performance.
