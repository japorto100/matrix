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
