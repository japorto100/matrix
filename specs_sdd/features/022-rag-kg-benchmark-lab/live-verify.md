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
- LV004 [done-initial] Run Meta-Harness RAG/KG canary benchmark and inspect
  candidate artifacts.
  - 2026-04-27: `uv run python -m meta_harness.meta_cli rag-benchmark --run-id run-rag-kg-live-devstack`.
  - Artifacts:
    `data/meta_harness/runs/run-rag-kg-live-devstack/candidates/matrix-vector-only/`,
    `.../matrix-kg-only/`, `.../matrix-fused-vector-kg/`.
  - Results: `matrix-vector-only` pass rate `0.5`, Recall@5 `0.5`;
    `matrix-kg-only` pass rate `0.0`, Recall@5 `0.5`;
    `matrix-fused-vector-kg` pass rate `1.0`, Recall@5 `1.0`, nDCG@5
    `0.8155`, fitness `0.9631`.
  - Interpretation: fused retrieval is the only currently feasible candidate
    for trading/geopolitical multi-hop plus plain document QA boundaries.
- LV005 Run OpenRouter embeddings when budget/rate limit allows.
- LV006 Run NornicDB/nonicdb projection smoke when available.
- LV007 Record keep/reject/defer decision per retrieval candidate.
- LV008 [done-static-live-smoke] Verify candidate metadata compatibility gates.
  - 2026-04-27: `uv run python -m meta_harness.meta_cli rag-benchmark --run-id run-rag-metadata-compat-smoke --data-dir ../data/meta_harness`.
  - Artifacts now include `metadata_compatibility` in
    `retrieval_benchmark.json` and `verdicts.json`.
  - Matrix vector-only, KG-only and fused baselines declared source corpus,
    parser, chunker, embedding model/dimension and KG projection version.
