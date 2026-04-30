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
- [x] T013 [done-static] Define generated chart/table input format.
  - 2026-04-29: `ReportDataArtifact` defines table/chart artifact ids,
    source refs, columns/rows, chart type and Markdown references as
    `{{artifact_id}}`; builds materialize them to `data.json`.
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
- [x] T023 [done-static] Add agent prompt constraints for source-grounded reports.
  - 2026-04-29: researcher and risk-manager role prompts/contracts require
    source markers, explicit `[UNSUPPORTED]` markings and `report_validate`
    before `report_build`.
- [x] T024 [done-static] Add Meta-Harness report scenario.
  - 2026-04-29: `meta_harness report-grounding` runs provider-free valid-build,
    missing-citation and unsupported-marker scenarios and writes Pareto-readable
    candidate artifacts.
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
- [x] T032 [done-static] Integration-test renderer on fixture.
  - 2026-04-29: fallback renderer fixture writes HTML/text/manifest and escapes
    HTML; Quarkdown fixture remains live-only until CLI/runtime is promoted.
- [x] T033 [done-static] Integration-test report build failure is surfaced to agent.
  - 2026-04-29: `report_build` returns structured validation failures for
    missing citations and does not write artifacts.
- T034 Live-verify generated HTML/PDF artifact.
- T035 Live-verify Matrix chat can display generated artifact link safely.
- [x] T036 [done-static] Meta-Harness score report against source-grounding gates.
  - 2026-04-29: Feature 022 canary `report-grounding-manifest-001` now scores
    whether report manifest/output/renderer metadata survives as cited
    retrieval evidence. Feature 027 now adds provider-free `report-grounding`
    scenarios for citation/build validation and unsupported-claim handling.
- [x] T037 [done-static] Frontend typecheck/lint for `/control/reports`.
- [x] T038 [done-static] Unit-test report artifact index over generated and
  invalid manifests.
- [x] T039 [done-static] Unit-test report validation/build tools and registry
  exposure.

## 2026-04-30 Runtime Artifact Additions

- T040 Emit Feature 033 runtime events for report validate/build/artifact
  created/citation readiness.
- T041 Add Agent Chat attachment handoff for report manifest, HTML/text/PDF
  outputs and data artifacts.
- [partial-static] T042 Add Control UI artifact event linkage so report rows point back to the
  originating session/turn/tool call.
  - 2026-04-30: Ops events now link forward to report rows through
    `linked_surfaces.report_artifacts` and `/control/reports?report_id=...`.
    Reverse links from report rows back to the originating event remain future
    persisted provenance work.
- T043 Add Meta-Harness downstream gate that fails if report text exists but
  artifact manifests/events are missing.
