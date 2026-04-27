---
title: Sandbox, Security and HITL Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
feature_id: 013
---

# Closeout

## Built

- Prompt scanner and scheduler-prompt security tests.
- Sanitizer/redaction primitives and trajectory-export redaction.
- Skills-Guard backend verdict logic and structured HITL action metadata.
- Skills-Guard frontend verdict extraction now handles both root response
  bodies and FastAPI `detail` wrappers forwarded by the BFF proxy.
- Matrix client `pendingEventOrdering: "detached"` security/workflow setting.
- Agent Chat markdown sanitize pipeline.
- Active Tuwunel dev config explicitly disables URL-preview allowlists.
- OpenSandbox manager/tools exist, but were not live-started in this pass.
- FileAnalyzeTool compatibility path is repaired: `SandboxManager.execute_file`
  now stages uploaded file bytes through the existing OpenSandbox
  `execute_code(upload_files=...)` lifecycle.

## Not Built

- Full live OpenSandbox execution evidence on this machine.
- Live file upload proof; current OpenSandbox/Podman runtime fails sandbox
  creation before user code runs.
- Full Skills-Guard UI drawer allow/reject retry path with audit evidence.
- HMAC/hash-chain audit-trail tamper detection.
- Tier-3 ML redaction/leak detector decision.
- Confirmed URL-preview disablement in prod/operator config, if distinct from
  the active dev config.

## Deviations From Plan

- ADR-004 HITL boundary is accepted from old docs for now; full ADR migration
  can happen in a later ADR cleanup pass.
- Skills-Guard is deliberately a surface/consent workflow, not an OpenSandbox
  responsibility.

## Verify Result

- PASS static: `uv run pytest tests/agent/security/test_prompt_scanner.py tests/agent/security/test_redact.py tests/agent/security/test_skills_guard.py tests/agent/test_trajectory_export.py -q`.
- PASS static: `uv run pytest tests/config/test_tuwunel_url_preview.py tests/agent/security/test_skills_guard.py -q`.
- PASS frontend static: `bun run test -- src/features/control/components/SkillsGuardDrawer.test.ts`.

## Live Verify Result

Pending: OpenSandbox start/execution, Skills-Guard drawer allow/reject/audit,
Control Security/Sandbox/Permissions tabs and prod URL-preview config check.

Partial live update 2026-04-27: OpenSandbox health on `:8080` passed, but live
file execution failed during sandbox creation with Podman/Docker archive
`broken pipe`; static file-staging code is fixed and covered.

## Follow-Ups

- Live-test dangerous skill import -> drawer -> allow/deny -> audit event.
- Live-test OpenSandbox execution and browser artifact path.
- Confirm URL-preview posture in prod config if it diverges from the active
  Tuwunel dev config.
- Decide whether audit integrity needs HMAC/hash-chain before production.
