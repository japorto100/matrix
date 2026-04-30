---
title: Hybrid RAG Retrieval Research
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-30
feature_id: 019
---

# Research

## Current Judgement

There is no single best open-source RAG system. For Matrix, the relevant
class is small, methodical retrieval systems rather than enterprise RAG apps.

Adopt as direct references:

- Researchwatcher HiRAG: intent routing, hybrid retriever, Context Bubble,
  Self-RAG and citation verification.
- LightRAG: practical GraphRAG baseline and graph extraction/query ergonomics.
- HippoRAG2: memory-like associative multi-hop retrieval baseline.
- LinearRAG: relation-free graph construction candidate.

Use as eval references:

- GraphRAG-Bench: when graph structures help over traditional RAG.
- arXiv 2604.09666 / RAGSearch: dense vs GraphRAG under identical agentic
  search protocols.
- RAGAS/RAGChecker/Phoenix/Langfuse style diagnostics for context and
  faithfulness.
- AutoRAG/AutoRAG-HP: inner-loop optimization for retrieval/chunking configs,
  now owned by Feature 023.

## Architecture Implication

Dense/hybrid vector retrieval remains the default baseline. Graph retrieval is
introduced for relational, temporal, multi-hop and world-model questions where
explicit structure earns its offline cost.

## 2026-04-27 Update

The strongest new evidence is not "pick one GraphRAG framework". It is that
preprocessing, hierarchy-aware chunking and metadata enrichment matter before
graph complexity.

`arXiv:2604.04948` compared Docling, MinerU, Marker and DeepSeek OCR across 19
PDF-to-Markdown/RAG configurations. The result is directly relevant to Matrix:
Docling plus hierarchical splitting and image descriptions reached the best
reported automated QA accuracy, while a naive GraphRAG implementation
underperformed basic RAG. The lesson is conservative:

- make the document pipeline layout/hierarchy/citation aware first.
- benchmark graph retrieval only on query classes where structure should help.
- avoid making graph retrieval the default for all document QA.

LightRAG remains the first practical GraphRAG baseline because it is runnable
and ergonomically close to a production service. HippoRAG2 remains important
for associative/multi-hop retrieval, but should be tested after Matrix's own
vector/KG/fused baseline and LightRAG adapter exist.

Feature 019 therefore depends on:

- Feature 021 for parser/chunk/citation quality.
- Feature 022 for matched retrieval benchmarks.
- Feature 023 for bounded inner-loop config search.

## 2026-04-29 Agentic RAG / GraphRAG Source Check

