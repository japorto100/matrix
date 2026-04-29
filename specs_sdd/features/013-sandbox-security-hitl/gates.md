---
title: Sandbox Security HITL Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-29
feature_id: 013
---

# Gates

## 2026-04-29 MCP/Widget/Report Follow-Up

- MCP STDIO server configuration is allowlisted and never prompt/user supplied.
- Remote MCP transport validates origin/auth according to Feature 024 policy.
- Matrix widget/app hosting uses Feature 030 sandbox/origin policy.
- Report rendering from Feature 027 has an explicit execution policy.

## G1 OpenSandbox Runtime

- [x] Compose/podman profile can start `opensandbox-server`/`opensandbox-api-gateway`.
- [x] Health check succeeds.
- [x] Sandbox execution paths now include sandbox_id and diagnostics payload summary in
  audit/output for sandbox code/browser tools.
- [ ] Safe Python execution returns stdout/stderr.
- [ ] File upload sample returns artifact/result. Static staging path is fixed;
  live sandbox creation is currently blocked by OpenSandbox/Podman archive
  `broken pipe` before user code runs.
- [ ] Browser sandbox returns screenshot or artifact.
- [ ] TTL/resource/output limits are enforced or documented as unavailable.
  Current blocker: sandbox creation fails before TTL/output limit proof.
- [ ] Egress-deny behavior is tested.

## G2 Consent / RBAC / Rate Limit

- [x] `sandbox_execute` requires confirm-level consent.
- [x] `sandbox_browser` requires confirm-level consent.
- [x] Graphless SimpleLoop runs `approval_node` before tool execution and fails
  closed for confirm-level tools when no interrupt/resume channel is available.
- [ ] allow once/session and deny once/session paths work.
- [ ] per-tool limit blocks after configured maximum.
- [x] insufficient role is denied before tool execution.

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
- [x] Matrix widget events block unsafe URLs and do not render arbitrary iframes.
- [x] E2EE agent-room trust boundary is documented in Feature 006.
- [x] `pendingEventOrdering: "detached"` remains configured.

## G7 Research Decision

- [ ] Redaction benchmark corpus is defined.
- [ ] Regex baseline false-positive/false-negative rate measured.
- [ ] Cloudflare/GitHub/Trufflehog/GitGuardian/OWASP leak taxonomy inputs are
  evaluated before any Tier-3 ML work.
