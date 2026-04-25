---
title: Control UI and Runtime Surfaces Plan
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 010
migrated_from:
  - specs/execution/exec-15-memory-control-ui.md
  - specs/execution/exec-13-ui-kg-extensions.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/VERIFY-GATES.md
adrs: []
---

# Plan

## Architecture

Control UI is the integration cockpit across memory, agents, models, audit,
sandbox, skills, MCP, system and context surfaces. It owns the tab-by-tab E2E
walkthrough, while backend ownership remains with the relevant feature.

## Critical Files

- `frontend_merger/src/features/control/**`
- `frontend_merger/src/features/memory/**`
- `frontend_merger/src/features/files/**`
- `frontend_merger/src/app/api/control/**`
- `frontend_merger/src/app/api/memory/**`
- Backend endpoints used by each tab

## Migration Strategy

1. Split giant exec-15 phases into subfeature task groups.
2. Treat archived KG extension as imported into control/memory.
3. Use live-verify tab matrix to route backend gaps to owning features.

## Risks

- UI tab exists but backend data path is fake or empty.
- Control UI becomes a dumping ground for backend feature work.

