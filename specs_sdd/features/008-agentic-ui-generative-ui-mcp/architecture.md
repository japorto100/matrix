---
title: Agentic UI Architecture Decisions
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 008
migrated_from:
  - docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
  - specs/execution/superpower-impl-log.md
---

# Architecture

## Layer Model

1. Python agent remains the brain: LangGraph/simple runner, LiteLLM and tools.
2. Next.js hosts browser-facing BFF routes: `/api/agent/chat`,
   `/api/copilotkit` and `/api/surfaces/[id]`.
3. CopilotKit provides frontend actions/readables and AG-UI runtime binding.
4. A2UI renders structured UI in chat-inline surfaces and the persistent main
   canvas.
5. MCP/WebMCP remains the tool/app protocol layer, not the primary A2UI data
   transport.

## Provider Hierarchy

`frontend_merger` owns the browser stack:

```tsx
<AgentProviders>
  <CopilotKit runtimeUrl="/api/copilotkit">
    <A2uiRootProvider>
      <GlobalCopilotContext>
        <GlobalTopBar />
        <main>{children}</main>
        <GlobalChatOverlay />
      </GlobalCopilotContext>
    </A2uiRootProvider>
  </CopilotKit>
</AgentProviders>
```

The provider must be env-gated so disabled CopilotKit does not create retry
loops or crash hooks mounted outside a provider.

## Route Ownership

- `/`: landing plus persistent A2UI main canvas (`surfaceId="main"`).
- `/matrix`: Matrix chat; CopilotKit integration is optional backlog #94.
- `/files`: files route, recent files readable, chat attachment save/add flows.
- `/memory`: memory/KG route, selected node/readable ownership shared with
  Feature 012.
- `/control`: admin/runtime tabs, `openControlTab` action and active tab
  readable.

Route consolidation into `/control/*` is backlog #95. It has low functional
value and should not block protocol work.

## A2UI Transport Evolution

### Historical Phase 1: Ansatz Y

The first path emitted A2UI JSON as a virtual tool result named
`render_a2ui_surface`. It reused `ToolOutputRenderer` and was acceptable for
static snapshots. It remains useful as compatibility/fallback but is not the
target for live data.

### Current Target: Ansatz X

Native A2UI packets are the target path:

- `data-a2ui-surface-start`
- `data-a2ui-update-components`
- `data-a2ui-update-data-model`
- `data-a2ui-surface-end`
- `data-a2ui-delete-surface`

Frontend packet adapters convert stream packets into renderer messages and feed
`useA2UIActions().processMessages`. This is what enables live updates without
abusing tool results.

## Persistence

Surfaces persist through a cache-first model:

- localStorage for instant hydration and reload continuity.
- Postgres-backed `agent_surfaces` via Go `/api/v1/surfaces/*` and Next.js BFF
  `/api/surfaces/[id]`.
- `schema_version` guards drift.
- user scope is enforced via `X-Actor-User-Id`/auth context, not anonymous
  global surface state.

## Frontend Actions And Readables

Global:

- `navigateTo(route)`
- `toggleAgentSidebar()`
- `currentRoute`
- `currentChatAttachments`

Files:

- `saveAttachmentToStorage(attachmentId)`
- `recentFiles`
- FileCard context menu: add file context to chat.

Control:

- `openControlTab(tab)`
- `activeControlTab`

Memory:

- `selectedMemoryNode` in phase 1; deeper memory semantics belong to Feature
  012.

## MCP Boundary

MCP is for tool discovery/calling, governance, Apps and external tool surfaces.
A2UI widget data binding uses native SSE push and TanStack/REST pull. Wrapping
A2UI live data in MCP is overhead unless a specific external MCP host requires
it.

MCP Apps are additive: sandboxed iframe UI resources may be evaluated for
dashboards/forms, but every app-capable tool must keep a text-only fallback.
