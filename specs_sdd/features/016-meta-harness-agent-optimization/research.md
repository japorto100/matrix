---
title: Meta-Harness Agent Optimization Research
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 016
---

# Research Notes

## Meta-Harness Paper Mapping

The paper's central claim is that harness engineering should be optimized as an
outer loop over executable code, not as a prompt-only tweak. The proposer is a
coding agent that reads a filesystem containing prior candidate source code,
scores and execution traces, then proposes new harnesses.

Matrix mapping:

- harness code: agent prompts, context assembly, memory policy, tool policy,
  routing, consent and runner behavior.
- execution traces: audit events, spans, SSE transcripts and session rows.
- scores: existing composite scorer plus scenario-specific trace gates.
- filesystem history: `data/meta_harness/runs/...`.
- proposer: Codex or LiteLLM-backed proposer, with bounded write scope.
- search set: scenario fixtures.
- test set: holdout fixtures hidden from proposer during search.

Important implication: the current proposer path is useful but insufficient
because it compresses traces into short summaries. Feature 016 needs raw,
queryable artifacts.

## Official Repo / Domain-Spec Correction

The official Stanford repo reinforces a stricter structure than the early
Matrix implementation used:

- every optimization target needs a domain-spec style contract: fixed task
  definition, fixed harness interface, fixed evaluator, search set, holdout
  set, allowed edit scope, budget and logging rules.
- the proposer may inspect traces and candidate history, but it must not
  change the evaluator during the same run.
- the proposer does not self-certify. Promotion requires a separate outer-loop
  evaluation against frozen gates.
- one candidate should be a falsifiable harness change, config overlay or
  bounded patch with a clear expected metric movement.

Matrix implication after the 001-023 review: Feature 016 should first optimize
source-grounding units that already have deterministic evidence paths
(ingestion, retrieval, KG boundary, memory route correctness) before broad
"make the agent better" loops. Full-stack UI behavior remains a live-verify
surface, not the first Meta-Harness optimization domain.

## Why Simulated User Matters

The paper evaluates harnesses by running task instances. For Matrix, task
instances are not just one prompt; they are user sessions that intentionally
exercise:

- memory creation, recall and correction.
- tool selection and refusal.
- consent handling.
- sandbox/file/browser analysis.
- scheduler setup without production delivery.
- skill retrieval/refinement.
- A2UI emission.

Therefore the Meta-Harness runner must play the user, not only post-process
organic logs. Organic logs are valuable later, but bootstrapping requires
designed scenarios.

## Tool Findings

The real tool set lives in `ToolRegistry.load()` and includes memory, canvas,
sandbox, A2UI and scheduler tools. The current `data/harness/search_set` expects
`market_data_fetch` and `chart_analysis`, which are not registered tools. Those
entries are historical intent and need migration to actual tool expectations or
to rubric-only tasks.

The current evaluator constructs `AgentExecutionContext(..., tools=())`, while
`llm_node` and `tool_node` independently load ToolRegistry. This ambiguity must
be removed for eval correctness. A scenario should be able to say whether tools
are enabled, restricted or expected.

2026-04-29 follow-up from `Z_Additional_For_Tool_Stuff.md`: the Z_ recommendation
is not MCP-only. It applies to normal `ToolRegistry` tools too: builtin memory,
sandbox, browser/file analysis, scheduler, canvas/A2UI and market tools need a
catalog, tool groups, progressive disclosure, risk/approval metadata and output
compaction gates. Feature 024 remains the MCP-specific external descriptor
owner; Feature 016 owns harness/eval pressure for normal tools.

2026-04-29 implementation follow-up: Meta-Harness trace gates now understand
normal tool catalog metadata through `allowed_tool_groups` and
`max_tool_disclosure_level`. This lets scenario files assert that a risky normal
tool such as sandbox execution was not exposed or used unless the scenario's
tool-group contract explicitly allows it.

## Memory Findings

Memory is both automatic and explicit:

- automatic prefetch in `_prepare_system_prompt` through MemoryManager or
  fallback Hindsight.
- explicit `memory_search` and `memory_add` tools.
- working memory `save_memory` and `load_memory`.
- memory_fusion operation logging can emit `memory_recall` and `memory_retain`
  audit actions when operation context is propagated.

Scenarios should test all three categories: automatic recall, explicit memory
tool calls and working-memory scratchpad.

## EvoSkill Mapping

EvoSkill should not replace Meta-Harness. It is the skill-specific evolution
layer:

- failure cluster -> skill or prompt proposal.
- generator writes skill/prompt changes.
- evaluator scores the variant.
- frontier keeps the best variants.
- feedback history helps avoid repeating failed ideas.

Matrix already has a simple SkillEvolver, finder, refiner, trigger-quality and
skill Pareto helper. Missing before real EvoSkill-style automation:

