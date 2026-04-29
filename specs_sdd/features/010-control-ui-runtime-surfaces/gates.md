---
title: Control UI and Runtime Surfaces Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 010
---

# Gates

## 2026-04-29 Feature 024-029 Follow-Up

- Tools tab shows effective ToolRegistry policy metadata, including risk,
  approval, group, provider and last-seen state.
- MCP tab shows effective filtered catalog and risk state from Feature 024, not
  raw untrusted descriptors only.
- [x] Semantic tab or inspector shows metric/term owner, version, provenance
  and conflict status from Feature 025 in static frontend coverage.
- Ops room shows live/replayed agent status from Feature 029 before optional
  spatial/3D experiments.

## G1 Shell / Routing

- [x] `/control/[[...tab]]` route exists in `frontend_merger`.
- [x] Control shell dispatches primary tabs from URL path.
- [x] Top navigation includes developer-mode tabs such as system, audit, MCP
  and A2A.
- [x] Frontend lint/typecheck/test/build gates pass under Feature 003/007.
- [ ] Browser walkthrough confirms no responsive/layout regressions.

## G2 BFF / Backend Wiring

- [x] Catch-all `/api/control/[...path]` BFF proxy exists.
- [x] React Query clients target `/api/control/*`, `/api/memory/*` and scheduler
  API surfaces.
- [ ] Header/body/query preservation is live-verified through the BFF.
- [ ] Every backend route has real owner-feature status or documented mock
  fallback.
- [x] Semantic catalog route has live backend endpoint plus documented frontend
  fallback.

## G3 Mock Fallback Discipline

- [x] Mock fallback is explicit in hooks/components.
- [ ] Live verify records which tabs use live data versus `mock-data.ts`.
- [ ] Mock-backed tabs expose actionable empty/deferred state where backend is
  absent.

## G4 Tab Coverage

- [ ] Files tab and upload/preview/reindex path live-verified.
- [ ] Memory browser/KG live data path live-verified.
- [ ] Agents/permissions/skills/tools/sandbox live or empty-state verified.
  Tools static frontend coverage is done; browser/live proof remains pending.
- [ ] System/audit/sessions/MCP/A2A live or empty-state verified.
- [ ] Models/provider/billing live or empty-state verified.

## G5 Ownership

- [x] Memory/KG backend gaps route to Feature 012.
- [x] LLM/models/billing gaps route to Feature 011.
- [x] Sandbox/security/HITL gaps route to Feature 013.
- [x] Observability/audit/session gaps route to Feature 014.
- [x] Skills/scheduler/planning gaps route to Feature 015.
