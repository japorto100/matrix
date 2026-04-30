---
title: Meta-Harness Agent Optimization Research
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-30
feature_id: 016
---

# Research Notes

## Meta-Harness Paper Mapping

The paper's central claim is that harness engineering should be optimized as an
outer loop over executable code, not as a prompt-only tweak. The proposer is a
coding agent that reads a filesystem containing prior candidate source code,
scores and execution traces, then proposes new harnesses.

2026-04-30 full-paper reread correction: the important mechanism is not merely
having a Pareto command or running trace gates. The proposer needs filesystem
access to prior executable harnesses, score files and raw execution traces at
candidate granularity. Summaries are explicitly insufficient in the paper's
ablation. For Matrix, a valid proposer packet must therefore point to raw
`traces/**/*.json`, `sse/*.jsonl`, `scores.json`/`aggregate.json`,
`source_snapshot.json` and the candidate decision ledger. `meta_harness/` is
the optimizer; the optimized harness is the agent-adjacent runtime around it.

Matrix mapping:

- harness code: agent prompts, context assembly, memory policy, tool policy,
  routing, consent and runner behavior.
- execution traces: audit events, spans, SSE transcripts and session rows.
- scores: existing composite scorer plus scenario-specific trace gates.
- filesystem history: `data/meta_harness/runs/...`.
- proposer: Codex or LiteLLM-backed proposer, with bounded write scope.
- search set: scenario fixtures.
- test set: holdout fixtures hidden from proposer during search.

Important implication: the current proposer path is useful but insufficient
because it compresses traces into short summaries. Feature 016 needs raw,
queryable artifacts.

Implemented follow-up: `meta_harness.outer_loop` creates
`candidate_manifest.json` and `experience_packet.json` artifacts. The manifest
marks missing source snapshots, scores, raw traces/benchmark evidence and
holdout-visible files as paper-readiness failures. The experience packet keeps
frontier/dominated candidates, failure clusters, decisions and inner-loop
candidates together while excluding holdout results from proposer context.

Evaluator-sidecar correction: paper-readiness must not accept an empty trace
file. `candidate_manifest.json` now records trace event count and fails with
`trace-empty` or invalid trace-list errors. The proposer-visible decision stream
sanitizes any `holdout*` fields, and `promotion-check` fails closed unless
pending-eval, search, holdout and safety evidence are all present.

Role separation for Codex-run loops:

- Codex-as-proposer may inspect search artifacts and edit bounded runtime
  surfaces.
- Codex-as-simulated-user may drive fixed search scenarios to collect traces.
- The frozen evaluator remains the CLI/trace-gate/Pareto lane; proposer notes
  cannot certify promotion.
- Holdout execution remains an explicit promotion step and is not visible in
  proposer packets.

## Official Repo / Domain-Spec Correction

The official Stanford repo reinforces a stricter structure than the early
Matrix implementation used:

- every optimization target needs a domain-spec style contract: fixed task
  definition, fixed harness interface, fixed evaluator, search set, holdout
  set, allowed edit scope, budget and logging rules.
- the proposer may inspect traces and candidate history, but it must not
  change the evaluator during the same run.
- the proposer does not self-certify. Promotion requires a separate outer-loop
  evaluation against frozen gates.
- one candidate should be a falsifiable harness change, config overlay or
  bounded patch with a clear expected metric movement.

Matrix implication after the 001-023 review: Feature 016 should first optimize
source-grounding units that already have deterministic evidence paths
(ingestion, retrieval, KG boundary, memory route correctness) before broad
"make the agent better" loops. Full-stack UI behavior remains a live-verify
surface, not the first Meta-Harness optimization domain.

## Why Simulated User Matters

The paper evaluates harnesses by running task instances. For Matrix, task
instances are not just one prompt; they are user sessions that intentionally
exercise:

- memory creation, recall and correction.
- tool selection and refusal.
- consent handling.
- sandbox/file/browser analysis.
- scheduler setup without production delivery.
- skill retrieval/refinement.
- A2UI emission.

Therefore the Meta-Harness runner must play the user, not only post-process
organic logs. Organic logs are valuable later, but bootstrapping requires
designed scenarios.

## Tool Findings

