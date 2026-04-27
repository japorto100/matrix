---
title: Meta-Harness Agent Optimization Live Verify
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-27
feature_id: 016
---

# Live Verify

## MV-00 Memory Lifecycle Unit Verify

Status: pass on 2026-04-26.

Scope: backend-only memory lifecycle before frontend/Go integration.

Commands:

- `cd python-backend && uv run --frozen ruff check memory_fusion/memory_provider.py agent/graph/runner.py meta_harness/scenario_runner.py tests/test_memory_provider.py tests/agent/test_phase_b_wiring.py tests/meta_harness/test_scenario_runner.py`
- `cd python-backend && UV_LINK_MODE=copy uv run --frozen pytest tests/test_memory_provider.py tests/agent/test_phase_b_wiring.py tests/meta_harness/test_scenario_runner.py tests/agent/middleware/test_compaction_compression.py -q`

Evidence:

- Ruff passed.
- Pytest: `66 passed in 99.58s`.
- Verified `pre_save` archives through `MemoryManager.on_pre_compress` without
  mutating messages.
- Verified `compaction` archives before tool-result truncation.
- Verified `FusionProvider.sync_turn` writes through `retain_batch_async`.
- Verified `FusionProvider.on_pre_compress` archives raw visible messages.
- Verified Meta-Harness can assert memory route/provider metadata.

## MV-00b Runner Variant Unit Verify

Status: pass on 2026-04-26.

Scope: Meta-Harness runner selection plus graphless SimpleLoop regression fix.

Commands:

- `cd python-backend && uv run --frozen ruff check agent/runners/simple.py tests/agent/runners/test_simple.py meta_harness/scenario_runner.py meta_harness/evaluator.py meta_harness/meta_cli.py tests/meta_harness/test_scenario_runner.py`
- `cd python-backend && UV_LINK_MODE=copy uv run --frozen pytest tests/meta_harness/test_scenario_runner.py tests/agent/runners/test_simple.py tests/agent/runners/test_dispatcher.py -q`

Evidence:

- Ruff passed.
- Pytest: `38 passed in 5.68s`.
- Meta-Harness now supports explicit in-process `dispatcher`, `langgraph` and
  `simple` variants; live service mode remains app-dispatcher based.
- Legacy evaluator/search-set runs use the same runner-variant plumbing instead
  of importing LangGraph directly.
- Source snapshots include `agent/runners/dispatcher.py`,
  `agent/runners/simple.py` and `agent/graph/runner.py`.
- Real SimpleLoop Meta-Harness run exposed a crash where tool calls arrived as
  dictionaries but `_append_tool_messages` expected object attributes.
- Fix verified: `_append_tool_messages` accepts ToolCall objects and dict
  payloads.
- Fix verified: OpenAI-style `function.arguments` strings are preserved instead
  of being double-encoded.
- Trace gates now fail by default on observed failed `tool_result` events;
  failure-tolerant scenarios must opt into `allow_tool_failures`.

## MV-01 Python-Only Stack Smoke

Status: pass on 2026-04-26.

Prerequisites:

- PostgreSQL running.
- LiteLLM Gateway running.
- Python Agent imports or service starts.

Probe:

- run one simple scenario with no frontend and no Go.
- confirm audit events and session rows exist.

Expected evidence:

- run id.
- thread id.
- trace artifact path.
- score/verdict JSON.

Evidence:

- Dev stack used: Postgres `:5433`, LiteLLM `:4000`, Python Agent `:8094`.
- Command:
  `cd python-backend && APP_ENV=development uv run --frozen python -m meta_harness.meta_cli run ../data/harness/search_set/queries.json --max-scenarios 1 --agent-url http://127.0.0.1:8094 --user-id anonymous --model openrouter/openrouter/auto`
- Latest pass run id: `run-cb0a1d988fe3`.
- Latest pass thread id: `mh-q001-35773a17`.
- Latest pass artifact dir:
  `data/meta_harness/runs/run-cb0a1d988fe3/candidates/baseline/`.
