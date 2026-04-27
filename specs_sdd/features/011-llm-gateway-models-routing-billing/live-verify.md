---
title: LLM Gateway, Models, Routing and Billing Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
feature_id: 011
---

# Live Verify

## Gateway

- Start LiteLLM.
- Call `/v1/chat/completions` through LiteLLM.
- Verify tool-call response with JSON arguments.
- Verify streaming response shape.

## Models

- Load model explorer in Control UI.
- Confirm model count/data comes from live gateway.
- Select model in UI.
- Confirm selected model affects Agent Chat request.
- Confirm selected model reaches LiteLLM/provider logs.

## Credentials

- Add/update provider credential.
- Confirm credential is stored encrypted.
- Confirm missing credential produces actionable error.

## Billing / Spend

- Configure LiteLLM DB.
- Run one billable request.
- Confirm usage ledger records request.
- Confirm span metadata includes prompt/completion/cache/reasoning token
  fields where provider supplies them.
- Confirm Spend dashboard shows data.

## Reasoning Budget

- Send a high-reasoning request through Anthropic/OpenRouter.
- Confirm thinking/reasoning content streams or provider-supported fallback
  is documented.
- Confirm `reasoning_tokens` appears in usage where supported.

## Smart Routing

- Enable smart routing for test user only.
- Trigger cheap path.
- Trigger strong path.
- Confirm user-visible routing indicator.
- Confirm Control-UI disable path turns routing off.
- Confirm A/B row records `routing_used`, reason and picked model.
- Confirm missing cheap-provider credential keeps primary model.
- Confirm ADR G1-G6/P1 checklist is satisfied before broader rollout.

## Follow-Ups

- [x] F-G4 race fixed at static/SQL-shape level.
- [x] F-G1 keyword quality fixed at static heuristic-test level.
- [x] F-4g4 scorer eval-id semantics documented as first-write-wins.

## Result

partial pass; backend streaming/default-model path is live verified, UI picker,
tool-call provider shape, spend dashboard and production credential drills remain
open.

## Live Evidence 2026-04-27

- Meta-Harness exposed a real DevStack issue: the LiteLLM container inherited
  `HINDSIGHT_DB_URL=...@localhost:5433...`, which points at the LiteLLM
  container itself. `docker-compose.yml` now overrides this for the container
  path as `...@postgres:5432...`.
- Recreated LiteLLM with `COMPOSE_PROFILES=litellm podman-compose up -d
  litellm`; the service listens on `:4000`.
- `GET /health/liveliness` returns `200` quickly and the compose healthcheck
  now uses that endpoint. `GET /health` stays a provider/credential diagnostic;
  it can fail or hang when configured provider keys are missing, invalid or
  quota-exhausted, so it is not used as the container liveness gate.
- `podman inspect litellm` reports container health `healthy`.
- Meta-Harness run `run-5f24325e7b1c` used the in-process simple runner through
  LiteLLM/OpenRouter with model `openrouter/openrouter/free`; metadata showed
  provider `openrouter`, model `openrouter/openrouter/free`, and successful
  `llm_response`.
- Direct Agent SSE smoke returned AI-SDK-v6 packets through the live Python
  service:
  - request: `POST http://localhost:8094/api/v1/agent/chat` with
    `x-auth-user: @alice:matrix.local`
  - model metadata: provider `openrouter`, model `openrouter/openrouter/free`
  - text packet: `{"type":"text-delta","delta":"matrix parser fixed"}`
- Matrix live bridge smoke then proved the same model response reaches the
  Matrix room via Python Bridge and Go Appservice:
  - room `!whDYMsaAvmfYe_DAuHoAO9GdXITGGtjMuNoDSBmpkKg`
  - reply body `matrix parser fixed`
- Credential boundary update: production still uses `agent.user_credentials`;
  provider ENV fallback is limited to development/local/test by default, with
  `AGENT_ALLOW_ENV_CREDENTIAL_FALLBACK` as an explicit override.

Remaining:

- tool-call response shape through raw LiteLLM;
- Control UI model explorer/picker;
- DB-backed spend dashboard;
- production credential/security drill for missing/invalid configured keys.
