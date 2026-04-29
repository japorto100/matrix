---
title: Agentic UI MCP Decisions
status: accepted
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 008
---

# Decisions

## D008-001: Custom A2UI Catalog

Accepted for current branch: keep local custom widgets plus
`render_a2ui_surface` fallback. Do not add a native A2UI catalog extension until
one of the local widgets needs cross-runtime reuse outside `frontend_merger`.

Rationale: Chart and portfolio widgets already exist locally, the native
`data-a2ui-*` packet path is the current target, and the migration safety
requirement is better served by keeping the tool-output fallback while live
browser verification is still pending.

## D008-002: Matrix CopilotKit Integration

Accepted for current branch: do not add `/matrix` CopilotKit actions yet.
Matrix Chat owns protocol actions directly; CopilotKit route-level actions are
kept for Agent/Control/Files style surfaces until a concrete Matrix workflow
requires them.

## D008-003: Route Consolidation

Accepted for current branch: keep `/control/*` consolidation as a UX/backlog
decision, not a Feature 008 blocker.

## D008-004: MCP External Enablement

Accepted for current branch: external MCP servers stay disabled/not promoted
until auth and tool filtering are explicit.

Minimum policy before external enablement:

- only configured internal MCP endpoints by default;
- user/session identity forwarded through the Go proxy where supported;
- per-server allowlist of tool names;
- no browser WebMCP exposure unless the browser/runtime supports
  `navigator.modelContext` and the user can see/disable the connection.
