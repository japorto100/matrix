---
title: Agent Harness Subagents Routing Research
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-30
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

## Matrix Transfer Map

Immediate transfer candidates:

- Feature 011: provider transport boundary so OpenRouter/LiteLLM, embeddings,
  rerankers and unsupported provider fields are not mixed into one agent loop.
- Feature 012: compression and memory flush hardening; stale async flushes and
  repeated memory writes must be trace-gated.
- Feature 013: pre-tool veto, hook policy and secret/redaction behavior before
  any plugin-like extension point is trusted.
- Feature 016: route/delegation decisions must be emitted as audit metadata
  before Matrix changes behavior.
- Feature 020: subagent control model with `max_spawn_depth=0` by default;
  first real promotion is flat, single-hop delegation only.

Deferred transfer candidates:

- Hermes-style coding subagents, file-editing workers and software-development
  skills. Matrix is a trading/geo/strategy agent, not a coding-agent product.
- TUI overlays except as event-model inspiration for Control UI.
- Unreviewed shell/output transformation hooks.

Open design pressure: route-decision telemetry should be implemented before
subagent behavior. Without it, Meta-Harness cannot tell whether a future answer
was improved by routing, retrieval, memory, model choice or accidental prompt
variance.

## 2026-04-29 Runtime Guard Slice

The fresh `Z_` docs and ADR-0009 reinforce a provider-agnostic boundary:
Matrix can learn from provider SDK examples, but runtime requests should be
shaped from capability data, not vendor-specific prompts or assumptions. The
implemented slice keeps unknown/custom LiteLLM models on the existing behavior
and only omits `tools` or `reasoning_effort` when LiteLLM-derived metadata
explicitly says the model does not support that field. This gives Feature 020
an unsupported-provider-field guard without forcing a full transport
abstraction through the agent runtime yet.

## 2026-04-30 Routing Contract Harness

The next useful hardening slice is provider-free and behavior-neutral:
`meta_harness routing-contract` evaluates route/delegation metadata and failure
gate behavior without invoking a model.

Findings:

- No-tool/no-subagent remains `direct_answer` with `delegation_decision=none`
  and `spawn_depth=0`.
- Retrieval should win before delegation. The contract explicitly checks
  `route_taxonomy=retrieval_answer` and keeps delegation disabled.
- Domain delegates can be represented without execution by
  `build_delegation_defer_metadata()`: `delegation_decision=deferred`,
  `delegate_kind=domain`, `fallback_reason=subagents_disabled`.
- Tool-budget exhaustion, provider retry loops and repeated failed tool calls
  are better expressed as trace gate failures before adding retry behavior.
- Reasoning/provider-specific fields and resolved secrets must be forbidden in
  trace metadata. This stays provider-agnostic: the gate checks metadata shape,
  not a vendor SDK name.

## Sources To Read

- `_ref/hermes-agent`
- `_ref/meta-harness`
- Current Matrix `agent/runners/simple.py`
- Current Matrix `agent/runners/dispatcher.py`
- Current Matrix `agent/graph/**`
