---
title: Agent Harness Subagents Routing Live Verify
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 020
---

# Live Verify

## LV-01 Runner Routing Smoke

Status: planned.

Expected:

- Postgres/audit store reachable.
- Meta-Harness local lane can run routing mechanics without OpenRouter quota.
- Live OpenRouter lane can run at least one quality smoke.

## LV-02 Subagent Boundary Smoke

Status: planned.

Expected:

- When subagents are not implemented, scenarios requiring delegation fail or
  defer explicitly, not silently hallucinate a delegate.
