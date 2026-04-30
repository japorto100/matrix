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
- Cache-break evidence needs a snapshot of provider, model, transport,
  cache-retention mode, system-prompt digest and tool digest.
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

2026-04-30 reload follow-up: MCP reload, skill reload, skill toggle and skill
import now use the same provider-agnostic `agent-cache-impact/v1` envelope. The
digest material is redacted to hashes and metadata, not raw prompts or raw skill
content. This keeps the Hermes/OpenClaw cache-stability lesson but makes the
contract independent of OpenAI/Anthropic-specific cache APIs.
