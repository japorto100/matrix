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

## 2026-04-26 Automatic Retain Verbatim-First Probe

Status: pass for backend-only Memory-Fusion after Meta-Harness outer-loop
candidate `memory-fusion-verbatim-first-retain`.

Evidence:

- Matrix memory-dev stack after reboot: Postgres `:5433` healthy, FalkorDB
  `:6380` running, Python Agent `:8094` healthy, LiteLLM `:4000` reachable with
  OpenRouter health pass.
- Manual Alembic upgrade against `hindsight_dev` completed before agent start.
- Fixed env loading so shell/process overrides such as
  `AGENT_AUTO_MIGRATE=false` and `PORT=9999` survive `.env.development`; this
  made controlled agent starts possible after reboot.
- Direct live probe:
  `MemoryAddTool.execute` returned `{"stored": true, "facts_extracted": 1}` and
  `MemorySearchTool.execute` returned the exact MemPalace/Postgres/pgvector
  context phrase.
- Direct `memory_recall_node` probe injected `## Relevant Context` with one
  `Personal Raw Evidence` block from MemPalace/Postgres.
- Meta-Harness run `run-408242ed1c2c`, candidate
  `memory-fusion-env-override-live`, passed both memory lifecycle scenarios
  (`trace_gate_pass_rate=1.0`, `completion_rate=1.0`,
  `fitness_score=0.8583`) but exposed automatic post-answer retain timeouts at
  `MEMORY_RETAIN_TIMEOUT_SEC=20`.
- Fix: automatic `memory_retain_node` now writes route `verbatim`
  synchronously and queues route `summary` in the background via
  `submit_async_retain`, matching the explicit memory tool path.
- Follow-up Meta-Harness run `run-a1cc52e7217f`, candidate
  `memory-fusion-verbatim-first-retain`, passed both memory lifecycle scenarios
  with no retain timeout messages. Trace events show route `verbatim`,
  provider `fusion`, providers `verbatim,summary_async`, and
  `summary_status=background_queued`.
- Meta-Harness run `run-a25abb61e18f`, candidate
  `memory-fusion-clean-tool-markup`, verified that new user-facing assistant
  text no longer leaks raw `<tool_call>` blocks, but exposed a stronger
  LangGraph/OpenAI serialization bug after `memory_search`:
  `messages[5]: missing field tool_call_id`.
- Fix: LangGraph `tool_node` now emits OpenAI-compatible `tool_call_id` on
  `role=tool` messages while retaining legacy `tool_use_id`.
- Follow-up Meta-Harness run `run-f1078e290e9f`, candidate
  `memory-fusion-openai-tool-message-id`, passed both memory lifecycle
  scenarios with `trace_gate_pass_rate=1.0`, `completion_rate=1.0` and
  `fitness_score=0.875`. The explicit `memory_search` tool returned results and
  the subsequent LLM response completed without OpenRouter 400.
- Focused tests:
  `uv run pytest tests/agent/graph/nodes/test_tool_node.py tests/agent/test_llm_node_caching.py tests/agent/graph/nodes/test_memory_node.py tests/bridge/test_env_loading.py tests/memory_fusion/test_mempalace_postgres_engine.py tests/agent/tools/test_memory_hindsight.py`
  => `29 passed`.
- Ruff:
  `uv run ruff check agent/graph/nodes/tool_node.py tests/agent/graph/nodes/test_tool_node.py agent/graph/nodes/llm_node.py tests/agent/test_llm_node_caching.py shared/app_factory.py bridge/config.py tests/bridge/test_env_loading.py agent/graph/nodes/memory_node.py tests/agent/graph/nodes/test_memory_node.py`
  => pass.

Residual risk:

- Old dev-memory rows from earlier probes can still contain historical
  `<tool_call>` text and may be retrieved as evidence until dev memory is reset
  or cleaned; new assistant output is cleaned before audit/SSE/memory sync.
- Shared-corpus evals and compaction/pre-save threshold live gates remain open.

## Result

partial pass; explicit tools, automatic recall injection, and automatic
verbatim-first retain are live-verified. Tool-message serialization and
assistant tool-markup cleanup are fixed for new turns. Remaining live work is
latency/cost, compaction threshold, historical dev-memory cleanup, and broader
Hindsight/MemPalace/Fusion shared-corpus eval coverage.