- Latest pass trace artifact:
  `data/meta_harness/runs/run-cb0a1d988fe3/candidates/baseline/traces/q001/mh-q001-35773a17.json`.
- Latest pass result: trace gate pass rate `1.0`; observed actions include
  `skill_found`, `skill_used`, `memory_recall` and `llm_response`.
- Latest pass score: `completed=true`, `completion_source=sse_finish`,
  `fitness_score=1.0`.
- Latest pass observed skills include `market-research`, `memory-usage`, `plan`
  and `risk-assessment`.
- Candidate decision: `keep`, recorded in
  `data/meta_harness/runs/run-cb0a1d988fe3/candidates/baseline/decision.json`.

Earlier failure/root cause:

- Run id: `run-7e71055b00bb`.
- Thread id: `mh-q001-1bdd7239`.
- Artifact dir:
  `data/meta_harness/runs/run-7e71055b00bb/candidates/baseline/`.
- Trace artifact:
  `data/meta_harness/runs/run-7e71055b00bb/candidates/baseline/traces/q001/mh-q001-1bdd7239.json`.
- Result: agent completed through LiteLLM/OpenRouter and audit captured
  `memory_recall`, `llm_response` and `memory_retain`.
- Gate result: failed because expected skill `market-research` was not observed
  in thread-scoped audit events.
- Root cause: prompt setup could hit its global timeout while cold-loading dense
  skill retrieval and legacy memory init, discarding skill injection/audit from
  the live trace.
- Fix: small skill corpora now use BM25 by default instead of cold-loading dense
  ranking, skill audit receives `thread_id`/`session_id`, and prompt memory
  init/recall has separate timeout budgets.
- Candidate decision: `defer`, recorded in
  `data/meta_harness/runs/run-7e71055b00bb/candidates/baseline/decision.json`.

## MV-02 Tool Scenario Smoke

Status: partial pass on 2026-04-26.

Prerequisites:

- Python Agent can load ToolRegistry.
- scenario uses a non-destructive tool such as `get_chart_state`,
  `get_portfolio_summary`, `memory_search` or `load_memory`.

Probe:

- run one scenario that should call a specific tool.
- assert `tool_call` and `tool_result` audit events.

## MV-03 Memory Lifecycle Meta-Harness Smoke

Status: pass/kept on 2026-04-27.

Scope: in-process `simple` runner, LiteLLM/OpenRouter, Memory-Fusion route,
explicit memory tools, no frontend and no Go.

Command:

- `cd python-backend && .venv/bin/python -m meta_harness.meta_cli run ../data/harness/memory_lifecycle/scenarios.json --candidate-id post-kg-context-memory-smoke --runner-variant simple --model openrouter/openrouter/free`

Evidence:

- Run id: `run-eeb4e11fab0f`.
- Artifact dir:
  `data/meta_harness/runs/run-eeb4e11fab0f/candidates/post-kg-context-memory-smoke/`.
- Trace gate pass rate: `1.0`.
- Completion rate: `1.0`.
- Fitness score: `0.8476`.
- Tool success rate: `1.0`.
- Memory utilization rate: `1.0`.
- Observed memory route/provider metadata includes `fusion`, `verbatim` and
  `summary_async`.
- Candidate decision: `defer`; it is Pareto-dominated and exposed a concrete
  hardening target: repeated `memory_add` calls with the same normalized content
  in one explicit-memory turn. This becomes T097a.
- Follow-up candidate after implementing explicit `memory_add` dedup:
  `run-22d2dfd38755`, candidate `memory-add-dedupe-smoke`.
- Follow-up result: trace gate pass rate `1.0`, completion rate `1.0`,
  fitness score `0.8583`, tool success rate `1.0`, memory utilization rate
  `1.0`.
