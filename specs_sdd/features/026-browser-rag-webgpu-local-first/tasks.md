---
title: Browser RAG WebGPU Local First Tasks
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 026
---

# Tasks

## Runtime

- T001 Inventory frontend workers and RAG/search call sites.
- T002 Add browser capability probe: WebGPU, WASM SIMD, storage quota and
  mobile constraints.
- T003 Define worker protocol for embed, search, rerank and unload.
- T004 Add model metadata schema: name, dimension, quantization, runtime and
  index version.
- T005 Implement cache policy using IndexedDB/OPFS/Cache API as appropriate.
- T006 Add explicit opt-in for large local model downloads.
- T007 Block main-thread model inference.

## Retrieval

- T010 Add lexical BM25/FlexSearch baseline for local documents/messages.
- T011 Add browser embedding baseline with a small 384-dim model candidate.
- T012 Add multilingual embedding candidate evaluation for German chat.
- T013 Add hybrid merge/RRF over lexical and dense local hits.
- T014 Add optional small reranker over top 10-20 hits.
- T015 Add server fallback when browser model load fails.
- T016 Add backend parity endpoint to compare local vs server retrieval.
- T017 Add privacy prefilter mode where query embedding stays local.

## UI

- T020 Add local-search status indicator without noisy marketing text.
- T021 Add model download/progress/error states.
- T022 Add "local/server/hybrid" retrieval source chips in evidence UI.
- T023 Add settings for local embeddings and opt-in local LLM experiments.
- T024 Prevent old hardware from auto-loading browser LLMs.

## Verification

- T030 Unit-test worker protocol.
- T031 Unit-test metadata/version mismatch invalidates stale local index.
- T032 Unit-test fallback chain.
- T033 Playwright-test local search UI states.
- T034 Browser live-test WebGPU path where available.
- T035 Browser live-test WASM fallback.
- T036 Meta-Harness compare local retrieval against Feature 022 canaries.
- T037 Record latency, memory and UI responsiveness.
