---
title: SDD Status Board
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
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
| 001 | Platform Baseline | closed_static | none | yes |
| 002 | Devstack Bootstrap, Env and Persistence Ops | static_closed_live_pending | operator/live bootstrap check | yes, static scope closed; live verify deferred |
| 003 | Frontend Merger and Shell | static_closed_live_pending | user-local full-stack live smoke | yes, static scope closed; live verify deferred |
| 004 | Matrix Homeserver, Connectivity and Mobile/Federation | static_classified_live_pending | Tuwunel/mobile/connectivity check | not as long as upstream monitoring is active |
| 005 | Matrix Chat Core | static_classified_live_pending | live Matrix session | no, live verify required |
| 006 | Appservice, NATS, E2EE and Bridges | static_verified_live_pending | A4 E2E publish/subscribe/decrypt | no, A4 pending |
| 007 | Agent Chat and Voice Runtime | static_verified_live_pending | BFF/Gateway/Python/tool/voice live verify | no, live verify required |
| 008 | Agentic UI, Generative UI and MCP | static_verified_live_pending | native A2UI live roundtrip | no, live A2UI/MCP verify remains |
| 009 | Multi-Agent and A2A Orchestration | static_verified_live_pending | A2A live smoke | no, A2A never live-tested |
| 010 | Control UI and Runtime Surfaces | static_verified_live_pending | tab-by-tab data-display/backend walkthrough | no, backend integration mixed; not an agent-tool surface |
| 011 | LLM Gateway, Models, Routing and Billing | static_verified_live_pending | LiteLLM/billing/routing live verify | no |
| 012 | Memory, Context, World Model and Personal KB | static_verified_live_pending | memory_fusion/context live verify + Hindsight/MemPalace upstream/session checks | no |
| 013 | Sandbox, Security and HITL | static_verified_live_pending | Skills-Guard HITL live verify | no |
| 014 | Observability, Harness and Evals | static_verified_live_pending | live trace + audit/eval evidence | no |
| 015 | Scheduler, Skills, Formal Planning and Automation | static_verified_live_pending | scheduler live delivery + real-LLM skill verify | no |
| 016 | Meta-Harness Agent Optimization | implementation_started | official-domain-spec loop + richer scenario coverage + promotion gate | no |
| 017 | Knowledge Graph, Bitemporal Claims and Decay Retrieval | planned | global/domain nonicdb/NornicDB KG schema/projection design | no |
| 018 | Database Schema Governance | implementation_done | keep registry updated with future migrations | yes |
| 019 | Hybrid RAG and Retrieval | implementation_started | OpenRouter embedding live verify + GraphRAG candidate evals | no |

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

## Open Work Triage

The post-static-pass open queue is tracked in `OPEN_WORK_TRIAGE.md`.

Current unchecked SDD items: 145.

The queue was trimmed on 2026-04-26: unchecked boxes now mean either active
implementation work in `tasks.md` or true acceptance gates in `gates.md`.
Procedure details in `live-verify.md`, acceptance prose in `spec.md`, and
template placeholders no longer count as open work.
Decision/defer questions were moved to `DECISION_BACKLOG.md`.

Work is split into four execution waves:

1. Local implementation cleanup with no full live stack. Done for current
   Wave-1 scope.
2. Local full-stack live verify batch.
3. Agent runtime live verify batch.
4. External capability verify.

## Implementation Progress After Static Pass

2026-04-25:

- Feature 001 closed for static SDD scope.
- Feature 002 closed for static/buildless scope; live/operator bootstrap remains
  deferred by instruction.
- Feature 003 closed for static frontend scope: lint, typecheck, Vitest and
  Turbopack build pass; browser/full-stack route smoke remains deferred.
- Feature 004 static homeserver/connectivity classification complete; live
  startup/mobile/tunnel checks remain deferred.
- Feature 005 Matrix gate groups classified; `/matrix` build route confirmed;
  real Matrix session remains deferred.
- Feature 006 static Go/Python checks pass; thread reply metadata, Python
  routed-subject subscription, NATS agent-subject allowlist and Go subject
  sanitization gaps fixed; A4 E2E and subject-routing live verify remain open.
- Feature 007 static frontend/Python checks pass; Agent Chat is overlay/control
  plus `/api/agent/*`, not `/agent`; approval controls, context rail and
  markdown sanitizer static coverage added; full-stack and voice live verify
  remain deferred.
- Feature 008 static A2UI/Copilot/Python-emitter checks pass; #93/#94/#95 and
  MCP external-auth decisions recorded; MCP/WebMCP and visible live A2UI
  roundtrips remain deferred.
- Feature 009 static A2A/dispatcher/router checks pass; A2A SSE delta parsing,
  graph compile, role tool allowlists, Matrix agent-name sanitization, default
  DM routing decision, per-user default-model lookup and per-user agent
  settings contract gaps fixed; live delegation remains deferred.
- Feature 010 static Control shell/BFF/query surfaces verified; tab-by-tab
  live/mock ownership walkthrough remains deferred.
- Feature 011 static billing/model/routing/resilience checks pass; routing race,
  keyword quality, persisted model selection and eval-id semantics follow-ups
  are closed/accepted; live LiteLLM/provider/DB spend verification remains
  deferred.
- Feature 012 static memory/context/compaction/backend primitive checks pass;
  eval classes/metrics, World Model contracts and Personal KB capture/import
  contracts are defined; implementation/live verify remain open.
- Feature 013 static prompt-scanner/redaction/Skills-Guard checks pass; active
  dev URL-preview config and BFF/FastAPI verdict parsing are covered;
  OpenSandbox/HITL live verify and prod config check remain open.
- Feature 014 static harness/insights/trajectory/control-runtime checks pass;
  async evaluator, cache, scorer interface, proposer/evaluator integration and
  exec-eval workpack migration are covered; live trace, audit and eval evidence
  remain deferred.
- Feature 015 static scheduler/skills/plan/security checks pass; skill loader
  source modes, disabled filtering and PDDL refusal/repair contract are covered;
  live scheduler delivery and real-LLM skill verification remain deferred.
- Feature 016 created from Meta-Harness deepdive and first slices implemented:
  Python-only in-process and live-service scenario runner, ToolRegistry-aware
  legacy evaluator, trace gates, candidate artifact layout, CLI/MCP scenario
  run surfaces, normalized search-set tool names, protected holdout split,
  proposer artifact/decision-history input, keep/discard/defer decision log and
  tests. Official Stanford repo is vendored under `_ref/meta-harness`; initial
  Matrix `domain_spec.md` and proposer skill exist. Promotion gate, external
  proposer opt-in guard and richer scenario coverage remain open.

## Closure Rule

`implementation_done` is not `closed`. A feature closes only when:

- legacy sources are summarized or linked with provenance,
- open tasks live in `tasks.md`,
- automated verify gates are recorded,
- live verify is either passed or explicitly not applicable,
- `closeout.md` states deviations and remaining follow-ups.
