---
title: Real Meta-Harness Outer Loop Live Verify
status: planned
owner: filip
created: 2026-05-01
updated: 2026-05-01
feature_id: 034
---

# Live Verify

Browser live verification is intentionally not the first gate. The first live
path is backend/no-browser so the loop can run for hours without UI flakiness.

- LV001 Start the Python backend stack and run a baseline search-set scenario
  that writes candidate artifacts.
- LV002 Run one full outer-loop iteration and verify the summary says
  `true_meta_harness_iteration=true`.
  - Command:
    `cd python-backend && APP_ENV=development uv run python -m meta_harness.meta_cli outer-loop --run-id run-real-meta-harness-memory-$(date +%Y%m%d%H%M%S) --scenario-path ../data/harness/memory_lifecycle/scenarios.json --max-scenarios 1 --iterations 1 --runner-variant simple --user-id anonymous`
- LV003 Verify the proposer interaction log lists raw files inspected:
  source snapshot, score file, verdict file and trace file.
- LV004 Verify a candidate decision is logged as keep, discard or defer with
  metric evidence.
- LV005 Verify Pareto summary changes or explicitly records no improvement.
- LV006 Run protected holdout only after promotion preflight passes.
- LV007 Later browser pass: open Control/Ops and verify the Meta-Harness run,
  candidates, verdicts and traces replay without requiring raw provider logs.
