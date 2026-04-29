---
title: Control UI and Runtime Surfaces
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-26
feature_id: 010
migrated_from:
  - specs/execution/exec-15-memory-control-ui.md
  - specs/execution/exec-13-ui-kg-extensions.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/VERIFY-GATES.md
adrs: []
---

# Control UI and Runtime Surfaces

## Current State / Ist

Control UI is built across many tabs and has some live verified paths,
especially memory browser data loading. But backend ownership is split across
memory, LLM, observability, sandbox, skills, MCP and A2A.

Static verification on 2026-04-25 confirms the `frontend_merger` route
`/control/[[...tab]]`, Control shell tab dispatch, the catch-all
`/api/control/[...path]` BFF proxy and React Query clients for the Control
surfaces. This does not close the feature: many components still intentionally
fall back to `mock-data.ts` when a backend route is absent or down.

## Target State / Soll

Control UI is the integrated runtime cockpit. Every tab either shows real data
from its owning backend or explicitly declares why it is empty/deferred.

Control UI is a data display, inspection and admin surface. It is not part of
the agent action space by default. Backend tools only become agent tools when a
specific owner feature intentionally exposes them through the Agent
ToolRegistry/MCP contract. Control can show tool state, traces, Memory/KG
state, runs, gates and admin affordances, but those UI affordances do not
automatically grant the agent new tools.

## Subfeatures

- Memory tab and KG graph
- Files and memory navigation
- Agents and A2A tabs
- API models, provider and billing tabs
- Audit and observability tabs
- Sandbox, permissions and security tabs
- Skills, tools and MCP tabs
- System/context/tasks tabs
- Full tab-by-tab E2E smoke

## Gap

- Full Control UI E2E walkthrough is still required.
- Empty/mock-backed tabs need owning-feature follow-up.
- Backend wiring is mixed across tabs.
- Browser/layout verification is separate from static build success.

## Static Verify

- [x] `/control/[[...tab]]` route exists.
- [x] `/api/control/[...path]` catch-all proxy exists.
- [x] Query clients cover Control, Memory and Scheduler backend surfaces.
- [x] Frontend lint/typecheck/test/build gates passed in the shared frontend
  verification.

## Live Verify

- Navigate every Control UI tab.
- Record whether each tab has real data, empty state, or broken state.
- Route broken/empty states back to owning features.

## Closeout Criteria

- Control UI is not closed by frontend tests alone; it needs a tab-by-tab
  integration evidence record.
