# Domain Spec: Matrix Agent Harness Optimization

## Domain Summary

The target domain is the Matrix Python agent harness for trading analysis,
geopolitical/geomap reasoning, strategy review, research/source-quality work,
memory behavior and safe tool use.

One evaluation unit is a scenario: a single-turn or multi-turn simulated user
conversation executed against the Matrix Python agent. Each scenario has a
stable `scenario_id`, `thread_id`, `user_id`, `run_id`, `candidate_id`,
category, expected trace gates and optional judge rubric.

Fixed components for the first loop:

- base product scope: Matrix agent, not an autonomous coding-agent product.
- base runtime: Python Agent service or in-process runner.
- fixed runner variants under evaluation: `dispatcher`, `langgraph`, `simple`.
- fixed tool surface unless a candidate explicitly tests tool routing/policy.
- fixed memory stack components: Hindsight, MemPalace and orchestration/fusion
  diagnostic modes.
- fixed external proposer budget: disabled by default. Codex acts as proposer
  through filesystem/GitNexus/MCP context. External LLM proposer/judge calls
  require explicit run opt-in.

Stable optimization domains after the 001-023 checkpoint:

1. Source grounding and retrieval:
   - Features: 021 -> 019 -> 022 -> 023.
   - Unit: parser/chunker/retriever candidate over fixed canaries or PDF
     ground truth.
   - Required artifacts: source corpus, parser version, chunker version,
     embedding model/dimension, KG projection version, scores and verdicts.
2. Memory lifecycle and context injection:
   - Feature: 012, evaluated through Feature 016 scenarios.
   - Unit: multi-turn memory scenario with Hindsight, MemPalace or Fusion
     route expectations.
   - Required artifacts: memory route/provider metadata, evidence terms,
     source/session refs and no unrelated mutation.
3. Runner/tool/provider routing:
   - Features: 011, 013, 016, 020.
   - Unit: scenario trace with `route_decision`, tool/consent events and
     provider/budget metadata.
   - Required artifacts: runner variant, route decision, delegation decision,
     spawn depth, tool success rate and provider/token config.
4. Skills and inner-loop optimization:
   - Features: 015 and 023.
   - Unit: bounded config or skill candidate promoted only after search and
     holdout evidence.

Allowed changes for candidate search:

- prompt/context assembly overlays.
- memory routing, trigger policy and evidence-selection logic.
- skill selection/promotion policy.
- tool-use policy, consent flow, retry/recovery behavior and trace gates.
- scenario fixtures, deterministic validators and artifact logging.
- bounded developer-reviewed code patches inside declared write scope.

Candidate type must be explicit:

- `config_overlay`: environment, prompt, routing, threshold or policy change.
- `benchmark_candidate`: parser, chunker, retrieval or KG configuration with no
  runtime patch.
- `code_patch`: bounded implementation patch with file scope and rollback.
- `docs_only`: SDD/research update; cannot be promoted as runtime improvement.

Out of scope:

- switching base model as the primary optimization lever.
- productizing autonomous coding agents.
- changing frontend/Go/Matrix delivery as a prerequisite for Python-only
  harness search.
- holdout-set leakage into proposer context.
- scenario-specific hardcoded hacks.

Budget defaults for local runs:

- external LLM proposer budget: `0`.
- external LLM judge budget: `0`.
- initial candidate count: 1-3 mechanism-level candidates per iteration.
- initial scenario budget: 1-5 search scenarios per smoke run.
- larger loop budget: unknown until local stack stability is proven.

## Harness and Search Plan

Candidate harnesses must preserve the Matrix agent scenario interface:

- input: scenario fixture with turns, metadata, allowed consent overrides and
  trace expectations.
- execution: Python Agent service or in-process runner.
- output: transcript, SSE chunks, audit trace, scores, trace verdicts and
  candidate artifacts.

The first search loop should optimize harness mechanisms, not constants:

- memory trigger policy: when to use Hindsight context, when to recall
  MemPalace verbatim evidence, and when to require live tools.
- context construction: ordering, source/freshness labels, token-budget use and
  compaction/pre-save behavior.
- tool policy: required/forbidden tool expectations, consent behavior, failed
  tool recovery and safe sandbox/browser/file use.
- skill policy: trading/geopolitical/strategy/research skill selection and
  promotion evidence.

The first implementation loop should prefer source-grounding and route
observability over broad agent-behavior claims. A candidate that merely
"answers better" without trace evidence is not promotable.

Baselines:

- current dispatcher runner.
- LangGraph runner.
- graphless SimpleLoop runner.
- no-tool smoke scenarios.
- memory diagnostic modes: Hindsight-only, MemPalace-only and orchestration.

