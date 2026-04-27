---
title: Ingestion Paperwatcher Research
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Research Notes

Researchwatcher is useful mostly as workflow evidence: it shows how a
paper-focused research product can combine download/search/synthesis/citation
flows and expose them through tests/API/MCP surfaces. Matrix should adopt the
workflow shape, not the whole product architecture.

The important design point is separation:

- ingestion preserves source truth.
- retrieval ranks chunks and citations.
- KG promotion creates bitemporal world/domain claims only after evidence
  gates.
- memory may reference user sessions and prior work, but it is not a document
  ingestion source of truth.
