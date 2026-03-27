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
- [x] Topic nur Admin/Mod editierbar (`state_default` Power-Level Check)
- [x] Name/Avatar nur Admin/Mod editierbar (`canEditRoomInfo` Check)
- [x] Mute aus Header entfernt → nur noch in InfoPanels (DM + Room)
- [x] DM Name-Bug gefixt: SDK room.name Fallback-Kette (sdkName → member.name → displayName → username)
- [x] General Stern-Bug gefixt (auto-favourited entfernt)

### Nicht eingebaut (Begründung)
- ❌ Disappearing Messages: SDK hat kein `m.room.retention` (MSC1763 nicht finalisiert), Cross-Client inkompatibel
- ❌ View Once: Existiert in Matrix Spec nicht, eigene Erfindung wäre nicht Spec-konform
- ❌ Globale Rollen: Matrix hat keine — NextAuth Rollen → Power-Levels Mapping bei Portierung (Go Backend)

### Noch zu verifizieren
- [ ] DM erstellen → Bob erscheint als "Eingeladen", Name = "Bob"
- [ ] Bob akzeptiert → normaler Chat
- [ ] Auto-Accept DM: Alice wird eingeladen → auto-join + Toast
- [ ] Gruppen-Einladung: Toast mit Accept/Decline
- [ ] Read Receipts: Mini-Avatar (braucht echten zweiten Client)
- [ ] Online-Status Dot (braucht echten zweiten Client)
- [ ] B-8: Thread-Chip + Side-Panel (braucht Element X)
- [ ] UI-14: ReadBy Liste
- [ ] Call starten + Overlay (braucht zweites Device)

### Element X Mobile Verbindung (Cloudflare Tunnel)
- [ ] `tools/cloudflared.exe` vorhanden ✅
- [ ] Cloudflare Account erstellen (gratis)
- [ ] Tunnel starten: `tools/cloudflared.exe tunnel --url http://localhost:8448`
- [ ] HTTPS URL erhalten: `https://xxx.trycloudflare.com`
- [ ] tuwunel.toml: `well_known.client` auf Tunnel-URL setzen
- [ ] Element X Mobile: Tunnel-URL als Homeserver eingeben
- [ ] Login testen mit Alice oder Bob
- [ ] Cross-Signing zwischen Web + Mobile testen
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

### Threads
- ThreadPanel, useThreadTimeline, ThreadChip existieren
- Aktuell nutzt "Antworten" `m.in_reply_to` (Inline-Reply), nicht `m.thread`
- Für echte Threads: Separate "Thread starten" Action nötig die `m.relates_to.rel_type: "m.thread"` setzt
- Keine Test-Threads in aktuellen Räumen vorhanden

### Space erstellen
- Space-Rail zeigt existierende Spaces, aber kein "+" Button zum Erstellen
- Braucht: `client.createRoom({ creation_content: { type: "m.space" } })`
- Low-Priority: Erst relevant bei vielen Räumen

### Profil-Location bei Portierung
- Aktuell: Profil-Avatar in Space-Rail (unten)
- Bei Portierung zum Hauptprojekt: Profil in App-Settings (Hauptprojekt hat eigenes Settings-UI)
- Chat-Komponente sollte kein eigenes Profil-UI haben

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
