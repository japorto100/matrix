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
  - 2026-04-27: initial `compare_candidates()` runner enforces shared canary
    set, `k`, token budget and max-hits budget for Matrix vector/KG/fused
    candidates.
- Graph candidates must improve relevant multi-hop cases without regressing
  simple factual cases beyond an accepted threshold.
- KG retrieval cannot use personal memory lanes as evidence.
- Memory retrieval cannot use global KG as a personal-memory substitute.
- External candidate setup must be reproducible on this machine or documented
  as deferred.
- Promotion requires holdout results, not only search-set gains.
  - 2026-04-27: benchmark code now separates `search` and `holdout` canaries
    and reports `split_summary`/`holdout_pass_rate`; default Meta-Harness
    optimization still runs search only, so holdout promotion must be an
    explicit later gate.
- Source-grounded candidates must preserve reference-level provenance, not just
  answer-level citations.
  - 2026-04-27: canary expectations can require reference metadata keys; the
    benchmark runner fails candidates that lose source artifact, chunk hash,
    parser/chunker or `citation_ref` metadata on selected references.
