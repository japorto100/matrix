---
title: Agentic UI, Generative UI and MCP Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 008
---

# Gates

## G1 Provider Runtime

- [x] CopilotKit disabled mode does not register hooks.
- [x] CopilotKit enabled mode registers global actions/readables.
- [x] A2UI provider and subscriber code builds in `frontend_merger`.
- [ ] Route-level Files and Control Copilot actions are live-verified.

## G2 A2UI Static Rendering

- [x] A2UI tree validation accepts whitelisted component trees.
- [x] Malformed/unknown tree output is rejected.
- [x] Valid A2UI packet adapter maps to renderer messages.
- [x] Renderer subscriber catches renderer errors without breaking chat.
- [ ] Browser render of inline chat surface is live-verified.
- [ ] Browser render of main-canvas surface is live-verified.

## G3 Native A2UI Stream

- [x] Python `A2uiEmitter` emits start/update/end/delete packet dataclasses.
- [x] SSE serialization preserves camelCase wire fields.
- [x] TypeScript packet adapter covers `data-a2ui-*` message shapes.
- [x] `useA2uiSseSubscriber` forwards A2UI packets to the renderer.
- [ ] Live LLM path creates a visible UI surface via `data-a2ui-*`.

## G4 Surface Persistence / Live Data

- [x] Widget data hook fetches `/api/a2ui/<dataRef>` and handles params/errors.
- [ ] Surface localStorage hydration survives browser reload.
- [ ] Server-backed surface save/load/delete through Go/Postgres is verified.
- [ ] Schema-version mismatch drops stale cache safely.

## G5 MCP / WebMCP

- [x] Python FastMCP server is mounted under `/mcp`.
- [x] Go MCP proxy handler exists under `/api/v1/mcp/`.
- [x] Frontend `use-mcp` and WebMCP hooks exist and build.
- [ ] MCP initialize/list-tools roundtrip is live-verified.
- [ ] Browser `navigator.modelContext` tool roundtrip is live-verified.
- [x] External MCP auth/tool filtering is documented before enabling.

## G6 Catalog / Scope

- [x] Tambo is historical/superseded by A2UI.
- [x] `render_a2ui_surface` fallback remains available.
- [x] Chart and portfolio widgets exist as local custom widgets.
- [x] #93 custom catalog-extension decision is closed.
- [x] Matrix-chat CopilotKit integration decision is closed.
