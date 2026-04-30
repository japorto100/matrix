---
title: LLM Gateway, Models, Routing and Billing Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
feature_id: 011
---

# Gates

## 2026-04-29 Provider-Agnostic Follow-Up

- Regular live lanes use a real configured provider path; `llm-mock` is limited
  to deterministic tests.
- Provider capability detection is data-driven and does not hardcode a single
  vendor contract into agent prompts.

## G1 Gateway / Provider

- [x] LiteLLM starts on port 4000.
- [x] `/v1/chat/completions` non-streaming response works.
- [x] Streaming SSE response works.
- [ ] Tool-call response arguments shape is compatible.
- [ ] Direct provider fallback path still works.

## G2 Credentials / Settings

- [x] Credential preflight tests pass.
- [x] Smart-routing config cache tests pass.
- [x] CredentialPool tests pass.
- [ ] Key set/delete/validate endpoints are live-verified.
- [ ] Encrypted DB value and masked API response are live-verified.
- [ ] Missing `KEY_ENCRYPTION_SECRET` fails closed in operator config.
- [x] Meta-Harness/dev anonymous LLM path is reviewed so it cannot bypass
  production named-user CredentialPool, quotas, billing or audit. Current
  fallback is development/local/test only unless explicitly enabled.
- [ ] OpenRouter embedding calls for MemPalace are reviewed under the same
  credential/redaction/quota/audit rules as chat model calls.

## G3 Model Selection

- [x] Model metadata tests pass.
- [ ] Control UI model explorer loads live provider/model data.
- [x] Agent Chat backend accepts selected/default model through BFF/backend;
  browser picker render remains Feature 007/Frontend live scope.
- [x] Selected model reaches LiteLLM/provider.

## G4 Billing / Insights

- [x] Canonical usage pricing tests pass.
- [x] Insights rollup tests pass.
- [ ] Real LLM response writes usage/cost/span data.
- [ ] LiteLLM spend logs are visible with configured DB.
- [ ] Event-driven rollup is implemented or explicitly deferred.
- [ ] Embedding model usage/cost is represented before remote MemPalace
  embeddings are enabled beyond dev/smoke.

## G5 Smart Routing

- [x] Router-node tests cover bilingual keyword behavior, credential preflight,
  config absence and routing error fallback.
- [x] A/B routing metadata write helper is tested.
- [ ] User-visible routing indicator is browser/live verified.
- [ ] Control UI smart-routing toggle/disable path is live verified.
- [x] F-G4 race, F-G1 keyword quality and F-4g4 scorer semantics are fixed or
  accepted in closeout.

## G6 A2FM Boundary

- [x] A2FM remains research/phase-2+ and is not treated as shipped router.
- [ ] L1 post-hoc mode labeling starts only after enough audit events exist.
- [ ] L2/L3/L4 adaptive/classifier/training work remains deferred unless
  promoted.

## 2026-04-30 Added Gates

- [ ] Provider request telemetry normalizes request id, processing time and
  rate-limit headers when available.
- [ ] Usage counters distinguish input, output, cache read, cache write and
  total.
- [ ] Unknown provider counters remain unknown instead of guessed.
- [ ] Provider-specific reasoning and resolved credentials are redacted from
  telemetry and artifacts.
