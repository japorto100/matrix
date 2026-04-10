# exec2-03: Matrix Chat UI Rework + Element X Paritaet + SOTA

> Konsolidiert aus exec-04 (implementierte Features) + exec-07 (Refactoring)
> Stand: 30.03.2026

---

## UI Rework Phasen (exec-04)

### Phase 1-10: Redesign
- [x] Theme & Globals (Dark/Light/Blue/Green Themes)
- [x] Toaster + Error Handling (sonner)
- [x] RoomList Redesign (Tabs, Filter, Search, Virtualisierung)
- [x] Space-Rail (Element X Pattern)
- [x] RoomHeader Redesign
- [x] Timeline Redesign
- [x] Message Redesign (Bubble-Gruppen, Reactions)
- [x] MessageComposer Redesign (File Upload, Voice, Emoji)
- [x] Side-Panel Polish (RoomInfo, Members, SharedMedia)
- [x] Bug Fixes (diverse)

### Element X Feature-Paritaet

#### Virtualisierte Room List
- [x] @tanstack/react-virtual, estimateSize 60px, overscan 5

#### WYSIWYG Composer (Tiptap)
- [x] Tiptap Editor: Bold, Italic, Strike, Code, CodeBlock, Listen, Quote
- [x] User-Mentions (@): Room-Members Autocomplete, Pill → matrix.to Permalink
- [x] Agent-Mentions (@agent-*): Lila AI Badge, isAgentUser() Erkennung
- [x] @room Mention: Megaphone-Icon, m.mentions.room = true (MSC3952)
- [x] Room-Pills (#): Separater Trigger, Autocomplete aus gejointen Raeumen
- [x] formatted_body + m.mentions in allen Send-Modes

#### MatrixRTC / LiveKit Calls
- [x] LiveKit SFU + lk-jwt-service Binaries + Configs
- [x] useMatrixRTCCall.ts: MatrixRTCSession + JWT Austausch
- [x] CallOverlay: VideoConference + AudioConference Prefabs
- [x] MatrixKeyProvider fuer Media-E2EE (SFrame)
- [x] 1:1 + Gruppen, Voice + Video, Screen Share
- [x] Legacy useCall.ts entfernt
- [x] Background Blur via @livekit/track-processors

#### Permalinks + Navigation
- [x] matrix:navigate Event-Listener (Raum/User oeffnen)
- [x] Pfeiltasten in RoomList (ArrowUp/Down, scrollToIndex)

#### Keyboard Shortcuts
- [x] Pfeil-Oben → letzte eigene Nachricht editieren
- [x] Ctrl+K → Search Panel
- [x] Esc → aktives Panel schliessen
- [x] Pfeiltasten → RoomList Navigation

---

## Refactoring (exec-07)

- [x] Contacts-Ordner: CreateDMDialog, InviteDialog, ContactPicker
- [x] Spaces-Ordner: SpaceSelector, SpaceSettings, CreateSpaceDialog
- [x] Threads-Ordner: ThreadPanel, ThreadOverview
- [x] Composer-Ordner: WysiwygEditor, MentionList, mentionSuggestion
- [x] Shared-Ordner: MatrixAvatar, EncryptionBadge
- [x] Index-Dateien fuer Barrel-Exports

---

## SOTA Packages (30.03.2026)

- [x] react-shiki (installiert, Umstellung in Agent Chat)
- [x] motion (installiert, ersetzt framer-motion in Agent Chat)
- [x] @livekit/track-processors (Background Blur in CallOverlay)
- [x] @formkit/auto-animate (installiert)
- [x] react-shiki in Matrix TextContent.tsx umstellen
- [x] motion Import in Matrix Components umstellen
- [x] auto-animate in Matrix RoomList/Timeline einbauen

---

## Offene Punkte (Backlog)

- [x] Location Content: OpenStreetMap-Embed statt Link (10.04.2026)
  - [x] `parseGeoUri()` shared utility in `shared/src/geo/parseGeoUri.ts`
  - [x] `LocationEmbed.tsx` (iframe OSM embed, SSR-safe) in `shared/src/location/`
  - [x] `LocationMapInner.tsx` (react-leaflet, dynamic import) in `shared/src/location/`
  - [x] `LocationContent.tsx` in nextjs-chat refactored auf shared/ imports
  - [ ] Agent-Chat: generische {lat, lon, label} Props (kein SDK) — bei Bedarf einbauen
  - **SDK-Version:** matrix-js-sdk 41.2.0 hat `M_LOCATION` types, `makeLocationContent()`, `parseLocationEvent()`
  - **Agent-Version:** Nur `{lat, lon, label}` Props, kein matrix-js-sdk noetig
- [ ] Client→Server Analyse: welche API Calls optimierbar (Analyse, kein Code)
- [ ] api.ts fuer zentralisierte Matrix-API-Calls evaluieren (Analyse, kein Code)
