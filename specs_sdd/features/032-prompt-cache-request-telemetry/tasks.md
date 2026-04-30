---
title: Prompt Cache Request Telemetry Tasks
status: planned
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 032
---

# Tasks

## Research And Spec

- T001 Capture Hermes/OpenClaw/OpenClaude cache and usage transfer notes in
  `research.md`.
- T002 Define provider-agnostic request telemetry fields and redaction rules.
- T003 Define cache snapshot fields: provider, model, transport,
  cache-retention, system digest, tool digest, tool count and tool names.
- T004 Define cache-break reasons: model, transport, cache retention, system
  prompt, tools, MCP reload, skill reload and stream strategy.

## Backend

- [x] T010 Implement normalized usage extraction for prompt/input/output/cache
  read/cache write/total counters.
  - 2026-04-30: `UsageTelemetry` now carries provider-agnostic
    `prompt_tokens`, fresh `input_tokens`, `completion_tokens`,
    `output_tokens`, `total_tokens`, `reasoning_tokens`,
    `cache_read_tokens` and `cache_write_tokens`. Fresh input remains
    `unknown` unless prompt, cache-read and cache-write counters are all known.
- [partial-static] T011 Record last-call usage and session totals in agent runtime traces.
  - 2026-04-30: per-call `request_telemetry` is emitted by `llm_node`, and
    graph state still accumulates prompt/completion/reasoning/cache/total
    counters. A consolidated per-session telemetry summary remains open.
  - 2026-04-30: the prompt-cache read model now exposes `by_thread` session
    rollups for requests, cache impacts, invalidations, cache breaks,
    provider/model sets and prompt/completion/cache token totals. Runtime graph
    state still owns in-turn counters; replay surfaces now have the durable
    session summary.
- [x] T012 [done-static] Add request metadata capture for request id,
  processing time and rate-limit headers when providers expose them.
  - 2026-04-30: LLM runtime telemetry now stores allowlisted response metadata
    under `metadata.response`: request id, provider/local duration and
    normalized rate-limit buckets. It intentionally excludes raw headers,
    prompt text and secrets.
- [x] T013 Add deterministic prompt/tool digest generation with secret redaction.
  - 2026-04-30: request telemetry computes `prompt_digest`,
    `prompt_layout_digest` and `tool_catalog_digest` from normalized prompt
    shape and sorted tool descriptors. Raw prompt text and tool schemas are not
    stored in telemetry.
- [x] T014 [done-static] Detect meaningful cache-read drops and emit a
  cache-break event with reasons.
  - 2026-04-30: `llm_node` emits `llm.prompt_cache_break` runtime events when
    request telemetry reports model/prompt/tool cache-break reasons or when
    cache-read tokens drop versus the previous request. Event metadata carries
    digests, reasons, request id and cache-read counters only.
- [x] T015 [done-static] Ensure MCP reload and tool catalog changes mark cached agent sessions
  stale or force a rebind.
  - 2026-04-30: MCP reload and skill reload/toggle/import now return or audit
    `agent-cache-impact/v1`; unknown or changed prior digests set
    `rebind_required` for cached sessions without mutating the same turn.

## UI And Harness

- [partial-static] T020 Add Control UI Prompt Cache surface with current session counters,
  cache-break reasons and recent request traces.
  - 2026-04-30: Ops events expose prompt-cache link metadata from
    `provider-request-telemetry/v1` including provider, model, prompt/tool
    digests, cache read/write counters and cache-break reasons.
  - 2026-04-30: `/api/v1/control/prompt-cache` now builds a read model from
    audit request telemetry, and `/control/prompt-cache` renders current
    counters, break reasons, provider/model distribution and recent traces.
  - 2026-04-30: backend read model now includes `by_thread`, so Control/Ops
    can link a session to prompt-cache totals without recomputing from raw
    audit rows.
- [x] T021 Add Meta-Harness cache-stability scenario with stable prompt/tool
  ordering.
  - 2026-04-30: `prompt-cache-contract` adds provider-free scenarios for
    stable prompt/tool digests, content-only prompt change reasons, tool schema
    cache-break reasons and unknown usage counters.
  - 2026-04-30: `run-prompt-cache-contract-gate` passed 4/4 scenarios.
- [x] T022 [done-static] Add regression scenario where MCP reload invalidates
  cache and surfaces explicit impact metadata.
  - 2026-04-30: static regressions cover MCP reload impact,
    skill catalog digest changes and prompt-cache replay of cache-impact events.
  - 2026-04-30: `prompt-cache-mcp-reload-impact-replayed` now runs in the
    provider-free `prompt-cache-contract`; the lane has 5 scenarios and the
    aggregate contract suite has 46 scenarios.
- [x] T023 [done-static] Add provider-free session rollup scenario for
  prompt-cache request telemetry.
  - 2026-04-30: `prompt-cache-thread-session-rollup` validates two request
    telemetry items collapse into one thread summary with cache read/write
    totals, cache-break count and provider de-duplication. The
    `prompt-cache-contract` lane now has 6 scenarios.
