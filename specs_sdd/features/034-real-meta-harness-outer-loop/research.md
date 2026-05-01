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

## 2026-05-01 Local Bonsai / 8B Floor Finding

Bonsai 8B is useful as the frozen target-agent floor, not as the
Meta-Harness proposer. Local inspection found the GGUF model at
`/mnt/cold-storage/models/huggingface/models--prism-ml--Bonsai-8B-gguf/.../Bonsai-8B.gguf`.
It is Qwen3-family, about 8.19B parameters and advertises a 65,536 token
context window. On this i7-2600/8GB machine, direct `llama-cli` generation was
slow but usable for small no-browser traces, roughly 4 tok/s in the local
smoke.

`llama-server` was built locally and exposes an OpenAI-compatible endpoint at
`http://127.0.0.1:8081/v1` with model alias `bonsai-8b`. A direct chat smoke
returned the expected marker, and `meta_harness provider-smoke` passed when
`LITELLM_BASE_URL` pointed at the local llama.cpp server. Matrix now records
`bonsai-8b` as a provider-agnostic local capability override with provider
`llamacpp`; no OpenAI/Anthropic-specific assumptions are needed.

One live no-browser finding matters for future local-model rounds: the normal
Agent Harness prompt is already about 1.1k prompt tokens even with tools
disabled, because the run still includes system instructions, skill finder
evidence, memory recall/retain hooks, route telemetry and downstream stream
metadata. On CPU Bonsai this direct case took about 110 seconds. Therefore
local 8B floor runs should use a realistic timeout such as
`META_HARNESS_TURN_TIMEOUT_S=420` and low `AGENT_MAX_OUTPUT_TOKENS`, instead of
clipping the harness surface to make the smoke look cheap.

The first failed floor run was useful: TCP on `:55433` was not enough to prove
Postgres readiness because a stale rootless port proxy accepted connections
while the container was not SQL-ready. Runtime preflight now verifies an actual
Postgres `SELECT 1`, auto-starts the known local Memory-Eval container when
safe, and records `postgres_ready_before/after` in the artifact.

The second failure exposed an env-leak: importing `hindsight_api` can reload
repo env files and overwrite `LITELLM_BASE_URL`, sending the later LLM call to
the default LiteLLM gateway instead of llama.cpp. `memory_fusion.providers`
now restores explicit LLM provider/model/base-url env along with DB and
embedding env after that import.

Verification:

- `run-provider-smoke-bonsai-local-v3` passed with provider snapshot
  `llm_provider=llamacpp`, model `bonsai-8b`, and direct chat through
  `http://127.0.0.1:8081/v1`.
- `run-local8b-floor-bonsai-direct-long-timeout` passed the direct routing
  scenario with real audit events, Memory-Fusion hooks, route decision,
  `llm_response`, SSE text/finish packets and `trace_gate_pass_rate=1.0`.

The right 8B usage is a floor gate:

- Codex/frontier model remains proposer and code editor.
- Bonsai/local 8B is the agent under test that must drive the Matrix Agent
  Harness through standard chat/tool/SSE/memory paths.
- Passing the floor does not prove top-end quality; failing the floor reveals
  harness affordance or instruction/tool-schema issues that small models cannot
  overcome.

`data/harness/local_8b_floor/scenarios.json` turns this into an executable
contract over the whole Agent Harness boundary: direct routing, skill
injection, explicit memory, chart tool stream evidence, RAG/KG retrieval
boundary, semantic lookup and subagent policy. This is synthetic only in the
user input; it still runs the real backend agent, provider transport, tools,
memory, audit and stream capture.

## 2026-05-01 Expectation-Adjusted Fitness Finding

Round 2 showed that generic session fitness is insufficient for Meta-Harness
selection. A run can complete, call tools and emit healthy traces while still
missing an answer-level exact term or downstream stream artifact. That is a
wrong run for the scenario, so it must not keep a high scalar fitness merely
because the transport was healthy.

`run_scenario()` now keeps the original `base_fitness_score`, records
`trace_gate_passed`, `stream_gate_passed` and `expectation_gate_passed`, and
caps `fitness_score` when deterministic gates fail. The raw verdicts remain
the primary evidence; the scalar change exists so Pareto/frontier code cannot
accidentally promote a healthy but wrong candidate.

## 2026-05-01 Formal Local-8B Outer-Loop Round

`run-metaharness-round-local8b-001` is the first formal Local-8B Feature 034
round. It used the frozen Local-8B floor search file with `max_scenarios=1`,
Codex/deterministic Matrix policy as proposer and Bonsai 8B over llama.cpp as
the target agent.

Evidence:

- `real_outer_loop_summary.json` reports `true_meta_harness_iteration=true`.
- Runtime preflight passed with `postgres_ready_before=true` and
  `postgres_ready_after=true`.