The real tool set lives in `ToolRegistry.load()` and includes memory, canvas,
sandbox, A2UI and scheduler tools. The current `data/harness/search_set` expects
`market_data_fetch` and `chart_analysis`, which are not registered tools. Those
entries are historical intent and need migration to actual tool expectations or
to rubric-only tasks.

The current evaluator constructs `AgentExecutionContext(..., tools=())`, while
`llm_node` and `tool_node` independently load ToolRegistry. This ambiguity must
be removed for eval correctness. A scenario should be able to say whether tools
are enabled, restricted or expected.

2026-04-29 follow-up from `Z_Additional_For_Tool_Stuff.md`: the Z_ recommendation
is not MCP-only. It applies to normal `ToolRegistry` tools too: builtin memory,
sandbox, browser/file analysis, scheduler, canvas/A2UI and market tools need a
catalog, tool groups, progressive disclosure, risk/approval metadata and output
compaction gates. Feature 024 remains the MCP-specific external descriptor
owner; Feature 016 owns harness/eval pressure for normal tools.

2026-04-29 implementation follow-up: Meta-Harness trace gates now understand
normal tool catalog metadata through `allowed_tool_groups` and
`max_tool_disclosure_level`. This lets scenario files assert that a risky normal
tool such as sandbox execution was not exposed or used unless the scenario's
tool-group contract explicitly allows it.

2026-04-29 output follow-up: normal builtin tool outputs now get a direct
post-sanitizer cap in `tool_node` before model re-entry. This complements the
later context-compaction pass: raw `tool_results` stay available for audit and
debug artifacts, but the next LLM call receives bounded, marked content.

## 2026-04-30 Knowledge Contract Follow-Up

The Memory/KG/RAG/Semantic slice should be optimized as one knowledge-layer
contract, not as disconnected feature checkboxes. The current implementation
adds `meta_harness.knowledge_contract` and CLI `knowledge-contract` as a
provider-free lane. It proves five boundary behaviors:

- Memory-Fusion recall/retain traces preserve raw evidence refs, source status,
  operation logs and diffs before compaction.
- The Feature 012 T039q variant additionally treats summary retain as
  incomplete unless exact visible session text, tool input/output refs, tool
  call id, source timestamp and Matrix room/thread/session refs are present.
- Personal memory cannot silently promote to global KG without evidence refs,
  citation refs, valid/system time and semantic term links.
- Selected RAG/KG context carries source artifact, chunk/hash, citation and
  semantic catalog metadata before answer support.
- Semantic ambiguity and missing tenant permission fail closed and keep
  `raw_sql_allowed=false`.
- User semantic corrections become review proposals, not silent truth changes.

This maps the local `Z_Semantik_layer and so on.md` direction and the RAG/KG
papers into a falsifiable harness lane: definitions, evidence and graph claims
must remain provider-agnostic and auditable before any live/browser/provider
optimization is allowed to promote them.

## 2026-04-30 Meta-Harness Credential Boundary

The `anonymous` eval user is a local harness convenience, not a production
credential bypass. The in-process runner and live FastAPI Meta-Harness hook now
default process-env provider credentials to development/local/test only. In
production or staging the env-key path is closed unless
`META_HARNESS_ALLOW_ENV_CREDENTIALS=true` is explicitly set, and live requests
still need a Meta-Harness run id plus a key that matches the server env. Normal
named users continue through `agent.user_credentials`/CredentialPool policy.

## Memory Findings

Memory is both automatic and explicit:

- automatic prefetch in `_prepare_system_prompt` through MemoryManager or
  fallback Hindsight.
- explicit `memory_search` and `memory_add` tools.
- working memory `save_memory` and `load_memory`.
- memory_fusion operation logging can emit `memory_recall` and `memory_retain`
  audit actions when operation context is propagated.

Scenarios should test all three categories: automatic recall, explicit memory
tool calls and working-memory scratchpad.

## EvoSkill Mapping

EvoSkill should not replace Meta-Harness. It is the skill-specific evolution
layer:

- failure cluster -> skill or prompt proposal.
- generator writes skill/prompt changes.
- evaluator scores the variant.
- frontier keeps the best variants.
- feedback history helps avoid repeating failed ideas.

Matrix already has a simple SkillEvolver, finder, refiner, trigger-quality and
skill Pareto helper. Missing before real EvoSkill-style automation:

- benchmark/search set per skill class.
- candidate skill versioning and rollback.
- promotion gate based on repeated success.
- edit-existing vs create-new decision.
- root-cause feedback history.

