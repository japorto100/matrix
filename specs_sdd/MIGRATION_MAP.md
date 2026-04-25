---
title: Specs SDD Migration Map
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
---

# Migration Map

This file is the routing table from legacy docs to `specs_sdd/`. It uses the
final 15-feature model from `FEATURE_DETERMINATION.md`.

Legend:

- `feature`: goes into `features/NNN-*/`
- `adr`: binding decision candidate
- `research`: non-binding investigation
- `journal`: chronological log or handoff
- `archive`: historical only
- `evidence`: raw supporting artifact

## Final Feature Set

| ID | Folder | Status | Primary Sources |
|---|---|---|---|
| 001 | `features/001-platform-baseline` | baseline | `specs/00-overview.md`, `specs/08-tooling.md`, `specs/09-privacy.md`, `specs/10-portierung.md`, `specs/FUTURE_IDEAS.md`, `specs/agent-output-pattern.md` |
| 002 | `features/002-devstack-bootstrap-env-persistence` | implementation_done | `specs/05-devstack.md`, `exec-linux-setup-users`, `exec-secrets-bootstrap`, `exec-postgres-tuning`, `archive/exec-19-devstack-consolidation.md`, env-layout finding |
| 003 | `features/003-frontend-merger-shell` | implementation_done | branch exec folder, `exec-merge-chat-SUPERSEDED`, Superpowers frontend merger v1/v2/design |
| 004 | `features/004-matrix-homeserver-connectivity` | active_monitoring | `specs/01-homeserver.md`, `07-mobile`, `11-bore-tunnel`, `12-connectivity`, `exec-matrix-monitor`, `exec-blocking` C1-C6 |
| 005 | `features/005-matrix-chat-core` | implementation_done | `specs/04-nextjs-chat.md`, all `exec2-*`, archived Matrix UI/review/refactor slices |
| 006 | `features/006-appservice-nats-e2ee-bridges` | implementation_done_live_verify_open | `specs/02-go-appservice.md`, `03-python-agent-bridge`, `06-e2ee`, `13-e2ee-agent-architecture`, `exec-05*` |
| 007 | `features/007-agent-chat-voice-runtime` | implementation_done_live_verify_open | `specs/14-agent-chat-ui-enhancements.md`, `specs/agent-ui/*`, `exec-06`, archived `exec-08`, relevant `exec-hermes` rows |
| 008 | `features/008-agentic-ui-generative-ui-mcp` | mostly_built | `exec-09`, `exec-20`, Superpowers A2UI/CopilotKit design and v2 plan, `Copilotkit_additional.md` |
| 009 | `features/009-multi-agent-a2a-orchestration` | implementation_done_live_verify_open | `exec-10`, A2A/Mention sections from `exec2-04`, Superpowers task #94 |
| 010 | `features/010-control-ui-runtime-surfaces` | frontend_built | `exec-15`, archived `exec-13`, branch `VERIFY-GATES.md` Control UI sections |
| 011 | `features/011-llm-gateway-models-routing-billing` | in_progress | `exec-16`, `exec-a2fm`, ADR smart routing gate, A2FM research, relevant `exec-19` stage 5 |
| 012 | `features/012-memory-context-world-personal-kb` | mixed_active | `exec-11`, `exec-memory`, `exec-context`, `exec-world-model`, `exec-personal-kb`, memory boundary finding |
| 013 | `features/013-sandbox-security-hitl` | mixed_active | `specs/16-security.md`, `exec-12`, `exec-security`, ADR-004, opensandbox usecases |
| 014 | `features/014-observability-harness-evals` | in_progress | `exec-17`, `exec-harness`, `exec-eval`, ADR-002, harness analysis, observability tier strategy |
| 015 | `features/015-scheduler-skills-planning-automation` | mixed_active | `exec-scheduler`, `exec-scheduler2`, `exec-skills`, `exec-14-pddl`, `exec-14-DSPy`, PDDL delta, ADR-003 |

