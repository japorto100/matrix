---
title: Semantic Layer Metrics Claims Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-29
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
