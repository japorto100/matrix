---
title: Real Meta-Harness Outer Loop Research
status: draft
owner: filip
created: 2026-05-01
updated: 2026-05-01
feature_id: 034
---

# Research

## Local References

- `docs/Meta-Harness-2603.28052v1.md`: local copy of the paper.
- `_ref/meta-harness/README.md`: official repo structure and reference
  experiments.
- `_ref/meta-harness/ONBOARDING.md`: domain-spec onboarding requirements.
- `_ref/meta-harness/reference_examples/text_classification/meta_harness.py`:
  compact reference outer loop.
- `_ref/meta-harness/reference_examples/text_classification/inner_loop.py`:
  trace-rich inner-loop example.
- `_ref/meta-harness/reference_examples/terminal_bench_2/meta_harness.py`:
  agentic coding reference loop with expensive full evaluation.
- `_ref/meta-harness/reference_examples/terminal_bench_2/README.md`: smoke ->
  hard -> full bring-up order and cost warning.
- `_ref/autoresearch/README.md` and `_ref/autoresearch/program.md`: fixed
  evaluator, one mutable file, five-minute budget, keep/discard discipline.
- `data/meta_harness/domain_spec.md`: current Matrix domain mapping.
- `specs_sdd/features/016-meta-harness-agent-optimization/`: current harness,
  trace gate, artifact and promotion infrastructure.
- `specs_sdd/features/023-auto-optimization-inner-loops/`: current bounded
  inner-loop candidate infrastructure.

## Web Sources Checked

- [Meta-Harness: End-to-End Optimization of Model Harnesses](https://arxiv.org/abs/2603.28052)
  is the primary source. The key correction for Matrix is that Meta-Harness is
  an outer loop over harness code where the proposer can inspect prior source,
  scores and raw execution traces through the filesystem.
- [stanford-iris-lab/meta-harness](https://github.com/stanford-iris-lab/meta-harness)
  is the official reference repo. It reinforces the need for domain
  onboarding, candidate source/results/traces and held-out evaluation.
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch/blob/master/README.md)
  is not Meta-Harness, but its run discipline transfers well: fixed evaluator,
  single mutable target, fixed budget, result log and keep/discard loop.
- [AutoRAG](https://github.com/AutoRAG/AutoRAG) and
  [Marker-Inc-Korea/AutoRAG](https://github.com/Marker-Inc-Korea/AutoRAG)
  show RAG pipeline optimization as module/config search. This maps to Feature
  023 inner loops, not directly to Feature 034 promotion.
- [AutoRAG paper](https://arxiv.org/abs/2410.20878) frames automated RAG
  optimization around preprocessing, indexing, retrieval and prompt modules.
  Matrix should use this as a candidate generator for RAG/KG, not as the final
  agent-harness evaluator.
- [AutoRAG-HP](https://arxiv.org/abs/2406.19251) treats RAG hyperparameter
  tuning as an online bandit. Matrix can borrow budgeted exploration ideas for
  Feature 023 parameter sweeps.
- [SuperagenticAI/metaharness](https://github.com/SuperagenticAI/metaharness)
  is an unofficial implementation. Useful transferable patterns are explicit
  write scopes, run store, outcomes and inspect/compare CLI. It is not the
  authoritative definition of the method.

## Findings

- The previous Matrix work built important pieces, but a contract lane or
  one-off scenario run is not a full Meta-Harness iteration.
- The paper's ablation says raw traces matter; compressed summaries lose the
  signal needed to diagnose causality. Matrix proposer packets must therefore
  reference raw trace files and source snapshots, not only aggregate notes.
- The proposer should act as a coding agent with filesystem access. For Matrix,
  Codex can be the proposer, but we still need a durable interaction log so the
  run proves which files and traces were inspected.
- The evaluator must be frozen per run. If we change trace gates, goldens or
  holdout in the same iteration, the result is not a clean harness comparison.
- Search and holdout must be separated. The proposer can see search-set
  traces, but holdout results must stay out of experience packets.
- Pareto is useful because Matrix has multiple objectives: success, trace-gate
  pass rate, safety, memory correctness, RAG support, tool correctness, cost
  and latency.
- AutoResearch contributes operational rigor rather than agent-runtime design:
  bounded mutable zone, fixed budget, one run log, keep/discard, rollback.
- AutoRAG-style systems belong in Feature 023 as inner loops. Their best
  candidates feed Feature 034, where the outer loop decides promotion under
  Matrix agent-harness trace gates.

## Synthetic Versus Frontend Traces

The user does not need to drive Agent Chat in the frontend for the first real
Meta-Harness loop. The paper requires task rollouts that produce source
snapshots, scores and execution traces; it does not require a browser UI as the
source of those traces. Matrix can therefore create valid search-set traces by
having `meta_harness.scenario_runner` play synthetic user turns against the real
Python agent runtime.

For Feature 034, "synthetic" must mean deterministic scenario/user inputs with
real backend execution, not fake trace files. A valid no-browser rollout should
still exercise the same agent runner, LLM transport, tool registry, memory
nodes, retrieval/KG path, SSE stream capture and audit/runtime-event writers
that a frontend request would hit where practical. The scenario runner is the
simulated user; the Python agent is still the real system under test.

Frontend usage becomes necessary later for downstream live gates, not for the
initial Meta-Harness loop:

- Agent Chat rendering: verify tool calls, artifacts, PDFs/images and runtime
  cards are visible and usable.
- Control/Ops rendering: verify run timelines, candidate decisions, traces and
  prompt-cache evidence replay correctly.
- Matrix/widget gates: verify client-specific state events, fallbacks and
  visual behavior.

This matches the paper's task-instance framing: the search set can be simulated
episodes, while the proposer sees raw execution traces and scores from those
episodes. It also matches the official onboarding guidance that the important
questions are the unit of evaluation, search/holdout split, raw trace storage
and leakage policy, not whether a browser produced the user input.

## OpenRouter Practicality

Local env currently has an OpenRouter route available (`OPENROUTER_API_KEY`
and `LITELLM_BASE_URL` are set). `AGENT_DEFAULT_MODEL` is not set in the checked
env, while `AGENT_DEFAULT_UTILITY_MODEL` points at an OpenRouter free model.
Feature 034 runs should therefore pass `--model <openrouter/...>` explicitly
or set `AGENT_DEFAULT_MODEL` for the round.

OpenRouter is suitable for the first no-browser loop because its Chat
Completion API is OpenAI-compatible and supports standard bearer-token
authentication. OpenRouter prompt-cache behavior is provider/model dependent:
their docs describe automatic caching for many providers and explicit
`cache_control` for Anthropic-family routes, plus sticky routing to improve
cache hits. Feature 034 should not assume cache counters are always present;
Feature 032 owns provider-agnostic cache telemetry and the live cache probe.

Sources:

- [OpenRouter Chat Completion API](https://openrouter.ai/docs/api-reference/chat-completion)
- [OpenRouter Prompt Caching](https://openrouter.ai/docs/features/prompt-caching)
- [OpenRouter API overview](https://openrouter.ai/docs/api-reference/overview/)

## Decision

Create Feature 034 as the owner of the real iterative outer-loop. Keep Feature
016 as infrastructure and Feature 023 as candidate-generation/inner-loop work.
From now on, call a run "Meta-Harness applied" only when it completes at least
one propose/evaluate/decide iteration with prior raw artifacts and frozen
search evaluation.
