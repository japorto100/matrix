---
title: Semantic Layer Metrics Claims Gates
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-30
feature_id: 025
---

# Gates

- G001 No metric-sensitive answer uses an invented definition when a semantic
  catalog is available.
- G002 Metric definitions carry owner, version, grain and freshness.
- G003 Ambiguous definitions produce a clarification or explicit choice.
- G004 Permission filtering applies before value exposure.
- G005 SQL generation is constrained by semantic definitions.
- G006 KG claims linked to semantic terms retain bitemporal provenance.
- G007 RAG citations linked to semantic terms retain source artifact refs.
- G008 User corrections create proposals, not silent truth mutations.
- G009 Control UI exposes semantic definitions and conflict status.
- G010 Meta-Harness covers structured, KG and RAG semantic questions.

## 2026-04-30 Static Gate Status

- [x] G003/G004 are covered by
  `knowledge-semantic-ambiguity-permission-fail-closed`.
- [x] G001/G002/G005 now have provider-free agent-answer coverage through
  `knowledge-semantic-lookup-before-metric-answer`: a metric-sensitive answer
  must observe `semantic_lookup`, carry the metric id/catalog version/freshness
  and keep `raw_sql_allowed=false`.
- [x] G001 now also covers near-miss lexical suggestions: unknown phrases may
  surface `candidate_matches`, but they remain non-authoritative and require
  confirmation before any metric answer. This is covered by
  `knowledge-semantic-lexical-candidate-requires-confirmation`.
- [x] G006/G007 are covered by
  `knowledge-rag-kg-semantic-context-grounded`.
- [x] G007 also has runtime coverage through Feature 019 semantic retrieval
  filters over `semantic_term_ids` and `metric_id`.
- [x] G007 now has agent-tool handoff coverage: compact `semantic_lookup`
  model output carries catalog version, term ids, KG claim types and RAG source
  classes for term matches, plus metric id/catalog version for metric plans.
- [x] G008 is covered by
  `knowledge-semantic-correction-review-proposal`.
- [x] G008 has runtime Control API coverage: corrections create/list/review
  proposals and return `catalog_mutated=false`.
- [x] G008 has memory-feedback runtime coverage: source-linked memory evidence
  can create a semantic correction proposal, but unreferenced memory feedback is
  rejected and the catalog is not mutated.
- [x] G010 has provider-free static coverage through `knowledge-contract`;
  it now includes structured metric lookup, KG/RAG grounding, ambiguity,
  corrections, lexical provenance and downstream artifact visibility. Live
  agent/Control UI verification remains in `live-verify.md`.
