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
  - 2026-04-30: normalized request usage now separates prompt vs fresh input
    and completion vs output tokens. Fresh input is only populated when cache
    read/write counters are known; otherwise `unknown_fields` records the
    missing counters.
- G002 Request ids and rate-limit headers are redacted and never written to
  memory/KG as factual user content.
  - 2026-04-30: free-form request telemetry metadata is recursively sanitized:
    response request ids remain, but raw prompts/messages, headers,
    authorization, resolved secrets and provider-specific reasoning/thinking
    blocks are dropped before trace emission.
- G003 Stable prompt/tool digests are deterministic across equivalent runs.
  - 2026-04-30: `digest_prompt()` separates content digest from layout digest,
    and `digest_tool_catalog()` sorts tools before hashing descriptor shape.
- G004 Cache-break events include a reason or explicitly say reason unknown.
- [x] G005 MCP reload and tool descriptor changes mark cache invalidation impact.
  - 2026-04-30: `agent-cache-impact/v1` carries previous/current digest,
    source, reason and `rebind_required` action for MCP reloads.
- [x] G006 Skills reload does not mutate the system prompt in the same turn.
  - 2026-04-30: `/skills/reload` is a control action with
    `reload_mode=next_turn_rebind`; toggles/imports audit cache-impact metadata
    and runtime events for the next agent turn.
- [partial-static] G007 Control UI shows cache evidence without provider-specific secrets.
  - 2026-04-30: Ops drilldown shows provider/model/cache counters and digests
    from redacted request telemetry. `/control/prompt-cache` now renders the
    dedicated trace table from the same audit-backed read model.
  - 2026-04-30: prompt-cache read model also replays cache-impact events so the
    surface can join cache invalidation, request telemetry and Ops events.
- [x] G008 Meta-Harness can fail a candidate that churns stable prompt/tool order.
  - 2026-04-30: `prompt-cache-contract` requires unchanged prompt/layout/tool
    digests for equivalent inputs and no cache-break reasons when only tool
    ordering changes.
  - 2026-04-30: `run-prompt-cache-contract-gate` passed 4/4 without provider
    calls.
- [x] G009 MCP reload cache invalidation is visible in provider-free harness
  and read-model replay.
  - 2026-04-30: `prompt-cache-mcp-reload-impact-replayed` requires
    `agent-cache-impact/v1`, `cache.invalidated` runtime event and
    prompt-cache read model `cache_invalidations=1`.
