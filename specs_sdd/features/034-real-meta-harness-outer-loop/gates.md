---
title: Real Meta-Harness Outer Loop Gates
status: planned
owner: filip
created: 2026-05-01
updated: 2026-05-01
feature_id: 034
---

# Gates

- [x] G001 A run must distinguish support lanes from real Meta-Harness iteration.
  Contract-suite-only runs cannot be reported as full Meta-Harness application.
- [x] G002 Every candidate has source/config snapshot, scores, verdicts and raw
  traces or typed benchmark evidence.
- [x] G003 Proposer packets exclude holdout results and holdout trace previews.
- [partial-static] G004 Evaluator, goldens and holdout files are immutable during one run.
- [x] G005 Candidate write scope is explicit before evaluation.
- [x] G006 Candidate notes cannot mark promotion; only frozen evaluator artifacts,
  safety gates and explicit holdout evidence can.
- [x] G007 Search-set score, trace-gate pass rate and cost/latency are written
  before a keep/discard/defer decision.
- [x] G008 Pareto frontier records dominated and non-dominated candidates.
- [x] G009 Inner-loop candidates from Feature 023 are visible as candidates, but
  cannot promote themselves without the Feature 034 outer-loop decision.
- [x] G010 A completed run summary states whether the proposer inspected raw prior
  artifacts and lists the artifact classes inspected.
- [x] G011 Provider calls are budgeted and optional; provider-free iterations remain
  valid when the search set uses deterministic gates only.
- [ ] G012 Holdout execution requires an explicit guard and produces separate
  promotion evidence.

2026-05-01 static gate evidence: `meta_harness.real_outer_loop` implements the
no-browser iteration path and tests assert proposal/pending-eval/decision/
proposer-interaction artifacts plus `true_meta_harness_iteration=true`. G004 is
partial because current code hashes frozen files before/after but does not yet
block arbitrary external git diffs. G012 remains open for the explicit Feature
034 holdout execution command.

2026-05-01 live no-browser gate evidence:
`run-metaharness-round-1-fixed` passed G001-G003 and G005-G011 with real
backend execution. Baseline and candidate both had raw traces/SSE/scores/
verdicts/source snapshots, holdout stayed hidden, the candidate had explicit
write scope and pending eval, trace/cost/latency metrics were written before
decision, and the candidate was discarded as dominated. G004 remains partial
for arbitrary code-patch candidates; G012 remains open.
