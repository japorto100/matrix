# exec-04: UI Rework — Matrix Chat Redesign + Error Handling

**Datum:** 26.03.2026
**Status:** Abgeschlossen (Core + Polish)

---

## Was wurde gemacht

### Phase 1: Theme & Globals
- `globals.css`: Base-Layer (`border-border`, `bg-background text-foreground antialiased`)
- Status-Utilities (`text-status-success/warning/error/info` + `bg-status-*`)
- Themes identisch zum Hauptprojekt (oklch, 4 Themes: light, dark, blue-dark, green-dark)
- Theme-System port-ready (next-themes, class-Attribut)

### Phase 2: Toaster + Error Handling
- Sonner Toaster in `layout.tsx` (`bottom-right`, Dark-Theme)
- `ErrorBoundary.tsx` um MatrixChat gewrappt
- Toast bei Send/Upload/Voice-Recording Fehlern
- Cross-Signing: Toast + Erklärungstext wenn kein zweites Device vorhanden

### Phase 3: RoomList Redesign
- Suchleiste mit Search-Icon + client-seitige Filterung
- Filter-Tabs: Alle, Ungelesen (mit Count), Personen
- Farbige Avatare (Hash-basiert, 8 Farben)
- Zeitstempel rechts aligned, Room-Name bold bei Unread
- Unread-Badge als Pill (`bg-primary`)
- DecryptionError: "🔒 Verschlüsselte Nachricht" statt Rohtext
- Sidebar: `w-72`

### Phase 4: Space-Rail (Element X Pattern)
- Vertikale Icon-Leiste links neben der Room-Liste
- Home-Button (alle Räume) mit Selected-Indicator
- Space-Icons mit farbigen Avataren + Tooltip
- Profil-Avatar unten in der Rail (aus Sidebar-Footer verschoben)
- SpaceSelector komplett umgebaut von Dropdown zu Rail

### Phase 5: RoomHeader Redesign
- Kompaktes Layout: Avatar + Shield + Name + Member-Count inline
- E2EE Shield dreistufig:
  - ShieldCheck (grün) — Verschlüsselt + verifiziert
  - ShieldAlert (gelb) — Verschlüsselt, nicht verifiziert
  - ShieldOff (grau) — Nicht verschlüsselt
- Backdrop-blur beibehalten
- Action-Buttons gruppiert

### Phase 6: Timeline Redesign
- Datum-Separatoren: "Heute", "Gestern", volles Datum als zentrierte Pills
- Message-Gruppierung: Gleicher Sender innerhalb 2 Min → kein Avatar/Name
- "Ältere Nachrichten" als dezenter Text-Link statt Button
- Scroll-to-bottom FAB (runder Button unten rechts wenn hochgescrollt)
- `scrollbar-hide` auf Timeline

### Phase 7: Message Redesign
- Blaue Bubbles für eigene Messages (`bg-blue-600/90 text-white`)
- Sender-Farben Hash-basiert (12 Farben, wie Element X)
- Uhrzeit (HH:MM) statt "vor X Minuten"
- DecryptionError: Lock-Icon + "Diese Nachricht kann nicht entschlüsselt werden"
- URLs als klickbare Links (linkifyText)
- isGrouped: Kein Avatar/Name bei gruppierten Messages
- Hover-Actions: Button-Component statt raw `<button>`

### Phase 8: MessageComposer Redesign
- Abgerundetes Input (`rounded-xl bg-muted/30 border-border/50`)
- Runder Send-Button, nur sichtbar wenn Text
- Mic-Button für Audio-Aufnahme (wenn kein Text)
- Recording-UI: Roter Puls + Timer + MicOff-Cancel + Send
- Error-Handling: Permission-Dialog, NotFound, NotAllowed

### Phase 9: Side-Panel Polish
- Alle Panels: `border-border/50`, konsistente Header-Höhe
- SearchPanel: Input-Styling wie RoomList
- RoomSettingsPanel: Input-Styling konsistent

### Phase 10: Bug Fixes
- **Infinite-Loop Fix**: Read-Receipt Effect hing an `messages` Array → Loop
  - `MatrixChat.tsx`: Dependency auf `lastEventId` statt `messages`
  - `useTimeline.ts`: Receipt-Handler debounced (300ms)
- **Cross-Signing**: Toast statt stilles Schließen
- **Pre-existing Lint**: Alle suppressions/unused, noImgElement, exhaustive-deps gefixt

---

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `src/app/globals.css` | Status-Utilities, Base-Layer |
| `src/app/layout.tsx` | Toaster |
| `src/components/matrix/MatrixAppClient.tsx` | ErrorBoundary |
| `src/components/matrix/MatrixChat.tsx` | Space-Rail, Sync-Status, Empty-State, Read-Receipt Fix |
| `src/components/matrix/RoomList.tsx` | Komplett neu (Suche, Filter, Design, kein Profil-Footer) |
| `src/components/matrix/SpaceSelector.tsx` | Komplett neu (vertikale Icon-Rail statt Dropdown) |
| `src/components/matrix/RoomHeader.tsx` | E2EE Shield dreistufig, Layout |
| `src/components/matrix/Timeline.tsx` | Komplett neu (Datum-Separatoren, Gruppierung, Scroll-FAB) |
| `src/components/matrix/Message.tsx` | Sender-Farben, Bubbles, linkifyText, DecryptionError, Button-Actions |
| `src/components/matrix/MessageComposer.tsx` | Styling, Audio-Recording, Toast |
| `src/components/matrix/ErrorBoundary.tsx` | **NEU** |
| `src/components/matrix/CrossSigningSetup.tsx` | Erklärungstext, QR alt-text |
| `src/components/matrix/CallOverlay.tsx` | Unused suppressions entfernt |
| `src/components/matrix/ThreadPanel.tsx` | Border polish |
| `src/components/matrix/SearchPanel.tsx` | Input-Styling |
| `src/components/matrix/RoomSettingsPanel.tsx` | Input-Styling |
| `src/lib/matrix/hooks/useTimeline.ts` | Receipt-Debounce |
| `src/lib/matrix/hooks/useCrossSigning.ts` | Toast, Biome-Suppressions |
| `src/lib/matrix/types.ts` | m.replace Filter, m.new_content Body für Edits |

---

## Verification Gates — exec-04

### Build
- [x] `bunx biome check ./src` — 0 Errors, 0 Warnings
- [x] `bunx tsc --noEmit` — 0 Errors

### UI Redesign
- [x] Nachricht senden (Text)
- [x] Reply senden (Quote-Banner + Antwort, Reply-Banner text-sm lesbar)
- [x] URL als klickbarer Link (linkifyText, `text-blue-400 hover:underline`)
- [x] Datum-Separator "Heute"/"Gestern"
- [x] Message-Gruppierung (gleicher Sender <2min → kein Avatar/Name)
- [x] E2EE Shield gelb (verschlüsselt, nicht verifiziert)
- [x] E2EE Shield grau (nicht verschlüsselt)
- [x] E2EE Shield grün (verschlüsselt + verifiziert) — Code vorhanden, nicht testbar ohne Cross-Signing
- [x] DecryptionError graceful (Sidebar: italic Text, Bubble: Lock-Icon)
- [x] Space-Rail mit Home-Button + Profil-Avatar
- [x] Suchleiste + Filter-Tabs (Alle/Ungelesen/Personen)
- [x] Room-Sortierung nach Aktivität
- [x] Mic-Button sichtbar (wenn kein Text eingegeben)
- [x] Infinite-Loop weg (nur TURN 404 in Console)
- [x] Blaue Bubbles für eigene Messages
- [x] Sender-Farben Hash-basiert (12 Farben)
- [x] Uhrzeit (HH:MM) statt relative Zeit in Messages
- [x] Kurze Timestamps in Sidebar (11m, 16h, 2d)
- [x] Sidebar overflow gefixt (kein Overlap mit Chat-Bereich)
- [x] Selected-Indicator Space-Rail dezent
- [x] "Ältere Nachrichten" als dezenter Text-Link
- [x] Scroll-to-bottom FAB (runder Button wenn hochgescrollt)
- [x] Edit-Banner im Composer (✏️ Nachricht bearbeiten)
- [x] "(bearbeitet)" Badge nach Edit
- [x] "[Nachricht gelöscht]" bei Redaction
- [x] Side-Panels: konsistente Borders (border-border/50)
- [x] Message Hover-Actions: Button-Component statt raw buttons
- [x] Cross-Signing: Erklärungstext + Toast bei Fehler
- [x] ErrorBoundary um MatrixChat
- [x] Toast bei Send/Upload-Fehlern

