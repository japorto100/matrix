---
title: Feature Groups 001-023 Checkpoint
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
scope: features 001-023
---

# Feature Groups 001-023 Checkpoint

This checkpoint groups the current `001-023` feature set by runtime domain.
Future features can extend the grouping without rewriting this snapshot.

Use this together with `REVIEW_001_023_2026-04-27.md`:

- `REVIEW_*` answers: what is done, live-only, implementation-open or
  research-needed.
- this file answers: which features should be handled together.

## Why This Exists

The numeric order is useful for migration history, but it is not the right work
order anymore. Many later features are cross-cutting Python-agent work, while
early features still hold live-verify debt. Work should now be planned by
domain and dependency.

## Domain Groups

### A. Platform / Dev / Schema

Features:

- `001-platform-baseline`
- `002-devstack-bootstrap-env-persistence`
- `018-database-schema-governance`

Purpose:

- keep the repo bootstrap, environment, storage and schema rules stable.
- make Alembic authoritative while exposing a readable current schema inventory.
- protect Matrix-local containers and volumes from other projects.

Current status:

- `001` is effectively closed as baseline/docs.
- `002` is static-done/live-open; recent Matrix Postgres namespace/pgvector work
  should be reflected in live evidence.
- `018` is implementation-open but smaller than the RAG/agent features.

Next best work:

- run Matrix-local Postgres/Alembic live proof.
- add current-schema inventory/drift gate.
- keep devstack namespace distinct from Tradeview/other project volumes.

Research need:

- low. Compare schema.py-style references such as Agno only as implementation
  references; do not replace Alembic unless a concrete drift/visibility problem
  remains after inventory generation.

### B. Matrix Runtime

Features:

- `004-matrix-homeserver-connectivity`
- `005-matrix-chat-core`
- `006-appservice-nats-e2ee-bridges`

Purpose:

- run the actual Matrix stack.
- verify Matrix UI, Element X/mobile, appservice, NATS and gateway E2EE flow.

Current status:

- local backend/live Matrix runtime is now partially verified.
- `004` remains active monitoring because upstream Tuwunel/Matrix/mobile items
  can change; local Tuwunel, `.well-known`, credential recovery and setup-users
  now pass against the persisted dev volume.
- `006` has an unencrypted live Matrix Client API -> Tuwunel -> Go appservice
  -> NATS -> Python bridge/agent -> NATS reply -> Go appservice -> Matrix room
  proof. Encrypted-room, key backup, cross-signing and browser/mobile proof
  remain closure blockers.

Next best work:

- verify Matrix UI login/room/timeline/send path when browser render scope is
  active.
- execute encrypted-room Matrix bridge flow, key backup and key deletion gates.
- verify Element X `.well-known` only when mobile/tunnel scope is active.
- keep a Matrix-channel regression gate for Python agent fallback
  `(keine Antwort)`; the current full-path proof returns real model text.

Research need:

- periodic web/upstream review for Tuwunel, MatrixRTC, Element X, OIDC/MAS,
  encrypted state event support and native per-agent E2EE direction.

### C. Frontend Surfaces

Features:

- `003-frontend-merger-shell`
- `007-agent-chat-voice-runtime`
- `008-agentic-ui-generative-ui-mcp`
- `010-control-ui-runtime-surfaces`

Purpose:

- own all user-visible app surfaces: shell, Matrix Chat, Agent Chat, A2UI,
  files, memory and Control.

Current status:

- `003` is mostly live-verify-only.
- `007` is mixed: Agent Chat is static-tested, but roundtrip/provenance/title
  behavior and Voice are open.
- `008` is static-tested but live A2UI/MCP/persistence proof is open.
- `010` is mixed: Control UI has shell/API/query wiring, but many tabs can
  still fall back to mock data.

Next best work:

- browser route smoke for `/matrix`, `/control`, `/files`, `/memory` and global
  Agent Chat overlay.
- Agent Chat live roundtrip through BFF/Go/Python.
- A2UI packet live render and surface persistence smoke.
- Control tab-by-tab audit: real data, actionable empty state, mock fallback or
  broken state.

Research need:

- low for shell.
- medium for current A2UI/CopilotKit/MCP/WebMCP if external tool exposure is
  promoted.
