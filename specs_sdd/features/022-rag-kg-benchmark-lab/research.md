---
title: RAG/KG Benchmark Lab Research
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 022
---

# Research Notes

The local GraphRAG benchmark paper is important because it argues against a
blanket "GraphRAG is always better" rule. Matrix should treat graph retrieval
as a query-class-specific candidate: useful for multi-hop/world-relation
questions, dangerous when it bloats context or loses document nuance.

Initial candidate ordering:

1. Matrix vector-only and fused vector+KG baselines.
2. LightRAG-style practical graph retrieval.
3. HippoRAG2-style associative/multi-hop retrieval.
4. LinearRAG/E2GraphRAG only after setup feasibility is proven.

Production recommendation must come from benchmark evidence, not community
hype or framework size.

## 2026-04-27 Benchmark Update

The benchmark lab must include ingestion quality, not only retrieval mode.
`arXiv:2604.04948` is a warning: a naive GraphRAG setup can lose to basic RAG
when parsing/chunking/metadata are weak. Therefore Feature 022 evaluates
candidate families, not isolated frameworks:

- parser/chunking candidates from Feature 021.
- retrieval/fusion candidates from Feature 019.
- KG/path candidates from Feature 017.
- auto-optimization candidates from Feature 023.

LightRAG is the first external GraphRAG adapter candidate because it is
practical and has an active implementation. HippoRAG2 is still relevant for
associative/multi-hop recall, but should be tested on multi-hop/world-model
goldens rather than generic document QA.

AutoRAG-style optimization belongs in Feature 023. Feature 022 consumes its
candidate artifacts and judges them under matched budgets and holdout sets.

## 2026-04-29 Z_ Follow-Up

The benchmark lab now needs new candidate dimensions:

- browser-local retrieval from Feature 026;
- semantic filters/terms from Feature 025;
- visual-layout evidence from Feature 028;
- report-grounding outputs from Feature 027.

Keep the same rule: every candidate is compared against strong dense/hybrid
baselines under matched budgets before promotion.

2026-04-29 implementation note: the benchmark lab now includes three
cross-feature source-grounding cases derived from the Z-MDs:

- Feature 025 semantic-term case: `semantic-term-tool-success-001`.
- Feature 028 visual-layout case: `visual-layout-source-coordinates-001`.
- Feature 027 report-grounding case: `report-grounding-manifest-001`.

These cases intentionally use the same provider-agnostic canary machinery as
the existing vector/KG/fused comparisons. A candidate passes by preserving
source/citation metadata and citing the selected reference, not by calling a
specific commercial provider.

2026-04-29 parser-derived holdout note: `holdout-hierarchy-aware-parser-001`
adds a protected dense baseline from the ResearchWatcher extraction fixture.
It requires hierarchy-aware chunking metadata, parser candidate profile, page
anchor and table count before graph/fused retrieval can claim an advantage.
