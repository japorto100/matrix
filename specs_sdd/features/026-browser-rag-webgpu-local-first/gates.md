---
title: Browser RAG WebGPU Local First Gates
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 026
---

# Gates

- G001 Model inference runs in a worker.
- G002 WebGPU failure falls back to WASM or server without crashing UI.
- G003 Browser LLMs are opt-in; CPU LLM fallback is not automatic.
- G004 Embedding index version records model, dimension and runtime.
- G005 Local retrieval exposes provenance and source type.
- G006 Local RAG never becomes the authoritative KG or memory store.
- G007 Playwright verifies non-blocking UI during model load.
- G008 Benchmarks compare local vs backend retrieval under the same canaries.
- G009 Cache can be cleared and rebuilt deterministically.
- G010 Mobile/low-resource devices get a safe degraded path.
