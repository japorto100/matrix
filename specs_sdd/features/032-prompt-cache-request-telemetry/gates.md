---
title: Prompt Cache Request Telemetry Gates
status: planned
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 032
---

# Gates

- G001 Telemetry is provider-agnostic and preserves unknown counters as unknown.
- G002 Request ids and rate-limit headers are redacted and never written to
  memory/KG as factual user content.
- G003 Stable prompt/tool digests are deterministic across equivalent runs.
- G004 Cache-break events include a reason or explicitly say reason unknown.
- G005 MCP reload and tool descriptor changes mark cache invalidation impact.
- G006 Skills reload does not mutate the system prompt in the same turn.
- G007 Control UI shows cache evidence without provider-specific secrets.
- G008 Meta-Harness can fail a candidate that churns stable prompt/tool order.

