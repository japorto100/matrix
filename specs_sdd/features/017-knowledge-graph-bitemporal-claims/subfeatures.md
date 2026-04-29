---
title: Knowledge Graph Subfeatures
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 017
---

# Subfeatures

## 017.1 Bitemporal Claim Store

Scope:

- global/domain claims for trading, geopolitical, macro and world-model
  knowledge.
- entities and reified claims/relations as first-class rows.
- valid-time and system-time semantics.
- append-only corrections or safe split logic for overlapping validity windows.
- status machine for candidate, active, superseded, contradicted and rejected.

Design note:

Postgres-first is preferred. The source of truth should be relational and
auditable before any graph-backend projection.

Out of scope:

- Hindsight KG-like agent-memory structures.
- MemPalace loci/episodic links.

## 017.2 Evidence Backlinks And Provenance

Scope:

- claims point to immutable raw evidence refs from Memory-Fusion, Personal KB
  or World Evidence.
- derived KG claims require at least one source ref.
- answer-time KG context includes provenance, freshness and confidence.

Out of scope:

- storing raw tool outputs directly as KG claims.
- silently treating assistant summaries as primary evidence.

## 017.3 Decay And Access-Aware Retrieval

Scope:

- semantic KNN candidates over pgvector.
- recency/validity/access decay in retrieval scoring.
- access events or aggregate stats in separate tables.
- no hot updates to claim rows for every recall.

Initial formula:

`final_score = semantic_similarity * recency_decay * validity_decay * access_decay`

## 017.4 Fast/Slow/Wisdom Lane Model

Scope:

- Fast Lane for temporal/event/world claims with short validity, TTL-like
  query filtering, temporal decay and no inline GraphMERT.
- Slow Lane for stable structural domain claims with longer validity,
  confidence decay, promotion/demotion and curated source quality gates.
- Wisdom lane for adjudication: multi-source corroboration, contradiction
  checks, conflict handling and optional GraphMERT batch validation.
- Intelligence remains non-persistent runtime reasoning and prompt context; it
  must not be stored as global KG truth.

GraphMERT role:

- candidate batch validator after claim reification, only for Slow Lane
  triples and structural relation checks;
- may score plausibility or tail-prediction, but may not promote claims without
  provenance and status checks;
- first implementation may be a stub/eval contract until a domain-specific
  model/checkpoint exists.

## 017.5 Graph Projection

Scope:

- optional projection from Postgres claim source to nonicdb/NornicDB first;
  FalkorDB, Neo4j or another graph backend remain fallback candidates.
- projection is rebuildable and never the only truth source.
- Fast Lane temporal/event claims vs Slow Lane structural validated claims.

## 017.6 KG Control Surface

Scope:

- claim details: status, valid period, system version, confidence.
- evidence backlinks and conflict history.
- graph view for entities/relations.
- promotion/demotion review queue.

## 017.7 Hybrid Graph-Vector Retrieval

Scope:

- vector candidates from pgvector/vector store with `embedding_version`,
  source refs, TTL/validity metadata and entity signatures.
- KG candidates from canonical entities, bitemporal claims and short graph
  paths.
- late fusion using RRF as the first deterministic baseline.
- optional cross-encoder/MMR re-ranking after RRF.
- context builder emits selected chunks plus compact graph paths and
  attribution refs.

Rules:

- Vector chunks are evidence/context artifacts, not truth.
- KG claims remain status-managed and source-linked.
- Graph backend projections are rebuildable indexes over Postgres claim state.
- Entity signatures create merge candidates; ambiguous merges require review.
