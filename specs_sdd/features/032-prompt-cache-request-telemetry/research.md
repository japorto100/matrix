---
title: Prompt Cache Request Telemetry Research
status: draft
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 032
---

# Research

## Local References

- `Z_Additional_For_Tool_Stuff.md`: tool catalog/search should not stuff full
  schemas into the prompt; descriptor/tool ordering affects cache stability.
- `_ref/hermes-agent`: `/usage` shows session input/output/cache read/cache
  write, MCP reload warns that tool schema changes invalidate provider prompt
  cache, skills reload is moved to a next-turn note to preserve cache.
- `_ref/claude_code/openclaw`: `docs/reference/prompt-caching.md`,
  `src/agents/pi-embedded-runner/prompt-cache-observability.ts`,
  `src/agents/cache-trace.ts` and usage accumulator code show the clearest
  provider-agnostic cache observability shape.
- `_ref/claude_code/openclaude`: `OPENCLAUDE_LOG_TOKEN_USAGE` and
  `/config showCacheStats` separate user-facing debug output from model-facing
  token-usage attachment.

## Findings

- Cache counters should be normalized into `input`, `output`, `cache_read`,
  `cache_write` and `total`, with "unknown" preserved when providers do not
  expose a value.
- The actual prompt/KV cache is provider-owned. Matrix cannot inspect, delete
  or reuse provider cache entries directly; it can only shape requests with
  provider-supported hints and record returned usage counters.
- Cache-break evidence needs a snapshot of provider, model, transport,
  cache-retention mode, system-prompt digest and tool digest.
- The snapshot should be provider-neutral enough to survive transport changes:
  `transport` names the client/API path, `cache_retention` names the cache
  policy class, and `stream_strategy` names the wire strategy. Provider-native
  names can appear only as values, not as required schema branches.
- Tool schema/MCP changes are real cache invalidation events. They need a
  user-visible impact warning and runtime session rebind/invalidation.
- Volatile content should live below a cache boundary; stable tool/skill/system
  sections should be deterministically ordered.

2026-04-30 implementation note: Ops now converts request telemetry into a
`linked_surfaces.prompt_cache` ref with provider, model, prompt/layout/tool
digests, cache read/write counters and cache-break reasons. The dedicated
`/control/prompt-cache` surface reads the same audit-backed data and keeps
unknown counters explicit instead of fabricating cache values.

2026-04-30 response metadata update: `provider-request-telemetry/v1` now carries
allowlisted provider response metadata under `metadata.response`: request id,
provider processing duration, local duration and normalized rate-limit buckets.
This is intentionally not a raw-header dump. It gives prompt-cache and Ops
surfaces enough quota/latency context while preserving provider-agnostic
redaction.

2026-04-30 cache-break runtime update: `llm_node` now emits a separate
`llm.prompt_cache_break` runtime event when cache locality changes after the
first request. The event is derived from provider-agnostic request telemetry:
model/prompt/tool digest breaks plus cache-read-token drops versus the previous
request. It carries digests and counters only, so Agent Chat/Ops can render a
diagnostic card without parsing provider-specific chunks or raw prompts.

2026-04-30 reload follow-up: MCP reload, skill reload, skill toggle and skill
import now use the same provider-agnostic `agent-cache-impact/v1` envelope. The
digest material is redacted to hashes and metadata, not raw prompts or raw skill
content. This keeps the Hermes/OpenClaw cache-stability lesson but makes the
contract independent of OpenAI/Anthropic-specific cache APIs.

2026-04-30 harness update: the provider-free `prompt-cache-contract` now replays
an MCP reload cache-impact event through the prompt-cache read model. This
guards the Hermes-derived requirement that tool catalog changes invalidate or
rebind cached agent sessions, while keeping the implementation provider-neutral
and UI-readable.

2026-04-30 session rollup update: cache observability now has a backend
session aggregate, not only request rows and UI counters. The prompt-cache read
model exposes `by_thread` with request count, cache impact count,
invalidations, cache breaks, prompt/completion/cache token totals, unknown
cache-field count and provider/model sets. The provider-free
`prompt-cache-thread-session-rollup` scenario checks this directly from audit
telemetry, matching the Hermes/OpenClaw lesson that cache stats must be
session-readable without relying on a CLI/TUI or provider-specific logs.

2026-04-30 snapshot implementation update: `provider-request-telemetry/v1`
now carries the cache snapshot as top-level telemetry fields: provider, model,
router, transport, cache retention, stream strategy, prompt digest, layout
digest, system prompt digest, tool catalog digest, tool count and sorted tool
names. Raw system text and raw tool schema content remain absent. The
provider-free `prompt-cache-snapshot-break-dimensions` gate verifies transport,
cache-retention, stream-strategy and system-prompt break reasons, while MCP and
skill reloads stay represented by `agent-cache-impact/v1` so reload provenance
does not get confused with one request's prompt diff.

2026-04-30 Z_Prompt_Cache alignment: large `cached` token counters are
cumulative reuse counters across requests, not one huge context window. Matrix
matches this interpretation by treating cache reads/writes as provider usage
telemetry and by rolling them up per thread/session. The cache storage itself
remains upstream/provider-owned; Matrix stores only redacted request telemetry,
digests and cache-impact events.

2026-04-30 durable aggregate update: to avoid confusing "recent trace window"
with "all-time cached token reuse", Control now materializes per-user,
per-thread cumulative stats in `agent.prompt_cache_thread_summaries`. This
preserves the Z_Prompt_Cache interpretation that cached tokens can be much
larger than fresh input over many calls, while keeping Matrix provider-agnostic:
only counters, provider/model labels, digests and redacted thread summaries are
stored. The actual cache state remains provider/gateway-owned.

2026-04-30 live probe update: `scripts/live_prompt_cache_probe.py` verifies the
real Agent LLM path, not a mock. It sends two same-prefix calls through
`llm_node`, using the existing Anthropic-family `cache_control` injection and
fails unless the second call exposes provider cache-read counters. This is a
live gate because OpenRouter/model support and upstream cache behavior are
runtime facts, not static guarantees.
