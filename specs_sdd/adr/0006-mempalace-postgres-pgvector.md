---
title: ADR-0006 MemPalace Postgres Pgvector Runtime
status: accepted
owner: filip
created: 2026-04-26
updated: 2026-04-26
affects:
  - 012-memory-context-world-personal-kb
  - 011-llm-gateway-models-routing-billing
sources:
  - _ref/mempalace/README.md
  - _ref/mempalace/mempalace/backends/chroma.py
  - _ref/mempalace/mempalace/searcher.py
  - _ref/mempalace/tests/test_mcp_server.py
  - https://openrouter.ai/docs/api/reference/embeddings
  - https://openrouter.ai/collections/embedding-models
---

# ADR-0006 MemPalace Postgres Pgvector Runtime

## Decision

Matrix adopts MemPalace's product concepts but not its runtime storage stack.

Adopt:

- verbatim drawers as exact evidence records.
- wings, rooms, halls, closets, drawers and loci-path metadata.
- wing/room/hall filtering before or during retrieval.
- source/session references for audit and old-session reconstruction.

Do not adopt for Matrix production runtime:

- ChromaDB as the MemPalace store.
- SQLite/file-palace storage as the production source of truth.
- local default embedding model cold-starts during agent or Meta-Harness runs.

Matrix MemPalace storage is `agent.mempalace_drawers` in Postgres with pgvector
embeddings. Hindsight and MemPalace both use Matrix's `MEMORY_EMBEDDING_*`
configuration and an OpenRouter-compatible remote embedding adapter, with a
deterministic test embedder for CI/unit tests. Each MemPalace row stores
`embedding_model` and `embedding_dim` so model changes do not mix incompatible
vector dimensions during retrieval.

Agent writes are verbatim-first. Explicit `memory_add` and automatic
post-answer `memory_retain_node` synchronously persist exact evidence to the
MemPalace/Postgres route, then queue Hindsight summary retain asynchronously.
This preserves raw chat/tool evidence before compaction without blocking the
user turn on slower summary extraction.

## Rationale

Matrix already depends on Postgres for Hindsight, audit, control and harness
state. A second local Chroma/SQLite memory truth would make deletion,
credentials, backup, schema review and Meta-Harness evidence harder to reason
about.

The user machine is not a good target for repeated local embedding cold-starts.
Remote embeddings make Meta-Harness latency measurements more representative of
the intended runtime and avoid loading local model weights for every memory
probe.

## OpenRouter Embedding Policy

As of 2026-04-26, OpenRouter exposes an embeddings endpoint and an embedding
model catalogue. Existing Hindsight data in the dev database uses 384-dimension
embeddings, but that legacy dev data does not constrain the final architecture.
The temporary non-destructive default is `sentence-transformers/all-minilm-l6-v2`
through OpenRouter until Feature 012's embedding-dimension research/eval chooses
the target model. Upstream review found that MemPalace's hierarchy
(wings/rooms/closets/drawers) is metadata scoping, not multiple vector
dimensions; its ChromaDB default is `all-MiniLM-L6-v2` in the 384-dim class.
Hindsight's local default is also 384-dim (`BAAI/bge-small-en-v1.5`), while its
OpenAI-compatible default is `text-embedding-3-small` at 1536 dimensions. The
only observed zero-priced OpenRouter embedding model in the live model list was
`nvidia/llama-nemotron-embed-vl-1b-v2:free`, but it returns 2048 dimensions in
smoke tests and must not be mixed with 384-dim Hindsight data without an explicit
reset/re-embedding/migration plan. Stable candidates for later quality/cost
gates include `openai/text-embedding-3-small`, `baai/bge-m3`, Perplexity and
Qwen embedding models.

Remote embedding sends memory text to an external provider. Production enablement
therefore requires the same credential, redaction, quota, audit and user-consent
gates as other external model calls.

## Consequences

- Feature 012 owns MemPalace as a Postgres evidence archive, not a Chroma
  sidecar.
- Agent-facing memory retain must treat MemPalace/verbatim as the synchronous
  safety path; Hindsight summary/learning enrichment is allowed to lag behind.
- Feature 011 must include embedding-model credentials, spend and audit in the
  provider policy.
- Any future upstream MemPalace update is reviewed for concepts first; storage
  changes are mapped deliberately into Postgres/Alembic rather than copied.