- Frozen evaluator gate passed; no evaluator or scenario path changed during
  the run.
- The proposer inspection read 24 source/score/verdict/trace artifacts from
  prior candidate history.
- Baseline passed the direct Local-8B floor:
  `completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
  `stream_gate_pass_rate=1.0`, `fitness_score=0.9995`.
- Candidate `iter-001-config-overlay` also passed deterministic gates but
  scored `0.9994`, so the decision ledger discarded it as a small regression.
- Final frontier size was 15 and holdout remained hidden from proposer input.

This confirms the loop mechanics now work with a local small target model. It
does not imply that the local 8B model is good enough for all tool/memory/RAG
tasks; the remaining six `local_8b_floor` scenarios should be executed in
separate small rounds because CPU latency is several minutes per Agent Harness
turn.

## 2026-05-01 Local-8B Skill-Injection Slice

The first targeted post-round slice was `local8b-skill-risk-001`. It proved
two useful harness facts:

- Running as the shared `anonymous` user can contaminate synthetic scenarios
  with memories retained by earlier harness runs. The first skill run passed,
  but its prompt included unrelated Direct-Route recall blocks and took about
  403s.
- Running with an isolated synthetic user initially failed before the LLM call
  because the Meta-Harness env credential resolver did not know local
  OpenAI-compatible providers. The graph-level CredentialPool correctly found
  no per-user DB credential for `mh-local8b-skill-risk-001`, but the
  in-process harness should have passed the process `LITELLM_API_KEY` for
  `llamacpp`.

Decision: keep synthetic Meta-Harness users isolated and let the harness
credential resolver support provider-agnostic local routes (`llamacpp`,
`ollama`, `vllm`, `lmstudio`). This does not change production FastAPI user
credential semantics. The fixed run passed with real skill search/injection,
real LLM transport, runtime telemetry, memory/audit writes and SSE finish
evidence.

## 2026-05-01 Tool Search / Deferred Tool Loading Finding

The Local-8B memory floor exposed the same scaling issue Anthropic documents
for large tool sets. In `run-local8b-floor-memory-explicit-001`, the eager
ToolRegistry path sent the full tool grammar to llama.cpp. The request grew to
about 7.8k tokens and failed against a 4k context before the model could call
`memory_add` or `memory_search`.

Relevant references:

- `https://code.claude.com/docs/en/agent-sdk/tool-search`: Claude Code Tool
  Search withholds tool definitions from context and loads only relevant tools
  on demand; the docs state that 50 tools can consume 10-20K tokens and that
  accuracy degrades with more than 30-50 loaded tools.
- `https://www.anthropic.com/engineering/advanced-tool-use`: Anthropic
  describes `defer_loading`, a Tool Search Tool, and regex/BM25/custom search
  strategies; only matching tool definitions are expanded into the model
  context.

Matrix decision:

- Short term: add per-scenario `allowed_tools` so no-browser Local-8B floors can
  test the intended tool path without unrelated schemas causing context
  overflow.
- Verification: `run-local8b-floor-memory-explicit-001-tools-filtered` reduced
  the first-turn prompt to about 1.3k tokens, exercised `memory_add` and
  `memory_search`, and passed trace/stream/completion gates at `1.0` with
  `fitness_score=0.8473`.
- Product follow-up: implement provider-agnostic deferred tool discovery in
  the Agent Runtime. The first prompt should contain a compact searchable
  catalog or `tool_search` capability, then load only the selected 3-5 full
  schemas for the current turn. This should apply to normal tools and MCP
  tools; static scenario allowlists are not the final architecture.
- Implementation follow-up: Feature 024 now adds the normal-tool runtime
  version of this pattern. Large builtin tool sets start with searched full
  schemas plus a normal `tool_search` fallback; `tool_search` returns
  metadata-only matches; LangGraph and SimpleLoop expand provider
  `tool_definitions` after the search result. Feature 034 still needs a
  Local-8B no-browser gate that removes scenario `allowed_tools` and proves the
  deferred path live.
- Live follow-up: `run-local8b-floor-memory-explicit-001-deferred-tools-
  slim-long` passed the no-allowlist version of the memory floor. The provider
  telemetry showed `tool_count=4` for the active turn instead of the full
  registry, while trace and stream gates still observed `memory_add` and
  `memory_search` with `tool_success_rate=1.0`.

## Decision

Create Feature 034 as the owner of the real iterative outer-loop. Keep Feature
016 as infrastructure and Feature 023 as candidate-generation/inner-loop work.
From now on, call a run "Meta-Harness applied" only when it completes at least
one propose/evaluate/decide iteration with prior raw artifacts and frozen
search evaluation.
