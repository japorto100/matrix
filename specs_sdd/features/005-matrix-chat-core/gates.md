---
title: Matrix Chat Gate Ledger
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 005
migrated_from:
  - specs/execution/exec2-04-verify-gates.md
---

# Matrix Chat Gate Ledger

This is the semantic import of `exec2-04` gate sections A-O. Exact old gate
sections are preserved as SDD gate groups so `exec2-04` no longer needs to be
the operational source of truth once these are classified.

## A — Infrastructure

### A1 Homeserver

- Tuwunel starts with current config.
- New room uses room version 12.
- RocksDB direct I/O setting does not produce log errors.
- Backup directory exists after first start.
- Go appservice loads `.env.development` in development.
- No `changeme` placeholders remain in env files.

### A2 Sliding Sync

- Room list loads under target latency with 20+ rooms.
- Network shows simplified MSC3575 sync endpoint.
- Non-visible room event load is not excessive.

### A3 LiveKit + JWT Service

- LiveKit listens on 7880.
- JWT service listens on 8080.
- Tuwunel `.well-known` advertises RTC foci.

### A4 Env

- Matrix agent prefix is consistent in Go, frontend and env examples.
- JWT service URL is set for frontend calls.

## B — Auth + E2EE

### B1 E2EE Core

- Go OlmMachine loads.
- Keys upload to homeserver.
- Browser Rust crypto initializes.
- User send produces encrypted event.
- Reload uses IndexedDB without full resync.
- No key upload/token/decrypt errors in UI/logs.

### B2 Cross-Signing

- Seeds are created and reloaded.
- Agent device trust state is visible in Element X.
- Web banner/QR/SAS flows work and recover cleanly on abort.

### B3 Key Backup

- Backup password set.
- Megolm backup file updates.
- Appservice exports on stop.
- New deployment imports backup and can read old messages.

### B4 MSC4381

- Encrypted events omit deprecated `sender_key` and `device_id`.
- Browser and Element X can still decrypt.

## C — Chat Core

### C1 Messages

- Text send/receive.
- `formatted_body` renders allowed HTML.
- HTML is not wrongly re-parsed as Markdown.
- XSS and unsafe styles are blocked.

### C2 Message Actions

- Edit/react/delete/reply/forward visible.
- Edit banner/save/cancel works.
- Deleted messages have no actions.
- Element X interop works for edits/deletes.

### C3 Reactions

- Emoji picker opens/closes.
- Reaction event sends and renders.
- Element X shows reaction.

### C4 Read Receipts

- Room switch marks read.
- RoomList unread count clears.
- Read avatars appear.

### C5 Presence

- Local presence enabled.
- Online/offline dots update.

### C6 URL Previews

- URL preview card renders.
- Preview uses own token.
- Cache avoids duplicate fetch.

### C7 Mentions

- Own handle highlights.
- Bot messages show AI/Agent identity.
- Prefix changes are recognized by Go and frontend.

### C8 Location Content

- Matrix location events render OSM/Leaflet map.
- Element X interop remains to be verified.
- Agent Chat location integration belongs to Feature 007.

## D — Advanced Features

- D0: second-client basics: unread, read receipt, online, other-user bubbles,
  thread chip, read-by list, calls.
- D1: polls: create/vote/live results/Element X interop.
- D2: threads: side panel, reply count, routing, Element X interop.
- D3: media: images, thumbnails, legacy media off, video/audio, no 401s.

## E — WYSIWYG Composer

- Bold/italic/code formatted body.
- User/agent/room mentions and pills.
- Room links.
- Edit mode prefill.
- Reply/thread relation.
- Plain text emits plain Matrix event.

## F — MatrixRTC / LiveKit Calls

- F1 voice 1:1.
- F2 video 1:1.
- F3 group voice.
- F4 group video.
- F5 E2EE, RTC member keys, background blur, state cleanup.
- F6 Element X mobile interop.

## G — Navigation + Shortcuts

- Matrix permalinks.
- DM permalink.
- Arrow-up edit last message.
- Ctrl+K search.
- Esc close active panel.
- keyboard navigation in RoomList.

## H — Optional SOTA Packages

- Background blur.
- Performance fallback for blur.

## I — Connectivity + Tunnel

- Cloudflare quick tunnel first choice.
- Devstack tunnel summary and timeout behavior.
- HTTPS Matrix client versions through tunnel.
- Element X login/room/message through tunnel.
- Upload limits align with Cloudflare free plan.

## J — Tuwunel v1.6 RC / Storage Provider

- Pre-flight binary/config/ref backup.
- Smoke test without S3.
- Rollback to v1.5.
- S3 storage provider connection.
- Async upload MSC2246.
- Larger uploads blocked by upstream #411 until fixed.
- Upstream monitor items live in Feature 004.

## K — Config SOTA / Breaking Changes

- unknown config key enforcement.
- explicit prune/compression/encryption defaults.
- appservice `id` field.
- v1.5 -> v1.6 media path.
- startup order SeaweedFS before Tuwunel.
- persistent SeaweedFS bucket.
- WSL1 TCP timeout warning documented.

## L — Cinny Integration Tier A-C

Severity:

- critical: L8, L10, L11
- high: L1, L5, L6
- medium: L2, L3, L4, L7, L9

Gates:

- L1 FeatureCheck for IndexedDB/private browsing.
- L2 verifiedDevice helper.
- L3 useAlive unmount safety.
- L4 useAccountData reactive account data.
- L5 slash commands.
- L6 join-before-navigate dialog.
- L7 splash screen.
- L8 manual verification passphrase/recovery fallback.
- L9 upload queue multi-file/retry.
- L10 backup restore UI.
- L11 secret storage setup UI.

## M — Cinny Full Expansion

Includes:

- async search,
- capabilities,
- space unread aggregation,
- leave confirm,
- notification modes and mute submenu,
- mark as read,
- member list search/sort/virtualization,
- shared media lightbox,
- room info/settings tabs,
- devices,
- encryption enable double-confirm,
- admin extensions,
- invite users,
- suggested rooms,
- space lobby,
- add-existing room picker.

Deferred or alias:

- M23 DnD reorder originally deferred, later N5 covers sidebar reorder.
- M24 room categories covered by N3.

## N — Phase 3/3.5 Gates

- N1 auto-restore backup after verification.
- N2 cross-room message search.
- N3 room list categories and flat virtualizer.
- N4 image editor crop/rotate.
- N5 sidebar DnD reorder.
- N-Lobby room item DnD between categories.

Skipped for now:

- PPTX preview.
- Space members drawer.

## O — Architecture Decisions

### O1 Bridge Architecture

Decision: keep Bridge option C.

Meaning:

- Go appservice communicates with NATS.
- `python-backend/bridge/` translates NATS inbound to agent HTTP/SSE and back.
- Agent remains pure HTTP from frontend perspective.
- NATS remains buffer/transport for Matrix path.

Re-evaluate if bridge becomes reliability or latency bottleneck.

### O2 Agent Orchestration Topology

Target: single orchestrator agent per user, with internal subagents.

Current state:

- mention-based routing exists,
- `@agent-*` appservice namespace can support both current and target patterns,
- body parsing should eventually move out of appservice dispatcher logic.

### O3 Current Verify Scope

Current minimal production-readiness scope:

- bridge option C works,
- env loader loads `.env.development`,
- dynamic reply routing resolves `target_agent`,
- deeper orchestrator/subagent design is Feature 009 scope.

## Classification Required

Every gate above must be classified during migration as:

- `active`
- `done`
- `blocked_external`
- `deferred`
- `superseded`
- `moved_to_feature:<id>`

