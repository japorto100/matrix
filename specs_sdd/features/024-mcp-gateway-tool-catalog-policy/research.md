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

## Design Consequence

Feature 024 is a prerequisite for promoting external MCP beyond local dev:

```text
configured server -> descriptor snapshot -> risk policy -> filtered catalog
  -> approval gate -> bounded call -> audit/trace -> optional widget handoff
```

Feature 008 can keep local A2UI. Feature 030 can host Matrix widgets. Feature
024 decides which MCP tools and resources are allowed to enter those surfaces.

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
