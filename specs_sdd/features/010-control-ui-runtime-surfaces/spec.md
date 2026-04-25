---
title: Control UI and Runtime Surfaces
status: frontend_built
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

# Control UI and Runtime Surfaces

## Current State / Ist

Control UI is built across many tabs and has some live verified paths,
especially memory browser data loading. But backend ownership is split across
memory, LLM, observability, sandbox, skills, MCP and A2A.

## Target State / Soll

Control UI is the integrated runtime cockpit. Every tab either shows real data
from its owning backend or explicitly declares why it is empty/deferred.

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
- Empty tabs need owning-feature follow-up.
- Backend wiring is mixed across tabs.

## Verify

- [ ] Navigate every Control UI tab.
- [ ] Record whether each tab has real data, empty state, or broken state.
- [ ] Route broken/empty states back to owning features.

## Closeout Criteria

- Control UI is not closed by frontend tests alone; it needs a tab-by-tab
  integration evidence record.

