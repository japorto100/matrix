---
title: MCP Gateway Tool Catalog Policy Tasks
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
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
- T006 Persist descriptor snapshots in a migration-owned table or documented
  transient cache decision.
- [x] T007 [done-static] Expose read-only catalog endpoint for Control UI.
- [x] T008 [done-static] Expose agent-facing catalog endpoint filtered by user/session policy.
  - 2026-04-29: `/control/mcp/catalog/agent` returns only visible catalog
    entries for a tenant/user/session and keeps secrets redacted.

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
- T025 Add server health probe without invoking model-visible tools.
- T026 Add deterministic local fixture server for tests.
- T027 Add configured-provider-backed live lane only after catalog policy is
  green.

## UI And Harness

- T030 Add Control UI MCP catalog table with server, tool, risk, approval and
  last-seen status.
- T031 Add Control UI descriptor diff view.
- T032 Add Meta-Harness scenario for benign external tool exposure.
- T033 Add Meta-Harness scenario for tool poisoning in descriptor text.
- T034 Add Meta-Harness scenario for changed descriptor after initial approval.
- T035 Add audit queries for catalog changes and call denials.
- T036 Link Matrix widget/resource output handoff to Feature 030.

## Verification

- [x] T040 Unit-test descriptor normalization and collision handling.
- [x] T041 Unit-test policy filtering by user/session/tenant.
- [x] T042 [done-static] Unit-test confirm-unavailable fail-closed behavior.
- [x] T043 Unit-test token passthrough redaction and denial.
- [x] T044 Unit-test descriptor diff risk escalation.
- T045 Integration-test fixture MCP server through gateway.
- T046 Live-verify Control UI reads the effective catalog.
- T047 Live-verify Meta-Harness blocks poisoned descriptors.
