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
- Parsed chunks must carry source refs and parser/chunker versions.
- Embedding jobs must record provider, model, dimension and embedding version.
- KG proposals must include evidence refs and remain `candidate` until Feature
  017 promotion gates approve them.
- No ingestion live smoke may require frontend or Go Gateway.
  - 2026-04-27: verified for local Markdown CLI path with Postgres only.
- Network-dependent paper/API smokes must have local fixture fallback.
- Known text extensions must not be downgraded to generic `text/plain` when
  MIME magic is less specific; parser selection must preserve Markdown/code
  semantics.
