---
title: Memory Research And Adoption Notes
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-30
feature_id: 012
migrated_from:
  - main_docs/root/MEMORY_ARCHITECTURE.md
  - main_docs/root/CONTEXT_ENGINEERING.md
  - main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md
  - docs/papers/knowledgegraph/
  - specs/execution/exec-memory.md
  - specs/execution/exec-world-model.md
  - specs/execution/exec-personal-kb.md
---

# Research

## Main Docs Carry-Forward

`main_docs/root/MEMORY_ARCHITECTURE.md` is older but still relevant. Adopted
concepts:

- M1-M5 layering: shared cache, KG, episodic store, vector/RAG and working
  memory.
- epistemic separation: user statements, agent inferences, world claims and KB
  artifacts must not collapse into one bucket.
- Fast Lane vs Slow Lane KG growth.
- source persistence and vector ingestion boundaries.
- overlay/claim/evidence/stanced merge concepts.

`main_docs/root/CONTEXT_ENGINEERING.md` remains reference material for:

- context consumer matrix.
- query type to memory layer routing.
- retrieval order and fallback behavior.
- relevance scoring, caps and override/decay.
- token budget allocation and compaction priority.
- multi-source merge, conflict resolution and graceful degradation.
- context trace and quality metrics.

`main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` contributes runtime mode and
non-goal framing: search, compare/audit, verify and global/corpus modes are
different retrieval contracts.

## Hindsight vs MemPalace

Hindsight is the agent-memory engine: extraction, reflection, consolidation,
multi-channel search and derived observations. MemPalace is primarily verbatim
conversation retrieval. The useful architecture is not "replace Hindsight", but
evaluate which query classes benefit from verbatim-first retrieval.

Boundary update on 2026-04-26: Hindsight may maintain KG-like structures for
agent learning memory inside Postgres, and MemPalace may maintain loci/episodic
links for exact recall. These are agent-memory internals. They must not be
confused with the global/domain KG in Feature 017.

ADR-0006 update on 2026-04-26: Matrix adopts MemPalace's loci model but not its
Chroma/SQLite production runtime. Upstream `_ref/mempalace` currently stores
drawers in Chroma, queries via `query_texts`, and uses Chroma's default local
embedding behavior unless benchmark-specific embedding functions are supplied.
Matrix maps the concepts to Postgres/pgvector instead: `agent.mempalace_drawers`
stores verbatim content, wing/room/hall/closet/drawer metadata, source refs,
embedding model and embedding dimension.

Adopted from MemPalace concepts:

- query sanitizer.
- source/provenance refs.
- Method-of-Loci metadata for recall filters.
- verbatim evidence surfacing.
- shared eval route through `memory_fusion`.

Not adopted as current target:

- filesystem MemPalace runtime as production store.
- ChromaDB as primary store.
- SQLite as the Matrix production MemPalace store.
- local embedding model cold-start as the default agent/Meta-Harness path.

OpenRouter embedding note: the live model list on 2026-04-26 includes a
zero-priced `nvidia/llama-nemotron-embed-vl-1b-v2:free` option, but live smoke
tests returned 2048-dimensional vectors. Existing Hindsight dev data is
384-dimensional; this only explains the temporary non-destructive default and
must not decide the final Memory-Fusion architecture. Matrix should choose the
Hindsight/MemPalace embedding dimension by upstream documentation review,
retrieval evals and reset/re-embedding cost. Stable candidates for later quality
gates include low-cost text embedding models such as
`sentence-transformers/all-minilm-l6-v2`, `openai/text-embedding-3-small`,
`baai/bge-m3`, Perplexity and Qwen embedding models.

Embedding-dimension research update (2026-04-26):

- MemPalace's house/wing/room/closet/drawer language is a hierarchy for scoping,
  metadata filtering and human/agent navigation. It is not three separate vector
  dimensions. The vector store still compares one embedding vector per drawer.
- MemPalace upstream documents ChromaDB semantic search with the default
  `all-MiniLM-L6-v2` embedding model; its benchmark code labels that default as
  384-dimensional. The same benchmark code exposes stronger alternatives such as
  `bge-base` at 768 dimensions and `bge-large` / `mxbai` at 1024 dimensions for
  ablation, not as a mandatory production default.
- Hindsight upstream defaults to `BAAI/bge-small-en-v1.5` locally, also 384
  dimensions. Its OpenAI-compatible default is `text-embedding-3-small` at 1536
  dimensions. Hindsight detects dimensions at startup, but once memories exist
  the dimension cannot be changed without reset/re-embedding.
