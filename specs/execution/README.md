# Execution Slices

Operative Umsetzungspläne mit Checkboxen und Verify Gates.
Werden abgearbeitet und als Referenz behalten.

## 🎯 Priorisierter Durchlauf → [`EXECUTION-ORDER.md`](./EXECUTION-ORDER.md)

Living document mit 3-wellen plan:
- **Welle 1**: verify-gates für exec-05/06/09/10/12/15/17 (existing code prüfen)
- **Welle 2**: Phase-C tail + Option-3 features (smart-routing review, frontend, title-gen)
- **Welle 3**: planning-arbeit für isolation / A2FM-ML-router / EBM / world-model / personal-kb

Die "Empfohlene Reihenfolge" unten ist die **domänen-orientierte** sicht (memory/context/harness). `EXECUTION-ORDER.md` ist die **phasen-orientierte** sicht für den tagesgeschäft-durchlauf.

## Empfohlene Reihenfolge (Memory / World Model / Personal KB / Context / Harness — 2026-04)

1. **Specs abstimmen:** [`exec-memory.md`](./exec-memory.md), [`exec-world-model.md`](./exec-world-model.md), [`exec-personal-kb.md`](./exec-personal-kb.md), [`exec-context.md`](./exec-context.md), [`exec-harness.md`](./exec-harness.md), [`exec-skills.md`](./exec-skills.md) — Refs `_ref/mempalace`, `_ref/agno` (siehe [`exec-18-unified-agent-schema.md`](./exec-18-unified-agent-schema.md)).
2. **Memory sauber schneiden:** `exec-memory` = Personal Memory, `exec-world-model` = globale Wissensseite, `exec-personal-kb` = user-kuratierte KB.
3. **Code zuerst Runtime:** `exec-context` (Python: `agent/llm_client.py`, `context/merge.py`) — Retrieval-/Assembly-Regeln, Compaction, Caching, Prompt-Economics.
4. **Parallel Eval:** MemPalace vs Hindsight (siehe exec-memory §5) — Artefakte unter `python-backend/experiments/memory_eval/` möglich, DB optional.
5. **Schema bei Bedarf:** `exec-18` — Bridges / Claims / KB / `agent.evals`, wenn Persistenzentscheidungen stabil sind.
6. **Harness danach explizit:** `exec-harness` fuer layer-aware / consumer-aware Tuning, nicht nur generische Trace-Optimierung.
7. **UI:** [`exec-15-memory-control-ui.md`](./exec-15-memory-control-ui.md) + Agent-Chat ([`exec-06`](./exec-06-agent-chat-integration.md), [`exec-merge-chat.md`](./exec-merge-chat.md)), wenn APIs stehen.

| Datei | Inhalt | Status |
|---|---|---|
| exec-05-nats-e2ee-pipeline.md | NATS E2EE Pipeline (Go↔Python Bridge) | ✅ Implementiert |
| exec-05b-messaging-bridges.md | Messaging Bridges (NATS → Memory) | Geplant |
| exec-05c-agent-isolation.md | Agent-Isolation (NATS Routing, Key Deletion, Hybrid E2EE) | Geplant |
| exec-06-agent-chat-integration.md | Shared Components (CodeBlock, ImagePreview, Location) | ✅ Phase 5 in Arbeit |
| exec-09-protocols-generative-ui.md | MCP Server, Generative UI, A2A Protocol | ✅ Implementiert |
| exec-10-multi-agent.md | Multi-Agent Orchestrierung (Trading Roles) | ✅ Implementiert |
| exec-11-memory-evolution.md | Hindsight Memory Engine (4 Networks) | ✅ Phase 1 implementiert |
| exec-12-sandbox-security.md | OpenSandbox + Security Hardening | ✅ Phase 1+2 implementiert (03.04.2026) |
| exec-13-ui-kg-extensions.md | ARCHIVIERT — alles nach exec-15 verschoben | Archiviert |
| exec-14-pddl-formal-planning.md | PDDL Formale Plan-Validierung | Geplant |
| exec-15-memory-control-ui.md | Memory & Control UI (Frontend Surfaces, KG Viz, Settings) | Geplant |
| exec-16-llm-provider-gateway.md | LLM Provider Gateway (LiteLLM + Multi-Provider Routing) | Geplant |
| exec-merge-chat.md | Chat UI Merge + Dual-Panel Layout (tradeview-fusion) | Geplant |
| exec2-01-matrix-chat-core.md | Matrix Chat Core (restructured) | Referenz |
| exec2-03b-advanced-matrix-options.md | Advanced Matrix Options (Server-Auswahl, Onboarding, BYOS, E2EE Key UI) | Geplant |
| exec2-02-protocol-infra.md | Protocol Infrastructure | Referenz |
| exec2-03-ui-rework-sota.md | UI Rework + SOTA Packages | Referenz |
| exec2-04-verify-gates.md | Gesammelte Verify Gates (Chat/E2EE/Calls) | Aktiv |

| exec-openworldlib.md | OpenWorldLib Integration Evaluation (Synthesis, Memory, Operators) | Evaluation |
| exec-ebm.md | Energy-Based Models fuer Agent Scoring, Game Theory, Commodity Markets | Evaluation |
| exec-rust.md | Rust Indicator Core & Compute Integration (aus TradeFusion portiert) | Portiert |
| exec-20-mcp-manager.md | MCP Security, Governance, Auth Proxy, Tool Filtering, MCP Apps | Evaluation |
| exec-memory.md | Memory Architecture Evaluation — Hindsight vs MemPalace vs weitere Systeme | Evaluation |
| exec-world-model.md | Global World Evidence + Claims + KG + Adjudication | Planung |
| exec-personal-kb.md | Personal Knowledgebase — Capture, Curation, Retrieval, UI-Patterns | Planung |
| exec-context.md | Context Assembly — Compaction-Trigger, Prompt-Caching, merge.py-Reihenfolge, SOTA Prompt-Economics | Evaluation / aktiv |
| exec-harness.md | Layer-aware / consumer-aware Harness Tuning, Pareto, Trace-informed Optimization | Draft |
| exec-skills.md | Skill Discovery, Refinement & Evolution — finder, refiner, SkillRL | Evaluation / Phase 1 bereit |

Archivierte Slices: `archive/`
