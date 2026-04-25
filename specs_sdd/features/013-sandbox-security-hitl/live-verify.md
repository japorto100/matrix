---
title: Sandbox, Security and HITL Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 013
---

# Live Verify

## Source Checks

- `exec-12` Phase 1/2 implemented items are either verified here or marked
  stale with reason.
- `exec-security` shipped/open split is reflected in tasks.
- ADR-004 surface-dialog decision is represented in gates.
- Superpower implementation log entries for Skills-Guard drawer are checked
  against current code.
- `16-security.md` Matrix SSRF/XSS/E2EE decisions are checked against config.

## Sandbox Runtime

- Start sandbox profile.
- Run safe command/script.
- Confirm output is captured.
- Confirm denied operation is blocked or isolated.
- Upload CSV/JSON/code sample and confirm sandbox result.
- Run browser sandbox smoke test and capture artifact.
- Stop/restart sandbox and confirm graceful error message when unavailable.

## Prompt / Redaction

- Submit benign scheduled task prompt.
- Submit malicious/prompt-injection scheduled task prompt.
- Confirm scanner blocks high-risk prompt.
- Send sample sensitive data through redaction path.
- Confirm sensitive value is redacted in logs/output.
- Export trajectory/sample span and confirm redacted value does not reappear.
- Confirm non-secret text remains readable enough for debugging.

## HITL / UI

- Import a dangerous synthetic skill.
- Confirm structured 422 body includes verdict and suggested action.
- Confirm BFF opens Skills-Guard drawer/dialog.
- Approve once and confirm import retry succeeds.
- Deny and confirm import remains blocked.
- Confirm consent/audit events record both outcomes.
- Confirm Control UI Security/Sandbox/Permissions state reflects result.

## Matrix Security

- Try URL preview path/config; confirm previews are disabled.
- Send sanitized markdown/XSS sample; confirm unsafe HTML is stripped.
- Confirm private/E2EE and agent-room trust boundary matches feature 006.

## Result

pending
