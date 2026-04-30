---
title: Matrix Chat Core Research
status: draft
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 005
---

# Research

## OpenClaw / Hermes Matrix Transfer 2026-04-30

Local references:

- `_ref/claude_code/openclaw/docs/channels/matrix.md`
- `_ref/claude_code/openclaw/docs/concepts/qa-e2e-automation.md`
- `_ref/claude_code/openclaw/docs/channels/matrix-push-rules.md`
- `_ref/claude_code/openclaw/docs/install/migrating-matrix.md`
- `_ref/hermes-agent/gateway/platforms/matrix.py`
- `Z_matrix_widgets_formulars_and so on.md`

Findings to transfer:

- Matrix chat must treat DMs, rooms and threads as distinct routing/session
  surfaces, with explicit allowlist, mention and bot-loop policies.
- Tuwunel is suitable for disposable live QA: driver, SUT and observer users
  plus one private room can verify real transport behavior without external
  Matrix credentials.
- Streaming previews need explicit modes: final-only, editable partial preview
  and quiet finalized-preview behavior. Quiet mode requires push-rule setup and
  must not be assumed for generic clients.
- Reactions, read receipts, rich formatting, media, voice and `m.mentions`
  should be verified as first-class Matrix behavior, not agent-text parsing.
- E2EE recovery requires device/backup/verification state gates and migration
  snapshots before mutating crypto state.