### Bug Fixes (während Redesign entdeckt)
- [x] Infinite-Loop: Read-Receipt → messages → setMessages Loop
- [x] Edit-Doppel-Send: m.replace Events aus Timeline gefiltert
- [x] Edit `* ` Prefix: m.new_content Body statt Fallback-Body
- [x] Sidebar Overflow: Radix ScrollArea horizontal expandiert → natives overflow-y-auto
- [x] Pre-existing Lint: Alle suppressions/unused, noImgElement, exhaustive-deps

### Emoji & Reactions (26.03.2026)
- [x] Emoji-Picker testen — emoji-mart installiert, 9 Kategorien + Suche + Skin-Tones
- [x] Composer: Emoji-Button links im Input (WhatsApp-Style)
- [x] Message: 6 Quick-Reactions (👍👎😂🔥😮😢) via Reagieren-Button
- [x] Hover-Actions von seitlich nach oberhalb der Message verschoben (Element X Pattern)
- [x] WhatsApp Reaction-Logik: 1 pro User, Toggle (entfernen), Replace (ersetzen)
- [x] Eigene Reaction unter Message hervorgehoben (bg-primary/20) + klickbar zum Entfernen
- [x] Zähler nur bei > 1 sichtbar
- [x] B-3: Emoji-Picker (exec-03) — erledigt via emoji-mart
- [x] UI-12: Emoji-Picker Kategorien (exec-03) — erledigt (9 Kategorien)
- [x] Forward Button in Hover-Toolbar vorhanden

### Bug Fixes (während Emoji/Reactions)
- [x] Redacted m.reaction nicht mehr als "[Nachricht gelöscht]" angezeigt
- [x] pendingEventOrdering Crash bei Reactions gefixt (fetch statt SDK)
- [x] Reaction-Aggregation ignoriert redacted Events

### E2EE & Room-Typen (26.03.2026)
- [x] Tuwunel: `encryption_enabled_by_default_for_room_type = "off"` (alle 3 Configs)
- [x] CreateRoomDialog: E2EE Checkbox → Auswahl "Privater Raum" (invite+E2EE) / "Offener Raum" (public)
- [x] CreateRoomDialog: Avatar-Upload bei Raum-Erstellung (Camera-Button)
- [x] CreateRoomDialog: Warnhinweis bei Privat ("Verschlüsselung nicht rückgängig machbar")
- [x] CreateDMDialog: DMs immer unverschlüsselt (bis exec-05)
- [x] Shield → Lock-Icon: Grün = verschlüsselt, Rot = nicht verschlüsselt (kein gelbes Shield mehr)
- [x] Cross-Signing Banner: Rotes Shield + "Cross-Signing nicht eingerichtet" (statt gelb + "nicht verifiziert")
- [x] Cross-Signing Status im UserProfileDialog (rot/grün Shield)

### InfoPanel (26.03.2026)
- [x] RoomSettingsPanel.tsx → InfoPanel.tsx umgebaut mit room/dm Mode
- [x] DM-Modus: User-Avatar groß, Name, User-ID, E2EE-Status, Block User
- [x] Room-Modus: Room-Avatar + Upload (Camera), Name inline editierbar (Stift + Enter), Thema inline editierbar
- [x] Room-Modus: Mitgliederliste mit Kick/Ban (fetch API)
- [x] Trigger: Avatar im Header klickbar → öffnet InfoPanel (Name nicht mehr klickbar)
- [x] Leave/Delete: Membership-Check, fetch API (leave → forget → store.removeRoom)
- [x] Block User im DM-Modus: `m.ignored_user_list` Account-Data (toggle)
- [x] Profil-Dialog: Funktional (Name + Avatar ändern)

### RoomList Actions (26.03.2026)
- [x] "..." Button bei Hover (ersetzt Timestamp, group-hover)
- [x] Kontextmenü: Favorit Toggle + Raum verlassen/Chat löschen
- [x] Favorit: fetch API (`m.favourite` Tag), Stern-Icon sichtbar in Liste
- [x] Leave: Membership-Check + fetch leave/forget + store.removeRoom
- [x] Filter-Tabs: + "Räume" (Gruppen ohne DM) + "Favoriten" (`m.favourite` Tag)
- [x] `resolveRoom`: `isFavourite` Feld aus Room-Tags

### UI Polish (26.03.2026)
- [x] Linien vereinheitlicht: alle `border-border` (nicht `/50`), gleiche Dicke/Farbe
- [x] Header-Höhe: `h-[57px]` fixiert für RoomHeader + InfoPanel — pixel-genau
- [x] Doppelte Composer-Linie entfernt (Wrapper border-t war redundant)
- [x] RoomList Flicker bei Profiländerung gefixt (`roomInfoEqual` Vergleich in useRooms)
- [x] Button-in-Button Hydration Error gefixt (RoomItem: div statt button)
- [x] Alle SDK-Aufrufe (kick/ban/leave/forget/reaction) auf fetch umgestellt (pendingEventOrdering Bug)

### Bug Fixes (während InfoPanel/Actions)
- [x] pendingEventOrdering Crash bei Leave/Kick/Ban → fetch statt SDK
- [x] Kontextmenü Overlay: `onMouseDown` statt `onClick` (Menu-Buttons nicht blockiert)
- [x] Leave 403 "not joined": Membership-Check vor API-Call, Fallback auf store.removeRoom
- [x] Leave: Raum verschwindet sofort aus UI (emit deleteRoom Event nach store.removeRoom)
- [x] Favourite: Stern erscheint sofort (SDK tags direkt updaten + emit Room.tags)
- [x] Favourite: Filter "Favoriten" funktioniert (isFavourite in roomInfoEqual + RoomEvent.Tags listener)
- [x] useRooms: ClientEvent.DeleteRoom + RoomEvent.Tags listener hinzugefügt
- [x] Button-in-Button Hydration Error: RoomItem outer button → div

