---
title: Observability, Harness and Evals
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
  - docs/superpowers/findings/2026-04-23-harness-mode-analysis.md
  - docs/superpowers/findings/2026-04-23-harness-mode-analysis.csv
  - docs/superpowers/findings/2026-04-24-observability-tier-strategy.md
adrs:
  - 0002
---

# Observability, Harness and Evals

## Current State / Ist

OTel infra stages 1-5 are documented as landed: Python, Go, collector,
OpenObserve compose/devstack wiring and span taxonomy. Agent execution spans are
implemented, but live `dev-stack --observability` verification is still pending.
Tracing and audit are intentionally parallel stores per ADR-002. Harness
composite fitness, A/B backfill and eval-id wiring have landed, while full
Evaluator Stage-4, dashboards and weighting remain open.

Static verification on 2026-04-25 passes harness scorer, billing insights,
trajectory export and control runtime tests. This proves local scoring/export
logic, not a live OpenObserve/audit/eval persistence path.

## Target State / Soll

Agent/runtime behavior is observable through traces, audit events and evals.
Harness scoring can compare changes, route experiments and feed future routing
or context decisions.

## Subfeatures

- Trace/span model
- Audit events and parallel-store ADR
- OpenTelemetry/OpenObserve tiers
- Langfuse/LLM-specific observability path
- MCP trace tools
- Harness composite fitness
- A/B backfill and Pareto analysis
- AutoResearch component tuning
- Meta-Harness trace-informed optimization
- Eval runbooks
- Evidence artifacts and CSV inputs

## Gap

- OpenObserve live trace verification is pending.
- Harness TODOs around eval IDs, dashboards and weighting need task extraction.
- Evaluator Stage-4 full loop remains open.
- Browser RUM tier remains a separate follow-up because of security/privacy.
- CSV/source evidence should be copied or referenced under feature evidence.

Static cleanup on 2026-04-25 adds `evidence.md`, which references the
Superpowers harness-mode report/CSV, records the CSV fingerprint and clarifies
that the historical CSV is header-only because no audit-event threads were
found. Eval-id semantics are synchronized with Feature 011 as first-write-wins.

## Static Verify

- [x] `uv run pytest tests/meta_harness/test_scorer.py tests/agent/billing/test_insights.py tests/agent/test_trajectory_export.py tests/agent/test_control_runtime.py -q` passes.
- [x] Harness scorer composite fitness logic is covered.
- [x] Insights rollup and trajectory export logic are covered.
- [x] Control runtime static tests pass.
- [x] Historical harness-mode report/CSV is linked with checksum in
  `evidence.md`.

## Live Verify

- Live trace reaches OpenObserve or documented target.
- Audit event is persisted and queryable.
- Harness backfill produces expected score rows.
- One eval run fills persistent eval/score data.
- Eval runbook can be executed on current stack.

## Closeout Criteria

- Observability cannot close on docs alone; it needs at least one live trace and
  one audit/eval evidence path.
