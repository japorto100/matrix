---
title: Meta-Harness Agent Optimization Sources
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 016
---

# Sources

## Local Matrix Sources

| Source | Role |
|---|---|
| `python-backend/agent/app.py` | Python Agent service, `/api/v1/agent/chat`, `/mcp-traces`, LiteLLM-dependent runtime. |
| `python-backend/agent/graph/runner.py` | Main LangGraph execution path and memory/skills preprocessing. |
| `python-backend/agent/runners/dispatcher.py` | Variant dispatch and A/B experiment linkage. |
| `python-backend/agent/graph/nodes/llm_node.py` | LiteLLM call, tool definitions, LLM audit, token/cost metadata. |
| `python-backend/agent/graph/nodes/tool_node.py` | Real ToolRegistry execution, timeouts, sanitizer, `tool_call`/`tool_result` audit. |
| `python-backend/agent/graph/nodes/approval_node.py` | Consent decisions and audit behavior. |
| `python-backend/agent/tools/registry.py` | Canonical tool names and registered tool set. |
| `python-backend/agent/audit/logger.py` | Audit action taxonomy used by trace gates. |
| `python-backend/agent/audit/store.py` | JSONL/Postgres audit backends. |
| `python-backend/agent/mcp_traces.py` | Existing MCP trace/harness tools to extend or wrap. |
| `python-backend/meta_harness/*.py` | Current proposer/evaluator/scorer/pareto/config implementation. |
| `python-backend/memory_fusion/*` | Hindsight/MemPalace/Fusion memory runtime and operation logging. |
| `python-backend/agent/skills/*` | Skill loader/finder/refiner/evolver/audit/Pareto surfaces. |
| `data/harness/search_set/queries.json` | Historical single-turn search set; must be normalized or migrated. |
| `specs_sdd/features/014-observability-harness-evals/` | Observability/evaluator infrastructure dependency. |
| `specs_sdd/features/015-scheduler-skills-planning-automation/` | Skill and scheduler dependency. |

## Paper / Reference Sources

| Source | Adopted Idea |
|---|---|
| Meta-Harness, arXiv `2603.28052` | Outer loop searches over harness code; proposer reads source code, scores and raw traces through filesystem; search/holdout separation; Pareto frontier; full trace access beats score/summary-only feedback. |
| `_ref/meta-harness/README.md` | Official reference repo scope: reusable framework, onboarding flow, reference experiments and proposer wrapper requirement. |
| `_ref/meta-harness/ONBOARDING.md` | New-domain onboarding must produce `domain_spec.md` before implementation, with fixed harness interface, search/holdout split, metrics, budget, baselines, leakage controls, logs and artifacts. |
| `_ref/meta-harness/reference_examples/text_classification/.claude/skills/meta-harness/SKILL.md` | Proposer skill pattern: analyze prior summaries/frontier/logs, prototype mechanism-level candidates, write `pending_eval.json`; do not run benchmarks inside proposer. |
| `_ref/meta-harness/reference_examples/terminal_bench_2/.claude/skills/meta-harness-terminal-bench-2/SKILL.md` | Agent-scaffold evolution pattern: one falsifiable mechanism per candidate, anti-overfit rules, pending eval artifact. Used as reference only because Matrix is not a Terminal-Bench coding-agent product. |
| Meta-Harness TerminalBench-2 appendix | Causal reasoning over prior failures; safer additive changes after prompt/control-flow regressions; environment bootstrap as discovered improvement. |
| EvoSkill, arXiv `2603.02766` and local `_ref/EvoSkill` | Skill/prompt candidate loop, feedback history, frontier and benchmark-based skill promotion. |
| Karpathy Autoresearch local `_ref/autoresearch` | Fixed evaluator, fixed budget, keep/discard log, branch/rollback discipline and single editable artifact mindset. |
| Feedback Descent | Optional pairwise compare mode when scalar scores are noisy. |

## Source Preservation Rule

Feature 016 must keep paper and local artifact provenance attached to every
implementation task. If a behavior comes from Meta-Harness, EvoSkill or
Autoresearch, name the adopted mechanism and the local Matrix component it maps
to.

## Official Skill Compatibility

The official skills are not copied verbatim into Matrix runtime instructions:

- text-classification hardcodes exactly three memory-system candidates and a
  `MemorySystem` Python interface.
- Terminal-Bench hardcodes a coding-agent scaffold, `AgentHarness`, benchmark
  task assumptions and subagent workflow.

Matrix adopts their outer-loop discipline but uses
`.claude/skills/meta-harness-matrix/SKILL.md` for the actual proposer role.

## Local Hardening Notes

- Pareto uses feasibility gates before trade-offs: candidates must complete and
  pass deterministic trace gates before cost/token/latency trade-offs matter.
- Memory use is not a generic ranking bonus. Memory correctness is owned by
  trace expectations such as `expected_memory`, required memory routes and
  required providers.
- External proposer LLM calls are disabled by default; Codex is the active
  proposer unless a run explicitly opts into `META_HARNESS_ENABLE_EXTERNAL_LLM`.
