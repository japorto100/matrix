---
title: Sandbox Security HITL Research
status: draft
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 013
---

# Research

## Subagent / Gateway Safety Transfer 2026-04-30

References: `_ref/hermes-agent/tools/delegate_tool.py`,
`_ref/claude_code/openclaw/src/gateway/server-methods.ts` and Feature 033.

Safety invariants:

- Subagent worker threads must never block on interactive stdin approvals.
- Dangerous commands in child contexts default to deny unless explicitly
  configured and audited.
- Gateway/control-plane methods need scope classification and rate limiting.
- Matrix room/DM authorization must fail closed before agent execution.

