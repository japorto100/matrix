---
title: LLM Gateway Subfeatures
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 011
migrated_from:
  - specs/execution/exec-16-llm-provider-gateway.md
  - specs/execution/exec-a2fm-adaptive-routing.md
  - specs/execution/superpower-impl-log.md
---

# Subfeatures

## 011.1 LiteLLM Gateway

Status: built, live verify required.

Scope:

- LiteLLM proxy in isolated `python-backend/litellm-gateway` venv.
- Port 4000 gateway with provider config and OpenAI-compatible API.
- Direct provider fallback mode through ENV remains available.
- OpenRouter direct/aggregated/free model paths.

Open:

- Verify chat completions, streaming and tool calls against current config.
- Decide whether docker-compose LiteLLM service is still needed or only venv
  path is supported.

## 011.2 User LLM Settings And Credentials

Status: built.

Scope:

- `agent.user_llm_settings`.
- shared `agent.user_credentials` by category/provider.
- Python and Go AES-256-GCM KeyVault with prefix format.
- Go HPKE/ML-KEM backend readiness.
- CRUD endpoints for default model, role overrides and provider keys.

Open:

- Multi-key credential pool beyond `SingleKeyCredentialPool`.
- Preferred runner column for dispatcher override if still needed.

## 011.3 Model Discovery And Selection

Status: mostly built.

Scope:

- Model explorer/control UI provider state.
- Agent Chat model picker.
- model metadata cache through LiteLLM `get_model_info`.
- reasoning type/levels in model info.

Open:

- Persist user model selection beyond current request/local UI behavior.
- Verify selected model affects a live Agent Chat request.

## 011.4 Billing And Insights

Status: built, live verify required.

Scope:

- `CanonicalUsage` normalization.
- `estimate_usage_cost`.
- span attributes for usage/cost.
- `InsightsEngine` rollup from spans.
- LiteLLM spend tracking DB.

Open:

- Event-driven rollup.
- Smart-routing cost-attribution split.
- Live spend dashboard verification with `LITELLM_DATABASE_URL`.

## 011.5 Reasoning Budget

Status: partially built.

Scope:

- `reasoning_effort` pass-through to LiteLLM.
- reasoning delta streaming.
- reasoning token metadata in usage.

Open:

- Provider-access live gates for Anthropic/OpenAI reasoning models.
- `_compute_auto_effort` heuristic.
- Control-UI filter for auto-mode capable models.
- Reasoning quality sort once dashboard data exists.

## 011.6 Smart Routing Phase 0/1

Status: built, rollout requires live verification.

Scope:

- bilingual cheap-vs-strong heuristic.
- credential pre-flight.
- 60s config cache.
- A/B routing dimensions.
- user-visible indicator.
- Control-UI smart-routing panel and disable path.
- `router_node` Phase-1 architecture.

Open:

- Follow-up F-G1: review over-broad English keywords.
- Follow-up F-G4: fix insert/update ordering race.
- Validate actual cost savings and quality impact before broad default.

## 011.7 A2FM-Inspired Phase 2+

Status: research.

Scope:

- L1 post-hoc mode labeling of audit logs.
- L2 adaptive-reward feedback loop for threshold tuning.
- L3 optional small encoder classifier after sufficient audit corpus.
- L4 full A2FM-style model training is deferred research.

Decision:

- Do L1/L2 before any ML classifier. If audit data says most queries are one
  mode, optimize that case instead of building a router prematurely.
