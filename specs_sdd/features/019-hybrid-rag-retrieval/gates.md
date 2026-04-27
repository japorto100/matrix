---
title: Hybrid RAG Retrieval Gates
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 019
---

# Gates

- Remote embeddings are configurable without hardcoding one provider.
- Local embedding downloads are disabled by default and cache to HDD when
  enabled.
- Retrieval modes are independently runnable: vector-only, KG-only, fused.
- Every answer context item carries provenance.
- Graph retrieval is not default for simple/general QA until eval shows value.
- KG context can be disabled without breaking dense RAG.
- Eval reports quality and latency, not only functional success.
