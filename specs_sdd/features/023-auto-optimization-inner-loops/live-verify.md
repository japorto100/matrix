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
- LV004 Run parser/chunking optimization smoke over the ResearchWatcher PDF
  fixture.
- LV005 [done] Verify OpenRouter-free mode refuses to exceed configured request caps.
  - 2026-04-27:
    `meta_harness.meta_cli inner-loop --kind rag --run-id run-inner-loop-blocked-smoke --provider-calls-budget 1`
    returned `blocked: true` and `provider_gate.allowed: false` because
    `META_HARNESS_ALLOW_PROVIDER_CALLS` was not enabled.
- LV006 Verify a promoted candidate can be rerun through a real agent
  Meta-Harness scenario.
