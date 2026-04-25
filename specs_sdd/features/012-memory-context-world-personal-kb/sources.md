---
title: Memory Context World KB Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
---

# Sources

## Normative / Reference Main Docs

| Source | Role in SDD |
|---|---|
| `main_docs/root/MEMORY_ARCHITECTURE.md` | Older but important architecture source for M1-M5, epistemic separation, KG lanes, storage roles and ownership matrix. |
| `main_docs/root/CONTEXT_ENGINEERING.md` | Context retrieval/merge/token-budget/compaction policy reference. |
| `main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` | RAG/GraphRAG mode and production-standard reference. |
| `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md` | Memory-write policy and runtime policy-tier reference. |
| `main_docs/root/AGENT_ARCHITECTURE.md` | Agent memory/context rules and orchestration context. |
| `main_docs/root/AGENT_SECURITY.md` | Retrieval broker, capability envelope and evidence-completeness constraints. |
| `main_docs/specs/data/DATA_ARCHITECTURE.md` | Data zones, ownership and storage-role context. |
| `main_docs/specs/data/SOURCE_STATUS.md` | Source status/trust context. |

## Execution / Superpower Sources

| Source | Role in SDD |
|---|---|
| `specs/execution/exec-11-memory-evolution.md` | Hindsight phase history. |
| `specs/execution/exec-memory.md` | Memory architecture evaluation and Hindsight/MemPalace comparison. |
| `specs/execution/exec-context.md` | Matrix-specific implementation/gate document for context assembly. |
| `specs/execution/exec-world-model.md` | World evidence/claim/KG plan. |
| `specs/execution/exec-personal-kb.md` | Personal KB capture/curation/retrieval plan. |
| `docs/superpowers/findings/2026-04-24-memory-umbrella-boundaries.md` | Boundary review accepted as stable feature split. |

## Paper / Research Corpus

| Source | Use |
|---|---|
| `docs/Memory_Autonomous_LLM_Agents_2603.07670v1.pdf` | Memory eval/governance implications; source attribution and forgetting/privacy separation. |
| `docs/papers/knowledgegraph/NomicDB/*2604.11364*` | Missing Knowledge Layer / cognitive architecture and NornicDB proposal context. |
| `docs/papers/knowledgegraph/A2RAG*` | Adaptive agentic graph retrieval research. |
| `docs/papers/knowledgegraph/Core-based Hierarchies*` | Efficient GraphRAG hierarchy research. |
| `docs/papers/knowledgegraph/EXPLORING KNOWLEDGE CONFLICTS*` | Knowledge conflict benchmark/method input for world claims. |
| `docs/papers/knowledgegraph/INTEGRATING GRAPHS*` | Graphs + LLMs + agents retrieval/reasoning survey input. |
| `docs/papers/extraction/colsmol-colflor-guide.md` | Document extraction / visual retrieval research for KB ingestion. |

## Adopted Into Matrix

- SDD is the current task/gate owner; `main_docs` remain architecture reference
  sources until explicitly superseded by accepted SDD decisions.
- Memory, context, world and KB are separate layers with separate write paths.
- Context assembly must be source/status/provenance aware.
- GraphRAG and NornicDB ideas are research inputs, not automatic backend choices.
