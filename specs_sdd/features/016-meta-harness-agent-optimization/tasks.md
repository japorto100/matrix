---
title: Meta-Harness Agent Optimization Tasks
status: implementation_started
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 016
---

# Tasks

## SDD / Design

- [x] T001 Read Meta-Harness paper and map it to Matrix runtime.
- [x] T002 Deepdive existing Python Agent, harness, audit, memory, skills and
  tools code paths.
- [x] T003 Create Feature 016 with stack, roles, architecture and gates.
- [x] T004 Add official Stanford Meta-Harness repo as `_ref/meta-harness`.
- [x] T005 Read official repo onboarding and example skills; record Matrix
  deviations from their text-classification and Terminal-Bench assumptions.
- [x] T006 Write initial Matrix Meta-Harness `domain_spec.md`.
- [x] T007 Create Matrix-specific Meta-Harness skill for Codex-as-proposer.
- [x] T008 Add CLI/config guard so external LLM proposer/judge calls are disabled
  by default unless a run explicitly opts in.
- T009 Keep autonomous coding-agent product behavior out of scope; bounded
  developer-reviewed harness patches remain allowed as experiments.
- T009a Security-review Meta-Harness/dev `--user-id anonymous` behavior: prove
  it is local-eval scoped and does not bypass production CredentialPool,
  user-key, quota, audit or billing policy for named users.

## Scenario Runner

- [x] T010 Define scenario fixture schema with multi-turn support.
- [x] T011 Implement Python-only scenario runner in service mode.
- [x] T012 Implement or decide in-process runner path.
- [x] T013 Capture SSE transcripts per scenario.
- [x] T014 Assign stable `user_id`, `thread_id`, `scenario_id`, `run_id` and
  `candidate_id` metadata.
- [x] T015 Split search set and holdout set; proposer must not see holdout scores.
- [x] T016 Add explicit in-process runner variants for `dispatcher`,
  `langgraph` and graphless `simple`.
- [x] T017 Add CLI support for selecting the in-process runner variant.
- [x] T018 Make legacy evaluator/search-set runs use the same runner-variant
  plumbing instead of hardcoding LangGraph.
- T019 Add parity scenarios that run the same tool/memory fixture against
  `dispatcher`, `langgraph` and `simple` and compare trace gates.
- [x] T019a Add a minimal no-tool runner-parity scenario for isolating runner
  health without sandbox/tool availability.

## Tool-Aware Evaluation

- [x] T020 Make evaluator run with the real ToolRegistry by default.
- [x] T021 Add per-scenario required/forbidden tool assertions.
- [x] T022 Add consent decision assertions for risky tools.
- [x] T023 Normalize current `queries.json` expected tools to actual Matrix tool
  names or mark them historical placeholders.
- [x] T024 Add sandbox/file/browser scenarios gated by local sandbox availability.
- T025 Add scheduler tool scenarios without requiring Matrix delivery.
- T026 Add A2UI surface scenarios that assert `render_a2ui_surface` behavior.

## Memory-Aware Evaluation

- T030 Add memory fixture setup and cleanup for eval users.
- T031 Assert automatic memory prefetch on recall scenarios.
- T032 Assert memory retain on remember/correction scenarios.
- T033 Assert explicit memory tools when the user asks to store/search memory.
- [x] T034 Record Hindsight/MemPalace/Fusion route metadata in trace artifacts.
- T035 Add conflict/correction scenarios to detect memory drift.
- T036 Add Hindsight diagnostic scenarios that verify summarized preference/fact
  recall, update, deletion and outcome-learning behavior.
- T037 Add MemPalace diagnostic scenarios that verify verbatim/episodic recall,
  loci metadata, source/session refs and query-sanitization behavior.
- T038 Add orchestration scenarios where Hindsight and MemPalace both contain
  useful but different evidence, and the agent must combine them without
  inventing.
- T039 Add orchestration conflict scenarios where MemPalace verbatim evidence
  should constrain or correct stale Hindsight summaries.
- T039a Add a scenario proving global KG/nonicdb retrieval is not used as an
  agent-memory substitute when the expected behavior is Hindsight or MemPalace
  recall.
- T039b Add a scenario proving Hindsight KG-like memory stays in the
  agent-memory lane and does not silently promote to Feature 017 global KG.
- T039c Add a scenario proving MemPalace Postgres archive uses room/thread/
  session identifiers and preserves tool-output evidence across compaction.
- [x] T040 Add memory route assertions for `summary`, `verbatim`, `hybrid` and
  provider mode `hindsight|mempalace|fusion`.
- T041 Add memory holdout set that is not visible to proposer/search runs.
- T042 Add deterministic memory correctness gates before any LLM judge:
  expected recall terms, forbidden stale terms, evidence/source presence and
  no unrelated mutation.