### Media & Datei-Handling (26.03.2026)
- [x] File Preview vor Senden: Banner mit Thumbnail/Icon + Caption-Input + Enter sendet
- [x] Bild: 150px Thumbnail in Chat, Lightbox-Dialog (80vw) mit Download + neuer Tab
- [x] Bild: Caption unter Bild (body ≠ filename → als Text angezeigt)
- [x] Bild: Komprimierung > 5MB (browser-image-compression, Target 5MB, max 4K)
- [x] Bild: Bubble `inline-block` (passt sich an Bildgröße an, nicht volle Zeile)
- [x] Video: Preview im Banner (erster Frame via `<video preload="metadata">`)
- [x] Video: Player in Chat (250x200px max)
- [x] Audio/MP3: Player in Chat (Music-Icon + Filename + Duration + `<audio controls>`)
- [x] Voice Message: Voice-Pill (Mic-Icon + Audio-Player + Duration + MSC3245)
- [x] PDF: Klickbar → Dialog mit iframe Preview (80vw)
- [x] Alle anderen Dateien: Download-Link mit Icon + Dateiname + Größe
- [x] Upload Progress-Bar im Preview-Banner (SDK `progressHandler`)
- [x] Accept `*/*` — alle Dateitypen erlaubt
- [x] Tuwunel: `max_request_size = 524288000` (500 MB Upload-Limit)
- [x] Client: 500MB Limit mit Toast bei Überschreitung
- [x] readFileDimensions: 5s Timeout + `preload="metadata"` für Videos
- [x] Auto-Scroll bei neuen Nachrichten
- [x] Scroll-to-bottom FAB mittig
- [x] Fokus bleibt auf Textarea nach Dateiauswahl

### Solo-Tests (26.03.2026)
- [x] Suche: Client-seitige Filterung in RoomList funktioniert
- [x] Theme-Switch: 4 Themes konfiguriert (light, dark, blue-dark, green-dark), port-ready via next-themes, kein eigener Switcher nötig
- [x] Mute Toggle: UI funktioniert (Bell/BellOff), Push-Rules via SDK, funktionaler Test braucht zweiten User

### Braucht zweiten User (Bot/Element X)
- [ ] Unread-Badge erscheint bei neuer Nachricht von anderem User
- [ ] Ungelesen-Zähler fällt auf 0 nach Raumwechsel
- [ ] Read Receipts: Mini-Avatar erscheint wenn anderer User liest
- [ ] Online-Status Dot bei DM
- [ ] Nachrichten von anderem User: Bubble links, Sender-Farbe
- [ ] Call starten + Overlay

### exec-03 Gates getestet (26.03.2026)
- [x] QW-1: HTML-Rendering — `<strong>`, `<code>`, `<table>` korrekt gerendert (rehype-sanitize + prose)
- [x] QW-1: XSS geblockt — `<script>` und `onerror` komplett gestripped, nur Safe-Text bleibt
- [x] QW-3: @mention — Code korrekt (`isMentioned` → gelbe Bubble), braucht zweiten User zum visuellen Test
- [x] B-5: URL Preview — Code korrekt (`extractFirstUrl` + `UrlPreview`), nur bei Messages von anderen sichtbar

### exec-03 Gates getestet (26.03.2026 — Runde 2)
- [x] S-1: Sliding Sync — aktiv, Requests an `simplified_msc3575/sync` mit Status 200
- [x] UI-8: Suche — Side-Panel öffnet mit Suchfeld, funktional
- [x] UI-13: Forward — "Weitergeleitet von alice: ..." korrekt angezeigt
- [x] F-1: Spaces — Rail mit Home-Button, Filter-Tabs (Alle/Ungelesen/Favoriten/Personen/Räume)
- [x] B-7: Poll — "Abstimmung" + "0 Stimmen" gerendert (Abstimmen braucht zweiten User)

### Zweiter User Tests mit Bob (27.03.2026)
- [x] Messages von anderem User: Bubble links, muted Hintergrund, Sender-Farbe (grün)
- [x] QW-3: @mention gelb hervorgehoben — gelbe Bubble + gelbe Border bei Mention von Bob
- [x] Unread-Badge: "3" am Raum + "Ungelesen (3)" Tab
- [x] Unread-Zähler fällt auf 0: Read Receipt + setUnreadNotificationCount lokal + ClientEvent.Room emit
- [x] Datum-Separator "Heute" bei Tageswechsel
- [x] Member Count aktualisiert (3 nach Bob join)
- [x] pendingEventOrdering Root-Cause Fix: `"detached"` statt Default `"chronological"` in client.ts

### Noch offen (nächste Session)
- [x] B-5: URL Preview — deaktiviert (SSRF-Risiko). Code vorhanden (`UrlPreview.tsx`, `getUrlPreview` SDK), bei Bedarf aktivierbar. Siehe specs/16-security.md
- [x] DM mit Bob: Raumname "bob 💕", Bubble links, Sender-Farbe ✅
- [ ] Read Receipts: Code vorhanden (`readBy` in useTimeline + Mini-Avatare in Message.tsx), Sync-Timing schwer testbar mit API-Bob
- [ ] Online-Status Dot: Code vorhanden (`isOnline` in resolveRoom + grüner Punkt in RoomList), braucht echten zweiten Client
- [ ] B-8: Thread-Chip + Side-Panel — braucht Element X Mobile (Cloudflare Tunnel)
- [ ] UI-14: ReadBy Liste — braucht Read Receipts sichtbar
- [ ] Call starten + Overlay — braucht zweites Device (Element X Mobile)
- [x] LLM Mock: Agent-Chat funktioniert! Alice → Trading Agent DM → Python Bridge → LLM Mock → Antwort in Chat
  - Agent auto-joined DM (Python Bridge akzeptiert Invite automatisch)
  - Markdown-Rendering in Agent-Antwort (Bold, Emoji)
  - Bot-User: `@trading-agent:matrix.local`

### SDK-Migration + Invite-Handling (27.03.2026)
- [x] SDK-Migration: DM-Erkennung via `m.direct` Account-Data (statt guessDMUserId)
- [x] SDK-Migration: `room.getMyMembership()` → `membership` Feld in RoomInfo
- [x] SDK-Migration: `room.getInvitedAndJoinedMemberCount()` statt nur joined
- [x] SDK-Migration: `otherUserId` → `dmUserId` + `inviterUserId` in RoomInfo
- [x] useRooms: Filter erweitert auf `["join", "invite"]` (Invite-Rooms sichtbar)
- [x] useRooms: `RoomEvent.MyMembership` listener hinzugefügt
- [x] Auto-Accept: `useAutoAcceptInvites` Hook (DMs auto-join, Gruppen Toast)
- [x] Auto-Accept: localStorage Setting `matrix_auto_accept_dms` (default: true)
- [x] RoomList: Invite-Sektion oberhalb normaler Rooms mit Accept/Decline Buttons
- [x] RoomList: InviteItem Komponente (DM vs Gruppe unterscheidbar)
- [x] DMInfoPanel: Invite-Status "Einladung ausstehend" wenn anderer User invited
- [x] DMInfoPanel: Accept/Decline wenn eigene Membership = invite
- [x] DMInfoPanel: Block nur bei joined (nicht bei invite)
- [x] Timeline: Invite-Placeholder mit Annehmen/Ablehnen (kein Composer bei invite)
- [x] InfoPanel.tsx gelöscht → DMInfoPanel + RoomInfoPanel
- [x] Tuwunel: `auto_join_rooms = ["#general:matrix.local"]`
- [x] DM Name-Fix: "Bob" statt "Empty room" bei invited Members
- [x] Auto-Accept Toggle in UserProfileDialog (Checkbox)
- [x] RoomInfoPanel: Accept/Decline Footer bei invite Membership
- [x] "Warte auf Antwort..." Banner bei DM mit invited Member
- [x] General-Raum erstellt + Alice gejoined
- [x] fetch→SDK Migration: alle leave/forget/kick/ban/redact/sendEvent auf SDK-Calls umgestellt
- [x] DM-Name: Immer Display-Name des anderen Users (nicht User-ID oder "Empty room")
- [x] DM-Erkennung: `m.direct` Account-Data statt `guessDMUserId()` (SDK rät zu aggressiv)
- [x] Mute aus Header entfernt → nur noch in InfoPanels (DM + Room)
- [x] DMInfoPanel vollständig: Online-Status, Presence-Text, Status/Bio, Mute, Block (SDK setIgnoredUsers), geteilte Medien, gemeinsame Räume, Invite-Status, E2EE Lock
- [x] RoomInfoPanel: Mute-Button hinzugefügt
- [x] UserProfileDialog: Status/Bio Input + Speichern (SDK setPresence)
- [x] Auto-Accept Toggle in UserProfileDialog (Checkbox + localStorage)