## Autoresearch Mapping

Autoresearch contributes process discipline, not direct runtime code:

- fixed evaluator.
- fixed budget.
- one run log.
- keep/discard/crash status.
- rollback on regression.
- do not change evaluator during the loop.

For Matrix this means scenario fixtures and judges are frozen during a run.
Harness candidates may change; the scoring harness may not.

Inner-loop bridge decision: inner loops should be connected, but only as
candidate generators. A RAG/KG/memory/tool-policy inner loop can produce typed
candidate artifacts with frozen inputs and metrics. The Meta-Harness outer loop
must still decide promotion after trace gates and Pareto ranking. This avoids
turning inner-loop sweeps into hidden evaluator mutation or self-certification.

## Early Implementation Slice

Recommended first slice:

1. Define scenario schema.
2. Implement Python-only runner over 3 scenarios: simple no-tool, memory
   remember/recall, one harmless tool.

## 2026-04-29 Provider Lane Hardening

The fresh `Z_` docs pushed the harness work toward provider-agnostic live
verification instead of an OpenRouter-only lane. The implemented slice follows
ADR-0009: keep `llm-mock` as a deterministic contract lane, add
`provider-smoke` for configured-provider metadata and optional chat completion,
and write provider capability snapshots into Meta-Harness run artifacts. This
keeps Meta-Harness useful for static/non-browser gates before browser live
verification starts.

## 2026-04-30 Contract Suite Aggregation

The stable provider-free lanes now have a single `contract-suite` command. This
keeps static backend agent contracts visible before browser/live work starts:

- Feature 020: route/delegation/loop-guard contract.
- Feature 015: skill audit lifecycle, usage sidecar and reload-control policy.
- Feature 024: MCP catalog poisoning and descriptor-drift policy.
- Feature 027: report artifact grounding, citations and unsupported-claim
  failure.
- Feature 030: Matrix widget approval, unsafe URL denial and MCP resource
  handoff denial.

This is intentionally not a substitute for live UI/provider verification. It is
the frozen, cheap contract lane that should run before larger implementation
passes and before any future subagent behavior is promoted.

## 2026-04-30 Python-Backend Domain Contract

The Meta-Harness paper plus the official `_ref/meta-harness` onboarding make a
hard distinction between real optimization and placebo optimization: a candidate
must change a declared harness surface and then be evaluated by a frozen
evaluator over a search split and protected holdout. Autoresearch reinforces
the same discipline with one modifiable target, a fixed time budget, a fixed
metric and keep/discard/crash logs.

The implemented `meta_harness.domain_contract` turns that into a provider-free
Matrix backend gate. It declares optimization domains for:

- agent runtime routing.
- Matrix transport/session hygiene.
- subagent delegation roles.
- skills lifecycle/curator.
- tool gateway/policy.
- memory/context fusion.
- source ingestion/parser handoff.
- hybrid RAG retrieval.
- KG/semantic provenance.

Every domain carries allowed write scopes, frozen evaluator, search/holdout
split, budget, metrics, source artifacts and forbidden edits. Runtime domains
reject docs-only candidates, reject Meta-Harness self-edits and require source
artifacts plus metric targets.

Hermes Agent is useful here as a reference corpus, not as a product blueprint.
The fresh `_ref/hermes-agent` update to `fc7f55f49` contributes transfer
signals:

- Curator/skill usage: agent-created skills need usage sidecars, pinned-skill
  write fences, archive-not-delete behavior and per-run reports.
- Delegation: children start with fresh context, leaf delegates cannot clarify,
  write shared memory or send messages, orchestrator role/depth is opt-in, and
  interrupts propagate.
- Tool/plugin lifecycle: pre-tool veto, schema sanitizer, output caps and
  fail-open observability are good gate patterns, but any mutation hook must be
  audited before runtime adoption.
- Provider hardening: resolved secrets and provider-specific reasoning blocks
  must not leak into traces, memory or KG evidence.
- Matrix transport fixes: Hermes' Matrix adapter/changelog is directly
  relevant because our product is Matrix-native. It highlights echo or pairing
  loops, mention/thread gates, approval reactions, message chunking,
  reconnect/session hygiene and X-sign/bootstrap as classes of bugs we should
  test in our Matrix appservice/bridge/webclient path.

