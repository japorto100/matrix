---
title: MCP Gateway Tool Catalog Policy Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 024
---

# Research

## Local Z Reference

Derived from `Z_Additional_For_Tool_Stuff.md`. The core recommendation is
"Gateway + Tool-Katalog + Policy + Code-Execution-Schicht" instead of stuffing
many MCP tools directly into the model prompt.

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

## Design Consequence

Feature 024 is a prerequisite for promoting external MCP beyond local dev:

```text
configured server -> descriptor snapshot -> risk policy -> filtered catalog
  -> approval gate -> bounded call -> audit/trace -> optional widget handoff
```

Feature 008 can keep local A2UI. Feature 030 can host Matrix widgets. Feature
024 decides which MCP tools and resources are allowed to enter those surfaces.
