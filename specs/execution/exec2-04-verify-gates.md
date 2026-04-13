# exec2-04: Verify-Gates (Gesammelt)

> Alle Verify-Gates aus exec2-01/02/03 + exec-04 an einer Stelle.
> Reihenfolge: so wie man beim DevStack-Start logisch durchgehen wuerde.
> Stand: 30.03.2026

---

## Offene Tasks (aus exec2-01/02/03 + exec-04)

### Extern blockiert (kein Action moeglich)
- Siehe: `exec-blocking.md` (Matrix-Protokoll-Blocker)

### Code-Tasks (Matrix Chat)
- [x] react-shiki in Matrix TextContent.tsx umstellen (Syntax Highlighting)
- [x] motion Import in Matrix Components umstellen (framer-motion → motion/react)
- [x] auto-animate in Matrix RoomList/Timeline einbauen
- [x] Location Content: OpenStreetMap-Embed statt Link (10.04.2026, shared/ Components)
- [ ] Client→Server Analyse: welche API Calls optimierbar
- [ ] api.ts fuer zentralisierte Matrix-API-Calls evaluieren

### Federation + Security (Backlog — erst bei Prod-Deployment)
- Siehe: `exec-eval.md` (Prod/Deployment-abhängige Verify-Gates)

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

## D. Erweiterte Features (brauchen teils zweiten Client / Element X Mobile)

### D0. Grundfunktionen mit zweitem Client
- [ ] Unread-Badge erscheint bei neuer Nachricht von anderem User
- [ ] Ungelesen-Zaehler faellt auf 0 nach Raumwechsel
- [ ] Read Receipts: Mini-Avatar erscheint wenn anderer User liest
- [ ] Online-Status Dot bei DM (braucht echten zweiten Client)
- [ ] Nachrichten von anderem User: Bubble links, Sender-Farbe
- [ ] Thread-Chip + Side-Panel (braucht Element X fuer Thread-Start)
- [ ] ReadBy Liste (braucht Read Receipts sichtbar)
- [ ] Call starten + Overlay (braucht zweites Device)

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

---

## I. Connectivity + Tunnel (exec2-03b / 11.04.2026)

### I1. Cloudflare Quick Tunnel im devstack
- [x] `.\scripts\dev-stack2.ps1 -Tunnel` startet cloudflared als erste Wahl (nicht ngrok/bore)
- [x] Terminal-Summary zeigt gelbe Zeile `Tunnel (Element X): https://*.trycloudflare.com`
- [x] URL wird innerhalb von 5 Minuten extrahiert (Poll aus `logs/dev-stack/tunnel.stderr.log`)
- [x] Status-Updates alle 15 Sekunden waehrend Wait — Code vorhanden, nicht beobachtet (URL kam in <2 Sekunden)
- [ ] Bei Timeout: rote TIMEOUT-Meldung + letzte 5 Log-Zeilen sichtbar — Code vorhanden, nicht getestet (kein Timeout-Fall)
- [x] End-to-End HTTPS via Tunnel: `curl https://*.trycloudflare.com/_matrix/client/versions` → HTTP 200, 244 ms, valide Matrix JSON
- [ ] Element X (Mobile) kann sich mit der `trycloudflare.com` URL verbinden — Client-Test ausstehend
- [ ] Login + Raumliste + Nachricht senden funktioniert ueber Tunnel — Client-Test ausstehend

**Nebenfund gefixt:** `Register-Service -Port 0` Services (z.B. cloudflared Tunnel) ueberspringen Port-Check jetzt mit `[tunnel] Launched (client-only, no port check)`. Kein False-Positive `WARNING: 1 failed` mehr. Gleicher Fix auch im Watch-Restart-Loop angewendet.

### I2. Upload-Limit auf Cloudflare Free Plan aligned
- [x] Alle 5 Tuwunel-Configs enthalten `max_request_size = 104857600  # 100 MB`:
  - [x] `homeserver/tuwunel.toml`
  - [x] `homeserver/tuwunel.example.toml`
  - [x] `homeserver/tuwunel.image.toml`
  - [x] `homeserver/tuwunel.image.example.toml`
  - [x] `homeserver/tuwunel.prod.toml`
- [ ] Upload > 100 MB gibt 413 Payload Too Large zurueck (nicht irgendwo stumm haengen) — Client-Test ausstehend
- [ ] Upload ≤ 100 MB geht ueber CF-Tunnel durch ohne Fehler — Client-Test ausstehend

---

## J. Tuwunel v1.6.0-rc Upgrade (exec2-03b / 11.04.2026)

