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
  - 2026-04-30: docs now make cache ownership explicit: provider/gateway owns
    actual prompt-cache storage, while Matrix owns only redacted counters,
    digests, rollups and cache-impact metadata.
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
  - 2026-04-30: request telemetry now emits explicit cache-break reasons for
    model, transport, cache retention, stream strategy, system prompt,
    prompt layout/content and tool catalog changes. Legacy telemetry without
    snapshot fields is handled without fabricated break reasons.
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
  - 2026-04-30: prompt-cache read model now exposes `by_thread` summaries with
    request counts, cache impact counts, invalidations, cache breaks, token
    totals and provider/model sets.
  - 2026-04-30: read model rows expose transport, cache retention, stream
    strategy, system digest, tool count and sorted tool names for the Control
    UI without raw prompt/tool content.
- [x] G008 Meta-Harness can fail a candidate that churns stable prompt/tool order.
  - 2026-04-30: `prompt-cache-contract` requires unchanged prompt/layout/tool
    digests for equivalent inputs and no cache-break reasons when only tool
    ordering changes.
  - 2026-04-30: `run-prompt-cache-contract-gate` passed 4/4 without provider
    calls.
  - 2026-04-30: `prompt-cache-snapshot-break-dimensions` extends the lane to
    7 provider-free scenarios, including cache-retention, transport,
    stream-strategy and system-prompt changes.
- [x] G009 MCP reload cache invalidation is visible in provider-free harness
  and read-model replay.
  - 2026-04-30: `prompt-cache-mcp-reload-impact-replayed` requires
    `agent-cache-impact/v1`, `cache.invalidated` runtime event and
    prompt-cache read model `cache_invalidations=1`.
- [x] G010 Session-level prompt-cache totals are replayable without a browser.
  - 2026-04-30: `prompt-cache-thread-session-rollup` validates backend
    `by_thread` rollups for cache read/write totals, cache-break count and
    provider de-duplication from audit-backed telemetry.
- [x] G011 All-time prompt-cache totals survive beyond the recent audit replay
  window.
  - 2026-04-30: `agent.prompt_cache_thread_summaries` stores per-user,
    per-thread cumulative request/cache-impact/cache-read/write/token totals.
    The Control API returns `aggregate: prompt-cache-aggregate/v1`, while
    recent `items` remain limited trace rows.
- [x] G012 Live provider probe uses the real Agent LLM path, not a mock.
  - 2026-04-30: `scripts/live_prompt_cache_probe.py` exercises
    `llm_node` with a long stable prefix and real OpenRouter/LiteLLM
    credentials; it passes only when the provider exposes second-call
    cache-read evidence.