Non-transferable: Hermes is a CLI/gateway coding agent. Matrix should not
adopt its subagent product behavior, platform gateway architecture, TUI overlay
or plugin hook power 1:1. These references inform contracts and gates only.
3. Write artifact directory.
4. Add deterministic trace gates.
5. Add CLI JSON output.
6. Then extend proposer to read artifact directories.

## 2026-04-26 Live Outer-Loop Findings

The first real service-mode Meta-Harness rounds produced implementation fixes,
not only documentation:

- Live trace gates must require `tool_call` or `tool_result`; a
  `consent_request` alone cannot satisfy a required-tool gate.
- Meta-Harness session consent must be granted inside the running agent service,
  not only inside the harness process. The live service now accepts an explicit
  Meta-Harness-only consent header and records session consent before graph
  execution.
- LangGraph must not compile with unconditional `interrupt_before` on
  `approval_gate`; otherwise service-mode tool calls stop before execution and
  no normal resume path exists.
- The sandbox SDK import has drifted: the installed
  `opensandbox-code-interpreter` exposes `code_interpreter`, while older code
  imported `opensandbox_code_interpreter`. The sandbox manager now supports both
  module names.
- Pareto ranking must treat completion and trace gates as hard feasibility
  gates. Failed zero-token candidates otherwise appear Pareto-optimal because
  they look cheap.

Current live evidence:

- `run-8ba52ec0f56e` exercised chart, portfolio, memory and sandbox scenarios
  through the real FastAPI service with OpenRouter/LiteLLM.
- Chart, portfolio and explicit memory scenarios passed trace gates with real
  `tool_call` and `tool_result` audit events.
- Sandbox consent worked and `sandbox_execute` was called, but the tool result
  failed because the local OpenSandbox code image/runtime is not available.
- The sandbox infra blocker is machine state, not agent planner behavior:
  OpenSandbox `:8080` starts, but `/` has about 4 GB free and pulling
  `opensandbox/code-interpreter:v1.0.2` failed with `no space left on device`.

## 2026-04-27 Feature Review Consequence

The 001-023 checkpoint split the remaining work into two categories:

- live verification debt: Matrix UI, ElementX/Tuwunel, Control UI tabs and
  Agent Chat surfaces need real user-flow evidence.
- implementation/research debt: Python Agent, memory, RAG, KG, ingestion,
  optimization loops and subagent routing still have concrete code/spec work.

Meta-Harness should therefore operate on stable backend domains first:

1. parser/chunk/retrieval benchmark candidates from Features 021/019/022/023.
2. memory lifecycle and Hindsight/MemPalace/Fusion route correctness from
   Feature 012.
3. route/tool/provider/compression behavior from Features 011/013/016/020.

It should not be used to claim UI completion unless the trace contains the
actual frontend/API path being verified.

## 2026-04-29 Feature 024-030 Domains

The Z_ pass adds new Meta-Harness domains:

- Feature 024: MCP catalog policy and tool-poisoning resistance from
  `Z_Additional_For_Tool_Stuff.md`.
- Feature 025: semantic metric/claim correctness from
  `Z_Semantik_layer and so on.md`.
- Feature 027: report artifact grounding from
  `Z_Tool_very interessting Quarkdown.md`.
- Feature 028: visual memory provenance from
  `Z_Chatgpt_Chronicles vs DeepseekOCRpaper.md`.
- Feature 029: ops-room replay and status compression from
  `Z_Hermes_Desktop_claw3d.md`.
- Feature 030: Matrix widget proposal/fallback behavior from
  `Z_matrix_widgets_formulars_and so on.md`.

All scenarios must remain provider-agnostic. The harness can call whatever
configured provider is available, but the gates judge behavior, traces and
artifacts, not vendor-specific response style.

## 2026-04-30 Agent Chat Stream Findings

The Meta-Harness paper requirement for raw execution traces is necessary but
not sufficient for Agent Chat UI claims. Agent Chat has two downstream truths:

- backend trace truth: Postgres/audit events prove route decisions, skills,
  tool calls, memory events and scoring.
- UI stream truth: SSE data parts prove what the frontend can render in
  `AgentChatMessage`, `AgentChatToolBlock`, `ToolOutputRenderer`,
  A2UI surfaces and artifact components.

