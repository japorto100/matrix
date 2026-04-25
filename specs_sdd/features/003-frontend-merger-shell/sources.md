---
title: Frontend Merger Shell Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 003
---

# Sources

| Source | Role in SDD |
|---|---|
| `specs/execution/claude-merge-frontend-chat-ui-2OqmH/README.md` | Branch merger narrative and scope. |
| `specs/execution/claude-merge-frontend-chat-ui-2OqmH/VERIFY-GATES.md` | Evidence ledger: passed, open and local-only gates. |
| `exec-01-frontend-merger-scaffold.md` | Shell scaffold and route mount. |
| `exec-02-envfiles-devstack-compose.md` | Env/compose integration changes. |
| `exec-03-linter-fixes.md` | Go/Python/frontend linter and behavior fixes from merger. |
| `exec-04-playwright-verify.md` | Playwright and route smoke details. |
| `exec-05-ui-viewers-polish.md` | Files/model viewer polish ownership. |
| `archive/exec-merge-chat-SUPERSEDED.md` | Historical merge-chat rationale; superseded by frontend_merger. |
| `docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md` | Current Superpower plan; v1 is superseded. |
| `docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md` | Control/UI mapping design source. |
| `main_docs/specs/architecture/FRONTEND_ARCHITECTURE.md` | Frontend shell, BFF boundary, state layers, route and feature ownership reference. |

## Adopted Into Matrix

- `frontend_merger` is the canonical UI shell.
- Evidence must preserve pass/open/local-only distinction.
- Live local full-stack smoke is still separate from build/playwright evidence.
