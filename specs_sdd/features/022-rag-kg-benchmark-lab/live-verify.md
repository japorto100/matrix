---
title: RAG/KG Benchmark Lab Live Verify
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 022
---

# Live Verify

- LV001 Start Postgres and Python backend.
- LV002 Seed canary documents and KG claims.
- LV003 [done-initial] Run vector-only, KG-only and fused Matrix retrieval.
  - 2026-04-27: deterministic canary report:
    `matrix-vector-only` pass_rate `0.5`, Recall@5 `0.5`;
    `matrix-kg-only` pass_rate `0.0`, Recall@5 `0.5`;
    `matrix-fused-vector-kg` pass_rate `1.0`, Recall@5 `1.0`, nDCG@5 `0.8155`.
  - Artifact smoke wrote `/tmp/matrix-rag-kg-benchmark-report.json`.
- LV004 Run Meta-Harness RAG/KG canary scenarios and inspect trace gates.
- LV005 Run OpenRouter embeddings when budget/rate limit allows.
- LV006 Run NornicDB/nonicdb projection smoke when available.
- LV007 Record keep/reject/defer decision per retrieval candidate.
