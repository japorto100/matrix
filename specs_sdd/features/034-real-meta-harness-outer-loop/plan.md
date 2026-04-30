---
title: Real Meta-Harness Outer Loop Plan
status: planned
owner: filip
created: 2026-05-01
updated: 2026-05-01
feature_id: 034
---

# Plan

1. Freeze the smallest useful domain: memory/RAG/tool-routing behavior inside
   the Python agent harness.
2. Use Feature 016 artifacts as the baseline storage/evaluator substrate.
3. Use Feature 023 outputs only as candidate inputs; do not let inner loops
   self-promote.
4. Build the missing real iteration command and ledger.
5. Run a cheap no-browser loop first, then widen budget only after the first
   iteration proves artifact quality.
6. Use browser/Control replay only after backend iteration evidence exists.

The first implementation should optimize a narrow causal failure, not attempt
to improve the whole agent runtime in one candidate.