- Improvement over `run-eeb4e11fab0f`: total tokens reduced from `60506` to
  `36959`; average duration reduced from `74463ms` to `22902ms`; each memory
  lifecycle scenario emitted one `memory_add` tool call.
- Candidate decision: `keep`; globally Pareto-dominated by unrelated tiny/no-
  tool scenarios, but kept because it fixes a scenario-specific duplicate-write
  regression and preserves all trace gates.
- Static follow-up: `evaluate_trace_gates` now emits a deterministic warning
  when multiple `memory_add` tool calls in a scenario use the same normalized
  `content`/`fact_type`. Covered by
  `tests/meta_harness/test_scenario_runner.py`.

Expected evidence:

- required tool gate pass.
- no forbidden tool gate violation.

Evidence:

- Command:
  `cd python-backend && APP_ENV=development uv run --frozen python -m meta_harness.meta_cli run ../data/harness/live_probe/scenarios.json --agent-url http://127.0.0.1:8094 --user-id anonymous --candidate-id baseline --model openrouter/openrouter/auto`
- Run id: `run-8ba52ec0f56e`.
- Artifact dir:
  `data/meta_harness/runs/run-8ba52ec0f56e/candidates/baseline/`.
- Aggregate: `trace_gate_pass_rate=0.75`, `completion_rate=1.0`,
  `fitness_score=0.8125`.
- Passed tool scenarios:
  - `lp-chart-001`: observed `get_chart_state` `tool_call` and successful
    `tool_result`.
  - `lp-portfolio-001`: observed `get_portfolio_summary` `tool_call` and
    successful `tool_result`.
- Failed tool scenario:
  - `lp-sandbox-001`: consent pregrant worked and `sandbox_execute` was called,
    but `tool_result.success=false`.
- Candidate decision: `defer`, recorded in
  `data/meta_harness/runs/run-8ba52ec0f56e/candidates/baseline/decision.json`.

## MV-03 Memory Scenario Smoke

Status: pass on 2026-04-26.

Prerequisites:

- memory provider configured.
- eval user has seeded memory or scenario creates it in an earlier turn.

Probe:

- run a remember/recall/correction scenario.
- assert memory retain and recall behavior.

Expected evidence:

- memory gate pass.
- provider/route metadata where available.
- final answer references correct memory without invention.

Evidence:

- Run id: `run-8ba52ec0f56e`.
- Scenario `lp-memory-001` passed with observed `memory_add` and
  `memory_search` tool calls/results plus `memory_recall` and `memory_retain`
  audit actions.
- Observed skills include `global:memory-usage`, `global:plan`,
  `global:risk-assessment` and `global:trading-analysis`.

## MV-03b Sandbox Infra Gate

Status: blocked on local SSD/container state on 2026-04-26.

Evidence:

- OpenSandbox service `opensandbox-api-gateway` on `:8080` started and `/health`
  returned `{"status":"healthy"}`.
- The alternate `opensandbox` service on `:8100` attempted Kubernetes mode and
  failed without kubeconfig; local service runs should use
  `OPENSANDBOX_SERVER_URL=http://127.0.0.1:8080`.
- The installed SDK package exposes `code_interpreter`; sandbox manager now
  falls back from `opensandbox_code_interpreter` to `code_interpreter`.
- Pulling `opensandbox/code-interpreter:v1.0.2` failed because `/` had about
  4 GB free and Podman reported `no space left on device`.
- Until Podman storage is freed/moved or the image is prebuilt, sandbox live
  verify remains deferred.

## MV-03c Runner-Parity Live Attempt

Status: blocked on local Postgres/Podman port stability on 2026-04-26.

Evidence:

- Matrix Postgres container was restarted and reached `healthy`, and direct
  `psql` through `127.0.0.1:5433` briefly succeeded.
- Alembic migration succeeded after loading `.env` and `.env.development`
  through `python-dotenv`.
