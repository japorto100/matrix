---
title: Feature Determination
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
---

# Feature Determination

This pass determines how many SDD features are needed and which legacy execs
are active, already built, superseded or research-only.

## Decision

Use **15 final features** plus **3 meta destinations**.

The order is intentional:

- Earlier IDs are baseline or mostly completed.
- Middle IDs are implemented but carry live-verify debt.
- Later IDs are in progress, mixed, decision-pending or research-gated.

## Final Features

| ID | Feature | Status | Main Reason |
|---|---|---|---|
| 001 | Platform Baseline | baseline | Legacy top-level architecture needs one stable baseline. |
| 002 | Devstack Bootstrap, Env and Persistence Ops | implementation_done | Mostly implemented local ops. |
| 003 | Frontend Merger and Shell | implementation_done | Built and tested; local live smoke remains. |
| 004 | Matrix Homeserver, Connectivity and Mobile/Federation | active_monitoring | Required baseline, with external blockers. |
| 005 | Matrix Chat Core | implementation_done | Large implemented surface; live verify debt. |
| 006 | Appservice, NATS, E2EE and Bridges | implementation_done_live_verify_open | A4 E2E remains. |
| 007 | Agent Chat and Voice Runtime | implementation_done_live_verify_open | SSE/API/voice live verify remains. |
| 008 | Agentic UI, Generative UI and MCP | mostly_built | A2UI built; phase-2 and live roundtrip gaps. |
| 009 | Multi-Agent and A2A Orchestration | implementation_done_live_verify_open | A2A live smoke is hot blocker. |
| 010 | Control UI and Runtime Surfaces | frontend_built | Needs cross-backend walkthrough. |
| 011 | LLM Gateway, Models, Routing and Billing | mostly_built | Smart routing/billing/model live verification and followups active. |
| 012 | Memory, Context, World Model and Personal KB | mixed_active | Umbrella with real subfeature boundaries. |
| 013 | Sandbox, Security and HITL | mixed_active | OpenSandbox/security built; HITL live verify remains. |
| 014 | Observability, Harness and Evals | in_progress | Infra partly live; evidence/spec lag. |
| 015 | Scheduler, Skills, Formal Planning and Automation | mixed_active | Scheduler/skills partly built; PDDL/DSPy gated. |

## Why Subfeatures Matter

Several old execs are not top-level features. They become subfeatures because
their real ownership is inside a broader product/platform capability:

- `exec-context`, `exec-world-model`, `exec-personal-kb` are subfeatures of
  Feature 012, with `exec-memory` as the umbrella.
- `exec-skills`, `exec-scheduler`, `exec-14-pddl`, `exec-14-DSPy` are one
  automation feature with separate subfeatures.
- `exec-20-mcp-manager` is a subfeature of Agentic UI/MCP, not its own product
  feature yet.
- `exec-13-ui-kg-extensions` is historical input to Control UI and Memory, not
  active work.
- `exec-hermes` is an adoption index; each row belongs to its owning feature.

## Meta Destinations

| Destination | Why not a feature |
|---|---|
| `archive/schema-history/` | `exec-18` is explicitly superseded; schema truth is slice-owned migrations. |
| `research/backlog/` | Media, EBM, Rust, OpenWorldLib, notifications and transformers.js are not one active implementation feature. |
| `journal/` | Superpowers logs and bootstrap notes are chronology/handoff, not task source of truth. |

## Clearly Superseded or Historical

| Source | Verdict |
|---|---|
| `archive/exec-04-ui-rework.md` | superseded by `exec2-03` and current Matrix Chat Core |
| `archive/exec-07-refactoring.md` | historical done |
| `archive/exec-08-agent-backend-voice.md` | merged into Agent Chat / media history |
| `exec-13-ui-kg-extensions.md` | archived into Control UI / Memory |
| `archive/exec-18-unified-agent-schema-SUPERSEDED.md` | schema-history only |
| `archive/exec-19-devstack-consolidation.md` | split into multiple features |
| `archive/exec-merge-chat-SUPERSEDED.md` | replaced by Frontend Merger branch exec |
| `archive/exec-transformers-js-SUPERSEDED.md` | duplicate of active `exec-transformersjs.md` research |
| `archive/pddl_phase22b_delta.md` | delta imported into planning automation history |
| Superpowers frontend merger plan v1 | superseded by v2 |

## Already Built, Keep As Closeout Input

- Devstack scripts/env/secrets/Postgres tuning.
- Branch frontend merger execs.
- `exec2-03c-cinny`.
- Superpowers frontend merger plan v2 phase 1 and most phase 2.
- Hermes Phase B/C/P6 adoption rows.
- Scheduler phase 1.
- Core skills loader/finder/refiner/store/importer/evolver pieces.

## Implemented But Not Done

These are the key reason `live-verify.md` exists:

- `exec-05`: A4 E2E pending.
- `exec-06`: SSE/API/voice full-stack verify pending.
- `exec-09`: native A2UI stream exists in SDD; live LLM-to-A2UI roundtrip still
  needs verification.
- `exec-10`: A2A never live-tested.
- `exec-12`: HITL decision is accepted via ADR-004; Skills-Guard drawer path
  still needs live verify.
- `exec-15`: full Control UI backend walkthrough pending.
- `exec-16`: smart routing G1-G6/P1 imported; spend/user-picker/followup live
  gaps remain.
- `exec-17`: OpenObserve/live traces pending.
