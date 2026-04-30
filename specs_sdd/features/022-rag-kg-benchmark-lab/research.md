---
title: RAG/KG Benchmark Lab Research
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-30
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

## 2026-04-30 Knowledge Contract Update

The benchmark lab now has an additional provider-free lane:
`meta_harness.knowledge_contract`. It is not a replacement for real retrieval
benchmarks; it is the cross-feature precondition that says a candidate is even
eligible for scoring. It checks memory ground-truth refs, KG proposal evidence,
selected RAG/KG context provenance, semantic ambiguity/permission fail-closed
behavior and correction proposal review state.

This references `Z_Browser_RAG_WebGPU_CPU_Models.md` and
`Z_Semantik_layer and so on.md` by keeping browser/semantic additions as
measured candidate dimensions, not implicit defaults. External LightRAG,
HippoRAG2 and related adapters still need matched-budget benchmarks before
promotion.

## 2026-04-30 Benchmark Transfer

Inputs: Feature 019 lexical/semantic gates, Feature 032 usage telemetry and
Feature 033 runtime events.

Benchmark candidates should capture cost/latency/cache counters and runtime
event completeness alongside retrieval quality. A candidate that improves an
answer metric but loses citation provenance, hides cache misses or fails to
emit downstream artifact events is not promotable without an explicit waiver.

2026-04-30 implementation update: `knowledge-contract` now makes that
downstream condition executable for the provider-free suite. It requires
RAG/KG provenance runtime events and Agent Chat stream artifact filenames for
source lists and KG paths, so a benchmark candidate cannot pass solely by
retrieving or answering correctly.

This keeps RAG/KG/semantic experiments comparable across provider, embedding
and local/offline candidates.
