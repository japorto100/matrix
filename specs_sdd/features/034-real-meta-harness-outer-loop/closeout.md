---
title: Real Meta-Harness Outer Loop Closeout
status: open
owner: filip
created: 2026-05-01
updated: 2026-05-01
feature_id: 034
---

# Closeout

Open for holdout and arbitrary code-patch enforcement. The first real
no-browser outer-loop iteration is complete and has evidence for baseline
evaluation, proposer artifact inspection, bounded candidate creation, frozen
evaluation, decision logging and Pareto update.

## 2026-05-01 Static Implementation Evidence

- `python-backend/meta_harness/real_outer_loop.py` implements the first real
  no-browser outer loop:
  baseline -> experience packet -> deterministic proposer artifact inspection
  -> config-overlay candidate -> pending eval -> frozen scenario evaluation ->
  keep/discard/defer decision -> final experience packet.
- CLI: `python -m meta_harness.meta_cli outer-loop`.
- Candidate artifacts include `proposal.json`, `config_overlay.json`,
  `proposer_interaction.json`, `pending_eval.json`, `patch.diff`,
  `decision.json`, scores/verdicts/source snapshot and raw traces from the
  scenario runner.
- Summary artifact: `real_outer_loop_summary.json` with
  `true_meta_harness_iteration`.
- Remaining closeout blockers: add explicit Feature 034 holdout command/evidence
  and add full git-diff scope enforcement for arbitrary code-patch candidates.

## 2026-05-01 First Real No-Browser Loop Evidence

- Provider/model selection:
  `openrouter/nvidia/nemotron-3-super-120b-a12b:free` exists but returned 429
  during the local check; `openrouter/free` worked directly against OpenRouter
  but failed through the local LiteLLM gateway with a free-tier/credits error.
  The explicit LiteLLM route `openrouter/openai/gpt-oss-20b:free` passed the
  provider smoke and was used for Round 1.
- Infrastructure fix: `hindsight_api` import was overriding
  `HINDSIGHT_DB_URL` back to the repo `.env.development` value on `:5433`.
  `memory_fusion.providers.create_hindsight_engine` now restores the explicit
  runtime DB env after the import so Meta-Harness rounds can point at the
  isolated Memory-Eval Postgres on `:55433`.
- Verification before rerun:
  `uv run pytest tests/memory_fusion/test_providers_env.py -q` passed and the
  import sanity check preserved `HINDSIGHT_DB_URL=...:55433`.
- Sanity candidate:
  `run-metaharness-round-1-db-sanity-fixed` passed with
  `trace_gate_pass_rate=1.0`, `stream_gate_pass_rate=1.0`, tool success
  `1.0`, memory route `fusion`, providers `fusion/summary_async/verbatim`,
  tools `memory_add` and `memory_search`, and real prompt-cache telemetry.
- True outer-loop:
  `run-metaharness-round-1-fixed` completed baseline -> proposer inspection ->
  config-overlay candidate -> frozen evaluation -> decision.
  Baseline: `trace_gate_pass_rate=1.0`, fitness `0.8424`.
  Candidate: `paper_ready=true`, `trace_event_count=22`,
  `trace_gate_pass_rate=1.0`, fitness `0.8423`.
  Decision: `discard`, because the candidate was dominated by baseline under
  the frozen search evaluator.

## 2026-05-01 Bounded Runtime Candidate Evidence

- Candidate: recent explicit memory write fallback for immediate
  `memory_add` -> `memory_search` recall in
  `python-backend/agent/tools/memory_hindsight.py`.
- Rationale: durable Memory-Fusion write can succeed while same-turn search
  still misses due indexing/summary lag. The fallback is scoped to the existing
  dedupe window, same thread, same bank and matching fact type.
- Verification:
  `uv run pytest tests/agent/tools/test_memory_hindsight.py -q` passed.
  `run-metaharness-round-2-recent-memory-fixed` passed trace and stream gates;
  the transcript answered with the exact probe phrase. Holdout is still open,
  so this is a kept search-set improvement, not full promotion evidence.

## 2026-05-01 Runtime Preflight Evidence

