# exec2-04: Verify-Gates (Gesammelt)

> Alle Verify-Gates aus exec2-01/02/03/03b + exec-04 an einer Stelle.
> Reihenfolge: so wie man beim DevStack-Start logisch durchgehen wuerde.
> Stand: 13.04.2026 (Gates A-H: 30.03.2026 | Gates I-K: 11-13.04.2026 Infrastructure)

> **⚙️ BEVOR Verify-Run:** Stack-Setup + Troubleshooting siehe `scripts/devstack.md`.
> Enthält: presets (`--matrix-full`, `--matrix-mobile`, etc.), erster-Start-Chain
> (setup-garage → users → dev-stack), db-wipe-Szenarien, bekannte upstream-bugs
> (Tuwunel v1.6.0 appservice-autoload, podman-compose --profile, etc.), und
> ports-Übersicht. Täglicher Re-Start: `./scripts/dev-stack.sh --matrix-full`.

---

## Offene Tasks (aus exec2-01/02/03 + exec-04)

### Extern blockiert (kein Action moeglich)
- Siehe: `exec-blocking.md` (Matrix-Protokoll-Blocker)

### Code-Tasks (Matrix Chat)
- [x] react-shiki in Matrix TextContent.tsx umstellen (Syntax Highlighting)
- [x] motion Import in Matrix Components umstellen (framer-motion → motion/react)
- [x] auto-animate in Matrix RoomList/Timeline einbauen
- [x] Location Content: OpenStreetMap-Embed statt Link (10.04.2026, shared/ Components)
- [x] Client→Server Analyse: 75+ SDK-Calls, 8 direct fetches auditiert, 4 Fixes umgesetzt (13.04.2026)
- [x] api.ts Evaluation: SDK ist die API-Schicht, nicht noetig. Dead-Code `/api/matrix/preview` geloescht.

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

### C8. Location Content (OpenStreetMap)
- [x] Matrix-Chat: Location Event (m.location) zeigt OSM-Embed via `LocationEmbed.tsx` (iframe, 0 Dependencies)
- [x] Matrix-Chat: Leaflet/react-leaflet `LocationMapInner.tsx` rendert interaktive Karte in Timeline
- [x] Components in `nextjs-chat/src/components/matrix/message/content/Location*.tsx` + `lib/matrix/geo.ts`
- [ ] Element X zeigt Location Events korrekt (interop) — Client-Test ausstehend
- [ ] Agent-Chat Location Integration — **verschoben nach `exec-merge-chat.md`** (Shared Component Nutzung zwischen UIs)

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

### J6. Merge-Entscheidung + J7. Upstream-Bugs — verschoben nach `exec-matrix-monitor.md`

