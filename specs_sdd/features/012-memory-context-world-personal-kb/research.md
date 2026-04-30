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

2026-04-30 runtime guard update: automatic post-answer memory syncs are still
fire-and-forget for user latency, but they are now per-thread sequenced.
Runner scheduling assigns a generation and `_safe_sync_turn` serializes writes
per thread. If a newer turn has already scheduled persistence, the older
generation is skipped before calling MemoryManager. This is deliberately a
runtime harness guard, not a MemoryProvider API change: providers continue to
own retain semantics, while the agent loop prevents stale background writes
from racing newer turns.

2026-04-30 context-poisoning update: compressed summaries are no longer
reinserted as bare user text. The summary content is wrapped as
`<context_summary trusted="false">` and preceded with an instruction that it is
historical context only. If the summary itself contains known prompt-injection
phrases, a security warning is added before reinsertion. This does not make
LLM compression fully trustworthy, but it gives the next turn a clear boundary
between current user intent and lossy historical context.

2026-04-30 context-overflow recovery update: provider errors classified as
context overflow now trigger a bounded compression recovery in both runners.
The harness compresses the active messages, restarts the retry from iteration
zero for that compressed context and surfaces
`context_overflow_compress_retry`. The guard is deliberately one-shot; repeated
overflow remains a surfaced failure rather than an infinite retry loop.
Provider failures still exit through the normal ErrorPacket path instead of
looping.

2026-04-30 compaction-provenance update: mechanical tool-output compaction now
preserves provider-neutral provenance metadata before prompt truncation. Large
tool messages keep a redacted `metadata.compaction` envelope with offload ref,
full content size, SHA-256 hash and preview length. This follows the
ground-truth preservation rule above: the LLM sees a compact preview, while
audit/memory/ops code can still verify which full tool artifact was shortened.

2026-04-30 source-discovery handoff: Personal KB/RAG can now expose candidate
sources before loading full content. Feature 019 returns metadata-only source
candidates from explicit KB inputs or retrieved hits. This supports a safer
"choose/open source" UX and agent planning path while preserving the rule that
answer support still needs selected, source-backed context.

2026-04-30 delegation memory enforcement: Feature 020 A2A child requests now
carry parent-only memory policy through `AgentExecutionContext` and runner
state. `memory_retain_node` treats that policy as authoritative and returns a
blocked memory runtime event before any durable Memory engine lookup/write.
Delegated outcomes must therefore flow through the parent-side curation handoff
instead of child-side shared memory writes.

2026-04-30 implementation note: this is now represented in the
Meta-Harness `knowledge-contract` lane. The static scenario requires
Memory-Fusion recall/retain events to carry source status, raw evidence refs,
operation log ids and diff refs before cross-feature context assembly can treat
derived memory as usable. This references `Z_Semantik_layer and so on.md`
indirectly through the correction handoff: personal feedback may propose
semantic changes, but it does not mutate global definitions or KG truth.

2026-04-30 context-injection comparison update: `meta_harness.memory_context_smoke`
now emits three provider-free candidates for the same task:
Hindsight-summary-only, MemPalace-verbatim-only and Fusion. This implements the
MemMachine-style judgement locally: summaries are useful but insufficient
without exact evidence, while verbatim recall is safer but misses derived
context. The Fusion candidate wins the static Pareto comparison only when both
summary and source-backed exact evidence are available, preserving the
Hindsight/MemPalace distinction instead of collapsing them into one memory
bucket.

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

# 2026-04-30 Runtime Evidence Trace Follow-Up

The `Z_Semantik_layer and so on.md` lesson is now applied to memory_fusion
before KG/RAG/Semantic handoff: personal memory is evidence-bearing context,
not global truth. Retain builders derive durable raw refs from explicit
`raw_evidence_ref`, `source_ref`, `provenance_ref`, audit/idempotency refs or
source-file/chunk metadata; recall and audit payloads carry the same
`source_status`, `raw_evidence_ref`, `operation_log_id` and `diff_ref` fields.

