---
title: Research Pass 001-023 Agent/RAG/Memory/KG
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
scope: features 001-023
---

# Research Pass 001-023 Agent/RAG/Memory/KG

This pass checks local `_ref` projects, current Matrix code and targeted 2026+
web/paper evidence for the feature groups in
`FEATURE_GROUPS_001_023_CHECKPOINT_2026-04-27.md`.

It is intentionally pragmatic: only decisions that affect Matrix architecture or
next implementation order are recorded.

## Source Discipline

Decision evidence:

- 2026 papers.
- current official project repositories/docs.
- local benchmark/live evidence from Matrix.

Method references:

- older papers and older local project notes.
- community posts, unless backed by reproducible code/results.

Papers downloaded in this pass:

- `docs/papers/harness/Meta-Harness-End-to-End-Optimization-of-Model-Harnesses-2603.28052.pdf`
- `docs/papers/memory/MemMachine-Ground-Truth-Preserving-Memory-System-2604.04853.pdf`

Already available and used:

- `docs/papers/extraction/PDF-to-RAG-Ready-Evaluating-Document-Conversion-Frameworks-2604.04948.pdf`
- `docs/papers/extraction/Benchmarking-VLMs-French-PDF-to-Markdown-2602.11960.pdf`
- `docs/papers/extraction/MultiDocFusion-Hierarchical-Multimodal-Chunking-Pipeline-RAG-Long-Industrial-Documents-2604.12352.pdf`
- `docs/papers/knowledgegraph/Do We Still Need GraphRAG Benchmarking RAG and GraphRAG for Agentic Search Systems arXiv 2604.09666.pdf`

## High-Level Decision

The next work should not start with UI live verify alone. The highest leverage
is a short research-to-implementation pack around source grounding:

1. `021` ingestion/source artifacts/citations/parser registry.
2. `019` retrieval pipeline using those artifacts.
3. `022` benchmark lab proving retrieval modes and parser/chunking choices.
4. `023` bounded inner-loop candidates feeding `016` Meta-Harness artifacts.

Then use those artifacts to improve:

5. `012` memory/context injection.
6. `007` Agent Chat provenance and context behavior.
7. `016` real Meta-Harness traces and proposer loops.

Live verify for Matrix/UI/Control remains important, but it should not decide
RAG/KG/memory architecture before source and benchmark contracts are solid.

## Agent Harness Findings

Features:

- `007`, `009`, `011`, `012`, `013`, `014`, `015`, `016`, `020`, `023`

Local code:

- `python-backend/agent/runners/simple.py`
- `python-backend/agent/graph/*`
- `python-backend/agent/tools/registry.py`
- `python-backend/agent/middleware/*`
- `python-backend/agent/skills/*`
- `python-backend/meta_harness/*`

Reference findings:

- HermesAgent v0.11 adds a transport abstraction, provider-specific format
  conversion, auxiliary model controls, plugin hooks, shell hooks, mid-run
  steering, subagent spawn-depth controls, sibling coordination and memory
  provider fixes.
- Matrix should adopt the principles, not the product scope:
  - transport/provider formatting boundaries belong to `011`/`020`;
  - route-decision telemetry and tool-budget metadata belong to `020`/`016`;
  - pre-tool veto and tool-result transforms belong to `013` before becoming
    generic plugins;
  - subagent contracts stay future-only until search/holdout scenarios prove
    they help Matrix trading/research tasks.
- Hermes release notes also highlight compression anti-thrashing, fallback to
  main model for auxiliary tasks, session timeout hardening and memory-provider
  deduplication. Those map directly to Matrix gates in `012`, `016` and `020`.

Matrix consequence:

- before implementing subagents, add route-decision/audit metadata and parity
  scenarios for graphless vs LangGraph runners.
- do not make Control UI actions agent tools by accident.
- keep `020` as routing/subagent contract and telemetry work, not a coding
  agent feature.

## Meta-Harness Findings

Features:

