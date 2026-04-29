---
title: Agentic UI Research And Adoption Notes
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-29
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

### 2026-04-29 Z-MD / Web SOTA Pass

Sources checked from the fresh `Z_*.md` queue and current web search:

- [MCP 2025-11-25 core spec](https://modelcontextprotocol.io/specification/2025-11-25/basic)
  and
  [security best practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices):
  HTTP auth and external servers require explicit authorization, HTTPS except
  loopback dev, private-IP blocking and no-credential resource/icon fetches.
- [MCP Apps / SEP-1865](https://modelcontextprotocol.io/extensions/apps/overview):
  UI-returning tools are now a real extension, but the secure pattern is
  sandboxed iframe plus CSP plus postMessage/AppBridge. Matrix should not invent
  a parallel unsandboxed host.
- [Matrix Widget API package](https://www.npmjs.com/package/matrix-widget-api)
  and
  [Matrix Rust SDK widget driver](https://matrix-org.github.io/matrix-rust-sdk/matrix_sdk/widget/index.html):
  the active ecosystem is still Element/Web-centered and widget support depends
  on postMessage/capability mediation.
- [OpenAI GPT-5.3-Codex model docs](https://developers.openai.com/api/docs/models/gpt-5.3-codex):
  current Codex-class agents favor long-horizon task loops with explicit skills,
  live browser verification and controlled memory. Chronicle-style visual memory
  remains research/input inspiration, not an adoption target without privacy
  controls and opt-in storage policy.

Matrix decision:

- Keep A2UI as the first-party in-agent UI stream.
- Treat MCP Apps as feature-flag research for dashboards/forms only, with a text
  or tool-output fallback and a hardened sandbox host.
- Treat Matrix widgets as room-state artifacts. In the chat timeline, render a
  safe link card first; do not inline arbitrary widget iframes until a dedicated
  Widget API/AppBridge-style host exists.

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

### Matrix Widgets

Question: Should Matrix room widgets become first-class agent UI surfaces?

Default:

- Render `m.widget` / `im.vector.modular.widgets` as safe link cards in Matrix
  chat.
- Only preserve `http/https` widget URLs; block active script/data URLs.
- Do not map Matrix widget state to A2UI automatically. If an agent creates an
  interactive dashboard, A2UI or MCP Apps must own the host/sandbox contract.
- Future adoption requires a Widget API v2-compatible host with CSP, postMessage
  mediation, capability negotiation and Matrix room permission checks.

## Verification Risk

The main false-positive risk is unit tests passing while the live LLM path never
emits valid A2UI packets. Live verify must include one real stream that reaches
the browser renderer and one malformed stream that is rejected safely.

## 2026-04-29 Z_ Follow-Up

`Z_Additional_For_Tool_Stuff.md` and `Z_matrix_widgets_formulars_and so on.md`
confirm the split:

- MCP gateway/catalog/policy moves to Feature 024.
- Matrix room-state widget/app hosting moves to Feature 030.
- Feature 008 remains provider-agnostic local A2UI/generative UI with safe
  fallback rendering.

Provider-specific app-resource examples are useful as protocol pressure, but
they are not Matrix's runtime contract.
