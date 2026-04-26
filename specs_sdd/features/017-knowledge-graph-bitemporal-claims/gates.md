---
title: Knowledge Graph Gates
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 017
---

# Gates

## Schema Gates

- KG claims carry valid-time and system-time metadata.
- Historical revisions remain queryable.
- Current-truth queries exclude superseded/rejected claims by default.
- Overlapping corrections do not destroy the right-hand remainder of an older
  validity window.
- Claim rows have provenance refs before promotion.

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

## Boundary Gates

- Raw memory/tool output is evidence, not a KG claim.
- Assistant summaries are secondary artifacts unless explicitly grounded.
- Personal Memory, Personal KB and global/world KG writes stay policy-separated.
- Missing KG support emits a degradation flag instead of silent fallback.

## Live Gates

- Evidence can produce a candidate KG claim.
- Candidate claim can be promoted with source refs.
- Corrected claim supersedes current truth while preserving history.
- Hybrid retrieval returns vector chunks plus KG paths with attribution.
- `/memory/kg` or successor surface can inspect claim status and provenance.
