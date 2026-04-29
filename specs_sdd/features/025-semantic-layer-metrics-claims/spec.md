---
title: Semantic Layer Metrics Claims
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 025
---

# Semantic Layer Metrics Claims

## Current State / Ist

Matrix has KG claims in Feature 017, schema governance in Feature 018, RAG in
Feature 019 and agent/harness evals in Feature 016. It does not yet have a
single semantic contract for business metrics, glossary terms, SQL-safe
dimensions, document concepts and KG claims.

Agents can therefore answer with plausible but inconsistent definitions:
`revenue`, `risk`, `exposure`, `PnL`, `claim`, `evidence` or `confidence` can
mean different things depending on which tool or prompt was active.

Static implementation follow-up on 2026-04-29 adds `semantic_lookup` as a
read-only agent tool. It resolves Matrix-owned semantic terms and metrics,
returns permission-filtered metric contracts, fails closed for ambiguous or
unknown phrases and keeps `raw_sql_allowed=false`.

## Target State / Soll

Feature 025 creates a provider-agnostic semantic layer:

- metrics-as-code definitions for measures, dimensions and filters;
- glossary terms linked to tables, documents, KG entities and RAG concepts;
- permission-aware semantic query API instead of free-form SQL by default;
- provenance from metric value to source table/document/claim;
- correction loop when users or evaluators reject a definition;
- Meta-Harness scenarios where agents must use the semantic API rather than
  inventing metric definitions.

The layer must cover structured and unstructured evidence. A metric definition
can cite a SQL column, a KG claim type and a RAG source class when the business
concept spans both.

## Boundaries

- Feature 017 owns bitemporal KG claim persistence.
- Feature 018 owns Alembic and schema registry generation.
- Feature 019 owns answer-time retrieval.
- Feature 010 owns UI inspection surfaces.
- Feature 014 owns metric/eval trace visibility.

Feature 025 owns the semantic meaning and API contract that agents use.

## Closeout Criteria

- Metric and glossary definitions are versioned in repo-owned files or DB rows
  with migration governance.
- Agents query semantic definitions before answering metric-sensitive prompts.
- Row/user permissions affect semantic query results.
- Metric values expose provenance and freshness.
- Rejected/corrected definitions enter an auditable proposal workflow.
- Agent tool output includes refusal guidance when no authoritative definition
  exists, rather than letting the model invent a metric.
