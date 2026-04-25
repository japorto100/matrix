---
title: Sandbox Security HITL Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 013
---

# Gates

## G1 OpenSandbox Runtime

- [ ] Compose/podman profile starts `opensandbox-server`.
- [ ] Health check succeeds.
- [ ] Safe Python execution returns stdout/stderr.
- [ ] File upload sample returns artifact/result.
- [ ] Browser sandbox returns screenshot or artifact.
- [ ] TTL/resource/output limits are enforced or documented as unavailable.
- [ ] Egress-deny behavior is tested.

## G2 Consent / RBAC / Rate Limit

- [ ] `sandbox_execute` requires confirm-level consent.
- [ ] `sandbox_browser` requires confirm-level consent.
- [ ] allow once/session and deny once/session paths work.
- [ ] per-tool limit blocks after configured maximum.
- [ ] insufficient role is denied before tool execution.

## G3 Prompt Injection / Sanitization

- [x] Scheduled task create blocks high-risk prompt in tests.
- [x] Scheduled task edit blocks high-risk prompt in tests.
- [x] Benign multilingual prompt passes in tests.
- [x] XML tagging wraps untrusted tool output in tests.
- [x] Regex scanner detects known injection/exfil samples in tests.
- [ ] Optional DeBERTa classifier is verified or marked unavailable.
- [x] Output anomaly scanner detects suspicious final output in tests.

## G4 Redaction

- [x] Static secret corpus redacted.
- [x] Non-secret corpus false-positive rate covered by tests.
- [x] Span persistence redaction primitives are covered by tests.
- [x] Trajectory export redacts secrets.
- [ ] Tier-2 pattern consumer has ReDoS guard when enabled.
- [ ] Admin raw access, if present, requires role and reason.

## G5 Skills-Guard HITL

- [x] Dangerous synthetic skill returns structured verdict in backend tests.
- [x] Frontend extractor unwraps BFF/FastAPI verdicts for the Skills-Guard drawer.
- [x] Drawer verdict extraction covers findings and decision-body shapes.
- [ ] allow once/session retries import successfully.
- [ ] deny keeps import blocked.
- [ ] audit metadata records verdict and matched patterns.

## G6 Matrix Security

- [x] URL previews are disabled in active dev config.
- [ ] URL previews are disabled in active prod config when prod config exists.
- [x] XSS sanitizer strips script/event/javascript payloads in tests/static
  sanitizer pipeline.
- [x] E2EE agent-room trust boundary is documented in Feature 006.
- [x] `pendingEventOrdering: "detached"` remains configured.

## G7 Research Decision

- [ ] Redaction benchmark corpus is defined.
- [ ] Regex baseline false-positive/false-negative rate measured.
- [ ] Cloudflare/GitHub/Trufflehog/GitGuardian/OWASP leak taxonomy inputs are
  evaluated before any Tier-3 ML work.