Headless HTTP against the real Next BFF route `/api/agent/chat` is enough to
prove stream shape without rendering a browser, because the React UI consumes
the same AI SDK stream parts. Browser/Playwright is still required for visual
layout and rich-renderer correctness.

Live evidence from `run-live-frontend-chat-20260430-db`:

- `get_chart_state` and `get_portfolio_summary` were visible both as backend
  audit `tool_call`/`tool_result` and as SSE `tool-input-start` /
  `tool-output-available`; these map to rich chat renderers.
- `memory_add` and `memory_search` were also visible in audit and stream, but
  their payloads said `Memory not available`. This is not a successful memory
  scenario even if transport-level `success=true`, so gates now fail on
  soft-unavailable payloads.
- Frontdoor trace requires DB stability before the run; an earlier run through
  `/api/agent/chat` produced UI-visible tool parts but no audit events because
  Postgres had been smart-shutdown. The correct response is a failing harness
  artifact, not manual success.

## 2026-04-30 Memory Provider Hardening

The live frontdoor memory gap came from the embedding provider, not from the
LLM chat provider. OpenRouter chat completed through LiteLLM, while
OpenRouter embeddings returned 402, causing `auto_fusion_provider` to return
`None`. Meta-Harness now treats that as a failing dependency, and
memory_fusion has an explicit `MEMORY_EMBEDDING_PROVIDER=deterministic`
lane for dev/harness orchestration runs.

This remains provider-agnostic: the harness records provider/model/dimension
and evaluates behavior. Deterministic embeddings may prove that Agent Chat,
tools, audit, Fusion routing and UI stream surfaces work. They must not be used
to promote retrieval-quality, ranking or semantic-memory claims without a
separate real embedding candidate and holdout evaluation.

## 2026-04-30 Live Provider Quota Finding

`openrouter/openrouter/free` is an unreliable live-gate model selector for
Agent Chat verification: LiteLLM reports missing model metadata and the router
can stall long enough to trigger turn timeouts. A concrete OpenRouter free
model, `openrouter/nvidia/nemotron-3-super-120b-a12b:free`, successfully ran
the direct Agent endpoint and produced real tool, memory and stream traces.

Follow-up live evidence:

- `run-live-agent-direct-20260430-memory-fixed` proved that the memory
  dependency was fixed: `memory_add` returned `stored=true`, `memory_search`
  ran, Fusion/Verbatim routes were observed and stream gates passed.
- The only remaining gate failure in that run was skill coverage: the memory
  prompt contained `risk per trade`, but only `memory-usage` fired. The
  Skill-Finder now preserves `risk-assessment` for memory intents that also
  contain risk/trade/position-sizing terms.
- `run-live-agent-direct-20260430-memory-risk-skill` then proved the corrected
  skill selection in audit, but OpenRouter returned `429 free-models-per-day`
  before the model could call tools. This remains a live-provider quota
  blocker, not an agent/memory regression.

## 2026-04-30 Cache / Runtime Event Harness Transfer

Inputs: Feature 032, Feature 033, Meta-Harness paper reread and the Z_ pass.

Meta-Harness gates need both upstream and downstream evidence. Upstream evidence
means request, prompt-layout, tool-policy, memory/RAG/KG and provider counters.
Downstream evidence means the events that Agent Chat or Control UI would show:
tool cards, artifacts, PDFs/data files, report links, subagent summaries and
error/degradation markers.

The harness therefore needs scenario assertions over:

- prompt-cache/request telemetry completeness and cache-break hypotheses.
- runtime event envelope completeness and event ordering.
- subagent isolation, parent-side memory curation and child trace rollups.
- ingestion/RAG/KG downstream artifact visibility, not only retrieval scores.

2026-04-30 implementation note: the first non-browser runtime-event gate is
now in the provider-free routing contract. The harness reads nested
`runtime_events` from audit rows and can require event names plus required or
forbidden metadata keys. This specifically covers the Feature 032/033
intersection: prompt-cache break events must expose cache diagnostics useful to
the evaluator while omitting raw prompts, headers, authorization fields,
resolved secrets and full request telemetry. The next step is to reuse the same
gate vocabulary for subagent isolation and RAG/KG downstream artifact scenarios.

2026-04-30 subagent gate update: `TraceExpectations` can now assert
runtime-event metadata values, including list membership. The routing contract
uses this to check the Hermes-derived but Matrix-specific isolation rule:
child tasks run in isolated context, get a narrow tool allowlist, cannot retain
directly into shared memory, and return only a parent-side memory handoff with
digest metadata. This is intentionally provider-free and synthetic, so it tests
the trace contract before any live A2A/provider run.