### J0. Pre-Flight (einmalig vor erstem RC-Start)
- [x] `tools/tuwunel-v1.6` existiert, chmod +x, `wsl ./tools/tuwunel-v1.6 --version` zeigt `tuwunel 1.6.0`
- [x] `homeserver/tuwunel.v1.6.toml` existiert, enthaelt `database_path = "./homeserver/data/db"` (shared)
- [x] `_ref/tuwunel-v1.6.0-rc/` enthaelt: `tuwunel-example.toml`, `COMPARISON.md`, `TESTING.md`, `storage-provider-schema.rs`
- [x] `scripts/backup-before-v1.6.ps1` laeuft, refused bei Port 8448 belegt, refused bei existierendem Backup
- [x] Backup erzeugt: `homeserver/data/db-pre-v1.6` und `homeserver/data/media-pre-v1.6` vorhanden mit Inhalt

### J1. Phase 1 — Smoke-Test ohne S3
- [x] `.\scripts\dev-stack2.ps1 -Tuwunel16` startet ohne Crash
- [x] Gelbe Meldung `[tuwunel] Using v1.6.0-rc (...)` beim Start sichtbar
- [x] Schema-Migration laeuft in < 30 Sekunden durch (`Loaded RocksDB database with schema version 17`)
- [x] `logs/dev-stack/tuwunel.stderr.log` zeigt keine Panics / Errors (leer)
- [x] HTTP Listener aktiv: `Listening on ["tcp:0.0.0.0:8448"]`
- [x] `http://127.0.0.1:8448/_matrix/client/versions` antwortet mit gueltiger JSON (HTTP 200, zeigt Matrix v1.15 + unstable_features inkl. msc2964/65/66/67, msc2815, msc3814, simplified_msc3575, msc3916.stable)
- [ ] Element X Login funktioniert (nach einmaligem Re-Login wegen Token-Wechsel akzeptabel) — Mobile-Geraet-Test ausstehend
- [ ] Bestehende Raume sichtbar, Historie lesbar — Client-Test ausstehend
- [ ] Text-Nachricht senden + empfangen — Client-Test ausstehend
- [ ] Bild < 100 MB posten, erscheint in Timeline — Client-Test ausstehend
- [x] **Abbruch-Kriterien NICHT erfuellt:** Tuwunel crasht nicht, Config parst, alle Services OK

### J2. Rollback-Fahigkeit
- [ ] Devstack stoppen, DB aus `db-pre-v1.6` zurueckkopieren, v1.5.1 startet wieder
- [ ] Nach Rollback: `.\scripts\dev-stack2.ps1` (ohne `-Tuwunel16`) startet v1.5.1 sauber
- [ ] Historie und Raume wie vor dem RC-Test vorhanden

### J3. Phase 2 — S3 Storage Provider aktivieren
- [x] **Provider DEFINIERT in Config (Service-Level verifiziert):** `media_storage_providers = ["media", "seaweedfs"]`
- [x] SeaweedFS-Startup-Check prueft Bucket-Erreichbarkeit (`startup_check = true`) → erfolgreich
- [x] Log zeigt `Connected to storage provider name=seaweedfs` (Service-Registration erfolgreich)
- [x] SeaweedFS Bucket `matrix-media` existiert (manuell via `aws s3 mb` erstellt)
- [x] **`store_media_on_providers = ["seaweedfs"]` aktiviert** — Config umgestellt, Tuwunel startet sauber, beide Provider connected
- [ ] Neues Bild posten → Blob liegt in SeaweedFS unter `matrix-media/tuwunel-v1.6/...` — Client-Test ausstehend
- [ ] Via SeaweedFS Filer UI (`http://localhost:8888`) ist der Blob sichtbar — Client-Test ausstehend
- [ ] Element X kann das frische Bild wieder oeffnen (Download via S3) — Client-Test ausstehend
- [ ] Altes Bild (aus Phase 1 oder vor RC) ist weiterhin lesbar (Fallback-Pfad `media` aktiv) — Client-Test ausstehend

### J4. Phase 3 — MSC2246 Async Upload verifizieren
- [ ] Element X Version mit MSC2246 Support (mind. v0.8+)
- [ ] Grosses Bild (~50 MB) posten
- [ ] `logs/dev-stack/tuwunel.stderr.log` zeigt getrennte Requests:
  - [ ] `POST /_matrix/media/v1/create`
  - [ ] `PUT /_matrix/media/v3/upload/matrix.local/<mediaId>`
- [ ] Falls nur `POST /_matrix/media/v3/upload` sichtbar → Client nutzt Legacy-Pfad (kein Abbruch, nur Info)

### J5. Phase 4 — max_request_size erhoehen (optional, nur LAN-Test)

