---
title: Auto-Optimization Inner Loops Closeout
status: open
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 023
---

# Closeout

Partial implementation done, not fully closed.

Done:

- Deterministic RAG retrieval-mode inner-loop can emit typed
  `InnerLoopCandidate` and `InnerLoopRun` artifacts.
- Candidates write Meta-Harness-compatible `aggregate.json`, `scores.json`,
  `verdicts.json`, `config.json`, source snapshot and run manifest.
- Provider-call budget gate blocks live-provider loops unless explicit quota
  env permits them.
- Pareto sees the promoted fused retrieval candidate:
  `run-inner-loop-rag-smoke:inner-matrix-fused-vector-kg`.

Still open:

- Parser/chunking loop over the ResearchWatcher PDF fixture.
- Memory/context loop over Hindsight/MemPalace/Fusion routes.
- Live-provider loop with bounded OpenRouter request caps.
- Holdout separation beyond the current deterministic smoke.
