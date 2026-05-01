---
title: MCP Gateway Tool Catalog Policy Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-30
feature_id: 024
---

# Research

## Local Z Reference

Derived from `Z_Additional_For_Tool_Stuff.md`, but only for the external MCP
portion. The core recommendation is broader than MCP: "Gateway + Tool-Katalog +
Policy + Code-Execution-Schicht" instead of stuffing many tools directly into
the model prompt. Feature 024 owns external MCP descriptors/resources. Normal
`ToolRegistry` tool groups, progressive disclosure and policy metadata are
tracked in Feature 016 and surfaced by Feature 010.

## Working Judgement

MCP is now a real interoperability layer, but the security story is still
immature enough that Matrix should treat every external MCP descriptor as
untrusted input. The right product shape is not "plug any MCP server straight
into the agent". It is a gateway with descriptor snapshots, policy filtering,
explicit credential scopes, approval gates and audit evidence.

## Source Check 2026-04-29

- Provider ecosystems are converging on MCP-backed tool/app/resource surfaces.
  Matrix should learn from those descriptor/resource concepts without binding
  the runtime to any single model or vendor SDK.
- MCP Apps-style examples show widget metadata and UI resources attached to
  tool results. Matrix should therefore split "tool execution permitted" from
  "resource/widget executable in a host".
- OWASP MCP Top 10 lists Tool Poisoning as a named risk category. Tool
  descriptions and metadata must be scanned and snapshotted before exposure.
- Recent MCP security papers and reports focus on prompt injection, tool
  poisoning, descriptor mutation and STDIO/command execution risks. Matrix
  should keep external MCP disabled by default and prefer fixture/live-gated
  rollout.
- The 2025-11-25 MCP authorization spec and security best-practices text call
  out token caching/logging and token passthrough risk; Matrix therefore blocks
  passthrough unless a server config names an allowed credential scope.
- The 2026 OWASP MCP Top 10 and MCP-38 taxonomy both validate treating
  descriptors as untrusted semantic input. The first implementation slice
  snapshots descriptor hashes, scans prompt-injection/destructive/admin hints
  and requires reapproval on descriptor drift.
- 2026-04-29 implementation follow-up: denylist and resource policy are now
  separate from tool execution. Matrix can deny an MCP server, tool name,
  domain or resource URI before exposure, and resource fetches have their own
  scheme/domain/prefix gate. Confirm/destructive/admin tools fail closed when
  no approval channel is available.
- 2026-04-29 implementation follow-up: external tools now need user-visible
  provenance before entering the effective catalog. Tools that look like
  Matrix high-trust names such as memory writes, sandbox execution, scheduler
  mutations or destructive canvas/chart actions are blocked when served by
  untrusted MCP servers. Temporary grants are session-scoped, expiry-bound and
  require audit references, so approval shortcuts cannot silently become
  durable access.
- 2026-04-29 execution follow-up: MCP execution now has a bounded adapter that
  preserves `tool_call_id`, converts timeout/cancellation/remote exceptions to
  structured tool messages and caps output before agent-context entry. This is
  MCP-specific plumbing; the same output-compaction pressure for normal tools is
  tracked through Feature 016.
- 2026-04-29 fixture/health follow-up: health checks are deliberately separate
  from tool listing or tool invocation. Static config validation and explicit
  non-tool probe callbacks provide readiness evidence, while deterministic
  fixture descriptors exercise policy tests without reaching external MCP
  servers.
- 2026-04-29 Control UI follow-up: the MCP tab now consumes the effective
  catalog endpoint and displays approval level, risk flags, denial reasons,
  provenance/server label and visible/blocked state. This keeps Control aligned
  with policy-filtered state instead of raw descriptors.
- 2026-04-29 Meta-Harness follow-up: `mcp-catalog-policy` is a provider-free,
  external-server-free scenario lane covering benign fixture exposure, poisoned
  descriptor blocking and descriptor drift/reapproval. It gives Feature 024 a
  repeatable artifact before live external MCP promotion.
