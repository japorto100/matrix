---
title: Agentic UI, Generative UI and MCP Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-29
feature_id: 008
---

# Live Verify

## 2026-04-29 Feature 024/030 Follow-Up

- Verify A2UI can render a fallback when an MCP resource is blocked by Feature
  024 policy.
- Verify Matrix widget/app payloads are handed to Feature 030 proposal flow
  instead of being executed inline.

## A2UI / CopilotKit

- Enable required env flags.
- Confirm `/api/copilotkit` responds.
- Confirm provider-off mode has no CopilotKit hook crash.
- Ask agent for visual output that should emit A2UI.
- Confirm backend emits `data-a2ui-surface-start`.
- Confirm backend emits `data-a2ui-update-components`.
- Confirm backend emits `data-a2ui-update-data-model` for live data when
  requested.
- Confirm widget renders inline in chat.
- Confirm widget renders on main canvas if targeted.
- Confirm invalid widget/tree is rejected safely.
- Confirm legacy `render_a2ui_surface` fallback is either still rendered or
  explicitly unavailable by design.

## Persistence

- Local surface persistence works.
- Reload restores surface from local cache before server response.
- Postgres sync works through `/api/surfaces/[id]`.
- Delete clears local and server surface.
- Schema-version mismatch drops stale local state safely.

## Open Plan-v2 Gaps

- #93 custom catalog decision is recorded.
- If #93 adopted: ChartWidget and PortfolioCard render as native A2UI
  catalog entries.
- #94 Matrix CopilotKit decision is recorded.
- #95 route consolidation decision is recorded.

## MCP

- Connect to configured MCP server.
- List tools.
- Invoke safe tool.
- Confirm tool filtering/governance state in UI.
- Confirm MCP Apps remain feature-flag/evaluation-only unless explicitly
  adopted.

## Matrix Widgets

- Send or inject `m.widget` and `im.vector.modular.widgets` room-state events.
- Confirm `https://` widget URL renders as an external link card.
- Confirm `javascript:`, `data:` or malformed URL renders as passive blocked
  text.
- Confirm no `<iframe>` is created by the Matrix chat timeline.

Static evidence 2026-04-29:

- `bunx vitest run src/features/matrix/lib/resolvers.test.ts src/features/matrix/components/message/MessageContent.test.tsx`
  => `2 passed`, `4 passed`.
- `bun run typecheck` => pass.

## Result

pending

## 2026-04-30 Added Live Gates

- LV030 Send an Agent Chat turn that emits tool/runtime events and verify cards
  render for start/result/error without layout overflow.
- LV031 Verify developer-mode request/cache telemetry card appears only for
  allowed operators and contains no raw prompt text.
- LV032 Trigger a report/PDF/data artifact and verify typed attachment rows use
  manifest/runtime-event refs.
- LV033 Verify unknown runtime event kinds render as safe fallback rows.
