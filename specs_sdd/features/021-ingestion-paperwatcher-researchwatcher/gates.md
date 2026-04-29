---
title: Ingestion Paperwatcher Gates
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Gates

## 2026-04-29 Visual/Report/Semantic Follow-Up

- Layout extraction preserves source artifact, page/block and coordinate refs
  for Feature 028.
- Report generation from Feature 027 references ingestion artifacts instead of
  copying unsourced text.
- Semantic concept proposals for Feature 025 remain pending until reviewed.

- Artifact registry writes must be idempotent for the same content hash.
  - 2026-04-27: local source artifact upsert uses stable
    `uuid5(file://resolved_path)` and can write a minimal artifact even when
    the file is skipped as duplicate.
- Parsed chunks must carry source refs and parser/chunker versions.
  - 2026-04-27: `source-provenance-001` asserts source artifact id, source
    URI, chunk id/hash, citation ref and parser/chunker metadata survive into
    retrieval references.
- Embedding jobs must record provider, model, dimension and embedding version.
- KG proposals must include evidence refs and remain `candidate`/`proposed`
  until Feature 017 promotion gates approve them.
  - 2026-04-27: ingestion KG output now enters `/propose` with
    `persist=false`; evidence metadata carries source artifact/chunk/citation
    refs and embedding dimension/reuse flags, but not copied vector payloads.
- No ingestion live smoke may require frontend or Go Gateway.
  - 2026-04-27: verified for local Markdown CLI path with Postgres only.
- Network-dependent paper/API smokes must have local fixture fallback.
- Known text extensions must not be downgraded to generic `text/plain` when
  MIME magic is less specific; parser selection must preserve Markdown/code
  semantics.
