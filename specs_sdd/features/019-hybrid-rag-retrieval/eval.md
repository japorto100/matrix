---
title: Hybrid RAG Retrieval Eval
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 019
---

# Eval

## Required Comparisons

- Matrix vector-only baseline.
- Matrix KG-only/path baseline.
- Matrix fused vector+KG baseline.
- Hierarchy-aware document RAG baseline.
- LightRAG adapter/baseline.
- HippoRAG2 adapter/baseline after LightRAG feasibility is known.

## Metrics

- Recall@k and nDCG@k over chunk/claim refs.
- Citation completeness and unsupported-claim rate.
- Context Bubble diversity and token cost.
- Multi-hop path completeness for KG queries.
- Regression check for simple document QA where KG should not help.

## Promotion Rule

Fused/graph retrieval can become default only for query classes where it beats
vector-only on holdout and does not regress simple document-grounded QA.
