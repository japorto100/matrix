---
title: Matrix Widget App Host Gates
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 030
---

# Gates

- G001 Widgets are never executed from arbitrary message bodies.
- G002 Agent-created room-state widget events require approval.
- G003 Unsafe URL schemes remain passive text.
- G004 Hosted apps use allowlisted origins/resources.
- G005 Unsupported clients receive stable markdown/link fallback.
- G006 Room power levels are checked before widget state mutation.
- G007 Widget lifecycle supports revoke/expire.
- G008 MCP/App resources pass Feature 024 policy before hosting.
- G009 Audit events exist for proposal, approval, update and revoke.
- G010 Live compatibility matrix is updated for Element Web, Element X and
  FluffyChat.
