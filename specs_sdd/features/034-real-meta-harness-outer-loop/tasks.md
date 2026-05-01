---
title: Real Meta-Harness Outer Loop Tasks
status: planned
owner: filip
created: 2026-05-01
updated: 2026-05-01
feature_id: 034
---

# Tasks

## Spec And Boundaries

- [x] T001 [done-static] Create a separate feature for the real iterative
  Meta-Harness loop so Feature 016 static gates and Feature 023 inner loops are
  no longer mislabeled as full Meta-Harness application.
- [x] T002 [done-static] Reference the existing agent harness infrastructure:
  Feature 016 owns scenario runner, trace gates, candidate artifacts, holdout
  guard and promotion preflight.
- [x] T003 [done-static] Reference the existing inner-loop infrastructure:
  Feature 023 owns bounded RAG/extraction/memory/tool-policy sweeps that emit
  candidates for the outer loop.
- [x] T004 [done-static] Mark current static contract lanes as support lanes, not proof that
  Meta-Harness was iteratively applied.
  - 2026-05-01: `real_outer_loop_run.json` and
    `real_outer_loop_summary.json` carry
    `support_lanes_are_not_full_meta_harness=true`, and Feature 016/023 docs
    cross-link Feature 034 as the real iteration owner.

## Domain And Dataset

- [x] T010 [done-static] Freeze the first executable domain: agent runtime memory/RAG/tool
  routing, not the entire product surface.
- [partial-static] T011 Define the search scenario set and holdout scenario set for the
  first loop.
- [x] T012 [done-static] Add contamination/leakage guard that blocks holdout artifacts from
  proposer packets.
- [x] T013 [done-static] Define candidate write scopes for the first loop, with evaluator and
  golden files forbidden.
- [x] T014 [done-static] Define budget: candidate count, max wall-clock per candidate, max
  provider calls, max tool calls and rollback criteria.
  - 2026-05-01: `meta_harness.real_outer_loop` defaults to
    `agent-runtime-memory-rag-tool-routing` over
    `data/harness/memory_lifecycle/scenarios.json`; CLI budget args cover
    iterations, max scenarios, provider-call budget and wall-clock budget.
    Holdout sets remain protected by Feature 016; a Feature 034 holdout command
    is still open.

## Proposer Workspace

- [x] T020 [done-static] Persist proposer interaction logs when Codex is the proposer:
  files read, candidate hypothesis, causal diagnosis and selected source refs.
- [x] T021 [done-static] Require proposer packets to point at raw artifacts instead of only
  summaries: `source_snapshot.json`, `scores.json`, `verdicts.json`,
  `traces/**/*.json`, `sse/*.jsonl` and `decision.json`.
- [partial-static] T022 Add a pre-run checklist that fails if the proposer has no prior
  baseline artifacts to inspect.
- [x] T023 [done-static] Add read-statistics summary per iteration so we can prove the
  proposer actually inspected history rather than editing from memory.
  - 2026-05-01: every candidate stores `proposer_interaction.json` with raw
    file previews, hashes, artifact classes, failure clusters and
    `files_read_count`. Baseline artifacts are generated before proposal; a
    strict fail-closed pre-run check for externally supplied histories remains
    open.

## Candidate Generation

- [x] T030 [done-static] Implement prompt/config overlay candidate generation without
  external proposer LLM calls by default.
- [partial-static] T031 Implement bounded code-patch candidate envelopes with rollback ref,
  changed file list and declared risk.
- [x] T032 [done-static] Store patch/diff and proposal rationale beside every candidate.
- [x] T033 [done-static] Require `pending_eval.json` before evaluation and `decision.json`
  after evaluation.
- [partial-static] T034 Fail candidates that change evaluator, goldens, holdout or
  `python-backend/meta_harness/` during a product-domain run.
  - 2026-05-01: `outer-loop` creates deterministic provider-agnostic
    `config_overlay` candidates, stores proposal/config/interaction/patch
    artifacts, writes pending eval before evaluation and decision after
    evaluation. Frozen evaluator/scenario files are hashed before/after; full
    git-diff scope enforcement for arbitrary code patches remains open.

## Frozen Evaluation

- [x] T040 [done-static] Build one no-browser search runner command that evaluates baseline
  plus one candidate on the frozen search set.
- [ ] T041 Build one no-browser holdout command that requires explicit
  `allow_holdout=true`.
- [x] T042 [done-static] Ensure deterministic trace gates run before any LLM judge.
- [x] T043 [done-static] Store failure clusters over trace gates, root causes, tool errors,
  memory misses, retrieval misses and provider/budget failures.
- [x] T044 [done-static] Compute Pareto frontier over pass rate, trace-gate pass rate, cost,
  latency, tool correctness, memory correctness, RAG support and safety.
  - 2026-05-01: `python -m meta_harness.meta_cli outer-loop` evaluates
    baseline plus config-overlay candidates through `run_scenario_file`;
    experience packets carry failure clusters and Pareto frontier metadata.

## Iteration Loop

- [x] T050 [done-static] Implement a real `outer-loop` command that runs N iterations:
  experience packet -> propose -> pending eval -> evaluate -> decide ->
  update frontier.
- [x] T051 [done-static] Add dry-run mode that writes proposed next action without editing
  runtime files.
- [partial-static] T052 Add stop conditions: no improvement, repeated same failure cluster,
  budget exhausted, evaluator instability or user-required approval.