- 2026-04-29 audit/diff follow-up: Control catalog payloads now carry a
  `descriptor_diff` object for drift/reapproval rendering, and
  `/control/audit/mcp-policy` gives operators a focused query for catalog
  changes, descriptor drift, tool/resource denials and MCP session grants.
- 2026-04-29 Control UI second follow-up: the MCP tab now presents the policy
  posture before the raw table: effective visible/blocked counts, approval
  required count, descriptor drift count, secret-redaction status, per-tool
  last-seen timestamps and a recent focused audit rail. This aligns the UI with
  the gateway decision layer rather than making operators infer policy state
  from descriptor rows.
- 2026-04-29 widget handoff follow-up: Feature 030 consumes
  `evaluate_resource_fetch_policy()` before any MCP resource can become a
  Matrix widget/app proposal.
- 2026-04-29 snapshot storage follow-up: descriptor persistence is expressed as
  `McpDescriptorSnapshotStore` with in-memory and JSON adapters. This documents
  the transient-cache path while leaving the production DB table as a later
  adapter, not a policy rewrite.
- 2026-04-29 fixture execution follow-up: fixture descriptors now pass through
  the same effective-catalog policy and bounded `execute_mcp_tool_call()` path
  used for real MCP calls, proving catalog-to-gateway wiring without an
  external server.
- 2026-04-30 normal-tool discovery follow-up: `Z_Additional_For_Tool_Stuff.md`
  is broader than external MCP. The same progressive-disclosure pattern now
  exists for builtin tools: `search_tool_catalog()` uses regex/token extraction
  and BM25-style TF/IDF scoring over short policy-visible summaries. It returns
  names, groups, summaries, risk and approval metadata, not full schemas.
  `/control/tools/search` exposes the primitive for Control and future
  agent-facing discovery. MCP descriptor search now reuses the same pattern
  after effective-catalog filtering via `search_effective_catalog()` and
  `/control/mcp/catalog/agent/search`, returning provenance/risk/approval
  summaries without schemas.
- 2026-04-30 runtime transfer: `_prepare_system_prompt()` now consumes builtin
  tool search directly for the active `AgentExecutionContext.tools` and injects
  compact `Tool Discovery Hints`. This keeps the same metadata-only boundary
  while moving the benefit from Control into the real agent loop.
- 2026-05-01 runtime schema transfer: the Local-8B Meta-Harness memory floor
  proved that metadata-only hints are not enough when the provider tool payload
  still contains every full schema. The runtime now uses provider-agnostic
  deferred schema loading for builtin tools: select relevant schemas with the
  same regex/BM25 catalog search, always expose a normal `tool_search` fallback,
  and expand provider tool definitions after `tool_search` returns matches.
  This mirrors the Anthropic Tool Search pattern without binding Matrix to
  Anthropic SDKs; execution remains server-side through `ToolRegistry`,
  approval, policy and audit gates.

## Design Consequence

Feature 024 is a prerequisite for promoting external MCP beyond local dev:

```text
configured server -> descriptor snapshot -> risk policy -> filtered catalog
  -> approval gate -> bounded call -> audit/trace -> optional widget handoff
```

Feature 008 can keep local A2UI. Feature 030 can host Matrix widgets. Feature
024 decides which MCP tools and resources are allowed to enter those surfaces.

## 2026-04-30 Prompt Cache / Reload Transfer

Inputs: Hermes MCP reload/cache invalidation notes,
`Z_Additional_For_Tool_Stuff.md` and Feature 032.

MCP/tool reloads must be treated as prompt-cache and runtime-cache events:

- tool descriptor digest changes invalidate or rebind cached agent sessions.
- Control UI reload requires confirm/impact display when tool schemas,
  approval levels or descriptor hashes changed.
