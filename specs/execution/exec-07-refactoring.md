# exec-07: Matrix Chat UI Refactoring

**Datum:** 28.03.2026
**Status:** Abgeschlossen

---

## Warum

Die Matrix Chat UI (7.800 LOC, 24 Komponenten) ist organisch gewachsen:
- 5 Dateien >490 LOC (Message 1028, RoomInfoPanel 803, MessageComposer 634, MatrixChat 493, RoomList 492)
- 11x inline MXC URL Konvertierung statt `mxcToHttp()`
- 4 Duplikat-Muster: Mute-Toggle, Encryption-Badge, Avatar+Initials, Power-Level Checks
- Self-built UI statt shadcn/ui (Context-Menu, Tabs, Tooltips, Select, Input)
- types.ts mischt Interfaces + Utilities + Resolvers (404 LOC)

## Ergebnis

### Vorher → Nachher (groesste Dateien)

| Datei | Vorher | Nachher | Aenderung |
|---|---|---|---|
| Message.tsx | 1028 | 149 (+ 4 Subdateien: 752 total) | Aufgebrochen in message/ |
| RoomInfoPanel.tsx | 803 | 281 (+ 3 Subdateien: 562 total) | Aufgebrochen in room-info/ |
| RoomList.tsx | 492 | 125 (+ 2 Subdateien: 269 total) | Aufgebrochen in room-list/ |
| MatrixChat.tsx | 493 | 419 | Hooks extrahiert |
| DMInfoPanel.tsx | 369 | 325 | Hooks + EncryptionBadge |
| types.ts | 404 | 87 (+ utils 42 + resolvers 296) | Aufgesplittet |

### Neue Dateien

**lib/matrix/:**
- `utils.ts` — mxcToHttp, mxcToThumbnail, formatFileSize, hashColor
- `resolvers.ts` — resolveMessage, resolveRoom, isAgentUser
- `hooks/useMuteRoom.ts` — Mute-Toggle (aus RoomInfoPanel + DMInfoPanel)
- `hooks/usePinnedMessages.ts` — Pin State + Listener + canPin + togglePin
- `hooks/useRoomMembers.ts` — Member-Loading via API + SDK Fallback + roleLabel
- `hooks/useMessageActions.ts` — handleReact + handleRedact

**components/matrix/shared/:**
- `MatrixAvatar.tsx` — Wiederverwendbarer Avatar (MXC + Initials + Online-Dot)
- `EncryptionBadge.tsx` — Lock/LockOpen Badge (aus 3 Dateien dedupliziert)

**components/matrix/message/:**
- `Message.tsx` — Orchestrator (149 LOC)
- `MessageActions.tsx` — Hover-Toolbar (99 LOC)
- `MessageContent.tsx` — Bubble Router + ReplyBanner (~65 LOC)
- `Reactions.tsx` — Reaction-Chips + ThreadChip (56 LOC)
- `content/TextContent.tsx` — Text + HTML Sanitization + Linkify + Notice + Emote (~80 LOC)
- `content/MediaContent.tsx` — Image (Lightbox) + Video + Audio + Sticker (~95 LOC)
- `content/FileContent.tsx` — File Router + Docx + Xlsx + PDF + Generic (~150 LOC)
- `content/LocationContent.tsx` — Standort-Sharing via geo: URI → OpenStreetMap (~20 LOC)
- `content/index.ts` — Barrel Export
- `index.ts` — Barrel Export

**components/matrix/room-info/:**
- `RoomInfoPanel.tsx` — Orchestrator (281 LOC)
- `MemberList.tsx` — Mitgliederliste + Moderation (81 LOC)
- `SharedMedia.tsx` — Medien/Dateien/Links (86 LOC)
- `AdminSettings.tsx` — RoleManagement + PermissionsPanel mit shadcn Select (114 LOC)
- `index.ts` — Barrel Export

**components/matrix/room-list/:**
- `RoomList.tsx` — Orchestrator mit shadcn Tabs + Input (125 LOC)
- `RoomItem.tsx` — Raum-Eintrag mit shadcn DropdownMenu (144 LOC)
- `InviteItem.tsx` — Einladungs-Eintrag (57 LOC)
- `index.ts` — Barrel Export

## Phasen-Log

### Phase 1: types.ts splitten ✅
- [x] types.ts → types.ts (87 LOC, Interfaces) + utils.ts (42 LOC) + resolvers.ts (296 LOC)
- [x] Re-Exports in types.ts fuer Backward-Kompatibilitaet

