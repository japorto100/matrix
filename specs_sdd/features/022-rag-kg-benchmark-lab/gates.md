---
title: RAG/KG Benchmark Lab Gates
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-30
feature_id: 022
---

# Gates

## 2026-04-29 Expanded Candidate Gates

- Browser-local retrieval from Feature 026 is evaluated under matched canaries.
- Semantic-term retrieval from Feature 025 is evaluated against ambiguity and
  provenance cases.
- Visual-layout evidence from Feature 028 is evaluated for citation accuracy.
- Report-grounding from Feature 027 is evaluated for unsupported-claim rate.
- 2026-04-30: `knowledge-contract` adds a provider-free benchmark lane for
  Memory/KG/RAG/Semantic boundary contracts and is included in the aggregate
  `contract-suite`.

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
- KG/fused candidates must prove their graph projection is rebuildable from the
  primary Postgres/source-artifact store before promotion.
  - 2026-04-30: metadata compatibility now fail-closes KG-bearing candidates
    without `kg_projection_source_of_truth=postgres_source_artifacts`,
    `kg_projection_rebuildable=true` and `kg_projection_replay_checksum`.
    The NornicDB projection canary also checks selected KG reference metadata
    for `rebuildable` and `replay_checksum`.
