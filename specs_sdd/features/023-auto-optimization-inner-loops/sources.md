---
title: Auto-Optimization Inner Loops Sources
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 023
---

# Sources

| Source | Use |
|---|---|
| `_ref/auto-rag-optimizer/README.md` | Local Karpathy/autoresearch-inspired inner-loop design. |
| `_ref/auto-rag-optimizer/orchestrator.py` | Bounded config proposal, experiment log, best-config update. |
| `_ref/auto-rag-optimizer/evaluator.py` | RAGAS/LLM-as-judge evaluation pattern. |
| `_ref/auto-rag-optimizer/research_log.md` | Machine-readable experiment history pattern. |
| `docs/papers/rag/AutoRAG-Automated-Framework-Optimization-RAG-Pipeline-2410.20878.pdf` | AutoRAG framework paper. |
| `docs/papers/rag/AutoRAG-HP-Automatic-Online-HyperParameter-Tuning-RAG-2406.19251.pdf` | Online/hierarchical MAB optimization reference. |
| `https://github.com/AutoRAG/AutoRAG` | Official AutoRAG implementation reference. |
| `https://marker-inc-korea.github.io/AutoRAG/optimization/optimization.html` | AutoRAG optimization mechanics. |
| `specs_sdd/features/016-meta-harness-agent-optimization/` | Outer-loop owner and artifact format consumer. |
| `specs_sdd/features/022-rag-kg-benchmark-lab/` | Initial RAG/KG benchmark consumer. |
