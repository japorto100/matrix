---
title: Feature Workplan 001-022
status: active
owner: filip
created: 2026-04-27
updated: 2026-04-27
---

# Feature Workplan 001-022

This is the operating queue across all SDD features. Feature files remain the
source of detailed requirements; this file decides what to build, what to
verify and where Meta-Harness should drive the next iterations.

## Execution Rules

- Keep Meta-Harness as the outer loop for agent, memory, tool, RAG/KG and
  routing changes.
- Use `llm-mock` for plumbing/parity and OpenRouter/live models only for
  quality or provider-specific probes.
- Use Postgres-backed audit traces for serious Meta-Harness runs; JSONL is only
  a local smoke fallback.
- Do not optimize simulations. A candidate is useful only if it improves real
  harness behavior, retrieval quality, memory correctness, safety or
  observability.
- Keep autonomous coding-agent product scope out of Matrix. HermesAgent informs
  harness design; Matrix focuses on trading, geopolitics, strategy, research,
  memory, KG, RAG and workflow assistance.

## Immediate Queue

1. Feature 020: complete HermesAgent code deep-read and define Matrix route/
   delegation event schema.
2. Feature 021: extend the new local-file ingestion path into durable source
   artifact/citation refs, then run it over the GraphRAG paper artifact.
3. Feature 022: build the first RAG/KG canary runner comparing vector-only,
   KG-only and fused Matrix retrieval.
4. Feature 019/017: use benchmark failures to harden retrieval, KG paths,
   provenance and Context Bubble behavior.
5. Feature 012/015/016: expand memory/skill/routing trace gates from the new
   retrieval and Hermes lessons.
6. Feature 013: bring sandbox/file/browser scenarios online once core routing
   and retrieval gates are stable.

## Feature Matrix

| Feature | Current action | Meta-Harness role | Next concrete gate |
|---|---|---|---|
| 001 Platform baseline | Keep stable | None except regression context | No active build unless baseline docs drift |
| 002 Devstack/env | Maintain | Stack prerequisites for scenarios | `--postgres --llm-mock --agent` reproducible smoke |
| 003 Frontend shell | Live verify later | UI smoke only | Route/files/control entry walkthrough |
| 004 Matrix homeserver | Monitor/live | Matrix delivery scenarios later | Tuwunel room send/receive and mobile/federation checks |
| 005 Matrix chat core | Live verify | Chat E2E scenarios | Agent mention, room thread and message lifecycle |
| 006 Appservice/NATS/E2EE | Live verify | Bridge trace scenarios later | Matrix -> appservice -> NATS -> Python handoff |
| 007 Agent chat/runtime | Harden | Core chat/tool/memory scenarios | SSE finish, interruption, approval and context gates |
| 008 Agentic UI/MCP | Live verify later | Tool surface/A2UI trace gates | A2UI/MCP roundtrip without Control UI confusion |
| 009 Multi-agent/A2A | Defer | Later after internal delegation | Do not promote before Feature 020 is proven |
| 010 Control UI | Verify display/admin | Observability consumer only | Prove Control UI is not treated as agent tool surface |
| 011 LLM gateway/routing | Harden from Hermes | Provider safety and routing probes | Transport boundary, max tokens, secret/reasoning leak gates |
| 012 Memory/KW/Personal KB | Continue hardening | Memory lifecycle/correctness gates | Hindsight + MemPalace + Fusion conflict and compaction cases |
| 013 Sandbox/security/HITL | Scenario-gated | Tool risk and approval gates | OpenSandbox live smoke plus pre-tool veto policy |
| 014 Observability/evals | Support layer | Stores traces/scores | Trace export and eval artifact completeness |
| 015 Scheduler/skills | Harden with Hermes skills | Skill selection/trigger gates | Skill selection, online skill import and no-overselection |
| 016 Meta-Harness | Keep improving | Outer loop itself | Search/holdout split, proposer ledger, trace-source provenance |
| 017 Global KG | Build/evaluate | KG boundary and retrieval gates | Evidence -> claim proposal -> promoted claim -> KG recall |
| 018 Schema governance | Maintain | Drift gate | Alembic + generated schema registry stays current |
| 019 Hybrid RAG | Build/evaluate | Retrieval quality gates | Vector/KG/fused canaries with attribution and faithfulness |
| 020 Harness/subagents | Research then implement metadata | Routing/delegation gates | Route-decision audit schema before behavior changes |
| 021 Ingestion/Paperwatcher | Local CLI path implemented | Paper-grounded retrieval scenario | Durable source/citation refs plus GraphRAG paper ingest |
| 022 RAG/KG Benchmark Lab | Start build | Candidate comparison/Pareto | Vector-only vs KG-only vs fused baseline report |

## HermesAgent Transfer Backlog

- Feature 011: provider transport abstraction, provider-specific request fields,
  model metadata, timeout/retry config and resolved-secret persistence gates.
- Feature 012: compression anti-thrashing, memory tool dedupe, Hindsight
  session metadata and async/stale flush guards.
- Feature 013: pre-tool veto and transformed tool-result policy with explicit
  audit.
- Feature 015: skill install/source tracking and concise trigger descriptions.
- Feature 016: subagent/delegation trace artifacts, steering artifacts and
  holdout protection for routing behavior.
- Feature 020: orchestrator role, `max_spawn_depth`, sibling coordination and
  delegation event schema.

## Meta-Harness Scenario Backlog

- Routing no-tool parity: `simple`, `langgraph`, `dispatcher`.
- Retrieval-vs-delegation: prove RAG should answer before subagent delegation.
- Memory boundary: Hindsight/MemPalace personal evidence vs global KG claims.
- RAG/KG canaries: simple factual, document-grounded, multi-hop KG, stale-data
  negative case.
- Provider safety: no leaked reasoning, no stored resolved secrets, unsupported
  provider fields stripped.
- Compression: no infinite loop, no context poisoning, language preserved.
- Tool policy: pre-tool veto, HITL approval, tool-result transformation
  auditable.
