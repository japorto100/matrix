---
title: MCP Gateway Tool Catalog Policy Live Verify
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 024
---

# Live Verify

- LV001 Start dev stack with external MCP disabled and verify no external tools
  are agent-visible.
- LV002 Enable the deterministic fixture MCP server and verify catalog
  discovery.
- LV003 Open Control UI MCP tab and verify descriptor provenance and risk
  status render.
- LV003a Verify Control UI MCP summary cards match the effective catalog:
  visible/blocked count, approval-required count, descriptor drift count,
  secret-redaction state and per-tool last-seen timestamp.
- LV004 Ask the agent to use an auto-approved fixture tool and verify the tool
  call succeeds with a preserved tool_call_id.
- LV005 Ask the agent to use a confirm-level fixture tool without approval UI
  and verify fail-closed denial.
- LV006 Approve the same confirm-level tool through HITL and verify exactly one
  execution.
- LV007 Change the fixture descriptor after approval and verify risk
  escalation.
- LV008 Add a poisoned descriptor instruction and verify the tool is blocked
  before model exposure.
- LV009 Configure a blocked credential scope and verify token passthrough is
  redacted/denied.
- LV010 Return oversized tool output and verify truncation plus audit event.
- LV011 Return widget/resource metadata and verify it is routed to Feature 030
  policy instead of direct execution.
- LV012 Run Meta-Harness `mcp-catalog-policy` scenario and verify allowed,
  denied and poisoned cases are artifacted.
- LV013 Verify audit search shows discovery, denial, approval and execution
  events.
- LV013a Verify the MCP tab focused audit rail shows recent
  `/control/audit/mcp-policy` events and success/denial status.
- LV014 Verify shutdown/restart preserves or intentionally rebuilds descriptor
  snapshots according to the chosen persistence decision.

## 2026-04-30 Added Live Gates

- LV030 Reload MCP/tool catalog and verify changed descriptor/tool digests are
  visible before confirmation.
- LV031 Verify cached agent sessions are invalidated or rebound after reload.
- LV032 Verify agent-facing catalog search returns only filtered summaries,
  risk/provenance/approval metadata and no raw schemas/secrets.
- LV033 Verify runtime telemetry links MCP catalog digest/tool digest to each
  call or denial.
