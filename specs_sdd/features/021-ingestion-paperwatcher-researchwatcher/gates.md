---
title: Ingestion Paperwatcher Gates
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Gates

- Artifact registry writes must be idempotent for the same content hash.
  - 2026-04-27: local source artifact upsert uses stable
    `uuid5(file://resolved_path)` and can write a minimal artifact even when
    the file is skipped as duplicate.
- Parsed chunks must carry source refs and parser/chunker versions.
  - 2026-04-27: `source-provenance-001` asserts source artifact id, source
    URI, chunk id/hash, citation ref and parser/chunker metadata survive into
    retrieval references.
- Embedding jobs must record provider, model, dimension and embedding version.
- KG proposals must include evidence refs and remain `candidate` until Feature
  017 promotion gates approve them.
- No ingestion live smoke may require frontend or Go Gateway.
  - 2026-04-27: verified for local Markdown CLI path with Postgres only.
- Network-dependent paper/API smokes must have local fixture fallback.
- Known text extensions must not be downgraded to generic `text/plain` when
  MIME magic is less specific; parser selection must preserve Markdown/code
  semantics.
