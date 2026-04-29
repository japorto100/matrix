---
title: MCP Gateway Tool Catalog Policy Gates
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
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
- [x] G011 Control and agent-facing catalog endpoints expose policy-filtered
  entries, not raw unfiltered descriptors.
