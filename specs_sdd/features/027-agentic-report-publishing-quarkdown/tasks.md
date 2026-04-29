---
title: Agentic Report Publishing Quarkdown Tasks
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 027
---

# Tasks

## Renderer Evaluation

- T001 Install/evaluate Quarkdown locally without global toolchain churn.
- T002 Verify HTML, PDF, slides and plain text outputs on a tiny fixture.
- T003 Compare fallback options: Pandoc, MkDocs, plain Markdown/MDX.
- [x] T004 [done-static] Define renderer capability matrix.
- [x] T005 [done-static] Decide whether Quarkdown is default, optional or experimental.
  - 2026-04-29: Quarkdown remains experimental; `markdown-fallback` is the
    deterministic contract renderer until local Quarkdown CLI builds pass.

## Report Contract

- [x] T010 [done-static] Define report source layout: `.qd` or markdown, data, charts, citations,
  output and manifest.
- [x] T011 [done-static] Define report manifest with title, owner, input sources, generated_at,
  renderer version and checksum.
- [x] T012 [done-static] Define citation block contract shared with Feature 019/021.
- T013 Define generated chart/table input format.
- [x] T014 [done-static] Define validation rules before build.
- T015 Define artifact retention and cleanup policy.

## Agent Integration

- [x] T020 [done-static] Add report-generation tool contract.
  - 2026-04-29: `ReportArtifactInput` defines the provider-agnostic report
    source/manifest/citation payload agents must produce before build.
- [x] T021 [done-static] Add report build tool contract.
  - 2026-04-29: `report_build` writes deterministic artifacts under
    `MATRIX_REPORT_ARTIFACT_DIR`/`data/reports`, rejects path traversal ids and
    forces `markdown-fallback` until Quarkdown is promoted.
- [x] T022 [done-static] Add report validation tool contract.
  - 2026-04-29: `report_validate` checks manifest metadata, citation usage and
    checksum without writing files.
- T023 Add agent prompt constraints for source-grounded reports.
- T024 Add Meta-Harness report scenario.
- T025 Add Matrix chat handoff: link/attachment plus provenance summary.
- [x] T026 [done-static] Add Control UI report artifact list.
  - 2026-04-29: `/control/reports` provides the frontend artifact index for
    report manifests, renderer/version, checksum, output files, citations,
    validation failures and Matrix publication readiness. It remains read-only
    and uses fallback fixtures until persisted report artifact listing exists.
- [x] T026a [done-static] Add read-only Control API report artifact index.
  - 2026-04-29: `/api/v1/control/reports` scans `MATRIX_REPORT_ARTIFACT_DIR`
    or `data/reports`, reads `manifest.json`, revalidates against the Feature
    027 report contract and returns normalized artifact rows for Control UI.

## Verification

- [x] T030 Unit-test manifest validation.
- [x] T031 Unit-test citation completeness.
- T032 Integration-test renderer on fixture.
- T033 Integration-test report build failure is surfaced to agent.
- T034 Live-verify generated HTML/PDF artifact.
- T035 Live-verify Matrix chat can display generated artifact link safely.
- T036 [partial-static] Meta-Harness score report against source-grounding gates.
  - 2026-04-29: Feature 022 canary `report-grounding-manifest-001` now scores
    whether report manifest/output/renderer metadata survives as cited
    retrieval evidence. Full report-generation Meta-Harness scenario remains
    open.
- [x] T037 [done-static] Frontend typecheck/lint for `/control/reports`.
- [x] T038 [done-static] Unit-test report artifact index over generated and
  invalid manifests.
- [x] T039 [done-static] Unit-test report validation/build tools and registry
  exposure.
