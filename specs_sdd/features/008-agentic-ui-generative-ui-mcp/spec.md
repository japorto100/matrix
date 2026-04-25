---
title: Agentic UI, Generative UI and MCP
status: mostly_built
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 008
migrated_from:
  - specs/execution/exec-09-protocols-generative-ui.md
  - specs/execution/exec-20-mcp-manager.md
  - docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
  - Copilotkit_additional.md
adrs: []
---

# Agentic UI, Generative UI and MCP

## Current State / Ist

Tambo is historical. Google A2UI v0.9 plus CopilotKit is the current agentic
frontend stack. The initial static-widget path used `render_a2ui_surface` as a
virtual tool result. The later Plan-v2 Phase-2 work landed the stronger path:
native `data-a2ui-*` SSE packets, `a2ui-agent-sdk`, server-backed surface
persistence and live-data bindings. MCP is not the transport for A2UI live data;
it remains the tool/app/governance layer.

## Target State / Soll

The agent can emit safe structured UI surfaces into chat and canvas, while MCP
and WebMCP tools are governed through explicit runtime surfaces. A reader of
this feature should be able to reconstruct the full UI protocol story without
opening `exec-09`, `exec-20` or Superpowers Plan v2.

## Subfeatures

- A2UI tree schema and renderer
- CopilotKit runtime endpoint
- Global actions and readables
- Chat-inline and main-canvas rendering
- Surface persistence
- Native A2UI SSE packet stream and live data binding
- Python `a2ui-agent-sdk` emitter wrapper
- MCP manager and WebMCP hooks
- MCP Apps evaluation path
- Custom widget catalog
- Matrix CopilotKit integration

## Gap

- Custom A2UI widget catalog remains open.
- Matrix-chat CopilotKit integration remains open.
- Route consolidation into `/control/*` is a UX-only decision and not a
  functional blocker.
- Browser/WebMCP roundtrip still needs live verification where it is meant to be
  active.
- MCP Apps are evaluation-only and must not replace text/tool fallbacks.

## Verify

- [ ] A2UI validation tests pass.
- [ ] Agent can emit a widget through the live LLM/A2UI packet path.
- [ ] MCP server connection works with current config.
- [ ] Unsafe widget/tree output is rejected.

## Closeout Criteria

- Plan-v2 gaps #93, #94 and #95 are either closed or explicitly transferred to
  backlog.
- `data-a2ui-*` packet path is live-verified, not only unit-tested.
- `exec-09` no longer references Tambo as current target.