### Phase 2: hashColor + mxcToHttp Deduplizierung ✅
- [x] hashColor() in utils.ts, 3 Duplikate ersetzt (Message, RoomList, SpaceSelector)
- [x] 10x inline mxcToHttp ersetzt (RoomInfoPanel 4x, RoomList, RoomHeader, DMInfoPanel, SpaceSelector, UserProfileDialog, useTimeline, UrlPreview)

### Phase 3: Shared Components ✅
- [x] MatrixAvatar.tsx erstellt (noch nicht ueberall eingesetzt — kommt bei Portierung)
- [x] EncryptionBadge.tsx erstellt und in 3 Dateien eingesetzt (RoomInfoPanel, DMInfoPanel, RoomHeader)

### Phase 4: Hooks — useMuteRoom + usePinnedMessages ✅
- [x] useMuteRoom.ts (aus RoomInfoPanel + DMInfoPanel, ~50+30 LOC eliminiert)
- [x] usePinnedMessages.ts (aus MatrixChat + RoomInfoPanel, ~35+15 LOC eliminiert)
- [x] Bugfix: users_default Fallback in Power-Level Berechnung

### Phase 5: Hooks — useRoomMembers + useMessageActions ✅
- [x] useRoomMembers.ts (aus RoomInfoPanel, ~40 LOC eliminiert, mit refresh() fuer kick/ban)
- [x] useMessageActions.ts (aus MatrixChat, handleReact + handleRedact)
- [x] Bugfix: users_default in member power-level und canPin

### Phase 6: Message.tsx aufbrechen → message/ ✅
- [x] 4 Dateien + index: Message (149), MessageActions (99), MessageContent (65 Bubble Router), Reactions (56)
- [x] Content-Typen in message/content/: TextContent, MediaContent, FileContent, LocationContent
- [x] Re-Export-Stub entfernt, Timeline.tsx Import direkt umgeleitet

### Phase 7: RoomInfoPanel.tsx → room-info/ + shadcn Select ✅
- [x] 4 Dateien + index: RoomInfoPanel (281), MemberList (81), SharedMedia (86), AdminSettings (114)
- [x] shadcn Select statt native `<select>` in RoleManagement + PermissionsPanel

### Phase 8: RoomList.tsx → room-list/ + shadcn Tabs/DropdownMenu ✅
- [x] 3 Dateien + index: RoomList (125), RoomItem (144), InviteItem (57)
- [x] shadcn Tabs statt self-built Filter-Buttons
- [x] shadcn Input statt native `<input>` fuer Suche
- [x] shadcn DropdownMenu statt self-built Context-Menu

### Phase 9: MessageComposer — Reviewed, bleibt zusammen
- [x] Reviewed: 634 LOC, Logik stark verflochten (Recording Refs, Upload State, Send)
- [x] Entscheidung: Aufbrechen wuerde Komplexitaet erhoehen, nicht reduzieren
- [x] Bleibt als einzelne Datei

### Phase 10: shadcn Input/Switch in Dialogen ✅
- [x] shadcn Input in: InviteDialog, CreateDMDialog, CreateRoomDialog, CreatePollDialog, ForwardDialog, UserProfileDialog, SearchPanel
- [x] shadcn Switch statt native `<input type="checkbox">` in UserProfileDialog (Auto-Accept DMs)

### Phase 11: Cleanup ✅
- [x] index.ts in message/, message/content/, room-info/, room-list/
- [x] Re-Export-Stubs entfernt (Message.tsx, RoomInfoPanel.tsx, RoomList.tsx)
- [x] Imports in MatrixChat.tsx + Timeline.tsx direkt auf neue Pfade umgeleitet
- [x] Letzter native `<input type="text">` in room-info/RoomInfoPanel.tsx → shadcn Input
- [x] SpaceSelector: title Attribute → shadcn Tooltip (3 Stellen)
- [x] tsc --noEmit: 0 Fehler (ausser vorbestehende shadcn UI type issues in input-otp, resizable)

---

## Bugfixes (in Phasen integriert)
1. ✅ `users_default` Fallback bei Power-Level (Phase 4+5)
2. ✅ MXC URL inline → mxcToHttp() (Phase 2, 10 Stellen)
3. ✅ `EventType.RoomPinnedEvents` statt `as any` (vor exec-07, Pin-Fix Commit)

## Verifikation
- tsc --noEmit: 0 Fehler pro Phase ✅
- End-to-End: devstack2.ps1 + Smoke Test ausstehend (nach Commit)