[RAGSearch](https://arxiv.org/abs/2604.09666) directly tests the question raised
in the fresh Z-MDs: whether agentic multi-round search reduces the need for
explicit graph retrieval. Current reading: do not remove graph retrieval from
the roadmap, but do not promote GraphRAG as default either.

Implications:

- Dense/hybrid RAG plus agentic re-query remains the default baseline.
- Graph/KG retrieval is a measured candidate for multi-hop, temporal and
relational questions where explicit structure should pay for its offline cost.
- Feature 022 benchmark canaries should include both answer-quality and
efficiency/stability metrics, matching RAGSearch's focus beyond final accuracy.

## 2026-04-29 Z_ Follow-Up

`Z_Browser_RAG_WebGPU_CPU_Models.md` adds browser-local retrieval as a candidate
lane, not as a backend replacement. Feature 026 owns the runtime; Feature 019
owns answer-time assembly and comparison to backend retrieval.

`Z_Semantik_layer and so on.md` means retrieval should accept semantic
term/metric filters from Feature 025 rather than relying only on raw user text.

2026-04-29 implementation note: semantic, visual and report evidence now enter
the deterministic retrieval benchmark as reference-metadata contracts:

- `semantic-term-tool-success-001` covers Feature 025 term/metric metadata.
- `visual-layout-source-coordinates-001` covers Feature 028 page/bbox layout
  evidence.
- `report-grounding-manifest-001` covers Feature 027 report manifest citations.

This keeps GraphRAG/RAG experiments provider-agnostic and source-grounded: the
benchmark checks metadata and citations, not any single vendor model behavior.

## 2026-04-30 SOTA/Contract Check

Fresh source check keeps the same architecture:

- LightRAG's public paper/repo still supports evaluating graph+vector retrieval
  as a practical GraphRAG candidate, not as a universal default.
- RAGChecker-style evaluation supports claim/citation-level diagnostics instead
  of answer-only scoring.
- MetricFlow/Cube-style semantic layers support deterministic, versioned
  semantic contracts before any generated SQL or unstructured retrieval answer.

Matrix implementation note: `knowledge-contract` connects those findings into
one static gate. A selected context item is not enough because it ranks well;
it must keep source artifact, chunk/hash, citation, semantic catalog and KG
claim metadata. Browser-local retrieval from `Z_Browser_RAG_WebGPU_CPU_Models.md`
stays a candidate lane, while backend RAG/KG remains the auditable source of
truth for shared/global context.

2026-04-30 lexical lane note: BM25/regex candidates are useful for recall and
source discovery, but they are not answer support unless they carry the same
provenance contract as vector/KG context. The provider-free knowledge contract
now encodes this with `knowledge-lexical-candidate-without-provenance-blocked`.

2026-04-30 runtime follow-up: `retrieve(...)` now annotates selected hits and
references with `provenance_status`. Agent callers that are about to use
retrieved context for answer support can pass `require_context_provenance=True`
to degrade fail-closed when selected context has no source URI, artifact,
citation, memory raw evidence ref, document/chunk or KG claim ref. This keeps
regex/BM25/semantic discovery useful without allowing unattributed context to
silently become answer evidence.

2026-04-30 downstream artifact follow-up: provider-free `knowledge-contract`
now connects retrieval provenance to Agent Chat downstream visibility. RAG/KG
runtime events must carry source artifact, chunk/hash, citation and claim
metadata, and the stream gate must expose source/path artifact filenames. This
keeps retrieval quality and UI inspectability coupled before browser/live
verification.

## 2026-04-30 BM25 / Regex Discovery Transfer

Inputs: `Z_Additional_For_Tool_Stuff.md`, Feature 024 tool search and Feature
025 semantic filtering.

Hybrid RAG should keep lexical retrieval as a first-class lane. Regex and
BM25-style scoring are useful for tool/skill/resource discovery and for
source-grounded RAG prefiltering, as long as answer support still requires
provenance. The practical contract is:

- lexical candidates may improve recall and debuggability.
- semantic/KG filters may narrow candidates only when they preserve source refs.
- selected context must expose retrieval lane, score fields and degradation
  reason when a lane is unavailable.

This avoids a false split between "normal tools" and MCP tools: both can use
the same progressive-disclosure search primitive before exposing full schemas
or source content to an agent.

2026-04-30 runtime implementation: `retrieve(...)` now treats BM25, regex and
generic lexical candidates as first-class runtime lanes. They can participate
in text/hybrid/temporal ranking with lower fusion weight than vector/KG, but
selected context still carries lane metadata and provenance status. Runtime
events expose counts/ids/lane names only, so lexical debugging does not leak
source bodies into Ops or Meta-Harness traces.

## 2026-04-30 Runtime Audit Follow-Up

Retrieval runtime events now have a replay bridge into Ops. When a caller
supplies runtime scope (`thread_id`, `session_id`) or explicitly opts in with
`audit_runtime_events=True`, `retrieve(...)` writes a `rag_retrieval` audit row
containing only ids/counts/status, degradation reasons and a short query digest.
This gives Feature 029 enough data to render RAG/KG lanes without treating the
audit store as a second retrieval corpus.

## 2026-04-30 Runtime Discovery Follow-Up

Feature 024's progressive-disclosure primitive now reaches the agent prompt
path for builtin tools. `_prepare_system_prompt()` searches the active
`ctx.tools` with the current user query and adds schema-free Tool Discovery
Hints. This is adjacent to RAG because it gives the same lexical/BM25-style
discovery pattern three runtime uses:

- RAG/context candidates via `retrieve(...)` lexical lanes.
- Skill candidates via `agent.skills.finder` traces.
- Tool candidates via `agent.tools.catalog.search_tool_catalog()` in prompt
  preparation.

2026-04-30 source-discovery implementation: `retrieve(...)` now accepts
explicit `source_candidates` and derives candidates from vector/KG/lexical hits.
The candidate shape is metadata-only: id, source, source URI, score, retrieval
lane, provenance status and a small allowlist of source/chunk/citation metadata.
It intentionally excludes hit content and full source bodies. Runtime events
emit candidate ids/counts only, so Agent Chat/Ops can show source options
without turning event logs into another document store.

## 2026-04-30 Semantic Candidate Propagation

Feature 025's lexical semantic candidates now propagate into retrieval as
clarification metadata. If `semantic_phrase` is unknown but has near-miss
candidates, retrieval still filters out all context and marks the run degraded,
but `rag.retrieve.completed` exposes `semantic_candidate_count` and
`semantic_candidate_ids`. This lets Agent Chat/Ops explain "I found a likely
semantic metric, please confirm" without treating a BM25-style match as an
authoritative semantic contract.
