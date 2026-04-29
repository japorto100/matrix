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
- T002 Define `McpServerConfig` with transport, command/url, env, scopes,
  tenant allowlist, user allowlist and enabled flag.
- T003 Define `McpToolDescriptorSnapshot` with source server, descriptor hash,
  first_seen, last_seen, security schemes and risk flags.
- T004 Normalize MCP descriptors into Matrix tool names without collisions.
- T005 Add descriptor diff detection for changed name, description, schema,
  output template, auth and destructive hints.
- T006 Persist descriptor snapshots in a migration-owned table or documented
  transient cache decision.
- T007 Expose read-only catalog endpoint for Control UI.
- T008 Expose agent-facing catalog endpoint filtered by user/session policy.

## Policy And Consent

- T010 Map MCP tools to Matrix approval levels: auto, confirm, destructive,
  admin and blocked.
- T011 Fail closed when a confirm/destructive tool is requested without an
  available approval channel.
- T012 Block token passthrough unless server config explicitly permits a named
  credential scope.
- T013 Redact descriptor/env/secrets in traces and Meta-Harness artifacts.
- T014 Add tool-description prompt-injection scan before exposure.
- T015 Add lookalike/collision checks for high-trust tools.
- T016 Require user-visible provenance for external tools.
- T017 Add per-session temporary grants with expiry and audit refs.
- T018 Add denylist support for server, tool name, domain and resource URI.

## Execution

- T020 Add gateway wrapper around MCP calls with timeout, cancellation and
  output-size caps.
- T021 Convert MCP failures into structured tool messages compatible with the
  agent runners.
- T022 Preserve tool_call_id across approvals, denials and execution errors.
- T023 Add resource fetch policy separate from tool execution policy.
- T024 Add metadata-only mode for catalog review without tool execution.
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

- T040 Unit-test descriptor normalization and collision handling.
- T041 Unit-test policy filtering by user/session/tenant.
- T042 Unit-test confirm-unavailable fail-closed behavior.
- T043 Unit-test token passthrough redaction and denial.
- T044 Unit-test descriptor diff risk escalation.
- T045 Integration-test fixture MCP server through gateway.
- T046 Live-verify Control UI reads the effective catalog.
- T047 Live-verify Meta-Harness blocks poisoned descriptors.
