---
title: Real Meta-Harness Outer Loop Gates
status: planned
owner: filip
created: 2026-05-01
updated: 2026-05-01
feature_id: 034
---

# Gates

- [x] G001 A run must distinguish support lanes from real Meta-Harness iteration.
  Contract-suite-only runs cannot be reported as full Meta-Harness application.
- [x] G002 Every candidate has source/config snapshot, scores, verdicts and raw
  traces or typed benchmark evidence.
- [x] G003 Proposer packets exclude holdout results and holdout trace previews.
- [partial-static] G004 Evaluator, goldens and holdout files are immutable during one run.
- [x] G005 Candidate write scope is explicit before evaluation.
- [x] G006 Candidate notes cannot mark promotion; only frozen evaluator artifacts,
  safety gates and explicit holdout evidence can.
- [x] G007 Search-set score, trace-gate pass rate and cost/latency are written
  before a keep/discard/defer decision.
- [x] G008 Pareto frontier records dominated and non-dominated candidates.
- [x] G009 Inner-loop candidates from Feature 023 are visible as candidates, but
  cannot promote themselves without the Feature 034 outer-loop decision.
- [x] G010 A completed run summary states whether the proposer inspected raw prior
  artifacts and lists the artifact classes inspected.
- [x] G011 Provider calls are budgeted and optional; provider-free iterations remain
  valid when the search set uses deterministic gates only.
- [ ] G012 Holdout execution requires an explicit guard and produces separate
  promotion evidence.
- [x] G013 Live no-browser `run`/`outer-loop` commands must preflight the trace
  DB endpoint and record the result as an artifact before evaluation.
- [x] G014 Scenario scalar fitness must include deterministic expectation
  failures, not only generic session health.
- [partial-live-no-browser] G015 A provider-agnostic Local-8B floor suite must
  exist for direct routing, skills, memory, tools, RAG/KG, semantic lookup and
  subagent policy. Static parsing and provider smoke are complete; the full
  seven-scenario live run is the next no-browser execution gate.

2026-05-01 static gate evidence: `meta_harness.real_outer_loop` implements the
no-browser iteration path and tests assert proposal/pending-eval/decision/
proposer-interaction artifacts plus `true_meta_harness_iteration=true`. G004 is
partial because current code hashes frozen files before/after but does not yet
block arbitrary external git diffs. G012 remains open for the explicit Feature
034 holdout execution command.

2026-05-01 live no-browser gate evidence:
`run-metaharness-round-1-fixed` passed G001-G003 and G005-G011 with real
backend execution. Baseline and candidate both had raw traces/SSE/scores/
verdicts/source snapshots, holdout stayed hidden, the candidate had explicit
write scope and pending eval, trace/cost/latency metrics were written before
decision, and the candidate was discarded as dominated. G004 remains partial
for arbitrary code-patch candidates; G012 remains open.

2026-05-01 bounded runtime candidate gate evidence:
`run-metaharness-round-2-recent-memory-fixed` passed trace and stream gates
after the recent-memory fallback. The visible transcript now contains the exact
searched phrase immediately after `memory_add`. This uncovered a remaining gate
gap: answer-level exact-recall quality needs a first-class metric because the
aggregate fitness did not distinguish the improved transcript from the prior
passing trace.

2026-05-01 runtime preflight gate evidence: `meta_harness.runtime_preflight`
unit tests cover no-DB warning, local `:55433` auto-start, unknown unreachable
DB fail-fast and `ensure_runtime_preflight` raising on failures. The real
outer-loop summary now embeds `runtime_preflight`, and each run gets
`runtime_preflight.json`.

2026-05-01 Local-8B floor evidence: `data/harness/local_8b_floor/scenarios.json`
defines the no-browser target-model floor across the Agent Harness boundary.
`tests/meta_harness/test_scenario_runner.py` parses the suite and asserts the
expected surfaces are represented. Direct `llama-server` provider smoke with
`bonsai-8b` passed as `llamacpp`, and
`run-local8b-floor-bonsai-direct-long-timeout` passed the direct routing floor
through the real backend Agent Harness with trace/stream pass rate `1.0`.
The remaining six scenarios are still live no-browser gates because they will
deliberately reveal which skills/tools/memory/retrieval paths an 8B target can
operate through.

2026-05-01 formal Local-8B outer-loop evidence:
`run-metaharness-round-local8b-001` is a true Feature 034 iteration:
`true_meta_harness_iteration=true`, frozen evaluator gate passed with no
changed evaluator/scenario paths, holdout stayed hidden, the proposer
inspection read 24 raw artifact files, and a config-overlay candidate was
evaluated then discarded by the decision ledger. Baseline:
`completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
`stream_gate_pass_rate=1.0`, `fitness_score=0.9995`. Candidate:
`completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
`stream_gate_pass_rate=1.0`, `fitness_score=0.9994`.

2026-05-01 expectation-fitness gate evidence: Scenario runs now keep
`base_fitness_score` and lower `fitness_score` when trace or stream gates fail.
This closes the Round-2 exact-recall scoring gap where trace presence could
look healthy even when the visible answer missed required evidence.

