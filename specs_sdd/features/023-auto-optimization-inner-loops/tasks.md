---
title: Auto-Optimization Inner Loops Tasks
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-29
feature_id: 023
---

# Tasks

## Source Review

- T001 Deep-read `_ref/auto-rag-optimizer` and record reusable pieces:
  `research_log.md`, bounded config proposal, pipeline run, evaluator,
  best-config tracking and chart/report outputs.
- T002 Review AutoRAG official framework for modular node search and
  combinatorial module/parameter evaluation.
- T003 Review AutoRAG-HP for online/hierarchical MAB ideas that reduce API
  calls versus grid search.
- T004 Review whether DSPy/GEPA-style optimizers already in `docs/papers/dspy`
  should inform prompt/tool/memory policy optimization.
- T005 Treat research/source reading as part of the optimization setup, not as
  the measured loop: AutoRAG/inner-loop can propose parser/retrieval/memory
  configs, but Feature 016 Meta-Harness remains the outer loop that decides
  promotion under frozen gates.

## Candidate Schema

- T010 [done-static] Define `InnerLoopCandidate`: id, feature owner, search-space version,
  config, changed parameters, expected metric impact, budget estimate and
  rollback/default.
- T011 [done-static] Define `InnerLoopRun`: corpus/scenario set, train/holdout split,
  component metrics, cost/latency, failures and generated artifacts.
- T012 [done-static-live-smoke] Define adapter from inner-loop run to Meta-Harness candidate artifact:
  `aggregate.json`, `scores.json`, `verdicts.json`, config snapshot and
  evidence refs.
- T013 [done-static] Add decision fields: promote to outer loop, discard, defer, needs human
  review.

## RAG/Extraction Inner Loop

- T020 Add search spaces for parser/splitter/chunking:
  PyMuPDF4LLM, Docling, MinerU, recursive/character/hierarchy-aware chunking,
  chunk size, overlap and metadata enrichment.
  - 2026-04-27: parser candidate space now has an optional MarkItDown adapter
    in addition to PyMuPDF4LLM and remote Docling/MinerU placeholders. It must
    still be benchmarked before promotion.
  - 2026-04-27: the PDF extraction benchmark accepts an explicit extractor
    registry name, allowing parser candidates to share the same evaluator,
    ground truth and Meta-Harness artifact shape.
- T021 [partial-done] Add search spaces for retrieval:
  vector-only, KG-only, fused, top-k, RRF weights, citation verifier and
  context-bubble size/diversity policy.
  - 2026-04-27: inner-loop retrieval candidates now carry concrete
    `top_k`, `token_budget`, `max_hits`, `fusion` and `context_bubble`
    parameters from the CLI run instead of only mode/vector/KG booleans.
    RRF weighting remains open because the current runtime only exposes the
    default RRF fusion.
- T022 [done-static-live-smoke] Add budget-safe local/deterministic mode for repeated loops.
- T023 Add optional OpenRouter-free/provider mode with strict request caps and
  pacing.
  - 2026-04-27: retrieval benchmark artifacts now record redacted provider and
    budget config, so provider-mode inner loops can be audited for model,
    embedding dimension and request-budget assumptions without storing secrets.
- T024 Add source-grounding candidate generator for Feature 021/019:
  parser, chunker, metadata enrichment, top-k, RRF weight and citation-verifier
  settings.
  - 2026-04-27: Feature 022 now exposes reference-level metadata failures
    (`missing-reference-metadata:<ref>:<key>`) that inner-loop candidates can
    optimize against without mutating goldens or holdout sets.
  - 2026-04-27: Feature 022 benchmark artifacts also emit decision-log entries
    for KG/fused candidates, giving the outer Meta-Harness proposer a concrete
    keep/discard/defer history instead of only raw scores.
  - 2026-04-27: `meta_harness.inner_loop` now propagates CLI retrieval search
    parameters into `inner_loop_candidate.json`, making source-grounding and
    retrieval-budget candidates auditable by Feature 016 before promotion.

## Memory/Agent Inner Loop

- T030 Define memory candidate dimensions: Hindsight/MemPalace recall blend,
  query gate threshold, pre-save/compaction threshold, injection order and
  decay settings.
- T031 Define skill/tool candidate dimensions: trigger threshold, max selected
  skills, tool subset, output transformation and consent behavior.
- T032 Define runner candidate dimensions: dispatcher/simple/LangGraph parity,
  timeout, max iterations and max output tokens.
  - 2026-04-29: add consent/approval parity to runner dimensions:
    `approval_interrupts`, confirm-unavailable fail-closed behavior and
    duplicate tool-message prevention are now explicit runner candidate checks.
- T033 Define KG candidate dimensions: projection backend off/Postgres-only/
  NornicDB, path expansion depth, temporal filter, access/recency decay and
  KG/vector fusion weight.

## Verification

- T040 [done-static] Unit-test candidate schema validation.
- T041 [done-static] Unit-test Meta-Harness artifact conversion.
- T042 [done-static-live-smoke] Run one deterministic RAG inner-loop smoke over Feature 022 canaries.
- T043 [done-static-live-smoke] Run one parser/chunking smoke over the ResearchWatcher PDF fixture.
  - 2026-04-27: `meta_harness.meta_cli pdf-extraction-benchmark` ran
    PyMuPDF4LLM against the ResearchWatcher PDF/Markdown ground-truth fixture
    as `run-pdf-extraction-feature023-20260427`.
  - Result: passed, token recall `0.9091`, phrase coverage `1.0`, table
    count `1`, latency `3532.881ms`, fitness `0.9682`.
  - Known gaps preserved for future parser candidates: formula count `0`,
    figure count `0`, no code fence.
- T044 [done-static-live-smoke] Run one memory/context smoke without live provider calls.
  - 2026-04-27: added `meta_harness.memory_context_smoke` and
    `meta_harness.meta_cli memory-smoke`. It writes normal Meta-Harness
    scenario artifacts from synthetic but contract-shaped memory events, so no
    LLM/provider call is required.
  - Smoke `run-memory-context-smoke-20260427` passed with provider calls `0`,
    trace gate pass rate `1.0`, tool success `1.0`, memory utilization `1.0`,
    and observed memory providers `hindsight,mempalace`.
- T045 [done-static-live-smoke] Gate all live-provider loops behind quota/cost config.
- T046 [done-static-live-smoke] Prove inner-loop candidates cannot modify benchmark goldens,
  deterministic evaluator code or holdout sets during a run.
  - 2026-04-27: `protected_input_gate()` fails candidates that expose
    `holdout_score`, `holdout_results`, `goldens_patch`, `evaluator_patch` or
    `canary_patch` in mutable candidate sections, and requires
    `frozen_evaluator.goldens_mutable == False`. Inner-loop smoke
    `run-inner-rag-splits-20260427` passed this gate.
