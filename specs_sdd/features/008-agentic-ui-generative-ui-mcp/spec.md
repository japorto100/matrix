---
title: Agentic UI, Generative UI and MCP
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-29
feature_id: 008
migrated_from:
  - specs/execution/exec-09-protocols-generative-ui.md
  - specs/execution/exec-20-mcp-manager.md
  - docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
  - Copilotkit_additional.md
adrs:
  - specs_sdd/adr/0010-matrix-events-as-mobile-widget-primitive.md
---

# Agentic UI, Generative UI and MCP

## Current State / Ist

Tambo is historical. Google A2UI v0.9 plus CopilotKit is the current agentic
frontend stack. The initial static-widget path used `render_a2ui_surface` as a
virtual tool result. The later Plan-v2 Phase-2 work landed the stronger path:
native `data-a2ui-*` SSE packets, `a2ui-agent-sdk`, server-backed surface
persistence and live-data bindings. MCP is not the transport for A2UI live data;
it remains the tool/app/governance layer.

Static verification on 2026-04-25 confirms the current implementation has A2UI
schema validation, TypeScript packet translation, renderer subscription,
frontend widget-data tests, CopilotKit env-gated global actions/readables and
Python `A2uiEmitter` tests. `render_a2ui_surface` remains available as a
fallback while native `data-a2ui-*` packets are the target path.

AI SDK package verification on 2026-04-29 updates Agent Chat to the current
stable SDK-6 patch line (`ai` 6.0.170, `@ai-sdk/react` 3.0.172,
`@ai-sdk/devtools` 0.0.16). The frontend now uses SDK tool-part helpers so both
static `tool-*` and `dynamic-tool` stream parts render in the timeline.

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
- Route consolidation into `/control/*` is a UX-only decision and is not a
  functional blocker.
- Browser/WebMCP roundtrip still needs live verification where it is meant to be
  active.
- MCP Apps are evaluation-only and must not replace text/tool fallbacks.
- SDK server-side validation helpers such as `safeValidateUIMessages()` and
  browser history helpers such as `pruneMessages()` are not yet wired into our
  BFF/harness path.
- Server-backed surface persistence still needs live verification; static tests
  cover packet/widget-data behavior, not Postgres reconciliation.
- ADR-0010 assigns rich MCP Apps, code widgets, tool dashboards and approval
  forms to Agent Chat UI / generative UI surfaces. Matrix rooms receive
  mobile-compatible event fallbacks and optional widget metadata, not required
  iframe apps.

Decision cleanup on 2026-04-25 closes the local architecture questions in
`decisions.md`: local custom widgets plus fallback are accepted for now, Matrix
CopilotKit actions stay deferred, route consolidation is UX/backlog only, and
external MCP enablement requires auth/tool filtering first.

## Static Verify

- [x] `bun run test` covers A2UI tree validation, packet adapter, renderer
  subscriber, widget-data hook and Copilot global context.
- [x] `uv run pytest tests/agent/test_a2ui_emitter.py -q` passes.
- [x] Unsafe widget/tree output is rejected by validation tests.
- [x] Python emitter can serialize protocol packets to SSE frames.
- [x] #93/#94/#95 and MCP external-enablement decisions are documented in
  `decisions.md`.
- [x] Agent Chat renders AI SDK v6 static and dynamic tool parts after the
  package update.

## Live Verify

- Agent can emit a widget through the live LLM/A2UI packet path.
- MCP server connection works with current config.
- WebMCP browser tool roundtrip works where enabled.
- Surface persistence survives reload and server reconcile.

## Closeout Criteria

- Plan-v2 gaps #93, #94 and #95 are either closed or explicitly transferred to
  backlog.
- `data-a2ui-*` packet path is live-verified, not only unit-tested.
- `exec-09` no longer references Tambo as current target.
