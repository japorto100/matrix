---
title: Agentic UI Research And Adoption Notes
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 008
migrated_from:
  - specs/execution/exec-09-protocols-generative-ui.md
  - specs/execution/exec-20-mcp-manager.md
  - docs/superpowers/findings/2026-04-22-open-tasks.md
  - specs/execution/superpower-impl-log.md
---

# Research And Adoption Notes

## Adopted

- CopilotKit hooks for frontend action/readable registration.
- A2UI v0.9 as current generative UI protocol.
- Native A2UI stream packets for live rendering.
- Local plus Postgres surface persistence.
- Python SDK wrapper around `a2ui-agent-sdk`, with selective imports.
- FastMCP server plus Go reverse proxy for MCP tool exposure.
- WebMCP bridge pattern for browser-native tools.

## Superseded

- Tambo as primary generative UI stack.
- Custom `frontend-tools.ts` protocol as primary frontend action mechanism.
- A2UI as only a tool-result envelope for live data. It remains an incremental
  fallback but is not the target architecture.

## Explicit Non-Adoptions

- Replacing the existing `AgentChatPanel` with CopilotKit UI components.
- Using MCP as the normal A2UI live-data transport.
- Brightwing MCP Manager as a desktop app. Only its security/governance patterns
  are relevant.
- Global route consolidation as a prerequisite for agentic UI.

## Open Research

### Custom A2UI Catalog

Question: How should ChartWidget and PortfolioCard be wrapped as first-class
A2UI catalog entries without losing the current rich tool-output fallback?

SDD default:

- Add an extended catalog module.
- Register custom components through the renderer-supported API.
- Keep old tool names in `ToolOutputRenderer` until live traffic proves native
  catalog rendering works.

### MCP Auth And Governance

Question: Which MCP security layer fits this stack?

Current adoption stance:

- FastAPI/FastMCP auth is the likely fit for the Python agent side.
- Tool filtering should integrate with the existing token budget logic.
- External MCP servers should pass through policy/gateway evaluation before
  becoming generally available.

### MCP Apps

Question: When should UI-returning MCP Apps be used?

Default:

- Evaluate behind feature flag.
- Use for interactive dashboards/forms only when a text/tool fallback exists.
- Keep sandboxed iframe boundary explicit in UI and security review.

## Verification Risk

The main false-positive risk is unit tests passing while the live LLM path never
emits valid A2UI packets. Live verify must include one real stream that reaches
the browser renderer and one malformed stream that is rejected safely.
