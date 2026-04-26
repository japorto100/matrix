---
title: Meta-Harness Agent Optimization Gates
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 016
---

# Gate Ledger

## Stack Gates

- PostgreSQL is reachable and migrations needed by agent audit/session/component
  paths are applied.
- LiteLLM Gateway responds to a smoke completion for Base Agent runs when a
  live LLM scenario is requested.
- External proposer/judge LLM usage is disabled by default and requires an
  explicit run opt-in.
- Python Agent service starts or in-process runner imports cleanly.
- Memory provider mode is explicit: `disabled`, `hindsight`, `mempalace` or
  `fusion`.
- Sandbox-dependent scenarios are skipped with evidence when sandbox is not
  available.

## Local Commands

- In-process scenario run:
  `cd python-backend && uv run --frozen python -m meta_harness.meta_cli run ../data/harness/search_set/queries.json --max-scenarios 1`
- In-process SimpleLoop scenario run:
  `cd python-backend && uv run --frozen python -m meta_harness.meta_cli run ../data/harness/search_set/queries.json --max-scenarios 1 --runner-variant simple`
- In-process LangGraph scenario run:
  `cd python-backend && uv run --frozen python -m meta_harness.meta_cli run ../data/harness/search_set/queries.json --max-scenarios 1 --runner-variant langgraph`
- Runner-parity smoke without tools:
  `cd python-backend && APP_ENV=development uv run --frozen python -m meta_harness.meta_cli run ../data/harness/runner_parity/scenarios.json --runner-variant simple --user-id anonymous --model openrouter/openrouter/auto`
- Live-service scenario run:
  `cd python-backend && uv run --frozen python -m meta_harness.meta_cli run ../data/harness/search_set/queries.json --max-scenarios 1 --agent-url http://127.0.0.1:8094 --user-id anonymous --model openrouter/openrouter/auto`
- MCP surface:
  `harness_run_scenarios(path="../data/harness/search_set/queries.json", max_scenarios=1, agent_url="http://127.0.0.1:8094")`
- Protected holdout eval:
  `harness_evaluate(split="holdout", allow_holdout=true, max_queries=1)`
- External proposer opt-in:
  `cd python-backend && META_HARNESS_ENABLE_EXTERNAL_LLM=true uv run --frozen python -m meta_harness.proposer --enable-external-llm --iterations 1 --sessions 3`
- Candidate decision log:
  `harness_decide_candidate(run_id="...", candidate_id="...", decision="discard", rationale="...", metrics_json="{...}")`
- Live probe with real tools:
  `cd python-backend && APP_ENV=development uv run --frozen python -m meta_harness.meta_cli run ../data/harness/live_probe/scenarios.json --agent-url http://127.0.0.1:8094 --user-id anonymous --candidate-id baseline --model openrouter/openrouter/auto`
- Pareto frontier from run artifacts:

```bash
cd python-backend && APP_ENV=development uv run --frozen python - <<'PY'
from meta_harness.meta_cli import _load_env_files
_load_env_files()
from meta_harness.pareto import get_frontier_summary
import json
print(json.dumps(get_frontier_summary(), indent=2))
PY
```

- CLI Pareto summary:
  `cd python-backend && uv run --frozen python -m meta_harness.meta_cli pareto`
- CLI protected holdout guard:
  `cd python-backend && uv run --frozen python -m meta_harness.meta_cli evaluate --split holdout --max-queries 1`
- CLI proposer guard:
  `cd python-backend && uv run --frozen python -m meta_harness.meta_cli propose --sessions 2`

- Required env depends on runner mode: `AGENT_DEFAULT_MODEL` or request model,
  provider credentials/LiteLLM routing for LLM calls, and `HINDSIGHT_DB_URL` or
  audit-store fallback for persistent trace queries.
- Dev-stack note: if `agent.user_credentials` has no row for the eval user, use
  `--user-id anonymous` for local service runs so LiteLLM proxy routing can use
  its configured provider credentials.
- Security follow-up: the `anonymous` Meta-Harness/dev path must be audited
  before closeout. It may exist for local evaluation, but it must not bypass
  production CredentialPool, user-key, quota, audit or billing policy for named
  users.
- Provider note: this machine currently has OpenRouter credentials, not a direct
  Anthropic key. Use `--model openrouter/openrouter/auto` for live probe runs
  unless `agent.user_credentials` or ENV has a matching provider key.
- Sandbox note: local service mode should target
  `OPENSANDBOX_SERVER_URL=http://127.0.0.1:8080`; the `:8100` container defaults
  to Kubernetes mode and is not a valid local dev target on this machine.

## Scenario Gates

- Official Meta-Harness onboarding has been completed or every unresolved field
  is explicitly marked `unknown` with a proposed default.
- `data/meta_harness/domain_spec.md` defines candidate harness interface, fixed
  base model or model set, allowed change surface, out-of-scope changes,
  search/holdout split, metrics, budget, baselines and artifact/log layout.
