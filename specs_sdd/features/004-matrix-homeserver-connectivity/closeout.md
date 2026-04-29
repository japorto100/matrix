---
title: Matrix Homeserver, Connectivity and Mobile/Federation Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 004
---

# Closeout

## Built

- Tuwunel v1.6.0 is the documented Linux/podman homeserver baseline.
- Static config parse passes for `homeserver/tuwunel.v1.6.toml`.
- Federation-off, presence, upload-size, `.well-known`, LiveKit RTC transport
  and appservice-registration strategy are documented.
- `exec-blocking` C1-C6 are classified into external blockers, deferred
  deployment work or owning SDD features.

## Not Built

- No live homeserver startup proof in this pass.
- No mobile Element X / tunnel proof in this pass.
- No federation deployment runbook is active because current deployment remains
  private/dev.

## Deviations From Plan

- Dendrite/Zendrite remains historical fallback only.
- Keeping the 100 MB upload cap is intentional for Cloudflare alignment even
  though Tuwunel #411 is upstream-fixed.

## Verify Result

- PASS: Tuwunel TOML parses.
- PASS: compose default image points at Tuwunel v1.6.0.
- PASS: external/deferred blockers have feature ownership and review triggers.

## Live Verify Result

Deferred per current work order.

## Follow-Ups

- Monthly/upstream monitor remains active.
- Pull/restart the Tuwunel container during live/operator verify if an older
  image is still running.
