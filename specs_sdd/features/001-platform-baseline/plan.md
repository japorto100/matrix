---
title: Platform Baseline Plan
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 001
migrated_from:
  - specs/00-overview.md
  - specs/08-tooling.md
  - specs/09-privacy.md
  - specs/10-portierung.md
  - specs/FUTURE_IDEAS.md
  - specs/agent-output-pattern.md
adrs: []
---

# Plan

## Architecture

This feature is a documentation baseline, not a runtime component. It provides
the stable project frame for the rest of `specs_sdd`.

## Critical Files

- `specs_sdd/constitution.md`
- `specs_sdd/README.md`
- `specs_sdd/FEATURE_DETERMINATION.md`
- `specs_sdd/LEGACY_COVERAGE.md`
- `specs_sdd/research/backlog/README.md`

## Migration Strategy

1. Import enduring architecture from old top-level specs.
2. Move machine/tooling/privacy rules into constitution where binding.
3. Split future ideas into backlog or owning features.
4. Keep historical project framing in this feature.

## Risks

- Treating stale historical assumptions as current rules.
- Duplicating constitution rules in feature specs.