### Security (27.03.2026)
- [x] tuwunel.toml aus Git entfernt (enthält Tokens)
- [x] tuwunel.example.toml + tuwunel.image.example.toml erstellt (Platzhalter)
- [x] gitignore: `homeserver/tuwunel.toml`, `tuwunel.prod.toml`, `tuwunel.image.toml`
- [x] Portierungs-Spec: NextAuth → Admin API User-Provisioning dokumentiert
- [x] Prod + Image TOMLs: max_request_size, auto_join_rooms, URL Preview ergänzt

### Federation (noch nicht aktiviert, Checkboxen für später)
- [ ] `allow_federation = true` in Tuwunel setzen
- [ ] DNS: `_matrix._tcp` SRV Record oder `.well-known/matrix/server`
- [ ] HTTPS + echte Domain (Cloudflare Tunnel oder eigene)
- [ ] Draupnir/Mjolnir Bot deployen (Spam-Schutz, separater Node.js Prozess mit eigenem Matrix-Account)
- [ ] Server ACLs konfigurieren (Blacklist für bekannte Spam-Server)
- [ ] `block_non_admin_invites` evaluieren
- [ ] Auto-Accept auf interne User beschränken (`endsWith(":matrix.local")`)
- [ ] Public Room Directory versteckt lassen
- [ ] Testen: Externer User von matrix.org kann Alice/Bob nicht finden aber eingeladen werden

### RoomInfoPanel Features (27.03.2026)
- [x] Geteilte Medien: Bilder/Dateien/Links Zähler (wie DMInfoPanel)
- [x] Invite-Link: `matrix.to` URL generiert + Copy-Button
- [x] Rollen-Management: Admin kann andere zu Admin/Mod/Member befördern (`client.setPowerLevel()`)
- [x] Gruppen-Einstellungen: Berechtigungen für Senden/Einladen/Raum-Info ändern (`m.room.power_levels`)
- [x] Pinned Messages: Liste im InfoPanel + Pin/Unpin Button auf Message-Hover-Toolbar
- [x] Pinned Messages Banner: "📌 X angepinnte Nachrichten" unter Room-Header, Klick öffnet InfoPanel
- [x] Pinned Messages: Unpin-Button (PinOff) in InfoPanel Pin-Liste (hover, nur für Admins/Mods)
- [x] Pinned Messages: Power-Level Check — Pin-Button nur sichtbar wenn User Berechtigung hat
- [x] Pinned Messages: SDK-Typen korrekt (`EventType.RoomPinnedEvents` statt `as any`)
- [x] Topic nur Admin/Mod editierbar (`state_default` Power-Level Check)
- [x] Name/Avatar nur Admin/Mod editierbar (`canEditRoomInfo` Check)
- [x] Mute aus Header entfernt → nur noch in InfoPanels (DM + Room)
- [x] DM Name-Bug gefixt: SDK room.name Fallback-Kette (sdkName → member.name → displayName → username)
- [x] General Stern-Bug gefixt (auto-favourited entfernt)

### Nicht eingebaut (Begründung)
- ❌ Disappearing Messages: SDK hat kein `m.room.retention` (MSC1763 nicht finalisiert), Cross-Client inkompatibel
- ❌ View Once: Existiert in Matrix Spec nicht, eigene Erfindung wäre nicht Spec-konform
- ❌ Globale Rollen: Matrix hat keine — NextAuth Rollen → Power-Levels Mapping bei Portierung (Go Backend)

### Verify Gates — RoomInfoPanel Features
- [ ] Geteilte Medien: Room mit Bildern/Dateien öffnen → Zähler im InfoPanel sichtbar
- [ ] Invite-Link: Room öffnen → InfoPanel → Link sichtbar + Copy-Button kopiert in Zwischenablage
- [ ] Rollen-Management: Als Admin → InfoPanel → Member-Dropdown → "Moderator" wählen → Power-Level ändert sich
- [ ] Gruppen-Einstellungen: Als Admin → InfoPanel → "Nachrichten senden" auf "Moderator+" setzen → normaler Member kann nicht mehr senden
- [ ] Pinned Messages: Nachricht hovern → Pin-Button klicken → Toast "Angepinnt" → Pin-Liste im InfoPanel sichtbar
- [ ] Pinned Messages: Bereits gepinnte Nachricht → PinOff-Button → Toast "Entpinnt" → verschwindet aus Liste
- [ ] Pinned Messages Banner: Banner unter Header zeigt "X angepinnte Nachrichten" → Klick öffnet InfoPanel
- [ ] Pinned Messages: Als normaler Member (PL < state_default) → kein Pin-Button sichtbar
- [ ] Pinned Messages: Im InfoPanel → Hover über Pin → PinOff-Button → Entpinnen funktioniert
- [ ] Topic Edit: Als Admin → InfoPanel → Stift bei Thema → editieren → Enter → gespeichert
- [ ] Topic Edit: Als normaler Member → kein Stift sichtbar (wenn state_default >= 50)
- [ ] Name Edit: Als Admin → Stift neben Name → editieren → Enter → gespeichert
- [ ] Avatar Edit: Als Admin → Camera-Button am Avatar → Bild wählen → hochgeladen
- [ ] Name/Avatar/Topic: Als normaler Member → kein Stift, kein Camera-Button

### Verify Gates — DM + Invite
- [ ] DM erstellen mit `@bob:matrix.local` → Name "bob" (nicht "Empty room" oder "@bob:matrix.local")
- [ ] DM erstellen → Bob auto-accept (wenn Python Bridge / Bot) oder Invite-Sektion in RoomList
- [ ] DMInfoPanel: Avatar, Name, User-ID, Online-Status, E2EE, Mute, Block, Chat löschen
- [ ] DMInfoPanel: Gemeinsame Räume sichtbar (wenn Bob in gleichen Räumen)
- [ ] Auto-Accept DM: Bob erstellt DM an Alice → Alice auto-joined + Toast
- [ ] Auto-Accept Toggle: Profil → Checkbox aus → DM-Einladung zeigt Accept/Decline statt Auto-Join
- [ ] Gruppen-Einladung: Bob erstellt Gruppe + lädt Alice ein → Toast mit Accept/Decline
- [ ] Timeline Invite-Placeholder: Raum mit membership=invite → "Annehmen/Ablehnen" statt Composer
- [ ] "Warte auf Antwort..." Banner bei DM wo anderer User invited

### Verify Gates — Noch offen (braucht Element X Mobile)
- [ ] Read Receipts: Mini-Avatar wenn anderer User liest
- [ ] Online-Status Dot bei DM
- [ ] B-8: Thread-Chip + Side-Panel
- [ ] UI-14: ReadBy Liste
- [ ] Call starten + Overlay

