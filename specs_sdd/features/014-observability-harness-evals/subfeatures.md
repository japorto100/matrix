---
title: Observability Harness Subfeatures
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
---

# Subfeatures

## 014.1 OTel Infrastructure

Status: built, live verify required.

Scope:

- `otel-collector.yaml`.
- `docker-compose.otel.yml`.
- OpenObserve service/devstack integration.
- Python `shared/app_factory.py` OTel.
- Go `internal/telemetry`.
- env wiring for Python, Go and frontend.

Open:

- run full devstack with `OTEL_ENABLED=true`.
- verify backend trace appears in OpenObserve.
- verify `OTEL_ENABLED=false` has graceful no-op behavior.

## 014.2 Agent Execution Spans

Status: built, live verify required.

Scope:

- `agent.session` root span.
- `agent.turn` spans for prompt construction and LLM calls.
- `agent.tool_call` spans.
- `agent.memory` spans for recall/retain.
- approval/consent span attributes.

Open:

- confirm nested span tree in queryable backend.
- confirm cost/token/model attrs appear on LLM spans.
- confirm no sensitive content leaks beyond configured policy.

## 014.3 Audit Parallel Store

Status: decided.

Scope:

- tracing (`agent.spans`) and audit (`agent.audit_events`) remain parallel.
- audit stores compliance/content events.
- tracing stores runtime/latency/structure.

Open:

- future per-tool `audit_required` classification.
- ensure removed cross-writes stay removed.

## 014.4 Frontend Observability Tiers

Status: tier 1 built, tier 2 in-scope, tier 3 follow-up.

Scope:

- Tier 1: backend Go/Python OTel.
- Tier 2: Next.js BFF server-side `@vercel/otel`.
- Tier 3: browser RUM via BFF proxy only.

Decision:

- no direct browser OTLP export with credentials.
- Browser RUM requires CSP/CORS/consent/privacy design.

## 014.5 Harness Scoring And A/B

Status: partial.

Scope:

- composite fitness.
- A/B experiments.
- routing dimensions.
- harness backfill worker.
- eval-id wiring.
- Pareto helper.

Open:

- race/follow-up interactions tracked in Feature 011 when routing-specific.
- Control UI Pareto dashboards.
- fitness weight tuning.

## 014.6 Evaluator Full Loop

Status: planned.

Scope:

- async parallel evaluator.
- evaluator cache.
- `agent/harness/scorers/`.
- full eval aggregation into persistent rows.
- skill and Hermes-pattern consumers.
- optional feedback descent pairwise scoring.

Open:

- Stage-4 implementation.
- persistent `agent.evals`/component config integration where not already done.
- end-to-end proposer -> evaluator -> frontier loop.

## 014.7 Eval Workpacks

Status: active backlog.

Scope:

- Matrix chat verify.
- NATS E2E.
- Agent Chat/Voice.
- Memory.
- Messaging bridges.
- MCP/Generative UI.
- Control UI.

Decision:

- keep infra/account/secret gated verification here, not duplicated as code
  tasks inside each feature.
