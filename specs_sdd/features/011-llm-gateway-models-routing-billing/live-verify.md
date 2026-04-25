---
title: LLM Gateway, Models, Routing and Billing Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
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

pending
