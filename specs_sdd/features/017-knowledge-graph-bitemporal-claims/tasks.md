---
title: Knowledge Graph Tasks
status: implementation_started
owner: filip
created: 2026-04-26
updated: 2026-04-30
feature_id: 017
---

# Tasks

## Schema

- T000 Define global/domain KG boundary: Feature 017 is for world/trading/
  geopolitical/domain claims, not Hindsight KG-like memory or MemPalace loci.
- T000a Restore the old world-model four-layer mapping in Feature 017:
  Knowledge, Memory, Wisdom and Intelligence, with Feature 017 owning only the
  global KG persistence/promotion parts and context/runtime owning ephemeral
  Intelligence.
- T000b Define Fast Lane vs Slow Lane claim semantics in schema fields:
  temporal/event lane, structural/stable lane, lane-specific TTL/decay/status
  rules and promotion/demotion constraints.
- T001 [done-static] Define KG entity table and canonical entity key strategy.
- T002 [done-static] Define bitemporal claim/relation table with `valid_period`
  and system-version history.
- T003 [done-static] Define evidence backlink table from KG claims to
  Memory-Fusion, Personal KB and World Evidence refs.
- T004 [done-static] Define conflict key semantics beyond a single
  `entity_key`.
- T005 [done-static] Decide whether overlap handling is append-only query logic or explicit
  split-on-insert; do not use lossy truncation triggers.
- T006 [partial-static] Add Wisdom/validation fields or companion tables for adjudication state:
  validation method, validator version, plausibility score, contradiction refs,
  corroboration count and promotion decision.

## Retrieval

- T010 [done-static] Define claim embedding text and embedding dimension
  configuration.
- T010a [done-static] Define RAG/KG vector handoff: KG builders reuse
  ingestion chunk/evidence embedding refs where possible, but store separate
  entity/claim embeddings with explicit `embedding_model`, `embedding_dim` and
  provenance when canonical KG objects need semantic retrieval.
- T011 [done-static-live-smoke] Implement pgvector candidate retrieval for KG claims as a KG-side
  candidate source for Feature 019.
- T012 [done-static] Add decay scoring for recency, validity-end and access
  signals.
- T013 [done-static-live-smoke] Store access telemetry in event/stats tables,
  not as per-query hot updates on claim rows; Feature 019 now records access
  only for KG claims that survive ranking and Context Bubble selection.
- T014 [done-static-live-smoke] Add answer-time KG context metadata: status,
  freshness, confidence and provenance refs.
- T015 [done-static] Define vector chunk metadata contract: `chunk_id`, `source_uri`,
  `embedding_version`, ingest timestamp, TTL/validity metadata and candidate
  entity signatures.
- T016 [done-static-live-smoke] Expose KG entity/claim/path expansion API for
  Feature 019 fused retrieval.
- T017 [done-static] Define deterministic KG candidate ordering before Feature
  019 fusion.
- T018 Coordinate optional cross-encoder/MMR hooks with Feature 019.
- T019 [done-static-live-smoke] Add KG context output for compact graph paths
  plus claim/source attribution.
- T019a [partial-static-live-smoke] Add lane-aware retrieval policy: Fast Lane
  favors freshness and temporal decay; Slow Lane favors stability/confidence
  and GraphMERT/adjudication status; Intelligence/current-context stays outside
  KG retrieval unless explicitly requested as runtime context.

## Memory/KG Boundary

- T020 [partial-static] Wire Memory-Fusion as a claim proposal source, not an
  automatic KG promotion path.
  - 2026-04-30: `knowledge-personal-memory-kg-promotion-blocked` now fails the
    static contract when personal memory lacks evidence/citation/bitemporal
    metadata or review requirement. Runtime write-policy enforcement remains
    open.
- T021 [partial-static] Require raw evidence refs before a derived memory fact
  can become a KG claim.
  - 2026-04-30: the same provider-free contract requires `evidence_refs`,
    `source_artifact_id`, `chunk_id`, `chunk_hash` and `citation_ref` on KG
    proposals.
- T022 Keep personal memory, Hindsight KG-like memory, MemPalace loci, Personal
  KB and global/world KG namespaces separate in write policy and degradation
  flags.
  - 2026-04-30: static contract coverage exists for personal memory -> KG
    promotion blocking; full runtime namespace enforcement remains open.
- T023 [done-static-live-smoke] Add correction scenarios where old KG claims remain historically
  visible but are not retrieved as current truth.

## GraphMERT / Wisdom Validation

- T024 [done-static] Define GraphMERT as optional async L6 validator after IE and claim
  reification, not inline retrieval and not a source of truth.
- T025 [done-research] Evaluate `_ref`/upstream GraphMERT implementation and
  whether a usable checkpoint exists for financial/geopolitical/domain KG, or
  whether only a stub/eval contract is realistic for now.
- T025a [done-research] Record current finding: official
  `jha-lab/graphmert_umls` exposes code and HF datasets but no confirmed public
  model checkpoint; community Finance repo `Nelumbium-Capital/GraphMert` is
  small/reference-grade, not production evidence.
- T026 [done-static] Define GraphMERT input/output contract: `(head, relation) -> tail`
  plausibility, negative sampling, score threshold, validator version and
  evidence refs.
- T027 [done-static] Add GraphMERT/Wisdom promotion rules: GraphMERT score can support or
  demote Slow Lane claims, but cannot override missing provenance, explicit
  contradictions or human review gates.
- T028 [done-static] Add canary eval for GraphMERT/validator: obvious valid structural
  triples, hard negatives, temporal false positives and domain-shift examples.

