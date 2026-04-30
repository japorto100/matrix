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

## 2026-04-30 Tool Hook Policy Transfer

Hermes' useful signal is the lifecycle boundary, not the plugin surface itself:
tools may need pre-call veto and output transformation hooks, but those hooks
must be policy-controlled and observable before they can affect agent behavior.

Matrix now implements the smallest provider-agnostic backend slice inside the
LangGraph tool runtime:

- missing `tool_hook_policy` preserves existing behavior.
- `pre_tool_veto`/`deny_tools` blocks a tool before validation/execution and
  writes a blocked runtime event with `hook=pre_tool_call`.
- `redact_result_keys` transforms configured dict fields before audit output,
  stream handoff and the next LLM turn, and writes
  `hook=transform_tool_result`.
- shell/output hooks are deliberately still absent; if Matrix later adds a
  terminal/shell execution surface, it must reuse the same explicit audit and
  runtime-event policy shape first.

Open design pressure: route-decision telemetry should be implemented before
subagent behavior. Without it, Meta-Harness cannot tell whether a future answer
was improved by routing, retrieval, memory, model choice or accidental prompt
variance.

## HermesAgent Fresh Pull 2026-04-30

Reference version after fast-forward: `_ref/hermes-agent` `fc7f55f49`.

Additional upstream signals after `v2026.4.23-600-g8ed599dc`:

- Curator became concrete: background skill maintenance tracks use/view/patch
  counters, pins skills, archives instead of deleting and writes per-run
  reports. This maps to Feature 015 and the Meta-Harness skill lifecycle
  domain, not to general agent routing.
- Skill-write hardening: pinned skills now block `skill_manage` writes. Matrix
  should treat pinned/user-authored skills as a hard write fence before any
  self-improvement loop can patch skills.
- Observability plugin: Langfuse is opt-in/fail-open and truncates fields. This
  is a useful pattern for Tool/Ops observability: observability must not alter
  runtime behavior or leak oversized tool payloads.
- Matrix adapter churn continued. This is directly important for Matrix, even
  though Hermes' gateway architecture is not copied. Relevant bug classes are
  echo/pairing loops, mention/thread/free-response room rules,
  reaction-based approval binding, E2EE bootstrap/cross-signing and
  reconnect/session hygiene. These become prioritized gates for our Matrix
  bridge/appservice/webclient path.
- Provider hardening continued around DeepSeek/Kimi/Anthropic thinking blocks
  and resolved secrets. Matrix should keep provider-specific reasoning traces
  out of route metadata, memory, RAG and KG evidence.
- Vercel sandbox, Google Meet plugin and dashboard/TUI work are reference-only
  unless a Matrix feature explicitly needs the same pattern. They are not
  agent harness requirements.

Boundary: Hermes is a CLI/gateway coding agent with broad platform adapters.
Matrix is a Matrix-native agent system with its own appservice, webclient,
memory/RAG/KG and Control surfaces. Transfer only the invariants and test
classes; do not transfer Hermes product behavior 1:1.

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

## 2026-04-30 Runtime Tool Retry Guard

Hermes' compression/retry hardening translates to Matrix as bounded runtime
guardrails, not as coding-agent-specific retry behavior.

Matrix now stops after repeated failures for the same tool before asking the
model to retry again. The guard is provider-agnostic and shared by the graphless
SimpleLoop and the LangGraph increment path:

- threshold: `AGENT_MAX_TOOL_FAILURES_PER_TOOL`, default `2`.
- signal: `tool_retry_guard_stopped` in degradation metadata.
- behavior: set `done=true`, keep the last tool evidence in messages/results
  and return a bounded final response rather than looping until max iterations.

This implements the max-tool-retry part of Feature 020. Compression retry
reset, stale async memory flush and deeper context-poisoning checks remain
Feature 012/016 follow-ups.

## 2026-04-30 A2A Child Policy Enforcement

Hermes' useful invariant is not the CLI-child implementation itself; it is that
children get a fresh scope, a restricted toolset and no direct shared-memory
write path. Matrix now enforces that invariant inside the runtime:

- A2A child requests are recognized only when the thread id is `a2a-*` and the
  context starts with the Matrix delegation prefix.
- The delegation fields become `AgentExecutionContext` and graph state policy:
  role, parent thread, spawn depth, isolated context mode, allowed tools and
  `memory_write_policy=parent_only`.
- The app filters actual tools to `allowed_tools` before the provider sees tool
  definitions.
- `memory_retain_node` blocks parent-only child runs before looking up or
  writing the durable Memory engine, and emits a memory runtime event instead.

This keeps user-provided chat context non-authoritative while making the
Matrix-owned A2A context operational rather than placebo prompt text.

2026-04-30 memory flush guard update: the stale async flush part is now a
runner-level guard rather than a provider change. LangGraph and SimpleLoop both
schedule automatic post-answer memory retain through a per-thread generation
counter. `_safe_sync_turn` then serializes writes for that thread and skips old
generations if a newer turn already scheduled persistence. Compression retry
reset and context-poisoning gates remain separate follow-ups.

2026-04-30 context-poisoning update: the first static guard is now in
compression itself. LLM summaries are reinserted as untrusted historical
context blocks, not as bare user instructions, and prompt-injection-like text
inside the summary is flagged. This does not replace future compression
quality gates, but it removes the most obvious poisoning failure mode.

