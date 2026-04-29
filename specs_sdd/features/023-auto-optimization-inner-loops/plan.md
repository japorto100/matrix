---
title: Auto-Optimization Inner Loops Plan
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 023
---

# Plan

1. Define candidate/run schema and artifact adapter.
2. Implement deterministic RAG inner-loop over Feature 022 canaries.
3. Add parser/chunking inner-loop over Feature 021 PDF fixture.
4. Feed outputs into Meta-Harness Pareto/decision flow.
5. Add memory/context candidate class only after RAG loop is stable.
6. Add LLM/bandit proposal only after bounded config search works.
