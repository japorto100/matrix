---
title: Knowledge Graph Research Notes
status: draft
owner: filip
created: 2026-04-26
updated: 2026-04-27
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

## Four-Layer Cognitive Mapping

The old `exec-world-model.md` imported Roynard's four-layer decomposition from
`arXiv:2604.11364` and mapped it to Matrix:

- Knowledge: stable shared world/domain knowledge -> Slow Lane KG.
- Memory: temporal, episodic and personal facts -> Fast Lane world KG for
  global events, while personal episodic memory stays in Feature 012.
- Wisdom: evidence-gated validation and adjudication -> claim promotion,
  contradiction handling and GraphMERT-style validation.
- Intelligence: ephemeral reasoning/context -> runtime context, not KG truth.

This matters because a single graph/vector store with one decay policy will
mishandle at least some of the layers. Feature 017 should encode lane and
status explicitly instead of treating all claims as one generic `facts` table.

## GraphMERT As Wisdom Validator

`main_docs/root/MEMORY_ARCHITECTURE.md` and
`specs/execution/exec-world-model.md` both treat GraphMERT as Phase 2 / L6:
after entity linking, relation extraction, post-processing and claim
reification. The adopted role is:

- Slow Lane only; no inline use for Fast Lane live events.
- asynchronous batch validation/refinement, not a serving dependency.
- tail-prediction and structural plausibility checks over candidate triples.
- demotion/support signal for claims, not automatic truth promotion.
- versioned validator output attached to provenance and promotion decisions.

Current checkpoint finding:

- official Hugging Face search for GraphMERT/graphmert/jha-lab GraphMERT
  returns datasets, not model repos.
- official `jha-lab/graphmert_umls` README says `predict_tails.py` requires a
  trained checkpoint and documents training producing checkpoints in
  `output_dir`.
- community repos exist, including `Nelumbium-Capital/GraphMert` for finance
  KG, but visible signals are small/reference-grade rather than proven
  production checkpoints.

Open constraints:

- no confirmed domain checkpoint for financial/geopolitical Matrix KG.
- likely needs hard negatives and domain-specific fine-tuning/eval before it is
  more than a stubbed validation contract.
- promotion still requires provenance, multi-source corroboration, contradiction
  checks and possibly human review.

## Candidate Backends

Postgres is the first source of truth. nonicdb/NornicDB is the first global KG
projection/backend candidate because it is already present in `_ref/NornicDB`
and aligns with the NornicDB paper/doc lane. FalkorDB, Neo4j or another graph
backend remain alternatives if traversal/query ergonomics justify them after
the schema is proven.

NornicDB adoption boundary:

- use it as a rebuildable projection/query backend for global/domain KG.
- do not make it the authoritative claim store until local durability,
  rebuild, query and operational behavior are proven.
- do not use it as an agent-memory KG rail. Hindsight KG-like memory and
  MemPalace loci stay in Feature 012.
- benchmark hybrid vector+graph+history reads against Postgres-only baselines
  before enabling it by default.

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

Feature 019 now owns the answer-time RAG implementation and GraphRAG candidate
benchmarking. Feature 017 remains responsible for the KG claim/path source.