- T043 Record memory fixture manifests per run so failed scenarios can be
  reproduced with the same user, bank, palace path and provider env.
- T044 Keep old `experiments/memory_eval` A/B evidence linked to the
  Meta-Harness memory scenarios instead of treating it as separate history.
- [x] T045 Wire `pre_save` stage to call the MemoryManager archive hook without
  mutating visible context.
- [x] T046 Wire `compaction` stage to archive before mechanical truncation.
- [x] T047 Keep `emergency`/compression archive-before-summary behavior and
  use the same per-user memory bank id shape as prefetch/sync.
- [x] T048 Make `FusionProvider.sync_turn` persist through
  `retain_batch_async` so Fusion routes receive normal turn writes.
- [x] T049 Make `FusionProvider.on_pre_compress` archive raw visible messages
  into Fusion before context reduction.
- [x] T050 Add deterministic Meta-Harness trace gates for memory route/provider
  metadata.
- [x] T050a Make explicit `memory_add`/`memory_search` tool paths emit
  `memory_retain`/`memory_recall` audit events with Fusion route/provider
  metadata so trace gates can evaluate them.
- [x] T051 Capture Memory-Fusion runtime hypotheses in Meta-Harness config
  snapshots: embedding provider/model, Verbatim backend, Hindsight reranker
  provider and canonical bank id shape.
- T052 Add explicit Pareto candidate runs for embedding dimension/model:
  384 baseline, 768/1024 stronger open embeddings, 1536 OpenAI-compatible and
  2048 free OpenRouter smoke, each with reset/re-embedding evidence.
- T053 Add explicit Pareto candidate runs for reranker strategy: `rrf` baseline,
  local cross-encoder, TEI/remote and LiteLLM/Cohere-compatible rerankers.

## Candidate Store

- [x] T060 Implement `data/meta_harness/runs/<run_id>/candidates/<candidate_id>/`
  artifact layout.
- [x] T061 Store source/config snapshots, raw traces, SSE, scores and verdicts.
- T062 Store proposal JSON and patch/diff for candidate changes.
- [x] T063 Add run manifest with stack versions and env flags.
- [x] T064 Ensure artifacts are easy to query with `rg`, `fd`, `jq` and `bat`.

## Proposer Loop

- [x] T070 Extend proposer input from truncated summaries to artifact-directory
  inspection.
- T071 Add candidate generation mode for prompt/config overlays without
  external LLM calls by default.
- T072 Add candidate generation mode for bounded developer-reviewed code
  patches.
- T073 Add failure clustering over scenarios, trace gates and root causes.
- T074 Keep proposer free to inspect full history, but constrain write scope and
  forbidden actions.
- [x] T075 Add keep/discard result log inspired by Autoresearch.
- T076 Implement official-style proposer iteration ledger:
  analyze -> prototype/patch -> pending_eval -> outer-loop evaluate -> decide.
- T077 Persist proposer interaction/log summaries even when Codex, not an API
  LLM, acts as proposer.

## Scoring / Promotion

- [x] T080 Add deterministic trace-gate verdicts before LLM judging.
- [x] T080a Make trace gates fail by default when observed tool results fail;
  scenarios can opt into `allow_tool_failures` only when failure handling is the
  behavior under test.
- T081 Add task/rubric judge interface for scenario success.
- [x] T082 Combine score dimensions into Pareto frontier: success, trace gates,
  tool correctness, memory correctness, safety, cost and latency.
- [x] T082a Remove raw memory utilization as a generic Pareto/fitness bonus;
  memory correctness is judged by trace gates.
- [x] T082b Add feasibility reasons plus cost/latency efficiency dimensions to
  Pareto artifacts.
- T083 Add holdout regression gate.
- T084 Add promotion command that stages candidate only after gates pass.
- [x] T085 Record rejected candidate reasons for future proposer inspection.
- [x] T086 Record kept candidate reasons after live trace gates pass.
- [x] T087 Split Meta-Harness out of `agent/` into top-level
  `meta_harness/` package so production agent runtime and outer-loop optimizer
  have a clear boundary.

## CLI / MCP

- [x] T090 Add CLI `run` command for scenario files.
- [x] T091 Add JSON output mode for implemented CLI command.
- [x] T092 Wrap stable CLI primitives in MCP tools after schemas settle.
- [x] T093 Document required local stack commands and env variables.
- [x] T094 Add CLI `evaluate`, `propose`, `loop`, `decide`, `history` and
  `pareto` primitives with holdout/external-LLM guards.
