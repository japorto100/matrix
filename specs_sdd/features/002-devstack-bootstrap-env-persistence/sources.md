---
title: Devstack Bootstrap Env Persistence Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 002
---

# Sources

| Source | Role in SDD |
|---|---|
| `specs/05-devstack.md` | Service list, startup order, compose profiles and verification commands. |
| `specs/execution/exec-linux-setup-users-2026-04-17.md` | Linux user/setup execution history. |
| `specs/execution/exec-secrets-bootstrap-2026-04-17.md` | SOPS/age encrypted master secret pattern and generated secrets. |
| `specs/execution/exec-postgres-tuning-2026-04-17.md` | Postgres tuning for local hardware. |
| `specs/execution/archive/exec-19-devstack-consolidation.md` | Archived consolidation history; split into current owner features. |
| `docs/superpowers/findings/2026-04-24-env-layout-decision.md` | Env layout decision: root env vs service env, secrets handling. |
| `AGENTS.md` machine instructions | SSD/HDD cache policy and preferred tooling on this host. |

## Adopted Into Matrix

- Linux devstack is the current operating target; Windows/PowerShell docs remain
  useful history and portability reference.
- SOPS/age master file is the intended safe secret bootstrap pattern.
- Postgres tuning must fit the 8GB RAM host.
- Hot build/runtime directories must not be moved to HDD.
