---
title: Memory Context World Personal KB Decisions
status: accepted
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
---

# Decisions

## D012-001: First World Model Slice

Accepted first slice: start with relational Postgres tables for world evidence
and claims, then bridge to a graph backend only after the evidence -> claim ->
answer-time smoke is proven.

Minimum schema concepts:

- `world_evidence`: source URI or document id, extracted text/span, timestamp,
  source type, confidence, provenance metadata.
- `world_claim`: normalized claim text, status (`candidate`, `supported`,
  `contested`, `deprecated`), confidence, subject/entity keys, timestamps.
- `world_claim_evidence`: many-to-many claim/evidence links with relation
  (`supports`, `contradicts`, `mentions`) and extractor metadata.

Deferred: Graphiti/Cognee/native KG backend selection. They remain candidates
for the second slice, not the first storage dependency.

## D012-002: First Personal KB Slice

Accepted first slice: use the existing Files/ingestion surface as the Personal
KB namespace and store KB entries as user-scoped documents/chunks, not personal
memory facts.

Minimum store concepts:

- `kb_document`: user id, namespace, source type (`note`, `link`, `file`,
  `markdown`), title, source URI/path, status, created/updated timestamps.
- `kb_chunk`: document id, text, chunk index, embedding/vector reference,
  metadata.
- `kb_annotation`: document/chunk id, label, highlight/span, note, pinned flag.

Deferred capture flows: YouTube/podcast transcripts and PKM/bookmark bulk
import. First live slice should cover note/link/file because Feature 010 already
has Files/Memory surfaces to anchor them.

## D012-003: Context Retrieval Policy

Accepted policy: Personal KB and World Model enter the prompt through dedicated
context layers with provenance labels. They do not write into personal memory by
default and must preserve source/status metadata when summarized.