Reusable helpers needed from the start:

- scenario loader and runner.
- deterministic trace-gate evaluator.
- candidate artifact writer.
- Pareto frontier loader over filesystem/DB candidates.
- keep/discard/defer decision ledger.
- proposer interaction ledger for Codex-run iterations.
- paper-style candidate manifest and outer-loop experience packet.

Paper-aligned artifact rule:

- `meta_harness/` is the optimizer implementation.
- optimized harness surfaces are agent runtime, memory fusion, RAG/KG,
  skills/tool policy, Matrix transport/session handling and context assembly.
- every candidate must expose source references, scores and raw traces or typed
  benchmark evidence through `candidate_manifest.json`.
- before proposing new changes, create or inspect an `experience_packet.json`
  that lists Pareto frontier, dominated candidates, failure clusters,
  candidate decisions and inner-loop bridge candidates.
- inner loops can propose candidates, but only the outer loop can promote them.
- Autoresearch discipline applies to the run: fixed evaluator, fixed budget,
  keep/discard/defer log and no evaluator mutation during a run.

## Evaluation Plan

Search set:

- small, fast scenarios under `data/harness/search_set/`,
  `data/harness/runner_parity/`, `data/harness/memory_lifecycle/` and
  `data/harness/live_probe/`.
- covers memory, tools, skills, trading/research prompts and runner parity.

Held-out test set:

- `data/harness/holdout_set/`.
- proposer must not inspect holdout scores during search.
- holdout may be executed only with explicit `allow_holdout=true` or equivalent
  CLI/MCP guard.

Primary metrics:

- scenario completion rate.
- deterministic trace-gate pass rate.
- fitness score from existing scorer.
- required tool/memory/skill behavior correctness.
- safety/consent correctness.

Secondary metrics:

- turns.
- token use.
- cost estimate.
- latency.
- failed tool result count.
- memory/provider route correctness.

Noise and leakage:

- deterministic gates run before any LLM judge.
- external LLM judges are disabled by default.
- holdout results are excluded from proposer context.
- candidates must be mechanism-level and general, not tuned to exact scenario
  wording.
- proposer notes do not certify promotion. Only frozen evaluator artifacts,
  holdout verdicts and explicit keep/discard/defer decisions can do that.
- candidate generation must not modify benchmark goldens, deterministic
  evaluator code or holdout files during a run.

Cheap validation checks:

- import/test smoke for `meta_harness`.
- in-process no-tool runner parity.
- trace-gate unit tests.
- Pareto frontier load over existing run artifacts.

## Experience and Logging

Offline experience:

- existing audit/session traces.
- `data/meta_harness/runs/*/candidates/*` artifacts.
- `data/harness/*` scenario files.
- Feature 014 and 015 evidence.
- `_ref/meta-harness`, `_ref/EvoSkill`, `_ref/autoresearch`,
  `_ref/hermes-agent`, `_ref/hindsight`, `_ref/mempalace`.

Per-candidate artifacts:

- `run.json`.
- `scenario_set.json`.
- `config.json`.
- `source_snapshot.json`.
- `scores.json`.
- `verdicts.json`.
- raw trace JSON.
- SSE JSONL.
- `result.json`.
- aggregate metrics when a run has multiple scenarios.
- proposal/pending-eval/decision records when candidate generation is active.

High-signal debugging files:

- `python-backend/meta_harness/scenario_runner.py`.
- `python-backend/meta_harness/evaluator.py`.
- `python-backend/meta_harness/proposer.py`.
- `python-backend/meta_harness/pareto.py`.
- `python-backend/agent/runners/dispatcher.py`.
- `python-backend/agent/runners/simple.py`.
- `python-backend/agent/graph/runner.py`.
- `python-backend/memory_fusion/*`.
- `python-backend/agent/skills/*`.

Useful commands:

- `python -m meta_harness.meta_cli run <scenario-file>`.
- `harness_run_scenarios(...)` through MCP.
- `harness_evaluate(split="search")`.
- `harness_evaluate(split="holdout", allow_holdout=true)`.
- `harness_decide_candidate(...)`.
- Pareto summary from `meta_harness.pareto`.

## Open Questions and Unknowns

- Larger scenario budget: unknown until local Postgres/LiteLLM/OpenSandbox
  stability is proven.
- Exact production model set: unknown; OpenRouter is currently the practical
  local provider route.
- LLM-as-judge rubric: deferred; deterministic gates first.
- Promotion command: partially specified, not complete.
- Public-skill import strategy: owned by Feature 015 and evaluated by Feature
  016.
- Live frontend/Go/Matrix-room verification: out of Phase 1, later live-product
  verification path.
