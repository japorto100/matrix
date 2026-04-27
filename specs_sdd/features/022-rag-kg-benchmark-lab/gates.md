---
title: RAG/KG Benchmark Lab Gates
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 022
---

# Gates

- Every candidate uses the same corpus, question set, retrieval budget and
  context budget.
- Graph candidates must improve relevant multi-hop cases without regressing
  simple factual cases beyond an accepted threshold.
- KG retrieval cannot use personal memory lanes as evidence.
- Memory retrieval cannot use global KG as a personal-memory substitute.
- External candidate setup must be reproducible on this machine or documented
  as deferred.
- Promotion requires holdout results, not only search-set gains.
