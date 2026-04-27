---
title: Matrix Homeserver, Connectivity and Mobile/Federation Live Verify
status: partial-local-live
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 004
---

# Live Verify

## Required Flows

- Start Tuwunel with current compose/profile.
- Confirm homeserver health endpoint or login discovery responds.
- Confirm appservice registration is accepted if appservice is in scope.
- Confirm tunnel URL reaches the homeserver if tunnel testing is in scope.
- Confirm Element X/mobile can discover the server via `.well-known`.
- Confirm federation is disabled or configured according to current scope.

## Blocked/External Checks

- MSC3414/MSC4362 state noted.
- OIDC/MAS state noted.
- Tuwunel upstream bugs state noted.

## Result

partial local backend/live pass; browser/mobile/federation gates are not closed.

## Local Evidence 2026-04-27

- `garage` was manually started after compose left it in `Created`; Garage
  health returned `Garage is fully operational`.
- `tuwunel` was manually started after storage was available. Tuwunel logs show
  v1.6.0 listening on `0.0.0.0:8448` and connected storage providers
  `garage` and `media`.
- `GET http://localhost:8448/_matrix/client/versions` returned Matrix versions
  through `v1.15` plus expected unstable feature flags.
- `GET http://localhost:8448/.well-known/matrix/client` returned local
  homeserver discovery and MatrixRTC LiveKit focus metadata.
- `./scripts/dev-stack.sh --tuwunel --storage=garage` timed out before manual
  recovery; this is tracked as a devstack orchestration/start-order issue, not
  as a Tuwunel runtime failure.
- `scripts/setup-users.sh` failed against the existing persisted Tuwunel volume:
  `@alice` and `@bob` exist but the expected dev passwords no longer match.
  Appservice admin-command registration therefore remains blocked until the
  persisted dev credentials are recovered or the Tuwunel dev volume is reset
  intentionally.