> **BLOCKED by [tuwunel#411](https://github.com/matrix-construct/tuwunel/issues/411):**
> S3-Backend hat single-stream PUT/GET mit 180s Hard-Timeout. Files > ~200 MB loesen
> Transport-Timeout + 500 Internal Server Error aus. Betrifft alle S3-kompatiblen Stores
> (gemeldet fuer Cloudflare R2, gleicher S3-Client-Code auch fuer SeaweedFS).
> Unser 100 MB Cap schuetzt uns — NICHT erhoehen bis #411 upstream gefixt ist.
> Sobald Tuwunel Multipart-Upload oder konfigurierbare Timeouts implementiert → Gate freigeben.

- [ ] `tuwunel.v1.6.toml`: `max_request_size = 524288000  # 500 MB`
- [ ] Element X direkt im LAN (`http://192.168.1.34:8448`, kein CF-Tunnel)
- [ ] Video ~200 MB hochladen
- [ ] Upload erfolgreich, als Blob in SeaweedFS sichtbar
- [ ] Wert **zurueck auf 100 MB** wenn CF-Tunnel wieder genutzt wird (sonst 413 downstream)

### J6. Merge-Entscheidung (Phase 5)
- [ ] Mindestens 3 Tage Betrieb ohne Regression
- [ ] v1.6.0 stable Release verfolgt (erwartet Ende April / Anfang Mai 2026)
- [ ] Entscheidung dokumentiert: RC produktiv nutzen ODER auf stable warten
- [ ] `tools/tuwunel` und `homeserver/tuwunel.toml` werden konsolidiert wenn Merge erfolgt
- [ ] `-Tuwunel16` Flag aus `dev-stack2.ps1` entfernt wenn Merge erfolgt
- [ ] `homeserver/data/db-pre-v1.6` und `media-pre-v1.6` erst loeschen wenn v1.6 stable laeuft

### J7. Bekannte v1.6 Upstream-Bugs — Tracking (Stand 11.04.2026)

> Diese Bugs existieren upstream in Tuwunel v1.6.0-rc. Wir koennen sie nicht selbst fixen,
> aber muessen sie beim Testing und bei der Go-Appservice-Integration beruecksichtigen.
> Upstream-Links tracken, bei Merge-Entscheidung (J6) erneut pruefen ob gefixt.

**[tuwunel#411](https://github.com/matrix-construct/tuwunel/issues/411) — S3 Large File Timeout (CRITICAL)**
- S3-Client nutzt single-stream PUT/GET mit 180s Hard-Timeout
- Files > ~200 MB → Transport-Timeout → 500 Internal Server Error
- Betrifft alle S3-kompatiblen Stores (R2, SeaweedFS, MinIO)
- **Workaround:** `max_request_size ≤ 100 MB` (bei uns gesetzt via CF-Cap-Alignment)
- **Blockiert:** Gate J5 (max_request_size erhoehen)
- **Go-Layer Impact:** Keiner direkt — Go Appservice nutzt eigene S3-Calls fuer Artifacts (nicht via Tuwunel)

**[tuwunel#401](https://github.com/matrix-construct/tuwunel/issues/401) — Appservice E2EE: kein device_id in /whoami (HIGH)**
- MSC3202 (Appservice E2EE) braucht `device_id` in `/whoami` Response
- Tuwunel liefert es nicht → bridges/bots die matrix-bot-sdk nutzen crashen
- **Go-Layer Impact:** MUSS GEPRUEFT WERDEN. Unser Go Appservice nutzt mautrix-go, nicht matrix-bot-sdk. mautrix-go hat einen anderen Auth-Flow — moeglicherweise nicht betroffen. Beim naechsten Go-Appservice-Test gegen v1.6 explizit pruefen ob `/whoami` device_id zurueckgibt.
- [ ] Go Appservice gegen v1.6 getestet: /whoami Response enthaelt device_id
- [ ] Falls nicht: Workaround in Go (device_id aus Config/Startup-State statt /whoami) ODER auf upstream fix warten

**[tuwunel#377](https://github.com/matrix-construct/tuwunel/issues/377) — device_lists.changed fehlt in /sync (MEDIUM)**
- Cross-Signing Key-Aenderungen und neue Device-Keys nicht im Sync-Response
- Clients sehen neuen Verifikations-Status erst nach Full-Resync
- **Go-Layer Proaktiver Workaround angewendet (11.04.2026):**
  `go-appservice/internal/crypto/machine.go:EnsureSession()` ruft jetzt `olm.FetchKeys(ctx, members, true)` auf bevor eine Megolm-Session geteilt wird. Das force-refreshed Device-Keys via `/keys/query` direkt, statt sich auf `/sync` device_lists.changed zu verlassen.
  - Non-fatal: Wenn FetchKeys fehlschlaegt, wird mit vorhandenen (evt. veralteten) Keys weitergearbeitet
  - Targeted: Nur fuer User im aktuellen Raum, nur wenn verschluesselt wird (kein idle Polling)
  - Forward-compatible: Wenn #377 upstream gefixt wird, ist der extra FetchKeys-Call ein harmloser No-Op
  - `go build ./...` kompiliert ohne Fehler
- [x] Proaktiver Workaround in Go-Layer implementiert
- [ ] Verification Flow testen: nach Cross-Signing-Bootstrap prufen ob Element X das Go-Device sofort als verified sieht
- [ ] Falls verzoegert trotz Workaround: auf upstream fix warten

**[tuwunel#372](https://github.com/matrix-construct/tuwunel/issues/372) — /room_keys/version 500 statt 404 (LOW)**
- Key Backup API gibt 500 wenn kein Backup existiert (sollte 404 sein)
- Clients die Key Backup Feature Detection nutzen interpretieren 500 als Server-Error statt "kein Backup"
- **Go-Layer Impact:** Go Appservice Key-Backup-Bootstrap prueft ob Backup existiert. 500 statt 404 koennte den Bootstrap-Flow abbrechen. mautrix-go wrapped den Error aber — zu pruefen ob der Fallback greift.
- [ ] Go Key-Backup-Init gegen v1.6 testen: startet ohne Crash trotz 500 auf /room_keys/version

---

## K. Config SOTA + Breaking Change Fixes (exec2-03b / 11.04.2026 Abend)

Zusaetzliche Gates fuer die Arbeit die im ersten RC-Test aufgedeckt wurde.

### K1. SOTA Config-Keys (alle 6 Configs)
- [x] `error_on_unknown_config_opts = true` in allen 6 Configs
- [x] `prune_missing_media = false` explizit in allen 6 Configs
- [x] `encryption_enabled_by_default_for_room_type = "none"` in allen 6 Configs (war `"off"`)
- [x] `zstd_compression = true` in 5 Dev-/Image-/Example-Configs
- [x] `zstd_compression = false` in `tuwunel.prod.toml` mit BREACH-Kommentar (TLS-Risiko bei direkter TLS-Terminierung)
- [x] Tuwunel v1.6 startet ohne `unknown key` Error → implizit verifiziert dass alle Keys v1.6-kompatibel sind

### K2. v1.6 Breaking Change: Appservice `id` Feld
- [x] `id = "trading-agent"` in allen 6 Configs mit appservice section eingetragen
- [x] Tuwunel v1.6 Log zeigt KEIN `service "appservice" aborted: Invalid id in config appservice: does not match trading-agent` mehr

### K3. Media-Pfad Migration (v1.5 → v1.6)
- [x] `tuwunel.v1.6.toml`: `storage_provider.media.local.base_path = "./homeserver/data/db/media"` (matcht den v1.5 Default-Media-Pfad)
- [x] Tuwunel v1.6 Log zeigt `Connected to storage provider name=media`
- [x] RocksDB `db/archive/` cleanup (einmalig, 616 MB gespart)

### K4. Devstack Startup-Order
- [x] In `dev-stack2.ps1` ist SeaweedFS Register-Service Block **vor** Tuwunel Block (infra-Tier registration order)
- [x] Devstack-Output zeigt `Registered: seaweedfs, tuwunel` (korrekte Reihenfolge)
- [x] Devstack-Output zeigt `[seaweedfs] Ready on :8333` VOR `[tuwunel] Ready on :8448`
- [x] Tuwunel-Log zeigt `Connected to storage provider name=seaweedfs` ohne Retries / Errors
- [x] Kommentar-Block dokumentiert die Abhaengigkeit (warum Order wichtig ist)

### K5. SeaweedFS Bucket
- [x] Bucket `matrix-media` in SeaweedFS angelegt (manuell via `aws --endpoint-url http://127.0.0.1:8333 s3 mb s3://matrix-media`)
- [x] Bucket persistent (lebt weiter nach devstack restart — in SeaweedFS filer db gespeichert)
- [ ] Bucket-Creation ins devstack-Setup-Skript integriert ODER in separates Setup-Skript → **ausstehend** (einmaliger Setup-Schritt, aktuell manuell)

### K6. WSL1-Quirk Dokumentation
- [x] `WARN tcp set_tcp_user_timeout error: Protocol not available (os error 92)` als harmlos dokumentiert in exec2-03b
- [x] Devstack-Kommentar zur WSL1 vs. WSL2 Netzwerk-Semantik (relevant fuer Podman-Migration)
