---
title: Ingestion Paperwatcher Package
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Package

## Current Package / Ist

- `python-backend/ingestion/loaders/`
- `python-backend/ingestion/detectors/`
- `python-backend/ingestion/extractors/`
- `python-backend/ingestion/chunkers/`
- `python-backend/ingestion/embedders/`
- `python-backend/ingestion/sinks/`
- `python-backend/ingestion/tracking/`

## Proposed Package / Soll

- Add parser adapters without making Docling/MinerU hard runtime dependencies
  for every dev stack.
- Store parser version and output format in source artifact metadata.
- Keep raw artifacts immutable; chunks, embeddings and KG proposals are
  rebuildable.
- Feed parser/chunking configs to Feature 023 rather than hardcoding a single
  winner before benchmarks.
