---
title: Browser RAG WebGPU Local First
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 026
---

# Browser RAG WebGPU Local First

## Current State / Ist

Matrix RAG currently lives mostly in backend retrieval, KG and Meta-Harness
features. Browser-side search exists as UI behavior, not as a measured
local-first retrieval runtime.

## Target State / Soll

Feature 026 adds browser-local RAG primitives:

- worker-based embedding and lexical search;
- WebGPU-first, WASM fallback for small embedding/reranking models;
- no automatic browser CPU LLM fallback for normal users;
- versioned model/dimension/runtime metadata;
- local privacy prefiltering for selected documents/messages;
- server/KG fallback for persistent truth and heavy generation;
- benchmark gates across desktop/mobile and old hardware.

## Boundaries

- Feature 019 owns backend retrieval and context assembly.
- Feature 022 owns matched RAG/KG benchmark lab.
- Feature 023 owns optimization loops.
- Feature 005/007 own chat UI integration points.

Feature 026 owns browser runtime, cache and local retrieval behavior.

## Closeout Criteria

- Browser embedding runs in a worker, never main thread.
- WebGPU/WASM/server fallback chain is explicit and observable.
- Index metadata records model, dim, quantization and runtime.
- Local retrieval results can be compared against backend retrieval.
- Live browser tests prove no UI lockup on the target machine.
