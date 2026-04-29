---
title: Knowledge Graph, Bitemporal Claims and Decay Retrieval
status: implementation_started
owner: filip
created: 2026-04-26
updated: 2026-04-27
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

The old world-model plan also included a four-layer cognitive mapping and a
GraphMERT validation lane. That is not yet represented strongly enough in this
feature. Feature 017 therefore also owns the global KG interpretation of:

- `Knowledge`: stable shared domain/structural KG, primarily Slow Lane.
- `Memory`: temporal world/event KG, primarily Fast Lane; personal memory stays
  in Feature 012.
- `Wisdom`: evidence-gated validation/adjudication over claims. GraphMERT is a
  candidate batch validator here for Slow Lane triples.
- `Intelligence`: ephemeral reasoning and current prompt context, owned by
  context/runtime features, not persisted as KG truth.

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

Retrieval is hybrid, but answer-time RAG orchestration is owned by Feature 019.
Feature 017 exposes KG claims, paths and provenance for retrieval. Vector
chunks, KG claims and raw evidence are different artifacts; they are joined by
provenance and entity/claim ids, not collapsed into one truth table.

KG construction reuses the RAG/Ingestion evidence layer instead of creating an
isolated duplicate corpus. Source artifacts produce immutable chunks and chunk
embeddings; KG extraction links entities/claims back to those chunks and may
store additional canonical entity/claim embeddings for graph retrieval. Chunk
vectors are reused by id and embedding version, while KG vectors remain
separate because entity/claim text, validity windows, confidence and conflict
keys have different lifecycle and ranking semantics.

## Fast Lane, Slow Lane And GraphMERT

Feature 017 is not a single monolithic KG. It has at least two global lanes plus
clear boundaries to personal overlays:

- Fast Lane: temporal events and live world facts such as ACLED/GDELT/news,
  sanctions, macro prints and market-relevant appointments. It uses short
  validity/TTL windows, temporal decay and quick claim status transitions.
  GraphMERT is not used inline here.
- Slow Lane: structural domain knowledge such as game-theory stratagems,
  geopolitical power patterns, sector/supply-chain relations, macro-regime
  features and curated research. It uses longer validity windows, confidence
  decay and explicit promotion/demotion.
- Wisdom/validation lane: asynchronous evidence-gated validation. GraphMERT is
  a candidate L6 batch validator for Slow Lane triples after IE, claim
  reification and source checks. It should support tail-prediction,
  structural plausibility checks and demotion of unlikely triples, but it is not
  a source of truth by itself.
- Personal KG overlays remain outside Feature 017 unless they are rendered as
  separate user annotations over global KG ids. They do not become global truth
  through user interest alone.

The old execution plan's IE pipeline remains the intended shape:

`source -> normalize -> entity linking/NER -> relation extraction -> postprocess -> claim reification -> optional GraphMERT validation`

GraphMERT is therefore planned after initial KG build and extraction, not as a
blocking dependency for the first Postgres claim schema. As of 2026-04-27, no
public official `jha-lab/graphmert_umls` model checkpoint is confirmed; the
official repo publishes code and datasets, while checkpoints are produced by
training.

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
- explicit correction flow: close overlapping current system versions and mark
  them `superseded`, then insert the corrected claim as a new current version.
  Historical rows remain queryable for audit, while retrieval filters current
  truth to `sys_to = infinity` and active statuses.

Do not adopt blindly:

- one table for raw evidence, derived memory and KG claims.
- triggers that truncate overlapping valid periods without split handling.
- mutating claim rows on every access.
- unproven single `entity_key` as the whole conflict key.

## Hybrid Graph-Vector Handoff

Feature 017 adopts the KG-side contract and delegates answer-time orchestration
to Feature 019:

- KG retrieval for canonical entities, bitemporal claims and short paths.
- graph context as compact explanatory paths, not full subgraphs.
- source artifact, chunk, evidence and embedding refs from Feature 021 are the
  rebuildable input for KG proposals; KG projection must not require copying
  every RAG chunk vector into the graph backend.
- selected claims can be expanded through `GlobalKGStore.expand_claim_context`
  into subject/object identity, path, evidence refs and context metadata without
  requiring a live graph backend projection.
- entity signatures as merge candidates, with review for ambiguous nodes.
- embedding/version metadata for rollback and eval comparisons.

Do not adopt blindly:

- graph DB as a second source of truth before Postgres claim semantics are
  proven.
- entity merge by embedding fingerprint alone.
- TTL as hard delete for auditable facts.
- prompt stuffing with large graph neighborhoods.
- making graph retrieval the default for all RAG queries without Feature 019
  eval evidence.

## Closeout Criteria

- KG schema has bitemporal claim/edge semantics and provenance backlinks.
- Fast Lane, Slow Lane, Wisdom/GraphMERT and non-persistent Intelligence
  boundaries are explicit in schema, retrieval and promotion code.
- Access/decay scoring is implemented without hot-updating claim rows.
- Hybrid graph-vector retrieval has deterministic fusion tests.
- Memory-Fusion can propose claims, but promotion is explicit and auditable.
- Control UI can show KG claim status, temporal validity and evidence refs.
