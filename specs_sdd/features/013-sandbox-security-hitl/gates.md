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

- [ ] Scheduled task create blocks high-risk prompt.
- [ ] Scheduled task edit blocks high-risk prompt.
- [ ] Benign multilingual prompt passes.
- [ ] XML tagging wraps untrusted tool output.
- [ ] Regex scanner detects known injection/exfil samples.
- [ ] Optional DeBERTa classifier is verified or marked unavailable.
- [ ] Output anomaly scanner detects suspicious final output.

## G4 Redaction

- [ ] Static secret corpus redacted.
- [ ] Non-secret corpus false-positive rate reviewed.
- [ ] Span persistence redacts secrets.
- [ ] Trajectory export redacts secrets.
- [ ] Tier-2 pattern consumer has ReDoS guard when enabled.
- [ ] Admin raw access, if present, requires role and reason.

## G5 Skills-Guard HITL

- [ ] Dangerous synthetic skill returns structured verdict.
- [ ] Frontend routes verdict into Skills-Guard drawer.
- [ ] Drawer shows findings and three decisions.
- [ ] allow once/session retries import successfully.
- [ ] deny keeps import blocked.
- [ ] audit metadata records verdict and matched patterns.

## G6 Matrix Security

- [ ] URL previews are disabled in current dev/prod config.
- [ ] XSS sanitizer strips script/event/javascript payloads.
- [ ] E2EE agent-room trust boundary is documented in Feature 006.
- [ ] `pendingEventOrdering: "detached"` remains configured.

## G7 Research Decision

- [ ] Redaction benchmark corpus is defined.
- [ ] Regex baseline false-positive/false-negative rate measured.
- [ ] Cloudflare/GitHub/Trufflehog/GitGuardian/OWASP leak taxonomy inputs are
  evaluated before any Tier-3 ML work.
