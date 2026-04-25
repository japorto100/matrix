---
title: Agentic UI Subfeatures
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 008
---

# Subfeatures

## 008.1 Provider Runtime

Status: mostly built.

Scope:

- CopilotKit provider and runtime URL flags.
- A2UI root provider and shared surface store.
- Global actions/readables registered only when provider is active.

Open:

- Live verify provider-off mode: no hook crash, no endless `/api/copilotkit`
  retries.

## 008.2 A2UI Rendering

Status: built, verify required.

Scope:

- A2UI tree validation.
- Chat-inline renderer.
- Main canvas renderer.
- Unknown/malformed widgets fallback safely.

Open:

- Verify real LLM output, not only fixtures.
- Keep `render_a2ui_surface` as fallback/historical path.

## 008.3 Native A2UI Stream

Status: landed in Plan-v2 Phase-2, live verify required.

Scope:

- Python stream packet dataclasses.
- TypeScript packet types and renderer-message adapter.
- `useChatSession` `onData` wiring.
- `useA2uiSseSubscriber`.

Open:

- Confirm `data-a2ui-update-data-model` updates an existing surface without
  rebuilding the whole widget tree.

## 008.4 Surface Persistence

Status: landed in Plan-v2 Phase-2.

Scope:

- localStorage hydration.
- Postgres `agent_surfaces` table.
- Go surface load/save/delete.
- Next.js BFF proxy.
- cache-first reconcile and `schema_version`.

Open:

- Verify cross-reload and cross-device behavior against live DB.

## 008.5 Python A2UI Emitter

Status: built, verify required.

Scope:

- `a2ui-agent-sdk` selective imports.
- `A2uiEmitter`.
- system prompt/catalog helper.
- SDK message translation/validation.

Open:

- Confirm no unwanted Google ADK/genai/a2a runtime imports in normal agent boot.
- Confirm emitted protocol messages pass frontend validator.

## 008.6 Custom Widget Catalog (#93)

Status: open.

Scope:

- Convert ChartWidget and PortfolioCard from tool-output workaround to native
  A2UI catalog entries.
- Wire extended catalog in provider.
- Preserve old `ToolOutputRenderer` fallback during migration.

First step:

- Check whether `@a2ui/catalog-builder` is needed and read
  `createReactComponent` examples for the installed renderer version.

## 008.7 Matrix CopilotKit Integration (#94)

Status: decision backlog.

Scope:

- Mount provider/runtime in `/matrix` only if matrix users need AG-UI actions
  directly from Matrix chat.
- Possible actions: open file, navigate control tab, spawn agent chat context.

Decision:

- Low priority until a concrete user story exists. Matrix protocol/chat gates
  remain Feature 005; multi-agent Matrix bridge remains Feature 009.

## 008.8 Route Consolidation (#95)

Status: UX backlog.

Scope:

- Optional migration from `/matrix`, `/files`, `/memory` roots to
  `/control/matrix`, `/control/files`, `/control/memory`.

Decision:

- No functional value for protocol maturity. Requires explicit UX choice before
  implementation.

## 008.9 MCP Server And WebMCP

Status: partial/built, live verify required.

Scope:

- Python FastMCP server.
- Go MCP reverse proxy.
- frontend `use-mcp` hook.
- Browser `navigator.modelContext` polyfill and WebMCP bridge.

Open:

- Confirm live `POST /mcp/ initialize` response and tool count.
- Confirm browser tool registration and roundtrip.

## 008.10 MCP Governance And Apps

Status: evaluation.

Scope:

- MCP auth/OAuth 2.1 evaluation.
- Tool filtering and token-budget integration.
- MCP Apps as sandboxed iframe UI resources.
- Governance/proxy references for external MCP servers.

Decision:

- Do not adopt Brightwing desktop architecture. Reuse its patterns: credential
  injection, tool filtering, registry governance.
