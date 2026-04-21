# exec2-03c: Cinny-Pattern-Uebernahme in frontend_merger

**Datum:** 2026-04-19
**Status:** Implementierung abgeschlossen (sota-verify PASS nach Blocker-Fix)
**Plan:** `/home/lipfi2/.claude/plans/async-twirling-pixel.md`
**Scope-Nachfolger zu:** exec2-03 (UI-Rework), exec2-03b (Advanced Options), exec2-04 (Verify-Gates Section L)

---

## Context

Cinny (github.com/cinnyapp/cinny, AGPL-3.0) wurde als git-submodule unter `matrix/_ref/cinny` aufgenommen und mit GitNexus indiziert (787 Files, 3197 Nodes, 2750 Embeddings). Ziel **nicht** Code-Kopie (AGPL-Konflikt), sondern **selektive Pattern-Uebernahme**.

Zwei parallele GitNexus-Deep-Scans (Cinny + unser matrix-Repo) haben den Scope gegenueber der ersten File-Tree-Analyse verschoben: einige Cinny-Patterns **erweitern** bestehende Implementierungen (useCrossSigning QR/SAS existiert, MatrixChat Sync-Banner existiert, MessageComposer Upload-Skeleton existiert), andere sind echte Luecken (FeatureCheck, useCommands, useAccountData, JoinBeforeNavigate, SecretStorage, BackupRestore).

**Contrarian-Review (sota-contrarian, stakes=high)** hat 3 blocking Amendments gefunden:
1. `client.ts` E2EE-silent-fail war aktiv — musste zu hard-fail umgebaut werden
2. `secretStorageKeys` + `cryptoCallbacks`-Integration fehlte — Pre-Task vor B2 noetig
3. Tier-C scope 8h unrealistisch — 6 zusaetzliche Hook-Dependencies entdeckt

Alle drei wurden vor Implementation adressiert.

---

## Was umgesetzt wurde

### Phase 0b — E2EE-Hardening (Contrarian Amendment 1, CRITICAL)

**File:** `frontend_merger/src/features/matrix/lib/client.ts`

Der `catch`-Block in `getMatrixClient` (ca. L59-61) hat `initRustCrypto`-Fehler stumm geschluckt und den Client mit deaktivierter E2EE weiterlaufen lassen. **Security-Risiko**: User in Firefox-Strict / Tor / WASM-gesperrten Environments postet unverschluesselt ohne Warnung.

**Fix**:
- Neuer `NEXT_PUBLIC_E2EE_REQUIRED` env-var, **Default `true`** (opt-in-down, nicht opt-in-up)
- WASM-unavailability wird mit deutscher Klartext-Fehlermeldung differenziert
- `_client.stopClient()` + `_client = null` vor throw (verhindert stale-Singleton-Return beim naechsten Call)
- Nur explizites `NEXT_PUBLIC_E2EE_REQUIRED=false` laesst den graceful-fallback-Pfad weiterleben — fuer Dev/Bot-Accounts wo E2EE nicht gebraucht wird

**Dokumentiert in:** `frontend_merger/.env.example:42-47`

### Pre-Task B — secretStorageKeys + cryptoCallbacks (Contrarian Amendment 2, CRITICAL)

**Neue File:** `frontend_merger/src/features/matrix/lib/secretStorageKeys.ts`

