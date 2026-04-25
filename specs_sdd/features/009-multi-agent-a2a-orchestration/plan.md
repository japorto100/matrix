---
title: Multi-Agent and A2A Orchestration Plan
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 009
migrated_from:
  - specs/execution/exec-10-multi-agent.md
  - specs/execution/exec2-04-verify-gates.md
adrs: []
---

# Plan

## Architecture

Multi-agent orchestration owns LangGraph roles, delegation, A2A AgentCards,
Matrix mention routing and per-user/per-agent routing behavior.

## Critical Files

- `python-backend/agent/**`
- `python-backend/agent/a2a/**`
- `python-backend/bridge/nats_handler.py`
- `go-appservice/internal/**`
- `frontend_merger/src/features/control/**A2a*`

## Migration Strategy

1. Treat implemented phases as closeout input.
2. Promote A2A live test to top gate.
3. Move paper-insight ideas to research unless implemented.

## Risks

- Calling A2A implemented without live delegation evidence.
- Mixing Matrix mention routing with general agent delegation.

