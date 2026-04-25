---
title: Agentic UI, Generative UI and MCP Tasks
status: mostly_built
owner: filip
created: 2026-04-25
updated: 2026-04-25
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

- [ ] T010 Verify CopilotKit env flags in `.env.example` and local dev env.
- [ ] T011 Verify provider disabled mode has no hook crash and no retry spam.
- [ ] T012 Verify provider enabled mode mounts CopilotKit + A2UI root provider.
- [ ] T013 Verify `GlobalCopilotContext` registers global actions/readables.
- [ ] T014 Verify route-level readables/actions for Files and Control.

## A2UI Static Rendering

- [ ] T020 Verify A2UI tree validation tests.
- [ ] T021 Verify malformed tree rejected with safe fallback.
- [ ] T022 Verify valid tree renders inline in chat.
- [ ] T023 Verify main canvas renders a valid surface.
- [ ] T024 Verify unknown widget type does not crash the app.
- [ ] T025 Verify `render_a2ui_surface` fallback remains available or is
  explicitly retired.

## Native A2UI Stream

- [ ] T030 Verify Python stream dataclasses emit `data-a2ui-*` packets.
- [ ] T031 Verify TS packet adapter converts stream data to renderer messages.
- [ ] T032 Verify `useChatSession` forwards `onData` packets to A2UI subscriber.
- [ ] T033 Verify `data-a2ui-update-components` updates visible UI.
- [ ] T034 Verify `data-a2ui-update-data-model` updates bound live data.
- [ ] T035 Verify `data-a2ui-delete-surface` clears surface state.

## Surface Persistence

- [ ] T040 Verify localStorage hydration after reload.
- [ ] T041 Verify Postgres surface save/load/delete through Go API.
- [ ] T042 Verify Next.js BFF preserves auth/user scope.
- [ ] T043 Verify schema-version mismatch drops stale cache safely.
- [ ] T044 Verify failed Postgres sync does not break local UI.

## Python A2UI Emitter

- [ ] T050 Verify `a2ui-agent-sdk` imports are selective and side-effect safe.
- [ ] T051 Verify `A2uiEmitter` emits protocol-valid messages.
- [ ] T052 Verify system prompt includes catalog guidance only when needed.
- [ ] T053 Verify SDK message translation matches frontend packet adapter.

## Open Plan-v2 Gaps

- [ ] T060 #93 Decide/implement custom A2UI catalog-extension.
- [ ] T061 #93 Wrap ChartWidget and PortfolioCard as native A2UI entries if
  adopted.
- [ ] T062 #93 Keep tool-output fallback during migration.
- [ ] T063 #94 Decide whether `/matrix` needs CopilotKit actions.
- [ ] T064 #95 Keep route consolidation deferred unless UX decision changes.

## MCP / WebMCP

- [ ] T070 Verify Python FastMCP server starts and lists expected tools.
- [ ] T071 Verify Go `/mcp/` proxy initialize returns 200.
- [ ] T072 Verify frontend `use-mcp` hook reaches the current server URL.
- [ ] T073 Verify Browser WebMCP `navigator.modelContext.listTools()`.
- [ ] T074 Verify a safe browser tool roundtrip.
- [ ] T075 Document MCP auth/tool filtering status before enabling external
  servers.

## Verify Gates

- [ ] Malformed A2UI tree rejected.
- [ ] Valid A2UI tree renders.
- [ ] Live LLM path creates a UI surface via `data-a2ui-*`.
- [ ] Surface survives reload and server reconcile.
- [ ] MCP live connection tested or deferred with reason.