2026-05-01 Local-8B skill-injection gate evidence:
`run-local8b-floor-skill-risk-001-isolated` failed before the LLM call with
`CredentialPool exhausted` for isolated synthetic user
`mh-local8b-skill-risk-001` and provider `llamacpp`. The fix keeps the normal
production user-credential path untouched and extends only the Meta-Harness
env credential resolver for local OpenAI-compatible providers. After the fix,
`run-local8b-floor-skill-risk-001-isolated-fixed` passed:
`completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
`stream_gate_pass_rate=1.0`, `fitness_score=0.9992`, provider `llamacpp`,
model `bonsai-8b`, prompt tokens `1663`, completion tokens `58`, and
duration about `98.6s`. The run used isolated user state and selected
`risk-assessment` via the real skill finder.

2026-05-01 Local-8B memory/tool-scope gate evidence:
`run-local8b-floor-memory-explicit-001` failed before useful memory behavior
because the eager ToolRegistry path loaded the full tool grammar into a 4k
llama.cpp context, producing about 7.8k prompt tokens and no
`memory_add`/`memory_search` call. The short-term harness fix adds scenario
`allowed_tools` and filters the runtime registry for targeted floor slices.
After filtering to `memory_add` and `memory_search`,
`run-local8b-floor-memory-explicit-001-tools-filtered` passed
`completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
`stream_gate_pass_rate=1.0`, `tool_success_rate=1.0`, and
`fitness_score=0.8473`. This closes the immediate no-browser gate for the
memory floor while leaving the real product gate open: provider-agnostic
deferred tool discovery / Tool Search must replace static allowlists for
normal runtime turns and MCP tools.

2026-05-01 deferred schema live gate evidence:
`run-local8b-floor-memory-explicit-001-deferred-tools-slim-long` removed the
scenario `allowed_tools` shortcut and used `AGENT_DEFER_TOOL_SCHEMAS=true`.
The provider telemetry reported `tool_count=4` with `memory_add`,
`memory_search`, `save_memory` and `tool_search`, rather than the full builtin
registry. The run passed `completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
`stream_gate_pass_rate=1.0`, `tool_success_rate=1.0` and
`fitness_score=0.8465`.

2026-05-01 deferred chart/schema live gate evidence:
`run-local8b-floor-chart-deferred-tools-001` removed the scenario
`allowed_tools` shortcut for the chart/tool-stream floor and used
`AGENT_DEFER_TOOL_SCHEMAS=true`. Provider telemetry reported `tool_count=4`
with `get_chart_state`, `get_geomap_focus`, `set_chart_state` and
`tool_search`, rather than the full builtin registry. The run passed
`completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
`stream_gate_pass_rate=1.0`, `tool_success_rate=1.0` and
`fitness_score=0.8976`. The stream gate observed `tool-input-start`,
`tool-output-available` and the rich renderer for `get_chart_state`, so this
also covers downstream no-browser Agent Chat event shape for tool rendering.

2026-05-01 deferred retrieval/memory-boundary live gate evidence:
`run-local8b-floor-retrieval-deferred-tools-001` was a valid red Meta-Harness
finding: deferred schemas selected `retrieve_context`, but the trace failed
because automatic personal-memory recall/retain still ran for a prompt that
explicitly said not to store personal memory. After the bounded runtime fix,
`run-local8b-floor-retrieval-deferred-tools-001-skill-clean` passed with
provider `tool_count=2` (`retrieve_context`, `tool_search`),
`memory_recalls=0`, `memory_retains=0`, no observed memory routes/providers,
`completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
`stream_gate_pass_rate=1.0`, `tool_success_rate=1.0` and
`fitness_score=0.8978`. The stream exposed `rag-kg-sources.json`, proving the
RAG downstream artifact path stayed visible while personal memory remained
blocked.

2026-05-01 deferred semantic/memory-boundary live gate evidence:
`run-local8b-floor-semantic-deferred-tools-001` showed the same class of
boundary issue for semantic grounding: `semantic_lookup` executed, but memory
tools and automatic Memory-Fusion recall/retain were still present. After the
bounded runtime fix, `run-local8b-floor-semantic-deferred-tools-001-clean`
passed with provider `tool_count=2` (`semantic_lookup`, `tool_search`),
`memory_recalls=0`, `memory_retains=0`, no observed memory routes/providers,
`completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
`stream_gate_pass_rate=1.0`, `tool_success_rate=1.0` and
`fitness_score=0.8982`.

2026-05-01 subagent-policy/memory-boundary live gate evidence:
`run-local8b-floor-subagent-policy-001` passed the route/delegation headline
gate, but found a real boundary issue: the prompt was a non-personal harness
policy question, yet `memory-usage` was selected and Memory-Fusion
recall/retain wrote the exchange. After the bounded runtime fix,
`run-local8b-floor-subagent-policy-001-clean` passed with provider
`tool_count=0`, `delegation_decision=none`, `spawn_depth=0`,
`memory_recalls=0`, `memory_retains=0`, no observed memory routes/providers,
only `global:plan` selected, `completion_rate=1.0`,
`trace_gate_pass_rate=1.0`, `stream_gate_pass_rate=1.0` and
`fitness_score=0.9995`.

2026-05-01 no-allowlist eval/tool-control memory-boundary evidence:
a stricter Local-8B floor run with scenario `allowed_tools` removed exposed two
more real side effects. Direct marker turns and chart tool-control turns were
formally passing their visible response/tool gates while still causing
automatic Memory-Fusion recall/retain. After the bounded memory policy fix,
focused unit tests cover recall and retain for both cue classes, and
`run-local8b-floor-chart-no-allowlist-001-clean` passed with provider
`tool_count=4`, `get_chart_state` executed, downstream tool stream events
observed, `memory_recalls=0`, `memory_retains=0`,
`trace_gate_pass_rate=1.0`, `stream_gate_pass_rate=1.0`,
`tool_success_rate=1.0` and `fitness_score=0.8976`. The partial full-suite
artifacts remain diagnostic only; promotion evidence is the targeted clean
rerun.