- In-process SimpleLoop search-set run with
  `--runner-variant simple --candidate-id simple-smoke` produced artifact
  `data/meta_harness/runs/run-eb176d5af9b2/candidates/simple-smoke`.
- That run reached `completion_rate=1.0`, `runner_variant=simple` and surfaced
  the SimpleLoop dict tool-call bug fixed in MV-00b.
- The same run showed why trace gates needed stricter tool-failure handling:
  `tool_success_rate=0.0` but the previous trace gate still passed.
- Minimal no-tool runner-parity scenario was added at
  `data/harness/runner_parity/scenarios.json`.
- A follow-up no-tool SimpleLoop run hit repeated `AUDIT_DB_URL` connection
  refused errors because the rootless Podman Postgres port disappeared and the
  `postgres` container later exited cleanly. Live runner-parity comparison is
  therefore deferred until local DB port stability is fixed.

## MV-03d Runner-Parity Live Pass After Schema Governance

Status: pass on 2026-04-27.

Meta-Harness role/use:

- Codex acted as proposer/operator and simulated user.
- The first post-Feature-018 runner-parity run failed because the in-process
  agent could not reach the configured LiteLLM endpoint.
- DevStack investigation found that the LiteLLM container inherited a host DSN
  (`localhost:5433`) for Postgres. Inside the container this points to itself,
  so `docker-compose.yml` now overrides `HINDSIGHT_DB_URL` to
  `postgres:5432`.
- Recreated LiteLLM with `COMPOSE_PROFILES=litellm podman-compose up -d
  litellm` and reran the Meta-Harness scenario through LiteLLM/OpenRouter.

Evidence:

- Run id: `run-5f24325e7b1c`.
- Candidate: `post-schema-governance`.
- Artifact dir:
  `data/meta_harness/runs/run-5f24325e7b1c/candidates/post-schema-governance/`.
- Scenario: `rp-no-tools-001`.
- Runner: `simple`.
- Model/provider: `openrouter/openrouter/free` via LiteLLM/OpenRouter.
- Result: `trace_gate_pass_rate=1.0`, `completion_rate=1.0`,
  `fitness_score=1.0`.
- Observed actions: `skill_found`, `llm_response`; no tools and no required
  memory.
- Response: `Runner parity smoke.`

## MV-04 Candidate Artifact Smoke

Status: pass on 2026-04-26 for `run-7e71055b00bb`.

Probe:

- run baseline candidate over a tiny search set.
- write candidate artifact directory.

Expected evidence:

- `config.json`.
- `scores.json`.
- `verdicts.json`.
- raw trace JSON.
- SSE JSONL.

Evidence:

- `config.json`, `source_snapshot.json`, `scores.json`, `verdicts.json`,
  `result.json`, raw trace JSON, SSE JSONL and `decision.json` exist under
  `data/meta_harness/runs/run-7e71055b00bb/candidates/baseline/`.

## MV-05 Proposer Loop Smoke

Probe:

- run one propose iteration over baseline artifacts.
- evaluate candidate on one or two scenarios.

Expected evidence:

- proposal JSON.
- candidate score.
- keep/discard verdict.
- rejection reason if candidate fails gates.

## MV-05a Memory Lifecycle Outer-Loop Probe

Status: pass after several failed candidates and corrective patches on
2026-04-26.

Meta-Harness role/use:

- Codex acted as proposer and user: it sent the scenario instructions to the
  real in-process SimpleLoop agent, forced `memory_add` and `memory_search`,
  inspected raw trace artifacts, then patched the agent/tool path.
- Failed candidate `memory-fusion-mempalace-fast-add-384` first showed a true
  runtime issue: `memory_add` could timeout or retry because synchronous
  summary retain exceeded the 30s tool budget.
- Corrective candidate `memory-fusion-facttype-normalized-full-384` passed both
  memory lifecycle scenarios in run `run-6e38bdc3fc39`.

Evidence from passing run:

