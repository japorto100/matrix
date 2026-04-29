---
title: Devstack Bootstrap, Env and Persistence Ops Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 002
---

# Live Verify

## Required Flows

- Start infrastructure profile needed for current work.
- Confirm Postgres accepts connections and migrations can run.
- Confirm NATS is reachable when messaging features are in scope.
- Confirm Tuwunel starts when Matrix features are in scope.
- Confirm env files can be copied from examples without missing required keys.
- Confirm secrets bootstrap/runbook is usable without committing secrets.

## Evidence

- Command output summaries in `closeout.md`.
- Screenshots not required.

## Result

partial-pass

## Live Evidence 2026-04-27

- `llm-mock` was stopped and `--matrix-mock` no longer starts the
  OpenAI-compatible mock server on `:8095`; it remains explicit via
  `--llm-mock` for local Meta-Harness/mock gates.
- `matrix-postgres` is running on `:5433` with pgvector `0.8.2`.
  Postgres did not crash in the inspected logs; the previous stop was a normal
  smart shutdown with exit code `0`.
- Postgres logs showed runtime queries against missing
  `agent.user_agent_settings`; Feature 018/020 now owns the fix through
  Alembic revision `032_user_agent_settings`.
- Matrix NATS now runs as `matrix-nats` on host `:14222` with monitoring on
  `:18222` and dedicated `matrix_nats-data` volume. Tradeview's NATS remains
  untouched on `:4222/:8222`.
- Local Matrix env files were updated to `NATS_URL=nats://localhost:14222`;
  `scripts/bootstrap-env.py` was updated so regenerated env files keep that
  port.
- `python-bridge` was restarted and reports
  `nats_connected: true`, `nats_url: nats://localhost:14222`.
