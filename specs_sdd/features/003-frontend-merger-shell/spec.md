---
title: Frontend Merger and Shell
status: implementation_done
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 003
migrated_from:
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/README.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/VERIFY-GATES.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/exec-01-frontend-merger-scaffold.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/exec-02-envfiles-devstack-compose.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/exec-03-linter-fixes.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/exec-04-playwright-verify.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/exec-05-ui-viewers-polish.md
  - specs/execution/archive/exec-merge-chat-SUPERSEDED.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
  - docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md
adrs: []
---

# Frontend Merger and Shell

## Current State / Ist

`frontend_merger/` exists as the monolith for matrix chat, agent chat, control
UI, files and memory. The branch execution has strong automated evidence:
builds, tests, linting, Playwright and route smoke largely passed. Superpowers
plan v1 is superseded by v2; v2 phase 1 and most phase 2 are complete.

The old verify-gates file is stronger than the current SDD stub: it records
which gates actually ran, which were only code/doku changes, and which require
the user's local full stack. That distinction is part of this feature.

Static frontend gates passed on 2026-04-25: lint, typecheck, Vitest and
Turbopack production build. The shell exposes page routes for `/`, `/matrix`,
`/control`, `/files` and `/memory`. Agent Chat is mounted as a global overlay
and API surface (`/api/agent/*`), with agent configuration under Control tabs;
it is not a required top-level `/agent` page.

## Target State / Soll

The frontend shell is the accepted home for all user-facing surfaces. Old
parallel frontends are historical. Remaining work is local full-stack live smoke
and a few explicitly extracted phase-2 gaps.

## Subfeatures

- Shell scaffold and route mount
- Env and compose integration
- Go/Python/frontend linter cleanup caused by merger
- Playwright smoke and production build
- Files/model viewer polish
- Global navigation
- Route consolidation decision
- Evidence ledger for branch verification
- Open full-stack local smoke

## Gap

- User-local live smoke still needs real env values and running stack.
- Open plan-v2 items remain: custom A2UI widget catalog, Matrix CopilotKit
  integration, route consolidation decision.
- Some old `nextjs-chat`/`agent-chat` references are historical; current
  canonical UI path is `frontend_merger`.
- Current accepted shell route set is `/`, `/matrix`, `/control`, `/files` and
  `/memory`; Agent Chat remains overlay/API plus Control integration.

## Verify

- [x] `frontend_merger` production build passes locally.
- Full stack live smoke covers `/matrix`, `/control`, `/files`, `/memory`
  and the Agent Chat overlay. Deferred to live verify.
- [x] Legacy `exec-merge-chat` is referenced only as historical rationale.

## Closeout Criteria

- `closeout.md` records what was merged, what was deferred, and the user-local
  live smoke result.