- `trace_gate_pass_rate=1.0`, `completion_rate=1.0`, `fitness_score=0.8583`.
- Observed tools: `memory_add`, `memory_search`.
- Observed memory actions: `memory_retain`, `memory_recall`.
- Observed providers include `fusion`, `verbatim`, `summary_async`.
- No tool failures; tool success rate `1.0`.
- `memory_add` tool result duration was under the 30s tool timeout in both
  scenarios; warm path was about 1s, cold path was still about 17s.

Additional hardening from the same loop:

- `AGENT_MAX_OUTPUT_TOKENS=4096` prevents provider-default oversized completion
  requests; earlier OpenRouter/LiteLLM run failed with a 402 budget error after
  asking for up to 65536 output tokens.
- Explicit `memory_add` now treats default/accidental world writes as personal
  experience memory, keeping global-world/KG writes out of agent memory.
- Explicit tool requests now have a system prompt compliance rule; `save_memory`
  is documented as scratchpad-only and `memory_add` as persistent Fusion memory.
- LLM-invented memory `fact_type` values are normalized before hitting
  Hindsight/Fusion, with the original value retained as metadata.

Follow-up Meta-Harness hardening on 2026-04-26:

- Runner-parity exposed that `enable_tools=false` did not reach `llm_node`;
  LangGraph still offered the full ToolRegistry and the model requested
  `sandbox_execute` on a no-tool prompt.
- Candidate `runner-parity-dispatcher-skill-stopwords`, run
  `run-f12771a188cb`, passed with `trace_gate_pass_rate=1.0`,
  `completion_rate=1.0`, no observed tools, no observed skills and
  `totalTokens=215`.
- Before the skill-gating fix, the same no-tool prompt loaded
  `memory-usage`, `plan`, `market-research` and `trading-analysis` and used
  about 2.1k prompt tokens. After Stopword/query gating it loaded no skills.
- Candidate `memory-lifecycle-memory-timeout-90`, run `run-33660bc2c88e`,
  passed both memory lifecycle scenarios with `trace_gate_pass_rate=1.0`,
  `completion_rate=1.0`, `fitness_score=0.8583` after giving memory tools a
  dedicated 90s timeout budget.
- Timeout candidates now fail trace gates explicitly with `harness timeout`
  and stop further turns in that scenario.
- Pareto summary after these runs had 36 total candidates and kept
  `run-f12771a188cb:runner-parity-dispatcher-skill-stopwords` on the frontier
  because it dominated previous runner-parity candidates on token and latency
  efficiency.

## MV-05b Tool Live-Probe Outer-Loop Follow-Up

Status: partial pass with actionable infra/performance follow-ups on
2026-04-26.

Meta-Harness role/use:

- Codex acted as proposer and simulated user against the real in-process
  Dispatcher/LangGraph path.
- The first chart probe failed before tool execution because named user
  `meta-harness` had no DB credential row. Fix: in-process Meta-Harness now has
  a provider-neutral ENV credential fallback for simulated users; live service
  paths remain fail-closed through normal user credentials.
- The next chart probe reached `get_chart_state` and final LLM response but
  timed out before SSE finish because post-answer `memory_retain_node` blocked
  the graph. Fix: `MEMORY_RETAIN_TIMEOUT_SEC` now bounds retain and audit-logs
  timeout failures instead of blocking the user turn.
- Dispatcher probe then exposed provider reasoning markers leaking into
  assistant text (`analysis...assistantfinal`). Fix: `llm_node` strips these
  provider artifacts before SSE, audit and memory sync.
- Chart+Portfolio set exposed that later scenarios could lose their default
  model and fall to `provider=litellm`. Fix: `run_scenario_file` pins the
  effective model once per candidate run.

Passing evidence:

- `run-36646baea380`, candidate `live-probe-chart-clean-output`: chart probe
  passed with `trace_gate_pass_rate=1.0`, `completion_rate=1.0`,
  `fitness_score=0.9`, observed `get_chart_state`, clean assistant text and
  SSE `finish`.
