---
title: MCP Gateway Tool Catalog Policy Gates
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-30
feature_id: 024
---

# Gates

- G001 External MCP servers are disabled until explicit config enables them.
- G002 Every descriptor has provenance, descriptor hash and first/last seen
  timestamps.
- G003 Tool name collisions and lookalikes require manual review.
- G004 Tool descriptions are scanned for prompt-injection/tool-poisoning
  patterns before model exposure.
- G005 Token passthrough is denied unless an explicit credential scope matches.
- G006 Confirm/destructive tools fail closed if approval UI is unavailable.
- G007 Tool output is size-capped before entering agent context.
- G008 Resource/widget metadata is not executable UI without Feature 030 host
  policy.
- G009 Descriptor changes after approval trigger risk escalation.
- G010 Audit events exist for discovery, exposure, denial, execution and
  descriptor change.
- G011 Control UI shows effective policy, not raw unfiltered descriptor state.
- G012 Meta-Harness can replay allowed, denied and poisoned-descriptor cases.
- G013 Tool discovery uses regex/token search plus BM25-style scoring over
  policy-visible summaries, not full schema stuffing.

## Static Progress

- [x] G002 descriptor snapshots and catalog entries include hashes,
  timestamps and user-visible provenance metadata.
- [x] G003 duplicate normalized names and external high-trust lookalikes are
  blocked in the effective catalog.
- [x] G004 descriptor text and metadata are scanned before exposure.
- [x] G005 token passthrough requires explicit named credential scope.
- [x] G006 non-auto tools fail closed without approval channel or a valid
  session grant.
- [x] G007 MCP gateway execution caps output bytes before provider-facing tool
  messages are emitted.
- [x] G012 deterministic fixture descriptors and health probes cover allowed
  local MCP policy without invoking model-visible tools.
- [x] G011 Control and agent-facing catalog endpoints expose policy-filtered
  entries, not raw unfiltered descriptors.
- [x] G013 builtin tool discovery searches summaries with token/regex
  BM25-style scoring and keeps high-disclosure schemas out of results.
- [x] G013 MCP discovery searches only effective-catalog visible entries and
  returns provenance/risk/approval summaries without full schemas.

## 2026-04-30 Added Gates

- [x] MCP reload emits prompt-cache invalidation impact metadata.
  - 2026-04-30: confirmed and preview reloads return
    `agent-cache-impact/v1` metadata with previous/current catalog digests.
- [x] Cached agent sessions are invalidated or rebound after descriptor/tool
  catalog changes.
  - 2026-04-30: unknown or changed prior digests produce `rebind_required`,
    giving cached sessions a deterministic rebinding signal.
- [x] Descriptor diffs and reload decisions emit Feature 033 runtime events.
  - 2026-04-30: reload impact is mirrored as `cache.invalidated`/
    `cache.unchanged` runtime event metadata for Ops replay.
- [x] Progressive discovery remains metadata-only until full schema exposure is
  policy-approved.
  - 2026-04-30: the agent runtime now consumes builtin tool discovery only as
    `Tool Discovery Hints` with name/group/risk/approval/summary; provider tool
    schemas remain in the normal tool-calling payload and are not duplicated in
    the prompt.
  - 2026-05-01: full schema exposure is now approved only for selected builtin
    tools after local policy search or explicit `tool_search`; external MCP
    descriptors remain metadata-only until their own execution policy allows
    promotion.
- [x] Provider-facing builtin tool schemas can be deferred without losing a
  discovery path.
  - 2026-05-01: `selected_tools_for_turn()` reduces large active tool sets to
    query-relevant schemas plus `tool_search`; `tool_search` returns
    metadata-only matches, and both LangGraph and SimpleLoop expand
    `tool_definitions` after the search result. Unit tests cover searched
    subsets, exact-name high-risk override and schema expansion.
  - 2026-05-01 live no-browser: Local-8B memory floor without scenario
    `allowed_tools` passed through the real dispatcher with
    `AGENT_DEFER_TOOL_SCHEMAS=true`. The provider request telemetry reported
    `tool_count=4` (`memory_add`, `memory_search`, `save_memory`,
    `tool_search`) instead of the full builtin registry, and trace/stream gates
    passed at `1.0`.
  - 2026-05-01 live no-browser: Local-8B chart/tool-stream floor without
    scenario `allowed_tools` passed through the real dispatcher with
    `AGENT_DEFER_TOOL_SCHEMAS=true`. Provider request telemetry reported
    `tool_count=4` (`get_chart_state`, `get_geomap_focus`, `set_chart_state`,
    `tool_search`), `get_chart_state` executed successfully, and trace/stream
    gates passed at `1.0`.
  - 2026-05-01 live no-browser: the stricter chart no-allowlist rerun
    `run-local8b-floor-chart-no-allowlist-001-clean` kept the same provider
    `tool_count=4`, executed `get_chart_state`, surfaced downstream stream
    events (`tool-input-start`, `tool-output-available`, rich renderer), and
    passed trace/stream/tool gates at `1.0` with no automatic memory recall or
    retain side effect. This is the current clean proof that deferred builtin
    schema selection can drive a normal tool-control turn without memory
    pollution.
