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
- LV007 [done-static-live-smoke] Record keep/reject/defer decision per
  retrieval candidate.
  - 2026-04-27:
    `uv run python -m meta_harness.meta_cli rag-benchmark --run-id run-rag-kg-decisions-20260427 --data-dir ../.meta-harness`
    passed and wrote decision logs for KG-bearing candidates.
  - Results: `matrix-vector-only` pass_rate `0.6667`, no graph decision;
    `matrix-kg-only` pass_rate `0.0`, fitness `0.1666`, decision `defer`;
    `matrix-fused-vector-kg` pass_rate `1.0`, fitness `0.9754`, decision
    `defer` because this run intentionally used only the `search` split and
    promotion requires holdout evidence.
- LV008 [done-static-live-smoke] Verify candidate metadata compatibility gates.
  - 2026-04-27: `uv run python -m meta_harness.meta_cli rag-benchmark --run-id run-rag-metadata-compat-smoke --data-dir ../data/meta_harness`.
  - Artifacts now include `metadata_compatibility` in
    `retrieval_benchmark.json` and `verdicts.json`.
  - Matrix vector-only, KG-only and fused baselines declared source corpus,
    parser, chunker, embedding model/dimension and KG projection version.
- LV009 [done-static-live-smoke] Verify search/holdout split reporting without
  exposing holdout to the default optimization loop.
  - 2026-04-27:
    `uv run pytest tests/test_retrieval_benchmark_lab.py tests/meta_harness/test_meta_cli.py tests/test_retrieval_baseline.py -q`
    passed `40` tests.
  - `compare_candidates(DEFAULT_CANARIES, ...)` reports `splits:
    [holdout, search]`, question classes and per-candidate
    `split_summary`.
  - The default Meta-Harness retrieval benchmark still uses
    `DEFAULT_SEARCH_CANARIES`; holdout canaries are explicit rerun material.
- LV010 [done-static-live-smoke] Verify source artifact/chunk citation in the
  default search canary set.
  - 2026-04-27:
    `uv run pytest tests/test_retrieval_baseline.py tests/test_retrieval_benchmark_lab.py tests/meta_harness/test_meta_cli.py -q`
    passed `41` tests.
  - 2026-04-27:
    `uv run python -m meta_harness.meta_cli inner-loop --kind rag --run-id run-inner-rag-provenance-20260427 --data-dir ../.meta-harness`
    passed validation.
  - Results: `inner-matrix-vector-only` fitness `0.6667` deferred,
    `inner-matrix-kg-only` fitness `0.1666` deferred,
    `inner-matrix-fused-vector-kg` fitness `0.9754` promoted to outer loop.
- LV011 [done-static-live-smoke] Verify projection-replay canary contract before
  live NornicDB execution.
  - 2026-04-27:
    `uv run pytest tests/test_retrieval_benchmark_lab.py -q` passed `8`
    tests.
  - `nornicdb-projection-replay-001` now fails vector-only candidates and
    passes KG candidates only when selected references preserve projection
    target, projection event id, source artifact id, chunk id/hash,
    citation ref and expected compact KG path.