- `run-8608162b9557`, candidate `live-probe-chart-portfolio-pinned-model`:
  chart + portfolio probes passed with aggregate `trace_gate_pass_rate=1.0`,
  `completion_rate=1.0`, `fitness_score=0.9`; observed tools
  `get_chart_state` and `get_portfolio_summary`.
- `run-594f7f420f5c`, candidate `live-probe-memory-isolated`: explicit memory
  probe passed with `memory_add` and `memory_search`, tool success `1.0`,
  observed providers `fusion`, `verbatim`, `summary_async`.

Known follow-ups:

- `lp-sandbox-001`, run `run-502b65a06880`, selected `sandbox_execute` and
  passed consent/skill selection, but tool success was `0.0` because the
  OpenSandbox endpoint was unreachable (`ConnectError`). This is an infra gate,
  not an agent tool-selection regression.
- `lp-memory-001` still over-selects skills: `memory-usage` is correct, but
  `market-research`, `risk-assessment` and `plan` also loaded. Keep as a
  skill-precision Pareto candidate.
- Post-answer memory retain currently times out at 20s in these live probes.
  That preserves UX, but retain latency/coherence reliability still needs a
  separate Memory-Fusion performance candidate.

## MV-05c Memory-Fusion Retain Outer-Loop Follow-Up

Status: pass on 2026-04-26 with historical dev-memory cleanup follow-up.

Meta-Harness role/use:

- Codex acted as proposer and simulated user against the real in-process
  LangGraph path after a reboot where no stack was running.
- Stack bootstrap used Postgres `:5433`, FalkorDB `:6380`, Python Agent
  `:8094`, and LiteLLM `:4000`; frontend and Go were not required.
- The first candidate targeted controlled startup and memory correctness after
  discovering that `.env.development` overwrote shell overrides.

Evidence:

- `shared.app_factory` and `bridge.config` now merge `.env` and
  `.env.<APP_ENV>` while preserving process env overrides.
- Direct memory tool probe stored and recalled a MemPalace/Postgres/pgvector
  phrase through `memory_add` and `memory_search`.
- Direct `memory_recall_node` probe injected `## Relevant Context` with a
  Personal Raw Evidence block.
- Candidate `memory-fusion-env-override-live`, run `run-408242ed1c2c`, passed
  both memory lifecycle scenarios with `trace_gate_pass_rate=1.0`,
  `completion_rate=1.0`, `fitness_score=0.8583`, and exposed automatic retain
  timeouts.
- Corrective candidate `memory-fusion-verbatim-first-retain`, run
  `run-a1cc52e7217f`, passed both scenarios with `trace_gate_pass_rate=1.0`,
  `completion_rate=1.0`, `fitness_score=0.8583`, no retain-timeout messages,
  and trace events showing automatic retain route `verbatim`, provider
  `fusion`, providers `verbatim,summary_async`, and
  `summary_status=background_queued`.
- Candidate `memory-fusion-clean-tool-markup`, run `run-a25abb61e18f`, fixed
  new assistant output leaking textual `<tool_call>` blocks, but exposed an
  OpenAI/OpenRouter message-shape bug after `memory_search`:
  `messages[5]: missing field tool_call_id`.
- Corrective candidate `memory-fusion-openai-tool-message-id`, run
  `run-f1078e290e9f`, passed both memory lifecycle scenarios with
  `trace_gate_pass_rate=1.0`, `completion_rate=1.0` and
  `fitness_score=0.875`. Trace showed `memory_search` succeeded and the
  follow-up LLM response completed without provider 400.
- Focused tests after the patch:
  `29 passed in 6.40s`.
- Ruff on touched Python files: pass.

Follow-up:

- Old dev-memory rows from earlier failing runs can still retrieve historical
  `<tool_call>` content as evidence. This is a cleanup/reset question for dev
  data, not a new-turn output regression.

