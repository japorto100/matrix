---
title: Platform Baseline
status: baseline
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

# Platform Baseline

## Current State / Ist

The repo is an isolated Matrix integration setup that feeds into the larger
tradeview-fusion architecture. The old top-level `specs/*.md` files contain a
mix of current architecture, historical assumptions and future ideas.

The durable baseline is: Matrix is the communication layer testbed; Go owns the
Matrix/E2EE gateway; Python owns agent/business logic; `frontend_merger` is the
current UI home; Tuwunel is the primary homeserver; NATS is only the Matrix
event bus; Agent Chat and Voice use HTTP/SSE and LiveKit.

## Target State / Soll

This feature is the stable baseline for all other specs: project purpose,
architecture boundaries, machine/tooling assumptions, privacy constraints,
porting direction and backlog triage are documented in one place.

## Subfeatures

- Architecture overview
- Tooling and local development assumptions
- Privacy constraints
- Porting strategy
- Future ideas triage
- Agent output conventions
- Service/port inventory
- Current vs historical frontend/backend layout

## Gap

- Decide which top-level legacy docs are still accepted current state.
- Move outdated material into historical notes instead of active guidance.
- Extract non-negotiable rules into `specs_sdd/constitution.md`.
- Keep porting direction to tradeview-fusion separate from current matrix-repo
  runtime facts.

## Verify

- [ ] Every old top-level `specs/*.md` file is either referenced here, assigned
  to another feature, or marked historical in `MIGRATION_MAP.md`.

## Closeout Criteria

- `constitution.md` contains the active project rules.
- This spec links to all durable baseline docs.
- No top-level legacy spec is unclassified.
