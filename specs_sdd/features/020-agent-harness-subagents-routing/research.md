---
title: Agent Harness Subagents Routing Research
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 020
---

# Research

## Initial Hypotheses

- HermesAgent is valuable for graphless loop and self-learning harness
  principles, but its CLI coding-agent product scope does not transfer
  directly to Matrix.
- Matrix should first harden routing, budgets and traceability before building
  real subagents.
- Subagents should likely be domain-specific delegates: research, geopolitical
  mapping, strategy critique, risk/source-quality review.

## HermesAgent v0.11 Update Notes

Reference version after update: `_ref/hermes-agent`
`v2026.4.23-600-g8ed599dc`.

Important upstream lessons to inspect and selectively transfer:

- Transport layer: Hermes extracted provider-specific formatting and HTTP
  behavior into `agent/transports/*`. Matrix should evaluate the same boundary
  for Feature 011 so provider quirks do not stay embedded in one agent loop.
- Subagent orchestration: Hermes has an explicit `orchestrator` role,
  configurable `max_spawn_depth` and sibling file coordination. Matrix should
  borrow the control model, not the coding-agent product behavior.
- Tool/plugin lifecycle: `pre_tool_call` veto, `dispatch_tool`,
  `transform_tool_result`, shell hooks and slash-command registration are good
  design references for ToolRegistry/HITL, but Matrix should gate them through
  audit and policy first.
- `/steer`: mid-run steering is useful for operator/HITL control, but must be
  audited and scenario-gated before Matrix adopts it.
- Compression hardening: reset retry counters after compression, break
  compression-exhaustion loops, protect multimodal tail scans and preserve
  language in summaries. These map directly to Feature 012/016 gates.
- Memory: Hindsight session-scoped retain metadata, memory tool dedupe and
  async/stale flush guards are relevant to Hindsight/MemPalace/Fusion.
- Provider safety: do not persist resolved secrets, block cross-provider
  reasoning leaks, and only send provider-supported fields. These map to
  Feature 011/013/016.
- TUI/observability: subagent spawn overlays are product-UI specific, but the
  underlying event model is useful for Control UI and Meta-Harness artifacts.

Non-transferable or deferred:

- Autonomous coding-agent product mode.
- Direct file-editing worker delegates as end-user feature.
- Dashboard/TUI implementation details except as observability inspiration.
- Gateway platform breadth that is unrelated to Matrix/Tuwunel.
- Plugin hooks that can mutate tool results or terminal output without a
  Matrix audit/policy layer.

## Sources To Read

- `_ref/hermes-agent`
- `_ref/meta-harness`
- Current Matrix `agent/runners/simple.py`
- Current Matrix `agent/runners/dispatcher.py`
- Current Matrix `agent/graph/**`