- agent-facing search sees only filtered metadata summaries, not raw descriptor
  instructions or secret-bearing schemas.
- runtime telemetry links MCP catalog digest/tool digest to each call or denial.

The same pattern applies to builtin tools so MCP is not a special policy island.

2026-05-01 implementation note: builtin `tool_search` is now a normal
`TradingTool`. Large active tool sets begin with a relevant schema subset plus
`tool_search`; LangGraph `_increment_iteration()` and SimpleLoop both expand
`tool_definitions` after a successful search result. This makes deferred
loading available to OpenAI-compatible, Anthropic-compatible and local
llama.cpp routes because it only changes the provider-neutral tool-definition
payload.

2026-05-01 live note: `run-local8b-floor-memory-explicit-001-deferred-tools-
slim-long` removed the scenario `allowed_tools` shortcut and relied on runtime
deferred schema selection. Bonsai 8B saw 4 provider tools for the memory turn,
called `memory_add` and `memory_search`, and passed trace, stream and
completion gates. This is the first proof that the builtin-tool path no longer
needs to stuff all schemas into the model context.

2026-05-01 Anthropic Tool Search check: Anthropic's current Tool Search docs
describe the same boundary we want provider-agnostically in Matrix: the model
initially sees the search tool plus non-deferred tools, deferred tool schemas
are kept out of the context window, search returns a small set of
`tool_reference` entries, and those references expand to full definitions only
when needed. The docs explicitly name regex and BM25 variants, 3-5 result
sets, searching over names/descriptions/argument metadata, and prompt-cache
preservation because deferred schemas do not mutate the system-prompt prefix.
The Claude Code MCP docs add the operational shape for MCP specifically:
MCP tool schemas are deferred by default, only names/summaries are cheap to
keep around, and server instructions should help the model know when to search.
Matrix should keep our implementation provider-neutral, but this validates the
runtime direction from `Z_Additional_For_Tool_Stuff.md`: a normal
policy-filtered `tool_search` primitive, short tool summaries for discovery,
and provider tool payload expansion only after a search match.

2026-05-01 live note: `run-local8b-floor-chart-deferred-tools-001` removed the
scenario `allowed_tools` shortcut for the chart/tool-stream floor and relied on
runtime deferred schema selection. Bonsai 8B saw 4 provider tools
(`get_chart_state`, `get_geomap_focus`, `set_chart_state`, `tool_search`),
called `get_chart_state`, and passed completion, trace, stream and tool
success gates at `1.0` with `fitness_score=0.8976`. This proves the deferred
schema path is not memory-specific and still preserves rich downstream tool
events.

2026-04-30 implementation note: Matrix now exposes MCP reload as a
confirmation-first control action rather than a model-visible tool. The reload
path computes a deterministic effective-catalog digest from descriptor hashes,
approval level, visibility and denial reasons; returns `agent-cache-impact/v1`;
and emits a Feature 033 runtime event. This transfers the Hermes MCP reload
lesson without copying CLI-specific behavior: the web/control surface owns the
reload and the agent runtime receives a rebind signal.

## Checked Sources

- Matrix root `Z_Additional_For_Tool_Stuff.md`.
- MCP Authorization spec 2025-11-25:
  `https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization`.
- MCP Security Best Practices:
  `https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices`.
- OWASP MCP Top 10:
  `https://owasp.org/www-project-mcp-top-10/`.
- OWASP MCP Tool Poisoning:
  `https://owasp.org/www-community/attacks/MCP_Tool_Poisoning`.
- MCP-38 threat taxonomy:
  `https://arxiv.org/abs/2603.18063`.
- FastMCP Apps overview:
  `https://gofastmcp.com/apps/overview`.
- Anthropic Tool Search API docs:
  `https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool`.
- Claude Code Agent SDK Tool Search docs:
  `https://code.claude.com/docs/en/agent-sdk/tool-search`.
- Anthropic Tool Reference docs:
  `https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference`.
