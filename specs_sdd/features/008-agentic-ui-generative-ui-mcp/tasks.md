---
title: Agentic UI, Generative UI and MCP Tasks
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-29
feature_id: 008
migrated_from:
  - specs/execution/exec-09-protocols-generative-ui.md
  - specs/execution/exec-20-mcp-manager.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
---

# Tasks

## Migration

- [x] T001 Mark Tambo content superseded by A2UI.
- [x] T002 Preserve Superpowers Plan-v2 architecture in `architecture.md`.
- [x] T003 Preserve exec-09 MCP/Generative UI/Canvas scope in `subfeatures.md`.
- [x] T004 Preserve exec-20 MCP governance/App evaluation in `research.md`.
- [x] T005 Import post-session open tasks #93/#94/#95.

## Provider Runtime

- T010 Verify CopilotKit env flags in `.env.example` and local dev env.
- [x] T011 Static-test provider disabled mode has no hook registration.
- [x] T012 Static-build provider enabled mode with CopilotKit + A2UI provider
  path.
- [x] T013 Static-test `GlobalCopilotContext` registers global
  actions/readables.
- T014 Verify route-level readables/actions for Files and Control.

## A2UI Static Rendering

- [x] T020 Verify A2UI tree validation tests.
- [x] T021 Verify malformed tree rejected with safe fallback.
- T022 Live-verify valid tree renders inline in chat.
- T023 Live-verify main canvas renders a valid surface.
- [x] T024 Static-test unknown widget type is rejected and does not crash packet
  handling.
- [x] T025 Verify `render_a2ui_surface` fallback remains available or is
  explicitly retired.

## Native A2UI Stream

- [x] T030 Verify Python stream dataclasses emit `data-a2ui-*` packets.
- [x] T031 Verify TS packet adapter converts stream data to renderer messages.
- [x] T032 Verify `useChatSession` forwards `onData` packets to A2UI subscriber
  by code/test coverage of the subscriber path.
- T033 Verify `data-a2ui-update-components` updates visible UI.
- [x] T034 Static-test `data-a2ui-update-data-model` adapter and widget-data
  hook; live visible update remains pending.
- [x] T035 Static-test `data-a2ui-delete-surface` adapter; live visible delete
  remains pending.

## Surface Persistence

- T040 Verify localStorage hydration after reload.
- T041 Verify Postgres surface save/load/delete through Go API.
- T042 Verify Next.js BFF preserves auth/user scope.
- T043 Verify schema-version mismatch drops stale cache safely.
- T044 Verify failed Postgres sync does not break local UI.

## Python A2UI Emitter

- [x] T050 Verify `a2ui-agent-sdk` imports are selective and side-effect safe.
- [x] T051 Verify `A2uiEmitter` emits protocol-valid messages.
- [x] T052 Verify system prompt includes catalog guidance.
- [x] T053 Verify SDK message translation matches frontend packet adapter.

## Open Plan-v2 Gaps

- [x] T060 #93 Decide custom A2UI catalog-extension: local widgets plus
  fallback for current branch.
- [x] T061 #93 ChartWidget and PortfolioCard exist as local A2UI/custom widget
  entries; native catalog-extension decision remains open.
- [x] T062 #93 Keep tool-output fallback during migration.
- [x] T063 #94 Decide whether `/matrix` needs CopilotKit actions: deferred.
- [x] T064 #95 Keep route consolidation deferred unless UX decision changes.

## MCP / WebMCP

- T070 Verify Python FastMCP server starts and lists expected tools.
- T071 Verify Go `/mcp/` proxy initialize returns 200.
- [x] T072 Static-verify frontend `use-mcp` hook exists/builds against current
  server URL config.
- T073 Verify Browser WebMCP `navigator.modelContext.listTools()`.
- T074 Verify a safe browser tool roundtrip.
- [x] T075 Document MCP auth/tool filtering status before enabling external
  servers.
- [x] T076 Document MCP Apps adoption boundary after 2026 SOTA pass: feature-flag
  only, sandboxed iframe/AppBridge-style host, CSP/capability review and
  text/tool fallback.
- [x] T077 Static-harden Matrix widget rendering as a link-card bridge, not an
  iframe host. Full Matrix Widget API support remains a future sandboxed host
  decision.
- T078 Route external MCP discovery, descriptor risk, token passthrough and
  catalog filtering to Feature 024 instead of keeping policy inside A2UI.
- T079 Route Matrix room-state/app hosting to Feature 030; Feature 008 keeps
  local A2UI packets and safe fallbacks.
- T080 Add provider-agnostic MCP Apps compatibility adapter notes: learn from
  current app/resource patterns without tying Matrix UI to one LLM provider.
- [x] T081 [done-static] Capture ADR-0010 boundary between Matrix event
  fallbacks and Agent Chat rich surfaces.
  - 2026-04-29: ADR-0010 keeps mobile Matrix clients on event/link/code/media
    fallbacks and routes MCP Apps, code widgets, tool dashboards and approval
    forms to Agent Chat UI / A2UI surfaces.
- [x] T082 [done-static] Update frontend AI SDK packages to current stable v6
  patch line and verify Agent Chat type compatibility.
  - 2026-04-29: `ai` updated to 6.0.170, `@ai-sdk/react` to 3.0.172 and
    `@ai-sdk/devtools` to 0.0.16; unused installed assistant-ui AI SDK
    adapters were also patched to `@assistant-ui/react` 0.12.27 and
    `@assistant-ui/react-ai-sdk` 1.3.21. `tsc --noEmit` and targeted Agent
    Chat tests pass.
- [x] T083 [done-static] Render AI SDK v6 static `tool-*` parts as well as
  dynamic tool parts in Agent Chat.
  - 2026-04-29: `AgentChatMessage` now uses SDK helpers `isToolUIPart()` and
    `getToolName()`, so provider/gateway static tool streams do not disappear
    from the timeline.

## Verify Gates

- [x] Malformed A2UI tree rejected.
- [x] Agent Chat renders AI SDK v6 static and dynamic tool UI parts.
- Valid A2UI tree renders in browser.
- Live LLM path creates a UI surface via `data-a2ui-*`.
- Surface survives reload and server reconcile.
- MCP live connection tested or deferred with reason.
- Matrix widget events render safely without arbitrary iframe execution.
