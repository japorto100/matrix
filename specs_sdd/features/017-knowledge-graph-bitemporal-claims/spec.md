---
title: Knowledge Graph, Bitemporal Claims and Decay Retrieval
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 017
migrated_from:
  - specs_sdd/features/012-memory-context-world-personal-kb
  - main_docs/root/MEMORY_ARCHITECTURE.md
  - main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md
  - specs/execution/exec-world-model.md
---

# Knowledge Graph, Bitemporal Claims and Decay Retrieval

## Current State / Ist

Matrix has KG primitives and tests, plus world-model planning inside Feature
012. Memory-Fusion already distinguishes raw evidence, derived personal memory
and world/KB artifacts, but global/domain KG ownership is too mixed with the
memory umbrella.

This feature owns the global/domain graph-specific model: entities, reified
claims/edges, validity windows, system-version history, claim status, conflict
handling, evidence backlinks and KG retrieval scoring. It is connected to the
nonicdb/NornicDB global KG backend/projection line, not to the agent-memory KG
rail.

## Target State / Soll

The KG is a global/domain claim graph, not a generic memory dump and not the
agent's private memory graph. Raw chat/tool evidence stays immutable in
Memory-Fusion/Hindsight/MemPalace. Hindsight's KG-like derived memory and
MemPalace's loci/episodic links remain inside the agent-memory lane. Feature
017 stores promoted world/domain claims or relations with provenance and
temporal semantics:

- business/valid time: when the claim is asserted to apply.
- system time: when Matrix learned or revised the claim.
- status: candidate, active, superseded, contradicted, rejected or archived.
- evidence refs: immutable links back to raw memory, KB artifacts or world
  evidence.
- retrieval score: semantic similarity plus recency/access/validity decay.

Postgres is the first claim source-of-truth target. The nonicdb/NornicDB line
is the first global KG backend/projection candidate to evaluate. Any graph
backend must be a rebuildable projection/index over the same claim source of
truth, not a competing truth store.

Retrieval is hybrid: vector candidates provide broad semantic recall, KG claims
and graph paths provide precision, and late fusion ranks the combined set at
answer time. Vector chunks, KG claims and raw evidence are different artifacts;
they are joined by provenance and entity/claim ids, not collapsed into one
truth table.

## Relationship To Memory

Feature 012 keeps owning personal raw evidence, derived personal memory,
Hindsight KG-like memory internals, MemPalace loci/episodic recall, context
assembly and KB/world boundary policy. Feature 017 owns global/domain KG claims
and KG retrieval once a fact/relation is promoted beyond raw memory/world
evidence.

Memory can propose KG claims, but it must not silently promote them. Promotion
requires provenance, status and conflict checks. KG hits used in answers must
surface freshness, status and evidence refs.

## Bitemporal Pattern Adopted

Adopt:

- `valid_period` or equivalent for business time.
- `sys_from/sys_to` or append-only revisions for system time.
- pgvector embeddings on claim text or canonical relation text.
- decay scoring during retrieval, not hard deletion.
- separate access telemetry for recency/access signals.

Do not adopt blindly:

- one table for raw evidence, derived memory and KG claims.
- triggers that truncate overlapping valid periods without split handling.
- mutating claim rows on every access.
- unproven single `entity_key` as the whole conflict key.

## Hybrid Graph-Vector Pattern Adopted

Adopt:

- vector retrieval for high-recall chunk candidates.
- KG retrieval for canonical entities, bitemporal claims and short paths.
- late fusion via RRF, then optional cross-encoder/MMR re-ranking.
- graph context as compact explanatory paths, not full subgraphs.
- entity signatures as merge candidates, with review for ambiguous nodes.
- embedding/version metadata for rollback and eval comparisons.

Do not adopt blindly:

- graph DB as a second source of truth before Postgres claim semantics are
  proven.
- entity merge by embedding fingerprint alone.
- TTL as hard delete for auditable facts.
- prompt stuffing with large graph neighborhoods.

## Closeout Criteria

- KG schema has bitemporal claim/edge semantics and provenance backlinks.
- Access/decay scoring is implemented without hot-updating claim rows.
- Hybrid graph-vector retrieval has deterministic fusion tests.
- Memory-Fusion can propose claims, but promotion is explicit and auditable.
- Control UI can show KG claim status, temporal validity and evidence refs.
