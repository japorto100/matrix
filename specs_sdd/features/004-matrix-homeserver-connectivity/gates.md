---
title: Matrix Homeserver Connectivity Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 004
---

# Gates

## Local Homeserver

- [x] Tuwunel starts locally under the selected image/config.
- [x] Current image/tag is stable v1.6.0 or intentional alternative.
- [ ] Appservice registration loads. Blocked by stale local Alice/Bob
  credentials in the persisted Tuwunel dev volume.
- [ ] URL-preview disablement is confirmed in active config. Owned jointly with
  Feature 013.
- [x] Media/upload config matches active Cloudflare/Tuwunel limits.

## Connectivity / Mobile

- [x] `.well-known/matrix/client` works locally.
- [ ] HTTPS tunnel/domain path works for Element X. Deferred to live/mobile verify.
- [x] MatrixRTC/LiveKit transport is configured in `.well-known` when calls are active.
- [ ] TURN/STUN config is tested or marked deferred. Deferred to live/calls verify.

## Federation / Prod

- [x] Federation remains off for private/dev deployment.
- [ ] If federation is promoted: DNS SRV or `.well-known/matrix/server`,
  HTTPS, anti-spam, ACLs and invite policy are specified.
- [x] OIDC/MAS remains blocked or has a concrete target.

## Upstream Monitor

- [x] Tuwunel v1.6 stable migration actions are checked.
- [x] Upstream-fixed workarounds are reviewed for removal.
- [x] MSC3414/MSC4362 encrypted state events remain blocked until supported.
- [x] MSC2246 async upload is tested only with a supporting client.

## Static Evidence

Checked on 2026-04-25:

- `tomlq . homeserver/tuwunel.v1.6.toml` -> PASS
- `docker-compose.yml` default image resolves to
  `ghcr.io/matrix-construct/tuwunel:v1.6.0`
- `homeserver/tuwunel.v1.6.toml` sets `allow_federation = false`
- Active config does not currently prove URL-preview disablement; example files
  expose the allowlist knob. Feature 013 owns the SSRF posture and must confirm
  active dev/prod config before this gate closes.
- `max_request_size = 104857600` aligns with the Cloudflare 100 MB request cap.
- `[global.well_known]` and `[[global.well_known.rtc_transports]]` are present.

## 2026-04-30 Added Gates

- [ ] Disposable Tuwunel QA lane provisions driver/SUT/observer users and
  cleans up with bounded timeout.
- [ ] Matrix account-state diagnostics distinguish default and named accounts.
- [ ] E2EE startup verification and backup health are surfaced as
  connectivity blockers.
- [ ] Crypto/sync state migration refuses mutation without a recovery snapshot.
