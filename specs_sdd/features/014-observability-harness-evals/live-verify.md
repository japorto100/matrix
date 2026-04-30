---
title: Observability, Harness and Evals Live Verify
status: partial-backend-live
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
---

# Live Verify

## 2026-04-29 Feature 024-030 Trace Follow-Up

- Verify MCP policy denial appears in trace/audit with descriptor hash.
- Verify semantic lookup appears before a metric answer.
- Verify ops-room replay can be built from a Meta-Harness run artifact.
- Verify widget proposal approval/denial is visible in audit search.

## Tracing

- Start runtime with tracing env.
- Run one Agent Chat turn.
- Confirm trace ID is produced.
- Confirm span data is persisted.
- Confirm OpenObserve or configured backend can query it.
- Confirm Go and Python traces both appear when enabled.
- Confirm disabled tracing does not crash.

## Audit

- Trigger auditable action.
- Confirm audit event persisted.
- Confirm Control UI Audit tab shows event or query route works.

## Harness / Evals

- Run one small eval/harness job.
- Command/probe:
  `cd python-backend && uv run python - <<'PY'
  import asyncio, json
  from meta_harness.evaluator import evaluate_search_set
  print(json.dumps(asyncio.run(evaluate_search_set(max_queries=1, concurrency=1)), indent=2))
  PY`
- Confirm score rows are produced.
- Confirm composite fitness fields are populated.
- Confirm A/B backfill worker path if in scope.
- Confirm eval/candidate/source evidence is linked or stored.

## Eval Workpacks

Each migrated `exec-eval` workpack closes only when evidence is linked in the
owning feature's `live-verify.md` or `closeout.md`.

### EVAL-01 Matrix Chat Verify Gates

- Owning features: 004, 005, 007.
- Prerequisites: Tuwunel, Sliding Sync, Matrix UI, optional Element X/LiveKit.
- Command/probe: run local devstack, perform login/room/timeline/send/upload and
  optional second-client interop.
- Expected evidence: URLs, screenshots/log excerpts and failing gate notes.

### EVAL-02 NATS E2E Test

- Owning feature: 006.
- Prerequisites: NATS, registered Go appservice, Python bridge, mock or real
  agent backend.
- Command/probe: send Matrix message through Go -> NATS -> Python -> NATS -> Go
  and assert the Matrix reply appears.
- Expected evidence: NATS subjects, appservice log lines, Python bridge log
  lines and Matrix event IDs.

### EVAL-03 Agent Chat E2E and Voice

- Owning feature: 007.
- Prerequisites: Go gateway `/api/v1/agent/*`, Python Agent service, provider
  key or mock mode; LiveKit only for voice.
- Command/probe: run SSE chat turn, tool approval/reject flow and optional
  STT -> LLM -> TTS latency probe.
- Expected evidence: SSE event transcript, approval audit row and voice latency
  measurement if voice is in scope.

### EVAL-04 Memory Verify

- Owning feature: 012.
- Prerequisites: `HINDSIGHT_DB_URL`, Postgres+pgvector and provider key for
  retain/reflect paths.
- Command/probe: run retain/recall/reflect/consolidate on the shared corpus.
- Expected evidence: memory row IDs, recall result snippets, consolidation log
  and conflict/degradation notes.

### EVAL-05 Messaging Bridges

- Owning features: 006 and bridge-specific follow-up features.
- Prerequisites: external platform accounts/devices, appservice registrations,
  stable NATS pipeline.
- Command/probe: bridge message to Matrix and agent response back to platform.
- Expected evidence: platform message IDs, Matrix event IDs and routing logs per
  bridge.

### EVAL-06 MCP and Generative UI

- Owning feature: 008.
- Prerequisites: Python MCP server, Go MCP proxy, Agent Chat UI and supported
  browser/WebMCP runtime or polyfill.
- Command/probe: list tools, render one visible A2UI surface, verify canvas and
  WebMCP capability when runtime supports it.
- Expected evidence: tool-list payload, `data-a2ui-*` screenshot/DOM capture and
  browser capability output.

### EVAL-07 Devstack Control UI

- Owning features: 002, 010, 012.
- Prerequisites: devstack, SeaweedFS, PostgreSQL+pgvector, Python agent service
  and ingestion worker.
- Command/probe: start devstack, inspect all Control UI tabs, upload/preview one
  file and query memory/KG surfaces.
- Expected evidence: service health output, tab inventory, upload ID and
  memory/KG query response.

## Sources

- Confirm paper/product sources in `sources.md` still match current tasks.
- Confirm any paper-derived task names the adopted idea.

## Result

partial backend live pass; OpenObserve/collector and browser dashboard gates
remain open.

## 2026-04-30 Added Live Gates

- LV030 Query a real agent run and verify request/cache telemetry fields are
  present with redacted prompt digests.
- LV031 Query runtime events for run/turn/tool/memory/RAG/KG/artifact/subagent
  and verify event id/parent id ordering.
- LV032 Trigger pause/kill/replay/reload and verify trace/audit refs are linked
  but separated per ADR-002.

## Backend Evidence 2026-04-27

- Live Postgres migration:
  `HINDSIGHT_DB_URL=... uv run alembic upgrade head` applied
  `033_agent_evals`.
- Schema inventory regenerated and `tests/test_schema_governance.py -q`
  returned `3 passed`.
- Trace persistence:
  `AGENT_PERSIST_TRACES=1` plus `PostgresSpanProcessor` persisted an
  `agent.session` span for session `codex-live-014-6e167f2a`; query returned
  trace `7b2483b8d6bb7265a703326386ce2f8a`.
- Audit persistence:
  `audit_log(action=TOOL_CALL, user_id=local, thread_id=thread-014-route-fe8c0851)`
  wrote `agent.audit_events`.
- Control audit route:
  `GET /api/v1/control/audit?thread_id=thread-014-route-fe8c0851&limit=5`
  returned `total=1` and item `tool_name=feature014.control_route`.
- Eval persistence:
  `save_eval_run(run_id=eval-live-014-6e167f2a, eval_type=feature014_live_smoke)`
  wrote one row into `agent.evals`.
- Härtung: `audit_log()` now writes `userId` with default `local`, so scoped
  Control queries can see backend-generated audit rows.

Still open:

- OpenObserve/OTel collector live query.
- Go+Python distributed trace in the collector.
- Full Agent Chat turn with LLM/tool/memory/approval spans.
- Pareto dashboards and A/B backfill worker.