Eigene TypeScript-Implementation (nicht Copy von Cinny's `secretStorageKeys.js`). AGPL-Boundary-Disziplin: unabhaengige Identifier (`rememberSecretStorageKey`, `forgetAllSecretStorageKeys`, `getRememberedKeyCount` statt Cinny's `storePrivateKey`, `clearSecretStorageKeys`, etc.), anderer Kontrollfluss (for-loop mit direktem get vs. Cinny's `.find(hasPrivateKey)`-Chain), eigene Kommentierung.

**Integration**: `cryptoCallbacks` wird jetzt an `createClient({ cryptoCallbacks })` uebergeben (`client.ts:46`). Ohne diesen Layer haetten B2/C1/C2 alle runtime-failure weil `bootstrapSecretStorage()` und `bootstrapCrossSigning()` ueber `CryptoCallbacks.getSecretStorageKey` den Recovery-Key abfragen. SDK 41.2 JSDoc bestaetigt: *"result in a call to CryptoCallbacks.getSecretStorageKey"*.

### Tier A — Utilities (6 Features)

| # | Deliverable | File | Zweck |
|---|---|---|---|
| A1 | `checkIndexedDBSupport` + `FeatureCheck` Wrapper | `lib/featureCheck.ts` + `components/FeatureCheck.tsx` | Wrappt `MatrixLoader` — verhindert silent-fail bei Private-Browsing / deaktiviertem IDB. Fallback-UI mit MDN-Link. |
| A2 | `verifiedDevice` Helper | `lib/matrix-crypto.ts` | 12-Zeilen-Wrapper um `CryptoApi.getDeviceVerificationStatus` → `crossSigningVerified`. Baustein fuer Send-Decisions. |
| A3 | `useAlive` Hook | `lib/hooks/useAlive.ts` | Mount-Race-Guard fuer async-Flows. Genutzt in A4, A6, B2, C0, C1, C2. |
| A4 | `useAccountData` + `useAccountDataCallback` | `lib/hooks/useAccountData.ts` | Gateway-Hook fuer reactive `m.account_data` Events. Mit `try/catch` um `getAccountData()` und Re-Sync bei eventType-Change (Contrarian-Fix). |
| A5 | `useCommands` Slash-Command-Parser | `lib/hooks/useCommands.ts` | `/me`, `/shrug`, `/tableflip`, `/unflip`, `/kick`, `/ban`, `/unban`, `/invite`, `/plain`, `/html`. Integriert in `MessageComposer.send` (nur im freien Send-Modus, nicht in Edit/Reply/Thread). |
| A6 | `JoinBeforeNavigateDialog` | `components/JoinBeforeNavigateDialog.tsx` | Preview-Dialog mit Avatar/Name/Topic/Member-Count/Join-Rule via `client.getRoomSummary`. Schuetzt vor versehentlichen Joins. |

### Tier B — Extensions (3 Features)

| # | Deliverable | File(s) | Erweitert |
|---|---|---|---|
| B1 | `SplashScreen` | `components/SplashScreen.tsx` + `MatrixChat.tsx:207-216` | Ersetzt frueheren inline-Loader (`Loader2 + "Verbinde mit Matrix…"`) durch Brand-Polished Component mit optional detail-text. |
| B2 | `ManualVerification` + Integration | `components/ManualVerification.tsx` + `CrossSigningSetup.tsx` | Neuer **Passphrase/Recovery-Key-Pfad** als Alternative zum bestehenden QR/SAS-Flow. Guard gegen aktive QR/SAS-Session (`otherFlowActive`). Integration: "Passphrase"-Button im needs_verification-Banner. |
| B3 | `useUploadQueue` + `UploadQueueBar` | `lib/hooks/useUploadQueue.ts` + `components/composer/UploadQueueBar.tsx` + `MessageComposer.tsx` | Single-File pendingFile-State → Multi-File-Queue. Drag-Drop auf Container, Per-File Progress, Retry bei Fehler, Cancel pro Item. URL-Leak-Fix in `clearDone()` (Contrarian-Finding). |

### Tier C — E2EE-Recovery (3 Features)

**Plan-Deviation**: statt 6 Sub-Hooks (useKeyBackupInfo/Status/Sync/Trust + useRestoreBackupOnVerification + Progress-Atom) **ein konsolidierter Hook** `useKeyBackup`. Gruende: (1) unser React-Query-Pattern ist React-Query-Cache-based, nicht jotai-Atom-based; (2) alle Sub-Hooks brauchen dieselbe `CryptoApi`-Handle; (3) weniger Boilerplate.

| # | Deliverable | File | Zweck |
|---|---|---|---|
| C0 | `useKeyBackup` (konsolidiert) | `lib/hooks/useKeyBackup.ts` | `info`, `trust`, `activeVersion`, `restoreProgress`, `refresh`, `enable`, `reset`, `restoreWithPassphrase`, `restoreWithCachedKey`. Reactive via `CryptoEvent.KeyBackupStatus`-Listener (Contrarian-Fix). |
| C1 | `SecretStorage` Setup-UI | `components/SecretStorage.tsx` | 4S-Bootstrap-Flow: Passphrase → `createRecoveryKeyFromPassphrase` → `bootstrapSecretStorage({setupNewSecretStorage, setupNewKeyBackup})` → Recovery-Key-Display (Copy + Download). Warnung bei `alreadySetup=true`. |
| C2 | `BackupRestore` UI | `components/BackupRestore.tsx` | Status-Panel + Restore-Flow via Passphrase mit Progress-Bar. **Feature-gated** per `NEXT_PUBLIC_CINNY_TIER_C=true` (Default `false` — Rollback-Safety). |

**Integration**: SecretStorage- und BackupRestore-Trigger-Buttons in `CrossSigningSetup.tsx` (Recovery-Actions-Leiste unterhalb des Banners).

---

## Entscheidungen die vom urspruenglichen Plan abwichen

1. **6 Sub-Hooks → 1 konsolidierter `useKeyBackup`**: statt `useKeyBackupInfo/Status/Sync/Trust/RestoreBackupOnVerification + Progress-State` als getrennte Hooks, eine kombinierte Return-API. Cinny's Split war jotai-motiviert, fuer unser React-Query-Pattern nicht passend. Scope-Reduktion, ca. 4h eingespart.

2. **A5 (useCommands) parallel statt phase-sequentiell**: Contrarian Amendment 4 — A5 blockt B/C nicht und kann parallel gebaut werden.

3. **Tier-C als Full-Scope trotz 16-20h Realitaet**: User hat Scope-Extension explizit akzeptiert.

4. **BackupRestore Feature-Flag als Rollback-Safety** (Contrarian nicht-blocking): `NEXT_PUBLIC_CINNY_TIER_C` env-var, default `false`. SecretStorage laeuft ohne Flag weil weniger risky (Setup-only, kein Restore-State-Mutation).

---

## Contrarian-Findings und wie adressiert

### Blocking (vor Implementation behoben)
- **Amendment 1 (E2EE silent-fail)**: `client.ts:49-95` komplett umgebaut zu hard-fail mit env-var-opt-out.
- **Amendment 2 (cryptoCallbacks fehlt)**: `secretStorageKeys.ts` erstellt, in `createClient` integriert.
- **Amendment 3 (Tier-C scope unterschaetzt)**: Sub-Task-Expansion dokumentiert, realistische Est 16-20h akzeptiert.

### Non-Blocking (nach Implementation via sota-verify behoben)
- **useCommands Dead Code** → integriert in `MessageComposer.send` vor normalem Send, respektiert Edit/Reply/Thread-Modes.
- **SecretStorage/BackupRestore ohne Consumer** → Buttons in `CrossSigningSetup.tsx` (Passphrase einrichten + Backup verwalten).
- **useAccountData stale bei eventType-Change** → `useEffect` re-syncted initial-state zusaetzlich zum Listener.
- **clearDone() URL-Leak** → Object-URLs werden vor dem Filter revoziert.
- **useKeyBackup ohne CryptoEvent-Listener** → `CryptoEvent.KeyBackupStatus` subscribed fuer automatische Refreshes.

---

## Verifikation

Alle Gates grün (2026-04-19):
- `bun run typecheck` — `$ tsc --noEmit` ohne Output
- `bun run lint` — `Checked 326 files. No fixes applied.`
- `bun run build` — Next.js 16.2.2 Build erfolgreich, 16 Routen generiert
- `sota-verify` Verdict: **PASS** nach Blocker-Fix (ursprüngliche Runs: PARTIAL wegen Consumer-Missing, nach Wiring-Fix PASS)
- GitNexus `analyze --embeddings` reindex: läuft (BG)

---

## Cross-Reference zu bestehenden Specs

### exec2-03b B3 (E2EE Key Management UI) — teilweise technisch enabled

exec2-03b Phase B3 listet: „Security Key anzeigen/exportieren", „Key Backup import/export", „Cross-Signing Verification Flow (QR + SAS)", „Neuen Key generieren".

- **QR+SAS-Flow**: ✓ bereits vorhanden aus exec2-03 (`useCrossSigning.ts`). Nicht Scope dieses Specs.
- **Passphrase-Fallback** → Tier-B2 `ManualVerification` liefert das. ✓
- **Security Key anzeigen/exportieren** → Tier-C1 `SecretStorage` Display + Copy + Download (48-Char Recovery-Key). ✓
- **Key Backup import/export** → Tier-C2 `BackupRestore` Setup + Restore via Passphrase. ✓ (feature-flag-gated)
- **Neuen Key generieren** → Tier-C1 `SecretStorage` mit `setupNewSecretStorage=true`. ✓

**Kein Supersede**: exec2-03b B3 umfasst die vollstaendige **Settings-UI-Integration** (Buttons in control-ui Settings-Tab). Dieser Spec liefert die **technische Basis und einzelne Dialog-Komponenten** dafuer — die Settings-Page-Komposition bleibt B3-eigener Scope.

### exec2-03 UI-Rework-SOTA — unveraendert

Alle Phasen der UI-Rework-Serie bis 13.04.2026 bleiben abgeschlossen. Cinny-Port baut auf diesem Fundament auf (nutzt Tiptap-Composer, useMatrixRTCCall, SlidingSync, etc.).

### exec2-04 Verify-Gates — erweitert

Neue Section **L. Cinny-Integration Gates** (L1-L11) hinzugefuegt — siehe `exec2-04-verify-gates.md`.

---

## Bekannte Grenzen / Follow-Ups (Phase 1 Tier A/B/C)

1. **Settings-UI-Integration**: SecretStorage + BackupRestore werden aktuell nur im Cross-Signing-Banner getriggert (nur sichtbar bei `state=needs_verification`). Fuer laufende Setups braucht es einen Settings-Tab-Entry (exec2-03b B3 Scope).

2. **Tier-C-Feature-Flag**: `NEXT_PUBLIC_CINNY_TIER_C=false` default waehrend Dev. Aktivieren nach End-to-End-Browser-Test mit echtem Homeserver.

3. **A5 /html und /plain**: aktuell nur Pass-through auf bodyebene. Fuer echte HTML-Force (via `sendHtmlMessage`) muesste `MessageComposer.send` den `formatted_body` override explizit respektieren. Pass-through ist simpler und deckt 90% der Anwendungsfaelle.

4. **Singleton-Pattern in client.ts** (pre-existierend, nicht durch diesen Spec verursacht): `let _client = null` ist Next.js-16 Fast-Refresh-unsicher. Workaround: Full-Reload statt HMR bei Crypto-Debugging.

5. **AGPL-Disziplin**: Keine Cinny-Files wurden kopiert. Patterns wurden als Referenz gelesen, Code unabhaengig reimplementiert. Fuer zukuenftige Cinny-Pattern-Uebernahmen dieselbe Disziplin (Identifier, Kontrollfluss, Kommentare eigenstaendig).

---

## Phase 2 Vollausbau (Tier D/E/F/G) — 2026-04-19

Nach Phase 1 (Tier A/B/C) folgte der **Spaces/Settings-Vollausbau**: 20 weitere Tasks in den Tiers D (UI-Enhancements), E (Spaces), F (Features), G (Settings-Architektur). Die 7 Contrarian-Amendments aus `sota-contrarian` wurden alle eingearbeitet.

### Scope-Zusammenfassung

**Phase 1 Foundation** (6 Tasks): F0 AsyncSearch-Utility, F2 useCapabilities, G1-scaffold RoomInfoPanel-Tabs (Info/Members/Notifications/Admin/Advanced), G2-scaffold SpaceSettings-Tabs (General/Members/Rooms/Permissions), D1 Space-Unread-Aggregation-Badge, D7 Leave-Confirm als shared-Component.

**Phase 2 Notifications** (3 Tasks): D2 RoomNotificationMode (pure helpers + useRoomNotificationMode + RoomNotificationSwitcher, 4-state Unset/All/Mentions/Mute), D5 Mark-as-Read+Mute-Dropdown im RoomItem-Context-Menu inkl. DropdownMenuSub, G4 RoomNotificationsTab-Content direkt in G1-Tab (kein intermediate Dead-Code).

**Phase 3 Members+Media** (2 Tasks): D4 MemberList mit AsyncSearch + Sort-Dropdown (Power/Name/UserId) + @tanstack/react-virtual ab 30 Mitgliedern, D6 SharedMedia + MediaLightbox Full-Screen-Modal mit Download + Open-in-new-tab.

**Phase 4 Admin+Encryption** (2 Tasks): D8 RoomAdminExtensions mit Join-Rule-Select, History-Visibility-Select, Aliases-Manager (create/delete), Room-ID-Copy. G6 EncryptionSection mit Doppel-Confirm (checkbox-gated) vor dem IRREVERSIBLEN Enable.

**Phase 5 App-Settings** (2 Tasks): G5 useDevices + DevicesTab mit Verify-Badge (cross-signed/unverified), Last-Seen, Logout-Other-Sessions. G3 AppSettingsSheet (shadcn Sheet) mit 5 Tabs (Account/Appearance/Notifications/Devices/About), Trigger ueber "Einstellungen"-Button im UserProfileDialog (Contrarian-Amendment #2).

**Phase 6 Spaces** (5 Tasks): E5 InviteUsersToSpaceDialog mit searchUserDirectory + Multi-Select, E4 Suggested-Rooms-Flag in useSpaces (liest m.space.child.suggested), E3 Sub-Spaces-Data-Model (nur type-update, UI-nested-rendering deferred), F1 AddRoomToSpaceDialog virtualisiert mit Multi-Select-Checkboxes, E1 SpaceLobby mit default-collapsed-State (Contrarian-Amendment #3) + max 5 Hierarchy-Rows mit Expand + Hero-Card + Invite-Button.

**Deferred zu naechstem Sprint**:
- E2 Sidebar DnD-Reorder (braucht `@atlaskit/pragmatic-drag-and-drop` Dep + Element-Web-Event-Type-Recherche fuer cross-client-Kompatibilitaet)
- D3 RoomList-Categories (groesserer Refactor mit globalem flat-Virtualizer, eigene Iteration)

### Contrarian-Amendments Implementation-Status

| # | Amendment | Status |
|---|---|---|
| Crit #1 | G1/G2 Tab-Scaffolds in Phase 1 | ✓ |
| Crit #2 | G3-Trigger via ProfileDialog-Link (nicht Avatar-Click) | ✓ |
| Major #3 | E1 Lobby default collapsed + max 5 rows | ✓ |
| Major #4 | D2 beide Callers (RoomInfoPanel + DMInfoPanel) | ⚠ **teilweise** — RoomInfoPanel useMuteRoom-Import-Zombie entfernt, DMInfoPanel-Migration auf useRoomNotificationMode deferred (funktional unveraendert via kompatiblem useMuteRoom-Wrapper) |
| Major #5 | G4 direkt in G1-Tab (kein Dead-Code) | ✓ |
| Major #6 | E2 DnD-Event-Type-Entscheidung | DEFERRED mit E2 |
| Major #7 | D3 globaler flat-Virtualizer | DEFERRED mit D3 |

### Sota-Verify Run #1 Ergebnis

**Verdict: PARTIAL** — alle drei Gates (typecheck/lint/build) gruen. 3 Non-Blocker-Findings:

1. **RoomInfoPanel useMuteRoom Zombie-Import** — gefixt in 8b (`bun run lint` Warnings 6→4)
2. **G1 Tab-Switch editingName/editingTopic State-Reset fehlte** — gefixt in 8b (onValueChange-Handler auf Tabs)
3. **DMInfoPanel useMuteRoom nicht auf useRoomNotificationMode migriert** — als Follow-up dokumentiert (funktional unveraendert, semantic-gap non-blocking)

### Neue Files (Phase 2)

- `lib/asyncSearch.ts` (F0)
- `lib/notificationMode.ts` (D2 pure helpers)
- `lib/hooks/useCapabilities.ts` (F2)
- `lib/hooks/useRoomNotificationMode.ts` (D2 hook)
- `lib/hooks/useDevices.ts` (G5)
- `components/RoomNotificationSwitcher.tsx` (D2 UI)
- `components/AppSettingsSheet.tsx` (G3)
- `components/app-settings/AccountTab.tsx` + `AppearanceTab.tsx` + `NotificationsTab.tsx` + `DevicesTab.tsx` + `AboutTab.tsx` (G3 Tabs)
- `components/shared/LeaveRoomConfirm.tsx` (D7)
- `components/room-info/MediaLightbox.tsx` (D6)
- `components/room-info/RoomNotificationsTab.tsx` (G4)
- `components/room-info/RoomAdminExtensions.tsx` (D8)
- `components/room-info/EncryptionSection.tsx` (G6)
- `components/spaces/SpaceLobby.tsx` (E1)
- `components/spaces/InviteUsersToSpaceDialog.tsx` (E5)
- `components/spaces/AddRoomToSpaceDialog.tsx` (F1)

### Modifizierte Files (Phase 2)

- `components/room-info/RoomInfoPanel.tsx` — G1-Tab-Refactor (5 Tabs), D4/D6/D8/G4/G6 in Tab-Slots, Zombie-Import-Fix, Tab-Switch-State-Reset
- `components/room-info/MemberList.tsx` — D4 Search+Sort+Virtualization
- `components/room-info/SharedMedia.tsx` — D6 Lightbox-Integration + Download
- `components/spaces/SpaceSettings.tsx` — G2-Tab-Refactor (4 Tabs)
- `components/spaces/SpaceSelector.tsx` — D1 Unread-Badge + G3-AppSettings-Wiring
- `components/UserProfileDialog.tsx` — G3 "Einstellungen"-Link-Button im Footer
- `components/MatrixChat.tsx` — D1 useMemo Space-Unread-Aggregation + prop-pass
- `components/room-list/RoomItem.tsx` — D5 Context-Menu mit Mark-as-Read/Mute-SubMenu/Leave
- `lib/utils.ts` — aggregateSpaceUnread helper (D1)
- `lib/hooks/useSpaces.ts` — SpaceChildRoom um suggested/topic/avatarUrl erweitert (E3/E4)

### Phase 2 Gates (exec2-04 Section M)

Siehe `exec2-04-verify-gates.md` Section M (M1-M25) fuer Details.

---

## Phase 3 — Final Polish (2026-04-20)

Tier-H (Polish) — 4 reale UX-Items + Verify+Fix-Cycle. P0+P1+P2 geliefert, P3 (N5/N6/N7) bewusst skipped per Plan.

### Scope & Ergebnisse

**N1 AutoRestoreBackupOnVerification** (P0, E2EE-adjacent)
- Passive Listener-Component die nach erfolgreicher Verify (CryptoEvent.VerificationRequestReceived + phase=Done) automatisch `useKeyBackup.restoreWithCachedKey()` triggert. Auch Initial-Try beim Mount falls Backup schon trusted war.
- Dual-Guard (Contrarian #3): `useRef<boolean>` (sync) + `sessionStorage.matrix.autoRestoreDone` (cross-verify idempotency).
- File neu: `components/AutoRestoreBackupOnVerification.tsx`. Integration: Sibling in `MatrixChat.tsx` oberhalb CrossSigningSetup.
- UX-Win: nach QR-Scan mit Element X ist User ohne Extra-Klick fertig — alte Nachrichten werden im Hintergrund entschluesselt.

**N2 Cross-Room Message-Search** (P1)
- SearchPanel erweitert um Cross-Room-Toggle. Bei aktivem Toggle: `client.search({body: {search_categories: {room_events: {...}}}})` statt per-room. Results zeigen Room-Avatar + Sender + Message, Click navigiert via `matrix:navigate` Custom-Event.
- Encrypted-Rooms UX (Contrarian #4): `client.isRoomEncrypted()` filtert Rooms pre-search; Toggle wird disabled wenn alle encrypted (Tooltip); Results-Footer "X Raeume durchsucht, Y uebersprungen".
- Pagination via `next_batch` ("Mehr laden"-Button).
- File modifiziert: `components/SearchPanel.tsx`.

**N3 RoomList-Categories** (P1, ex-D3-deferred)
- Ersatz des 5-Tab-Filter-Systems durch 5 collapsible Sections: Einladungen / Favoriten / Personen / Raeume / Niedrige Prioritaet.
- Ein globaler flat-Virtualizer (Amendment #7) mit render-branching per item-type — NICHT per-Group-Virtualizer.
- Space-Filter Semantik (Amendment CRITICAL #2): Intersection auf `childRoomIds`, leere Gruppen ausgeblendet, kein separater Favorites-per-Space-Namespace.
- Keyboard-Nav skippt Group-Header via `navigableIndices`-Indirection.
- Collapse-State persistiert in `localStorage.matrix.roomList.collapsedGroups`.
- Files neu: `components/room-list/RoomGroupHeader.tsx` + `tests/roomlist-keyboard-nav.spec.ts` (Playwright minimal, skipped ohne MATRIX_* env-vars).
- Files modifiziert: `components/room-list/RoomList.tsx` (major refactor), `lib/types.ts` (+ `isLowPriority`), `lib/resolvers.ts` (m.lowpriority-Tag lesen), `lib/hooks/useRooms.ts` (Dirty-Check-Erweiterung).

**N4 Image-Editor Crop/Rotate** (P2)
- Modal vor Upload im Composer-Flow, mit Cropper aus `react-easy-crop` (~30KB, innerhalb Bundle-Budget).
- 4 Aspect-Ratios: 4:3 (Standard), 1:1, 16:9, 3:4. Rotate 90° Links/Rechts, Zoom-Slider. Save erzeugt neuen File<image/jpeg|png> via Canvas-Roundtrip.
- ObjectURL-Lifecycle (Contrarian #5): Editor-useEffect-Cleanup revoked URL; `replaceFile()` im useUploadQueue revoked alte preview-URL vor Ersatz.
- GIF-Detection: Edit-Button disabled mit Tooltip "Animated GIFs koennen nicht bearbeitet werden".
- Files neu: `components/composer/ImageEditor.tsx`. Files modifiziert: `components/composer/UploadQueueBar.tsx` (+ Crop-Button), `lib/hooks/useUploadQueue.ts` (+ `replaceFile`), `components/MessageComposer.tsx` (prop-wiring).
- Dep-Install: `bun add react-easy-crop` (5.5.7). Bundle-Delta < 50KB per post-install-Build-Diff (Amendment #7).

**DEFERRED (explicit, vom User bestaetigt)**
- Image-Pack Create-Flow fuer user-created Emojis (`im.ponies.user_emotes`) — 3-5h Aufwand, Nischen-Feature; Sticker-Rendering ist bereits via `StickerContent` verfuegbar.
- DMInfoPanel useMuteRoom → useRoomNotificationMode Migration — funktional identisch, 0 UX-Value.
- N5 E2 Sidebar-DnD-Reorder — pragmatic-drag-and-drop Dep, lokal-only Pattern; als Phase-4-Follow-up wenn echtes Nutzerbeduerfnis.
- N6 PPTX Preview (Download+Copy-URL-Fallback) — low-freq file type; triviale 30min Erweiterung wenn noetig.
- N7 Space-Members-Drawer — Cross-Room-Member-Aggregation; Nutzen erst bei Grossem-Space-Setup.
- Lobby-DnD zwischen Room-Categories — braucht N3+N5 als Vorarbeit.

### Workflow-Ergebnisse

- Plan: `/home/lipfi2/.claude/plans/async-twirling-pixel.md`
- sota-contrarian Run #1 → 7 Amendments (2 Critical, 2 Major, 3 Medium), alle eingearbeitet
- Implementation: P0 + P1 + P2 in einer Session
- sota-verify Run #1 → PARTIAL mit 2 realen Bugs:
  1. N2 Stale-Data-Race bei Toggle-Flip mid-flight → Fix via Request-Generation-Counter (`requestIdRef`) in SearchPanel; Counter-Invalidate im Toggle-Handler + post-await-Stale-Checks
  2. N4 "Frei"-Aspect-UX-Bug (Bedeutungs-Overlap mit 4:3) → Fix via strict AspectMode-Union ohne "free"; Select-Items mit klaren Labels ("4:3 Standard" / "1:1 Quadrat" / "16:9 Breitbild" / "3:4 Hochformat")
- sota-verify Run #2 → PASS, alle 3 Gates gruen (typecheck, lint mit 4 pre-existing warnings, build)

### Neue Files (Phase 3)

- `components/AutoRestoreBackupOnVerification.tsx` (N1)
- `components/composer/ImageEditor.tsx` (N4)
- `components/room-list/RoomGroupHeader.tsx` (N3)
- `tests/roomlist-keyboard-nav.spec.ts` (N3 Playwright minimal)

### Modifizierte Files (Phase 3)

- `components/MatrixChat.tsx` — N1 AutoRestoreBackup-Sibling
- `components/SearchPanel.tsx` — N2 Cross-Room-Toggle, Request-Generation-Counter
- `components/room-list/RoomList.tsx` — N3 Categories-Refactor (major)
- `components/composer/UploadQueueBar.tsx` — N4 Crop-Button + ImageEditor-Mount
- `components/MessageComposer.tsx` — N4 replaceFile-Prop-Wiring
- `lib/hooks/useUploadQueue.ts` — N4 `replaceFile(id, newFile)` + ObjectURL-Revoke
- `lib/hooks/useRooms.ts` — N3 isLowPriority im Dirty-Check
- `lib/resolvers.ts` — N3 m.lowpriority-Tag lesen
- `lib/types.ts` — N3 `isLowPriority?: boolean` an RoomInfo

### Phase 3 Dependencies

- `react-easy-crop@5.5.7` (neu, N4)

### Phase 3 Gates (exec2-04 Section N)

Siehe `exec2-04-verify-gates.md` Section N (N1-N4) fuer Details.

### Phase 3.5 — N5 + Lobby-DnD Nachschub (2026-04-20)

User-Nachreichung nach P0+P1+P2-Standard: **N5 Sidebar-DnD-Reorder + Lobby-DnD zwischen Categories** aus dem vorher deferred P3-Block.

**N5 Space-Order-Reorder**
- Space-Icons im SpaceSelector per pragmatic-drag-and-drop draggable + drop-target mit `attachClosestEdge`/`extractClosestEdge` (top/bottom).
- `useSpaceOrder`-Hook (`lib/hooks/useSpaceOrder.ts`): lokal-only via `localStorage.matrix.spaceOrder: string[]`, `mergeWithKnown` integriert neue Spaces am Ende.
- Einmaliger Toast "Reihenfolge nur auf diesem Geraet gespeichert." bei erstem Drop via `matrix.spaceOrderToastShown`-Flag.
- DnD-Data: `{type: "matrix.space-icon", spaceId}`. `DraggableSpaceItem`-Subcomponent fuer per-item useRef+useEffect-Scope.

**Lobby-DnD (Room-Items zwischen Categories)**
- RoomItem.tsx: draggable-Registrierung auf outer `<div>`, opacity-40 bei dragging.
- RoomGroupHeader.tsx: optional `groupId`-Prop → wenn gesetzt, dropTarget mit ring-highlight-visual.
- RoomList.tsx: `monitorForElements` haelt Tag-Mutation-Logik (setRoomTag/deleteRoomTag) und verwaltet Rooms-Ref (stale-closure-safe).
- Drop-Mapping: target=favourites → m.favourite+Toast; target=lowpriority → m.lowpriority+Toast; target=rooms/people → beide Tags entfernen; target=invites → no-op (groupId nicht durchgereicht).
- Same-Category-Guard verhindert unnoetige API-Calls bei Drop auf gleiche Kategorie.

### Phase 3.5 — Fixes (sota-verify Run #1 → PARTIAL)
1. **Invites-Drop-Target visual-vs-silent-skip** → Fix in RoomList.tsx: `groupId={item.groupId === "invites" ? undefined : item.groupId}` — Invites-Header bekommt gar nicht erst Drop-Target-Capability.
2. **Same-Category unnoetige API-Calls + irrefuehrender Toast** → Fix via `roomsRef` + `categorize(currentRoom) === targetGroup` early-return.

### Neue Files (Phase 3.5)
- `lib/hooks/useSpaceOrder.ts`

### Modifizierte Files (Phase 3.5)
- `components/spaces/SpaceSelector.tsx` — DraggableSpaceItem-Subcomponent + monitorForElements
- `components/room-list/RoomItem.tsx` — draggable-Hook
- `components/room-list/RoomGroupHeader.tsx` — optional dropTarget via `groupId`-Prop
- `components/room-list/RoomList.tsx` — monitorForElements + roomsRef + Tag-Mutation-Handler

### Phase 3.5 Dependencies
- `@atlaskit/pragmatic-drag-and-drop@1.8.0` + `-hitbox@1.1.0` + `-auto-scroll@2.1.5`

### Phase 3.5 Gates (in Section N)
Siehe Section N (N5 + N-Lobby) in exec2-04-verify-gates.md.
