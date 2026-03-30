# exec2-04: Verify-Gates (Gesammelt)

> Alle Verify-Gates aus exec2-01/02/03 + exec-04 an einer Stelle.
> Reihenfolge: so wie man beim DevStack-Start logisch durchgehen wuerde.
> Stand: 30.03.2026

---

## A. Infrastruktur (zuerst pruefen — ohne das laeuft nichts)

### A1. Homeserver
- [ ] Tuwunel startet ohne Fehler mit aktuellem Config
- [ ] Neuer Raum wird mit Room Version 12 erstellt
- [ ] `rocksdb_direct_io = false` → keine I/O-Fehler in Logs
- [ ] DB-Backup-Verzeichnis wird erstellt nach erstem Start
- [ ] `GO_ENV=development` → `.env.development` geladen (Go Appservice)
- [ ] Keine `changeme` Platzhalter in `.env` Dateien

### A2. Sliding Sync
- [ ] Raumliste laedt unter 500ms bei 20+ Raeumen
- [ ] DevTools → Network: Request geht an `simplified_msc3575/sync`
- [ ] Keine unnoetige Events fuer nicht-sichtbare Raeume

### A3. LiveKit + lk-jwt-service
- [ ] LiveKit SFU startet auf Port 7880
- [ ] lk-jwt-service startet auf Port 8080
- [ ] Tuwunel `.well-known` liefert `org.matrix.msc4143.rtc_foci` mit LiveKit URL

### A4. Env Variablen
- [ ] `MATRIX_AGENT_PREFIX=agent-` in allen `.env` Dateien
- [ ] `NEXT_PUBLIC_MATRIX_AGENT_PREFIX=agent-` in `.env.local`
- [ ] `NEXT_PUBLIC_LK_JWT_SERVICE_URL=http://localhost:8080` in `.env.local`

---

## B. Auth + E2EE (danach — Security-Basis)

### B1. E2EE Grundfunktion
- [ ] Go Appservice startet mit `[e2ee] OlmMachine geladen` Log
- [ ] Go Appservice Keys auf Homeserver hochgeladen (`/keys/upload`)
- [ ] Browser initialisiert Rust Crypto ohne Fehler (DevTools Console)
- [ ] User sendet Nachricht → Browser verschluesselt (m.room.encrypted)
- [ ] Page-Reload → kein Full-Resync (IndexedDB), Nachrichten sofort da
- [ ] Keine `M_UNKNOWN_TOKEN` Fehler beim Key Upload
- [ ] Keine `UNABLE_TO_DECRYPT` in der UI

### B2. Cross-Signing
- [ ] Go Bootstrap: `cross_signing_seeds.json` erstellt
- [ ] Go Restart: Seeds geladen aus Datei
- [ ] Bot-Geraet erscheint als cross-signed in Element X (kein Warndreieck)
- [ ] Web App Banner: Unverifiziert → gelbes Banner mit "Verifizieren"-Button
- [ ] QR-Code Flow: Modal → QR → Element X scannt → beide bestaetigen → Banner weg
- [ ] SAS Fallback: 7 Emojis vergleichen wenn QR nicht verfuegbar
- [ ] Abbruch-Test: Element X bricht ab → UI springt zurueck (kein Haenger)

### B3. Key Backup
- [ ] `MATRIX_KEY_BACKUP_PASSWORD` gesetzt
- [ ] Nachricht empfangen → `megolm_keys_backup.bin` erstellt/aktualisiert
- [ ] Appservice stoppen → Log: `"E2EE: key backup exported"`
- [ ] Neues Deployment + vorhandene Backup-Datei → Keys importiert, alte Nachrichten lesbar

### B4. MSC4381
- [ ] Go sendet encrypted Event → kein `sender_key`, kein `device_id` im Content
- [ ] Empfaenger (Browser + Element X) koennen trotzdem entschluesseln

---

## C. Chat Core (Grundfunktionen testen)

### C1. Nachrichten
- [ ] Text senden + empfangen
- [ ] formatted_body: `<table>`, `<code>`, `<strong>` korrekt als HTML gerendert
- [ ] HTML mit `*Sternchen*` wird NICHT als Markdown-Italic interpretiert
- [ ] XSS-Versuch (`<script>alert(1)</script>`) wird geblockt
- [ ] `style="color: red"` funktioniert, Injection-Styles werden entfernt

### C2. Message Actions
- [ ] Hover → Edit, React, Delete, Reply, Forward sichtbar
- [ ] Edit → Edit-Banner, nach Save `(bearbeitet)` Badge
- [ ] Escape → Edit abbrechen
- [ ] Element X zeigt edierte Nachricht korrekt
- [ ] Loeschen → `[Nachricht geloescht]`, keine Actions auf geloeschten Nachrichten
- [ ] Element X zeigt geloeschte Nachricht korrekt

### C3. Reactions
- [ ] Hover → Emoji-Picker erscheint
- [ ] Klick auf Emoji → m.reaction gesendet, Picker schliesst
- [ ] Klick ausserhalb → Picker schliesst
- [ ] Reaktion sofort sichtbar
- [ ] Element X zeigt Reaktion korrekt

