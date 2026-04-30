---
title: Real Meta-Harness Outer Loop Closeout
status: open
owner: filip
created: 2026-05-01
updated: 2026-05-01
feature_id: 034
---

# Closeout

Open. Close only after at least one real no-browser outer-loop iteration has
evidence for baseline evaluation, proposer artifact inspection, bounded
candidate creation, frozen evaluation, decision logging and Pareto update.

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
- Remaining closeout blockers: run the command against the local real backend
  model/provider path, add explicit Feature 034 holdout command/evidence and
  add full git-diff scope enforcement for arbitrary code-patch candidates.
