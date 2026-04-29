---
title: Browser RAG WebGPU Local First Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 026
---

# Research

## Local Z Reference

Derived from `Z_Browser_RAG_WebGPU_CPU_Models.md`.

## Working Judgement

The immediate value is browser RAG, not browser LLM chat. Small embeddings,
lexical search and reranking can improve privacy and UX. Local LLMs remain
opt-in because CPU fallback can degrade old hardware badly.

## Source Check 2026-04-29

- Transformers.js and ONNX/WebGPU runtimes make browser embeddings practical
  enough for a pilot, with WASM as fallback.
- WebLLM demonstrates provider-agnostic in-browser LLM inference, but model
  download, GPU memory and CPU fallback cost make it unsuitable as default.
- DuckDB-Wasm and browser storage patterns support local analytical/search
  workloads, but Matrix should start with a smaller local index path.
- RAGSearch/GraphRAG evidence still says retrieval quality must be benchmarked;
  local browser retrieval is a candidate lane, not a replacement for backend
  KG/RAG.

## Design Consequence

Default pipeline:

```text
worker lexical search + worker embedding search -> RRF -> optional small
reranker -> evidence UI -> backend/KG/LLM when needed
```

No provider dependency is required. Server fallback can target any compatible
embedding/reranking/generation backend configured by Feature 011/019.
