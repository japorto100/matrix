---
title: Ingestion Paperwatcher Tasks
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Tasks

## Researchwatcher Review

- T001 Read `_ref/Researchwatcher/researchwatcher.md` and map workflow pieces
  to Matrix ingestion, RAG and KG boundaries.
- T002 Review `_ref/Researchwatcher/tests/test_researchwatcher*.py` for MCP/API
  smoke patterns that Matrix can reuse.
- T003 Review paperwatcher frontend/API types only as workflow/reference, not
  as a required UI dependency.
- T004 Extract reusable ideas from Researchwatcher citation, synthesis and
  download flows into Matrix contracts.

## Source Artifact Model

- T010 Define source artifact fields: source id, source URI, fetch method,
  content hash, MIME/type, fetched_at, valid_from/to if known, license/source
  policy and parser version.
- T011 Define citation/provenance metadata for papers, URLs, filings, API
  payloads and local docs.
- T012 Keep raw artifacts immutable; derived chunks, embeddings and KG
  proposals are rebuildable projections.
- T013 Add Alembic-backed schema changes if new persistent artifact fields are
  needed; do not create ad hoc schema-only Python tables.

## Pipeline

- T020 [partial-done] Implement or normalize connector contract for local
  files, URL/web fetches, arXiv/paper URLs and structured API payloads.
  - 2026-04-27: `ingestion.cli ingest-file` now supports local files without
    SeaweedFS/Go via `DocumentPipeline.run_local_path`.
  - Remaining: URL/arXiv/API connectors and durable source artifact registry.
- T021 Implement parser registry with explicit parser/version metadata.
- T022 Implement chunking contract with deterministic chunk ids and citation
  refs.
- T023 Wire remote embedding provider config from Feature 019; local HF model
  downloads remain opt-in and use `HF_HOME=/mnt/cold-storage/models/huggingface`.
- T024 Emit KG `ClaimProposal` objects for extraction outputs, but do not
  promote claims automatically.

## Verification

- T030 [partial-done] Unit-test artifact id/hash stability.
  - 2026-04-27: local ingestion test verifies stable local `file_id`, chunk
    hash manifest write and no storage-service dependency.
- T031 Unit-test chunk/source/citation refs.
- T032 Unit-test optional KG proposal evidence refs.
- T033 [partial-done] Live-smoke local paper ingestion using
  `docs/papers/knowledgegraph/Do We Still Need GraphRAG Benchmarking RAG and GraphRAG for Agentic Search Systems arXiv 2604.09666.md`.
  - 2026-04-27: CLI local-file smoke passed against Postgres with
    `EMBEDDER_PROVIDER=deterministic`, `KG_PIPELINE_ENABLED=false`,
    `--sinks kg`; markdown MIME override confirmed.
  - Remaining: run the specific GraphRAG paper MD/PDF after retrieval sink
    contract from Feature 019 is wired.
- T034 Live-smoke one URL or arXiv-source ingest when network/API keys allow.
- T035 Meta-Harness scenario: user asks for paper-grounded answer; trace must
  show retrieval/citation path, not memory-only answer.

## Bugs Found While Implementing

- B001 [done] `python-magic` returned `text/plain` for `.md` files, bypassing
  the Markdown extractor. Detector registry now lets known specific extensions
  override generic `text/plain`/`application/octet-stream` magic results.
- B002 [done] Dedup audit metadata wrote Postgres UUID objects directly and
  could fail JSON serialization. Document and note pipelines now stringify
  `existing_job_id`.
