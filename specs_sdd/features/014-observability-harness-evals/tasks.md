---
title: Observability, Harness and Evals Tasks
status: in_progress
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
migrated_from:
  - specs/execution/exec-17-observability-harness-traces.md
  - specs/execution/exec-harness.md
  - specs/execution/exec-eval.md
---

# Tasks

## Migration

- [x] T001 Preserve paper/product sources in `sources.md`.
- [x] T002 Import ADR-002 tracing/audit parallel-store decision.
- [x] T003 Split runtime observability, audit, harness and eval workpacks.
- [ ] T004 Move or explicitly reference harness CSV under feature evidence.

## OTel Runtime

- [ ] T010 Verify OpenObserve starts and collector accepts OTLP.
- [ ] T011 Verify Go OTel span reaches backend.
- [ ] T012 Verify Python OTel span reaches backend.
- [ ] T013 Verify `OTEL_ENABLED=false` path is no-op.
- [ ] T014 Verify no direct OpenObserve API calls outside exporter/auth config.
- [ ] T015 Verify Tier-2 Next.js BFF `@vercel/otel` if implemented.
- [ ] T016 Keep Tier-3 browser RUM deferred until BFF proxy/privacy design.

## Agent Spans

- [ ] T020 Verify `agent.session` root span.
- [ ] T021 Verify prompt/LLM `agent.turn` spans.
- [ ] T022 Verify `agent.tool_call` spans.
- [ ] T023 Verify memory recall/retain spans.
- [ ] T024 Verify approval/consent spans.
- [ ] T025 Verify token/cost/model attrs.
- [ ] T026 Verify trace content redaction/sensitive policy.

## Audit

- [ ] T030 Verify auditable action writes `agent.audit_events`.
- [ ] T031 Verify Control UI Audit tab/query route shows event.
- [ ] T032 Verify ADR-002 separation: tracing is not audit, audit is not tracing.
- [ ] T033 Define/defer per-tool `audit_required` flag with Feature 013.

## Harness

- [ ] T040 Verify `score_session` composite fitness.
- [ ] T041 Verify A/B backfill worker fills missing score rows.
- [ ] T042 Verify eval-id semantics after rescoring.
- [ ] T043 Verify routing-specific race/followups with Feature 011.
- [ ] T044 Add/defer Control UI Pareto dashboards.
- [ ] T045 Add/defer fitness weight tuning.
- [ ] T046 Route per-model context thresholds from Feature 012 to harness
  research.

## Evaluator

- [ ] T050 Implement/verify async-parallel evaluator.
- [ ] T051 Implement/verify evaluator cache.
- [ ] T052 Implement/verify scorer interfaces.
- [ ] T053 Run small search-set eval and persist results.
- [ ] T054 Integrate proposer loop with real evaluator, not mocks.
- [ ] T055 Add/defer Feedback Descent pairwise mode.

## Eval Workpacks

- [ ] T060 Convert `exec-eval` workpacks into SDD-linked live verify items.
- [ ] T061 Ensure each workpack has prerequisites, command/probe and expected
  evidence.

## Verify Gates

- [ ] One live trace is queryable.
- [ ] One audit event is queryable.
- [ ] One harness/eval score is generated.
- [ ] Evidence is stored or linked under feature evidence.
