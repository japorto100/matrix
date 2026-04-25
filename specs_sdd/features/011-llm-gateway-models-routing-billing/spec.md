---
title: LLM Gateway, Models, Routing and Billing
status: in_progress
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 011
migrated_from:
  - specs/execution/exec-16-llm-provider-gateway.md
  - specs/execution/exec-a2fm-adaptive-routing.md
  - docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md
  - docs/superpowers/findings/2026-04-23-a2fm-paper-research-phase2.md
  - specs/execution/archive/exec-19-devstack-consolidation.md
adrs:
  - 0001
---

# LLM Gateway, Models, Routing and Billing

## Current State / Ist

LiteLLM/OpenRouter path, model explorer, usage pricing, insights, metadata and
smart routing work are implemented. ADR-001 originally blocked rollout behind
six gates; later superpower implementation log records G1-G6 plus the Phase-1
`router_node` refactor as landed. Remaining risk is no longer "gate not built",
but live verification and follow-up fixes from adversarial verify.

## Target State / Soll

All LLM calls go through one provider gateway with secure credentials, model
metadata, reasoning controls, usage/billing visibility and gated routing.

## Subfeatures

- LiteLLM proxy and OpenRouter path
- BYO credentials and key security
- Model discovery and metadata cache
- Utility models and reasoning budgets
- Usage ledger and spend dashboard
- Smart cheap-vs-strong routing
- A2FM research-to-router path
- User-visible routing indicators
- Reasoning/thinking budget pass-through
- Canonical usage ledger and insights rollup

## Gap

- Spend tracking needs live DB-backed verification.
- User-model-picker wiring needs live Agent Chat verification.
- Reasoning-token live verify is provider-access gated.
- A2FM ML router remains research/phase 2+; Phase 2 is now L1/L2 feedback
  before any classifier.
- Verify follow-ups remain: A/B insert/update race, smart-routing keyword
  quality review, scorer eval-id overwrite semantics.

## Verify

- [ ] LiteLLM tool-call smoke passes.
- [ ] Model explorer loads live models.
- [ ] Spend dashboard shows data with configured DB.
- [ ] Smart routing shows user-visible routing metadata and Control-UI disable
  path.
- [ ] Follow-up findings F-G4/F-G1/F-4g4 are closed or explicitly accepted.

## Closeout Criteria

- Routing is either off-by-default with documented gates or live-verified after
  G1-G6.
- A2FM research is not confused with shipped smart-routing heuristic.
