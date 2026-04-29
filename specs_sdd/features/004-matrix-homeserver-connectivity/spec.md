---
title: Matrix Homeserver, Connectivity and Mobile/Federation
status: active_monitoring
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

# Matrix Homeserver, Connectivity and Mobile/Federation

## Current State / Ist

Tuwunel is the primary homeserver path, with Zendrite/Dendrite as fallback
history for Windows-native dev. Connectivity, mobile and federation docs exist,
but several items are upstream- or deployment-dependent. The monitor exec tracks
Tuwunel v1.6, MSC3414/MSC4362, OIDC/MAS, federation readiness, MSC2246 async
upload and known upstream bugs.

Static config classification is documented in `research.md`. The current config
is Tuwunel v1.6.0, private/dev federation-off, Cloudflare-compatible 100 MB
upload cap, `.well-known` client/server discovery and LiveKit RTC transport.

## Target State / Soll

Homeserver and connectivity decisions are clear enough that Matrix chat, mobile
and appservice/E2EE work can be verified against one expected runtime shape.

## Subfeatures

- Tuwunel/Dendrite baseline
- Tunnels and external access
- Mobile `.well-known` and Element X verification
- Federation readiness
- OIDC/MAS decision tracking
- Upstream Matrix/Tuwunel blocker monitor
- MatrixRTC/LiveKit `.well-known` and TURN/STUN
- Media/upload limits and client-dependent gates

## Gap

- Some blockers belong in a monthly monitor, not active implementation tasks.
- Mobile and federation gates need live environment evidence.
- Tuwunel v1.6 stable is the compose default; a running old container still
  needs pull/restart during live/operator verify.
- Upstream-fixed workarounds are tracked; removing the Cloudflare-sized upload
  cap is not useful until an active large-upload test scope exists.

## Verify

- Tuwunel starts under the selected compose profile. Deferred to live verify.
- Mobile `.well-known` flow is verified when mobile scope is active. Deferred to live verify.
- [x] Upstream blockers are marked `blocked_external` rather than open local work.

## Closeout Criteria

- This feature may never fully close while upstream monitoring remains useful.
  It can close only as a release-scope feature once deployment assumptions settle.
