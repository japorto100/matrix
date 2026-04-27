---
title: Auto-Optimization Inner Loops Tasks
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
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

- T010 Define `InnerLoopCandidate`: id, feature owner, search-space version,
  config, changed parameters, expected metric impact, budget estimate and
  rollback/default.
- T011 Define `InnerLoopRun`: corpus/scenario set, train/holdout split,
  component metrics, cost/latency, failures and generated artifacts.
- T012 Define adapter from inner-loop run to Meta-Harness candidate artifact:
  `aggregate.json`, `scores.json`, `verdicts.json`, config snapshot and
  evidence refs.
- T013 Add decision fields: promote to outer loop, discard, defer, needs human
  review.

## RAG/Extraction Inner Loop

- T020 Add search spaces for parser/splitter/chunking:
  PyMuPDF4LLM, Docling, MinerU, recursive/character/hierarchy-aware chunking,
  chunk size, overlap and metadata enrichment.
- T021 Add search spaces for retrieval:
  vector-only, KG-only, fused, top-k, RRF weights, citation verifier and
  context-bubble size/diversity policy.
- T022 Add budget-safe local/deterministic mode for repeated loops.
- T023 Add optional OpenRouter-free/provider mode with strict request caps and
  pacing.
- T024 Add source-grounding candidate generator for Feature 021/019:
  parser, chunker, metadata enrichment, top-k, RRF weight and citation-verifier
  settings.

## Memory/Agent Inner Loop

- T030 Define memory candidate dimensions: Hindsight/MemPalace recall blend,
  query gate threshold, pre-save/compaction threshold, injection order and
  decay settings.
- T031 Define skill/tool candidate dimensions: trigger threshold, max selected
  skills, tool subset, output transformation and consent behavior.
- T032 Define runner candidate dimensions: dispatcher/simple/LangGraph parity,
  timeout, max iterations and max output tokens.
- T033 Define KG candidate dimensions: projection backend off/Postgres-only/
  NornicDB, path expansion depth, temporal filter, access/recency decay and
  KG/vector fusion weight.

## Verification

- T040 Unit-test candidate schema validation.
- T041 Unit-test Meta-Harness artifact conversion.
- T042 Run one deterministic RAG inner-loop smoke over Feature 022 canaries.
- T043 Run one parser/chunking smoke over the ResearchWatcher PDF fixture.
- T044 Run one memory/context smoke without live provider calls.
- T045 Gate all live-provider loops behind quota/cost config.
- T046 Prove inner-loop candidates cannot modify benchmark goldens,
  deterministic evaluator code or holdout sets during a run.
