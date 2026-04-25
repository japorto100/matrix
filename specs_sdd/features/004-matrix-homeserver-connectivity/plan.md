---
title: Matrix Homeserver, Connectivity and Mobile/Federation Plan
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 004
migrated_from:
  - specs/01-homeserver.md
  - specs/07-mobile.md
  - specs/11-bore-tunnel.md
  - specs/12-connectivity.md
  - specs/execution/exec-matrix-monitor.md
  - specs/execution/exec-blocking.md
adrs: []
---

# Plan

## Architecture

This feature owns external Matrix runtime assumptions: homeserver, tunnel,
mobile, federation, OIDC/MAS and upstream blocker monitoring.

## Critical Files

- `homeserver/tuwunel.toml`
- `homeserver/tuwunel.prod.toml`
- `homeserver/dendrite.yaml`
- `docker-compose.yml`
- `.well-known` related config and routes
- `specs/execution/exec-matrix-monitor.md`

## Migration Strategy

1. Convert current decisions into accepted baseline.
2. Move upstream blocker tracking into tasks/live-verify.
3. Keep monthly monitor items separate from local implementation work.

## Risks

- External blockers being misread as local TODOs.
- Mobile/federation assumptions drifting from current Tuwunel behavior.

