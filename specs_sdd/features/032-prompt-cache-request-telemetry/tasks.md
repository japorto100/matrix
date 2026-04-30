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

- T010 Implement normalized usage extraction for prompt/input/output/cache
  read/cache write/total counters.
- T011 Record last-call usage and session totals in agent runtime traces.
- T012 Add request metadata capture for request id, processing time and
  rate-limit headers when providers expose them.
- T013 Add deterministic prompt/tool digest generation with secret redaction.
- [partial-static] T014 Detect meaningful cache-read drops and emit a cache-break event with
  reasons.
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
- T021 Add Meta-Harness cache-stability scenario with stable prompt/tool
  ordering.
- T022 Add regression scenario where MCP reload invalidates cache and surfaces
  explicit impact metadata.
  - 2026-04-30: static regressions cover MCP reload impact,
    skill catalog digest changes and prompt-cache replay of cache-impact events.
