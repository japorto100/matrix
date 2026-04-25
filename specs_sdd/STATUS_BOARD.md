---
title: SDD Status Board
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
---

# SDD Status Board

This replaces the old idea of a standalone execution order. It is a compact
board; the source of truth for scope is each feature's `spec.md`.

Each feature now has the SDD core file set:

- `spec.md`
- `plan.md`
- `tasks.md`
- `live-verify.md`
- `closeout.md`

## Feature Status

| ID | Feature | State | Next Gate | Can Close? |
|---|---|---|---|---|
| 001 | Platform Baseline | baseline | classify remaining top-level docs | no, until legacy top-level docs are classified |
| 002 | Devstack Bootstrap, Env and Persistence Ops | implementation_done | operator/live bootstrap check | yes, after closeout |
| 003 | Frontend Merger and Shell | implementation_done | user-local full-stack live smoke | yes, after live smoke |
| 004 | Matrix Homeserver, Connectivity and Mobile/Federation | active_monitoring | Tuwunel/mobile/connectivity check | not as long as upstream monitoring is active |
| 005 | Matrix Chat Core | implementation_done | live Matrix session | no, live verify required |
| 006 | Appservice, NATS, E2EE and Bridges | implementation_done_live_verify_open | A4 E2E publish/subscribe/decrypt | no, A4 pending |
| 007 | Agent Chat and Voice Runtime | implementation_done_live_verify_open | SSE/tool-call/voice stack verify | no, live verify required |
| 008 | Agentic UI, Generative UI and MCP | mostly_built | native A2UI live roundtrip + #93 decision | no, phase-2 gaps remain |
| 009 | Multi-Agent and A2A Orchestration | implementation_done_live_verify_open | A2A live smoke | no, A2A never live-tested |
| 010 | Control UI and Runtime Surfaces | frontend_built | tab-by-tab backend walkthrough | no, backend integration mixed |
| 011 | LLM Gateway, Models, Routing and Billing | mostly_built | LiteLLM/billing/routing live verify | no |
| 012 | Memory, Context, World Model and Personal KB | mixed_active | memory_fusion/context live verify | no |
| 013 | Sandbox, Security and HITL | mixed_active | Skills-Guard HITL live verify | no |
| 014 | Observability, Harness and Evals | in_progress | live trace + audit/eval evidence | no |
| 015 | Scheduler, Skills, Formal Planning and Automation | mixed_active | scheduler live delivery + real-LLM skill verify | no |

## Immediate Migration Order

Completed semantic-deepening pass:

1. Feature 010 Control UI.
2. Feature 005 Matrix Chat Core.
3. Feature 008 Agentic UI/MCP.
4. Feature 011 LLM Gateway/Routing/Billing.
5. Feature 012 Memory/Context/World/KB.
6. Feature 015 Scheduler/Skills/Planning.

Completed follow-up semantic pass:

1. Global `SOURCES.md` and source-preservation rule.
2. Feature 014 Observability/Harness/Evals sources, subfeatures and gates.
3. Feature 013 Sandbox/Security/HITL sources, subfeatures and gates.
4. Features 006, 007 and 009 detailed live-gate imports.
5. Features 001-004 source/gate condensation.

Next order is no longer migration; it is review and live verification by
feature priority.

## Closure Rule

`implementation_done` is not `closed`. A feature closes only when:

- legacy sources are summarized or linked with provenance,
- open tasks live in `tasks.md`,
- automated verify gates are recorded,
- live verify is either passed or explicitly not applicable,
- `closeout.md` states deviations and remaining follow-ups.
