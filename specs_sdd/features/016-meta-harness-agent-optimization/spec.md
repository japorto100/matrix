---
title: Meta-Harness Agent Optimization
status: implementation_started
owner: filip
created: 2026-04-26
updated: 2026-04-27
feature_id: 016
depends_on:
  - 007-agent-chat-voice-runtime
  - 011-llm-gateway-models-routing-billing
  - 012-memory-context-world-personal-kb
  - 013-sandbox-security-hitl
  - 014-observability-harness-evals
  - 015-scheduler-skills-planning-automation
adrs:
  - 0005
---

# Meta-Harness Agent Optimization

## Current State / Ist

Matrix already has the building blocks for a Meta-Harness-style loop:

- Python Agent service with direct `/api/v1/agent/chat`, LangGraph runtime,
  graphless SimpleLoop runtime and dispatcher-based A/B routing.
- LiteLLM client for provider-agnostic LLM calls.
- audit events, spans, sessions, A/B rows and harness scoring.
- `agent.mcp_traces` with trace, score, config, proposer and evaluator tools.
- `meta_harness.proposer`, `evaluator`, `scorer`, `pareto` and config capture.
- memory paths through MemoryManager and `memory_fusion`, where the canonical
  target is memory orchestration: Hindsight owns durable summaries/preferences/
  facts/corrections/outcome learning, while MemPalace owns verbatim and
  episodic evidence that can constrain, verify or correct summaries.
- explicit tools for memory, sandbox, browser, files, scheduler, A2UI and chart
  state.

The current implementation is not yet a full Meta-Harness system. The first
016 slice adds a Python-only scenario runner, deterministic trace gates,
candidate artifacts, live-service execution via `/api/v1/agent/chat`, MCP
scenario-run exposure, real ToolRegistry use in the legacy evaluator, normalized
search-set tool gates, protected holdout-set execution, explicit runner-variant
coverage for `dispatcher`, `langgraph` and `simple`, proposer access to recent
Meta-Harness candidate artifacts and keep/discard/defer decision logs. Live
outer-loop rounds have already fixed skill audit propagation, graph approval
interruption, service-side Meta-Harness consent, sandbox SDK import drift,
Pareto feasibility filtering and the Python package boundary: the outer-loop
code now lives in top-level `meta_harness/`, while `agent/` remains the
production runtime. The next hardening pass adds official-style CLI primitives
for evaluate/propose/loop/decide/history/pareto, disables external proposer LLM
calls by default, removes raw memory utilization as a generic Pareto/fitness
bonus, adds cost/latency dimensions, and records feasibility reasons for failed
candidates. The first Codex-as-proposer candidate also fixes explicit memory
tool observability: `memory_add` and `memory_search` now emit memory
retain/recall audit events with Fusion route/provider metadata. Remaining gaps:
scenario coverage is still thin, promotion is not implemented, holdout
regression comparison is not yet automated, and sandbox live verify is blocked
by local Podman storage/image state.
- the official Stanford Meta-Harness reference repo is now vendored as
  `_ref/meta-harness` and is the normative external implementation reference
  for onboarding, proposer workflow, artifact logging and anti-overfit rules.

## Target State / Soll

Feature 016 turns the existing pieces into a production-oriented outer loop for
improving the Matrix agent harness:

1. A Meta-Harness runner plays simulated users against the real Python Agent.
2. The Base Agent runs with LiteLLM, memory, tools, consent and audit enabled.
3. Every scenario produces trace artifacts, scores and trace-gate verdicts.
4. The proposer reads source/config, all candidate artifacts, raw traces and
   scores through filesystem and MCP/CLI surfaces.
5. Candidate harness changes are evaluated on a search set and holdout set.
6. Promotion only happens when accuracy, tool behavior, memory behavior,
   safety, cost and latency gates do not regress.
7. Runner parity is first-class: in-process scenarios can target the app-like
   dispatcher, the LangGraph runner or the graphless SimpleLoop, while
   live-service scenarios naturally exercise the app dispatcher.

For memory work, "memory behavior" means more than a recall score. The harness
must prove that Hindsight, MemPalace and the orchestration path behave
correctly in their intended roles: compact learned context is injected when it
helps, verbatim evidence is recalled when exact prior context is needed, and
fresh/live data requirements are not bypassed by stale memory. Hindsight-only
and MemPalace-only runs are diagnostic eval modes, not a product decision to
make those systems compete.

The official Meta-Harness onboarding flow is now mandatory for Feature 016:
before broad implementation or candidate promotion, Matrix must keep a concrete
`data/meta_harness/domain_spec.md` covering fixed base agent/model surface,
candidate harness interface, search set, holdout set, metrics, leakage
controls, budget, baselines, logs and artifact layout. The proposer role for
now is this Codex session using local filesystem/GitNexus/MCP context; external
LLM proposer calls are disabled unless explicitly enabled for a run.

