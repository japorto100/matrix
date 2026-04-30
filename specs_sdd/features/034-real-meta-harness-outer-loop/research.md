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
- [Anthropic: Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
  reinforces the same practical lesson: harness assumptions should be tested
  against real traces and simplified or specialized as models improve.
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
  contributes the operational checklist pattern: progress artifacts, feature
  lists, dev-server/test self-checks and explicit verification before marking
  work complete.
- [Anthropic: Scaling Managed Agents](https://www.anthropic.com/engineering/managed-agents)
  frames agent systems as session, harness and sandbox interfaces that should
  be swappable. This supports Matrix's provider-agnostic requirement.
- [VeRO: An Evaluation Harness for Agents to Optimize Agents](https://arxiv.org/abs/2602.22480)
  independently supports versioned snapshots, budget-controlled evaluation and
  structured observations for agent-optimization loops.
- [Autoresearch analysis](https://kingy.ai/ai/autoresearch-karpathys-minimal-agent-loop-for-autonomous-llm-experimentation/)
  was used only as secondary context; the transfer is the explicit metric,
  fixed budget and keep/discard loop, not the ML-training-specific target.

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

## 2026-05-01 Local Model Decision

The first live no-browser loop should not use a tiny output cap. The limiting
resource in this session is request count, not tokens. A 768-token cap is only
appropriate for provider smoke tests; real agent/tool traces need enough output
room for tool-call recovery, memory responses, SSE metadata and final answers.
Round 1 therefore used `AGENT_MAX_OUTPUT_TOKENS=4096` with a small scenario
count instead of many clipped rollouts.

Checked routes:

- `nvidia/nemotron-3-super-120b-a12b:free`: available in the OpenRouter model
  catalog with large context and tool/structured-output support, but the local
  direct test returned 429. Do not burn the limited request budget on this
  route until rate limits recover.
- `openrouter/free`: direct OpenRouter call succeeded and routed to
  `openai/gpt-oss-20b:free`, but the local LiteLLM gateway returned an
  insufficient-credits error for the alias.
- `openrouter/openai/gpt-oss-20b:free`: passed through the local LiteLLM
  gateway and was used for Round 1. It produced real tool calls, cache
  telemetry and Memory-Fusion traces.

Operational decision: for the next no-browser rounds, keep the request count
low, use explicit provider/model routing instead of the `openrouter/free`
alias, and prefer 4096-8192 output tokens depending on scenario complexity.
The proposer remains Codex; OpenRouter supplies the agent under test, not the
Meta-Harness proposer.

## 2026-05-01 Paper Model Strength Finding

The paper does not show that a small model can reliably serve as the
Meta-Harness proposer. It uses a strong coding-agent proposer: local paper
Section 3.1 states that the proposer `P` is Claude Code with Opus-4.6, guided
by a short instruction file and given filesystem access to prior harness source,
scores and execution traces. The paper also says the base model `M` varies by
domain and is frozen.

The domain base/evaluation models are separate from the proposer:

- Text classification used `GPT-OSS-120B` as the fixed classifier model.
- Math retrieval searched on `GPT-OSS-20B` and evaluated the discovered harness
  on held-out models including `GPT-5.4-nano`, `GPT-5.4-mini`,
  `Gemini-3.1-Flash-Lite`, `Gemini-3-Flash` and `GPT-OSS-20B`.
- TerminalBench-2 evaluated discovered coding harnesses on Claude Opus 4.6 and
  Claude Haiku 4.5.

Implication for Matrix: the proposer should remain a frontier coding agent
with file/tool access when we expect real code changes. Free/OpenRouter
`gpt-oss-20b` routes are acceptable for cheap target-agent smoke/search
rollouts, but not for the proposer role in a serious multi-file backend
mutation. The paper's own limitation section says broader proposer-model
studies remain future work, so Matrix should not claim equivalence if we swap
the proposer for a much weaker model.

The important capability is not only raw IQ; it is the full proposer interface:
source tree access, raw traces, scores, prior candidate artifacts and enough
context/output budget to diagnose failure clusters. This matches the arXiv
abstract's core claim that Meta-Harness uses an agentic proposer with filesystem
access to source, scores and execution traces, and the ablation that raw traces
are the key ingredient.

## 2026-05-01 Round 1 Findings

The first attempted run was valuable but not paper-ready: traces were empty
because the local `:5433` port was owned by `geomapadvanced-postgres`, while
Matrix's intended `matrix-postgres` container was only created. This produced
Audit/Hindsight authentication errors and no Memory-Fusion events.

The isolated Memory-Eval Postgres in `docker-compose.memory-eval.yml` on
`:55433` is the right local target for Meta-Harness rounds when the normal
dev-stack port is occupied. The remaining issue was that importing
`hindsight_api` reloads `.env` and overwrites `HINDSIGHT_DB_URL`. The bounded
fix in `memory_fusion.providers` preserves explicit runtime DB env after that
import. After the fix:

- `run-metaharness-round-1-db-sanity-fixed` produced a valid backend trace with
  `trace_gate_pass_rate=1.0`, `stream_gate_pass_rate=1.0`, `memory_retain`,
  `memory_recall`, `memory_add`, `memory_search` and route `fusion`.
- `run-metaharness-round-1-fixed` was a true Meta-Harness iteration:
  baseline passed, the proposer inspected raw artifacts, the candidate was
  evaluated with the frozen runner, and the decision ledger discarded it as
  dominated.

The main design implication is important: Meta-Harness should first validate
its trace substrate before spending model calls. Empty traces, provider alias
failures and wrong DB routing must fail the round or produce infrastructure
findings, not be treated as candidate quality.

## 2026-05-01 Runtime Preflight Stabilization

Round 1 and Round 2 showed that the loop needs a hard preflight before it burns
provider calls. The new rule is narrow and safe: when `AUDIT_DB_URL` or
`HINDSIGHT_DB_URL` targets local `:55433`, Meta-Harness may auto-start only the
known `matrix-memory-eval-postgres` service. If another host/port is configured
and unreachable, the run fails instead of guessing which stack owns the port.

The preflight is recorded in `runtime_preflight.json` under the run directory
and embedded in `real_outer_loop_summary.json`. This turns DB readiness into an
explicit artifact: downstream analysis can distinguish candidate failure from
infrastructure failure.

## 2026-05-01 Round 2 Recent-Memory Finding

Round 1 also exposed a quality issue that the original trace gates did not
score strongly enough: after `memory_add` succeeded, the immediate
`memory_search` could still return no durable hit because indexing/summary work
lags the verbatim write. The trace gate passed because `memory_retain`,
`memory_recall`, `memory_add`, `memory_search` and route `fusion` were present,
but the visible assistant answer could still say the exact phrase was not
found.

The bounded runtime candidate adds a short-lived same-thread/same-bank recent
write fallback in `agent.tools.memory_hindsight.MemorySearchTool`. It only
serves explicit recent `memory_add` content inside the existing dedupe window
and does not bypass durable Memory-Fusion storage; it bridges the immediate
user-visible recall gap while the durable index catches up.

Verification:

- Unit: `tests/agent/tools/test_memory_hindsight.py` covers immediate
  `memory_add` -> `memory_search` recall before engine results are available.
- Live no-browser: `run-metaharness-round-2-recent-memory-fixed` passed
  `trace_gate_pass_rate=1.0` and `stream_gate_pass_rate=1.0`; transcript answer
  included the exact phrase
  `memory_lifecycle_probe_prefers_verbatim_evidence_before_compaction`.
- Scoring gap: fitness remained `0.8423`, so a future Feature 034/016 task
  should make answer-level exact-recall assertions first-class, not only trace
  presence assertions.

## Decision

Create Feature 034 as the owner of the real iterative outer-loop. Keep Feature
016 as infrastructure and Feature 023 as candidate-generation/inner-loop work.
From now on, call a run "Meta-Harness applied" only when it completes at least
one propose/evaluate/decide iteration with prior raw artifacts and frozen
search evaluation.
