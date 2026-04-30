---
title: Agent Harness Subagents Routing Spec
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 020
---

# Spec

Matrix needs explicit routing and delegation semantics before adding
subagents. The current baseline has three runner shapes:

- `dispatcher`: production app-selected runner.
- `langgraph`: explicit graph with memory, router, LLM, approval, tools and
  memory retain.
- `simple`: graphless loop for lower-overhead CLI-style behavior.

Subagents, when introduced, must be audited domain delegates. They should not
be used for routine retrieval, ordinary tool calls or hidden self-improvement.

## HermesAgent Reference Boundary

`_ref/hermes-agent` is pinned as an upstream reference and was updated to
`v2026.4.23-600-g8ed599dc` on 2026-04-27. Its v0.11 "Interface" release is
high-signal for harness architecture: pluggable provider transports, explicit
subagent orchestration, max spawn depth, sibling coordination, plugin tool
hooks, shell hooks, steering, context-compression hardening, memory metadata
and provider/credential safety.

This is a CLI coding-agent architecture, not Matrix's product target. Matrix
must not import the coding-agent product behavior wholesale. Transfer the
mechanisms, not the scope:

- use transport separation to simplify model/provider routing.
- use explicit delegation metadata before real subagents.
- use max-depth and sibling-coordination ideas for future bounded delegates.
- use pre-tool/transform hooks as ToolRegistry/HITL design input, but only
  behind explicit per-turn policy and runtime/audit events.
- use compression/reasoning-leak/secret-persistence fixes as safety gates.
- do not expose autonomous coding agents as a user-facing product mode in this
  phase.
- do not let subagents silently write memory, promote KG claims or schedule
  tasks.
- do not add shell/output hooks without an explicit policy surface and
  runtime-event/audit proof.

## Required Metadata

Every routed turn should eventually expose:

- runner variant.
- route decision.
- reason for route.
- tools allowed.
- memory mode.
- budget caps.
- delegation decision if any.
- fallback/degradation reason.

## Promotion Rule

No subagent behavior is production-promoted until Meta-Harness has search and
holdout gates proving it improves task success without increasing unsafe tool
use, memory pollution, token cost or loop failures.
