---
title: Auto-Optimization Inner Loops Research
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-30
feature_id: 023
---

# Research

## Working Judgement

Auto-optimization should be its own feature because the pattern is reusable
beyond RAG. It should still be subordinate to Meta-Harness:

- Inner loop optimizes component configurations under matched budgets.
- Meta-Harness outer loop validates candidate behavior in the real agent,
  memory, tool, retrieval and audit harness.

## `_ref/auto-rag-optimizer`

The local reference is a compact Karpathy/autoresearch-style loop:

1. Read `research_log.md`.
2. Ask a researcher LLM for one bounded config.
3. Run a RAG pipeline.
4. Evaluate faithfulness and relevance.
5. Append result to `research_log.md`.
6. Keep `best_config.json`.
7. Repeat.

Useful ideas:

- The experiment log is readable by both humans and LLMs.
- Config search is bounded and isolates a few parameters per run.
- `best_config.json` gives an explicit current champion.
- Results include tokens/cost/status, not only accuracy.

Limitations for Matrix:

- It is RAG-only and OpenRouter/OpenAI-call heavy.
- It does not know Matrix trace gates, memory boundaries, KG provenance,
  consent, tools or session-level behavior.
- It optimizes final QA scores, not agentic tool/memory correctness.

## AutoRAG / AutoRAG-HP

AutoRAG's official docs describe a modular pipeline where nodes can have
multiple modules/parameters and combinations are evaluated before selecting the
best result for the next node. This maps well to Matrix RAG components, but
full Cartesian search is too expensive.

AutoRAG-HP formulates RAG hyperparameter tuning as online bandit optimization
and reports substantial API-call savings versus grid search. This is the
better long-term direction for Matrix because OpenRouter-free and local
hardware budgets are tight.

2026-04-29 source check:

- Current
  [AutoRAG docs](https://marker-inc-korea.github.io/AutoRAG/optimization/optimization.html)
  still describe node/module/parameter combinations that are evaluated and
  selected through result summaries. This supports Matrix's candidate-artifact
  approach, but full combinatorial search remains too expensive for default dev
  loops.
- [RAGSearch](https://arxiv.org/abs/2604.09666) (published 2026-04-01)
  reframes dense RAG vs GraphRAG under agentic multi-round search. Its key
  practical lesson for Matrix is complementarity: agentic search can narrow the
  gap for dense RAG, while GraphRAG still helps complex multi-hop cases when
  offline graph cost is amortized.
- LinearRAG and GraphRAG-Bench keep graph retrieval in the candidate set, but
  only as a measured retrieval infrastructure, not as a default product-wide
  replacement for hybrid vector/KG retrieval.

## Design Consequence

Feature 023 should start small:

- deterministic local search over a few Feature 022 canaries.
- hand-authored bounded configs, not free-form code generation.
- emit Meta-Harness-compatible artifacts.
- only later add LLM-proposed configs or bandit selection.

The first useful candidate class is RAG:

```text
parser + splitter + chunk policy + retrieval mode + top_k + fusion weights
```

The second useful candidate class is memory/context:

```text
recall provider blend + query gate + injection order + compaction threshold
```

Do not use AutoRAG to directly edit product code.

## 2026-04-29 Z_ Follow-Up

The new features expand candidate spaces, but they stay bounded:

- Feature 024 tool policy can tune selection/compaction, not weaken security.
- Feature 025 semantic lookup can tune ambiguity thresholds and correction
  routing.
- Feature 026 browser-RAG can tune retrieval/runtime fallback choices.
- Feature 028 visual memory can tune confidence/decay/injection thresholds.

All candidates must still emit artifacts for Feature 016 Meta-Harness before
promotion.

2026-04-29 implementation note: inner-loop RAG candidates now carry bounded
cross-feature search spaces when the matching Feature 022 canaries are present:

- semantic layer: exact term id, approved alias expansion, ambiguity thresholds
  and review-required correction routing.
- visual memory: OCR confidence thresholds, required page/bbox coordinates,
  injection thresholds and stale-evidence provenance.
- report grounding: fallback vs experimental Quarkdown renderer as artifact
  metadata only, manifest-required citations and Feature 030-only inline
  rendering.
- tool policy: same-or-stricter catalog/risk policy only.

The protected-input gate was extended so inner loops cannot relax MCP/tool
security gates while searching for better scores.

Parser/chunker search is now represented in extraction benchmark artifacts:
parser profiles describe runtime/resource/source-class scope, and chunker
spaces carry hierarchy-aware chunking, size/overlap and metadata enrichment
requirements. This keeps heavy parsers such as Docling/MinerU optional until
their local resource footprint is proven.

`pdf-extraction-sweep` is the first bounded executor for that search space. It
runs available extractor profiles by default and can include unavailable
profiles as explicit failure artifacts, which is useful for planning without
silently pulling heavy packages onto the 8GB development machine.

## 2026-04-30 Skill Lifecycle Candidate Constraint

Derived from the fresh `_ref/hermes-agent` skill-curator/pinned-skill updates
and Feature 015 runtime implementation.

Inner loops may optimize skill retrieval, trigger thresholds, selected-skill
budgets and promotion/archive recommendations, but they must preserve these
runtime invariants:

- pinned skills are immutable to automated imports, archive installs and future
  skill-evolution writers.
- prompt usage and view counts are evidence inputs, not direct success labels.
- candidates emit Meta-Harness artifacts for outer-loop promotion; they do not
  patch skill files, DB rows or sidecar state directly.
- provider-specific assumptions are excluded; OpenRouter/provider calls remain
  optional and capped by the existing live-provider gates.

This connects Feature 023 to `Z_Additional_For_Tool_Stuff.md` and Feature 016:
tool/skill optimization is useful only when it cannot relax security, provenance
or pinned-lifecycle constraints.

## 2026-04-30 Agent Harness Candidate Spaces

Derived from `Z_Additional_For_Tool_Stuff.md`, the Matrix memory/KG follow-up
notes, Hermes bounded-subagent lessons and the implemented Feature 012/015/017
runtime constraints.

The inner loop now emits provider-agnostic, static candidate dimensions for the
agent harness around RAG candidates:

- memory context: Hindsight/MemPalace blend, query gate, compaction threshold,
  injection order, decay and required evidence trace fields.
- skills/tools: regex/BM25/RRF descriptor discovery, current skill trigger
  policy, max selected skills, usage evidence, pinned write fence and
  recommend-only mutation semantics.
- runner: dispatcher/LangGraph/simple parity, timeout, iteration/output-token
  bounds, approval interrupts and fail-closed confirm-unavailable behavior.
- KG: projection backend, path depth, temporal filtering, access/recency decay,
  vector/KG fusion weight and promotion evidence requirements.

These search spaces deliberately describe what a bounded optimizer may vary.
They are not permission to edit product code or mutate catalogs directly; every
candidate still has to become a Feature 016 Meta-Harness artifact before an
outer-loop promotion decision.
