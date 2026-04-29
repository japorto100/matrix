---
title: Observability Harness Evidence
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
---

# Evidence

## Static Harness Mode Analysis Input

Source files:

- `docs/superpowers/findings/2026-04-23-harness-mode-analysis.md`
- `docs/superpowers/findings/2026-04-23-harness-mode-analysis.csv`

CSV fingerprint:

- lines: 1
- sha256:
  `32c5b4e03e9b5ad927547805ac11483419d3313cbe58e591b2353e18dd623337`

Interpretation:

The CSV only contains the header row:

`thread_id,user_id,mode,llm_turns,has_tool_calls,max_iteration,total_tokens,avg_response_chars,total_duration_ms,model_used`

The paired Markdown report says no threads with audit events were found. This
is valid evidence of the historical run state, but it is not positive live
evidence for scoring quality. Feature 014 therefore keeps live audit/eval
persistence gates open.

## Eval-ID Semantics

Feature 011 and Feature 014 share the same accepted scorer behavior:
`harness_eval_id` is first-write-wins via SQL `COALESCE`. Rescoring with a new
eval id does not overwrite an existing grouping id unless a future explicit
overwrite mode is implemented.

Current static tests:

- `python-backend/tests/meta_harness/test_scorer.py`
- `python-backend/tests/agent/runners/test_mark_routing.py`
- `python-backend/tests/agent/llm/test_smart_routing.py`