- Matrix recommendation before eval: keep Hindsight and MemPalace on one shared
  embedding dimension per index. Use 384 dimensions for the first stable
  Memory-Fusion baseline because both MemPalace and Hindsight official defaults
  are 384-dim class models. Treat 768/1024/1536 as an explicit upgrade
  experiment requiring reset/re-embedding and retrieval-quality comparison.
- Hindsight's local cross-encoder reranker loads model weights. Matrix defaults
  to `HINDSIGHT_API_RERANKER_PROVIDER=rrf` for dev/Meta-Harness loops to avoid
  local cold-starts on this machine. Local/TEI/Cohere/LiteLLM rerankers stay
  explicit eval candidates rather than default runtime behavior.

Open research task:

- Refresh MemPalace upstream docs/repo before schema lock. If upstream added
  Postgres support, rooms/session semantics, updated loci storage or new eval
  patterns, pull that into this feature deliberately; otherwise record Matrix's
  Postgres divergence.
- Re-check official MemPalace source material before closeout. Public mirrors
  and summaries are not enough for schema lock because upstream may still be
  Chroma/SQLite oriented while Matrix intentionally targets Postgres/pgvector.

## Memory For Autonomous Agents Paper

Key adopted implications:

- summarization drift requires verbatim/audit backstop before compaction.
- memory eval must include recall quality, task outcome, cost/latency and
  governance.
- source attribution matters: user statement > agent inference.
- forgetting/privacy is separate from cold archival.
- memory operation logs and diffs are needed for regression testing.

## MemMachine 2026 / Ground-Truth Preservation

`arXiv:2604.04853` strengthens the decision to keep MemPalace-style verbatim
evidence beside Hindsight summaries. The relevant lesson is not another memory
store, but a policy:

- preserve episodic ground truth before summarization, compaction or deletion
  of visible session context.
- make retrieval/context formatting the optimization target; ingestion alone
  does not solve memory correctness.
- distinguish durable raw events, derived summaries and answer-time injected
  context.
- judge memory by exact evidence availability, source refs, answer correctness,
  cost and latency.

Matrix adoption: pre-save, compaction and emergency compression must archive
complete visible context into the verbatim lane first. Hindsight can then learn
summaries/reflections asynchronously. If embeddings are slow or remote quota is
exhausted, rows stay durable with `embedding_status=pending` and are hydrated
later rather than blocking evidence preservation.

2026-04-30 implementation note: this is now represented in the
Meta-Harness `knowledge-contract` lane. The static scenario requires
Memory-Fusion recall/retain events to carry source status, raw evidence refs,
operation log ids and diff refs before cross-feature context assembly can treat
derived memory as usable. This references `Z_Semantik_layer and so on.md`
indirectly through the correction handoff: personal feedback may propose
semantic changes, but it does not mutate global definitions or KG truth.

## World Model Research

World model is not personal memory. It needs evidence, claims, status and
adjudication.

Candidate/adopted concepts:

- Fast Lane for temporal/event data with short TTL.
- Slow Lane for structural knowledge with batch validation.
- claim reification before KG promotion.
- evidence-first answer-time composition.
- NornicDB as candidate global KG backend due Bolt/Cypher, temporal decay and
  vector support, subject to maturity evaluation.
- local `docs/papers/knowledgegraph/*` corpus as research input for GraphRAG,
  adaptive retrieval, knowledge conflict and cognitive memory-layer design.

## Personal KB Product References

Recall is useful for capture/product flows. TriliumNext is useful for
outliner/notebook/clipper UX patterns. Neither becomes the backend source of
truth by default.

Adopt patterns:

- inbox/library/save flow.
- document/transcript/note surfaces.
- labels/highlights/pins.
- personal, user-owned feel.

Avoid:

- a second backend truth beside matrix stores.
- manual graph maintenance as the primary workflow.

## Future Research

- Mem0/Letta for stateful memory patterns.
- Ebbinghaus decay instead of fixed cold-migration rules.
- Bayesian/uncertainty-aware retrieval.
- MemoryArena-style active decision-making evals.
- multimodal memory once voice/chart artifacts enter memory.
# 2026-04-29 Z_ Follow-Up

`Z_Chatgpt_Chronicles vs DeepseekOCRpaper.md` adds a useful split for memory:

- practical visual evidence memory belongs in Feature 028 and can feed Feature
  012 only with consent, source refs and confidence;
- optical context compression is research-only until Meta-Harness proves recall
  and safety;
- personal corrections to metric/term meaning route to Feature 025 proposals
  instead of silently changing global truth.
