---
title: Agent Harness Subagents Routing Live Verify
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-30
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

## LV-01b Provider-Free Routing Contract

Status: static-live-smoke pass on 2026-04-30.

Evidence:

- Command:
  `cd python-backend && uv run python -m meta_harness.meta_cli routing-contract --run-id run-routing-contract-20260430 --data-dir /tmp/matrix-meta-harness-routing-contract`
- Result: `passed=true`, `scenario_count=7`, `passed_count=7`.
- Covered scenarios: no-tool/no-subagent, retrieval-over-delegation, domain
  delegate deferred, tool-budget exhaustion failure, provider retry-loop
  failure, repeated failed tool-call failure and forbidden provider/secret
  metadata failure.

## LV-02 Subagent Boundary Smoke

Status: planned.

Expected:

- When subagents are not implemented, scenarios requiring delegation fail or
  defer explicitly, not silently hallucinate a delegate.

Evidence:

- 2026-04-30 static prep: `routing-domain-delegate-deferred` records
  `delegation_decision=deferred`, `delegate_kind=domain`,
  `fallback_reason=subagents_disabled` and `spawn_depth=0`.

## LV-03 SimpleLoop Approval Parity

Status: static pass plus Meta-Harness local parity pass on 2026-04-29.

Evidence:

- SimpleLoop now calls `approval_node` before `tool_node` with
  `approval_interrupts=false`.
- Confirm-level tools deny with a structured tool message if the runner cannot
  pause/resume human approval.
- Existing approved tool paths still execute and avoid duplicate tool messages.

Checks:

- `cd python-backend && uv run pytest tests/agent/graph/nodes/test_approval_node.py tests/agent/runners/test_simple.py -q`
  => `12 passed`.
- `cd python-backend && uv run ruff check agent/graph/nodes/approval_node.py agent/runners/simple.py agent/graph/state.py agent/graph/runner.py tests/agent/graph/nodes/test_approval_node.py tests/agent/runners/test_simple.py`
  => pass.
- `./scripts/dev-stack.sh --llm-mock` => `llm-mock :8095`.
- Meta-Harness parity run
  `run-simple-approval-parity-jsonl-20260429` with variants
  `simple,langgraph` => `parity_passed=true`,
  `all_variants_trace_passed=true`, `mismatches={}`.
- Artifact dirs:
  `data/meta_harness/runs/run-simple-approval-parity-jsonl-20260429/candidates/simple-approval-jsonl-simple/`
  and
  `data/meta_harness/runs/run-simple-approval-parity-jsonl-20260429/candidates/simple-approval-jsonl-langgraph/`.