### C4. Read Receipts
- [ ] Raum wechseln → Element X zeigt Raum als "gelesen"
- [ ] Ungelesen-Zaehler in RoomList faellt auf 0
- [ ] Mini-Avatare unter eigenen Nachrichten (max 5)
- [ ] Lesen ohne neue Nachricht → Avatar erscheint sofort

### C5. Presence
- [ ] `allow_local_presence = true` in tuwunel.toml
- [ ] Alice online → gruener Punkt am Avatar in RoomList
- [ ] Alice schliesst Browser → gruener Punkt verschwindet (Timeout)

### C6. URL Previews
- [ ] Nachricht mit URL → Vorschau-Karte (Titel, Bild, URL)
- [ ] Preview nutzt eigenen Token (DevTools → Authorization Header)
- [ ] Cache: kein Doppel-Fetch bei erneutem Rendern

### C7. Mentions
- [ ] Nachricht mit eigenem @handle → gelb hervorgehoben
- [ ] Nachricht ohne @handle → normales Background
- [ ] Bot-Nachrichten zeigen "AI" Avatar + "Agent" Badge
- [ ] Prefix aendern → Go + Next.js erkennen neue Bot-IDs

---

## D. Erweiterte Features

### D1. Polls (MSC3381)
- [ ] "Abstimmung erstellen" Button sichtbar
- [ ] Dialog: Frage + min. 2 Antworten eingeben
- [ ] Poll als Karte in Timeline (nicht als Text)
- [ ] Klick auf Antwort → Stimme gesendet, Progress-Bar aktualisiert
- [ ] Andere User sehen Stimme reaktiv
- [ ] Element X zeigt Poll korrekt
- [ ] Beendete Poll: Buttons disabled

### D2. Threads (MSC3440)
- [ ] Thread starten → "N Antworten" Chip erscheint
- [ ] Chip klicken → Side-Panel (380px) oeffnet
- [ ] Reply im Panel senden → erscheint sofort
- [ ] Reply-Count aktualisiert sich reaktiv
- [ ] Thread-Reply erscheint NICHT in Main-Timeline
- [ ] X-Button → Panel schliesst
- [ ] Raumwechsel → Panel schliesst automatisch
- [ ] Element X zeigt Thread-Replies korrekt

### D3. Media
- [ ] Bilder in m.image laden korrekt (ueber Media Proxy)
- [ ] Thumbnails laden
- [ ] `allow_legacy_media = false` → Media funktioniert trotzdem
- [ ] Video/Audio streamen korrekt
- [ ] Tuwunel-Logs: keine 401 fuer Media-Requests

---

## E. WYSIWYG Composer (Tiptap)

- [ ] **Bold/Italic/Code** senden → Empfaenger sieht formatted_body in TextContent
- [ ] **@user** tippen → Dropdown, Auswahl fuegt Pill ein, Empfaenger sieht gelbes Highlight
- [ ] **@agent-** tippen → Agent mit lila Badge im Dropdown
- [ ] **@room** tippen → "Alle benachrichtigen" erscheint, m.mentions.room = true
- [ ] **#room** tippen → Raum-Dropdown, Auswahl fuegt Room-Pill ein (Permalink)
- [ ] **Edit-Modus** → Editor mit bestehendem Body befuellt
- [ ] **Reply + Thread** → formatted_body korrekt mit m.relates_to
- [ ] **Plain text** → kein format/formatted_body im Event

---

## F. MatrixRTC / LiveKit Calls

### F1. Voice Call (1:1)
- [ ] Phone-Button → AudioConference UI, nur Mic aktiv, kein Video

### F2. Video Call (1:1)
- [ ] Video-Button → VideoConference UI, Grid mit Kamera

### F3. Gruppen-Voice
- [ ] Phone-Button in Gruppen-Raum → AudioConference mit mehreren Teilnehmern

### F4. Gruppen-Video
- [ ] Video-Button in Gruppen-Raum → VideoConference Grid mit Pagination

### F5. E2EE + Features
- [ ] Gruenes Shield-Badge sichtbar (E2EE aktiv)
- [ ] Keys via m.rtc.member verteilt
- [ ] Background Blur sichtbar bei Video-Call
- [ ] Call beenden → leaveRoomSession(), m.rtc.member State geraeumt

### F6. Interop
- [ ] Element X Mobile kann dem gleichen Call beitreten

---

## G. Navigation + Shortcuts

- [ ] Permalink klicken → Raum oeffnet
- [ ] User-Permalink klicken → DM oeffnet (falls vorhanden)
- [ ] Pfeil-Oben im leeren Composer → letzte eigene Nachricht im Edit-Modus
- [ ] Ctrl+K → Search Panel oeffnet
- [ ] Esc → aktives Panel schliesst
- [ ] Pfeiltasten in RoomList → Raum wechselt, scrollt mit

---

## H. SOTA Packages (optional — funktioniert auch ohne)

- [ ] Background Blur: unscharfer Hintergrund bei Video-Call
- [ ] Blur deaktivierbar falls Performance-Probleme
