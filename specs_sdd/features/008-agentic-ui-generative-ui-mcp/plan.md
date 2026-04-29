---
title: Agentic UI, Generative UI and MCP Plan
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 008
migrated_from:
  - specs/execution/exec-09-protocols-generative-ui.md
  - specs/execution/exec-20-mcp-manager.md
  - docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
adrs: []
---

# Plan

## Architecture

Agentic UI uses A2UI/CopilotKit paths inside `frontend_merger`. MCP/WebMCP
surface tool connectivity and governance. Tambo is historical, not current.
See `architecture.md` for the full layer model and packet evolution.

## Critical Files

- `frontend_merger/src/features/agent/components/A2ui*`
- `frontend_merger/src/features/agent/providers/**`
- `frontend_merger/src/app/api/copilotkit/route.ts`
- `frontend_merger/src/app/api/surfaces/[id]/route.ts`
- `frontend_merger/src/features/agent/lib/a2uiTreeSchema.ts`
- `frontend_merger/src/features/agent/lib/a2ui-packets.ts`
- `frontend_merger/src/features/agent/hooks/useA2uiSseSubscriber.ts`
- `frontend_merger/src/features/agent/hooks/useA2uiWidgetData.ts`
- `frontend_merger/src/features/agent/hooks/usePersistentSurface.ts`
- `python-backend/agent/tools/a2ui_surface.py`
- `python-backend/agent/a2ui/**`
- `python-backend/agent/streaming.py`
- `go-appservice/internal/handlers/http/surfaces_handler.go`
- MCP/WebMCP hooks in `frontend_merger/src/**`

## Migration Strategy

1. Split frontend shell evidence to Feature 003.
2. Keep A2UI/CopilotKit/MCP ownership here.
3. Treat old Tambo references as superseded.
4. Preserve historical Ansatz-Y as fallback; target native `data-a2ui-*`
   packets for live rendering.
5. Track phase-2 gaps #93, #94 and #95 as explicit tasks.

## Execution Order

1. Verify provider-off and provider-on modes.
2. Verify static A2UI render via fixtures.
3. Verify native stream packet render via live agent path.
4. Verify persistence through localStorage and Postgres.
5. Decide and implement/defer #93 custom catalog.
6. Keep #94/#95 deferred unless user story/UX decision changes.
7. Verify MCP server/proxy/WebMCP separately from A2UI.

## Risks

- Unit tests passing while live LLM-to-widget path is broken.
- MCP dependencies installed but no live server verified.
- Treating UX consolidation as protocol work and creating needless route churn.
- Importing heavy SDK side effects into normal agent boot.
