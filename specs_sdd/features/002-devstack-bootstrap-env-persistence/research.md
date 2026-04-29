---
title: Devstack Env Layout Rationale
status: documented
owner: filip
created: 2026-04-25
updated: 2026-04-25
migrated_from:
  - docs/superpowers/findings/2026-04-24-env-layout-decision.md
  - specs/05-devstack.md
  - specs/execution/archive/exec-19-devstack-consolidation.md
---

# Devstack Env Layout Rationale

## Decision

Keep env files scoped by runtime boundary:

- root `.env` for compose interpolation only,
- `frontend_merger/.env.local` for Next.js/BFF/browser-exposed settings,
- `go-appservice/.env.development` for Matrix gateway, appservice, storage and
  Go-side secrets,
- `python-backend/.env` or `.env.development` for agent, bridge, memory, LLM and
  Python-side service settings.

## Why

This prevents cross-runtime leakage:

- Frontend `NEXT_PUBLIC_*` values are intentionally browser-readable; secrets
  must not drift there.
- Go owns appservice tokens, storage credentials, signed-URL secrets and gateway
  control-plane env.
- Python owns LLM provider keys, agent runtime settings, NATS bridge settings
  and memory/context flags.
- Compose only needs container-level defaults and profile-specific settings.

## Current Static Evidence

Checked on 2026-04-25:

- `.env.example`
- `frontend_merger/.env.example`
- `go-appservice/.env.example`
- `python-backend/.env.example`
- `python-backend/ingestion/.env.example`

`podman compose -f docker-compose.yml config` parses under the current local
podman-compose provider.

## ADR Status

No ADR yet. This is operationally binding through Feature 002 and
`constitution.md`, but it can be promoted to ADR if future code starts depending
on automatic env generation or validation.
