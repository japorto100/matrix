---
title: Auto-Optimization Inner Loops Eval
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 023
---

# Eval

## Metrics

- Retrieval: Recall@k, nDCG@k, citation completeness, unsupported-claim rate.
- Extraction: token recall, heading/table/formula/figure/code preservation,
  parser latency and memory use.
- Memory/context: correct recall, false recall, boundary violations,
  injection usefulness, compaction loss.
- Agent/tool: trace-gate pass rate, tool success rate, consent correctness,
  final task completion.
- Operations: latency, request count, token count, cost and failure class.

## Promotion Rule

An inner-loop candidate can be promoted to Meta-Harness outer-loop only if:

- it beats the current baseline on search-set metrics,
- it does not regress hard negative canaries,
- it stays within budget,
- it writes complete provenance/config artifacts,
- and it has a defined rollback/default.

Outer-loop promotion still requires real Matrix harness evidence.
