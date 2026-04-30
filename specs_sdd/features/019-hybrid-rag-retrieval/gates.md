---
title: Hybrid RAG Retrieval Gates
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-30
feature_id: 019
---

# Gates

## 2026-04-29 Browser/Semantic/Visual Follow-Up

- Browser-local retrieval from Feature 026 is benchmarked against backend
  retrieval before promotion.
- Semantic filters from Feature 025 preserve source/provenance.
- Visual-layout evidence from Feature 028 carries coordinates/source refs in
  answer context.
- 2026-04-30: provider-free `knowledge-contract` validates selected RAG/KG
  context items for source artifact, chunk/hash, citation and semantic catalog
  metadata before they can support an answer.
- 2026-04-30: `retrieve(...)` applies optional `semantic_filter`/
  `semantic_phrase` constraints before fusion/context-bubble selection and
  emits semantic-filter degradation reasons on no-match, ambiguity or not-found.
- 2026-04-30: selected `retrieve(...)` context emits `provenance_status` on
  hits/references and supports `require_context_provenance=True` as a
  fail-closed gate.
- 2026-04-30: `knowledge-contract` also gates downstream Agent Chat-visible
  RAG/KG source/path artifact filenames, so provenance must be inspectable
  beyond answer text.

- Remote embeddings are configurable without hardcoding one provider.
- Local embedding downloads are disabled by default and cache to HDD when
  enabled.
- Retrieval modes are independently runnable: vector-only, KG-only, fused.
- Every answer context item carries provenance.
- Graph retrieval is not default for simple/general QA until eval shows value.
- KG context can be disabled without breaking dense RAG.
- Eval reports quality and latency, not only functional success.
- Deterministic canaries cover at least one KG-improves scenario and one
  vector-only-enough scenario before larger GraphRAG benchmarks are run.

## G2 Lexical / Runtime

- [x] BM25/regex/semantic/KG lanes expose lane name, score and degradation reason.
  - 2026-04-30: runtime retrieval annotates BM25/regex/lexical/vector/KG
    candidates with `retrieval_lane`, `lane_score`, lane counts and selected
    lanes without inlining source text into runtime metadata.
- [x] Lexical hits can improve recall but cannot become answer support without
  source/citation/provenance refs.
  - 2026-04-30: lexical hits flow through the same
    `require_context_provenance=True` fail-closed gate as vector/KG hits.
  - 2026-04-30: `knowledge-lexical-candidate-without-provenance-blocked`
    gates this in Meta-Harness; contract-suite now has 47 provider-free
    scenarios.
- [x] Retrieval runtime events preserve selected context ids without inlining large
  source text.
  - 2026-04-30: retrieval result runtime events carry ids/counts/status only;
    focused tests assert selected context/KG ids are present and source text is
    absent from event metadata.
  - 2026-04-30: scoped retrieval calls audit the same runtime events for Ops
    replay without storing raw query text.
- Tool/skill/source discovery uses progressive disclosure before full schema or
  document exposure.
- Semantic query planning has an agent-facing handoff: `semantic_lookup`
  returns compact term ids, catalog version, KG claim types and RAG source
  classes without exposing the full catalog or raw SQL.
