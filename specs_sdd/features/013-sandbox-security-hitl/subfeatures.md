---
title: Sandbox Security HITL Subfeatures
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 013
---

# Subfeatures

## 013.1 OpenSandbox Runtime Boundary

Owns untrusted code execution: LLM-generated code, user-entered code, file
analysis snippets, browser automation and skill evaluation. It must preserve
the `exec-12` lifecycle: create sandbox, upload files, execute, collect
artifacts, destroy in a finally path.

Key invariants:

- backend-owned deterministic code does not enter sandbox;
- sandbox has explicit CPU/memory/TTL/output/file limits;
- egress policy defaults to deny or constrained allowlist;
- unavailable sandbox fails closed with clear start guidance.

## 013.2 Consent, Rate Limit and Role Authorization

Owns policy-driven approvals for high-risk tools. `consent_policy.yaml`,
session consent cache, per-tool/session rate limits and role forwarding are one
system. The SDD boundary is the policy, not a specific UI.

## 013.3 Prompt-Injection and Output Sanitization

Owns P0-P3 defense:

- XML content tagging for untrusted tool output;
- regex prefilter for high-risk tools;
- optional ProtectAI DeBERTa classifier;
- final output anomaly scan;
- scheduler prompt scanner before create/edit DB writes.

## 013.4 Redaction and Secret-Leak Prevention

Owns what may be persisted/exported. Tier-1 static regex runs synchronously in
span persistence and trajectory export. Tier-2 DB-backed patterns are async and
default-disabled. Tier-3 ML is research only until benchmarked.

## 013.5 Skills-Guard HITL Surface Dialog

Owns the ADR-004 workflow:

1. skills_guard emits `clean | suspicious | dangerous`;
2. dangerous verdict returns structured 422 with `suggested_action`;
3. frontend BFF routes verdict to drawer/dialog;
4. user chooses allow once, allow session or deny;
5. import retries with human-approved trust source or remains blocked;
6. consent/audit events record decision and matched patterns.

## 013.6 Audit Integrity and Raw-Access Policy

Owns security semantics for audit data. Feature 014 owns tracing/observability
implementation details, but this feature owns whether audit is append-only,
whether raw access requires admin+reason, and whether future HMAC/hash-chain
tamper detection is worth implementing.

## 013.7 Matrix-Specific SSRF/XSS/E2EE Security

Owns security decisions that cut across Matrix chat:

- URL previews disabled because server-side preview fetching creates SSRF risk;
- E2EE trust model: Go appservice decrypts for agent rooms, Python does not own
  Matrix keys;
- markdown/HTML messages are sanitized;
- Matrix client uses `pendingEventOrdering: "detached"` for stable SDK calls.

## 013.8 Control UI Security Surfaces

Owns Security, Sandbox, Permissions and Skills-Guard user surfaces where they
represent security state. UI-only rendering is not enough; each panel needs a
backend state source or an explicit unavailable/deferred state.
