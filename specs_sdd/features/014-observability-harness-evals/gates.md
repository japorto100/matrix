---
title: Observability Harness Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
---

# Gate Ledger

## 2026-04-29 Feature 024-030 Trace Follow-Up

- MCP policy decisions include descriptor hash and policy verdict.
- Semantic answers include lookup and definition-version traces.
- Ops-room events can be derived from trace/audit data without hidden state.
- Widget proposal/approval/revoke events are traceable.

## OTel / OpenObserve

- OpenObserve starts on configured ports.
- Collector accepts OTLP gRPC/HTTP.
- Python service emits trace when `OTEL_ENABLED=true`.
- Go service emits trace when `OTEL_ENABLED=true`.
- `OTEL_ENABLED=false` produces no crash and no meaningful overhead.
- No app code calls OpenObserve APIs directly outside OTel/exporter paths.

## Agent Spans

- [x] One backend trace produces persisted `agent.session` in Postgres.
- LLM call produces `agent.turn` with provider/model/token/cost attrs.
- Tool call produces `agent.tool_call` with success/error/duration attrs.
- Memory recall/retain produces `agent.memory`.
- Approval/consent gate emits approved/denied counts.

## Audit

- [x] Auditable action creates `agent.audit_events` row.
- [x] Audit event is queryable from backend/control path.
- Tracing content and audit content follow ADR-002 separation.

## Harness

- [x] `score_session` produces composite fitness in tests.
- A/B backfill worker fills missing fitness scores.
- [x] eval id behavior is deterministic/documented in tests.
- [x] routing-specific follow-ups are synchronized with Feature 011.
- Pareto frontier can compute from real candidate data.

## Evaluator

- small search set runs through evaluator.
- [x] result rows persist in `agent.evals`.
- scorer output includes accuracy/cost/latency/grounding dimensions where
  applicable.
- cache avoids re-running identical config/query/model combinations.

## Eval Workpacks

- [x] Historical Superpowers harness-mode CSV is linked with checksum.
- Each workpack records prerequisites, command/probe, expected evidence and
  owning feature.
- A workpack is closed only with evidence, not by code existence.

## Runtime / Cache Telemetry Gates

- Provider request/cache telemetry is queryable without storing raw prompts by
  default.
- Runtime event envelopes preserve event id, parent id, session id, status,
  timestamp and redacted metadata.
- [partial-static] Pause/kill/replay/reload actions emit both audit-safe and
  trace-safe refs.
  - 2026-04-30: reload paths now emit audit-safe cache-impact metadata and
    trace-safe runtime events; pause/kill/replay verification remains open.
- Unknown provider counters remain explicit unknowns, not fabricated zeros.