- `016`, `014`, `020`, `022`, `023`

Reference findings:

- Official Meta-Harness onboarding requires a domain spec before
  implementation: task unit, fixed model, allowed harness changes, search set,
  held-out set, metrics, budget, baselines and logging.
- The proposer should read source, scores and raw traces from the filesystem and
  propose one falsifiable harness candidate. It should not self-certify by
  running the final benchmark and declaring success.
- Matrix has a good domain fit only where evaluation units are stable:
  retrieval canaries, memory lifecycle scenarios, route/tool scenarios, parser
  extraction fixtures, and bounded Agent Chat tasks.

Matrix consequence:

- `016` should maintain a Matrix `domain_spec.md`-style document or equivalent
  section before broad proposer loops.
- `023` should be the inner-loop source of candidate configs; `016` should own
  outer-loop traces, proposer ledger, heldout and promotion.
- never use Meta-Harness to optimize vague "agent feels better" sessions.

## Memory Findings

Features:

- `012`, `016`, `019`, `022`, `023`

Reference findings:

- Hindsight is a structured agent-memory system with retain/recall/reflect,
  banks, world/experience/opinion paths and multi-strategy retrieval:
  semantic, keyword, graph, temporal and reranking.
- MemPalace is local-first verbatim storage. It explicitly stores original
  content in wings/rooms/drawers and exposes agent diaries, KG operations and
  hooks for periodic save and pre-compression save. It warns that the official
  sources are GitHub, PyPI and `mempalaceofficial.com`; other domains can be
  impostors.
- MemMachine 2026 reinforces the direction that matters for Matrix:
  preserve episodic ground truth, expand retrieval around nucleus matches, and
  spend effort on retrieval depth/context formatting/query routing before
  over-optimizing ingestion-only tricks.
- Hindsight's own 2026 benchmark writing warns that LongMemEval/LoCoMo alone
  can be misleading with large context windows. We should test agentic memory:
  tool calls, research tasks, preference application and multi-session work.

Matrix consequence:

- Hindsight and MemPalace are complementary:
  - Hindsight learns structured memory and can support entity/time-aware recall.
  - MemPalace preserves verbatim session/tool evidence for exact context
    recovery.
- Pre-save must happen before both compression and compaction.
- MemPalace should remain exact-evidence-first, with Postgres/pgvector backend
  checked against upstream backend abstractions.
- Add a hydration worker or explicit deferred-embedding lane for MemPalace rows
  stored synchronously before embedding is ready.
- Agent memory injection must be a controlled tool/context path, not silent
  always-on stuffing.

## RAG / Document Conversion Findings

Features:

- `019`, `021`, `022`, `023`

2026 findings:

- `arXiv:2604.04948` is directly relevant: it compares Docling, MinerU, Marker
  and DeepSeek OCR over downstream QA. The key result for Matrix is not "choose
  parser X"; it is that metadata enrichment and hierarchy-aware chunking can
  matter more than parser choice alone. Naive GraphRAG underperformed basic RAG
  in that study.
- `arXiv:2602.11960` supports failure-mode-specific PDF-to-Markdown evaluation:
  text presence, reading order, table constraints and normalization that ignores
  harmless formatting variation.
- Microsoft MarkItDown is a strong lightweight baseline for broad file-to-
  Markdown ingestion and MCP-adjacent workflows. It should be benchmarked, not
  assumed to replace Docling/MinerU for layout-heavy PDFs.
- Researchwatcher/Paperwatcher already has the right workflow shape:
  multi-source paper search, structured metadata, PDF download/extraction,
  MCP exposure and a HiRAG-style pipeline.

Matrix consequence:

- implement parser registry around explicit parser/version metadata.
- benchmark PyMuPDF4LLM, MarkItDown, Docling and MinerU on the same fixtures.
- preserve section hierarchy, page anchors, tables, formulas, figures, code
  blocks and citation refs through chunking.
- prefer structured trading/finance sources like XBRL/CSV/API over PDF parsing
  where available.