### Verify Gates — Mobile Infrastruktur (28.03.2026)
- [ ] TURN Server: Metered.ca Open Relay in tuwunel.toml konfiguriert ✅ — Cross-Network Call testen
- [ ] Push Notifications: Element X (Play Store) → Elements Sygnal automatisch → verifizieren
- [ ] Push Notifications (Prod): ntfy + UnifiedPush evaluieren (F-Droid, kein Google)
- [ ] Authenticated Media: MSC3916 aktiv, Element X nutzt nativ → verifizieren dass Bilder laden
- [ ] Cross-Signing: Web-Client Verify-Button → QR-Code → Element X scannt → verifiziert
- [ ] Zendrite: `tools/zendrite.exe` builden + testen als Windows-Fallback (statt Dendrite)

### Element X Mobile Verbindung (Cloudflare Tunnel)
- [ ] `tools/cloudflared.exe` vorhanden ✅
- [ ] Cloudflare Account erstellen (gratis)
- [ ] Tunnel starten: `tools/cloudflared.exe tunnel --url http://localhost:8448`
- [ ] HTTPS URL erhalten: `https://xxx.trycloudflare.com`
- [ ] tuwunel.toml: `well_known.client` auf Tunnel-URL setzen
- [ ] Element X Mobile: Tunnel-URL als Homeserver eingeben
- [ ] Login testen mit Alice oder Bob
- [ ] Cross-Signing zwischen Web + Mobile testen (QR-Code / Emoji-Vergleich)
- [ ] Cross-Network Call testen (Mobile 4G ↔ Webapp Browser) — TURN muss funktionieren
- [ ] Devstack2: `-Tunnel` Flag auf cloudflared umstellen (statt bore)

### Test-Accounts
- **Alice:** `@alice:matrix.local` — Credentials in `.env.local`
- **Bob:** `@bob:matrix.local` — Token: `I45Mo07R3Ju4iz72UxeLDqyQeeg5GFsU`, Device: `NgAiNqK47A`, Passwort: `bob12345`
- Bob ist Member in: `!ALIz1gdreaaxFNVcHe:matrix.local` (matrix.local Admin Room)

---

## Offene Feature-Todos (nächste Iteration)

### Call-Events in Timeline
Element X zeigt "Video call started" + "Join call" Button inline in der Message-Timeline.
- Braucht eigenen Renderer für `m.call.invite` Events
- CallOverlay + useCall Hook existieren (State-Management, Video-Refs, Steuerleiste)
- Call-Buttons im Header sind funktional vorhanden
- **Voraussetzung:** STUN/TURN muss funktionieren (nach Tuwunel-Neustart mit STUN-Config)

### Threads (28.03.2026 — erweitert)

**Grundlagen:**
- Threads ≠ Spaces ≠ Sub-Raeume
- Threads = Nebengespraeche innerhalb eines Raums (wie Slack Threads)
- Erben E2EE, Rollen, Members vom Hauptraum — keine eigene Mitgliedschaft
- Alle Room-Members koennen in jedem Thread antworten
- Spec: `m.thread` Relation (stabil seit Matrix v1.3/v1.4, MSC3440)

**Vorhandener Code:**
- `ThreadPanel.tsx` — Side-Panel rechts (380px, eigene Timeline + Composer) ✅
- `useThreadTimeline.ts` — Hook fuer Thread-Events ✅
- `ThreadChip` in Reactions.tsx — "X Antworten" unter Root-Nachricht ✅
- `MessageComposer` akzeptiert `threadId` Prop ✅
- ThreadPanel nutzt dieselben Komponenten wie Hauptchat (Timeline, Composer, Message-Bubbles)

**Thread-Send — SDK korrekt genutzt:**
- `client.sendMessage(roomId, threadId, content)` ist die offizielle SDK API
- SDK setzt `m.relates_to` mit `rel_type: "m.thread"` + `is_falling_back` + `m.in_reply_to` intern
- Kein manuelles Setzen noetig ✅

**UI eingebaut (28.03.2026):**
- [x] "Thread starten" Action im Message-Hover-Menue (MessageSquare Icon)
- [x] Thread-Overview-Button im RoomHeader (neben Search, Info)
- [x] `ThreadOverview.tsx` — Thread-Liste: Root-Msg, Reply-Count, letzte Aktivitaet → Klick oeffnet ThreadPanel
- [x] Thread-Send nutzt SDK `client.sendMessage(roomId, threadId, content)` korrekt

**Agent Thread-Strategie:**
- Agent antwortet **im Hauptchat** bei: kurzen Antworten, Alerts, Status-Updates
- Agent **erstellt Thread** bei: langen Analysen, strukturierten Daten, parallelen User-Fragen
- Agent **antwortet im Thread** bei: Follow-up Fragen im existierenden Thread
- Regelbasiert: Antwort > X Zeichen oder enthaelt strukturierte Daten → Thread, sonst Hauptchat

### Verify Gates — Threads
- [ ] Thread starten: Message hovern → Thread-Button → ThreadPanel oeffnet sich mit Root-Nachricht
- [ ] Thread antworten: Im ThreadPanel Nachricht schreiben → erscheint im Thread
- [ ] Thread-Chip: Nach Antwort zeigt Root-Nachricht "X Antworten" Chip
- [ ] Thread-Overview: RoomHeader Thread-Button → Liste aller aktiven Threads → Klick oeffnet Thread
- [ ] Thread-Send korrekt: Gesendete Nachricht hat `rel_type: "m.thread"` (pruefen via Element Web/DevTools)
- Verschoben nach exec-05 Phase C4: Agent in Thread (braucht NATS Pipeline)

### Spaces (28.03.2026 — erweitert)

**Grundlagen:**
- Spaces = Ordner/Gruppen von Raeumen (wie Slack Workspace, Discord Server)
- Normale Spaces (Team-uebergreifend) vorerst, persoenliche Spaces spaeter
- Technisch: `m.space.child` State Events verknuepfen Raeume mit Spaces
- Ein Raum kann in mehreren Spaces sein
- Raeume ohne Space-Zugehoerigkeit erscheinen unter Home

**Vorhandener Code:**
- Space-Rail (SpaceSelector) zeigt existierende Spaces mit shadcn Tooltips ✅
- `useSpaces.ts` Hook: erkennt Space-Raeume, liest `m.space.child` Events ✅
- Space-Filter in RoomList: Klick auf Space → nur dessen Raeume sichtbar ✅

**Code-Aenderungen:**
- [x] **SpaceSelector → `spaces/` Verzeichnis** umziehen (Konsistenz mit message/, room-info/, room-list/)
- [x] **Home-Button funktional** — `onSelect(null)` bei Klick, Selected-Indicator wenn aktiv
- [x] **CreateSpaceDialog** gebaut (Name, Avatar, Public/Private mit shadcn Tabs, "+" Button in Rail)
- [x] **`getRoomHierarchy()`** in useSpaces integriert (fetchHierarchy Callback, zeigt ungejoinete Raeume)
- [x] **Raum zu Space hinzufuegen/entfernen**
  - CreateRoomDialog: optionaler `spaceId` Prop → setzt `m.space.child` nach Erstellung
  - SpaceSettings: Raeume anzeigen (via getRoomHierarchy), hinzufuegen per Room-ID, entfernen per Button
  - SDK: `client.sendStateEvent(spaceId, "m.space.child", { via }, roomId)` / leerer Content = entfernen
- [x] **Space-Settings** gebaut (SpaceSettings.tsx)
  - Name + Avatar aendern (Pencil, Camera wie RoomInfoPanel)
  - Raeume im Space anzeigen (aus getRoomHierarchy, inkl. ungejoinete mit "Beitreten")
  - Raum hinzufuegen (Room-ID Eingabe) / entfernen (Trash Button)
  - Erreichbar als Side-Panel (wie RoomInfoPanel)