- Search-set scenarios reflect Matrix product work: trading analysis,
  geopolitical/geomap reasoning, strategy review, research/source quality,
  memory use and tool-use safety.
- Holdout scenarios are hidden from proposer search feedback to reduce leakage.
- Multi-turn scenarios preserve thread identity.
- Search and holdout sets are separate.
- Scenario output stores raw SSE and trace artifacts.
- Scenario metadata includes run/candidate/scenario/thread/user ids.
- In-process scenarios can explicitly select `dispatcher`, `langgraph` or
  `simple`; service-mode scenarios document that they exercise the app
  dispatcher.
- Candidate artifacts include runner-variant metadata and source fingerprints
  for `agent/runners/dispatcher.py`, `agent/runners/simple.py` and
  `agent/graph/runner.py`.

## Tool Gates

- Evaluator uses real ToolRegistry unless a scenario opts out.
- Required tool gate can pass and fail deterministically.
- Forbidden tool gate can pass and fail deterministically.
- Observed `tool_result.success=false` fails trace gates by default; only
  scenarios that explicitly set `allow_tool_failures=true` may tolerate failed
  tool results.
- Consent gate records allow/deny/inform/confirm decisions where expected.
- Sandbox/file/browser scenarios never run without explicit local capability.
- Scheduler scenarios verify DB/tool behavior without requiring Matrix delivery
  in Phase 1.
- A2UI scenarios verify tool call and emitted payload, not frontend rendering.

## Memory Gates

- Automatic prefetch path is visible in traces or verdicts.
- Explicit memory tool use is visible when expected.
- Retain path is visible after remember/correction turns.
- Hindsight/MemPalace/Fusion route or provider is captured when available.
- `pre_save` context stage triggers a memory archive hook without changing the
  prompt messages.
- `compaction` context stage triggers a memory archive hook before mechanical
  tool-result truncation.
- `emergency`/compression still archives before LLM summarization and uses the
  same `user-<user_id>` bank shape as prefetch and turn sync.
- Fusion turn sync writes through `retain_batch_async`, not a non-existent
  legacy `retain` method.
- Fusion pre-compress archiving stores raw visible messages with stable source
  metadata before any context reduction.
- Hindsight diagnostic scenarios prove summarized preference/fact recall,
  update, correction and outcome learning without requiring MemPalace.
- MemPalace diagnostic scenarios prove verbatim/episodic recall, loci metadata,
  source/session refs and sanitized query behavior without requiring Hindsight.
- Orchestration/fusion scenarios prove the mixed path can combine Hindsight
  summary evidence with MemPalace verbatim evidence.
- Orchestration conflict scenarios must prefer fresh/source-backed verbatim
  evidence over stale summarized memory when the scenario explicitly corrects a
  fact.
- Memory conflict scenarios detect stale or contradictory recall behavior.
- Deterministic gates check expected recall terms, forbidden stale terms,
  evidence/source presence, route metadata and absence of unrelated mutation
  before any LLM judge can mark a scenario successful.
- Meta-Harness route/provider gates can assert `required_memory_routes` and
  `required_memory_providers` from audit metadata.
- Explicit `memory_add` and `memory_search` tool paths emit corresponding
  `memory_retain`/`memory_recall` audit events with route/provider metadata.
- Memory fixture manifests capture `user_id`, `bank_id`, `palace_path`,
  provider env and seed data for reproduction.
- Config snapshots expose Memory-Fusion Pareto hypotheses: embedding model/
  dimension, Hindsight reranker provider, Verbatim backend and bank id shape.
- Embedding and reranker sweeps are evaluated as candidate runs with
  reset/re-embedding and latency/cost evidence before promotion.

## Proposer Gates

- Proposer can inspect source/config snapshots.
- Proposer can inspect raw prior traces.
- Proposer can inspect scores and rejected-candidate reasons.
- Proposer does not see holdout scores during search.
- Candidate write scope is bounded and reviewable.
- Proposer may suggest developer-reviewed harness changes only; autonomous
  coding-agent behavior is not a product runtime feature in this phase.
- Candidate changes must be mechanism-level changes, not pure parameter sweeps,
  unless the domain spec explicitly marks a parameter as the hypothesis.
- Proposer interaction artifacts are logged even when Codex is the proposer
  instead of a wrapped API/Claude proposer.

## Promotion Gates

- Search score improves or candidate is Pareto-nondominated.
- Candidate is feasible before promotion: completion rate 1.0 and trace-gate
  pass rate 1.0, or an explicit human override explains why feasibility is
  being waived.
- Holdout does not regress beyond tolerance.
- Safety gates pass.
- Required tool and memory gates pass.
- Cost/latency regression is within budget or explicitly accepted.
- Raw memory utilization alone cannot make a candidate Pareto-better; memory
  quality must pass the relevant trace gates.
- Rejected candidates keep rationale for future proposer analysis.
