---
title: Agentic UI, Generative UI and MCP Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 008
---

# Live Verify

## A2UI / CopilotKit

- [ ] Enable required env flags.
- [ ] Confirm `/api/copilotkit` responds.
- [ ] Confirm provider-off mode has no CopilotKit hook crash.
- [ ] Ask agent for visual output that should emit A2UI.
- [ ] Confirm backend emits `data-a2ui-surface-start`.
- [ ] Confirm backend emits `data-a2ui-update-components`.
- [ ] Confirm backend emits `data-a2ui-update-data-model` for live data when
  requested.
- [ ] Confirm widget renders inline in chat.
- [ ] Confirm widget renders on main canvas if targeted.
- [ ] Confirm invalid widget/tree is rejected safely.
- [ ] Confirm legacy `render_a2ui_surface` fallback is either still rendered or
  explicitly unavailable by design.

## Persistence

- [ ] Local surface persistence works.
- [ ] Reload restores surface from local cache before server response.
- [ ] Postgres sync works through `/api/surfaces/[id]`.
- [ ] Delete clears local and server surface.
- [ ] Schema-version mismatch drops stale local state safely.

## Open Plan-v2 Gaps

- [ ] #93 custom catalog decision is recorded.
- [ ] If #93 adopted: ChartWidget and PortfolioCard render as native A2UI
  catalog entries.
- [ ] #94 Matrix CopilotKit decision is recorded.
- [ ] #95 route consolidation decision is recorded.

## MCP

- [ ] Connect to configured MCP server.
- [ ] List tools.
- [ ] Invoke safe tool.
- [ ] Confirm tool filtering/governance state in UI.
- [ ] Confirm MCP Apps remain feature-flag/evaluation-only unless explicitly
  adopted.

## Result

pending
