---
title: Semantic Layer Metrics Claims Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-30
feature_id: 025
---

# Research

## Local Z Reference

Derived from `Z_Semantik_layer and so on.md`. That note was explicitly marked
as a fast external sketch that had not seen the Matrix codebase, so Matrix uses
it as direction, not authority.

## Working Judgement

The useful idea is provider-agnostic: agents need a semantic API between
natural language and data, not blind Text-to-SQL. This applies equally to SQL
tables, KG claims, RAG documents and operational metrics.

## Source Check 2026-04-29

- Metrics-as-code systems such as dbt MetricFlow and Cube show the right shape:
  definitions are versioned and queryable instead of embedded in prompts.
- Governance/security products show the permission problem, but Matrix should
  implement the minimal local contract first: row/user/tenant filters and
  provenance in every semantic response.
- KG-backed semantic layers are useful for relations between terms, entities
  and documents, but they should not bypass Feature 017 claim provenance.
- Semantic feedback loops are valuable only if they produce proposals with
  review/audit state.
- Current dbt/MetricFlow and Cube references reinforce definitions-as-code,
  semantic manifests and permission-aware query planning. Matrix implements a
  smaller local catalog first instead of adopting a platform dependency.
- Text-to-SQL research still highlights ambiguity and semantic-equivalence
  issues. The first Matrix slice therefore returns a semantic contract and
  `raw_sql_allowed=false` instead of generating ad-hoc SQL.
- 2026-04-29 implementation follow-up: `semantic_lookup` is now a first-class
  read-only agent tool. It resolves terms/metrics from the local catalog,
  returns fail-closed refusal guidance for unknown/ambiguous phrases, includes
  permission-filtered metric contracts and never permits raw SQL. This is the
  agent-facing counterpart to the Control semantic API.
- 2026-04-29 routing follow-up: semantic lookup is classified as a retrieval
  route alongside memory/KG/RAG lookup. Metric-sensitive questions should be
  treated as "retrieve authoritative meaning first", not as generic tool-use or
  model-only answers.
- 2026-04-29 Control UI follow-up: Feature 010 `ToolsTab` now exposes
  `semantic_lookup` in the normal ToolRegistry view with `semantic` group,
  risk/approval metadata and filters. This references the same root Z_ semantic
  note, but intentionally keeps rich metric owner/version/provenance/conflict
  inspection as a separate Feature 025 semantic catalog surface.
- 2026-04-29 inspector follow-up: Feature 010 `/control/semantic` now renders
  that separate catalog surface. It remains provider-agnostic and read-only:
  users can inspect definitions, aliases, KG/RAG ties, metric scope/freshness
  and permission-aware plans, but the UI does not generate SQL or execute a
  metric.
- 2026-04-30 agent handoff follow-up: `semantic_lookup` now returns a compact
  semantic handoff envelope in model output. Term matches expose catalog
  version, `semantic_term_ids`, KG claim types and RAG source classes; metric
  matches expose metric id and catalog version inside the permission-aware
  metric plan. This keeps the Feature 019 RAG/KG bridge provider-agnostic and
  avoids dumping full catalog rows into the prompt.

## Design Consequence

Feature 025 should expose a small semantic catalog and query API before any
large BI-style platform choice:

```text
phrase -> semantic term/metric -> permission check -> source query/retrieval
  -> value/context -> provenance/freshness -> answer
```

The provider is irrelevant. The contract is what matters.

## Checked Sources

- Matrix root `Z_Semantik_layer and so on.md`.
- dbt MetricFlow repository: `https://github.com/dbt-labs/metricflow`.
- dbt Semantic Layer overview:
  `https://www.getdbt.com/blog/how-the-dbt-semantic-layer-works`.
- Cube semantic layer references from current web review.
- Text-to-SQL semantic equivalence paper:
  `https://arxiv.org/abs/2506.09359`.

## 2026-04-30 Source And Contract Refresh

Fresh source check keeps the local implementation deliberately small:

