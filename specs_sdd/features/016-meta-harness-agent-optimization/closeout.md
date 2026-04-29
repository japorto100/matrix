---
title: Meta-Harness Agent Optimization Closeout
status: open
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 016
---

# Closeout

Feature 016 has its first implementation slice. It is not implementation-closed.

## Current Decision

Use a Python-only first implementation:

- PostgreSQL + LiteLLM + Python Agent.
- no frontend required.
- no Go Gateway required.
- CLI and MCP surfaces for the implemented runner.

## Implemented Slice

- `meta_harness.scenario_runner` defines multi-turn scenarios, trace
  expectations, deterministic trace gates, in-process Python Agent execution,
  explicit runner variants (`dispatcher`, `langgraph`, `simple`), live service
  execution via `/api/v1/agent/chat` and artifact writing.
- `meta_harness.evaluator.evaluate_single` now runs with the real ToolRegistry
  and attaches legacy-query trace-gate verdicts through the same runner-variant
  plumbing.
- `meta_harness.meta_cli` exposes scenario JSON runs, including `--agent-url`
  for live-service execution and `--runner-variant` for in-process parity runs.
- `agent.mcp_traces.harness_run_scenarios` exposes the same scenario runner as a
  Trace MCP tool.
- `meta_harness.proposer` now receives recent Meta-Harness candidate artifact
  history: run metadata, scenario sets, scores, verdicts, source snapshots and
  compact raw-trace previews with paths to full files.
- `meta_harness.evaluator` now separates `search` and protected `holdout`
  splits; holdout execution requires explicit `allow_holdout=True`.
- `meta_harness.decisions` records keep/discard/defer decisions to global,
  run-local and candidate-local JSON artifacts, and the proposer reads recent
  decisions.
- `meta_harness/` is now a top-level Python package; `agent/` no longer owns the
  outer-loop optimizer modules.
- `data/harness/search_set/queries.json` now uses registered Matrix tool names
  in `expected_tools`; old placeholder names remain as
  `historical_expected_tools`.
- `data/harness/holdout_set/queries.json` defines a small protected regression
  seed set.
- `data/harness/runner_parity/scenarios.json` defines a minimal no-tool smoke
  for comparing dispatcher/LangGraph/SimpleLoop without sandbox dependency.
- Graphless SimpleLoop now accepts dict-shaped tool calls when appending tool
  messages between turns.
- Trace gates fail by default on failed observed tool results unless a scenario
  explicitly opts into `allow_tool_failures`.
- Live service smoke evidence exists for `run-7e71055b00bb`: Python Agent
  `:8094`, Postgres `:5433` and LiteLLM `:4000` produced SSE, audit traces,
  score/verdict artifacts and a `defer` candidate decision.
- Unit coverage exists for trace gates, legacy query mapping, artifact writing,
  fake scenario runs, service-runner selection, MCP exposure, proposer artifact
  indexing and evaluator ToolRegistry usage.

## Known Gaps

- current legacy evaluator remains single-turn, though scenario runner supports
  multi-turn and legacy evaluator now adds trace gates.
- proposer artifact access is bounded to recent candidate summaries and trace
  previews; deep file inspection is still done by Codex/filesystem tools.
- tool/memory correctness exists as deterministic trace gates, but is not yet a
  promotion gate.
- holdout execution exists, but automatic baseline-vs-candidate regression
  comparison is not yet implemented.
- sandbox live verify is deferred until local Podman storage has enough space
  for the OpenSandbox code-interpreter image or a local runtime image is built.

## Closeout Required Evidence

- one Python-only run artifact.
- one tool-gated scenario.
- one memory-gated scenario.
- one proposer iteration using artifact history.
- one keep/discard candidate decision.
- documented stack command and environment.
