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
- LV002 [partial-done] Ingest the local GraphRAG paper MD/PDF from
  `docs/papers/knowledgegraph/`.
  - 2026-04-27: local Markdown fixture smoke passed through
    `ingestion.cli ingest-file`; specific GraphRAG paper remains as a larger
    source fixture once Feature 019 retrieval sink is ready.
- LV003 [partial-done] Confirm source artifact, chunks and source refs are written.
  - 2026-04-27: `ingestion.jobs` and `ingestion.chunk_hashes` writes verified;
    durable source artifact table is still open.
- LV004 Run retrieval over the ingested chunks through Feature 019.
- LV005 If KG extraction is enabled, confirm outputs are claim proposals only.
- LV006 Run a Meta-Harness paper-grounded scenario and inspect trace/source
  artifacts.

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
