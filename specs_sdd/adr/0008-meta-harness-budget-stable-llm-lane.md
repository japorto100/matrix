---
title: ADR-0008 Meta-Harness Budget-Stable LLM Lane
status: accepted
owner: filip
created: 2026-04-27
updated: 2026-04-27
affects:
  - 016-meta-harness-agent-optimization
  - 012-memory-context-world-personal-kb
sources:
  - https://github.com/stanford-iris-lab/meta-harness
---

# ADR-0008 Meta-Harness Budget-Stable LLM Lane

## Decision

Matrix Meta-Harness must have a budget-stable LLM lane for repeated outer-loop
evaluation. Runner-parity, prompt/config plumbing and deterministic trace-gate
checks should prefer a local or mock LiteLLM-compatible model when the behavior
under test is the harness path itself.

OpenRouter/free models remain useful live-provider probes, but they must not be
the only route for hard Meta-Harness gates because they can fail for external
rate limits, model availability changes or missing account credits.

## Rules

- `AGENT_MAX_OUTPUT_TOKENS` is a run-level cap, not a globally low production
  default. Meta-Harness commands may set it inline and artifacts must record
  the effective value.
- Meta-Harness artifacts must distinguish harness failures from provider quota,
  rate-limit and credit failures.
- Free OpenRouter models may be used for cheap smoke tests, but passing local
  harness gates must not depend on free-tier availability.
- Paid OpenRouter/provider calls require explicit budget intent or a funded
  key; repeated proposer/evaluator loops should use local/mock lanes first.

## Consequences

- Feature 016 owns T097d: add and document a budget-stable Meta-Harness LLM
  lane for repeated autonomous optimization.
- Feature 012 memory scenarios may still run through real providers for live
  confidence, but static and local-lane gates should cover memory/tool wiring
  without exhausting provider quota.
- Live provider failures are still valuable Meta-Harness evidence, but they
  should become candidate diagnostics rather than blocking all harness work.
