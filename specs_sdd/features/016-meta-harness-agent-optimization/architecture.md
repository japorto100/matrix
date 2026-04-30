---
title: Meta-Harness Agent Optimization Architecture
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 016
---

# Architecture

## Runtime Shape

```text
Scenario Set
  -> Meta-Harness CLI
  -> Simulated User Runner
  -> Python Agent Runtime
      -> LiteLLM Gateway
      -> ToolRegistry
      -> Consent Gate
      -> MemoryManager / memory_fusion
      -> Audit + Spans + Sessions
  -> Trace Gate Evaluator
  -> Score/Judge
  -> Candidate Artifact Directory
  -> Proposer
  -> Candidate Config/Patch
  -> Search/Holdout Eval
  -> Promotion Gate
```

## Agent Harness Boundary

Feature 016 treats the agent harness as the production model wrapper, not as a
single Python package. The harness includes runners, prompt/context assembly,
tool registry and consent policy, memory fusion, RAG/KG grounding, skill
selection, delegation routing, provider/model routing, prompt-cache telemetry,
runtime events, audit/SSE replay and Matrix session/gateway semantics that
affect agent behavior.

`meta_harness/` is outside that runtime boundary. It owns scenarios, trace
gates, scoring, candidate artifacts, Pareto/frontier state and promotion
discipline. It can test and improve the agent harness, but it is not the
agent-under-test.

## Python-Only Execution Path

The first implementation should avoid frontend and Go by calling the Python
Agent directly:

- service mode: POST `/api/v1/agent/chat` and consume SSE.
- in-process mode: construct `AgentExecutionContext` and call
  `run_agent_loop_with_variant` or `run_agent_loop`.

The in-process path is faster for eval loops, but service mode proves the
actual API behavior. Both should share the same scenario schema and scoring.

## Candidate Artifact Layout

Meta-Harness paper behavior depends on full-history, filesystem-queryable
experience. Candidate artifacts should therefore be written as directories:

```text
data/meta_harness/runs/<run_id>/
  run.json
  stack.json
  scenario_set.json
  candidates/
    c000_baseline/
      config.json
      source_snapshot.json
      scores.json
      verdicts.json
      traces/
        <scenario_id>/<thread_id>.json
      sse/
        <scenario_id>.jsonl
      notes.md
    c001_<slug>/
      proposal.json
      patch.diff
      config.json
      scores.json
      verdicts.json
      traces/
```

The proposer should be able to use normal file tools (`rg`, `fd`, `bat`, `jq`)
over these artifacts instead of receiving one giant prompt.

## Scenario Schema

Scenarios need more structure than the current single-turn `queries.json`:

```json
{
  "id": "memory_preference_recall_001",
  "category": "memory",
  "turns": [
    {"user": "Remember that I prefer max 1% risk per trade."},
    {"user": "What risk size should you use for my next trade plan?"}
  ],
  "expected_trace": {
    "required_actions": ["memory_retain", "memory_recall"],
    "required_tools": [],
    "forbidden_tools": ["schedule_task"],
    "required_skills": ["memory-usage"]
  },
  "judge": {
    "type": "rubric",
    "success_criteria": ["mentions 1% max risk", "does not invent preferences"]
  }
}
```

## Trace Gates

Trace gates are deterministic checks over audit/spans before any LLM judge runs:

- required action present: `memory_recall`, `memory_retain`, `tool_call`,
  `tool_result`, `consent_decision`, `skill_found`, `skill_used`.
- required tool used.
- forbidden tool not used.
- tool success rate above threshold.
- memory query route/provider present when scenario expects memory.
- safety decision present for risky tools.
- no unexpected mutation tool in read-only advisory scenarios.

## Tool Policy

Tools are first-class evaluation targets. Feature 016 must cover:

- Memory tools: `memory_search`, `memory_add`, `save_memory`, `load_memory`.
- Sandbox tools: `sandbox_execute`, `sandbox_browser`, `file_analyze`.
- A2UI tool: `render_a2ui_surface`.
- Scheduler tools: `schedule_task`, `schedule_list`, pause/resume/cancel/edit,
  runs and run-now.
- Trading/control tools currently registered: chart state, portfolio summary and
  geomap focus.
- Dynamic browser tools passed by Agent Chat requests.

The old search-set tool expectations must be normalized to the actual
ToolRegistry or marked as historical placeholders.

## Memory Policy

Memory is not a bonus metric; it is a core harness dimension.

- automatic prefetch should fire for recall-oriented queries.
- explicit memory tools should be available when the task asks the agent to
  remember, search or correct a fact.
- retain should be traceable after memory-writing turns.
- memory failures must be fail-soft but visible in trace gates.
- Hindsight, MemPalace and Fusion routes should be distinguishable in metadata.
- Hindsight should be evaluated as the summary/fact/preference layer.
- MemPalace should be evaluated as the verbatim/episodic evidence layer.
- Fusion should be evaluated as the production mix, where summary recall and
  verbatim evidence can both contribute to the answer.
- Conflict scenarios should verify that a fresh MemPalace-backed source can
  prevent stale Hindsight summaries from leaking into the final answer.
- Context lifecycle must preserve memory before data loss:
  - `pre_save` archives visible context without mutating the prompt.
  - `compaction` archives visible context before mechanical truncation.
  - `emergency`/compression archives old messages before LLM summarization.
- Context thresholds come from the model/provider context window resolved by
  the Python agent metadata path; hard-coded token windows are only test
  fixtures.
- Session deletion is not memory deletion. A session kill may flush via
  `on_session_end`, but Hindsight/Fusion banks should persist until an
  explicit memory-forget/delete flow targets them.

Memory fixture design should keep three scenario classes side by side:

```text
memory_hindsight_*  -> summary/fact/preference recall and correction
memory_mempalace_*  -> verbatim/episodic/loci recall and query sanitation
memory_fusion_*     -> mixed evidence, conflict handling, route metadata
```

Each memory scenario should persist a fixture manifest next to the run artifacts
with the eval `user_id`, memory provider mode, bank id, palace path, seed turns
and expected recall/forbidden-stale terms. That makes a failed harness run
replayable without relying on hidden DB state.

## Promotion Policy

A candidate can be promoted only if:

- search-set score improves or moves the Pareto frontier.
- holdout does not regress beyond configured tolerance.
- required trace gates pass.
- safety gates pass.
- tool and memory behavior match scenario expectations.
- cost/latency stays within budget or the tradeoff is explicitly accepted.