- [x] **Activity Centre** gebaut
  - `ActivityCentre.tsx` — Side-Panel mit Tabs (Alle, Mentions, Threads, Einladungen)
  - `useNotifications.ts` Hook — sammelt Mentions, Thread-Antworten, Invites aus allen Raeumen
  - Bell-Button mit Badge-Count in Space-Rail
  - Klick auf Notification → springt zu Raum/Thread
- [x] **Sub-Spaces** unterstuetzt
  - getRoomHierarchy mit maxDepth=2 erkennt Sub-Spaces (`room_type === "m.space"`)
  - SpaceChildRoom hat `isSpace` Flag
  - SpaceInfo hat `parentSpaceId` fuer Verschachtelung
  - Space-Rail UI fuer verschachtelte Darstellung: TODO bei Bedarf

### Datei-Reorganisation (28.03.2026)

Abgeschlossen:
- [x] ThreadOverview + ThreadPanel → `threads/` Verzeichnis (Imports in MatrixChat aktualisiert)
- [x] SpaceSettings verdrahtet: Rechtsklick auf Space-Icon → SpaceSettings Side-Panel
- [x] CreateRoomDialog `spaceId` durchgereicht: neuer Raum wird automatisch zum aktiven Space hinzugefuegt

Offen (nach Verify Gates):
- [ ] MatrixAvatar shared Component in alle Dateien einsetzen (erstellt aber noch nicht substituiert — zu viele Dateien fuer blinden Swap, erst nach Live-Test)

### Verify Gates — Spaces
- [ ] Space-Rail: Existierende Spaces sichtbar mit Tooltips
- [ ] Home-Button: Klick → alle Raeume sichtbar (kein Space-Filter)
- [ ] Space-Filter: Klick auf Space → RoomList zeigt nur dessen Raeume
- [ ] Space erstellen: "+" in Rail → CreateSpaceDialog → Name eingeben → Space erscheint in Rail
- [ ] Raum in Space: Neuen Raum erstellen mit Space-Zuordnung → erscheint im Space-Filter
- [ ] Raum zu Space hinzufuegen: Bestehenden Raum einem Space zuweisen → erscheint im Filter
- [ ] Space-Settings: Space-Icon Rechtsklick → Name/Avatar aendern
- [ ] getRoomHierarchy: Space mit ungejointem Raum → Raum sichtbar mit "Beitreten" Button
- [ ] Element X Mobile: Space-Struktur sichtbar in Element X (nach Cloudflare Tunnel Setup)

### Contacts (28.03.2026)

**Grundlagen:**
- Matrix hat kein klassisches Kontaktbuch — stattdessen DM-Liste + User Directory Search
- DM-Kontakte aus `m.direct` Account Data = implizite Kontakte
- Server-Suche via `client.searchUserDirectory({ term, limit })` = findet User auf dem Homeserver
- MSC4133 Extensible Profiles (Zukunft) = erweiterte Nutzerprofile, Cross-Server Suche

**Gebaut:**
- [x] `useContacts.ts` Hook — DM-Kontakte laden (sortiert nach Aktivitaet) + `searchUsers()` Server-Suche
- [x] `ContactPicker.tsx` — Autocomplete-Input mit Avatar + Name + User-ID
  - DM-Kontakte als "Kontakte" Sektion oben
  - Server-Suchergebnisse als "Verzeichnis" Sektion darunter
  - Debounced Suche (300ms)
  - Click-Outside schliesst Dropdown
- [x] `InviteDialog.tsx` → nach contacts/ umgezogen, nutzt ContactPicker statt nacktes Input
- [x] `CreateDMDialog.tsx` → nach contacts/ umgezogen, nutzt ContactPicker statt nacktes Input
- [x] `contacts/index.ts` — Barrel Export

**Contact-Sortierung:**
1. DM-Kontakte zuerst (zuletzt aktive oben)
2. Server-Suchergebnisse darunter (beim Tippen)
3. Online-Status visuell hervorgehoben (gruener Dot)

**Tuwunel Config — User Directory:**
- `show_all_local_users_in_user_directory = true` in allen 5 Config-Dateien gesetzt
- true = geschlossene Team-Instanz (alle App-User sollen sich finden koennen)
- false = wenn Federation aktiv oder fremde User auf der Instanz (Privacy)
- Bei Federation-Aktivierung auf false wechseln!

**Zukunft — MSC4133 Extensible Profiles:**
- Erweiterte Nutzerprofile mit mehr Infos (Bio, Links, etc.)
- Cross-Server User Directory Suche
- Noch nicht in stabiler Spec — beobachten und integrieren wenn verfuegbar

### Verify Gates — Contacts
- [ ] ContactPicker: Tippen → DM-Kontakte werden gefiltert angezeigt
- [ ] ContactPicker: Tippen → Server-Suche liefert Ergebnisse nach 300ms Debounce
- [ ] ContactPicker: Klick auf Kontakt → User-ID wird uebernommen
- [ ] ContactPicker: Online-Dot sichtbar bei aktiven DM-Kontakten
- [ ] InviteDialog: Oeffnen → Kontakte sichtbar → Klick → User wird eingeladen
- [ ] CreateDMDialog: Oeffnen → Kontakte sichtbar → Klick → DM wird erstellt
- [ ] Sortierung: DM-Kontakte vor Server-Ergebnissen, zuletzt aktive zuerst

### MatrixChat.tsx — Inline JSX Dokumentation (28.03.2026)

MatrixChat ist der Layout-Orchestrator (419 LOC). Alle Sub-Komponenten sind extrahiert.
Folgende kleine inline JSX Bloecke sind bewusst nicht in eigene Dateien extrahiert:
- Pinned Messages Banner (~15 LOC) — Button der InfoPanel oeffnet
- Invite View (~35 LOC) — Annehmen/Ablehnen UI bei membership=invite
- DM Waiting Banner (~10 LOC) — "Warte auf Antwort von X" bei invited DM
- Sync Status Banner (~8 LOC) — WiFi/Error Indicator bei Reconnect
- Empty State (~15 LOC) — "Raum auswählen" wenn kein Raum selektiert
Kein weiterer Extraktionsbedarf — diese Bloecke sind zu klein fuer eigene Dateien.

### LocationContent — TODO (28.03.2026)

LocationContent (`message/content/LocationContent.tsx`) existiert aber hat minimale Funktionalitaet:
- Aktuell: Nur ein klickbarer OpenStreetMap Link (`geo:lat,lon` → OSM URL)
- Kein Karten-Preview/Thumbnail im Chat
- Kein Location-Picker zum Senden (User kann keinen Standort teilen)
- Matrix Spec: `m.location` mit `geo_uri` Feld

- [ ] **Location-Preview**: Statisches Karten-Bild (OSM Static Map API oder Mapbox) statt nur Text-Link
- [ ] **Location-Picker**: Button im Composer → Browser Geolocation API → sendet `m.location` Event
- [ ] Kompatibilitaet pruefen: Wie zeigt Element X Mobile Location-Messages an?

### Client→Server Analyse — TODO (28.03.2026)

Gesamten Matrix Frontend-Code analysieren: was laeuft clientseitig das serverseitig besser waere?

**Bekannte Faelle:**
- `useRoomMembers.ts`: fetch auf `/_matrix/client/v3/rooms/{roomId}/joined_members` weil
  Sliding Sync SDK `getJoinedMembers()` nicht alle Members cached → Workaround