## Projection And UI

- T030 [partial-static] Define rebuildable graph projection contract with
  nonicdb/NornicDB as the first global KG candidate; FalkorDB/Neo4j remain
  alternatives only if the first path fails requirements.
- T030a Evaluate `_ref/NornicDB` as a projection target, not as source of
  truth: schema mapping, rebuild procedure, bitemporal/historical reads,
  vector+graph query behavior, backup/restore and failure isolation.
- T030b [partial-static] Add projection-outbox replay smoke: delete/recreate the projection from
  Postgres evidence/claim/source artifacts and prove claim ids, path refs and
  citation refs remain stable enough for Feature 019.
  - 2026-04-27: `GlobalKGStore` now exposes pending projection events and a
    deterministic replay snapshot for `nornicdb` events. Static tests verify
    claim ids, compact paths, evidence ids and citation refs survive the
    replay contract in memory and, when a DB URL is present, through Postgres.
    Actual delete/recreate of a live NornicDB projection is still open.
- T031 Define Control UI KG claim detail contract.
- T032 Define promotion/demotion review queue behavior.
- T033 Coordinate `/memory/kg` and provenance graph surfaces with Feature 010.
- T034 Define entity merge review behavior for signature-based merge
  candidates.

## Verification

- T040 [done-static-live-smoke] Unit-test bitemporal insert/correction/query semantics.
- T041 [done-static] Unit-test no raw tool output is promoted to KG without
  explicit claim extraction and source refs.
- T042 [partial-static-live-smoke] Unit-test decay ranking with stale, recently
  accessed and expired-valid claims.
- T043 Live-smoke one evidence -> proposed claim -> promoted claim -> KG recall
  path.
- T044 [done-static] Unit-test vector/KG RRF fusion, attribution and selected
  KG-claim access telemetry from Feature 019.
- T045 [partial-static] Eval Recall@k, nDCG, answer faithfulness and latency on a small hybrid
  retrieval canary set.
- T046 [done-static] Verify global KG retrieval is not used as an agent-memory
  rail unless a scenario explicitly requests world/domain KG context.
- T047 [partial-static] Add RAGSearch-style comparison: vector-only, KG-only and fused retrieval
  under matched query, context, model and retrieval budgets; implementation
  owner is Feature 019, KG claim/path source owner is Feature 017.
- T048 [done-static] Add multi-hop trading/geopolitical canaries where global KG/nonicdb is
  expected to improve retrieval stability over dense RAG.
  - 2026-04-27: Feature 022 now includes `nornicdb-projection-replay-001`, a
    static projection canary requiring NornicDB target metadata, projection
    event id, source artifact/chunk/citation refs and the compact sanctions ->
    oil insurance path. Live NornicDB benchmark remains open in Feature 022.
- T049 Track offline KG build/update cost and online latency before promoting
  KG retrieval as default for any query class.
- T049a [partial-static] Verify KG extraction/projection can be rebuilt from source artifacts,
  chunks, embeddings and evidence refs without depending on a second graph DB
  as source of truth.
  - 2026-04-27: KG proposal mapping now preserves ingestion
    `source_artifact_id`, `chunk_id`, `chunk_hash`, `citation_ref`, page and
    parser/chunker metadata in `EvidenceRef.metadata` when extraction is run
    over source-grounded chunks.
  - 2026-04-27: ingestion `KGSink` forwards evidence metadata to `/propose`
    with `persist=false` and records embedding dimension/reuse metadata without
    duplicating vectors into KG.
  - 2026-04-27: `ClaimProposal.projection_payload()` now includes compact
    `evidence_refs` alongside `evidence_ids`, so the outbox payload can carry
    source URI, chunk/citation metadata and content hashes into rebuildable
    graph projections without rereading raw documents first.
- T049b Benchmark NornicDB/nonicdb path retrieval against Postgres-only KG
  candidate search and fused RAG on the same Feature 022 canaries; promote only
  for query classes where it improves path completeness, stability or latency.
- T050 [done-static] Verify GraphMERT/validator is never run on Fast Lane live-event ingest
  inline and cannot block fresh-event availability.
- T051 Verify Fast Lane -> Slow Lane promotion is auditable and evidence-gated:
  multi-source corroboration, time window, contradiction absence and optional
  GraphMERT/Wisdom score.
- T052 [done-static] Add `GlobalKGStore` facade with in-memory smoke mode,
  Postgres writer/search surface and NornicDB projection-outbox writes.
- T053 [done-static] Add KG-pipeline sink that maps extraction relations to
  explicit `ClaimProposal` objects with evidence refs, without automatic
  promotion.
  - 2026-04-27: evidence refs can now carry source artifact/chunk/citation
    metadata from Feature 021, so proposed claims can point back to exact
    source chunks before promotion.
  - 2026-04-27: KG ingestion now uses the `/propose` contract directly from
    `KGSink`, so the default path is proposal-only and non-persistent unless a
    caller explicitly opts into persistence.
- T054 [done-static] Add KG-pipeline `/propose` endpoint that returns
  Feature-017 claim proposals and only persists when explicitly requested.
- T055 [done-static] Add Feature 025 semantic-term links for KG claim types and
  entity classes.
  - 2026-04-30: `knowledge-contract` requires `semantic_term_ids` on KG claim
    proposals and selected KG context items.
- T056 Add Feature 028 visual evidence refs as claim proposal sources, never
  automatic promotions.
- T057 Add Feature 026 browser-local entity/linking candidates as proposal
  hints only.
