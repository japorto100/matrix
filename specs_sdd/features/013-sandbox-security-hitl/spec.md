---
title: Sandbox, Security and HITL
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 013
migrated_from:
  - specs/16-security.md
  - specs/execution/exec-12-sandbox-security.md
  - specs/execution/exec-security.md
  - docs/superpowers/findings/2026-04-23-adr-004-sandbox-hitl-layer.md
  - specs/execution/archive/opensandbox-gemini-usecases.txt
adrs:
  - 0004
---

> IMPORTANT: The large OpenSandbox Code Interpreter image is archived on HDD to
> keep the SSD free. Before running OpenSandbox-backed flows, load it with:
>
> ```bash
> podman load -i /mnt/cold-storage/archive/podman-images/opensandbox-code-interpreter-v1.0.2.tar
> ```

# Sandbox, Security and HITL

## Current State / Ist

OpenSandbox and the first security-hardening pass are implemented. The old
`exec-12` file marks Phase 1 OpenSandbox and Phase 2 security hardening as done:
container profile, SDK manager, `sandbox_execute`, file-analysis upload flow,
browser sandbox, structured audit logs, consent, rate limiting, sanitizer,
template validation, role forwarding and installer hardening.

The security umbrella (`exec-security`) adds cross-cutting posture: span and
trajectory redaction are shipped as Tier-1/Tier-2, scheduler prompt scanning is
shipped, audit-trail integrity is only partial, and ML-based secret detection is
still research.

ADR-004 decided the Skills-Guard HITL boundary on 2026-04-23: dangerous skill
imports must be handled at the surface/dialog layer through the existing consent
system, not inside OpenSandbox. The Superpower implementation log records that
the structured 422 response and `SkillsGuardDrawer` frontend later landed, but
live verification remains required.

Matrix-specific security decisions also belong here: URL previews must be
disabled because Matrix/Synapse server-side previews create SSRF risk, E2EE
trust boundaries are intentional, `pendingEventOrdering: "detached"` fixes SDK
send/redact/kick flows, and markdown/HTML messages are sanitized.

Static verification on 2026-04-25 passes prompt-scanner, redaction,
Skills-Guard and trajectory-export tests. Matrix client creation still contains
`pendingEventOrdering: "detached"` and Agent Chat markdown uses
`rehype-sanitize`. A later static cleanup on the same date made two local gaps
concrete:

- the active `homeserver/tuwunel.v1.6.toml` now explicitly sets the URL-preview
  allowlists to empty arrays and has a config test for that posture;
- `SkillsGuardDrawer.extractSkillsGuardVerdict()` now unwraps FastAPI
  `HTTPException.detail` bodies forwarded through the Next.js BFF proxy, so
  dangerous backend verdicts route to the drawer instead of a generic toast.

## Target State / Soll

Untrusted execution, prompt-risk handling, permissions, redaction and HITL
approvals are governed by one security model:

- own trusted backend code runs in backend processes;
- LLM-generated or user-entered executable code always runs in OpenSandbox;
- API/tool results are treated as data and sanitized before returning to the
  model;
- dangerous skill imports are paused at the API/UI surface, approved through the
  existing consent system, and audit-logged as consent decisions;
- sensitive persistence surfaces are redacted before they reach spans,
  trajectory exports or cross-user UI;
- Matrix SSRF/XSS/E2EE decisions remain explicit, not hidden as frontend
  implementation detail.

## Subfeatures

- 013.1 OpenSandbox runtime boundary
- 013.2 Consent, rate limit and role authorization
- 013.3 Prompt-injection and output-sanitization defense
- 013.4 Redaction and secret-leak prevention
- 013.5 Skills-Guard HITL surface dialog
- 013.6 Audit integrity and raw-access policy
- 013.7 Matrix-specific SSRF/XSS/E2EE security
- 013.8 Control UI security, sandbox and permissions surfaces

## Gap

- ADR-004 is decided and should be mirrored into `specs_sdd/adr/` or referenced
  as accepted until ADR migration is done.
- Skills-Guard drawer is reported as implemented in `superpower-impl-log`, but
  SDD still needs live verify: dangerous import -> drawer -> allow/deny ->
  audit event.
- OpenSandbox was implemented, but current live availability on this machine is
  not verified in SDD evidence.
- Audit trail is append-only by convention only; HMAC/hash-chain tamper
  detection remains optional future work.
- Redaction Tier-3 ML research is not decided. Cloudflare/GitHub/Trufflehog/
  GitGuardian/OWASP leak taxonomy references are open evaluation inputs.
- Control UI Security/Sandbox/Permissions tabs must be checked against real
  backend state, not only static rendering.
- URL-preview disablement is explicit in the active dev config; live prod
  config still needs operator verification before broad exposure.

## Static Verify

- [x] `uv run pytest tests/agent/security/test_prompt_scanner.py tests/agent/security/test_redact.py tests/agent/security/test_skills_guard.py tests/agent/test_trajectory_export.py -q` passes.
- [x] Prompt scanner positive/negative cases are covered.
- [x] Redaction and trajectory export redaction are covered.
- [x] Skills-Guard backend verdict logic is covered.
- [x] Skills-Guard frontend/BFF error-shape extraction is covered.
- [x] `pendingEventOrdering: "detached"` remains in Matrix client creation.
- [x] Agent Chat markdown uses a sanitize pipeline.
- [x] Active Tuwunel dev config has empty URL-preview allowlists.

## Live Verify

- Sandbox profile starts when selected.
- Prompt scanner blocks high-risk scheduled task prompt through the live API.
- Redaction path works for configured sensitive fields in persistence.
- Skills-Guard dangerous import opens the HITL drawer.
- Approve/reject decisions are audit-logged.
- URL preview disablement is confirmed in active prod homeserver config.
- Security/Sandbox/Permissions tabs reflect backend state.

## Closeout Criteria

- Security decisions are captured as ADRs.
- No security feature is considered done without live or adversarial verify.