- `useSpaces.ts`: liest `m.space.child` aus lokalem State statt `getRoomHierarchy()` Server-API
  → zeigt nur gejoinete Raeume, nicht alle im Space

**Zu pruefen:**
- [ ] Gibt es weitere Stellen wo SDK bei Sliding Sync unvollstaendige Daten liefert?
- [ ] Room-Liste: `useRooms.ts` nutzt SDK Room-Events — reicht das bei Sliding Sync oder fehlen Raeume?
- [ ] Read Receipts: Werden die korrekt ueber Sliding Sync synchronisiert?
- [ ] Typing Indicators: Kommen die zuverlaessig ueber Sliding Sync?
- [ ] Thread-Liste: `room.getThreads()` — liefert Sliding Sync alle Threads oder nur gesehene?
- [ ] Search: `SearchPanel.tsx` nutzt `client.searchRoomEvents()` — ist das serverseitig (ja) oder clientseitig?
- [ ] Power-Levels: Werden die bei Sliding Sync immer korrekt geladen? (required_state konfiguriert in MatrixProvider)

**Ziel:** Alle Stellen identifizieren wo Server-API-Calls noetig sind statt sich auf SDK-Cache zu verlassen.
Sliding Sync ist performanter aber cached nicht alles — deshalb ist diese Analyse wichtig.

### Profil-Location bei Portierung
- Aktuell: Profil-Avatar in Space-Rail (unten)
- Bei Portierung zum Hauptprojekt: Profil in App-Settings (Hauptprojekt hat eigenes Settings-UI)
- Chat-Komponente sollte kein eigenes Profil-UI haben

### MessageComposer Refactoring (zu evaluieren)
- Aktuell 634 LOC, reviewed in exec-07 Phase 9 — bewusst zusammen gelassen (Refs stark verflochten)
- Option: Aufbrechen in composer/ mit Hooks (useVoiceRecording, useFileUpload, useSendMessage)
- Vorteil: Hooks wiederverwendbar (z.B. Voice Recording im ThreadPanel), ~380 LOC verteilt
- Risiko: Geteilte Refs (recorderRef, audioChunksRef) machen Hook-Extraktion nicht trivial
- Entscheidung: Evaluieren wenn Composer erweitert wird oder bei Portierung

### api.ts fuer zentralisierte Matrix-API-Calls (zu evaluieren)
- Aktuell sind Fetch-Calls (fetchRoomMembers, setRoomAvatar, setUserAvatar) inline in Hooks/Komponenten
- Lohnt sich wenn: mehrere Stellen gleiche Calls brauchen, Error-Handling/Retry zentralisiert, bei Portierung
- Aktuell kein Duplikat → kein akuter Bedarf
- **Hinweis fetch in useRoomMembers:** `room.getJoinedMembers()` liefert bei Sliding Sync nicht alle Members
  (SDK cached nur die die der Client bisher "gesehen" hat). Deshalb holt der Hook Members via REST API
  (`/_matrix/client/v3/rooms/{roomId}/joined_members`) mit SDK-Cache als Fallback. Wenn Sliding Sync
  das irgendwann korrekt cached, kann der fetch weg und `room.getJoinedMembers()` reicht allein.

### Element X Web Feature-Paritaet (28.03.2026)

**2. Virtualisierte Room List:**
- [x] RoomList mit `@tanstack/react-virtual` virtualisiert (VirtualizedRoomList Komponente in RoomList.tsx)
- Invites bleiben oben (nicht virtualisiert, wenige), filteredRooms virtualisiert
- estimateSize 60px, overscan 5

**3. Rich Text Editor (WYSIWYG Composer):**
- [x] ~~`@vector-im/matrix-wysiwyg`~~ → **Tiptap** (`@tiptap/react` + `starter-kit` + Extensions)
  - Grund: Element WYSIWYG ist Monorepo-locked (`@vector-im/matrix-wysiwyg-wasm` nicht auf npm)
  - Tiptap: ProseMirror-basiert, headless, MIT — funktional identisch für unseren Use-Case
  - WASM Config (`asyncWebAssembly: true`) war bereits für matrix-sdk-crypto vorhanden
- [x] MessageComposer Textarea durch WysiwygEditor ersetzt (`composer/WysiwygEditor.tsx`)
- [x] Formatting-Toolbar: Bold, Italic, Strikethrough, Code, Code-Block, Liste, Nummerierte Liste, Quote
- [x] Senden: `format: "org.matrix.custom.html"` + `formatted_body` (nur wenn HTML-Formatierung vorliegt)
- [x] **User-Mentions** (`@`): Tiptap Mention Extension mit Room-Members Autocomplete
  - Pill-Rendering: `<a href="https://matrix.to/#/@user:server">@displayname</a>`
  - `m.mentions.user_ids` Array wird beim Senden gesetzt (MSC3952)
- [x] **Agent-Mentions** (`@agent-*`): Visuell unterschieden — lila "AI" Avatar + "Agent" Badge im Dropdown
  - Nutzt `isAgentUser()` aus resolvers.ts zur Erkennung
  - Technisch gleicher m.mentions.user_ids Eintrag wie User
- [x] **@room Mention**: Spezieller Eintrag im @-Dropdown ("Alle benachrichtigen", Megaphone-Icon)
  - Setzt `m.mentions.room: true` (MSC3952 Room Notification)
  - Braucht Power-Level (Server-seitig geprüft via `.m.rule.is_room_mention` Push Rule)
- [x] **Room-Pills** (`#`): Separater Tiptap Mention Extension mit `#`-Trigger
  - Autocomplete aus gejointen Räumen (non-DM)
  - Pill: `<a href="https://matrix.to/#/!roomId">#roomname</a>`
  - Kein m.mentions-Eintrag (nur Permalink, keine Notification)