- `python-backend/meta_harness/runtime_preflight.py` now verifies
  `AUDIT_DB_URL/HINDSIGHT_DB_URL` before live no-browser Meta-Harness commands.
- It auto-starts only the isolated local Memory-Eval Postgres target
  `matrix-memory-eval-postgres` on `localhost/127.0.0.1:55433`.
- Unknown unreachable DB targets fail-fast, which prevents a wrong `:5433`
  service from masquerading as candidate failure.
- Verification:
  `uv run ruff check meta_harness/runtime_preflight.py meta_harness/meta_cli.py meta_harness/real_outer_loop.py tests/meta_harness/test_runtime_preflight.py tests/meta_harness/test_real_outer_loop.py`
  and
  `uv run pytest tests/meta_harness/test_runtime_preflight.py tests/meta_harness/test_real_outer_loop.py -q`
  passed.

## 2026-05-01 Local-8B Floor And Scoring Evidence

- Local provider path: `llama-server` can serve Bonsai 8B through
  `http://127.0.0.1:8081/v1` as `bonsai-8b`; provider smoke passed against
  that OpenAI-compatible endpoint and now reports provider `llamacpp`.
- Harness suite: `data/harness/local_8b_floor/scenarios.json` defines the
  backend no-browser floor for direct routing, skills, memory, chart tool/SSE,
  retrieval/KG boundary, semantic lookup and subagent policy.
- Live floor evidence:
  `run-local8b-floor-bonsai-direct-long-timeout` passed the direct no-tool
  Bonsai floor with `trace_gate_pass_rate=1.0`, `stream_gate_pass_rate=1.0`
  and `completion_rate=1.0`. The run used the full backend harness, not a
  shortened fake prompt; CPU latency was about 110s for 1131 prompt tokens.
- Scoring fix: scenario fitness now records the raw base fitness and applies
  deterministic gate penalties for trace/stream failures.
- Verification:
  `uv run ruff check meta_harness/scenario_runner.py tests/meta_harness/test_scenario_runner.py`
  and
  `uv run pytest tests/meta_harness/test_scenario_runner.py -q`
  passed.

## 2026-05-01 Formal Local-8B Meta-Harness Round

- Run: `run-metaharness-round-local8b-001`.
- Contract: `real-meta-harness-outer-loop/v1`.
- Result: `true_meta_harness_iteration=true`.
- Baseline: `completion_rate=1.0`, `trace_gate_pass_rate=1.0`,
  `stream_gate_pass_rate=1.0`, `fitness_score=0.9995`.
- Candidate: `iter-001-config-overlay`, `completion_rate=1.0`,
  `trace_gate_pass_rate=1.0`, `stream_gate_pass_rate=1.0`,
  `fitness_score=0.9994`.
- Decision: `discard`, because the candidate regressed versus baseline under
  the frozen search evaluator.
- Proposer evidence: 24 raw source/score/verdict/trace files inspected; holdout
  hidden; frozen evaluator gate passed.
- Practical finding: the direct Local-8B Agent Harness turn used 1212 baseline
  prompt tokens and took about 270s on CPU. Full-suite Local-8B rounds should
  be split into small slices unless hardware changes.

## 2026-05-01 Targeted Skill Floor Hardening

- Added repeatable `--scenario-id` selection to `meta_harness run` and
  `scenario_ids` to MCP `harness_run_scenarios`, so expensive Local-8B floors
  can be run one slice at a time.
- Ran `local8b-skill-risk-001` through the real backend with Bonsai 8B.
- Finding 1: shared `anonymous` harness user state caused unrelated memory
  recall from previous Direct-Route runs.
- Finding 2: isolated synthetic users exposed a local-provider credential
  resolver gap for `llamacpp`.
- Fix: Meta-Harness env credentials now include local OpenAI-compatible
  providers via provider-specific `META_HARNESS_*_API_KEY` vars or
  `LITELLM_API_KEY`.
- Verification: `run-local8b-floor-skill-risk-001-isolated-fixed` passed
  trace/stream/completion gates at `1.0` with fitness `0.9992`.
