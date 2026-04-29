---
title: Visual Memory Layout Extraction Tasks
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 028
---

# Tasks

## Evidence Model

- T001 Inventory screenshot, OCR, file preview and ingestion paths.
- T002 Define `VisualEvidence`: source type, capture time, path/url, consent,
  retention and checksum.
- T003 Define layout block schema: text, bbox, page/frame, role, confidence and
  source ref.
- T004 Define table/formula/code/figure extraction metadata.
- T005 Define visual memory summary schema linked to evidence refs.
- T006 Define retention/decay policy for visual evidence.
- T007 Define privacy redaction rules for screenshots.

## Extraction

- T010 Add OCR/layout adapter interface.
- T011 Wire existing PDF/layout extractors from Feature 021 where applicable.
- T012 Add screenshot-to-markdown extraction lane.
- T013 Add table extraction smoke fixture.
- T014 Add coordinate-preserving citation refs for visual blocks.
- T015 Add duplicate/near-duplicate visual frame suppression.
- T016 Add confidence thresholds before memory injection.

## Memory And RAG

- T020 Add visual evidence search over summaries and block text.
- T021 Add visual memory injection only when source refs are present.
- T022 Add KG claim proposal path for visual evidence without auto-promotion.
- T023 Add optical-compression experiment flag.
- T024 Add old-context thumbnail/low-detail summary candidate.
- T025 Add visual memory decay metrics.
- T026 Coordinate with Feature 012 personal memory and Feature 017 KG claims.

## Verification

- T030 Unit-test visual evidence schema.
- T031 [partial-static] Unit-test layout coordinate refs.
  - 2026-04-29: Feature 022 canary
    `visual-layout-source-coordinates-001` statically verifies coordinate refs
    survive retrieval selection. Dedicated Feature 028 schema/unit tests remain
    open.
- T032 Unit-test screenshot redaction policy.
- T033 Integration-test OCR fixture to visual memory.
- T034 Meta-Harness scenario: recall visible screen text.
- T035 Meta-Harness scenario: refuse unseen screen content.
- T036 Meta-Harness scenario: stale visual memory must show age/provenance.
- T037 Live-verify screenshot/document extraction on a local fixture.