- do not promote GraphRAG/KG retrieval without a vector-only and hierarchy-aware
  RAG baseline.

## KG / NornicDB Findings

Features:

- `017`, `019`, `021`, `022`, `018`

Reference findings:

- NornicDB positions itself as graph, vector and historical truth in one
  Neo4j-compatible engine, with hybrid vector+graph retrieval and MVCC/historical
  reads. This aligns with the desired global/domain KG direction.
- Researchwatcher KG-module reinforces a dual-store/fused approach:
  vector/BM25 search remains primary for similarity; KG adds multi-hop,
  citation relations, contradictions and research-gap structure.

Matrix consequence:

- KG is global/domain knowledge, not the agent personal-memory rail.
- source artifacts and citation refs from `021` must be the evidence input to
  `017`; do not duplicate every RAG vector into the graph.
- NornicDB/nonicdb should be evaluated as a projection target for global KG,
  with Postgres remaining authoritative for Matrix app data and Hindsight/
  MemPalace memory rows.
- GraphMERT/4-layer KG ingestion remains a research item for `017`, but should
  wait until source artifact and benchmark contracts are stable.

## Feature Updates Needed

### Immediate Spec Updates

- `016`: add Matrix domain-spec gate and explicit proposer/evaluator boundary.
- `020`: add Hermes v0.11 adoption map: transport abstraction, hooks, route
  telemetry, spawn-depth, sibling coordination, compression anti-thrashing.
- `012`: add MemMachine/source-ground-truth finding and official MemPalace source
  warning.
- `019/021/022/023`: keep 2026 document conversion findings central and ensure
  MarkItDown is only a benchmark candidate.
- `017`: tighten NornicDB scope as global KG projection, not memory KG rail.

### Code Work That Should Follow

1. `021`: parser registry + citation/source-span rows.
2. `022`: benchmark adapters for Matrix vector-only and hierarchy-aware RAG.
3. `023`: candidate schema and deterministic parser/RAG smoke.
4. `012`: MemPalace hydration worker or explicit pending-embedding evaluator.
5. `020`: route-decision event schema and runner parity scenarios.
6. `014`: persistent live eval/audit trace smoke.

## Open Risks

- Memory benchmark claims are not directly comparable. Hindsight, MemPalace,
  MemMachine and community posts report different metrics and splits.
- NornicDB published performance claims must be locally validated before it
  becomes default global KG backend.
- Meta-Harness can overfit if search/holdout separation is weak.
- Adding many parser/framework dependencies can overload the 8GB RAM machine.
- OpenRouter free-route limits make live loops scarce; deterministic/local
  loops must carry most iteration.

## Sources

- Meta-Harness official repo: `https://github.com/stanford-iris-lab/meta-harness`
- Meta-Harness paper: `https://arxiv.org/abs/2603.28052`
- Microsoft MarkItDown: `https://github.com/microsoft/markitdown`
- PDF-to-RAG-Ready: `https://arxiv.org/abs/2604.04948`
- French PDF-to-Markdown VLM benchmark: `https://arxiv.org/abs/2602.11960`
- MemMachine: `https://arxiv.org/abs/2604.04853`
- Hindsight Agent Memory Benchmark manifesto:
  `https://hindsight.vectorize.io/blog/2026/03/23/agent-memory-benchmark`
- Hindsight comparison guide:
  `https://hindsight.vectorize.io/guides/2026/04/21/comparison-agent-memory-benchmark-hindsight-vs-alternatives`
- Local refs:
  - `_ref/hermes-agent/RELEASE_v0.11.0.md`
  - `_ref/meta-harness/README.md`
  - `_ref/meta-harness/ONBOARDING.md`
  - `_ref/mempalace/README.md`
  - `_ref/hindsight/README.md`
  - `_ref/Researchwatcher/README.md`
  - `_ref/Researchwatcher/kg-module/ARCHITECTURE.md`
  - `_ref/NornicDB/README.md`
