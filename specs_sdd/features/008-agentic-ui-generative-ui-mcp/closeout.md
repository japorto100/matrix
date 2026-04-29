---
title: Agentic UI, Generative UI and MCP Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 008
---

# Closeout

## Built

- A2UI v0.9 schema validation and safe rejection path.
- TypeScript `data-a2ui-*` packet adapter and renderer subscriber.
- Python `A2uiEmitter` wrapper around `a2ui-agent-sdk` with SSE packet
  serialization.
- CopilotKit env-gated global context actions/readables.
- Local Chart and Portfolio custom widgets.
- Python FastMCP app mount, Go MCP proxy handler and frontend MCP/WebMCP hooks.
- `render_a2ui_surface` fallback tool.
- Local decision ledger for #93/#94/#95 and external MCP auth/tool-filtering
  prerequisites.

## Not Built

- Proven live LLM -> `data-a2ui-*` -> visible browser surface roundtrip.
- Proven Postgres/server-backed surface persistence reconcile.
- Native A2UI catalog extension beyond local widgets.
- Matrix Chat CopilotKit action/readable implementation.
- External MCP auth/tool-filtering implementation for real external server
  enablement.

## Deviations From Plan

- Tambo is no longer a target. A2UI v0.9 plus CopilotKit is the current stack.
- MCP remains the tool/app/governance layer; it is not the A2UI live-data
  transport.
- Route consolidation into `/control/*` is a UX decision, not a functional
  blocker for Feature 008.

## Verify Result

- PASS static: frontend test suite includes A2UI tree validation, packet
  adapter, renderer subscriber, widget-data hook and Copilot context tests.
- PASS static: `uv run pytest tests/agent/test_a2ui_emitter.py -q`.
- PASS static: frontend lint/typecheck/build already passed under Feature 007
  verification.

## Live Verify Result

Pending: live LLM A2UI surface, browser render, surface persistence reconcile
and MCP/WebMCP roundtrip.

## Follow-Ups

- Implement native catalog extension only if local widgets need cross-runtime
  reuse.
- Live-test Browser WebMCP only if the target browser/runtime supports
  `navigator.modelContext`.
- Keep MCP Apps as evaluation-only until text/tool fallbacks and auth filtering
  are documented.
