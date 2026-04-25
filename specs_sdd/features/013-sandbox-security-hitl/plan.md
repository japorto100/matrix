---
title: Sandbox, Security and HITL Plan
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 013
migrated_from:
  - specs/16-security.md
  - specs/execution/exec-12-sandbox-security.md
  - specs/execution/exec-security.md
  - docs/superpowers/findings/2026-04-23-adr-004-sandbox-hitl-layer.md
adrs:
  - 0004
---

# Plan

## Architecture

This feature owns sandbox execution safety, consent/rate-limit/role policy,
prompt-risk scanning, redaction, HITL decisions and security UI contracts.

The core boundary is source-based:

| Source | Execution place | Security handling |
|---|---|---|
| Trusted backend code | Backend services | normal tests, RBAC, audit |
| LLM-generated code | OpenSandbox | confirm-level consent, resource limits, egress policy |
| User-entered code | OpenSandbox | confirm-level consent, resource limits, egress policy |
| Tool/API results | Backend data path | sanitizer/redaction before model/persistence |
| Skill imports | API surface | skills_guard verdict -> consent/HITL drawer |

OpenSandbox is a code-execution boundary, not a replacement for consent,
redaction, RBAC or audit. HITL belongs at the surface when the risk is known
before execution; runtime sandbox approvals would require a separate IPC design.

## Critical Files

- `docker-compose.yml`
- `python-backend/agent/sandbox/**`
- `python-backend/agent/tools/sandbox_tool.py`
- `python-backend/agent/tools/sandbox_browser_tool.py`
- `python-backend/agent/security/**`
- `python-backend/agent/middleware/sanitizer.py`
- `python-backend/agent/middleware/template_validator.py`
- `python-backend/agent/consent/**`
- `python-backend/agent/audit/**`
- `python-backend/alembic/versions/023_agent_redaction_patterns.py`
- `frontend_merger/src/features/control/**Security*`
- `frontend_merger/src/features/control/**Sandbox*`
- `frontend_merger/src/features/control/**Permissions*`
- `frontend_merger/src/features/control/**SkillsGuard*`
- Matrix client config for URL preview, E2EE and markdown sanitization

## Migration Strategy

1. Treat `exec-12` Phase 1/2 as implemented baseline, but require fresh live
   verify before closeout.
2. Promote ADR-004 as accepted decision: Skills-Guard HITL is surface-dialog via
   consent system.
3. Merge `exec-security` into subfeatures: redaction, prompt scanner, HITL,
   audit integrity and research backlog.
4. Keep Matrix-specific SSRF/XSS/E2EE decisions from `16-security.md` in this
   feature, even though some implementation lives in chat/frontend features.
5. Route span persistence and audit-store observability mechanics to Feature
   014, while keeping the security policy here.
6. Convert paper/repo references into `sources.md` entries with adopted ideas.

## Execution Order

1. Source ledger and subfeature split.
2. OpenSandbox runtime live verify.
3. Prompt scanner and redaction unit/live checks.
4. Skills-Guard HITL full path: import -> drawer -> decision -> audit.
5. Control UI backend-state checks.
6. Optional research decision for Tier-3 ML redaction.

## Risks

- Security controls marked done without adversarial or live verify.
- OpenSandbox may be installed but not operational because the container runtime
  socket/profile is unavailable.
- Surface-dialog HITL can regress into raw 422 errors if BFF parsing is missing.
- Redaction false positives can damage audit/debug value; false negatives can
  leak secrets into spans, trajectory exports or Matrix rooms.
- URL preview reactivation would reopen SSRF risk unless isolated fetcher design
  and denylist/allowlist are implemented.