This is provider-agnostic and intentionally does not depend on OpenAI,
Anthropic, Hindsight internals or a specific vector backend. The ids are
trace/correlation refs for memory operations and diffs; DB-row-level diff
tables can replace or enrich them later without changing the agent context
contract.

# 2026-04-30 Dev/Meta-Harness Embedding Lane

Live Agent Chat memory traces exposed a practical provider failure: the real
OpenRouter chat path worked, but the OpenRouter embeddings endpoint returned
402 and made the Fusion provider unavailable. The fix is not a silent
production fallback. `MEMORY_EMBEDDING_PROVIDER=deterministic` is now an
explicit, provider-agnostic dev/Meta-Harness lane with 384-dimensional
reproducible vectors for Hindsight and MemPalace.

This references the Meta-Harness lesson from the Z_ pass and paper work:
traces must show real tool/memory behavior, and unavailable dependencies must
fail gates instead of being counted as success. Deterministic embeddings are
acceptable only when the scenario is measuring orchestration, trace integrity,
memory write/read plumbing or UI stream visibility. Retrieval-quality claims
still require OpenRouter/OpenAI-compatible/local model candidates and Pareto
evaluation on held-out corpora.

# 2026-04-30 Delegation Memory Transfer

Inputs: Hermes `delegate_task` memory behavior, `Z_Additional_For_Tool_Stuff.md`
and Feature 020.

Subagents must not write shared personal/world memory directly. Child runs may
emit tool/runtime events and a final summary, but parent-side memory curation is
the only default path into durable memory. Parent curation must include child
session id, task id, source refs, confidence/degradation and explicit
retain/skip decision metadata.

This keeps memory Fusion, KG and semantic layers aligned with the current
evidence-first rule: delegated work can become evidence for a parent decision,
not hidden truth mutation by a worker process.

## 2026-04-30 Memory Runtime Audit Follow-Up

Memory recall/retain runtime events are now replayable through audit metadata.
Successful recall, successful retain and retain timeout rows include the same
redacted Feature 033 envelope that Agent Chat receives from graph state. The
event payload carries counts, route/provider, role, source-layer and
degradation metadata; raw recalled memory text and assistant response bodies
remain in the existing bounded audit input/output fields, not in runtime event
metadata.

## 2026-04-30 Fixture Manifest Follow-Up

The provider-free memory-context smoke now writes replayable fixture manifests.
This follows the Meta-Harness paper direction: evaluator/proposer loops need
stable artifacts, not just pass/fail summaries. Each candidate manifest records
the synthetic user/thread, bank id, route/providers, Palace/evidence refs,
expected terms, evidence digest and replay command. That lets memory regressions
be debugged without treating trace rows as the only fixture definition.

## 2026-04-30 Memory Source-Path Gate Follow-Up

Feature 016 now enforces the Feature 012 evidence rule at the audit level:
recall/retain traces must say which path produced them. Automatic prefetch is
`memory_recall_node`, automatic post-answer retain is
`automatic_memory_retain`, and explicit `memory_add`/`memory_search` remains
`explicit_memory_tool`.

This is provider-agnostic and useful for Hindsight, MemPalace and Fusion
because route/provider metadata alone cannot tell whether the agent correctly
used automatic lifecycle hooks or merely called a tool after being prompted.
The new correction scenario also ties stale-answer detection to source-backed
memory evidence, which is the first static drift gate before backend-specific
MemPalace trigger-policy evals.

## 2026-04-30 Memory Holdout Follow-Up

Feature 016 now owns a protected `memory_holdout` evaluator split for memory
correction, evidence-source and layer-boundary regressions. This is deliberately
separate from proposer-visible search fixtures: Memory-Fusion improvements can
learn from search traces, but promotion has to survive hidden cases where the
correct behavior is recall/source citation without accidental `memory_add` or
`save_memory` writes.
