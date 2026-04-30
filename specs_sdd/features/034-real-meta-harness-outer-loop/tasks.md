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

- [ ] T060 Run a first cheap loop over memory/RAG/tool-routing scenarios.
- [ ] T061 Inspect dominated candidates and update the next proposal from raw
  traces, not only aggregate scores.
- [ ] T062 Apply one bounded runtime improvement if a search-set failure has a
  clear causal trace.
- [ ] T063 Re-run the frozen search evaluator and log keep/discard/defer.
- [ ] T064 Run holdout only after a candidate passes promotion preflight.

## Documentation

- [x] T070 Record web and local research in `research.md`.
- [x] T071 [done-static] Update Feature 016 docs to cross-link Feature 034 as the real
  iterative execution owner.
- [x] T072 [done-static] Update Feature 023 docs to cross-link Feature 034 as the outer-loop
  promotion owner.
- [ ] T073 Add closeout evidence when the first true loop completes.
