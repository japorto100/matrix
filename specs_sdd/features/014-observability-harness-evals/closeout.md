---
title: Observability, Harness and Evals Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
---

# Closeout

## Built

- OTel/OpenObserve wiring is present by docs/config, pending live proof.
- Agent tracing/span helpers and Postgres span processor exist.
- Audit store and MCP trace-tool code exist.
- Harness scorer composite fitness and eval-id behavior are covered by tests.
- Billing insights rollup and trajectory export logic are covered by tests.
- Control runtime static tests pass.
- Historical harness-mode report/CSV is linked in `evidence.md` with checksum;
  it is header-only and therefore not positive live scoring evidence.

## Not Built

- Live OpenObserve trace evidence in this pass.
- Live queryable audit event evidence in this pass.
- Full Evaluator Stage-4 loop with persisted result rows.
- Control UI Pareto dashboards and fitness weight tuning.
- Browser RUM tier; intentionally deferred for privacy/security design.

## Deviations From Plan

- ADR-002 remains the governing separation: tracing and audit are parallel
  stores, not one overloaded event stream.
- Feature 014 cannot close on local tests alone; it needs at least one live
  trace and one audit/eval evidence path.

## Verify Result

- PASS static: `uv run pytest tests/agent/harness/test_scorer.py tests/agent/billing/test_insights.py tests/agent/test_trajectory_export.py tests/agent/test_control_runtime.py -q`.
- PASS static: Feature 011 routing race/keyword/eval-id follow-ups are
  synchronized with this feature's harness ledger.

## Live Verify Result

Pending: OpenObserve/OTLP live trace, queryable audit row and persistent eval
score evidence.

## Follow-Ups

- Run `dev-stack --observability` or equivalent and capture one queryable trace.
- Execute one auditable action and verify backend/control query path.
- Run one small eval workpack and persist score/evidence rows.
- Decide dashboard/weight tuning scope after initial live evidence exists.
