---
title: Knowledge Graph Gates
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-30
feature_id: 017
---

# Gates

## 2026-04-29 Semantic/Visual Follow-Up

- KG claim types can link to Feature 025 semantic terms without losing
  bitemporal claim status.
- Visual evidence from Feature 028 can create claim proposals only, not
  automatic truth.
- Browser-local entity/linking hints from Feature 026 are advisory and require
  server-side evidence before promotion.
- 2026-04-30: provider-free `knowledge-contract` validates KG proposals and
  selected KG context items for evidence refs, citation refs, semantic term
  links and bitemporal metadata before answer-time use.

## Schema Gates

- KG claims carry valid-time and system-time metadata.
- Historical revisions remain queryable.
- Current-truth queries exclude superseded/rejected claims by default.
- Overlapping corrections do not destroy the right-hand remainder of an older
  validity window.
- Claim rows have provenance refs before promotion.
- Static Meta-Harness `knowledge-contract` fails proposals that omit evidence,
  source artifact, chunk/hash, citation or semantic term refs.

## Retrieval Gates

- Retrieval combines semantic similarity with temporal/access decay.
- Dual retrieval can run vector-only, KG-only and fused modes.
- RRF fusion is deterministic and test-covered before adding learned re-rankers.
- Fused context carries both `source_uri`/chunk refs and KG `canonical_id` or
  claim refs.
- Decay affects ranking, not data retention.
- Access telemetry does not hot-update the main claim row on every recall.
- KG answer context exposes status, freshness, confidence and evidence refs.
- Large graph neighborhoods are summarized into short paths before prompt
  insertion.
- A selected claim can be expanded through the KG store API into a compact path
  and source refs before the generator sees it.
- [x] Selected KG claims emit runtime event metadata without source text.
  - 2026-04-30: fused retrieval emits `kg.retrieval.selected_claims` with
    selected claim ids and KG access counts after context-bubble selection.
  - 2026-04-30: scoped retrieval audits the same KG event metadata for replay
    while keeping claim text out of audit rows.

## Boundary Gates

- Raw memory/tool output is evidence, not a KG claim.
- Assistant summaries are secondary artifacts unless explicitly grounded.
- Personal Memory, Personal KB and global/world KG writes stay policy-separated.
- Personal-memory-derived claim proposals require review and cannot become
  accepted global KG claims through the static contract.
- Runtime KG store rejects direct promoted global claims from personal memory
  evidence layers and requires promoted claims to carry semantic terms plus
  citation/source/hash evidence.
- Missing KG support emits a degradation flag instead of silent fallback.

## Live Gates

- Evidence can produce a candidate KG claim.
- Candidate claim can be promoted with source refs.
- Corrected claim supersedes current truth while preserving history.
- Hybrid retrieval returns vector chunks plus KG paths with attribution.
- `/memory/kg` or successor surface can inspect claim status and provenance.