- medium for LiveKit/STT/TTS if Voice becomes active scope.

### D. Python Agent Harness

Features:

- `007-agent-chat-voice-runtime`
- `009-multi-agent-a2a-orchestration`
- `011-llm-gateway-models-routing-billing`
- `012-memory-context-world-personal-kb`
- `013-sandbox-security-hitl`
- `014-observability-harness-evals`
- `015-scheduler-skills-planning-automation`
- `016-meta-harness-agent-optimization`
- `020-agent-harness-subagents-routing`
- `023-auto-optimization-inner-loops`

Purpose:

- define how the real Matrix agent thinks, routes, calls tools, uses memory,
  handles security, traces behavior and improves over time.

Current status:

- this is not done. Many parts are static-tested, but the complete agent
  harness is still open.
- `016` is an optimization/eval layer over the agent harness, not a replacement
  for real implementation.
- `020` is future subagent/routing contract work. It must not turn Matrix into a
  coding-agent product in the current scope.

Next best work:

- research/deep-read pass for `_ref/hermes-agent`, `_ref/meta-harness`,
  `_ref/EvoSkill`, `_ref/hindsight`, `_ref/mempalace` and relevant local agent
  code.
- add route-decision telemetry before changing runner behavior.
- harden graphless vs LangGraph parity around no-tool, tool, memory and
  retrieval cases.
- keep Control UI as display/admin, not an implicit agent tool surface.

Research need:

- high for HermesAgent harness lessons, Meta-Harness proposer/evaluator split,
  EvoSkill/skill evolution, Hindsight/MemPalace usage and current provider
  routing policies.

### E. Memory / RAG / KG / Ingestion

Features:

- `012-memory-context-world-personal-kb`
- `017-knowledge-graph-bitemporal-claims`
- `019-hybrid-rag-retrieval`
- `021-ingestion-paperwatcher-researchwatcher`
- `022-rag-kg-benchmark-lab`
- `023-auto-optimization-inner-loops`

Purpose:

- provide the source-grounded context layer for trading, geo/macro, strategy
  review and long-running user/project memory.

Current status:

- active implementation frontier.
- `021` has source artifacts and local ingestion progress, but parser registry,
  URL/arXiv/API connectors and citation rows remain open.
- `019/022/023` define the RAG and benchmark/eval path, but production adapters
  and search spaces are not complete.
- `022/023` now have explicit search/holdout split metadata and protected
  inner-loop input gates. The deterministic fused Matrix candidate is still a
  search-set promotion candidate, not a production default until holdout/live
  provider and source-derived canaries pass.
- `017` is global/domain KG, not the agent personal-memory rail. It should use
  nonicdb/NornicDB projection work where useful, while Hindsight/MemPalace keep
  their own memory structures in Postgres.

Next best work:

- make source artifact/citation/chunk contracts strong enough before graph/RAG
  promotion.
- benchmark parser/chunker candidates: PyMuPDF4LLM, Microsoft MarkItDown,
  Docling and MinerU.
- implement vector-only, fused vector+KG and KG/path benchmark adapters.
- expand holdout and strong dense/parser-derived canaries before promoting KG
  routing defaults.
- decide where LightRAG/HippoRAG/LinearRAG are references, adapters or deferred
  comparison systems.
- wire inner-loop candidates from Feature 023 into Feature 022 benchmark
  evidence and Feature 016 Meta-Harness artifacts.

Research need:

- high. Prefer 2026+ papers and current official repos for SOTA decisions.
- older papers such as LightRAG 2024 and AutoRAG 2024 are method references,
  not current-date SOTA evidence by themselves.

### F. Security / Observability / Eval Gates

Features:

- `013-sandbox-security-hitl`
- `014-observability-harness-evals`
- `016-meta-harness-agent-optimization`
- `022-rag-kg-benchmark-lab`
- `023-auto-optimization-inner-loops`

Purpose:

- keep agent improvement measurable and safe.
- separate traces, audit, evals and candidate promotion.

Current status:

- static coverage exists, but live trace/audit/eval and sandbox/HITL gates are
  not fully closed.
- Meta-Harness is useful only when it has real traces, real scenarios and
  non-overfit holdouts.

