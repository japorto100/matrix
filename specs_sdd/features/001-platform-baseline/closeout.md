---
title: Platform Baseline Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 001
---

# Closeout

## Built

- Top-level `specs/*.md` classification is complete in
  `LEGACY_COVERAGE.md`.
- Binding machine, tooling, privacy, architecture and agent-output rules are
  promoted into `constitution.md`.
- `specs/FUTURE_IDEAS.md` is represented by the SDD-facing backlog split in
  `research/backlog/future-ideas.md`.
- The baseline spec now states the active architecture boundaries: Go owns the
  Matrix/E2EE gateway, Python owns agent/business logic, `frontend_merger` owns
  the UI, and NATS is only the Matrix event handoff bus.

## Not Built

- No runtime code belongs to Feature 001.
- No live verification is required for this feature beyond document
  consistency.

## Deviations From Plan

- Legacy files were not moved or deleted. They remain unchanged as provenance,
  matching the first-pass migration rule.

## Verify Result

- Static SDD consistency pass completed on 2026-04-25.
- `LEGACY_COVERAGE.md` has an owner/classification for every top-level
  `specs/*.md` source.

## Live Verify Result

Not applicable. Feature 001 is a specification/baseline feature.

## Follow-Ups

- If a future idea is activated, copy it into the owning feature `tasks.md`
  with acceptance criteria instead of editing `specs/FUTURE_IDEAS.md`.
