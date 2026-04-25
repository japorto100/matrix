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
