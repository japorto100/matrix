---
title: MCP Gateway Tool Catalog Policy
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 024
---

# MCP Gateway Tool Catalog Policy

## Current State / Ist

Matrix already has internal tool registry, approval/HITL logic, MCP notes in
Feature 008, Control UI tabs in Feature 010, security gates in Feature 013 and
Meta-Harness tool scenarios in Feature 016. What is missing is one authoritative
runtime boundary for external MCP servers, MCP Apps-style widgets and tool
catalog publication.

Without that boundary, every client or feature can accidentally decide its own
tool allowlist, metadata trust level, token forwarding, widget rendering policy
and audit shape.

## Target State / Soll

Feature 024 owns the MCP gateway and catalog policy:

- discover configured MCP servers without auto-trusting them;
- normalize tool descriptors into Matrix `ToolRegistry` shape;
- score descriptor risk before exposing tools to agents;
- enforce tenant/user/session allowlists and approval classes;
- redact or block token passthrough by default;
- separate tool execution from widget/resource rendering;
- expose catalog state to Control UI and Meta-Harness;
- emit audit events for descriptor changes, calls, denials and resource loads.

MCP Apps and WebMCP are treated as integration surfaces, not as implicit trust
boundaries. A widget can be useful UI, but its HTML/resource capability must be
policy-gated independently from the tool call that produced it.

## Boundaries

- Feature 008 owns local A2UI/generative UI packet rendering.
- Feature 010 owns Control UI display of tool state.
- Feature 013 owns sandbox, consent and security enforcement primitives.
- Feature 014 owns trace/eval observability.
- Feature 016 owns Meta-Harness scenarios and promotion evidence.
- Feature 030 owns Matrix chat widget/app host behavior.

Feature 024 owns the gateway/catalog decision layer shared by those features.

## Closeout Criteria

- MCP server config is explicit and disabled-by-default for external endpoints.
- Tool descriptor ingestion records provenance, version and risk flags.
- Agent-visible catalog is filtered by user/session policy.
- Confirm/destructive tools fail closed when approval UI is unavailable.
- Widget/resource metadata is never rendered as executable UI without a
  separate host policy.
- Control UI and Meta-Harness can inspect the effective catalog and denials.
