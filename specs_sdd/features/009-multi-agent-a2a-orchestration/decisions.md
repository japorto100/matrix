---
title: Multi-Agent and A2A Orchestration Decisions
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 009
---

# Decisions

## D009-001 Default Agent for Matrix DMs

Status: accepted.

Decision: a Matrix DM or routed inbound payload without an explicit
`target_agent` uses the configured Python bridge default `AGENT_USER_ID`.
In local development this defaults to `@agent-trading:matrix.local` via
`MATRIX_BOT_USER_ID` fallback.

Rationale:

- Keeps DM behavior deterministic without requiring a mention.
- Preserves the existing bridge contract: Go extracts `target_agent` only from
  explicit `@agent-*` mentions; Python owns reply identity fallback through
  `AGENT_USER_ID`.
- Avoids hidden per-room state until per-user agent settings are implemented.

Implications:

- Group rooms still require mention filtering when `MENTION_ONLY_IN_GROUPS=true`.
- Per-user default agent remains future work under T044; per-user default model
  lookup is already static-tested separately.
- Operator docs should treat `AGENT_USER_ID` as the default DM identity.
