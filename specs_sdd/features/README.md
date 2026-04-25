---
title: Feature Index
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
---

# Feature Index

Finale Feature-Ordnung: erledigte und baseline-nahe Themen stehen vorne;
aktive, gemischte oder gate-lastige Themen stehen weiter hinten.

| ID | Feature | Status | Warum hier |
|---|---|---|---|
| 001 | `001-platform-baseline` | baseline | Projektgrundlage, kein aktiver Slice |
| 002 | `002-devstack-bootstrap-env-persistence` | implementation_done | Lokale Ops weitgehend erledigt |
| 003 | `003-frontend-merger-shell` | implementation_done | Shell gebaut, nur Live-Smoke offen |
| 004 | `004-matrix-homeserver-connectivity` | active_monitoring | Externe Blocker/Monitoring, aber Basis fuer Matrix |
| 005 | `005-matrix-chat-core` | implementation_done | Implementiert, Live-Verify-Schuld |
| 006 | `006-appservice-nats-e2ee-bridges` | implementation_done_live_verify_open | Implementiert, A4 E2E offen |
| 007 | `007-agent-chat-voice-runtime` | implementation_done_live_verify_open | Implementiert, Stack/Voice-Verify offen |
| 008 | `008-agentic-ui-generative-ui-mcp` | mostly_built | Viel gebaut, Phase-2-Gaps |
| 009 | `009-multi-agent-a2a-orchestration` | implementation_done_live_verify_open | A2A live unverified |
| 010 | `010-control-ui-runtime-surfaces` | frontend_built | Frontend steht, Integration quer ueber Backends |
| 011 | `011-llm-gateway-models-routing-billing` | in_progress | Routing/Billing/Gates aktiv |
| 012 | `012-memory-context-world-personal-kb` | mixed_active | Umbrella mit offenen Subfeatures |
| 013 | `013-sandbox-security-hitl` | mixed_active | ADR-004 entschieden, HITL live offen |
| 014 | `014-observability-harness-evals` | in_progress | Infra live, Spec/Gates/Evidence offen |
| 015 | `015-scheduler-skills-planning-automation` | mixed_active | Scheduler/Skills teils gebaut, PDDL/DSPy gated |

## Meta-Bereiche

| Bereich | Ort | Zweck |
|---|---|---|
| Schema history | `../archive/schema-history/` | `exec-18` und zentrale Schema-Planung als Historie |
| Research backlog | `../research/backlog/` | Media, EBM, Rust, OpenWorldLib, notifications, transformers.js |
| Journal/handoff | `../journal/` | Bootstrap-, Session- und Superpowers-Handoff-Logs |

## Feature-Dateien

Jedes Feature besitzt den SDD-Kernsatz:

- `plan.md`
- `tasks.md`
- `live-verify.md`
- `closeout.md`
- `spec.md`

Optional kommen beim eigentlichen Content-Import dazu:

- `sources.md`
- `gates.md`
- `research.md`
- `contracts/`
- `evidence/`

## Live-Verify-Schwerpunkte

Die umfangreichsten Live-Verify-Listen liegen hier:

- Feature 003: Shell, Routes, Files/Memory/Control entrypoints
- Feature 005: Matrix Chat Core, `exec2-04` Gate-Gruppen A-O
- Feature 006: Matrix -> Appservice -> NATS -> Python E2EE handoff
- Feature 007: Agent Chat SSE, tools, approvals, voice
- Feature 008: A2UI/CopilotKit/MCP live roundtrip
- Feature 010: Control UI tab-by-tab walkthrough
- Feature 011: LLM gateway, model picker, spend, smart routing
