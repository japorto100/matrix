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
- T014 Detect meaningful cache-read drops and emit a cache-break event with
  reasons.
- T015 Ensure MCP reload and tool catalog changes mark cached agent sessions
  stale or force a rebind.

## UI And Harness

- [partial-static] T020 Add Control UI Prompt Cache surface with current session counters,
  cache-break reasons and recent request traces.
  - 2026-04-30: Ops events expose prompt-cache link metadata from
    `provider-request-telemetry/v1` including provider, model, prompt/tool
    digests, cache read/write counters and cache-break reasons. The link
    targets `/control/context` until a dedicated cache surface is added.
- T021 Add Meta-Harness cache-stability scenario with stable prompt/tool
  ordering.
- T022 Add regression scenario where MCP reload invalidates cache and surfaces
  explicit impact metadata.
