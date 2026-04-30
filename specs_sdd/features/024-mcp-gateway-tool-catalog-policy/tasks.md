---
title: MCP Gateway Tool Catalog Policy Tasks
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-30
feature_id: 024
---

# Tasks

## Discovery And Registry

- T001 Inventory current Python `ToolRegistry`, tool nodes, approval node and
  MCP server stubs.
- [x] T002 [done-static] Define `McpServerConfig` with transport, command/url, env, scopes,
  tenant allowlist, user allowlist and enabled flag.
  - 2026-04-29: config also carries denylisted server ids, tool names, domains
    and resource URI prefixes.
- [x] T003 [done-static] Define `McpToolDescriptorSnapshot` with source server, descriptor hash,
  first_seen, last_seen, security schemes and risk flags.
- [x] T004 [done-static] Normalize MCP descriptors into Matrix tool names without collisions.
- [x] T005 [done-static] Add descriptor diff detection for changed name, description, schema,
  output template, auth and destructive hints.
- [x] T006 [done-static] Persist descriptor snapshots in a migration-owned table or documented
  transient cache decision.
  - 2026-04-29: `agent.mcp_gateway.storage` defines a migration-neutral
    snapshot-store protocol plus in-memory and JSON-file adapters. Production
    can later bind the protocol to a migration-owned table without changing
    policy/diff call sites.
- [x] T007 [done-static] Expose read-only catalog endpoint for Control UI.
- [x] T008 [done-static] Expose agent-facing catalog endpoint filtered by user/session policy.
  - 2026-04-29: `/control/mcp/catalog/agent` returns only visible catalog
    entries for a tenant/user/session and keeps secrets redacted.
- [x] T009 [done-static] Add normal builtin tool search / progressive disclosure
  primitive from `Z_Additional_For_Tool_Stuff.md`.
  - 2026-04-30: `agent.tools.catalog.search_tool_catalog()` searches
    policy-visible builtin tool summaries without exposing full input schemas,
    and `/control/tools/search` exposes it for Control/agent-facing follow-up.
- [x] T009a [done-static] Add MCP effective-catalog search with the same
  regex/token + BM25-style progressive disclosure, but only after policy
  filtering.
  - 2026-04-30: `search_effective_catalog()` searches visible
    `McpCatalogEntry` summaries and `/control/mcp/catalog/agent/search`
    returns provenance/risk/approval summaries without exposing schemas.

## Policy And Consent

- [x] T010 [done-static] Map MCP tools to Matrix approval levels: auto, confirm, destructive,
  admin and blocked.
- [x] T011 [done-static] Fail closed when a confirm/destructive tool is requested without an
  available approval channel.
  - 2026-04-29: `evaluate_tool_invocation_policy()` permits auto tools,
    blocks disabled/blocked descriptors, fails closed when approval channels
    are unavailable and requires explicit approval for confirm/destructive/admin
    tools.
- [x] T012 [done-static] Block token passthrough unless server config explicitly permits a named
  credential scope.
- [x] T013 [done-static] Redact descriptor/env/secrets in traces and Meta-Harness artifacts.
- [x] T014 [done-static] Add tool-description prompt-injection scan before exposure.
- [x] T015 [done-static] Add lookalike/collision checks for high-trust tools.
  - 2026-04-29: external tools whose names normalize/compact to protected
    high-trust tool names are blocked before exposure.
- [x] T016 [done-static] Require user-visible provenance for external tools.
  - 2026-04-29: external catalog entries require a display name plus a visible
    source URL/command; catalog entries include provenance for UI/approval
    surfaces.
- [x] T017 [done-static] Add per-session temporary grants with expiry and audit refs.
  - 2026-04-29: `McpSessionGrant` validates session, tool, approval level,
    expiry and audit ref before allowing a non-auto invocation without another
    approval interruption.
- [x] T018 [done-static] Add denylist support for server, tool name, domain and resource URI.
  - 2026-04-29: effective catalog filtering now emits
    `server-denylisted`, `tool-denylisted`, `domain-denylisted` and
    `resource-uri-denylisted` denial reasons.

## Execution

- [x] T020 [done-static] Add gateway wrapper around MCP calls with timeout, cancellation and
  output-size caps.
  - 2026-04-29: `execute_mcp_tool_call()` applies bounded timeout,
    structured cancellation conversion and max-output-byte capping before tool
    content enters the agent context.
- [x] T021 [done-static] Convert MCP failures into structured tool messages compatible with the
  agent runners.
  - 2026-04-29: timeout, cancellation and remote exceptions serialize as
    provider-compatible `role=tool` messages with JSON error payloads.
- [x] T022 [done-static] Preserve tool_call_id across approvals, denials and execution errors.
  - 2026-04-29: `McpToolCallRequest`, `McpGatewayExecutionResult` and
    `to_tool_message()` preserve `tool_call_id` and `tool_use_id` across
    success, timeout, cancellation and exception paths.
