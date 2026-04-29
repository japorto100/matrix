---
title: Semantic Layer Metrics Claims Tasks
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 025
---

# Tasks

## Model

- T001 Inventory current schema registry, KG claim types and RAG source
  metadata.
- T002 Define semantic term schema: name, aliases, owner, status, description,
  source refs and allowed use.
- T003 Define metric schema: measure, dimensions, filters, grain, time field,
  freshness and allowed aggregation.
- T004 Define semantic claim mapping from KG claim types to glossary terms.
- T005 Define document concept mapping from RAG source classes to glossary
  terms.
- T006 Add semantic versioning and deprecation state.
- T007 Add permission annotations for row/user/tenant scoped metrics.
- T008 Add ambiguity handling when two definitions match one phrase.

## API

- T010 Implement read-only semantic catalog API.
- T011 Implement metric lookup by phrase, aliases and explicit id.
- T012 Implement provenance expansion for metric and term definitions.
- T013 Implement permission-filtered metric query planning.
- T014 Add SQL generation only behind a semantic contract, never raw agent SQL
  by default.
- T015 Add KG/RAG concept lookup for non-SQL semantic terms.
- T016 Add correction proposal endpoint.
- T017 Add acceptance/rejection workflow for corrections.
- T018 Add export to Control UI and Meta-Harness artifacts.

## Agent Integration

- T020 Add semantic lookup tool visible to agent runners.
- T021 Add prompt/router rule for metric-sensitive user questions.
- T022 Add refusal path when no authoritative definition exists.
- T023 Add answer template with definition, value, provenance and freshness.
- T024 Add memory feedback path for corrected definitions without silently
  promoting them.
- T025 Coordinate semantic terms with Feature 017 claim promotion.
- T026 Coordinate semantic terms with Feature 019 retrieval filters.

## Verification

- T030 Unit-test semantic schema validation.
- T031 Unit-test alias collision and ambiguity handling.
- T032 Unit-test permission filtering.
- T033 Unit-test correction proposal workflow.
- T034 Integration-test agent uses semantic lookup before metric answer.
- T035 Meta-Harness scenario: two similar metrics must not be conflated.
- T036 Meta-Harness scenario: unstructured document concept must link to a KG
  claim and RAG citation.
- T037 Live-verify Control UI semantic catalog.
