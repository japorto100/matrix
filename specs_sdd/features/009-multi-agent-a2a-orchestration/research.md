---
title: Multi-Agent A2A Orchestration Research
status: draft
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 009
---

# Research

## SOTA Multi-Agent Follow-Up 2026-04-30

Cross-checked against current Anthropic agents guidance, LangGraph
supervisor/swarm patterns, OpenAI Agents handoffs, Google ADK multi-agent
patterns and the fresh `_ref/hermes-agent` pull.

Reusable for Matrix:

- prefer explicit role/delegation contracts over ad-hoc prompt-only
  subagents.
- delegation should start with fresh bounded context and explicit tool access,
  not inherited unlimited state.
- handoff/delegation events need traceable parent/child IDs and result
  contracts.
- concurrency, depth and cancellation/interrupt propagation need hard defaults.
- subagents should not clarify directly to the user unless the orchestrator
  explicitly grants that channel.

Hermes-specific signals to adapt, not copy:

- leaf-agent restrictions, orchestrator depth opt-in, concurrency default and
  interrupt propagation are useful agent-harness rules.
- Hermes is CLI-first, so terminal/TUI assumptions are reference-only.
- Matrix group-room routing from Hermes is relevant as transport gating, but
  actual Matrix event handling remains Feature 006/030 territory.

Related fresh local inputs:

- `Z_Additional_For_Tool_Stuff.md` for tool/MCP boundary questions.
- Feature 020 research for provider-agnostic agent-harness routing decisions.
- Feature 016 domain contract: Meta-Harness validates subagent candidates only
  after real runtime contracts exist.