> J6 (Tuwunel v1.6 stable merge-decision) und J7 (upstream-bug-tracking #411/#401/#377/#372)
> sind **passive Monitor-Items** — wir warten auf upstream, keine aktiven Verify-Tests.
> Siehe `exec-matrix-monitor.md §M1 + §M2` für Details und Trigger-Bedingungen.
>
> J4 (MSC2246 Async Upload) bleibt oben — ist echter Client-Test sobald Element X v0.8+ verfügbar.
> J5 (`max_request_size` ≥ 500 MB) bleibt oben — BLOCKED by #411, aber der Gate ist konkret testbar sobald unblocked.

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
- [x] `error_on_unknown_config_opts = true` funktioniert: v1.6 haette bei unbekanntem Key den Start verweigert — kein Abort = alle unsere Keys sind bekannt. (WSL1 Warning `TCP_USER_TIMEOUT` ist kein Config-Key-Fehler sondern OS-Level.)

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
- [x] Bucket persistent (verifiziert 13.04.2026 — lebt weiter nach devstack restarts, in SeaweedFS filer-db gespeichert)
- [x] Kein Setup-Skript noetig: Bucket ist persistent und einmalig. Tuwunel prueft bei jedem Start via `startup_check = true`. Falls Bucket fehlt (frische Installation): `aws --endpoint-url http://127.0.0.1:8333 s3 mb s3://matrix-media` — dokumentiert in `_ref/tuwunel-v1.6.0-rc/TESTING.md` Troubleshooting-Tabelle.

### K6. WSL1-Quirk Dokumentation
- [x] `WARN tcp set_tcp_user_timeout error: Protocol not available (os error 92)` als harmlos dokumentiert in exec2-03b
- [x] Devstack-Kommentar zur WSL1 vs. WSL2 Netzwerk-Semantik (relevant fuer Podman-Migration)

---

## L. Cinny-Integration Gates (exec2-03c / 2026-04-19)

> Neue Gates aus der Cinny-Pattern-Uebernahme. Bestehende B2/B3-Gates (QR/SAS Cross-Signing, Key-Backup Grundfunktion) bleiben — werden durch diese Gates erweitert, nicht superseeded. Reihenfolge: Tier A (Utilities) → Tier B (UI-Extensions) → Tier C (E2EE-Recovery).

### L1. FeatureCheck (A1, Tier A)
- [ ] `/matrix` Route im Firefox Private-Browsing-Mode zeigt Fallback-UI mit MDN-Link statt weißem Screen
- [ ] IndexedDB verfuegbar → FeatureCheck rendert transparent `children` durch (kein Loading-Flash > 500ms)
- [ ] Probe-DB `matrix-idb-probe-<timestamp>` wird nach Check geloescht (im DevTools → Application → IndexedDB kontrollieren)

### L2. verifiedDevice Helper (A2, Tier A)
- [ ] Bei Send-Entscheidung wird Helper aufgerufen (Call-Site pruefen via `grep verifiedDevice`)
- [ ] `null`-Return bei unbekanntem Device (Device nicht im Device-Store)
- [ ] `true` fuer cross-signed Devices, `false` sonst — via Element X Mobile (cross-signed) und Browser-2-Session (unverified)

### L3. useAlive Hook (A3, Tier A)
- [ ] Unit-smoke: Component mit `useAlive` mounten + unmounten → Callback returnt `false` nach Unmount
- [ ] In `ManualVerification.tsx` (B2) verwendet — kein setState-after-unmount-warning nach Modal-Close waehrend laufendem `bootstrapSecretStorage`

### L4. useAccountData (A4, Tier A)
- [ ] `m.direct`-Change von Element X (User markiert Raum als DM) → unsere Raumliste updated ohne Refresh
- [ ] `m.push_rules`-Change via Element X → Notification-State ohne Refresh aktualisiert
- [ ] EventType-Literal-Change im Hook-Parameter → initial-state wird neu aus `getAccountData` gelesen (kein Hold-Over-Wert)
- [ ] `getAccountData`-Wurf in JSDOM → `console.warn` ohne Tree-Crash

### L5. useCommands (A5, Tier A — integriert in MessageComposer)
- [ ] `/me winkt` → Emote-Event (m.emote) in Timeline, rendered mit "• winkt"
- [ ] `/shrug` → Sendet `¯\_(ツ)_/¯` als m.text
- [ ] `/tableflip` + `/unflip` senden korrekt
- [ ] `/kick @user:server reason` → Kick + reason gesendet (via `client.kick`)
- [ ] `/ban @user:server`, `/unban @user:server`, `/invite @user:server` funktional
- [ ] `/plain text` → m.text ohne `formatted_body` auch wenn Editor HTML hat
- [ ] `/html <body>` → m.text mit `formatted_body=body`
- [ ] Unbekannter Command → Toast-Error, Message bleibt im Editor (kein Senden)
- [ ] Commands in Edit/Reply/Thread-Modus → normaler Text-Send (Commands uebergangen), als dokumentierte Intent
- [ ] `//text` mit doppeltem Slash → Nicht als Command interpretiert, normaler Send

### L6. JoinBeforeNavigateDialog (A6, Tier A)
- [ ] Klick auf Matrix-Room-Permalink (noch nicht joined) → Preview-Dialog oeffnet
- [ ] Avatar, Name, Topic, Member-Count, Join-Rule sichtbar (aus `client.getRoomSummary`)
- [ ] „Beitreten" → `client.joinRoom` erfolgreich, `onJoined(roomId)` Callback triggert Navigation
- [ ] „Abbrechen" / Klick ausserhalb → Dialog schliesst, kein Join
- [ ] Fehlgeschlagene Summary (z.B. Forbidden, Server-nicht-erreichbar) → Error-UI im Dialog

### L7. SplashScreen (B1, Tier B)
- [ ] Erster Page-Load `/matrix` zeigt Brand-Splash (Logo + Spinner + „Verbinde mit Matrix…") bis `isReady=true`
- [ ] Detail-Text „Initial-Sync laeuft…" waehrend `client!==null && !isReady`
- [ ] Nach `SyncState.Prepared` → Splash wird durch MatrixChat ersetzt

### L8. ManualVerification Passphrase-Fallback (B2, Tier B, erweitert exec2-04 B2)
- [ ] Banner-Button „Passphrase" oeffnet ManualVerification-Modal
- [ ] Passphrase-Input → Recovery-Key via PBKDF2 ableiten → `secretStorage.checkKey` validiert
- [ ] Falsche Passphrase → Error „Falsche Passphrase" in rotem Banner, Retry moeglich
- [ ] Richtige Passphrase → `bootstrapCrossSigning` + `bootstrapSecretStorage` + `loadSessionBackupPrivateKeyFromSecretStorage` erfolgreich → Toast „Verifikation per Recovery-Passphrase erfolgreich"
- [ ] Recovery-Key-Modus: 48-Character Key mit/ohne Spaces → `decodeRecoveryKey` parsed korrekt
- [ ] Aktive QR/SAS-Session laeuft → Submit blockiert, Warn-UI sichtbar („Eine QR-/SAS-Verifikation laeuft bereits")
- [ ] Kein 4S auf Server → klare Fehlermeldung „Kein Secret-Storage-Key eingerichtet"

### L9. Upload-Queue Multi-File + Retry (B3, Tier B)
- [ ] Drag-Drop von 3 Files auf Composer → Queue-UI zeigt 3 Items mit Thumbnails
- [ ] File-Input (Paperclip) mit `multiple` → mehrere Files gleichzeitig moeglich
- [ ] Per-File Progress-Bar waehrend Upload
- [ ] 1 File failt (Homeserver-429 oder Netzwerkfehler) → Error-Status mit Retry-Button, andere 2 gehen durch
- [ ] Retry-Button → Item zurueck auf `pending`, bei `uploadAll` erneut probiert
- [ ] Cancel-Button pro Item → Item aus Queue entfernt, Object-URL revoziert (kein Memory-Leak)
- [ ] Fertige Items werden nach `uploadAll` aus der Leiste entfernt (`clearDone()`)
- [ ] Drag-Over visualisierung: Composer bekommt Ring-Border

### L10. BackupRestore UI (C2, Tier C, feature-gated)
- [ ] Mit `NEXT_PUBLIC_CINNY_TIER_C=false` (Default) → Komponente rendert nichts, auch bei open=true
- [ ] Mit `NEXT_PUBLIC_CINNY_TIER_C=true` → Status-Panel zeigt korrekt: Kein Backup / Nicht vertrauenswuerdig / Nicht aktiv / Aktiv
- [ ] „Restore via Passphrase" → Passphrase-Input, bei Submit `restoreKeyBackupWithPassphrase`, Progress-Bar (`loaded/total`)
- [ ] Restore-Success → Toast mit total/imported-Zaehlern
- [ ] Ohne Backup auf Server: Hinweis „Kein Backup eingerichtet, richte zuerst eine Recovery-Passphrase ein"
- [ ] Backup existiert aber nicht aktiv: „Backup-Sync aktivieren"-Button ruft `checkKeyBackupAndEnable`
- [ ] Reactive: externer `CryptoEvent.KeyBackupStatus` triggert UI-Refresh (via Hook-Listener)

### L11. SecretStorage Setup-UI (C1, Tier C)
- [ ] Banner-Button „Passphrase einrichten" oeffnet SecretStorage-Modal
- [ ] Passphrase-Input + Confirm-Input; mismatched oder < 8 Chars → Error-UI
- [ ] Submit → `createRecoveryKeyFromPassphrase` + `bootstrapSecretStorage({setupNewSecretStorage, setupNewKeyBackup})`
- [ ] Success → 48-Character Recovery-Key in Mono-Font sichtbar, Copy + Download Buttons funktional
- [ ] Download erzeugt `matrix-recovery-key-YYYY-MM-DD.txt` mit Key + Erklaertext
- [ ] Re-Setup mit `alreadySetup=true` → Amber-Warning sichtbar vor Submit
- [ ] Nach Close wird `generatedKey` aus State geloescht (nicht wieder abrufbar ohne Re-Setup)

---

## Gate-Severity & Reihenfolge

- **Severity CRITICAL** fuer L8, L10, L11 (E2EE-Recovery, direkte Security-Auswirkung bei Fehlfunktion)
- **Severity HIGH** fuer L1, L5, L6 (User-sichtbare Features, Crash-Risiko ohne)
- **Severity MEDIUM** fuer L2, L3, L4, L7, L9 (Infrastruktur / UX-Polish)

Empfohlene Reihenfolge beim manuellen Test:
1. L1 (ohne FeatureCheck-Pass ist alles andere unsicher)
2. L4 (ohne Account-Data reactive sind L8/L10/L11 nicht verlaesslich)
3. L5, L7, L9 (parallel — alle UI-Visible)
4. L2, L3 (Smoke-Checks)
5. L8 (erfordert zweites Device fuer Cross-Signing-Vergleich)
6. L11 → L10 (in Reihenfolge: SecretStorage muss vor BackupRestore getestet sein weil Backup die Recovery-Passphrase benoetigt)
7. L6 (optional — erfordert Test-Room)

---

## M. Cinny-Vollausbau Gates (exec2-03c Phase 2, 2026-04-19)

> Tier D/E/F/G Vollausbau (Sidebar Unread-Aggregation, Notification-Modes, Settings-Tabs, Spaces-Lobby, etc.). Alle drei Gates (typecheck+biome+build) sind gruen. Gates hier = manuelle Browser-Tests gegen echten Homeserver.

### M1. AsyncSearch (F0)
- [ ] Unit-smoke: `createAsyncSearch({searchFields: (m) => [m.name]})` matcht Whitespace-normalisiert (case-insensitive, multi-token-AND)
- [ ] Leere Query → unveraenderte Eingabeliste

### M2. useCapabilities (F2)
- [ ] Homeserver-Capabilities geladen (React-Query-Cache `staleTime: Infinity`)
- [ ] `m.set_displayname.enabled` korrekt als boolean verfuegbar in G3 AccountTab

### M3. Space Unread-Aggregation Badge (D1)
- [ ] Space mit 3 unread-Rooms: rotes "3"-Pill am Space-Icon rechts-oben
- [ ] Nach Room-Mark-as-Read: Badge aktualisiert ohne Refresh
- [ ] > 99 Unreads: Label "99+"
- [ ] Tooltip zeigt Anzahl: "SpaceName (5 · 3 ungelesen)"

### M4. D7 Leave-Confirm (shared)
- [ ] RoomItem-Context-Menu "Raum verlassen" → AlertDialog (nicht silent leave)
- [ ] Bestaetigung → `client.leave` + `client.forget`
- [ ] Abbrechen → Dialog schliesst, kein Leave

### M5. D2 NotificationMode (+ DM-Mute)
- [ ] 4 Modes auswaehlbar: Standard / Alle / Nur Erwaehnungen / Stumm
- [ ] Mode-Wechsel persistiert in `m.push_rules` account_data
- [ ] Zweiter Browser-Tab: Mode-Aenderung reactive via AccountData-Event
- [ ] **DM-Mute via DMInfoPanel**: boolean-toggle (useMuteRoom) funktioniert weiterhin, setzt Override-Rule mit DontNotify (= "mute"-Mode)

### M6. D5 Mark-as-Read Context-Menu
- [ ] RoomItem mit unread>0: Context-Menu zeigt "Als gelesen markieren"
- [ ] Klick → `client.sendReadReceipt` auf latest event, unreadCount→0

### M7. D5 Mute-Submenu
- [ ] "Benachrichtigungen" SubTrigger mit 4 Modes
- [ ] Active-Mode mit Check-Icon markiert
- [ ] Keyboard-nav: ArrowRight oeffnet Sub, Enter selektiert

### M8. D4 MemberList (Search + Sort + Virt)
- [ ] Search-Input filtert live auf Name + UserID
- [ ] Sort-Dropdown (Rolle/Name/UserID) persistiert nicht (session-state)
- [ ] \> 30 Members: Virtualizer aktiv (kein DOM-Lag bei 500+ Members)

### M9. D6 SharedMedia (Lightbox + Download)
- [ ] Klick auf Media-Thumbnail → Full-Screen-Modal
- [ ] Download-Button → Browser-Download mit Filename
- [ ] Open-in-new-tab → Neuer Tab mit Media-URL
- [ ] ESC → Modal schliesst
- [ ] File-Tab: Download-Button pro Row sichtbar beim Hover

### M10. G1 RoomInfoPanel-Tabs
- [ ] 5 Tabs: Info / Mitglieder / Benachrichtigungen / Admin (nur PL>=100) / Erweitert
- [ ] Tab-Switch: Edit-States (editingName/editingTopic) werden reset
- [ ] Scroll-Position pro Tab unabhaengig

### M11. G2 SpaceSettings-Tabs
- [ ] 4 Tabs: Allgemein / Mitglieder / Raeume / Berechtigungen
- [ ] Raeume-Tab zeigt hierarchy + addRoomId-Form (vor F1-Modal-Migration)

### M12. G3 AppSettingsSheet
- [ ] Trigger: UserProfileDialog oeffnen → "Einstellungen"-Button (nicht Avatar-direkt!)
- [ ] Sheet oeffnet rechts (sm:max-w-lg)
- [ ] 5 Tabs: Konto / Aussehen / Alerts / Geraete / Info
- [ ] Close via ESC oder Outside-Click

### M13. G4 RoomNotificationsTab
- [ ] 4 Mode-Cards visuell mit Icon + Titel + Description
- [ ] Active-Mode hervorgehoben (primary-border + Check)
- [ ] Mode-Click waehrend `isSetting` → Buttons disabled

### M14. G5 Devices
- [ ] Aktuelle Session mit "Aktuell"-Badge markiert, nicht logout-fähig
- [ ] Verified vs. unverified per Device sichtbar (Shield-Icons)
- [ ] Logout-Other: `client.logoutSingleUserDevice` erfolgreich (oder UIA-Hinweis-Toast bei Fail)

### M15. G6 Encryption-Enable (Doppel-Confirm)
- [ ] Raum ohne E2EE: "Verschluesselung aktivieren"-Button sichtbar fuer Admins
- [ ] Klick: AlertDialog mit 5-Punkte-Liste + Checkbox "Ich verstehe"
- [ ] Checkbox nicht angehakt → Action-Button disabled
- [ ] Nach Aktivierung: Badge wechselt zu "E2EE aktiv" (emerald)
- [ ] Irreversibel: Downgrade-UI existiert nicht

### M16-18. D8 Admin-Extensions
- **M16 Join-Rule**: Dropdown (invite/public/knock/restricted) → State-Event `m.room.join_rules` geaendert
- **M17 History-Visibility**: Dropdown (shared/invited/joined/world_readable) → State-Event `m.room.history_visibility`
- **M18 Aliases**: Create (`#alias:domain` Format-Check) / Delete / List live aus `getLocalAliases`

### M19. E5 Invite-Users-Dialog
- [ ] searchUserDirectory liefert Treffer ab 2 Zeichen
- [ ] Multi-Select mit Chip-Preview der Selected-Liste
- [ ] Submit: invite pro User, Partial-Success-Toast bei gemischten Ergebnissen

### M20. E4 Suggested-Rooms
- [ ] Space mit `suggested: true` Child → Sparkles-Icon in SpaceLobby HierarchyRow
- [ ] Amber-Background (bg-amber-500/5) leicht sichtbar

### M21. E3 Sub-Spaces (nur Data-Model)
- [ ] `SpaceChildRoom.isSpace=true` fuer nested-Space-Kinder aus `getRoomHierarchy`
- [ ] UI-Nested-Rendering in SpaceSelector: **DEFERRED** zu naechstem Sprint

### M22. E1 Space-Lobby
- [ ] Space ohne vorher-Interaktion: Lobby collapsed (localStorage leer)
- [ ] Nach Expand: Lobby persist via localStorage `matrix.lobby.{id}.expanded`
- [ ] Hierarchie max 5 Rows, "Alle N anzeigen"-Button bei mehr
- [ ] Join-Button pro ungejointer Row, Beitritt aktualisiert Liste

### M23. E2 DnD-Reorder
- **DEFERRED**: pragmatic-drag-and-drop Dep + Element-Web-Event-Type-Recherche

### M24. D3 RoomList Categories
- **DEFERRED**: Globaler flat-Virtualizer Refactor eigene Iteration

### M25. F1 add-existing Room Picker
- [ ] Virtualizer aktiv bei `>30` Candidate-Rooms
- [ ] Filter: existing childIds + Self excluded
- [ ] Multi-Select → `sendStateEvent(m.space.child)` pro Room

---

## L-Gate Review nach Phase 2

Keine L-Gates sind **obsolet** oder **superseded**. L-Gates bleiben gueltig. Erweiterungen:

- **L2 verifiedDevice** → jetzt auch in G5 DevicesTab sichtbar als Verify-Badge
- **L3 useAlive** → zusaetzlich in MediaLightbox, InviteUsersToSpaceDialog, AddRoomToSpaceDialog, useDevices, useRoomNotificationMode verwendet (Phase-2-Expansion)
- **L4 useAccountData** → Konsument-Erweiterung: G3 NotificationsTab (Keywords), useRoomNotificationMode (Push-Rules reactive)
- **L8/L10/L11** (ManualVerification/BackupRestore/SecretStorage) → unveraendert aktiv. `NEXT_PUBLIC_CINNY_TIER_C` bleibt Rollback-Flag.

---

## Section N — Phase 3 Gates (N1-N4, 2026-04-20)

Phase 3 Final Polish (Tier-H). 4 Items implementiert + verifiziert (sota-verify Run #2 PASS). P3-Block (N5-N7) bewusst skipped per Plan.

### N1 — AutoRestoreBackupOnVerification

- [ ] Erster Verify-Flow nach Fresh-Login: Restore-Toast erscheint ("Alte Nachrichten werden entschluesselt..."), Key-Progress-Bar sichtbar
- [ ] Alte verschluesselte Nachrichten werden ohne weiteren User-Input entschluesselt (bei trusted Backup)
- [ ] Second-Verify in selber Session: kein Double-Restore (sessionStorage-Flag blockt, Dual-Guard aktiv)
- [ ] Verify ohne vorhandenes Backup: keine Error-Toasts, silent skip via try/catch
- [ ] Beim Cancel der Verify-Request: kein AutoRestore-Trigger (Phase=Cancelled detach-Handler aktiv)
- [ ] Error-Pfad: bei `restoreWithCachedKey`-Reject wird `restoreStartedRef` + sessionStorage rollbacked, Retry moeglich

### N2 — Cross-Room Message-Search

- [ ] SearchPanel hat Cross-Room-Toggle (Default OFF = per-room-Modus)
- [ ] Toggle an: Suche laeuft ueber alle joined, non-encrypted Rooms
- [ ] Jedes Result zeigt Room-Avatar + Name + Sender + Message-Preview + timestamp
- [ ] Click auf Result navigiert zum Event via `matrix:navigate`-Custom-Event
- [ ] Encrypted-Room-Hinweis "Verschluesselte Raeume werden nicht durchsucht (Matrix-Protokoll-Limitation)" sichtbar bei aktivem Toggle
- [ ] Toggle disabled mit Tooltip wenn alle Raeume verschlüsselt
- [ ] Results-Footer: "X Raeume durchsucht, Y uebersprungen" bei encryptedSkipped > 0
- [ ] Pagination "Mehr laden"-Button erscheint bei `nextBatch != null`, disabled waehrend in-flight
- [ ] Toggle-Flip mid-flight invalidiert stale responses via Request-Generation-Counter (kein Stale-Data-Render)

### N3 — RoomList-Categories

- [ ] 5 Groups angezeigt: Einladungen / Favoriten / Personen / Raeume / Niedrige Prioritaet (in dieser Reihenfolge)
- [ ] Collapse per-Group via ChevronRight/ChevronDown-Toggle funktioniert
- [ ] Collapse-State persistiert in `localStorage.matrix.roomList.collapsedGroups`
- [ ] Globaler flat-Virtualizer mit heterogenen Heights (Header 26px, Item 60px) rendert korrekt
- [ ] Pfeiltasten-Nav springt zwischen Room-Items, Group-Header werden uebersprungen
- [ ] Space-Filter (wenn Space ausgewaehlt): Groups zeigen nur Rooms aus `space.childRoomIds`
- [ ] Leere Groups werden im Space-Kontext ausgeblendet (kein "leer"-Placeholder)
- [ ] Search-Input filtert global ueber alle Groups, leere Groups dann auch ausgeblendet
- [ ] `m.lowpriority`-Tag wird korrekt aus Room-Tags gelesen und kategorisiert
- [ ] Playwright-Minimal-Test `tests/roomlist-keyboard-nav.spec.ts` laeuft (skipped ohne Matrix-Credentials)

### N4 — Image-Editor Crop/Rotate

- [ ] Image-Upload in der Queue zeigt Crop-Button bei `status === "pending" || "error"` UND `image/*` UND NICHT `image/gif`
- [ ] Animated GIF: Crop-Button disabled mit Tooltip "Animated GIFs koennen nicht bearbeitet werden"
- [ ] Click Crop-Button oeffnet ImageEditor-Modal mit Cropper
- [ ] Aspect-Ratio Select: 4 Optionen (4:3 Standard / 1:1 Quadrat / 16:9 Breitbild / 3:4 Hochformat), keine "Frei"-Option
- [ ] Rotate-Buttons 90° links/rechts funktional, kombiniert mit Crop
- [ ] Zoom-Slider 1.0×—4.0× aktiv
- [ ] Save: modifiziertes Image (JPEG oder PNG basierend auf Source) ersetzt Original via `replaceFile(id, newFile)`
- [ ] Cancel: unveraendert, original File bleibt in Queue
- [ ] ObjectURL-Lifecycle: Editor-useEffect-Cleanup revoked image-URL; `replaceFile` revoked alten preview-URL vor Ersatz
- [ ] Re-Upload nach Replace: upload-Progress laeuft ab status=pending

### N5-N7 (DEFERRED)

N5 Sidebar-DnD-Reorder, N6 PPTX Preview, N7 Space-Members-Drawer wurden per Plan-Entscheidung skipped. Bei Re-Aktivierung: sub-Gates N5.x / N6.x / N7.x hier ergaenzen.

### Phase-3-Fixes-Log

- **N2 Stale-Data-Race** (sota-verify Run #1 finding) → Fix in SearchPanel.tsx via `requestIdRef`-Counter: pre-await capture, post-await check, toggle-handler invalidate. Verified PASS.
- **N4 "Frei"-Aspect-UX-Bug** (sota-verify Run #1 finding) → Fix in ImageEditor.tsx: strict Union ohne "free", klarere Labels, kein `??`-Fallback-Deadcode mehr. Verified PASS.

### Review der M-Gates (Section M bleibt aktiv)

- **M5** (D2 NotificationMode Push-Rules) — unveraendert aktiv. DMInfoPanel-Migration auf useRoomNotificationMode bleibt DEFERRED (funktional identisch).
- **M24** (D3 Categories Flat-Virtualizer) — durch N3 **implementiert** (war in Phase 2 als Deferred dokumentiert). M24 wird jetzt in N3.x-Gates abgedeckt. M24 bleibt als Alias-Pointer zur N3-Section.

### Review der L-Gates

- **L1 Crypto-Bootstrap** → N1 nutzt `useKeyBackup` (Tier-C0), selber Crypto-Path; keine Regression.
- **L10 BackupRestore** → N1 konsumiert `restoreWithCachedKey` aus Tier-C2, erweitert Silent-Auto-Flow (ohne Passphrase-UI).
- Alle L-Gates bleiben aktiv unveraendert.

---

## Section N Add-On — Phase 3.5 Gates (2026-04-20)

Phase 3.5 ergaenzt 2 Items aus dem vorher deferred P3-Block.

### N5 — Sidebar DnD-Reorder (Space-Icons)
- [ ] Space-Icon ist draggable, Cursor-Indikation sichtbar
- [ ] Drop-Target zeigt top/bottom-Edge-Indikator (2px Linie) je nach Maus-Position
- [ ] Drop auf sich selbst: no-op
- [ ] Order persistiert in `localStorage.matrix.spaceOrder`
- [ ] Einmaliger Toast "Reihenfolge nur auf diesem Geraet gespeichert." bei erstem Drop (via `matrix.spaceOrderToastShown`)
- [ ] Neuer Space (nach Setup-Order erstellt) erscheint am Ende der Liste
- [ ] Home-Icon, Create-Button, Activity-Bell, Profil-Avatar nicht draggable
- [ ] localStorage corrupt: fallback auf default-order, kein Crash

### N-Lobby — Room-Item DnD zwischen Categories
- [ ] Room-Item ist draggable (outer div als drag-handle), opacity-40 waehrend drag
- [ ] Favoriten/Niedrige-Prio/Raeume/Personen-Header: ring-highlight bei drag-over
- [ ] Einladungen-Header: **kein** drop-target (keine ring-highlight)
- [ ] Drop auf Favoriten: setRoomTag(m.favourite) + deleteRoomTag(m.lowpriority) + Toast
- [ ] Drop auf Niedrige Priorität: setRoomTag(m.lowpriority) + deleteRoomTag(m.favourite) + Toast
- [ ] Drop auf Raeume/Personen: beide Tags deleted + Toast "Kategorie entfernt"
- [ ] Drop auf Einladungen: no-op (skipped in monitorForElements)
- [ ] Drop auf same category: early return, keine API-Calls, kein Toast
- [ ] Network-Fail auf setRoomTag: Error-Toast "Verschieben fehlgeschlagen"

### Phase 3.5 Fixes-Log
- **Invites als visuelles Drop-Target** (sota-verify Run #1 finding) → Fix: `groupId`-Prop in RoomList.tsx conditional durchreichen, "invites" bekommt gar nicht erst DropTarget-Capability. PASS.
- **Same-Category API-Call-Waste** (sota-verify Run #1 finding) → Fix: roomsRef + categorize-Lookup-Guard in onDrop. PASS.

---

## Section O — Architektur-Decisions (ADR-lite, 2026-04-21)

> Keine Verify-Gates, sondern Decisions die zum Verständnis der Matrix-Chat-Tests
> nötig sind. Verknüpft mit exec-06 (agent-chat bridge) und exec-10 (multi-agent orchestration).

### O.1 Bridge-Architektur (Go-Appservice ↔ Python-Agent)

**Context:** go-appservice kommuniziert über NATS, python-agent spricht HTTP/SSE. Irgendetwas muss übersetzen.

**Options:**

| Option | Wie | Pro | Contra |
|---|---|---|---|
| **A — Go ruft Agent direkt via HTTP** | go-appservice konsumiert `/api/v1/agent/chat` SSE-Stream direkt | kein NATS im agent-chat-pfad, 1 hop weniger | Go braucht SSE-client impl, kein buffer wenn agent down, streng gekoppelt |
| **B — Agent subscribed selber auf NATS** | python-agent hat eigenen NATS-consumer für `matrix.message.inbound` | kein bridge-prozess, direkt | agent verliert "pure HTTP"-interface, mixing transports im agent-code, frontend + matrix-pfad teilen dieselbe handler-logic |
| **C — Bridge (status quo)** | `python-backend/bridge/` ist dünner Translator: NATS inbound → HTTP POST → SSE collect → NATS reply | decoupled (Go + Agent unabhängig restart-bar), NATS als buffer, agent bleibt pure-HTTP, frontend + matrix share 0 code | extra prozess, extra hop (~5-10ms latency), doppelte (de)serialization |

**Decision: C (bridge behalten) — 2026-04-21**

**Gründe:**
- Bridge ist klein (~120 LOC in 3 files: `nats_handler.py` + `agent_client.py` + `config.py`), Wartungsaufwand minimal
- Decoupling hat echten Wert: frontend nutzt agent-HTTP direkt, matrix-pfad nutzt NATS — zwei orthogonale Transports am selben agent. Sauber.
- Architektur-Refactor wäre eigene Iteration (exec-06 territory), nicht blockierend für Verify-Lauf

**Re-evaluate wenn:**
- Bridge-Prozess wird performance-bottleneck (>50ms overhead je request)
- Bridge crasht >1×/Monat ohne Trigger (reliability-problem)
- matrix-pfad braucht features die HTTP/SSE nicht kann (z.B. bidirektionales streaming von tool-calls)

**Cleanup TODO (low prio):** `docker-compose.yml:261` zeigt `python-bridge` auf nicht-existierendes `./python-agent-bridge`. Dev-stack.sh startet bridge lokal korrekt. Compose-Eintrag ist dead weight — entfernen oder auf `./python-backend` mit korrektem Dockerfile umbiegen.

---

### O.2 Agent-Orchestration (User ↔ Agent Matrix-Topologie)

**Context:** Heute multi-agent-mention-routing (`@agent-trading`, `@agent-research`) via body-regex in `go-appservice/internal/handler/server.go:extractAgentName()`. User will: **single orchestrator-agent** der subagents intern delegiert.

**Options:**

| Option | Pattern | Status |
|---|---|---|
| **Multi-Agent-Mention (aktuell)** | User schreibt `@agent-trading ...` → go-appservice extract name → bridge → agent-service → reply als `@agent-<name>` | implementiert, body-parsing, NICHT SOTA 2026 |
| **Orchestrator + interne Subagents** | User spricht mit 1 agent pro user (`@agent-<userid>`). Agent ist LangGraph-Supervisor der subagents (als Graph-Nodes) routet. Subagents haben KEINE Matrix-Identity. | **Target-Pattern**, exec-10 Phase 1-4 impl, A2A nie live-getestet |
| **Orchestrator + sichtbare A2A-Subagents** | Wie oben, aber subagents haben eigene Matrix-UserIDs und posten Zwischenschritte in einen "workspace"-Room. Transparency für User. | exec-10 Phase 4 (A2A-protocol), verfügbar aber optional |

**Decision: Target = Orchestrator-Pattern, Refactor in exec-10 (nicht jetzt) — 2026-04-21**

**Gründe:**
- Body-parsing `extractAgentName` ist dispatcher-logic die eigentlich in den agent gehört
- Pro-user-agent ist skalierungstechnisch richtig (user_llm_settings, memory-isolation, eigene preferences)
- Subagent-Struktur ist **noch in Entwicklung** (welche Subagents, welche Routing-Regeln, Transparency-Level) → jetzt nicht festzementieren
- Matrix-Appservice-Namespace `@agent-.*:matrix.local` deckt beide Patterns bereits ab — refactor ist server-side ohne Matrix-Protokoll-Änderung

**Offene Design-Fragen (exec-10 scope):**
- Ein Singleton python-agent-prozess, der AS verschiedene `@agent-<userid>` antwortet (Appservice-Intent-Pattern) — oder ein prozess pro user-agent (n Prozesse, memory-heavy)?
- Subagents als LangGraph-Nodes (kein Matrix-Identity, aktuell) vs. A2A-Matrix-Agents (eigene Identity, transparency-Option)
- Wie bestimmt der orchestrator welche subagents er triggert? (intent-classifier-LLM, tool-use-routing, rule-based)
- E2EE-Scaling: Shared OlmMachine für alle agent-users (status quo, mautrix-go Appservice E2EE MSC3202) vs. per-agent OlmMachine (`exec-05c agent-isolation`, deferred)

**Für trading-project integration:**
- User-Registration → `@<userid>:matrix.local` via MAS/OIDC-provisioning (blockiert: `exec-matrix-monitor §M4`)
- User-Registration → `@agent-<userid>:matrix.local` **NICHT explizit registrieren** — appservice-namespace `@agent-.*` deckt das ab, lazy on-demand beim ersten SendText
- DM-Room(@user, @agent-user) auto-create nach Matrix-Init (exec2-03b §A2 Post-Login Matrix Init)

**Cross-refs:**
- Namespace-Pattern: `homeserver/registration.yaml`, `homeserver/tuwunel.toml [appservice.trading-agent.namespaces.users]`
- Intent-API: `go-appservice/internal/intent/agent.go:AgentSender` (`?user_id=@agent-xxx` query-param pattern)
- Body-Parsing (zu deprecaten): `go-appservice/internal/handler/server.go:extractAgentName()` (L776ff), `isAgentUser()` (L798ff)
- Per-user-model-routing (bereits implementiert): `python-backend/bridge/nats_handler.py:82-89` (`get_user_default_model(sender)` aus `agent.security.credentials`)

---

### O.3 Scope für aktuellen Verify-Lauf (2026-04-21)

**Implementiert in dieser Session (aus Prod-Readiness-Gründen, nicht aufschiebbar):**

- ✅ **Bridge Option C** — läuft
- ✅ **Env-loader** (`shared/app_factory.py` + `bridge/config.py`) lädt `.env.development` via `APP_ENV` default — OpenRouter-key wird geladen
- ✅ **Dynamic reply-routing in bridge** (`bridge/nats_handler.py:_resolve_reply_user_id()`) — nutzt `target_agent` aus NATS-payload, fallback auf config-default. Damit respondet das system schon heute pro-user korrekt (`@agent-alice` antwortet alice, `@agent-bob` antwortet bob), sobald body mention oder konfig das so sagt. **Go-seite war bereits dynamic-ready** (`InboundMessage.TargetAgent` wird von `extractAgentName()` gefüllt), nur die bridge hatte statischen reply-user.

**Test-Setup für diesen Lauf:**

- **User-Setup:** `@alice` (Webclient + Mobile), `@bob` (Mobile für Calls), `@agent-bot` (default orchestrator)
- **Testflow Phase 1:** alice mentioniert verschiedene agent-namen (`@agent-bot`, `@agent-alice`, `@agent-bob`) → bridge respondet lazy als entsprechender virtueller user (via appservice-namespace). Validiert dynamic-routing live.
- **Testflow Phase 2 (Calls):** alice ↔ bob 1:1 und Gruppe, keine agent-interaktion

**Nicht in dieser Session (verschoben nach `exec-10 Phase 7`):**

- DM-room-based default-routing (body-parsing deprecaten)
- Username-sanitizer für trading-project integration
- Orchestrator-supervisor-refactor mit subagent-design-session
- Per-user `user_agent_settings` (system-prompt, memory-scope, skills, tools gated by user_id)

**Architektonische Begründung:** Der minimale dynamic-routing-fix war unumgänglich weil Static-Routing per definition nicht skaliert (prod hat nicht 1-2 sondern n user). Der restliche refactor (orchestrator-pattern + subagent-design) ist substantiell genug für eigene exec-10-Iteration mit contrarian-review — Subagent-Topologie ist explizit WIP und darf nicht ad-hoc festgeklopft werden.