Next best work:

- one live OpenObserve trace and one queryable audit event.
- one persisted eval run.
- one sandbox/HITL flow with allow/deny/audit evidence.
- one Meta-Harness loop that reads trace artifacts, proposes one candidate and
  leaves it for evaluator/promotion instead of self-certifying.

Research need:

- medium/high for current Meta-Harness official repo usage, current OpenSandbox
  docs and 2026 security/prompt-injection/leak taxonomy only where those
  mechanisms are promoted.

### G. Skills / Automation

Features:

- `015-scheduler-skills-planning-automation`
- `020-agent-harness-subagents-routing`
- `023-auto-optimization-inner-loops`

Purpose:

- let the agent use skills and scheduled tasks without turning the system into
  an uncontrolled coding-agent framework.

Current status:

- scheduler and skills are partially/static implemented.
- real delivery, real DB skill lifecycle, skill feedback/promotion and online
  skill sourcing remain open.
- subagents are future contracts only.

Next best work:

- live scheduler create/list/run-now/cron path.
- skill DB seed/load roundtrip.
- online skill source research for trading/general Matrix use, with security
  provenance checklist before import.
- define skill optimization candidates for Feature 023, but promote only
  through Feature 016/022 evidence.

Research need:

- high for EvoSkill/Hermes-style skill lifecycle and online skill sources.
- DSPy/MIPRO belongs here only as an optimizer candidate, not as a blanket
  rewrite.

## Recommended Work Order

### Research Pass 1: Agent Core

Features:

- `007`, `009`, `011`, `012`, `013`, `014`, `015`, `016`, `020`, `023`

Inputs:

- local code under `python-backend/agent`, `memory_fusion`, `memory_engine`,
  `context`, `retrieval`, `meta_harness`.
- `_ref/hermes-agent`, `_ref/meta-harness`, `_ref/EvoSkill`,
  `_ref/hindsight`, `_ref/mempalace`.
- web/repo checks where APIs/policies have likely changed.

Output:

- concrete Matrix-specific diffs and gates, not generic agent theory.

### Research Pass 2: Memory/RAG/KG/Ingestion

Features:

- `012`, `017`, `019`, `021`, `022`, `023`

Inputs:

- current code under `ingestion`, `retrieval`, `kg_pipeline`,
  `memory_fusion`, `memory_engine`.
- `_ref/Researchwatcher`, `_ref/NornicDB`, `_ref/auto-rag-optimizer`.
- 2026+ papers/current repos for document conversion, agentic RAG, GraphRAG,
  bitemporal KG and benchmark methodology.

Output:

- implementation plan for source artifact -> chunk/citation -> retrieval ->
  KG proposal -> benchmark -> promotion.

### Live Verify Pass

Features:

- `002`, `003`, `004`, `005`, `006`, `007`, `008`, `010`, `011`, `013`, `014`

Surfaces:

- Matrix general and Element X/mobile.
- Agent Chat UI and A2UI/MCP.
- Control UI tabs.
- LLM gateway.
- Sandbox/HITL.
- Observability/audit/eval.

Output:

- `live-verify.md` evidence, or explicit deferred/out-of-scope decisions with
  owner and reason.

### Implementation Pack 1: Source Grounding

Features:

- `021`, `019`, `022`, `023`

Reason:

- ingestion, retrieval and benchmark contracts must exist before deeper KG or
  memory optimization can be trusted.

### Implementation Pack 2: Memory + Agent Context

Features:

- `012`, `007`, `016`

Reason:

- Agent Chat quality depends on context/memory injection, and Meta-Harness needs
  real memory/tool traces to optimize.

### Implementation Pack 3: KG + Schema + Routing/Skills

Features:

- `017`, `018`, `020`, `015`

Reason:

- KG and schema should build on the source-grounding layer. Routing/subagents
  and skills should wait until the core agent harness has better telemetry and
  gates.

## Non-Goals For This Checkpoint

- Do not introduce coding-agent product scope.
- Do not replace Alembic with ad hoc schema definitions.
- Do not treat Control UI as an agent tool surface by default.
- Do not promote old papers as 2026 SOTA evidence without current repo and
  local benchmark support.