## Meta Destinations

| Destination | Sources | Rule |
|---|---|---|
| `archive/schema-history/` | `specs/17-schema-ownership.md`, `archive/exec-18-unified-agent-schema-SUPERSEDED.md` | Historical input only; no central schema feature. |
| `research/backlog/` | `specs/15-document-preview-evaluation.md`, `exec-media-ingestion`, `exec-openworldlib`, `exec-ebm`, `exec-rust`, `exec-transformersjs`, `exec-notifications`, `archive/exec-transformers-js-SUPERSEDED.md`, `Superpowers_TestTimeCompute.md` | Promote to feature only when active implementation scope is chosen. |
| `journal/` | `docs/superpowers/findings/2026-04-22-open-tasks.md`, `2026-04-22-overnight-findings.md`, `docs/superpowers/journal/*`, `specs/execution/superpower-impl-log.md` | Extract concrete work into feature `tasks.md`; journal remains chronological. |

## Main Docs and Papers

Detailed mapping lives in `MAIN_DOCS_COVERAGE.md`.

| Source | Destination |
|---|---|
| `main_docs/root/MEMORY_ARCHITECTURE.md` | Feature 012 |
| `main_docs/root/CONTEXT_ENGINEERING.md` | Feature 012 |
| `main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` | Feature 012 |
| `main_docs/root/AGENT_ARCHITECTURE.md` | Features 009 / 012 / 015 |
| `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md` | Features 009 / 012 / 015 |
| `main_docs/root/AGENT_SECURITY.md` | Features 013 / 012 |
| `main_docs/root/AGENT_HARNESS.md` | Features 014 / 013 |
| `main_docs/specs/architecture/FRONTEND_ARCHITECTURE.md` | Features 003 / 010 |
| `main_docs/specs/data/*.md` | Features 002 / 010 / 012 |
| `docs/papers/knowledgegraph/*` | Feature 012 research |
| `docs/papers/extraction/*` | Features 010 / 012 research |

## Cross-Cutting Legacy Docs

| Source | Destination | Notes |
|---|---|---|
| `specs/execution/README.md` | `journal/` plus `features/README.md` | Historical old execution index; new entrypoint is `specs_sdd/features/README.md`. |
| `specs/execution/EXECUTION-ORDER.md` | `journal/` plus affected feature `tasks.md` | Old cluster-board. Keep as historical planning input; do not use as canonical SDD board. |
| `specs/execution/exec-blocking.md` C1-C6 | Feature 004 | Matrix/homeserver/connectivity blockers. |
| `specs/execution/exec-blocking.md` C7 | Feature 007 | Streaming SSE default. |
| `specs/execution/exec-blocking.md` C8 | Feature 006 | NATS JetStream at-least-once delivery. |
| `specs/execution/exec-blocking.md` C9 | Feature 014 / ADR-0002 | Tracing and audit parallel stores. |
| `specs/execution/exec-blocking.md` C10 | Feature 012 | Per-model context thresholds. |
| `specs/execution/exec-blocking.md` C11 | Features 007, 012, 014 | Phase-B carried-forward debt. |
| `specs/execution/exec-hermes.md` | owning features by row | Adoption index, not a feature. Each WIRED/PLANNED row maps to its owning feature. |

## Superpowers Distribution