- [x] T095 Add/configure `AGENT_MAX_OUTPUT_TOKENS` so Meta-Harness and live
  agent turns do not request provider-default giant completions that can fail
  budget gates before scenario quality is measured.
- [x] T096 Use Meta-Harness memory lifecycle traces to find and fix the explicit
  `memory_add` timeout loop: synchronous MemPalace verbatim write, background
  Hindsight summary retain, and corrected personal-memory fact-type defaults.
- [x] T096a Add explicit tool-instruction compliance prompt and disambiguate
  `save_memory` vs `memory_add` after Meta-Harness observed the agent choosing
  scratchpad memory for persistent project memory.
- [x] T096b Normalize LLM-invented memory fact types after Meta-Harness observed
  `memory_search(fact_type=memory_lifecycle_probe)` causing a recoverable tool
  error before a successful retry.
- [x] T096c Add Meta-Harness turn timeouts and make timeout an explicit
  trace-gate failure; timeout scenarios must stop additional turns instead of
  accidentally passing after late background tool work.
- [x] T096d Preserve explicit CLI environment over `.env.development` so
  Meta-Harness variants can intentionally test memory engines, providers and
  timeout budgets.
- [x] T096e Propagate `enable_tools=false` through LangGraph/SimpleLoop state to
  `llm_node` so runner-parity no-tool scenarios cannot request real tools.
- [x] T096f Add in-process Meta-Harness ENV credential fallback for named
  simulated users so `meta-harness` can keep its own memory bank without a DB
  credential row; live service requests still use normal user credentials.
- [x] T096g Bound post-answer `memory_retain_node` with
  `MEMORY_RETAIN_TIMEOUT_SEC` so slow retain/coherence cannot block SSE finish
  after the LLM has already produced a final answer.
- [x] T096h Strip provider-leaked reasoning markers such as
  `analysis...assistantfinal` before assistant text reaches SSE, audit output
  or session memory.
- [x] T096i Pin the effective default model once per scenario-file run so later
  scenarios in the same candidate cannot lose the model through runtime/env
  mutation.
- [x] T096j Use Meta-Harness runner-parity smoke after Feature 018 to expose
  and fix LiteLLM container DB routing: container DSN must use `postgres:5432`,
  not host-local `localhost:5433`.
- T097 Add a dedicated latency Pareto candidate for Memory-Fusion first-call
  warmup and remote embedding calls; current pass is correct but still slow.
- [x] T097a Add explicit `memory_add` deduplication for repeated normalized
  content/fact-type writes in the same thread and short time window after
  Meta-Harness exposed duplicate writes in `run-eeb4e11fab0f`.
- T097b Add a deterministic duplicate-memory-tool trace gate: if one assistant
  turn calls `memory_add` multiple times with the same normalized content/fact
  type, warn or fail the candidate unless the scenario explicitly expects
  duplicate writes.
- T098 Reduce skill over-selection in explicit memory probes; current
  `lp-memory-001` passes but still loads `market-research`, `risk-assessment`
  and `plan` alongside `memory-usage`.
- T099 Start or mock OpenSandbox before sandbox live probes; current
  `lp-sandbox-001` selects `sandbox_execute` correctly but fails because the
  sandbox service endpoint is unreachable.

## EvoSkill Bridge

- T100 Defer full EvoSkill bridge until Scenario Runner and Candidate Store are
  live.
- T101 Define skill candidate promotion contract using Feature 015 skill store.
- T102 Use skill trigger-quality and audit events as skill-specific trace gates.

## Domain Search Sets

- T110 Define trading-analysis search/holdout scenarios with current-data and
  source-quality requirements.
- T111 Define geopolitical/geomap search/holdout scenarios with temporal entity
  and provenance requirements.
- T112 Define strategy-review scenarios where memory can help with user
  preferences/process, but live market claims require current tools.
- T113 Define skill-selection scenarios that compare existing skills, imported
  public skills and newly authored Matrix skills under the same trace gates.
- T114 Define a global-KG scenario set where nonicdb/NornicDB context is
  expected only for world/domain facts, not personal agent memory.

## Verify Gates

- Python-only scenario suite runs without frontend and Go.
- Real ToolRegistry is exercised in at least one eval run.
- Memory recall/retain/tool trace assertions pass on Hindsight, MemPalace and
  orchestration scenarios.
- Meta-Harness credential mode is explicit: anonymous/dev runs are documented,
  named-user runs require DB credentials or fail closed.
- Candidate artifact directory contains raw traces and scores.
- Proposer consumes candidate artifacts rather than one compressed summary.
- Matrix Meta-Harness `domain_spec.md` exists before larger iterative searches.
- Pareto CLI can load existing artifact history and reports feasibility,
  cost/token/latency dimensions.
