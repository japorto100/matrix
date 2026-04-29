---
title: Observability, Harness and Evals Plan
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
migrated_from:
  - specs/execution/exec-17-observability-harness-traces.md
  - specs/execution/exec-harness.md
  - specs/execution/exec-eval.md
  - docs/superpowers/findings/2026-04-23-adr-002-tracing-audit-parallel-stores.md
  - docs/superpowers/findings/2026-04-24-observability-tier-strategy.md
adrs:
  - 0002
---

# Plan

## Architecture

Observability captures traces, spans, audit events and eval outputs. Harness
uses those artifacts for scoring, A/B backfills and future optimization.
OpenTelemetry is the vendor-neutral producer layer; OpenObserve is the current
backend/UI consumer.

## Critical Files

- `python-backend/agent/tracing/**`
- `python-backend/agent/audit/**`
- `python-backend/meta_harness/**`
- `python-backend/shared/app_factory.py`
- `go-appservice/internal/telemetry/**`
- `otel-collector.yaml`
- `docker-compose.otel.yml`
- `python-backend/agent/billing/insights.py`
- `frontend_merger/src/features/control/**Audit*`
- `frontend_merger/src/features/control/**Spend*`
- `frontend_merger/src/instrumentation.ts`

## Migration Strategy

1. Preserve sources/papers in `sources.md`.
2. Import ADR-0002 into gates/subfeatures.
3. Split observability runtime from harness optimization tasks.
4. Keep eval runbooks executable and narrow.
5. Treat browser RUM as a separate security-sensitive follow-up.

## Execution Order

1. Run OTel/OpenObserve live smoke for Go and Python.
2. Verify Agent Chat produces queryable nested agent spans.
3. Verify audit path separately from trace path.
4. Verify harness backfill/composite fitness on a small session set.
5. Build Evaluator Stage-4 loop only after trace/eval persistence is reliable.

## Risks

- Recording traces locally but not verifying queryability.
- Harness metrics being computed without stable eval IDs.
- Leaking secrets or prompts into trace backend without policy.
- Treating OpenObserve-specific auth/config as if it were OTel itself.
