---
title: Feature Index
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
---

# Feature Index

Finale Feature-Ordnung: erledigte und baseline-nahe Themen stehen vorne;
aktive, gemischte oder gate-lastige Themen stehen weiter hinten.

| ID | Feature | Status | Warum hier |
|---|---|---|---|
| 001 | `001-platform-baseline` | baseline | Projektgrundlage, kein aktiver Slice |
| 002 | `002-devstack-bootstrap-env-persistence` | static_done_live_open | Lokale Ops weitgehend erledigt; Postgres/Alembic/Bootstrap-Live-Evidence offen bzw. nachzuziehen |
| 003 | `003-frontend-merger-shell` | static_done_live_open | Shell gebaut, aber Browser/Full-Stack-Live-Smoke offen |
| 004 | `004-matrix-homeserver-connectivity` | partial_local_live | Tuwunel, lokale `.well-known`, dev credential recovery und setup-users live verifiziert; Mobile/Tunnel/Federation bleiben offen |
| 005 | `005-matrix-chat-core` | static_done_live_open | Matrix UI stark implementiert, aber echte Homeserver-Sitzung/E2EE/Media/Calls live offen |
| 006 | `006-appservice-nats-e2ee-bridges` | unencrypted_live_verified_e2ee_open | Unverschlüsselter Matrix API -> Tuwunel -> Go -> NATS -> Python -> NATS -> Matrix Raum Pfad live grün; E2EE/Keys/Browser-Matrix offen |
| 007 | `007-agent-chat-voice-runtime` | mixed_open | Agent Chat statisch verifiziert; Stack/Approval/Provenance live offen, Voice nicht vollständig implementiert/verifiziert |
| 008 | `008-agentic-ui-generative-ui-mcp` | static_verified_live_pending | A2UI/Copilot/Python-Emitter statisch verifiziert, #93/#94/#95 entschieden |
| 009 | `009-multi-agent-a2a-orchestration` | mixed_open | A2A-Client/AgentCards/Graph/Rollen statisch verifiziert; Delegation/Checkpoint/Per-User-Routing offen |
| 010 | `010-control-ui-runtime-surfaces` | mixed_open | Shell/BFF/Queries stehen; viele Tabs brauchen Live-Daten-Audit; Control ist Anzeige/Admin, kein Agent-Tool-Surface by default |
| 011 | `011-llm-gateway-models-routing-billing` | backend_streaming_live_partial | Backend default-model/OpenRouter SSE live verifiziert; UI picker, tool-call shape, spend dashboard und Production credential drills offen |
| 012 | `012-memory-context-world-personal-kb` | implementation_open | Hindsight/MemPalace/Fusion-Agent-Memory in Postgres; upstream/room-session/injection/hydration/eval offen |
| 013 | `013-sandbox-security-hitl` | mixed_open | Security-Logik statisch verifiziert, URL-preview dev config explizit; HITL/OpenSandbox/Consent/Audit live offen |
| 014 | `014-observability-harness-evals` | mixed_open | Harness/Export statisch verifiziert; Live-Trace/Audit/Eval-Persistence offen |
| 015 | `015-scheduler-skills-planning-automation` | mixed_open | Scheduler/Skills/Plan statisch verifiziert; Live-Delivery, Skill-Feedback und Promotion offen |
| 016 | `016-meta-harness-agent-optimization` | implementation_started | Scenario runner, trace gates, ToolRegistry eval, CLI/MCP run surface, artifact store, holdout split, official `_ref/meta-harness`, Matrix domain spec and proposer skill started |
| 017 | `017-knowledge-graph-bitemporal-claims` | planned | Global/domain KG ueber nonicdb/NornicDB-Linie: bitemporale Claims, Projection, Decay-Retrieval und Provenance |
| 018 | `018-database-schema-governance` | planned | Alembic bleibt authoritative, lesbare Current-Schema-Registry und Introspection-Gates |
| 019 | `019-hybrid-rag-retrieval` | implementation_started | Eigenes RAG/HiRAG-Feature: OpenRouter Embeddings, LightRAG/HippoRAG/LinearRAG-Eval, Context Bubble, Self-RAG und Fusion |
| 020 | `020-agent-harness-subagents-routing` | planned | Graphless/LangGraph/dispatcher routing, future subagent contracts and HermesAgent-style harness lessons without coding-agent product scope |
| 021 | `021-ingestion-paperwatcher-researchwatcher` | planned | Source ingestion, Paperwatcher/Researchwatcher adoption, artifact registry, citations and KG proposal handoff |
| 022 | `022-rag-kg-benchmark-lab` | planned | Evidence lane for vector, fused KG, LightRAG/HippoRAG-style candidates, matched budgets and Meta-Harness promotion decisions |
| 023 | `023-auto-optimization-inner-loops` | planned | AutoRAG/autoresearch-style inner loops for RAG, extraction, memory/context and tool-policy candidates feeding Meta-Harness |

See `REVIEW_001_023_2026-04-27.md` for the current done/live/research/open
classification. Do not read `implementation_done` in older feature frontmatter
as final closeout unless the corresponding `live-verify.md` has evidence or an
explicit out-of-scope decision.

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

Cross-feature execution is tracked in `WORKPLAN_001_022.md` and will be
renamed after Feature 023 consolidation.

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
- Feature 019: provider-konfigurierbare Embeddings, vector/KG/fused retrieval,
  Context Bubble, Self-RAG/citation verification and GraphRAG candidate evals
- Feature 020: agent harness routing/subagent contracts across dispatcher,
  LangGraph and graphless simple runner
- Feature 021: ingestion/Paperwatcher source artifacts, citation refs and
  explicit KG proposal handoff
- Feature 022: RAG/KG benchmark lab with fixed budgets, holdout and promotion
  evidence for graph retrieval candidates
- Feature 023: bounded inner-loop optimization over RAG, extraction,
  memory/context and tool-policy candidates that emits Meta-Harness artifacts
