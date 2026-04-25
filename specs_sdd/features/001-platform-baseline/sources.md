---
title: Platform Baseline Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 001
---

# Sources

| Source | Role in SDD |
|---|---|
| `specs/00-overview.md` | Primary platform overview, stack choices, ports and directory map. |
| `specs/08-tooling.md` | Tool/binary acquisition and local tooling assumptions. |
| `specs/09-privacy.md` | Privacy defaults and federation/presence/media decisions. |
| `specs/10-portierung.md` | Direction for later tradeview-fusion integration. |
| `specs/FUTURE_IDEAS.md` | Ideas backlog; must not be confused with active scope. |
| `specs/agent-output-pattern.md` | Agent output conventions. |
| `AGENTS.md` / project instructions | Local machine/tooling constraints and German communication preference. |

## Adopted Baseline

- This repo remains isolated testbed until porting is explicitly executed.
- Go is Matrix/E2EE boundary; Python is agent/runtime boundary.
- `frontend_merger` is the current UI consolidation target.
- Future ideas require promotion before they become feature tasks.