2026-04-30 context-overflow retry update: the error classifier already mapped
context overflow to `RecoveryStrategy.compress`, but the main runners did not
act on it. LangGraph and SimpleLoop now do one bounded recovery attempt:
compress current messages, reset iteration state for the compressed prompt,
emit `llm.context_overflow_compress_retry`, then retry once. If the retry
fails, normal ErrorPacket classification still surfaces the provider failure.
This is the Matrix interpretation of Hermes' compression retry reset: recover
from a too-large prompt without entering a provider retry loop.

2026-04-30 LLM failure event update: provider/runtime errors were previously
visible to spans and runner ErrorPackets but not always replayable through the
audit/runtime-event lane. `llm_node` now writes a failed `llm.call.failed`
runtime event before re-raising, using the shared error classifier for
provider-neutral `reason`, `recovery`, `retryable` and status-code metadata.
The provider-free routing contract gates this shape through
`routing-llm-failure-runtime-event-shape`; raw prompts, messages, API keys and
authorization material remain forbidden.

## 2026-04-30 Runtime Tool Discovery Slice

The earlier progressive-disclosure work lived mostly in Control/catalog
surfaces. That was useful for inspection but did not directly improve agent
runtime routing. Matrix now applies the same metadata-only search primitive in
`_prepare_system_prompt()`:

- source: current `AgentExecutionContext.tools`, not a global unfiltered list.
- search: `agent.tools.catalog.search_tool_catalog()` over summaries,
  group/risk/approval and policy reasons.
- exposure: name, group, risk, approval and summary only; no input schemas or
  hidden descriptors are added to the prompt.
- behavior: provider tool-calling payload remains unchanged, so this is a
  routing hint rather than a tool-execution contract change.

This maps the Hermes lesson to Matrix more accurately: the loop gets better
local tool awareness without copying CLI-agent tool behavior or exposing
dangerous/high-disclosure tools prematurely.

## 2026-04-30 Default-Off Single-Hop Delegation Slice

The Hermes pattern transfers best as policy-first delegation, not as a CLI
subagent clone. Matrix now has a provider-agnostic child policy envelope and a
gated A2A node path:

- `max_spawn_depth=0` remains default-off/fail-closed.
- single-hop enablement is explicit through `AGENT_A2A_MAX_SPAWN_DEPTH`.
- child context is isolated and explicit-context-only by default.
- child tools filter recursive delegation, direct memory writes,
  cross-platform sends, scheduling and code/sandbox execution.
- child approval behavior is non-interactive auto-deny, matching the Hermes
  lesson that worker agents must not block on parent/UI stdin.
- Feature 033 runtime events expose accepted, started, completed, failed and
  timeout/stale states without raw child output in metadata.
- A2A lifecycle events are persisted into audit metadata so Ops can rebuild
  subagent run rows from replay, not only from transient graph output.
- completed child output is handed back to the parent for memory curation as a
  digest-backed `subagent.parent_memory_handoff` event; the child cannot write
  shared memory directly.
- node-level child-send timeout uses `AGENT_A2A_DELEGATION_TIMEOUT_SECONDS` so
  a blocking/faulty A2A client becomes a stale delegation event with audit
  metadata and the child client is still closed.

This is still not production-promoted subagent behavior. It is the minimum
runtime contract that allows Meta-Harness to evaluate single-hop delegation
without hidden memory/KG pollution or unbounded child tool access.

2026-04-30 Ops correlation update: Feature 020 keeps the handoff as a parent
memory event, because making it a child lifecycle event would blur the memory
write boundary. Feature 029 now joins that handoff back into the subagent run
read model by `child_task_id`, so operators can see result digest, retain
decision and `child_memory_write_allowed=false` while the runtime still blocks
direct child writes.

2026-04-30 forged child policy update: treating the A2A context string as
Matrix-owned is not sufficient by itself, because the HTTP endpoint can still
receive a request that imitates the prefix. The app now re-applies
`build_child_tool_policy()` after parsing inbound child context, so serialized
`allowed_tools` is only a request, not authority. Forbidden memory, recursive
delegation and send tools are stripped before the child runner sees the tool
registry, and the provider-free routing contract verifies that shape.

2026-04-30 retrieval child-tool update: the policy allowlist previously named
`retrieve_context`, but the real ToolRegistry did not implement it. That made
retrieval-capable child agents a paper contract rather than executable runtime
surface. `retrieve_context` is now a read-only provider-agnostic tool over the
Feature 019 retrieval API. It emits RAG/KG/artifact runtime events and compact
downstream file metadata, while durable memory writes remain blocked and
parent-curated.

2026-04-30 durable A2A delegation update: the Control A2A surface already had
an `agent.a2a_delegations` table and read API, but runtime delegation only
produced transient tasks plus audit runtime events. Matrix now persists
accepted single-hop A2A runs into that table when a DB DSN is configured. The
delegation id is generated before the child request and reused as child task
id/thread id, so audit runtime events, parent memory handoff and Control rows
can correlate without parsing child output. Persistence is intentionally
fail-open for local/dev/no-DB runs; Meta-Harness still evaluates the audit
runtime events, while Control gains durable history when Postgres is present.

## Sources To Read

- `_ref/hermes-agent`
- `_ref/meta-harness`
- Current Matrix `agent/runners/simple.py`
- Current Matrix `agent/runners/dispatcher.py`
- Current Matrix `agent/graph/**`