- [x] T023 [done-static] Add resource fetch policy separate from tool execution policy.
  - 2026-04-29: `evaluate_resource_fetch_policy()` evaluates resource URI,
    scheme, domain and resource-prefix denylist independently from tool
    invocation.
- [x] T024 [done-static] Add metadata-only mode for catalog review without tool execution.
- [x] T025 [done-static] Add server health probe without invoking model-visible tools.
  - 2026-04-29: `probe_mcp_server_health()` validates disabled/static config
    and optional explicit probe callbacks while recording
    `model_visible_tools_invoked=false`.
- [x] T026 [done-static] Add deterministic local fixture server for tests.
  - 2026-04-29: `fixture_mcp_server_config()` and
    `fixture_mcp_descriptors()` provide stable local policy/health fixtures
    without external MCP network dependency.
- T027 Add configured-provider-backed live lane only after catalog policy is
  green.

## UI And Harness

- [x] T030 [done-static] Add Control UI MCP catalog table with server, tool, risk, approval and
  last-seen status.
  - 2026-04-29: `McpTab` reads `/api/control/mcp/catalog` and displays
    matrix tool name, provenance/server label, approval level, risk flags,
    denial reasons and visible/blocked state.
- [x] T031 [done-static] Add Control UI descriptor diff view.
  - 2026-04-29: Control catalog payloads include `descriptor_diff`; `McpTab`
    renders hash, drift/no-drift, changed fields and reapproval state.
- [x] T032 [done-static] Add Meta-Harness scenario for benign external tool exposure.
  - 2026-04-29: `mcp-catalog-policy` artifacts include
    `mcp-benign-fixture-visible`.
- [x] T033 [done-static] Add Meta-Harness scenario for tool poisoning in descriptor text.
  - 2026-04-29: `mcp-catalog-policy` artifacts include
    `mcp-poisoned-descriptor-blocked`.
- [x] T034 [done-static] Add Meta-Harness scenario for changed descriptor after initial approval.
  - 2026-04-29: `mcp-catalog-policy` artifacts include
    `mcp-descriptor-drift-reapproval`.
- [x] T035 [done-static] Add audit queries for catalog changes and call denials.
  - 2026-04-29: `/control/audit/mcp-policy` filters MCP catalog changes,
    descriptor drift, tool denials, resource denials and session grants.
- [x] T036 [done-static] Link Matrix widget/resource output handoff to Feature 030.
  - 2026-04-29: Feature 030 `agent.matrix_widgets.policy` calls Feature 024
    resource policy for MCP resource handoff before widget hosting.
- [x] T037 [done-static] Add Control UI MCP policy summary and focused audit
  rail.
  - 2026-04-29: `McpTab` now shows effective visible/blocked counts, approval
    required count, descriptor drift count, secret-redaction status, per-tool
    last-seen timestamp and recent `/control/audit/mcp-policy` events.

## Verification

- [x] T040 Unit-test descriptor normalization and collision handling.
- [x] T041 Unit-test policy filtering by user/session/tenant.
- [x] T042 [done-static] Unit-test confirm-unavailable fail-closed behavior.
- [x] T043 Unit-test token passthrough redaction and denial.
- [x] T044 Unit-test descriptor diff risk escalation.
- [x] T045 [done-static] Integration-test fixture MCP server through gateway.
  - 2026-04-29: `test_fixture_mcp_catalog_tool_executes_through_gateway`
    builds the fixture catalog, selects a visible descriptor and executes it
    through `execute_mcp_tool_call()` with preserved `tool_call_id`.
- [x] T045a [done-static] Typecheck Control UI MCP summary/audit rendering.
- [x] T045b [done-static] Unit-test builtin tool search excludes hidden
  high-disclosure tools and returns only short summaries.
- [x] T045c [done-static] Unit-test MCP effective-catalog search excludes
  blocked descriptors and returns only summary/provenance metadata.
- T046 Live-verify Control UI reads the effective catalog.
- [x] T047 [done-static-live-smoke] Live-verify Meta-Harness blocks poisoned descriptors.
  - 2026-04-29: provider-free CLI smoke `mcp-catalog-policy` writes artifacts
    for allowed, poisoned and drift scenarios; no external MCP server required.
  - 2026-04-29 live-smoke: `run-mcp-catalog-policy-20260429` passed 3/3
    scenarios in `/tmp/matrix-meta-harness-mcp-policy`.

## 2026-04-30 Prompt Cache / Reload Additions

- T048 Add MCP reload confirmation metadata with prompt-cache invalidation
  impact.
- T049 Invalidate or rebind cached agent sessions after MCP descriptor/tool
  catalog changes.
- T050 Emit Feature 032 cache-impact and Feature 033 runtime events for MCP
  reload, descriptor diff and policy denial.
- T051 Keep progressive search metadata-only until policy allows full schema
  exposure.