## Minimal Stack

Phase 1 can run without frontend and without Go Gateway.

Required:

- PostgreSQL for audit, sessions, component configs, A/B rows and memory.
  Trace gates read through `agent.audit.store.get_audit_store().query(...)`;
  persistent live Meta-Harness runs therefore need `AUDIT_DB_URL` or
  `HINDSIGHT_DB_URL` pointing at the Postgres-backed `agent.audit_events`
  table. JSONL audit remains a local smoke fallback, not the preferred source
  for full outer-loop evidence.
- LiteLLM Gateway for Base Agent calls. External proposer/judge LLM calls are
  optional and off by default while Codex is acting as proposer in this repo.
- Python Agent service or direct Python runner.
- `HINDSIGHT_DB_URL` / `AUDIT_DB_URL` configured for persistent traces.
- `AGENT_MEMORY_ENGINE=fusion|hindsight|mempalace` for memory scenarios.
  `fusion` means the production memory-orchestration path; `hindsight` and
  `mempalace` remain controlled eval modes for isolating regressions.
- CLI entrypoint for scenario runs, evaluation, proposal and history.

Optional for early phases:

- OpenObserve/Langfuse for visual trace inspection.
- Sandbox/OpenSandbox profile for sandbox/file/browser scenarios.
- MCP trace server for Codex/agent integration.

Not required for Phase 1:

- frontend_merger.
- Go Gateway/Appservice.
- Matrix room delivery.
- voice.

Those are live-product verification paths, not prerequisites for the
Python-only Meta-Harness search loop.

Sandbox is scenario-gated: missing OpenSandbox blocks sandbox/file/browser
cases, but it must not block core chat, memory, routing, RAG/KG or trace-store
Meta-Harness runs.

## Roles

- Simulated User: issues scenario turns and adversarial prompts.
- Base Agent: the Matrix Python agent being evaluated.
- Tool Runtime: ToolRegistry, consent gates, sandbox/file/browser/scheduler/A2UI
  and memory tools.
- Memory Runtime: automatic prefetch/retain plus explicit memory tools.
- Hindsight Layer: durable summary/fact/preference recall and correction.
- MemPalace Layer: verbatim/episodic recall, loci metadata and source evidence.
- Fusion Layer: combines both layers and exposes route/provider metadata.
- Trace/Audit Layer: raw events, spans, sessions, artifacts and candidate logs.
- Scorer/Judge: deterministic trace gates plus optional LLM-as-judge rubrics.
- Meta-Harness Proposer: this Codex/developer-side role inspects full history
  and proposes bounded harness, prompt, routing, memory and skill changes.
  External LLM proposer backends are later optional, not the default.
- Promotion Gate: keeps, rejects or defers candidate changes.

## Official Repo Alignment

Adopted from `_ref/meta-harness`:

- onboarding comes first and produces a domain spec before broad
  implementation.
- proposer analyzes results, raw traces and source; the outer loop runs
  validation/evaluation separately.
- candidates must test mechanisms, not only tune constants.
- search-set feedback and holdout results must stay separated.
- every run writes inspectable filesystem artifacts.
- anti-overfit rules prohibit scenario-specific hacks and hidden leakage.
- Pareto ranking uses hard feasibility gates first. Memory correctness is
  represented through trace gates, not by rewarding memory use in every task.

The two official skills are references, not drop-in Matrix skills. The
text-classification skill requires exactly three new memory systems per
iteration and its `MemorySystem` interface. The Terminal-Bench skill evolves a
coding scaffold and permits method-level agent rewrites in that benchmark. Both
encode assumptions that would be wrong for Matrix's trading/geomap/strategy
agent, so Feature 016 uses a Matrix-specific skill derived from their workflow
principles.

## Non-Goals

- No self-modifying live user runtime.
- No automatic production promotion without holdout results.
- No autonomous coding-agent product scope in this phase; developer-reviewed
  code patches are Meta-Harness experiments only.
- No frontend/Go dependency in the first implementation slice.
- No replacement of Feature 014 observability infra or Feature 015 skill
  evolution. Feature 016 consumes both.

## Closeout Criteria

- Python-only scenario runner executes at least one multi-turn search-set suite.
- Real ToolRegistry is available during eval runs unless a scenario explicitly
  disables tools.
- Memory recall/retain/tool behavior is asserted by trace gates for Hindsight,
  MemPalace and orchestration/fusion diagnostic cases.
- Matrix `domain_spec.md` exists and captures official onboarding assumptions
  before larger iterative search.
- Candidate artifacts are stored as navigable directories with source, config,
  scores, raw traces and verdicts.
- Proposer loop reads full artifacts, not only compressed summaries.
- CLI and MCP surfaces expose run/evaluate/propose/history/pareto primitives.