## MV-05d Post-Push Memory-Fusion Dotenv Guard

Status: pass on 2026-04-27.

Meta-Harness role/use:

- Codex acted as proposer and simulated user against the real in-process
  SimpleLoop path after committing/pushing the prior feature batch.
- Probe first ran a no-tool runner-parity scenario, then an explicit
  `memory_add`/`memory_search` memory lifecycle scenario.
- Failed memory candidates exposed an upstream integration issue: importing
  `hindsight_api.config` calls `load_dotenv(..., override=True)`, which can
  overwrite process-provided DB URLs with stale `.env` credentials during
  Harness/dev-stack runs.

Evidence:

- Runner-parity run `run-96e8e1d01cfa`, candidate `post-push-simple-free`,
  passed with `trace_gate_pass_rate=1.0`, `completion_rate=1.0`, no tool calls
  and model `openrouter/openrouter/free`.
- Failing memory runs `run-c174d5e71b23`, `run-cbe1be3f2a71` and
  `run-1e3bd30b235e` all selected the correct tools (`memory_add`,
  `memory_search`) but returned
  `Memory not available`; trace gates failed for missing `memory_retain` and
  missing route `fusion`.
- Root cause: Hindsight's dotenv import could override
  `HINDSIGHT_DB_URL`/`HINDSIGHT_API_DATABASE_URL` after Meta-Harness had already
  set clean process env vars.
- Fix: `create_hindsight_engine` re-applies explicit Hindsight runtime
  overrides after importing Hindsight modules.
- Fix: Fusion memory DB selection now prefers `MEMPALACE_DB_URL` as the shared
  Postgres override before `HINDSIGHT_DB_URL`, so MemPalace/Postgres live
  probes remain stable even if Hindsight import side effects touch
  `HINDSIGHT_DB_URL`.
- Harness command now sets `PYTHON_DOTENV_DISABLED=true` for Hindsight-backed
  live probes so upstream dotenv loading cannot override the controlled
  process environment.
- Passing memory run `run-8d52c444d94a`, candidate
  `post-patch-memory-dotenv-disabled`, passed with `trace_gate_pass_rate=1.0`,
  `completion_rate=1.0`, observed tools `memory_add` and `memory_search`,
  observed actions `memory_retain` and `memory_recall`, route `fusion`, and
  providers `fusion`, `verbatim`, `summary_async`.
- The exact phrase
  `memory_lifecycle_probe_prefers_verbatim_evidence_before_compaction` was
  stored and recalled through Fusion/MemPalace/Postgres/pgvector.
- Focused checks after the patch:
  `pytest tests/memory_fusion/test_mempalace_postgres_engine.py tests/test_retrieval_baseline.py -q`
  => `13 passed, 1 skipped`.
- Ruff:
  `ruff check memory_fusion/providers.py memory_fusion/engine.py` => pass.

## MV-06 MCP Exposure Smoke

Prerequisites:

- Python Agent service mounted `/mcp-traces` or standalone trace MCP.

Probe:

- call trace/history/evaluate/propose tools after a run.

Expected evidence:

- MCP tool response includes the run/candidate id.
- no frontend or Go dependency.

## MV-07 Global KG Boundary Gates

Status: static pass on 2026-04-27; live run pending real KG/runtime exposure.

Meta-Harness role/use:

- Codex acted as proposer and added deterministic trace-gate support for
  forbidden memory routes/providers.
- New scenario set:
  `data/harness/global_kg_boundaries/scenarios.json`.

Evidence:

- Personal-memory scenario requires `memory_search` and forbids
  `global_kg` route plus `nonicdb`/`nornicdb` providers.
- World/domain scenario forbids `memory_add`/`memory_search` so global KG or
  hybrid RAG work cannot be silently substituted by personal memory.
- Private-note scenario requires `memory_add` and forbids KG proposal/promotion
  actions.
- Static tests verify the new forbidden route/provider gates and scenario
  fixture load.
