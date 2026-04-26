---
title: Knowledge Graph Research Notes
status: draft
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 017
---

# Research Notes

## Bitemporal + Decay Pattern

Adopt the useful parts of the Postgres pattern:

- bitemporal claims combine business validity with system-version history.
- pgvector can provide a Postgres-only first KNN candidate set.
- recency, validity-end and access decay belong in retrieval ranking.
- corrections should preserve audit history instead of updating in place.

Refinements for Matrix:

- use separate evidence, claim and access telemetry tables.
- avoid a single generic `facts` table for raw memory plus KG.
- avoid lossy overlap triggers; use append-only revisions or safe split logic.
- use claim status and source refs as first-class retrieval filters.

## KG Relevance To Memory

The KG feature depends on Feature 012 for evidence and context, but owns graph
semantics. Memory-Fusion can retain raw/verbatim evidence and derived memory;
KG promotion should happen only when a claim is explicit, sourced and
status-managed.

Hindsight KG-like memory and MemPalace loci/episodic links are not this KG.
They are agent-memory internals owned by Feature 012. Feature 017 is only the
global/domain claim graph used for world, trading, geopolitical and macro
knowledge.

## Candidate Backends

Postgres is the first source of truth. nonicdb/NornicDB is the first global KG
projection/backend candidate because it is already present in `_ref/NornicDB`
and aligns with the NornicDB paper/doc lane. FalkorDB, Neo4j or another graph
backend remain alternatives if traversal/query ergonomics justify them after
the schema is proven.

## Dual Store Blueprint

Adopt the hybrid retrieval idea as an implementation pattern, not as a second
truth model:

- vector store: high-recall chunks with embedding version, source refs,
  TTL/validity metadata and entity signatures.
- KG store: canonical entities, bitemporal claims and typed relations.
- fusion: vector and KG candidates are retrieved separately, combined with RRF
  and optionally re-ranked.
- context: selected chunks plus compact graph paths, never whole subgraphs.

Entity signatures are useful for proposing merges, but not enough for automatic
canonicalization. For Matrix, signatures should include normalized name, domain,
aliases/source hints and embedding fingerprint; ambiguous merges go to review.

## RAGSearch / Agentic Search Benchmark

`arXiv:2604.09666` adds an important constraint to Feature 017: global KG must
earn its cost against a dense-RAG plus agentic-search baseline. The paper's
RAGSearch benchmark treats dense RAG and GraphRAG as retrieval backends under
the same agentic control loop and reports answer quality, offline build cost,
online efficiency and stability.

Matrix adoption:

- vector-only, KG-only and fused retrieval must run under matched query,
  context and model budgets.
- global KG/nonicdb is expected to matter most for relational, multi-hop and
  temporal trading/geopolitical questions.
- dense vector retrieval plus agentic decomposition remains the baseline for
  simple/general QA.
- KG promotion/closeout should include cost and latency evidence, not only a
  correctness demo.
