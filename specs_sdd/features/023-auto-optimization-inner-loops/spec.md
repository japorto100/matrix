---
title: Auto-Optimization Inner Loops
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 023
---

# Auto-Optimization Inner Loops

## Current State / Ist

Matrix has a working Meta-Harness outer loop with scenario runs, trace gates,
candidate artifacts, Pareto ranking and decision ledgers. It also has a small
RAG/KG benchmark writer and deterministic canaries for vector-only, KG-only and
fused retrieval.

What is still missing is a disciplined **inner loop** that proposes and tests
configuration variants before a human or Meta-Harness promoter evaluates them
inside the real agent harness. Current candidate generation is mostly manual:
change chunking, retrieval mode, prompt, memory policy or tool policy, then run
a scenario. That does not scale.

The `_ref/auto-rag-optimizer` project and AutoRAG/AutoRAG-HP literature show a
better shape: keep an experiment log, propose bounded variants, run matched
benchmarks, score them and only promote candidates with evidence.

## Target State / Soll

Feature 023 provides reusable inner-loop optimization infrastructure for:

- RAG retrieval configs: parser, splitter, chunk size, chunk overlap, top-k,
  vector/KG fusion, reranker, citation verifier and context-bubble policy.
- Ingestion/parser configs: PyMuPDF4LLM, Docling, MinerU, hierarchy-aware
  chunking, metadata enrichment and multimodal/table/formula handling.
- Memory/context configs: Hindsight/MemPalace query gates, context budget,
  pre-save/compaction thresholds, recall blend and injection order.
- Tool/skill configs: skill trigger thresholds, tool allow/deny policy,
  candidate tool subset and output transformation policies.
- Agent harness configs: runner variant, dispatcher routing, LangGraph/simple
  parity and provider/model budget settings.

The inner loop must not replace Meta-Harness. It feeds Meta-Harness.

```text
Inner loop:
  propose bounded candidate -> run component eval -> write candidate artifact

Outer loop:
  run candidate in real Matrix harness -> trace gates -> Pareto -> decision
```

## Boundaries

- Do not run unbounded overnight loops on free OpenRouter quota.
- Do not promote a config based only on synthetic canaries.
- Do not let an optimization loop edit product code directly unless a separate
  implementation feature explicitly authorizes it.
- Do not optimize for one metric only. Quality, latency, cost, trace-gate pass
  rate and failure mode must stay visible.

## Relationship To Other Features

- Feature 016 owns Meta-Harness outer-loop mechanics.
- Feature 019 owns runtime retrieval APIs and context assembly.
- Feature 021 owns ingestion/parser/source artifact pipelines.
- Feature 022 owns RAG/KG benchmark lab and retrieval score artifacts.
- Feature 012 owns memory/context policies that can become inner-loop
  candidates.

Feature 023 owns the candidate generation and experiment-log framework that can
be reused by those features.

## Closeout Criteria

- Inner-loop candidate schema is defined and versioned.
- RAG/ingestion optimization can emit Meta-Harness-compatible artifacts.
- Search spaces are bounded and budget-aware.
- At least one RAG config optimization run writes an experiment log and a best
  config.
- Meta-Harness can consume the resulting candidate artifacts and decide
  keep/discard/defer.
