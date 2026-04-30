---
title: LLM Routing Research
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 011
migrated_from:
  - specs/execution/exec-a2fm-adaptive-routing.md
  - docs/superpowers/findings/2026-04-23-a2fm-paper-research-phase2.md
---

# Research

## A2FM Interpretation

A2FM is an agent-harness architecture: a trained foundation model emits a mode
classification token and then follows instant, reasoning or agentic schemas. It
is not a drop-in router for matrix because matrix is provider-agnostic through
LiteLLM and does not control Claude/OpenAI/Gemini weights.

## Liftable Ideas

### L1 Post-Hoc Mode Labeling

Label existing audit sessions:

- `agentic`: tool call present.
- `reasoning`: no tool call, multi-step/long reasoning response.
- `instant`: no tool call, single-turn short response.

Output mode distribution plus cost/latency/fitness. Gate any further router work
on actual distribution.

### L2 Adaptive Reward Feedback

Use A2FM's adaptive reward idea as offline evaluation, not online RL:

- penalize cheap-routed turns that trigger immediate user retries or low
  fitness.
- aggregate per user/week.
- tune thresholds such as max simple chars/words and keyword lists.

### L3 Small Encoder Classifier

Only if L1/L2 data shows value and audit corpus is large enough. A small CPU
classifier can replace the heuristic inside `router_node`, but it must respect
the first-turn-only invariant.

### L4 Full Training

Deferred until GPU infra, >100k sessions and a strategic move toward
self-hosted model weights. Not current engineering scope.

## External Router References

Keep as research/backlog until needed:

- RouteLLM / FrugalGPT style cascades.
- OpenRouter `/auto` for provider-side routing where acceptable.
- LiteLLM cost/latency routing for failover and cheapest-capable model
  selection, not task complexity.
- Cursor/OpenAI auto-select as product references, not implementation specs.

## SDD Decision

The next useful implementation is L1 mode labeling, not a classifier. Real
matrix usage data should decide whether routing complexity is worth it.

## 2026-04-29 Provider-Agnostic Follow-Up

The new Feature 024/026/027/030 work uses vendor examples only as evidence of
emerging patterns. Feature 011 must keep the gateway model/provider layer
agnostic:

- no provider-named prompts in core agent logic;
- capability metadata is explicit data;
- deterministic mocks stay in tests, not live verification;
- remote live verify uses whichever configured provider is available.

## 2026-04-29 Implementation Note

ADR-0009 records the first code slice from the fresh `Z_` docs and link review:
keep the shared LiteLLM client stable, add a provider-agnostic capability
snapshot, and make the Meta-Harness `provider-smoke` gate fail closed for mock
providers unless explicitly allowed. This implements the non-browser part of
Feature 011 T074/T076 while leaving the full live smoke matrix T075 open until
the configured remote provider and embedding provider are exercised.

## 2026-04-30 Provider Telemetry Transfer

Inputs: OpenClaude cache-stat logging/config, Hermes dashboard model settings,
Feature 032 and `Z_Additional_For_Tool_Stuff.md`.

The gateway needs a provider-agnostic request accounting layer:

- normalize prompt, completion, reasoning, cache-read and cache-write token
  counters when a provider supplies them.
- preserve unknown counters instead of inventing values when providers omit
  cache/reasoning usage.
- record provider/model/router/credential source and prompt-layout digest
  without storing raw prompt text by default.
- expose main, routing, summarizer, curator, embedding and evaluator model
  roles as explicit settings, not OpenAI/Anthropic-specific fields.
- warn when tool/MCP/skill reloads or prompt-layout changes break prompt-cache
  locality for active sessions.

This is deliberately not a vendor cache implementation. It is telemetry and
routing context that works for OpenRouter/LiteLLM-compatible, local and future
provider adapters.
