---
title: Agent Harness Subagents Routing Live Verify
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 020
---

# Live Verify

## LV-01 Runner Routing Smoke

Status: partial-static-live-smoke.

Expected:

- Postgres/audit store reachable for full live lane.
- Meta-Harness local lane can run routing mechanics without OpenRouter quota.
- Live OpenRouter lane can run at least one quality smoke.

Evidence:

- 2026-04-27: local `llm-mock` Meta-Harness run
  `run-route-decision-metadata-smoke` / `route-decision-metadata-simple`
  passed trace gates on `data/harness/runner_parity/scenarios.json`.
- Observed actions: `route_decision`, `llm_response`, `skill_found`.
- `route_decision` metadata showed `runner=simple`,
  `decision=direct_answer`, `delegation_decision=none`, `spawn_depth=0`,
  no memory/retrieval route requested.
- 2026-04-27: static policy-helper tests passed:
  `uv run pytest tests/agent/routing/test_delegation_policy.py tests/agent/test_llm_node_caching.py::test_llm_node_emits_route_decision_for_tool_use -q`.
  Route metadata now includes `route_taxonomy`, `delegate_kind`,
  `max_spawn_depth`, `allowed_tools`, `memory_scope`, `budget` and
  `fallback_reason=subagents_disabled`; this keeps future delegation visible
  without enabling subagents yet.
- Residual: session row write warned because local Postgres required a
  password; this does not invalidate the JSONL/Audit trace gate but full live
  lane still needs DB credential alignment.

## LV-02 Subagent Boundary Smoke

Status: planned.

Expected:

- When subagents are not implemented, scenarios requiring delegation fail or
  defer explicitly, not silently hallucinate a delegate.
