---
title: Observability, Harness and Evals Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
---

# Live Verify

## Tracing

- [ ] Start runtime with tracing env.
- [ ] Run one Agent Chat turn.
- [ ] Confirm trace ID is produced.
- [ ] Confirm span data is persisted.
- [ ] Confirm OpenObserve or configured backend can query it.
- [ ] Confirm Go and Python traces both appear when enabled.
- [ ] Confirm disabled tracing does not crash.

## Audit

- [ ] Trigger auditable action.
- [ ] Confirm audit event persisted.
- [ ] Confirm Control UI Audit tab shows event or query route works.

## Harness / Evals

- [ ] Run one small eval/harness job.
- [ ] Confirm score rows are produced.
- [ ] Confirm composite fitness fields are populated.
- [ ] Confirm A/B backfill worker path if in scope.
- [ ] Confirm eval/candidate/source evidence is linked or stored.

## Sources

- [ ] Confirm paper/product sources in `sources.md` still match current tasks.
- [ ] Confirm any paper-derived task names the adopted idea.

## Result

pending
