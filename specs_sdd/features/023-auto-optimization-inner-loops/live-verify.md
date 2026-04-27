---
title: Auto-Optimization Inner Loops Live Verify
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 023
---

# Live Verify

- LV001 [done] Run deterministic RAG optimization smoke over Feature 022 canaries.
  - 2026-04-27:
    `uv run python -m meta_harness.meta_cli inner-loop --kind rag --run-id run-inner-loop-rag-smoke --data-dir ../data/meta_harness`
  - Result: validation passed. Candidates:
    `inner-matrix-vector-only` fitness `0.5` deferred,
    `inner-matrix-kg-only` fitness `0.25` deferred,
    `inner-matrix-fused-vector-kg` fitness `0.9631` promoted to outer loop.
- LV002 [done] Verify artifacts appear under `data/meta_harness/runs/<run>/`.
  - Artifacts written under
    `data/meta_harness/runs/run-inner-loop-rag-smoke/` plus linked retrieval
    run `run-inner-loop-rag-smoke-retrieval`.
- LV003 [done] Verify Pareto sees optimized candidates.
  - 2026-04-27: `meta_harness.meta_cli pareto` after the inner-loop smoke
    reported `has_inner_fused_frontier: true`; the promoted fused candidate
    appears as `run-inner-loop-rag-smoke:inner-matrix-fused-vector-kg`.
- LV004 [done-static-live-smoke] Run parser/chunking optimization smoke over the ResearchWatcher PDF
  fixture.
  - 2026-04-27:
    `uv run python -m meta_harness.meta_cli pdf-extraction-benchmark --run-id run-pdf-extraction-feature023-20260427 --data-dir ../.meta-harness`
  - Result: passed; token recall `0.9091`, phrase coverage `1.0`, table
    count `1`, extracted chars `905`, truth chars `1082`, latency `3532.881ms`,
    fitness `0.9682`.
  - Gap for next inner-loop parser candidates: formula extraction, figure
    extraction and code-fence preservation still fail to appear in the current
    PyMuPDF4LLM output.
- LV005 [done] Verify OpenRouter-free mode refuses to exceed configured request caps.
  - 2026-04-27:
    `meta_harness.meta_cli inner-loop --kind rag --run-id run-inner-loop-blocked-smoke --provider-calls-budget 1`
    returned `blocked: true` and `provider_gate.allowed: false` because
    `META_HARNESS_ALLOW_PROVIDER_CALLS` was not enabled.
- LV006 Verify a promoted candidate can be rerun through a real agent
  Meta-Harness scenario.
- LV007 [done-static-live-smoke] Verify protected benchmark inputs for
  inner-loop candidates.
  - 2026-04-27:
    `uv run python -m meta_harness.meta_cli inner-loop --kind rag --run-id run-inner-rag-splits-20260427 --data-dir ../.meta-harness`
    passed validation and wrote protected-input metadata.
  - Result: `inner-matrix-vector-only` fitness `0.5` deferred,
    `inner-matrix-kg-only` fitness `0.25` deferred,
    `inner-matrix-fused-vector-kg` fitness `0.9631` promoted to outer loop.
  - Generated run artifacts live under ignored local `.meta-harness/`; source
    control tracks the runner, tests and spec evidence, not transient run logs.
- LV008 [done-static-live-smoke] Verify source-grounding canaries participate
  in the deterministic RAG inner-loop.
  - 2026-04-27: `run-inner-rag-provenance-20260427` included
    `source-provenance-001`; the fused candidate stayed promotable while
    vector-only and KG-only remained deferred.
