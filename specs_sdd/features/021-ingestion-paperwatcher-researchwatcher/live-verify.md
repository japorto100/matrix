---
title: Ingestion Paperwatcher Live Verify
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Live Verify

- LV001 [done-partial] Start Postgres and Python backend.
  - 2026-04-27: Postgres on `:5433` available; no Go/frontend needed for the
    local CLI path.
- LV002 [done-md] Ingest the local GraphRAG paper MD/PDF from
  `docs/papers/knowledgegraph/`.
  - 2026-04-27: local Markdown fixture smoke passed through
    `ingestion.cli ingest-file`; this caught and fixed the Markdown MIME
    fallback issue before the real paper smoke.
  - 2026-04-27: specific GraphRAG paper MD ingested through the same CLI path;
    PDF/full retrieval path remains open under LV004.
- LV003 [partial-done] Confirm source artifact, chunks and source refs are written.
  - 2026-04-27: `ingestion.jobs`, `ingestion.chunk_hashes` and
    `ingestion.source_artifacts` writes verified.
  - Remaining: explicit citation/source-span rows are still open.
- LV004 Run retrieval over the ingested chunks through Feature 019.
- LV005 If KG extraction is enabled, confirm outputs are claim proposals only.
- LV006 Run a Meta-Harness paper-grounded scenario and inspect trace/source
  artifacts.
- LV007 [done] Run ResearchWatcher PDF extraction benchmark against Markdown
  ground truth.
  - 2026-04-27: `uv run python -m meta_harness.meta_cli pdf-extraction-benchmark --run-id run-pdf-extraction-live-devstack`
  - Artifact:
    `data/meta_harness/runs/run-pdf-extraction-live-devstack/candidates/pymupdf4llm-pdf-extraction/extraction_benchmark.json`.
  - Result: passed; token recall `0.9091`, phrase coverage `1.0`, page count
    `1`, table count `1`, extracted chars `905`, truth chars `1082`, latency
    about `3.55s`.
  - Gap captured for next parser candidates: no structured formula extraction,
    no figure count and no code fence in the extracted Markdown for this
    fixture.

## 2026-04-27 Local CLI Smoke

Command shape:

```bash
EMBEDDER_PROVIDER=deterministic KG_PIPELINE_ENABLED=false \
  uv run python -m ingestion.cli ingest-file \
  --path /tmp/matrix-local-ingest-smoke.md \
  --user meta-harness \
  --tags feature21 local-smoke markdown \
  --sinks kg
```

Observed:

- `detected mime=text/markdown`
- `chunked ... into 2 chunks`
- `sink kg: written=0 skipped=2 failed=0`
- final job status `done`

## 2026-04-27 GraphRAG Paper MD Smoke

Source:

`docs/papers/knowledgegraph/Do We Still Need GraphRAG Benchmarking RAG and GraphRAG for Agentic Search Systems arXiv 2604.09666.md`

Observed:

- job `3fe95fde-5161-486a-b562-7470ebcad692`
- `detected mime=text/markdown`
- `chunked ... into 6 chunks`
- `sink kg: written=0 skipped=6 failed=0` because KG extraction was disabled
- DB check: `ingestion.jobs.status=done`, `chunks_total=6`,
  `chunks_done=6`, `metadata.source=local`
- DB check: 6 `ingestion.chunk_hashes` rows written for the job
- DB check: `ingestion.source_artifacts.source_artifact_id`
  `c38f45c6-2595-5518-a78f-0b509a6eea09`, `mime_type=text/markdown`,
  `chunk_count=6`, `embedding_provider=deterministic`
