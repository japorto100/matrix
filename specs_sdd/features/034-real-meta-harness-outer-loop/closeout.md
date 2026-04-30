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
