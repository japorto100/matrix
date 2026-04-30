---
title: Prompt Cache Request Telemetry Live Verify
status: planned
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 032
---

# Live Verify

- LV001 Run two same-prefix provider calls and verify cache counters are
  captured when the provider exposes them.
- LV002 Reload MCP tools and verify cache invalidation impact appears in trace
  and Control UI.
- LV003 Reload skills and verify the next-turn note path does not change the
  stable system prompt digest.
- LV004 Open Control UI Prompt Cache surface and verify counters, request id
  redaction, model/provider and cache-break reason render.
- LV005 Run Meta-Harness cache-stability lane and verify deterministic tool
  ordering.

