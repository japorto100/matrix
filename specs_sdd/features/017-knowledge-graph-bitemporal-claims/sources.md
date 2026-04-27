---
title: Knowledge Graph Sources
status: draft
owner: filip
created: 2026-04-26
updated: 2026-04-27
feature_id: 017
---

# Sources

| Source | Use |
|---|---|
| `main_docs/root/MEMORY_ARCHITECTURE.md` | KG lane concepts, M1-M5 storage roles, Fast/Slow Lane split and GraphMERT Phase-2 Slow-Lane refinement. |
| `main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` | GraphRAG retrieval and context integration. |
| `specs/execution/exec-world-model.md` | World evidence/claim/KG plan, Roynard four-layer mapping, IE L0-L6 pipeline and GraphMERT Wisdom validation lane. |
| `specs_sdd/features/012-memory-context-world-personal-kb` | Evidence, memory and world/KB boundary owner. |
| `specs_sdd/features/010-control-ui-runtime-surfaces` | `/memory/kg` and provenance graph surfaces. |
| `docs/papers/knowledgegraph/*` | GraphRAG, conflict, adaptive retrieval and cognitive memory-layer research corpus. |
| `docs/papers/knowledgegraph/NomicDB/THE MISSING KNOWLEDGE LAYER IN COGNITIVE ARCHITECTURES FOR AI AGENTS arXiv 2604.11364.{pdf,md}` | Four-layer cognitive decomposition: Knowledge, Memory, Wisdom, Intelligence. Used to prevent one-store/one-policy KG design. |
| `docs/papers/knowledgegraph/Do We Still Need GraphRAG Benchmarking RAG and GraphRAG for Agentic Search Systems arXiv 2604.09666.{pdf,md}` | RAGSearch benchmark: dense RAG vs GraphRAG under agentic search; informs vector/KG/fusion eval gates. |
| `jha-lab/graphmert_umls` | GraphMERT reference implementation noted by `MEMORY_ARCHITECTURE.md`; evaluate as optional Slow-Lane/Wisdom batch validator, not as initial KG source of truth. |
| `jha-lab/GraphMERT_data`, `jha-lab/filtered_UMLS` | Public GraphMERT datasets found on Hugging Face; no confirmed official public model checkpoint found on 2026-04-27. |
| `Nelumbium-Capital/GraphMert` | Small community Finance-KG GraphMERT implementation; reference only until evaluated. |
| `specs_sdd/features/019-hybrid-rag-retrieval` | Owns answer-time RAG retrieval, LightRAG/HippoRAG/LinearRAG evals and context assembly. |
| `_ref/NornicDB` | First global KG backend/projection candidate; evaluate current state before adoption. |
