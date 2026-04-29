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

## Design Consequence

Feature 025 should expose a small semantic catalog and query API before any
large BI-style platform choice:

```text
phrase -> semantic term/metric -> permission check -> source query/retrieval
  -> value/context -> provenance/freshness -> answer
```

The provider is irrelevant. The contract is what matters.
