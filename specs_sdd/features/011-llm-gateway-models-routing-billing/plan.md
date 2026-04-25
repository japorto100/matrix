---
title: LLM Gateway, Models, Routing and Billing Plan
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 011
migrated_from:
  - specs/execution/exec-16-llm-provider-gateway.md
  - specs/execution/exec-a2fm-adaptive-routing.md
  - docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md
  - docs/superpowers/findings/2026-04-23-a2fm-paper-research-phase2.md
adrs:
  - 0001
---

# Plan

## Architecture

LiteLLM is the provider gateway. User credentials, model discovery, reasoning
budget, billing insights and smart routing sit behind this single call path.
Smart routing is a router-node decision before the first LLM call, not a hidden
side effect inside provider code.

## Critical Files

- `python-backend/agent/llm/**`
- `python-backend/agent/security/credentials*`
- `python-backend/agent/billing/**`
- `python-backend/agent/graph/**`
- `python-backend/agent/graph/nodes/router_node.py`
- `python-backend/alembic/versions/*smart*routing*`
- `frontend_merger/src/features/control/**Api*`
- `frontend_merger/src/features/agent/**model*`
- `frontend_merger/src/features/agent/components/AgentChatMessage.tsx`

## Migration Strategy

1. Keep gateway/model/billing pieces separate from routing policy.
2. Preserve ADR-001 gate history in `routing-gates.md`.
3. Treat G1-G6/P1 as built but live-verify them before broad enablement.
4. Keep A2FM ML-router as research until L1/L2 data supports it.
5. Track verify follow-ups separately from feature rollout.

## Execution Order

1. Verify LiteLLM request, streaming and tool-call shape.
2. Verify model explorer and model picker drive one live Agent Chat request.
3. Verify credential storage/masked retrieval and validation.
4. Verify billing ledger and spend dashboard with live DB.
5. Verify smart routing G1-G6/P1 behavior.
6. Address F-G4/F-G1/F-4g4 or document acceptance.
7. Run A2FM L1 audit labeling before any classifier work.

## Risks

- Heuristic smart routing being mistaken for A2FM ML router.
- Spend dashboard appearing broken when LiteLLM DB is simply not configured.
- Silent vendor substitution without user-visible disclosure.
- Routing data corrupting A/B decisions if routing dimensions are lost.
