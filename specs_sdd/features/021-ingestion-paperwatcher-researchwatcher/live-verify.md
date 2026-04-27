---
title: Ingestion Paperwatcher Live Verify
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Live Verify

- LV001 Start Postgres and Python backend.
- LV002 Ingest the local GraphRAG paper MD/PDF from `docs/papers/knowledgegraph/`.
- LV003 Confirm source artifact, chunks and source refs are written.
- LV004 Run retrieval over the ingested chunks through Feature 019.
- LV005 If KG extraction is enabled, confirm outputs are claim proposals only.
- LV006 Run a Meta-Harness paper-grounded scenario and inspect trace/source
  artifacts.