- Dateien:
  - `composer/WysiwygEditor.tsx` — Tiptap Editor + Formatting Toolbar + Ref-API
  - `composer/MentionList.tsx` — Mention-Dropdown UI (User/Agent/@room/Room-Pill)
  - `composer/mentionSuggestion.ts` — Suggestion Configs (getrennt für @ und #)

**Verify-Gate Slice 4 Punkt 3 (WYSIWYG):**
- [ ] Nachricht mit **Bold/Italic/Code** senden → Empfänger sieht formatted_body korrekt in TextContent
- [ ] **@user** tippen → Dropdown erscheint, Auswahl fügt Pill ein, Empfänger sieht gelbes Mention-Highlight
- [ ] **@agent-** tippen → Agent erscheint mit lila Badge im Dropdown, Pill wird korrekt gesetzt
- [ ] **@room** tippen → "Alle benachrichtigen" erscheint, Senden setzt `m.mentions.room: true`
- [ ] **#room** tippen → Raum-Dropdown erscheint, Auswahl fügt Room-Pill ein (klickbarer Permalink)
- [ ] **Edit-Modus** → Editor wird mit bestehendem Body befüllt, Senden aktualisiert formatted_body
- [ ] **Reply + Thread** → formatted_body wird korrekt mit m.relates_to gesendet
- [ ] **Plain text** (keine Formatierung) → kein `format`/`formatted_body` im Event (Backwards-Compat)

**4. MatrixRTC / LiveKit Calls (Option B — direkte Integration):**
- **Entscheidung:** Option B (LiveKit SDK direkt + MatrixRTC Signaling)
  - Option A (iframe Widget) verworfen: Antipattern, kein Styling-Kontrolle, Performance-Overhead
  - Option C (Legacy VoIP) deprecated in matrix-js-sdk, keine Element X Kompatibilitaet
- [x] **Backend:**
  - LiveKit SFU Binary: `tools/livekit-server.exe` (v1.10.0, Windows native)
  - lk-jwt-service Binary: `tools/lk-jwt-service` (v0.4.1, Linux/WSL)
  - Config: `homeserver/livekit.yaml` (Port 7880, UDP 50000-50200)
  - In devstack.ps1 integriert (`-NoLiveKit` Flag zum Deaktivieren)
- [x] **Tuwunel Config:**
  - `[[global.well_known.rtc_transports]]` in allen 5 toml-Dateien
  - Clients entdecken LiveKit SFU automatisch via `.well-known/matrix/client`
  - `org.matrix.msc4143.rtc_foci` wird von Tuwunel nativ unterstuetzt
- [x] **Frontend Packages:** `livekit-client@2.18.0` + `@livekit/components-react@2.9.20`
- [x] **`useMatrixRTCCall.ts`** — neuer Hook (ersetzt deprecated `useCall.ts`):
  - `matrix-js-sdk` MatrixRTCSession fuer m.rtc.member State Events
  - OpenID Token → lk-jwt-service → LiveKit JWT Austausch
  - `joinCall(roomId, "m.voice" | "m.video")` / `leaveCall()`
- [x] **`CallOverlay.tsx`** — komplett neu mit LiveKit React Components:
  - `<LiveKitRoom>` + `<VideoConference />` Prefab (Grid, Focus, ScreenShare, Controls)
  - `<RoomAudioRenderer />` fuer Voice-Only Teilnehmer
  - Joining-Spinner + Hangup-Button + Teilnehmerzaehler
- [x] **MatrixChat.tsx** — `useCall()` → `useMatrixRTCCall()` migriert
- Unterstuetzt: 1:1 Voice, 1:1 Video, Gruppen-Voice, Gruppen-Video, Screen Sharing
- [x] **Media-E2EE:**
  - `MatrixKeyProvider.ts` — Brücke: matrix-js-sdk Keys → LiveKit SFrame Encryption
  - `manageMediaKeys: true` aktiviert — matrix-js-sdk generiert + verteilt Keys via m.rtc.member
  - `EncryptionKeyChanged` Event → `MatrixKeyProvider.setEncryptionKey()` → LiveKit E2EE Worker
  - Call-E2EE ist **unabhängig** von Raum-E2EE (Megolm) — Calls sind immer verschlüsselt
  - Grünes Shield-Icon + "E2EE" Badge in CallOverlay wenn aktiv
- [x] Legacy `useCall.ts` (deprecated MSC2746) entfernt

**UI-Abdeckung:**
- [x] **1:1 Voice** — Phone-Button in RoomHeader → `<AudioConference />` (kompaktes Audio-UI)
- [x] **1:1 Video** — Video-Button in RoomHeader → `<VideoConference />` (Grid + Focus + ScreenShare)
- [x] **Gruppen-Voice** — Phone-Button auch in Gruppen-Raeumen (LiveKit SFU skaliert)
- [x] **Gruppen-Video** — Video-Button auch in Gruppen-Raeumen
- [x] Call-Buttons in RoomHeader fuer DMs UND Gruppen-Raeume (nicht mehr nur DMs)
- [x] `isVoiceOnly` Flag steuert ob AudioConference oder VideoConference angezeigt wird
- [x] `video={!isVoiceOnly}` — Kamera wird bei Voice-Calls nicht aktiviert

**Verify-Gate Slice 4 Punkt 4 (MatrixRTC):**
- [ ] LiveKit SFU + lk-jwt-service starten (devstack.ps1)
- [ ] Tuwunel `.well-known` liefert `org.matrix.msc4143.rtc_foci` mit LiveKit URL
- [ ] **Voice Call (1:1)** → AudioConference UI, nur Mic aktiv, kein Video
- [ ] **Video Call (1:1)** → VideoConference UI, Grid mit Kamera
- [ ] **Gruppen-Voice** → AudioConference mit mehreren Teilnehmern
- [ ] **Gruppen-Video** → VideoConference Grid mit Pagination
- [ ] **E2EE** → Gruenes Shield-Badge sichtbar, Keys via m.rtc.member verteilt
- [ ] Call beenden → `leaveRoomSession()`, m.rtc.member State geraeumt
- [ ] Element X Mobile kann dem gleichen Call beitreten (Interop-Test)

**5. Permalinks (matrix.to In-App Navigation):**
- [x] matrix.to Links in Nachrichten als In-App Navigation (TextContent.tsx linkifyText erweitert)
  - `parseMatrixPermalink()` erkennt @user, !roomId, $eventId aus matrix.to URLs
  - Rendert als klickbarer Button statt externem Link
  - Dispatcht `window.CustomEvent("matrix:navigate")` fuer MatrixChat Navigation
- [x] MatrixChat Event-Listener fuer `matrix:navigate` implementiert
  - `type: "room"` → Raum oeffnen (Match via roomId oder Alias-Name)
  - `type: "user"` → DM oeffnen falls vorhanden
  - Toast-Fehler wenn Raum nicht gefunden

**6. Keyboard Shortcuts:**
- [x] `useKeyboardShortcuts.ts` Hook gebaut + in MatrixChat verdrahtet
- [x] **Pfeil-Oben im leeren Composer** → letzte eigene Nachricht im Edit-Modus (`onEditLastMessage`)
- [x] **Ctrl+K** → oeffnet Search Panel (kontextabhaengig via `data-matrix-chat` Attribut)
- [x] **Esc** → schliesst aktives Panel (Thread → Search → Settings → Overview → Activity → SpaceSettings)
- [x] **Shift+Enter** → neue Zeile (implizit via Textarea)
- [x] **Pfeiltasten** in RoomList → Raum-Navigation (ArrowUp/Down, scrollToIndex)

**7. SOTA 2026 Package Upgrades (TODO):**
- [ ] `react-shiki` — VS Code Syntax Highlighting fuer Code-Bloecke in TextContent.tsx
- [ ] `motion` — framer-motion Successor, Import `motion/react` statt `framer-motion`
- [x] `@livekit/track-processors` — Background Blur in CallOverlay.tsx eingebaut
  - `BackgroundBlur(10)` als Default Video Processor
  - Graceful Fallback wenn nicht verfuegbar
- [ ] `@formkit/auto-animate` — zero-config List-Animations (RoomList, Timeline)
- Packages sind installiert, auto-animate Umstellung erfolgt in separatem Schritt

**Verify-Gate Punkt 7 (SOTA Packages):**
- [ ] Background Blur sichtbar bei Video-Call (unscharfer Hintergrund)
- [ ] Blur deaktivierbar falls Performance-Probleme

### Audio-Nachricht
- Recording-UI implementiert (Mic/MicOff, Timer, Send)
- Upload als `m.audio` mit `org.matrix.msc3245.voice` Flag
- Playback: AudioContent rendert Voice-Pill mit `<audio>` Controls
- **Voraussetzung:** Mikrofon am PC angeschlossen

### UrlPreview
- Funktional vorhanden, wird für Nachrichten von anderen gerendert
- Styling angemessen (OG-Image + Title + Description + Hostname)

### Online-Status Dots
- Code vorhanden (`room.isOnline` → grüner Dot am Avatar)
- Nur bei DMs mit Online-Users sichtbar
- Nicht visuell testbar ohne zweiten eingeloggten User

### Profil bei Portierung
- Siehe `specs/10-portierung.md` — Option A (Sync vom Hauptprojekt)
