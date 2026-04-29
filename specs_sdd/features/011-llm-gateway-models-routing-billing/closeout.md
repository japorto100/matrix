---
title: LLM Gateway, Models, Routing and Billing Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
feature_id: 011
---

# Closeout

## Built

- LiteLLM/OpenRouter-oriented gateway path and direct provider fallback logic.
- User credential/security primitives, credential preflight and smart-routing
  config cache.
- Model metadata, model explorer backend/control surfaces and utility model
  structures.
- Persisted default-model and selected-model settings exist on the Control
  router and are covered by DB-mocked endpoint tests.
- Canonical usage pricing and insights rollup logic.
- Smart routing router-node logic and A/B routing metadata write helper.
- A/B routing metadata write is now race-resistant: routing upsert can create a
  pending row and dispatcher insert later fills base experiment fields without
  clobbering routing fields.
- Smart-routing keyword quality was tightened: broad English single-word
  blockers were replaced with targeted phrase checks plus domain-specific terms.
- Resilience primitives around credential pools, error classification and rate
  limit tracking.
- LiteLLM compose liveness is separated from provider diagnostics: container
  health now uses `/health/liveliness` so missing or exhausted provider keys do
  not mark the gateway process itself unhealthy.

## Not Built

- Live-verified LiteLLM streaming/tool-call smoke in this pass.
- Live DB-backed spend dashboard proof.
- Live provider reasoning-token/thinking-content proof.
- A2FM learned classifier/router; this remains research/phase-2+.

## Deviations From Plan

- ADR-001 gates are built at logic/test level, but broad rollout still depends
  on live verification and follow-up decisions.
- A2FM is not the current shipped router; current routing is conservative
  heuristic plus credential preflight.
- Scorer `harness_eval_id` semantics are accepted as first-write-wins via
  `COALESCE`; no overwrite mode is shipped in this pass.

## Verify Result

- PASS static: `uv run pytest tests/agent/billing tests/agent/llm tests/agent/resilience tests/agent/security/test_credential_preflight.py tests/agent/security/test_smart_routing_cache.py tests/agent/graph/nodes/test_router_node.py tests/agent/runners/test_mark_routing.py -q`.
- PASS static: `uv run pytest tests/agent/llm/test_smart_routing.py tests/agent/runners/test_mark_routing.py tests/agent/graph/nodes/test_router_node.py -q`.
- PASS static: `uv run pytest tests/agent/control/test_user_llm_selection.py tests/agent/security/test_user_model_lookup.py -q`.
- PASS live: `GET http://127.0.0.1:4000/health/liveliness` returned `200`
  and `podman inspect litellm` reported container health `healthy`.
- PASS live: `scripts/dev-stack.sh --status` reported LiteLLM, Postgres,
  NATS, Valkey, python-agent, python-bridge and python-ingestion up.

## Live Verify Result

Pending: LiteLLM streaming/tool-call provider shape, live model list,
DB-backed spend dashboard, reasoning-token provider response and browser
routing controls.

Note: LiteLLM `/health` is treated as a provider/credential diagnostic, not as
container liveness. In the current dev stack it can fail or hang when a
configured provider key is missing/invalid/exhausted; that belongs to provider
verify gates rather than process health.

## Follow-Ups

- Live-verify A/B rows against a real Postgres instance when the full stack is
  running.
- Keep A2FM L1/L2/L3/L4 deferred until audit corpus and feedback data justify
  promotion.
