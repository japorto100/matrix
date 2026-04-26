---
title: Memory, Context, World Model and Personal KB Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
---

# Live Verify

## Personal Memory

- Start Python backend with memory dependencies.
- Query memory health endpoint/control contract.
- Confirm episodic/vector/KG layer states.
- Store a test memory or observation if supported.
- Retrieve that memory through recall/search path.
- Retain raw user input and confirm it is evidence, not derived truth.
- Retain derived observation and confirm source/evidence backlink.
- Try KB-like artifact in personal-memory path and confirm reject/bridge
  behavior.
- Try world-like claim in personal-memory path and confirm reject/bridge
  behavior.

## Context Runtime

- Run an Agent Chat turn.
- Inspect prompt/context metrics.
- Confirm static/dynamic prompt block order matches spec.
- Confirm missing layer flags are visible.
- Trigger or simulate compaction threshold if safe.
- Confirm provenance/evidence survives compaction expectations.
- Confirm pre-save/backstop happens before lossy compression where testable.

## World Model

- Add or inspect world evidence record if implemented.
- Confirm claim/KG/adjudication path or mark planned.
- If a world claim exists: retrieve claim with evidence/status/provenance.

## Personal KB

- Capture a personal KB item if implemented.
- Retrieve KB item in runtime context if implemented.
- If a KB artifact exists: retrieve it as KB, not world truth.
- Mark unimplemented surfaces as planned, not broken.

## Eval

- Run Hindsight shared-corpus eval or document blocker.
- Run MemPalace shared-corpus eval or document blocker.
- Run fusion shared-corpus eval or document blocker.
- Run memory_fusion E2E smoke or document blocker.

## 2026-04-26 Explicit Memory Tool Probe

Status: pass for explicit `memory_add`/`memory_search` path after making
summary retain background-only.

Evidence:

- Direct `MemoryAddTool.execute` with OpenRouter embeddings and Postgres
  MemPalace returned `{"stored": true, "facts_extracted": 1}` in 21.535s.
- Meta-Harness run `run-6e38bdc3fc39`, candidate
  `memory-fusion-facttype-normalized-full-384`, scenarios
  `ml-memory-explicit-add-search-001` and `ml-memory-fusion-route-001` passed
  trace gates.
- Observed trace: `memory_retain` route `fusion`, providers
  `verbatim,summary_async`, storage route `verbatim`, fact type `experience`,
  and `summary_status=background_queued`.
- Observed `memory_search` returned the exact phrase as the top result through
  Fusion/MemPalace recall. Existing dev rows may still show older
  non-normalized fact types; new writes normalize unknown fact types to
  `experience`.
- LLM-invented write fact types such as `project_memory` are normalized to
  `experience` and preserved as `original_fact_type` metadata.
- Follow-up run `run-33660bc2c88e`, candidate
  `memory-lifecycle-memory-timeout-90`, passed both memory lifecycle scenarios
  with `trace_gate_pass_rate=1.0`, `completion_rate=1.0` and
  `fitness_score=0.8583`.
- `memory_add` cold path was observed at about 18s, so memory tools now have a
  dedicated `MEMORY_TOOL_TIMEOUT_SEC=90` budget instead of the generic 30s
  tool timeout. Remaining risk is latency/cost, not correctness.
- Meta-Harness live probe `run-594f7f420f5c`, candidate
  `live-probe-memory-isolated`, passed the explicit memory scenario with
  `memory_add` and `memory_search`, tool success `1.0`, observed memory route
  `fusion`, and providers `fusion`, `verbatim`, `summary_async`.
- Post-answer automatic retain is now bounded by `MEMORY_RETAIN_TIMEOUT_SEC=20`
  in the agent graph. In live probes it timed out but did not block SSE finish;
  this is tracked as latency/reliability follow-up, not explicit memory-tool
  correctness failure.

## Result

partial pass; remaining live work is latency, compaction threshold, and broader
Hindsight/MemPalace/Fusion shared-corpus eval coverage.
