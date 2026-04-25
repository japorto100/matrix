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

- [ ] Tuwunel starts under selected profile.
- [ ] Current image/tag is stable v1.6.0 or intentional alternative.
- [ ] Appservice registration loads.
- [ ] URL previews remain disabled.
- [ ] Media/upload config matches active Cloudflare/Tuwunel limits.

## Connectivity / Mobile

- [ ] `.well-known/matrix/client` works when mobile scope is active.
- [ ] HTTPS tunnel/domain path works for Element X.
- [ ] MatrixRTC/LiveKit transport appears in `.well-known` if calls are active.
- [ ] TURN/STUN config is tested or marked deferred.

## Federation / Prod

- [ ] Federation remains off for private/dev deployment.
- [ ] If federation is promoted: DNS SRV or `.well-known/matrix/server`,
  HTTPS, anti-spam, ACLs and invite policy are specified.
- [ ] OIDC/MAS remains blocked or has a concrete target.

## Upstream Monitor

- [ ] Tuwunel v1.6 stable migration actions are checked.
- [ ] Upstream-fixed workarounds are reviewed for removal.
- [ ] MSC3414/MSC4362 encrypted state events remain blocked until supported.
- [ ] MSC2246 async upload is tested only with a supporting client.