| Source | Destination | Type |
|---|---|---|
| `docs/superpowers/findings/2026-04-22-open-tasks.md` | `journal/` plus affected feature tasks | journal/task backlog |
| `docs/superpowers/findings/2026-04-22-overnight-findings.md` | `journal/` or `research/backlog/` after split | journal/research |
| `docs/superpowers/findings/2026-04-23-a2fm-paper-research-phase2.md` | `features/011-llm-gateway-models-routing-billing/research.md` | research |
| `docs/superpowers/findings/2026-04-23-adr-002-tracing-audit-parallel-stores.md` | `adr/0002-tracing-audit-parallel-stores.md` | adr |
| `docs/superpowers/findings/2026-04-23-adr-003-exec-14-dspy-gating.md` | `adr/0003-dspy-gating.md` | adr |
| `docs/superpowers/findings/2026-04-23-adr-004-sandbox-hitl-layer.md` | `adr/0004-sandbox-hitl-layer.md` | adr |
| `docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md` | `adr/0001-smart-routing-rollout-gate.md` | adr |
| `docs/superpowers/findings/2026-04-23-harness-mode-analysis.md` | `features/014-observability-harness-evals/research.md` | research |
| `docs/superpowers/findings/2026-04-23-harness-mode-analysis.csv` | `features/014-observability-harness-evals/evidence/` | evidence |
| `docs/superpowers/findings/2026-04-24-env-layout-decision.md` | `features/002-devstack-bootstrap-env-persistence/research.md` or ADR | research/adr |
| `docs/superpowers/findings/2026-04-24-memory-umbrella-boundaries.md` | `features/012-memory-context-world-personal-kb/research.md` | research |
| `docs/superpowers/findings/2026-04-24-observability-tier-strategy.md` | `features/014-observability-harness-evals/research.md` | research |
| `docs/superpowers/journal/2026-04-23.md` | `journal/2026-04-23.md` | journal |
| `docs/superpowers/journal/README.md` | `journal/README.md` | journal |
| `docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan.md` | `features/003-frontend-merger-shell/research.md` | superseded plan |
| `docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md` | `features/003-frontend-merger-shell/tasks.md` and `features/008-agentic-ui-generative-ui-mcp/tasks.md` | plan/tasks |
| `docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md` | `features/003-frontend-merger-shell/plan.md` and `features/008-agentic-ui-generative-ui-mcp/plan.md` | plan |

## Superseded / Historical Sources

| Source | Verdict | Destination |
|---|---|---|
| `specs/execution/archive/exec-02-missing-features.md` | historical | Feature 005 closeout/history |
| `specs/execution/archive/exec-03-review-fixes.md` | historical | Feature 005 closeout/history |
| `specs/execution/archive/exec-04-ui-rework.md` | superseded | Feature 005 history |
| `specs/execution/archive/exec-07-refactoring.md` | historical done | Feature 005 history |
| `specs/execution/archive/exec-08-agent-backend-voice.md` | superseded/merged | Feature 007 history |
| `specs/execution/exec-13-ui-kg-extensions.md` | archived | Feature 010 and Feature 012 |
| `specs/execution/archive/exec-18-unified-agent-schema-SUPERSEDED.md` | superseded | `archive/schema-history/` |
| `specs/execution/archive/exec-19-devstack-consolidation.md` | superseded/split | Features 002, 003, 011, research backlog |
| `specs/execution/archive/exec-merge-chat-SUPERSEDED.md` | superseded | Feature 003 history |
| `specs/execution/archive/exec-transformers-js-SUPERSEDED.md` | superseded duplicate | `research/backlog/` |
| `specs/execution/archive/pddl_phase22b_delta.md` | superseded delta | Feature 015 history |
| `docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan.md` | superseded by v2 | Feature 003 history |

## Implemented But Not Closed

These sources must keep open live-verify or decision tasks:

- `exec-05-nats-e2ee-pipeline.md`: A4 E2E pending.
- `exec-06-agent-chat-integration.md`: SSE/API/voice full-stack verify pending.
- `exec-09-protocols-generative-ui.md`: LLM-to-A2UI live roundtrip partial.
- `exec-10-multi-agent.md`: A2A never live-tested.
- `exec-12-sandbox-security.md`: HITL decision pending.
- `exec-15-memory-control-ui.md`: full tab-by-tab backend walk-through pending.
- `exec-16-llm-provider-gateway.md`: routing rollout and spend/user-picker live gaps.
- `exec-17-observability-harness-traces.md`: live traces/OpenObserve pending.
