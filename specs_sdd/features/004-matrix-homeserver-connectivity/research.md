---
title: Homeserver Connectivity Static Classification
status: documented
owner: filip
created: 2026-04-25
updated: 2026-04-25
migrated_from:
  - specs/execution/exec-blocking.md
  - specs/execution/exec-matrix-monitor.md
  - specs/01-homeserver.md
  - specs/07-mobile.md
  - specs/11-bore-tunnel.md
  - specs/12-connectivity.md
---

# Homeserver Connectivity Static Classification

## Current Baseline

- Primary homeserver: Tuwunel v1.6.0 via `docker-compose.yml`.
- Active config: `homeserver/tuwunel.v1.6.toml`.
- Private/dev deployment: federation disabled.
- Mobile/external access path: Cloudflare quick tunnel or named tunnel, only
  when mobile scope is intentionally active.
- Calls path: MatrixRTC `.well-known` points at the LiveKit JWT service.
- TURN/STUN: public metered.ca/openrelayproject dev credentials plus coturn
  compose profile for production-like calls tests.

## `exec-blocking` C1-C6 Classification

| ID | Classification | Owner | Next Review |
|---|---|---|---|
| C1 MSC3414/MSC4362 encrypted state events | `blocked_external` | Feature 004 / Feature 005 | On Tuwunel or Matrix spec-support update. |
| C2 OIDC/MAS auth | `blocked_external` | Feature 004 | On Tuwunel MAS support or porting target decision. |
| C3 Federation + prod security runbook | `deferred_until_deployment` | Feature 004 / Feature 013 | When a real domain/DNS/TLS/federation decision exists. |
| C4 Multi-agent E2EE scaling decision | `moved_to_feature:006` | Feature 006 | When multi-tenant/compliance requirements appear. |
| C5 Tuwunel v1.6 upstream bugs | `active_monitoring` | Feature 004 | Monthly and on every Tuwunel release. |
| C6 Account provisioning / BYOS / multi-account | `deferred_backlog` | Feature 004 / Feature 005 | After Matrix Chat live verify and OIDC/MAS decision. |

## Static Config Findings

- `homeserver/tuwunel.v1.6.toml` parses as TOML.
- `address = "0.0.0.0"` supports LAN/mobile/tunnel exposure.
- `allow_federation = false` matches the private/dev baseline.
- `allow_local_presence = true`; incoming/outgoing federation presence is off.
- `max_request_size = 104857600` keeps the Cloudflare free-plan cap.
- `[global.well_known]` exists for client/server discovery.
- `[[global.well_known.rtc_transports]]` advertises LiveKit when calls are
  active.
- Appservice auto-load remains intentionally avoided because dynamic
  registration via `scripts/register-appservice.sh` is the documented workaround.

## Historical Fallback Notes

Dendrite/Zendrite material remains historical fallback context from the Windows
phase. It is not the active Linux-first homeserver path and should not create
new implementation work unless Tuwunel becomes unavailable for the target scope.