- dbt MetricFlow supports the definitions-as-code and query-plan shape, but
  Matrix should not adopt a dbt dependency before the local catalog contract is
  proven.
- Cube reinforces the agentic semantic-layer pattern: agents query a governed
  semantic runtime/API instead of directly inventing warehouse SQL.
- RAG/KG research reinforces that semantic terms must connect structured
  metrics, KG claims and unstructured citations without bypassing provenance.

Implementation follow-up: `meta_harness.knowledge_contract` now covers the
cross-feature semantic cases from `Z_Semantik_layer and so on.md`. It fails
closed on ambiguous phrases, denies tenant-scoped metrics without tenant
context, keeps `raw_sql_allowed=false`, requires semantic term links on KG/RAG
context, and keeps memory/user corrections as reviewed proposals.

Runtime follow-up: Feature 019 retrieval now consumes semantic constraints
without binding to a vendor model. Callers can pass a reviewed
`semantic_filter` or a catalog phrase; retrieval applies term/metric filters
before fusion and Context Bubble assembly, then reports explicit degradation
when the semantic filter is ambiguous, unknown or filters out all candidates.

2026-04-30 correction endpoint follow-up: the semantic Control API now exposes
the same proposal/review pattern as the Meta-Harness contract. This is the
runtime bridge for `Z_Semantik_layer and so on.md`: user or memory feedback can
propose a term/metric correction, but even an accepted review returns
`catalog_mutated=false` until a separate catalog publishing step applies it.
The implementation stays local and provider-agnostic.

2026-04-30 memory feedback follow-up: memory-derived corrections now have an
actual runtime helper instead of only a Control API placeholder.
`memory_fusion.semantic_feedback` requires durable evidence metadata, enriches
it through the Feature 012 evidence-trace contract and creates a normal
semantic review proposal with `_feedback_source=memory_fusion`. This keeps the
semantic catalog authoritative: Hindsight/MemPalace observations may propose
definition changes, but they cannot silently promote a personal memory into
shared metric/KG/RAG truth.

## 2026-04-30 Semantic Retrieval Transfer

Inputs: `Z_Semantik_layer and so on.md`, Feature 019 and Feature 012.

Semantic terms, metrics and correction proposals are retrieval constraints and
answer metadata, not hidden truth overrides. RAG/KG context can use semantic
term ids and metric ids for filtering, but selected context must preserve
catalog version, ambiguity status and source refs. Personal corrections route
to reviewed proposals before global semantic definitions change.

Runtime events should include semantic catalog version and selected term ids
when a tool/RAG/KG answer depends on them.

## 2026-04-30 Agent Metric Answer Gate

The remaining backend risk was not the catalog itself, but the agent-runtime
handoff: a model could still answer a metric question from prior context unless
the trace contract required the semantic tool before the answer. Feature 025 now
adds `knowledge-semantic-lookup-before-metric-answer` to
`meta_harness.knowledge_contract`.

This scenario is deliberately provider-agnostic and derives from the same root
`Z_Semantik_layer and so on.md` judgement: metric answers need authoritative
semantic mediation. The gate requires a `semantic_lookup` tool result, compact
model output with `agent_tool_success_rate`, semantic catalog version, semantic
contract, freshness and `raw_sql_allowed=false`, plus answer text that cites the
approved data path rather than inventing a metric value.

## 2026-04-30 Lexical Candidate Lane

The `Z_` notes mention regex/BM25-style lookup tricks. For the semantic layer,
the safe transfer is not automatic fuzzy matching. The implemented slice keeps
exact alias matching authoritative and adds a provider-free lexical candidate
lane only for non-matches. `lookup_phrase()` returns scored
`candidate_matches`; `semantic_lookup` exposes them as compact suggestions with
`authoritative=false` and `requires_confirmation=true`.

This improves agent ergonomics for phrases like "tool success ratio" without
letting a near miss become a metric contract. Retrieval/RAG/KG can use the same
candidate metadata for search UI or clarification, while answers still need an
exact term/metric or an explicit user choice.
