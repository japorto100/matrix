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

- T010 [partial-done] Define source artifact fields: source id, source URI,
  fetch method, content hash, MIME/type, fetched_at, valid_from/to if known,
  license/source policy and parser version.
  - 2026-04-27: Alembic migration `031_ingestion_source_artifacts` adds
    `ingestion.source_artifacts` with source URI/kind/fetch method, content
    hash, MIME, parser/chunker/embedding metadata and JSON metadata.
  - Remaining: license/source-policy and explicit citation rows.
- T011 [done-static] Define citation/provenance metadata for papers, URLs,
  filings, API payloads and local docs.
  - 2026-04-27: `DocumentPipeline` now attaches `source_artifact` and
    per-chunk `chunk_metadata` with source URI, parser/version, content hash,
    chunk hash, section/page fields and `citation_ref`.
- T012 [done-static] Keep raw artifacts immutable; derived chunks, embeddings
  and KG proposals are rebuildable projections.
  - 2026-04-27: source artifacts remain durable provenance rows; chunk IDs and
    citation refs are deterministic projections from artifact id, chunk index
    and chunk text.
- T013 [done] Add Alembic-backed schema changes if new persistent artifact
  fields are needed; do not create ad hoc schema-only Python tables.
  - 2026-04-27: source artifact registry added through Alembic and
    `SourceArtifactRegistry`.

## Pipeline

- T020 [partial-done] Implement or normalize connector contract for local
  files, URL/web fetches, arXiv/paper URLs and structured API payloads.
  - 2026-04-27: `ingestion.cli ingest-file` now supports local files without
    SeaweedFS/Go via `DocumentPipeline.run_local_path`.
  - Remaining: URL/arXiv/API connectors and durable source artifact registry.
- T021 [done-static] Implement parser registry with explicit parser/version
  metadata.
  - 2026-04-27: selected extractor name and document schema version flow into
    `source_artifacts` and per-chunk metadata for both local-file and
    Matrix-file document paths.
- T022 [done-static] Implement chunking contract with deterministic chunk ids
  and citation refs.
  - 2026-04-27: document chunks receive stable IDs of
    `<artifact-prefix>-<chunk-index>-<chunk-hash-prefix>` before embedding and
    sink writes; Hindsight metadata now carries the same source/citation refs.
- T023 [done-static] Wire remote embedding provider config from Feature 019;
  local HF model downloads remain opt-in and use
  `HF_HOME=/mnt/cold-storage/models/huggingface`.
  - 2026-04-27: `IngestionConfig` reads `EMBEDDER_PROVIDER`,
    `EMBEDDER_MODEL`, `EMBEDDER_BASE_URL` and `EMBEDDER_API_KEY`, with
    OpenRouter/OpenAI-compatible fallbacks. `EmbedderRegistry` exposes
    `openrouter` and deterministic providers; local sentence-transformers stays
    opt-in and uses HDD `HF_HOME` cache.
- T024 [done-static] Emit KG `ClaimProposal` objects for extraction outputs,
  but do not promote claims automatically.
  - 2026-04-27: `KGSink` now calls the KG pipeline `/propose` path rather than
    raw `/extract` when KG is enabled, passes `persist=false`, and treats
    returned proposals as candidate output only.
- T025 [done-static] Reuse ingestion chunk embeddings and source artifact refs
  as KG evidence inputs; KG may add canonical entity/claim embeddings, but must
  not duplicate the entire RAG vector store into the graph backend.
  - 2026-04-27: `KGSink` forwards per-chunk source metadata plus
    `embedding_dim`, `embedding_reused_as_evidence_input=true` and
    `kg_persist=false` into `evidence_metadata_by_ref`; it does not copy
    embedding vectors into the graph path.
- T026 Add parser adapter plan for PyMuPDF4LLM baseline, Docling SOTA candidate
  and MinerU heavy/complex-PDF candidate.
- T026a [done-static] Add Microsoft MarkItDown as a lightweight parser
  candidate for Office, HTML, simple PDFs and MCP-style conversion workflows;
  keep it behind the same extraction benchmark gates as the other parsers.
  - 2026-04-27: `MarkItDownExtractor` is registered as optional
    `markitdown` extractor. It does not change the default PDF extractor and
    does not add a hard dependency; selecting it requires the `markitdown`
    package to be installed. It supports current MarkItDown API output via
    `result.text_content` with a `result.markdown` fallback.
  - Source check: Microsoft/PyPI current docs describe `MarkItDown().convert`
    and `result.text_content`; PyPI shows a 2026-02-20 upload.
- T027 Preserve hierarchy/page/table/figure/formula/code metadata through
  chunking and citation refs.
- T028 Prefer structured trading/finance inputs such as XBRL/CSV/API over PDF
  extraction when available.
- T029 Feed parser/chunking configs into Feature 023 inner-loop experiments.
- T029a Maintain a source-date classification in Feature 021/019/023 docs:
  2026 papers and current official docs are decision evidence; older papers are
  method references unless validated by current repo state and local benchmark.