2026-04-30 downstream artifact update: stream gates can now require concrete
stream parts, rich renderer candidates and artifact filenames. The
provider-free `knowledge-contract` uses this to make RAG/KG success depend on
both upstream provenance (`rag.retrieval.completed` and `kg.context.selected`)
and downstream Agent Chat-visible artifacts (`rag-kg-sources.json` and
`kg-paths.json`). This prevents a retrieval-only candidate from passing while
the UI would have no inspectable sources or paths.

The proposer can still be Codex/manual during this phase, but candidate packets
must contain enough raw traces for an evaluator to reject placebo changes.

2026-04-30 retrieve-context implementation update: the downstream artifact gate
now reaches actual agent runtime, not only synthetic stream fixtures.
`retrieve_context` is registered in the real ToolRegistry, consumes exact
semantic handoff metadata, emits RAG/KG/artifact runtime events, and uses
tool-specific `to_model_output()` so Meta-Harness can evaluate both upstream
retrieval behavior and downstream source/path visibility without filling the
next LLM context with full artifact payloads.

2026-04-30 memory fixture reproducibility update: `memory-context-smoke` now
writes `memory_fixture_manifest.json` for the run and for each candidate. The
manifest records the synthetic memory bank/thread, Palace/evidence refs,
expected providers/terms, evidence digest and replay command. This makes
memory regressions inspectable as candidate artifacts instead of requiring the
proposer/evaluator to infer fixtures from trace rows.

2026-04-30 memory source-gate update: the Z_ Memory/KG/RAG notes and
Feature 012 evidence rule imply that "memory happened" is not enough. The
trace must identify which path wrote or read memory. `TraceExpectations` now
supports provider-agnostic audit metadata value gates, and the memory lifecycle
fixtures require automatic prefetch (`memory_recall_node`), automatic
post-answer retain (`automatic_memory_retain`) and explicit tool paths
(`explicit_memory_tool`) to be distinguishable. A new correction scenario
checks stale-vs-current preference drift before any LLM judge is allowed to
score the answer.

2026-04-30 memory holdout split update: the Z_ Memory/KG/RAG notes push the
harness to keep memory correction/source-boundary regressions separate from the
proposer-visible search loop. `data/harness/memory_holdout/queries.json` now
contains protected memory-only holdout fixtures for correction drift, source
evidence and Personal-Memory-vs-KG/RAG boundary behavior. The evaluator treats
`memory_holdout` like `holdout`: it is blocked unless explicitly allowed, and
the CLI exposes it only as a protected split. Legacy query scoring now carries
`forbidden_tools`, which matters because memory holdout cases often need to
prove "recall without write" rather than generic memory activity.

2026-04-30 memory diagnostic fixture expansion: Feature 012's Hindsight vs
MemPalace distinction is now reflected in `memory_lifecycle` fixtures instead
of only prose. The added scenarios separate summary-provider behavior
(`hindsight`/`summary`), verbatim episodic behavior (`mempalace`/`verbatim`
with loci and session/source refs), Fusion combine behavior and Fusion conflict
behavior where fresh source-backed verbatim evidence overrides a stale summary.
This is still provider-agnostic at the harness level: route/provider names are
trace contracts, not vendor APIs.

2026-04-30 memory anti-bloat runtime update: Feature 012 now has an actual
runtime guard, not only an eval intention. `memory_recall_node` classifies pure
current/live-market questions without personal-memory cues as
`current_market_without_personal_memory_cue`, skips the Memory-Fusion engine
lookup and surfaces `memory.recall.skipped`. Market prompts that mention
personal allocations, previous preferences or explicit recall still flow into
normal memory recall. This gives the Meta-Harness a clean upstream signal for
"no MemPalace injection" without relying on absence of context text alone.

2026-04-30 embedding audit update: Memory-Fusion now exposes redacted embedding
provider metadata through a provider-agnostic snapshot. The Meta-Harness can
inspect provider/model/base-url host, key presence/fingerprint, quota policy and
live-call budget without ever seeing the raw OpenRouter key. This supports
Feature 012 T039f while keeping model-quality selection (T039e) as a separate
Pareto/search problem.
