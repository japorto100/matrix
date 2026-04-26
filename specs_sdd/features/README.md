---
title: Feature Index
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-26
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
| 006 | `006-appservice-nats-e2ee-bridges` | static_verified_live_pending | Go/Python statisch verifiziert, A4 E2E offen |
| 007 | `007-agent-chat-voice-runtime` | static_verified_live_pending | Frontend/Python statisch verifiziert, Approval/Context/Sanitizer statisch nachgezogen, Stack/Voice offen |
| 008 | `008-agentic-ui-generative-ui-mcp` | static_verified_live_pending | A2UI/Copilot/Python-Emitter statisch verifiziert, #93/#94/#95 entschieden |
| 009 | `009-multi-agent-a2a-orchestration` | static_verified_live_pending | A2A-Client/AgentCards/Graph/Rollen statisch verifiziert, live offen |
| 010 | `010-control-ui-runtime-surfaces` | static_verified_live_pending | Shell/BFF/Queries stehen; Control ist Anzeige/Admin, kein Agent-Tool-Surface by default |
| 011 | `011-llm-gateway-models-routing-billing` | static_verified_live_pending | Billing/Model/Routing statisch verifiziert, Routing-Followups geschlossen |
| 012 | `012-memory-context-world-personal-kb` | static_verified_live_pending | Hindsight/MemPalace/Fusion-Agent-Memory in Postgres; upstream/room-session live offen |
| 013 | `013-sandbox-security-hitl` | static_verified_live_pending | Security-Logik statisch verifiziert, URL-preview dev config explizit, HITL/OpenSandbox live offen |
| 014 | `014-observability-harness-evals` | static_verified_live_pending | Harness/Export statisch verifiziert, Evidence verlinkt, Live-Trace/Audit/Eval offen |
| 015 | `015-scheduler-skills-planning-automation` | static_verified_live_pending | Scheduler/Skills/Plan statisch verifiziert, Loader-Source statisch nachgezogen, Live-Delivery offen |
| 016 | `016-meta-harness-agent-optimization` | implementation_started | Scenario runner, trace gates, ToolRegistry eval, CLI/MCP run surface, artifact store, holdout split, official `_ref/meta-harness`, Matrix domain spec and proposer skill started |
| 017 | `017-knowledge-graph-bitemporal-claims` | planned | Global/domain KG ueber nonicdb/NornicDB-Linie: bitemporale Claims, Projection, Decay-Retrieval und Provenance |
| 018 | `018-database-schema-governance` | planned | Alembic bleibt authoritative, lesbare Current-Schema-Registry und Introspection-Gates |

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
- Feature 010: Control UI tab-by-tab data-display walkthrough
- Feature 011: LLM gateway, model picker, spend, smart routing
- Feature 016: Python-only Meta-Harness scenario runner, official domain spec,
  tool/memory gates, candidate artifacts and proposer loop
- Feature 017: global/domain KG bitemporal claim schema, claim correction
  history, nonicdb/NornicDB projection and decay retrieval
- Feature 018: Alembic-head schema visibility, registry/doc generation and
  migration drift gates