- T029b Add a source-grounding implementation pack: immutable source artifact,
  parser registry, hierarchy-aware chunker, citation refs, embedding metadata
  and optional KG proposal emission must be testable as one pipeline before
  external GraphRAG candidates are judged.
  - 2026-04-27: Feature 022 canaries now require selected references to retain
    source artifact/chunk/citation/parser metadata, making this implementation
    pack enforceable in retrieval benchmarks.

## Verification

- T030 [done-static] Unit-test artifact id/hash stability.
  - 2026-04-27: local ingestion test verifies stable local `file_id`, chunk
    hash manifest write and no storage-service dependency.
- T031 [done-static] Unit-test chunk/source/citation refs.
  - 2026-04-27: local ingestion test asserts stable chunk id prefix,
    `source_artifact_id`, `source_uri` and `citation_ref`.
- T032 [done-static] Unit-test optional KG proposal evidence refs.
  - 2026-04-27: `proposals_from_extraction()` accepts
    `evidence_metadata_by_ref` and preserves `source_artifact_id`, `chunk_id`,
    `chunk_hash`, `citation_ref`, page and parser/chunker metadata in
    `EvidenceRef.metadata`; test covers source URI override from chunk metadata.
  - 2026-04-27: `ingestion.tests.test_kg_sink` verifies the ingestion sink
    sends source-grounded KG proposals with `persist=false`, embedding
    dimension/reuse metadata and no vector-store duplication.
- T033 [done] Live-smoke local paper ingestion using
  `docs/papers/knowledgegraph/Do We Still Need GraphRAG Benchmarking RAG and GraphRAG for Agentic Search Systems arXiv 2604.09666.md`.
  - 2026-04-27: CLI local-file smoke passed against Postgres with
    `EMBEDDER_PROVIDER=deterministic`, `KG_PIPELINE_ENABLED=false`,
    `--sinks kg`; markdown MIME override confirmed.
  - 2026-04-27: specific GraphRAG paper MD ingested as job
    `3fe95fde-5161-486a-b562-7470ebcad692`, status `done`, 6 chunks,
    `ingestion.chunk_hashes` refs written. Source artifact
    `c38f45c6-2595-5518-a78f-0b509a6eea09` written for the local file URI.
    PDF/full retrieval smoke remains covered by LV004/Feature 019 rather than
    this local-ingest gate.
- T034 Live-smoke one URL or arXiv-source ingest when network/API keys allow.
- T035 [partial-done] Meta-Harness scenario: user asks for paper-grounded answer; trace must
  show retrieval/citation path, not memory-only answer.
  - 2026-04-27: Feature 022 now includes `source-provenance-001`, a
    source-grounding canary whose generated answer must cite the exact
    `chunk-source-provenance` reference. Real agent trace remains open.
- [x] T036 Add real PDF extraction benchmark using ResearchWatcher
  PDF/Markdown ground-truth fixture so Meta-Harness can evaluate parser quality
  instead of only synthetic retrieval canaries.
  - 2026-04-27: `meta_harness.extraction_benchmark` compares
    `_ref/Researchwatcher/layout-module/tests/test_assets/Small-pdf-with-text-formula-table-code-picture.pdf`
    against the sibling `.md`, writes `extraction_benchmark.json`,
    `aggregate.json`, `scores.json` and `verdicts.json`.
- T037 Promote extraction benchmark failures into parser/chunker candidates:
  current PyMuPDF4LLM pass has high text recall but weak structured formula,
  figure and code-fence preservation.
- T038 Compare PyMuPDF4LLM vs Docling on the ResearchWatcher fixture and at
  least one financial/research PDF.
- T039 Evaluate MinerU only after resource footprint and install/cache location
  are clear.
- T040 [partial-static] Compare MarkItDown against PyMuPDF4LLM, Docling and MinerU on the
  ResearchWatcher fixture plus one Office-style fixture; promote it only for
  source classes where it preserves citations and structure well enough.
  - 2026-04-27: optional adapter and unit tests exist. Benchmark comparison is
    still open because `markitdown` is not installed as a hard dependency and
    must be run through the same Feature 023 extraction benchmark path.
- T041 Add one current trading/finance or macro PDF fixture so parser
  decisions are not based only on generic benchmark PDFs.
- T042 [done-static-live-smoke] Add a paper/source provenance fixture where the expected answer must
  cite paper id, page/section or chunk refs; this becomes the first
  Meta-Harness source-grounding scenario.
  - 2026-04-27: `SOURCE_PROVENANCE_CANARY` carries source artifact id,
    source URI, chunk id, chunk hash, parser/chunker metadata and
    `citation_ref`; `evaluate_canary()` requires the generated answer to cite
    `[chunk-source-provenance]`.
  - 2026-04-27: deterministic Meta-Harness inner-loop
    `run-inner-rag-provenance-20260427` included this source-grounding
    scenario and passed validation.

## Bugs Found While Implementing

- B001 [done] `python-magic` returned `text/plain` for `.md` files, bypassing
  the Markdown extractor. Detector registry now lets known specific extensions
  override generic `text/plain`/`application/octet-stream` magic results.
- B002 [done] Dedup audit metadata wrote Postgres UUID objects directly and
  could fail JSON serialization. Document and note pipelines now stringify
  `existing_job_id`.