- [x] T053 [done-static] Add keep/discard/defer ledger compatible with AutoResearch-style
  result logs.
- [x] T054 [done-static] Add run summary that explicitly says whether a true Meta-Harness
  iteration occurred.
  - 2026-05-01: CLI `outer-loop` writes
    `real_outer_loop_summary.json` with `true_meta_harness_iteration`, decision
    ledger evidence, frozen evaluator gate and final frontier size.

## First Real Application

- [x] T060 [done-live-no-browser] Run a first cheap loop over memory/RAG/tool-routing scenarios.
- [x] T061 [done-live-no-browser] Inspect dominated candidates and update the next proposal from raw
  traces, not only aggregate scores.
- [x] T062 [done-live-no-browser] Apply one bounded runtime improvement if a search-set failure has a
  clear causal trace.
- [x] T063 [done-live-no-browser] Re-run the frozen search evaluator and log keep/discard/defer.
- [ ] T064 Run holdout only after a candidate passes promotion preflight.
- [x] T065 [done-live-no-browser] Apply and verify the first bounded runtime
  candidate from raw trace inspection: immediate recent-memory recall after
  explicit `memory_add`.
  - 2026-05-01: first `run-metaharness-round-1` exposed empty traces and
    Postgres/Memory-Fusion misrouting to a foreign `:5433` container. A bounded
    runtime fix in `python-backend/memory_fusion/providers.py` preserves
    explicit `HINDSIGHT_DB_URL`/`MEMPALACE_DB_URL` across the third-party
    `hindsight_api` import. Verification:
    `run-metaharness-round-1-db-sanity-fixed` passed with
    `trace_gate_pass_rate=1.0`, `stream_gate_pass_rate=1.0`, memory route
    `fusion`, tools `memory_add/memory_search`, and real provider telemetry.
    Then `run-metaharness-round-1-fixed` completed a true propose/evaluate/
    decide loop with baseline fitness `0.8424`, candidate fitness `0.8423`,
    candidate `paper_ready=true`, and decision `discard`. Holdout remains open.
  - 2026-05-01: `run-metaharness-round-2-recent-memory-fixed` verified a
    runtime candidate in `agent.tools.memory_hindsight`: explicit
    `memory_search` can return a same-thread recent `memory_add` before the
    durable index catches up. Transcript included the exact probe phrase and
    trace/stream gates passed. Existing fitness did not increase, so add an
    answer-level exact-recall metric before relying on this scorer for
    promotion.
- [x] T066 [done-static] Add runtime preflight for live no-browser rounds so a
  down or wrong local Postgres is caught before provider calls are spent.
  - 2026-05-01: `meta_harness.runtime_preflight` checks
    `AUDIT_DB_URL/HINDSIGHT_DB_URL`, auto-starts only the known local
    `matrix-memory-eval-postgres` on `:55433`, fails unknown unreachable DB
    targets, and writes `runtime_preflight.json` plus summary metadata.
- [x] T067 [done-static-live-prep] Add a Local-8B Agent Harness floor suite
  for the full no-browser backend surface.
  - 2026-05-01: `data/harness/local_8b_floor/scenarios.json` covers direct
    routing, skill injection, explicit Memory-Fusion, tool/SSE rendering,
    RAG/KG retrieval boundary, semantic lookup and subagent policy. This is
    the target-model floor for Bonsai/llama.cpp or any provider-agnostic 8B
    OpenAI-compatible route.
- [x] T068 [done-static] Fold deterministic trace/stream gate failures into
  scalar scenario fitness.
  - 2026-05-01: `run_scenario()` now records `base_fitness_score`,
    `expectation_gate_passed`, per-gate booleans and `fitness_penalties`, then
    caps failed trace/stream runs. The outer loop can no longer treat a
    healthy-but-wrong response as Pareto-equivalent to a correct response.
- [x] T069 [done-live-no-browser] Run a formal Local-8B Meta-Harness outer-loop
  round with Bonsai as the target agent.
  - 2026-05-01: `run-metaharness-round-local8b-001` completed
    baseline -> proposer artifact inspection -> config-overlay candidate ->
    frozen search eval -> decision ledger -> final frontier. Summary reports
    `true_meta_harness_iteration=true`; frozen evaluator gate passed; baseline
    scored `0.9995`, candidate scored `0.9994`, and the candidate was
    discarded as a regression.

## Documentation

- [x] T070 Record web and local research in `research.md`.
- [x] T071 [done-static] Update Feature 016 docs to cross-link Feature 034 as the real
  iterative execution owner.
- [x] T072 [done-static] Update Feature 023 docs to cross-link Feature 034 as the outer-loop
  promotion owner.
- [x] T073 [done-live-no-browser] Add closeout evidence when the first true loop completes.
- [x] T074 [done-static] Record paper/web model-strength finding: the paper used
  Claude Code with Opus-4.6 as proposer, while frozen target models varied by
  domain. Matrix keeps Codex/frontier model as proposer and uses OpenRouter/free
  routes only for cheap target-agent rollouts.
- [x] T075 [done-static] Record local Bonsai/llama.cpp provider path and floor
  scenario contract in `research.md`.
- [x] T076 [done-live-no-browser] Record formal Local-8B outer-loop evidence in
  `research.md`, `gates.md` and `closeout.md`.
