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

- [ ] Tuwunel starts under selected profile. Deferred to live/operator verify.
- [x] Current image/tag is stable v1.6.0 or intentional alternative.
- [ ] Appservice registration loads. Deferred to live/operator verify.
- [ ] URL-preview disablement is confirmed in active config. Owned jointly with
  Feature 013.
- [x] Media/upload config matches active Cloudflare/Tuwunel limits.

## Connectivity / Mobile

- [ ] `.well-known/matrix/client` works when mobile scope is active. Deferred to live/mobile verify.
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
