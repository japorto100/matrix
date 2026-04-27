---
title: LLM Gateway, Models, Routing and Billing Tasks
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-27
feature_id: 011
migrated_from:
  - specs/execution/exec-16-llm-provider-gateway.md
  - specs/execution/exec-a2fm-adaptive-routing.md
---

# Tasks

## Migration

- [x] T001 Import ADR-001 smart routing rollout gate into
  `routing-gates.md`.
- [x] T002 Import A2FM paper research into `research.md`.
- [x] T003 Split subfeatures into gateway, settings, model, billing,
  reasoning, routing and A2FM.

## Gateway

- [x] T010 Verify LiteLLM starts on port 4000.
- [x] T011 Verify `/v1/chat/completions` non-streaming response.
- T012 Verify streaming SSE response.
- T013 Verify tool-call response arguments shape.
- T014 Verify direct provider fallback mode still works.
- [x] T015 Decide whether docker-compose LiteLLM path remains active.

## Credentials And Settings

- T020 Verify key set/delete/validate endpoints.
- T021 Verify encrypted DB value and masked API response.
- T022 Verify Python-encrypted value can be read by Go path where relevant.
- T023 Verify missing `KEY_ENCRYPTION_SECRET` fails closed.
- T024 Decide multi-key CredentialPool scope.
- T025 Decide `preferred_runner`/dispatcher override scope.
- T026 Verify remote embedding calls, starting with MemPalace/OpenRouter, use
  CredentialPool/user consent/quota/audit instead of unaudited env-only secrets
  before production enablement.

## Model Selection

- T030 Verify Control UI model explorer loads live provider/model data.
- T031 Verify Agent Chat model picker shows only active provider models.
- T032 Verify selected model reaches backend request.
- [x] T033 Verify selected model reaches LiteLLM/provider.
- [x] T034 Decide and implement/defer persisted user model selection.

## Billing And Insights

- [x] T040 Static-test `CanonicalUsage` prompt/completion/cache/reasoning token
  handling.
- [x] T041 Static-test cost estimate and model metadata logic.
- T042 Verify span attributes contain cost and usage.
- [x] T043 Verify InsightsEngine rollup.
- T044 Verify LiteLLM spend logs with configured DB.
- T045 Add or defer event-driven rollup.
- T046 Add or defer smart-routing cost-attribution split.
- T047 Add embedding usage/cost attribution for OpenRouter embedding models
  once MemPalace remote embeddings leave dev/smoke mode.

## Reasoning Budget

- T050 Verify Anthropic/OpenRouter reasoning effort high returns thinking
  content and reasoning tokens.
- T051 Verify OpenAI reasoning effort high returns usage details.
- T052 Verify reasoning deltas stream to frontend.
- T053 Implement or defer `_compute_auto_effort`.
- T054 Add or defer Control-UI auto-mode capable filter.

## Smart Routing

- [x] T060 Verify G1 bilingual keyword/tokenizer behavior.
- [x] T061 Verify G2 credential pre-flight keeps primary when cheap provider
  is unavailable.
- [x] T062 Verify G3 config cache avoids per-turn DB connection churn.
- [x] T063 Verify G4 A/B routing dimensions are written.
- T064 Verify G5 user-visible routing indicator.
- T065 Verify G6 Control-UI smart-routing toggle/disable path.
- [x] T066 Verify P1 `router_node` routing behavior and fallback behavior.
- [x] T067 Fix F-G4 A/B insert/update race with routing upsert semantics.
- [x] T068 Fix F-G1 keyword quality by removing broad single-word blockers and
  adding phrase-level checks/tests.
- [x] T069 Document F-4g4 scorer eval-id semantics as first-write-wins.

## A2FM Phase 2+

- T070 Implement L1 post-hoc mode labeling report when enough audit events
  exist.
- T071 Implement L2 adaptive reward feedback only after L1 proves useful.
- [x] T072 Keep L3 classifier deferred until corpus and L2 plateau justify it.
- [x] T073 Keep L4 full A2FM training out of current scope.

## Verify Gates

- LiteLLM responds to chat completion.
- Tool-call response shape is compatible.
- Model list loads.
- Billing row/span exists for a real call.
- Routing is off-by-default or passes G1-G6/P1 live verify.
