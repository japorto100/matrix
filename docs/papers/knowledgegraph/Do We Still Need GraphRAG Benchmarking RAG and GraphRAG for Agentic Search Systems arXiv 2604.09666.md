# Do We Still Need GraphRAG? Benchmarking RAG and GraphRAG for Agentic Search Systems

Source: https://arxiv.org/pdf/2604.09666
Local PDF: `docs/papers/knowledgegraph/Do We Still Need GraphRAG Benchmarking RAG and GraphRAG for Agentic Search Systems arXiv 2604.09666.pdf`

## Bibliography

- Authors: Dongzhe Fan, Zheyi Xue, Siyuan Liu, Qiaoyu Tan.
- arXiv: 2604.09666v1 `[cs.IR]`.
- Date: 2026-04-01.
- Code: https://github.com/FanDongzhe123/RAGSearch.

## Core Claim

The paper introduces RAGSearch, a benchmark comparing dense RAG and multiple
GraphRAG retrieval infrastructures under agentic search. It asks whether
multi-round agentic retrieval can compensate for the missing explicit graph
structure in dense RAG.

Main conclusion:

- Agentic search substantially improves dense RAG and narrows the gap to
  GraphRAG.
- GraphRAG remains more useful and stable for complex multi-hop reasoning,
  especially when graph construction cost can be amortized.
- Dense RAG remains a practical baseline for general QA because graph
  construction and retrieval overhead may not pay off for simpler tasks.

## Matrix Relevance

Feature 017 should not assume that every query needs the global KG. The global
KG/nonicdb path is justified for world/trading/geopolitical/macro claims where
relations, temporal validity, provenance and multi-hop joins matter. For simple
lookup or general QA, dense vector retrieval plus agentic query decomposition is
the lower-cost baseline.

Adopt:

- Treat dense RAG and graph/KG retrieval as interchangeable retrieval
  backends behind one agentic interface.
- Benchmark vector-only, KG-only and fused retrieval under the same query
  budget, model, context budget and answer rubric.
- Add explicit multi-hop canaries where graph structure should win.
- Track offline graph construction cost, online latency, retrieval stability
  and answer faithfulness, not only answer accuracy.
- Keep GraphRAG as a precision/stability layer for complex relational tasks,
  not a default prompt-stuffing source.

Do not adopt blindly:

- Replacing graph work with agentic dense RAG for all tasks.
- Shipping KG infrastructure without a dense-RAG baseline and cost comparison.
- Evaluating GraphRAG as a monolithic app instead of a retrieval backend that
  can be swapped under the same agentic control loop.

## Feature 017 Implications

- `017.6 Hybrid Graph-Vector Retrieval` needs a RAGSearch-style evaluation:
  vector-only, KG-only and fused modes under matched budgets.
- The first nonicdb/NornicDB global KG slice should target relational,
  multi-hop and temporal questions, not generic memory recall.
- Meta-Harness scenarios should include both easy general QA where vector
  retrieval is expected to be enough and multi-hop cases where KG context is
  expected to improve stability.
- Promotion gates should require evidence that KG improves the target class
  after accounting for graph build cost and runtime latency.

## Open Questions For Matrix

- What are the first trading/geopolitical multi-hop canaries where global KG
  should beat dense RAG?
- Which metric is primary for our use case: answer faithfulness, provenance
  completeness, retrieval hit rate, latency or analyst usefulness?
- Should the first eval use RAGSearch directly, or mirror its protocol with
  Matrix-native trading/world questions?
