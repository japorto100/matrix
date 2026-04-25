---
title: Sandbox, Security and HITL Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 013
migrated_from:
  - specs/execution/exec-12-sandbox-security.md
  - specs/execution/exec-security.md
---

# Tasks

## Migration / SDD

- [x] T001 Import `exec-12`, `exec-security`, ADR-004 and `16-security` into
  one feature boundary.
- [x] T002 Record source/paper/repo context in `sources.md`.
- [x] T003 Split feature into explicit subfeatures and gates.
- [x] T004 Mirror ADR-004 into `specs_sdd/adr/` or mark old ADR path as accepted
  canonical until ADR migration pass.

## OpenSandbox Runtime

- T010 Verify compose/podman profile starts `opensandbox-server`.
- T011 Verify safe Python execution returns stdout/stderr/files.
- T012 Verify file upload is copied into sandbox and result is returned while
  original stays outside agent process.
- T013 Verify browser sandbox screenshot/artifact path.
- T014 Verify denied egress or empty `allowed_domains` prevents network
  access where configured.
- T015 Verify resource/time/output limits: TTL destroy, stdout/stderr caps,
  max file size, per-tool timeout.

## Consent / RBAC / Rate Limits

- T020 Verify `sandbox_execute` and `sandbox_browser` require confirm-level
  consent.
- T021 Verify session cache paths: allow once, allow session, deny, deny
  session.
- T022 Verify per-tool and per-session rate limits stop execution.
- T023 Verify role forwarding (`X-User-Role`, `X-Auth-User`) reaches consent
  checks and blocks insufficient roles.

## Prompt Injection / Sanitization

- [x] T030 Static-test scheduled-task prompt scanner blocks malicious create and
  edit prompts before DB write.
- [x] T031 Static-test safe multilingual scheduler prompts pass.
- [x] T032 Static-test sanitizer P0 XML content tagging around untrusted tool
  output.
- [x] T033 Static-test P1 regex warning for high-risk tool output.
- T034 Verify optional ProtectAI DeBERTa classifier behavior when model is
  present, with graceful degradation when absent.
- T035 Verify P3 output anomaly scan catches suspicious exfil outputs.
- T036 Verify prompt template validator blocks dangerous variable/code
  access.

## Redaction / Secret Leak Prevention

- [x] T040 Verify Tier-1 redaction corpus for static secret patterns.
- [x] T041 Verify non-secret corpus has acceptable false-positive rate.
- [x] T042 Static-test redaction primitives used before persistence paths.
- [x] T043 Verify trajectory exporter redacts before ShareGPT/fine-tuning output.
- T044 Verify Tier-2 redaction consumer is disabled by default and ReDoS
  guarded when enabled.
- T045 Decide whether Tier-3 ML redaction research is needed after benchmark.

## Skills-Guard HITL

- [x] T050 Static-test dangerous skill import returns structured verdict with
  `suggested_action: "hitl_confirm"`.
- [x] T051 Verify BFF parses Skills-Guard verdict instead of showing generic
  toast.
- [x] T052 Static-test `SkillsGuardDrawer` verdict extraction for findings and
  HITL action body shapes.
- T053 Verify allow-once/allow-session retries import with human-approved
  trust source.
- T054 Verify deny path keeps import blocked.
- T055 Verify CONSENT_REQUEST/CONSENT_DECISION audit metadata includes
  verdict and matched patterns.

## Matrix-Specific Security

- [x] T060 Verify URL preview remains disabled in active dev homeserver config.
- T060b Verify URL preview remains disabled in active prod homeserver
  config when prod config exists.
- [x] T061 Verify E2EE trust model is represented in Matrix Chat feature docs
  and agent-room bridge docs.
- [x] T062 Static-verify markdown/HTML sanitizer strips script/event/javascript
  payloads.
- [x] T063 Verify `pendingEventOrdering: "detached"` remains in Matrix client
  creation.

## Control UI

- T070 Verify Security tab loads live backend state.
- T071 Verify Sandbox tab reports OpenSandbox health and unavailable state
  clearly.
- T072 Verify Permissions tab shows real consent/RBAC policy where available.
- T073 Verify audit/raw-access UI requires admin role and reason if raw span
  access is exposed.

## Verify Gates

- Sandbox starts or is explicitly unavailable.
- [x] Prompt scanner has positive and negative tests.
- [x] Redaction behavior is tested.
- HITL decision path is live-verified.
- [x] Matrix SSRF/XSS decisions are checked statically for active dev config.
