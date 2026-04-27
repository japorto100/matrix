---
title: Ingestion Paperwatcher Plan
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Plan

1. Inventory Matrix ingestion code and `_ref/Researchwatcher` paperwatcher
   flows.
2. Define source artifact, chunk metadata and citation contracts.
3. Add small local-first ingestion path: local PDF/MD/URL -> artifact -> chunks.
4. Wire embedding jobs to provider-agnostic Feature 019 embedding config.
5. Emit optional KG `ClaimProposal` objects with evidence refs for Feature 017.
6. Add static tests and one live smoke that can run without frontend/Go.