- benchmark/search set per skill class.
- candidate skill versioning and rollback.
- promotion gate based on repeated success.
- edit-existing vs create-new decision.
- root-cause feedback history.

## Autoresearch Mapping

Autoresearch contributes process discipline, not direct runtime code:

- fixed evaluator.
- fixed budget.
- one run log.
- keep/discard/crash status.
- rollback on regression.
- do not change evaluator during the loop.

For Matrix this means scenario fixtures and judges are frozen during a run.
Harness candidates may change; the scoring harness may not.

## Early Implementation Slice

Recommended first slice:

1. Define scenario schema.
2. Implement Python-only runner over 3 scenarios: simple no-tool, memory
   remember/recall, one harmless tool.

## 2026-04-29 Provider Lane Hardening

The fresh `Z_` docs pushed the harness work toward provider-agnostic live
verification instead of an OpenRouter-only lane. The implemented slice follows
ADR-0009: keep `llm-mock` as a deterministic contract lane, add
`provider-smoke` for configured-provider metadata and optional chat completion,
and write provider capability snapshots into Meta-Harness run artifacts. This
keeps Meta-Harness useful for static/non-browser gates before browser live
verification starts.
3. Write artifact directory.
4. Add deterministic trace gates.
5. Add CLI JSON output.
6. Then extend proposer to read artifact directories.

## 2026-04-26 Live Outer-Loop Findings

The first real service-mode Meta-Harness rounds produced implementation fixes,
not only documentation:

- Live trace gates must require `tool_call` or `tool_result`; a
  `consent_request` alone cannot satisfy a required-tool gate.
- Meta-Harness session consent must be granted inside the running agent service,
  not only inside the harness process. The live service now accepts an explicit
  Meta-Harness-only consent header and records session consent before graph
  execution.
- LangGraph must not compile with unconditional `interrupt_before` on
  `approval_gate`; otherwise service-mode tool calls stop before execution and
  no normal resume path exists.
- The sandbox SDK import has drifted: the installed
  `opensandbox-code-interpreter` exposes `code_interpreter`, while older code
  imported `opensandbox_code_interpreter`. The sandbox manager now supports both
  module names.
- Pareto ranking must treat completion and trace gates as hard feasibility
  gates. Failed zero-token candidates otherwise appear Pareto-optimal because
  they look cheap.

Current live evidence:

- `run-8ba52ec0f56e` exercised chart, portfolio, memory and sandbox scenarios
  through the real FastAPI service with OpenRouter/LiteLLM.
- Chart, portfolio and explicit memory scenarios passed trace gates with real
  `tool_call` and `tool_result` audit events.
- Sandbox consent worked and `sandbox_execute` was called, but the tool result
  failed because the local OpenSandbox code image/runtime is not available.
- The sandbox infra blocker is machine state, not agent planner behavior:
  OpenSandbox `:8080` starts, but `/` has about 4 GB free and pulling
  `opensandbox/code-interpreter:v1.0.2` failed with `no space left on device`.

## 2026-04-27 Feature Review Consequence

The 001-023 checkpoint split the remaining work into two categories:

- live verification debt: Matrix UI, ElementX/Tuwunel, Control UI tabs and
  Agent Chat surfaces need real user-flow evidence.
- implementation/research debt: Python Agent, memory, RAG, KG, ingestion,
  optimization loops and subagent routing still have concrete code/spec work.

Meta-Harness should therefore operate on stable backend domains first:

1. parser/chunk/retrieval benchmark candidates from Features 021/019/022/023.
2. memory lifecycle and Hindsight/MemPalace/Fusion route correctness from
   Feature 012.
3. route/tool/provider/compression behavior from Features 011/013/016/020.

It should not be used to claim UI completion unless the trace contains the
actual frontend/API path being verified.

## 2026-04-29 Feature 024-030 Domains

The Z_ pass adds new Meta-Harness domains:

- Feature 024: MCP catalog policy and tool-poisoning resistance from
  `Z_Additional_For_Tool_Stuff.md`.
- Feature 025: semantic metric/claim correctness from
  `Z_Semantik_layer and so on.md`.
- Feature 027: report artifact grounding from
  `Z_Tool_very interessting Quarkdown.md`.
- Feature 028: visual memory provenance from
  `Z_Chatgpt_Chronicles vs DeepseekOCRpaper.md`.
- Feature 029: ops-room replay and status compression from
  `Z_Hermes_Desktop_claw3d.md`.
- Feature 030: Matrix widget proposal/fallback behavior from
  `Z_matrix_widgets_formulars_and so on.md`.

All scenarios must remain provider-agnostic. The harness can call whatever
configured provider is available, but the gates judge behavior, traces and
artifacts, not vendor-specific response style.
