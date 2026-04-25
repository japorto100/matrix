---
title: Main Docs and Papers Coverage
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
---

# Main Docs and Papers Coverage

This file maps `main_docs/` and local paper markdowns into `specs_sdd/`. These
sources are not deleted or copied wholesale. They are carried forward by
feature ownership, source ledgers and research notes.

## Root Main Docs

| Source | SDD Destination | Handling |
|---|---|---|
| `main_docs/root/MEMORY_ARCHITECTURE.md` | Feature 012 | Normative/reference source for M1-M5, epistemic separation, KG lanes, storage roles and memory ownership. |
| `main_docs/root/CONTEXT_ENGINEERING.md` | Feature 012 | Normative/reference source for context consumers, retrieval order, token budgets, merge semantics and compaction. |
| `main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` | Feature 012 | Reference source for RAG/GraphRAG runtime modes, production standards and non-goals. |
| `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md` | Features 009, 012, 015 | Runtime roles, memory-write policy, policy tiers and scheduler/Temporal-later context. |
| `main_docs/root/AGENT_ARCHITECTURE.md` | Features 009, 012, 015 | Agent role/orchestration principles, registry/tool system, memory/context rules. |
| `main_docs/root/AGENT_SECURITY.md` | Feature 013 plus 012 | Retrieval broker, capability envelope, agentic storage write path and evidence gates. |
| `main_docs/root/AGENT_HARNESS.md` | Feature 014 plus 013 | Harness principles, complete mediation, sandboxing, observability and regression gates. |
| `main_docs/root/AGENT_TOOLS.md` | Features 008, 013, 015 | Tool classifications, language/tool boundaries and planning/PDDL context. |
| `main_docs/root/AGENT_MODEL_TOKEN_TUNING.md` | Feature 011 plus 012 | Model/token tuning and context-budget implications. |
| `main_docs/root/GO_GATEWAY.md` | Features 006, 011 | Gateway ownership and Go/Python routing boundaries. |
| `main_docs/root/UNIFIED_INGESTION_LAYER.md` | Features 010, 012 | Ingestion surfaces and memory/KB routing. |
| `main_docs/root/storage_layer.md` | Features 002, 010, 012 | Storage placement and signed URL / persistence boundaries. |

## Main Specs

| Source | SDD Destination | Handling |
|---|---|---|
| `main_docs/specs/DOCUMENTATION_ARCHITECTURE.md` | Global SDD policy | Documentation ownership, SSOT, split and archive rules. |
| `main_docs/specs/EXECUTION_PLAN.md` | Feature-specific tasks/research | Old plan board; do not use as canonical SDD board. |
| `main_docs/specs/SYSTEM_STATE.md` | Status board / feature closeouts | Current-state reference only. |
| `main_docs/specs/architecture/FRONTEND_ARCHITECTURE.md` | Features 003, 010 | Frontend shell, BFF boundaries, state layers and route ownership. |
| `main_docs/specs/data/DATA_ARCHITECTURE.md` | Features 002, 010, 012 | Data zones, data product ownership and storage roles. |
| `main_docs/specs/data/STORAGE_AND_PERSISTENCE.md` | Features 002, 010, 012 | Persistence/storage policy. |
| `main_docs/specs/data/UNSTRUCTURED_INGESTION_UIL.md` | Features 010, 012 | Unstructured ingestion and KB/memory routing. |
| `main_docs/specs/data/AGGREGATION_IST_AND_GAPS.md` | Features 010, 012 | Data aggregation gaps. |
| `main_docs/specs/data/SOURCE_STATUS.md` | Feature 012 | Source trust/status context. |
| `main_docs/specs/execution/*.md` | Owning features by topic | Delta inputs, not independent feature IDs. |

## Local Papers

| Source Area | SDD Destination | Handling |
|---|---|---|
| `docs/papers/knowledgegraph/*` | Feature 012 | GraphRAG, KG, memory/knowledge/wisdom and conflict-reasoning research. |
| `docs/papers/knowledgegraph/NomicDB/*2604.11364*` | Feature 012 | Missing Knowledge Layer / NornicDB proposal context; not adopted as backend by default. |
| `docs/papers/extraction/colsmol-colflor-guide.md` | Features 010, 012 | Document extraction / visual retrieval research; routed through ingestion/File/KB backlog. |

## Current Gap

This file records coverage, not full synthesis. Feature 012 now explicitly owns
the older memory/context architecture docs. If future work depends on a
specific main-doc section, that section should be summarized inside the owning
feature before implementation starts.
