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
- T004 Define renderer capability matrix.
- T005 Decide whether Quarkdown is default, optional or experimental.

## Report Contract

- T010 Define report source layout: `.qd` or markdown, data, charts, citations,
  output and manifest.
- T011 Define report manifest with title, owner, input sources, generated_at,
  renderer version and checksum.
- T012 Define citation block contract shared with Feature 019/021.
- T013 Define generated chart/table input format.
- T014 Define validation rules before build.
- T015 Define artifact retention and cleanup policy.

## Agent Integration

- T020 Add report-generation tool contract.
- T021 Add report build tool contract.
- T022 Add report validation tool contract.
- T023 Add agent prompt constraints for source-grounded reports.
- T024 Add Meta-Harness report scenario.
- T025 Add Matrix chat handoff: link/attachment plus provenance summary.
- T026 Add Control UI report artifact list.

## Verification

- T030 Unit-test manifest validation.
- T031 Unit-test citation completeness.
- T032 Integration-test renderer on fixture.
- T033 Integration-test report build failure is surfaced to agent.
- T034 Live-verify generated HTML/PDF artifact.
- T035 Live-verify Matrix chat can display generated artifact link safely.
- T036 Meta-Harness score report against source-grounding gates.
