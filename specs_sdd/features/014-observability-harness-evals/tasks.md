---
title: Observability, Harness and Evals Tasks
status: static_verified_live_pending
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
- [x] T004 Move or explicitly reference harness CSV under feature evidence.

## OTel Runtime

- T010 Verify OpenObserve starts and collector accepts OTLP.
- T011 Verify Go OTel span reaches backend.
- T012 Verify Python OTel span reaches backend.
- T013 Verify `OTEL_ENABLED=false` path is no-op.
- T014 Verify no direct OpenObserve API calls outside exporter/auth config.
- T015 Verify Tier-2 Next.js BFF `@vercel/otel` if implemented.
- T016 Keep Tier-3 browser RUM deferred until BFF proxy/privacy design.

## Agent Spans

- T020 [done-live-postgres] Verify `agent.session` root span.
  - 2026-04-27: `AGENT_PERSIST_TRACES=1` plus `PostgresSpanProcessor`
    persisted an `agent.session` span for session
    `codex-live-014-6e167f2a` with trace
    `7b2483b8d6bb7265a703326386ce2f8a`.
- T021 Verify prompt/LLM `agent.turn` spans.
- T022 Verify `agent.tool_call` spans.
- T023 Verify memory recall/retain spans.
- T024 Verify approval/consent spans.
- T025 Verify token/cost/model attrs.
- T026 Verify trace content redaction/sensitive policy.

## Audit

- T030 [done-live-postgres] Verify auditable action writes `agent.audit_events`.
  - 2026-04-27: `audit_log(action=TOOL_CALL, user_id=local)` persisted a row
    in live Matrix Postgres.
- T031 [done-live-api] Verify Control UI Audit tab/query route shows event.
  - 2026-04-27: `GET /api/v1/control/audit?thread_id=thread-014-route-fe8c0851`
    returned `total=1`.
- T032 Verify ADR-002 separation: tracing is not audit, audit is not tracing.
- T033 Define/defer per-tool `audit_required` flag with Feature 013.

## Harness

- [x] T040 Verify `score_session` composite fitness.
- T041 Verify A/B backfill worker fills missing score rows.
- [x] T042 Static-test eval-id semantics after rescoring/document current
  behavior.
- [x] T043 Verify routing-specific race/followups with Feature 011.
- T044 Add/defer Control UI Pareto dashboards.
- T045 Add/defer fitness weight tuning.
- T046 Route per-model context thresholds from Feature 012 to harness
  research.

## Evaluator

- [x] T050 Implement/verify async-parallel evaluator.
- [x] T051 Implement/verify evaluator cache.
- [x] T052 Implement/verify scorer interfaces.
- T053 [done-live-postgres] Run small search-set eval and persist results.
  - 2026-04-27: added Alembic migration `033_agent_evals`; `save_eval_run`
    inserted `eval-live-014-6e167f2a` into `agent.evals`.
- [x] T054 Integrate proposer loop with real evaluator, not mocks.
- T055 Add/defer Feedback Descent pairwise mode.

## Eval Workpacks

- [x] T060 Convert `exec-eval` workpacks into SDD-linked live verify items.
- [x] T061 Ensure each workpack has prerequisites, command/probe and expected
  evidence.

## Verify Gates

- [x] One live trace is queryable from Postgres.
- [x] One audit event is queryable through the backend/control route.
- [x] One harness/eval score is generated in static tests.
- [x] One harness/eval result is persisted in `agent.evals`.
- [x] Evidence is stored or linked under feature evidence.

## 2026-04-29 Feature 024-030 Trace Follow-Up

- T062 Add MCP catalog policy trace fields from Feature 024: descriptor hash,
  risk, policy verdict and call/denial.
- T063 Add semantic lookup trace fields from Feature 025: term id, metric id,
  definition version and ambiguity status.
- T064 Add ops-room read-model export for Feature 029.
- T065 Add widget proposal/audit trace fields from Feature 030.

## 2026-04-30 Feature 032-033 Trace Additions

- T066 Add provider request/cache usage trace fields: provider, model, router,
  prompt digest, tool digest, token counters and unknown-counter flags.
- T067 Add runtime event envelope trace fields for run/turn/tool/memory/RAG/KG/
  artifact/subagent events.
- [partial-static] T068 Add stale/recovery/action trace fields for pause, kill, replay, MCP
  reload and cached-session invalidation.
  - 2026-04-30: MCP and skill reload/toggle/import emit
    `agent-cache-impact/v1` plus Feature 033 `cache.invalidated`/
    `cache.unchanged` runtime events. Pause/kill/replay action traces remain
    pending.
- T069 Add redaction tests for request telemetry and runtime event payloads.
- [x] T070 Add skill-search trace fields for trigger-quality/debugging:
  selected ids, query terms, BM25/RRF scores, matched terms and ranking reason.
  - 2026-04-30: `find_skills_with_trace()` and `skill_found` audit metadata
    expose body-redacted search traces that Meta-Harness can assert without
    browser or provider calls.
