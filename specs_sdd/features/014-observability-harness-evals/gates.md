---
title: Observability Harness Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
---

# Gate Ledger

## OTel / OpenObserve

- OpenObserve starts on configured ports.
- Collector accepts OTLP gRPC/HTTP.
- Python service emits trace when `OTEL_ENABLED=true`.
- Go service emits trace when `OTEL_ENABLED=true`.
- `OTEL_ENABLED=false` produces no crash and no meaningful overhead.
- No app code calls OpenObserve APIs directly outside OTel/exporter paths.

## Agent Spans

- One Agent Chat turn produces `agent.session`.
- LLM call produces `agent.turn` with provider/model/token/cost attrs.
- Tool call produces `agent.tool_call` with success/error/duration attrs.
- Memory recall/retain produces `agent.memory`.
- Approval/consent gate emits approved/denied counts.

## Audit

- Auditable action creates `agent.audit_events` row.
- Audit event is queryable from backend/control path.
- Tracing content and audit content follow ADR-002 separation.

## Harness

- `score_session` produces composite fitness.
- A/B backfill worker fills missing fitness scores.
- eval id behavior is deterministic/documented.
- Pareto frontier can compute from real candidate data.

## Evaluator

- small search set runs through evaluator.
- result rows persist.
- scorer output includes accuracy/cost/latency/grounding dimensions where
  applicable.
- cache avoids re-running identical config/query/model combinations.

## Eval Workpacks

- Each workpack records prerequisites, command/probe, expected evidence and
  owning feature.
- A workpack is closed only with evidence, not by code existence.
