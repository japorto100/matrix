---
title: Semantic Layer Metrics Claims Tasks
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-30
feature_id: 025
---

# Tasks

## Model

- T001 Inventory current schema registry, KG claim types and RAG source
  metadata.
- [x] T002 [done-static] Define semantic term schema: name, aliases, owner, status, description,
  source refs and allowed use.
- [x] T003 [done-static] Define metric schema: measure, dimensions, filters, grain, time field,
  freshness and allowed aggregation.
- [x] T004 [done-static] Define semantic claim mapping from KG claim types to glossary terms.
- [x] T005 [done-static] Define document concept mapping from RAG source classes to glossary
  terms.
- [x] T006 [done-static] Add semantic versioning and deprecation state.
- [x] T007 [done-static] Add permission annotations for row/user/tenant scoped metrics.
- [x] T008 [done-static] Add ambiguity handling when two definitions match one phrase.

## API

- [x] T010 [done-static] Implement read-only semantic catalog API.
- [x] T011 [done-static] Implement metric lookup by phrase, aliases and explicit id.
- [x] T012 [done-static] Implement provenance expansion for metric and term definitions.
- [x] T013 [done-static] Implement permission-filtered metric query planning.
- [x] T014 [done-static] Add SQL generation only behind a semantic contract, never raw agent SQL
  by default.
- [x] T015 [done-static] Add KG/RAG concept lookup for non-SQL semantic terms.
- [x] T016 [done-static] Add correction proposal endpoint.
  - 2026-04-30: Control API now exposes semantic correction create/list/review
    endpoints backed by review proposals; accepted reviews still do not mutate
    the runtime catalog.
- [x] T017 [done-static] Add acceptance/rejection workflow for corrections.
- [x] T018 [done-static] Add export to Control UI and Meta-Harness artifacts.

## Agent Integration

- [x] T020 [done-static] Add semantic lookup tool visible to agent runners.
  - 2026-04-29: `SemanticLookupTool` is registered in `ToolRegistry.load()`
    as `semantic_lookup` and included in advisory/trading role allowlists.
- [x] T021 [done-static] Add prompt/router rule for metric-sensitive user questions.
  - 2026-04-29: `semantic_lookup` is classified as a retrieval route in
    `agent.routing.delegation_policy`, so route-decision telemetry treats it
    like memory/KG/RAG lookup instead of generic tool use.
- [x] T022 [done-static] Add refusal path when no authoritative definition exists.
  - 2026-04-29: unknown phrases return `status=not_found`,
    `refusal_reason=no-authoritative-definition` and explicit no-invention
    guidance; ambiguous phrases fail closed.
- [x] T023 [done-static] Add answer template with definition, value, provenance and freshness.
  - 2026-04-29: matched terms/metrics return an answer template with
    definition/measure, source refs, freshness SLA and `raw_sql_allowed=false`.
- T024 [done-static] Add memory feedback path for corrected definitions
  without silently promoting them.
  - 2026-04-30: `knowledge-semantic-correction-review-proposal` proves the
    proposal/review contract. Runtime feedback wiring remains open.
  - 2026-04-30: Runtime Control API now preserves the same proposal/review
    contract for user/agent corrections; memory feedback can call this surface
    instead of writing semantic truth directly.
  - 2026-04-30: `memory_fusion.semantic_feedback` now turns source-linked
    memory evidence into semantic correction proposals with
    `_feedback_source=memory_fusion`, durable evidence refs and
    `catalog_mutated=false`. The Control API accepts this path via
    `source=memory_fusion` and rejects unreferenced feedback.
- T025 [done-static] Coordinate semantic terms with Feature 017 claim
  promotion.
  - 2026-04-30: `knowledge-contract` requires `semantic_term_ids` on KG claim
    proposals and KG context.
- T026 [done-static] Coordinate semantic terms with Feature 019 retrieval
  filters.
  - 2026-04-30: selected RAG/KG context now has a static contract for
    `semantic_catalog_version` and `semantic_term_ids`.
  - 2026-04-30: Feature 019 runtime retrieval now accepts `semantic_filter`
    and `semantic_phrase`, using the semantic catalog to derive metric filters
    and filtering selected vector/KG candidates by `semantic_term_ids` and
    `metric_id`.

## Verification

- [x] T030 Unit-test semantic schema validation.
- [x] T031 Unit-test alias collision and ambiguity handling.
- [x] T032 Unit-test permission filtering.
- [x] T033 Unit-test correction proposal workflow.
- [x] T033a [done-static] Unit-test `semantic_lookup` tool registration,
  permission-fail-closed behavior, refusal guidance and compact model output.
- [x] T033b [done-static] Expose `semantic_lookup` in Control UI Tools registry
  fallback and filters.
  - 2026-04-29: Feature 010 `ToolsTab` shows the semantic group, risk/approval
    policy and last-seen state; Feature 025 still owns the richer semantic
    catalog/metric inspector.
- [x] T033c [done-static] Expose semantic catalog/metric inspector in Control
  UI.
  - 2026-04-29: `/control/semantic` consumes the semantic catalog API with a
    fallback fixture, renders validation/conflicts, KG/RAG term metadata,
    metric permissions/freshness/source refs and a no-raw-SQL plan panel.
- T034 Integration-test agent uses semantic lookup before metric answer.
- [x] T035 [done-static] Meta-Harness scenario: two similar metrics must not be
  conflated.
  - 2026-04-30: `knowledge-semantic-ambiguity-permission-fail-closed` checks
    alias collision/ambiguity and permission fail-closed behavior.
- [x] T036 [done-static] Meta-Harness scenario: unstructured document concept
  must link to a KG claim and RAG citation.
  - 2026-04-30: `knowledge-rag-kg-semantic-context-grounded` requires semantic
    catalog/version/term metadata plus RAG citation and KG claim refs.
- T037 Live-verify Control UI semantic catalog and correction proposal flow.
