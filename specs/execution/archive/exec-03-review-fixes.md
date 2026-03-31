# Execution Slice 03: Komplett-Status aller Matrix Chat Features

> Erstellt: 25.03.2026
> Basis: exec-02-missing-features.md + Deep-Dive Code Review + Bugfixes
> Bezug: specs/04-nextjs-chat.md, specs/06-e2ee.md

---

## Legende

- ✅ Erledigt + Review bestanden
- ✅🔧 Erledigt + nachträglich gefixt (Review-Finding)
- 🔄 Offen — noch zu tun
- ⏸️ Bewusst offen — kein Fix nötig / extern blockiert

---

## 1. Quick-Wins

---

### ✅🔧 QW-1: `formatted_body` (HTML) rendern

**Implementiert:** HTML-Rendering für Matrix `formatted_body` (org.matrix.custom.html).

**Review-Fixes (25.03.2026):**
- **Fix 1:** `span[style]` war blanket erlaubt → CSS-Injection-Vektor. Jetzt nur `color`, `background-color`, `font-weight`, `font-style`, `text-decoration` via `filterMatrixStyle()`.
- **Fix 2:** `formatted_body` wurde durch ReactMarkdown (Markdown-Parser) gejagt → Metazeichen wie `*`, `_` in HTML wurden fehlinterpretiert. Jetzt direktes HTML-Parsing via `unified` + `rehype-parse` + `rehype-sanitize` + `rehype-stringify` mit `dangerouslySetInnerHTML`.

**Dateien:** `nextjs-chat/src/components/matrix/Message.tsx`
**Deps:** `unified`, `rehype-parse`, `rehype-stringify`, `rehype-sanitize`

**Verify Gate:**
- [ ] Bot-Antwort mit `<table>`, `<code>`, `<strong>` wird korrekt als HTML gerendert
- [ ] HTML mit `*Sternchen*` wird NICHT als Markdown-Italic interpretiert
- [ ] XSS-Versuch (`<script>alert(1)</script>`) wird geblockt
- [ ] `style="color: red"` funktioniert, `style="background: url(javascript:...)"` wird entfernt
- [ ] Normaler m.text ohne formatted_body → weiterhin plain text / Markdown für Bots

---

### ✅ QW-2: Read Receipts senden

**Implementiert:** `client.sendReadReceipt()` bei Raumwechsel + neuer Nachricht.

**Dateien:** `nextjs-chat/src/components/matrix/MatrixChat.tsx`

**Verify Gate:**
- [ ] Raum wechseln → Element X zeigt Raum als "gelesen"
- [ ] Ungelesen-Zähler in RoomList fällt auf 0

---

### ✅ QW-3: Mention-Highlighting (MSC3952)

**Implementiert:** `m.mentions.user_ids` Auswertung + gelbes Highlight für eigene Mentions.

**Dateien:** `nextjs-chat/src/lib/matrix/types.ts`, `nextjs-chat/src/components/matrix/Message.tsx`

**Verify Gate:**
- [ ] Nachricht mit eigenem @handle → gelb hervorgehoben
- [ ] Nachricht ohne @handle → normales Muted-Background

---

### ✅🔧 QW-4: Authenticated Media (MSC3916)

**Implementiert:** Ursprünglich nur `allow_legacy_media = true` (Dev-only).

**Review-Fix (25.03.2026):** Next.js Media-Proxy `/api/matrix/media` erstellt:
- Authenticated Media API (`/_matrix/client/v1/media/`) mit Auth-Header
- Legacy-Fallback (`/_matrix/media/v3/`) für Homeserver ohne MSC3916
- `mxcToHttp()` / `mxcToThumbnail()` leiten auf Proxy um statt direkt auf Homeserver
- 24h Cache-Header, 15s Timeout

**Dateien:** `nextjs-chat/src/app/api/matrix/media/route.ts` (neu), `nextjs-chat/src/lib/matrix/types.ts`

**Verify Gate:**
- [ ] Bilder in m.image laden korrekt (über `/api/matrix/media` Proxy)
- [ ] Thumbnails laden (mit `?thumbnail=1&w=800&h=600`)
- [ ] `allow_legacy_media = false` in tuwunel.toml → Media funktioniert trotzdem
- [ ] Tuwunel-Logs zeigen keine `401 Unauthorized` für Media-Requests
- [ ] Video/Audio-Dateien streamen korrekt über den Proxy

---

## 2. Standard-Features

---

### ✅ B-1: Message-Editing UI

**Implementiert:** Voller Edit-Flow: Edit-Banner im Composer, `m.replace` mit `m.new_content`, Escape-Cancel, `(bearbeitet)` Badge.

**Dateien:** `Message.tsx`, `MessageComposer.tsx`, `MatrixChat.tsx`

**Verify Gate:**
- [ ] Hover über eigene Nachricht → "Bearbeiten" Button sichtbar
- [ ] Edit-Banner erscheint im Composer mit alter Nachricht
- [ ] Escape → Edit abbrechen, Composer leer
- [ ] Nach Edit → `(bearbeitet)` Badge erscheint
- [ ] Element X zeigt edierte Nachricht korrekt

---

### ✅🔧 B-2: Read Receipts visuell anzeigen

**Implementiert:** Mini-Avatare (Initials) unter eigenen Nachrichten, max 5.

**Review-Fix (25.03.2026):** `RoomEvent.Receipt` Listener fehlte → Avatare aktualisierten sich nur bei neuer Nachricht, nicht wenn jemand liest.

**Dateien:** `nextjs-chat/src/lib/matrix/hooks/useTimeline.ts`, `nextjs-chat/src/components/matrix/Message.tsx`

**Verify Gate:**
- [ ] Alice liest eine Nachricht → Mini-Avatar von Alice erscheint sofort (ohne neue Nachricht)
- [ ] Max 5 Avatare angezeigt
- [ ] Bei Raumwechsel korrekt zurückgesetzt

---

### ✅🔧 B-3: Reactions — Eigene Reaktion senden

**Implementiert:** 8-Emoji Quick-Picker, `m.reaction` mit `m.annotation`.

**Review-Fix (25.03.2026):** Emoji-Picker hatte keinen Click-Outside-to-Close Handler. Jetzt `mousedown` Listener auf `document` mit `pickerRef.contains()` Check.

**Dateien:** `nextjs-chat/src/components/matrix/Message.tsx`, `nextjs-chat/src/components/matrix/MatrixChat.tsx`

**Verify Gate:**
- [ ] Hover → Emoji-Picker erscheint
- [ ] Klick auf Emoji → `m.reaction` Event gesendet, Picker schließt
- [ ] Klick außerhalb Picker → Picker schließt
- [ ] Reaktion sofort in der UI sichtbar
- [ ] Element X zeigt Reaktion korrekt

---

### ✅🔧 B-4: Nachrichten löschen (Redaction)

**Implementiert:** Hover-Menü → "Löschen" mit Confirm-Dialog, `client.redactEvent()`.

**Review-Fix (25.03.2026):** Guard gegen Actions auf gelöschten Nachrichten war `message.body === "[Nachricht gelöscht]"` (fragiler String-Vergleich). Jetzt `isRedacted: boolean` Feld in `ResolvedMessage`, gesetzt via `ev.isRedacted()`.

**Dateien:** `nextjs-chat/src/lib/matrix/types.ts`, `nextjs-chat/src/components/matrix/Message.tsx`

**Verify Gate:**
- [ ] Eigene Nachricht löschen → `[Nachricht gelöscht]` erscheint
- [ ] Keine Edit/React/Delete Buttons auf gelöschten Nachrichten
- [ ] Element X zeigt ebenfalls `[Nachricht gelöscht]`

---

### ✅🔧 B-5: URL-Vorschauen / Link-Unfurling

**Implementiert:** OpenGraph-Vorschau via Next.js API Route → Homeserver `preview_url` API.

**Review-Fix (25.03.2026):** Preview-Proxy nutzte statischen `MATRIX_ACCESS_TOKEN` aus Env für alle User → Multi-User Privacy-Problem. Jetzt: Client sendet eigenen Token via `Authorization` Header, Proxy leitet weiter. Fallback auf Env-Token.

**Dateien:** `nextjs-chat/src/app/api/matrix/preview/route.ts`, `nextjs-chat/src/components/matrix/UrlPreview.tsx`

**Verify Gate:**
- [ ] Nachricht mit `https://matrix.org` → Vorschau-Karte (Titel, Bild, URL)
- [ ] Preview nutzt den Token des aufrufenden Users (DevTools → Network → Authorization Header prüfen)
- [ ] Cache: 5 Minuten, kein Doppel-Fetch bei erneutem Rendern

---

### ✅🔧 B-6: Presence / Online-Status

**Implementiert:** Grüner Punkt am Avatar für online User in DMs.

**Review-Fix (25.03.2026):** Sliding Sync hatte kein `extensions.presence` Block → Homeserver schickte keine Presence-Events → `isOnline` war immer `false`. Jetzt `extensions: { presence: { enabled: true } }` in SlidingSync-Config.

**Dateien:** `nextjs-chat/src/components/matrix/MatrixProvider.tsx`, `nextjs-chat/src/lib/matrix/hooks/useRooms.ts`, `nextjs-chat/src/lib/matrix/types.ts`

**Verify Gate:**
- [ ] tuwunel.toml: `allow_local_presence = true`
- [ ] Alice online → grüner Punkt am Avatar in RoomList
- [ ] Alice schließt Browser → grüner Punkt verschwindet (nach Timeout)
- [ ] Sliding Sync Request enthält `extensions.presence.enabled: true` (DevTools → Network)

---

### ✅🔧 B-9: 1:1 Voice/Video Calls

**Implementiert:** Call UI mit Klingel-Overlay, Video-Elemente, Mute/Camera Toggle, Hangup. State Machine: idle → incoming/outgoing → connecting → connected → ended.

**Review-Fixes (25.03.2026):**
- **Fix 1:** `callStatus` blieb `"idle"` bis SDK-Event → kurzer Flash. Jetzt sofortiges `setCallStatus("outgoing")` vor async SDK call.
- **Fix 2:** `activeCall` in useEffect-Deps → Stale Closure, Incoming Calls konnten verloren gehen. Jetzt `activeCallRef` (Ref) statt State.
- **Fix 3:** `callerName` für ausgehende Calls nie gesetzt → zeigte "Unbekannt". Jetzt Room-Member-Lookup.

**Dateien:** `nextjs-chat/src/lib/matrix/hooks/useCall.ts`, `nextjs-chat/src/components/matrix/CallOverlay.tsx`, `nextjs-chat/src/components/matrix/RoomHeader.tsx`

**Verify Gate:**
- [ ] Call starten → Overlay erscheint sofort (kein Flash)
- [ ] Ausgehender Call → Name des Gegenübers sichtbar (nicht "Unbekannt")
- [ ] Eingehender Call während laufendem Call → wird rejected (kein Crash)
- [ ] Klingel-Overlay bei eingehendem Call mit Avatar + Buttons
- [ ] Lokaler + Remote-Stream sichtbar in `<video>`
- [ ] Audio-Call User ↔ User funktioniert (gleicher Homeserver)
- [ ] Mute/Camera Toggle funktioniert
- [ ] Call beenden → sauber aufgeräumt (kein Leak)
- [ ] Call User ↔ Element X (Mobile) interoperabel

---

## 3. Protokoll-Level Features

---

### ✅ C-2: Authenticated Media URL-Format (MSC3916)

**Status:** Identisch mit QW-4 — durch Media-Proxy vollständig gelöst. Siehe QW-4 oben.

---

### ✅ C-1: Sliding Sync (MSC3575/MSC4186)

**Implementiert:** `SlidingSync` Instanz mit Recency-Sorting, Lazy Member Loading, 50 Timeline Events.

**Hinweis:** SDK v41.2.0 nutzt `/_matrix/client/unstable/org.matrix.simplified_msc3575/sync` (MSC3575-Endpoint, hardcoded im SDK). Tuwunel unterstützt beide Pfade. Kein Fix nötig — wird automatisch mit SDK-Update behoben.

**Dateien:** `nextjs-chat/src/components/matrix/MatrixProvider.tsx`

**Verify Gate:**
- [ ] Raumliste lädt unter 500ms bei 20+ Räumen
- [ ] Keine unnötigen Events für nicht-sichtbare Räume
- [ ] DevTools → Network: Request geht an `simplified_msc3575/sync`

---

### ✅🔧 C-3: Cross-Signing (MSC4153) — Deadline April 2026

**Implementiert:**
- **Go:** Bootstrap MSK/SSK/USK, SignOwnDevice, SignOwnMasterKey, Seeds-Persistence (`cross_signing_seeds.json`, 0o600)
- **Browser:** `useCrossSigning` Hook, `CrossSigningSetup` Komponente (Banner + Modal), QR-Code Flow + SAS Emoji-Fallback

**Review-Fix (25.03.2026):** `waitForPhase()` hatte keinen Terminal-State Guard → Promise hing ewig bei Abbruch. Jetzt: Prüfung auf `Cancelled`/`Done` Phase → reject statt endlos hängen.

**Dateien:** `go-appservice/internal/crypto/machine.go`, `nextjs-chat/src/lib/matrix/hooks/useCrossSigning.ts`, `nextjs-chat/src/components/matrix/CrossSigningSetup.tsx`

**Verify Gate:**
- [ ] **Go Bootstrap**: Erster Start → `cross_signing_seeds.json` erstellt → Log: `"E2EE: cross-signing keys generated and uploaded"`
- [ ] **Go Restart**: Seeds geladen → Log: `"E2EE: cross-signing keys loaded from disk"`
- [ ] **Bot Trust in Element X**: Bot-Gerät erscheint als cross-signed (kein Warndreieck)
- [ ] **Web App Banner**: Unverifiziert → gelbes Banner mit "Verifizieren"-Button
- [ ] **QR-Code Flow**: Button → Modal → QR → Element X scannt → beide bestätigen → Banner weg
- [ ] **SAS Fallback**: 7 Emojis vergleichen wenn QR nicht verfügbar
- [ ] **Abbruch-Test**: Element X bricht Verifikation ab → UI springt zurück auf "needs_verification" (kein Hänger)
- [ ] **MSC4153 Kerntest**: Bot + Web App empfangen Room-Keys → E2EE-Nachrichten lesbar

---

### ✅🔧 D-1: E2EE Vollbetrieb (Szenario C)

**Implementiert:** Browser `initRustCrypto()` + Go Appservice `MATRIX_E2EE_ENABLED=true` + OlmMachine.

**Review-Fixes (25.03.2026):**
- **Fix 1:** `sendEncryptedReply` rief `Encrypt()` ohne `EnsureSession()` → erste Antwort pro Raum schlug fehl. Jetzt: `EnsureSession()` mit Room-Members vor `Encrypt()`. Neue `GetMembers()` Methode im StateStore.
- **Fix 2:** Browser nutzte `MemoryStore` → Full-Resync bei jedem Page-Reload. Jetzt: `IndexedDBStore` mit persistentem Sync-State.

**Dateien:** `go-appservice/internal/handler/server.go`, `go-appservice/internal/crypto/statestore.go`, `nextjs-chat/src/lib/matrix/client.ts`

**Verify Gate:**
- [ ] Go Appservice startet mit `[e2ee] OlmMachine geladen` Log
- [ ] Go Appservice Keys auf Homeserver hochgeladen (`/keys/upload`)
- [ ] Browser initialisiert Rust Crypto ohne Fehler (DevTools Console)
- [ ] User sendet Nachricht → Browser verschlüsselt (m.room.encrypted)
- [ ] Go Appservice entschlüsselt → NATS → Python empfängt Klartext
- [ ] Bot-Antwort kommt verschlüsselt beim Browser an + wird entschlüsselt
- [ ] Page-Reload → kein Full-Resync (IndexedDB), Nachrichten sofort da
- [ ] Element X (Mobile) kann ebenfalls lesen (Cross-Device)

---

### ✅ D-2: Key Exchange Ablauf

**Implementiert:** Key Upload, Query, One-Time Key Claiming — alles intern von mautrix-go. To-Device Events korrekt vor Room Events verarbeitet.

**Verify Gate:**
- [ ] Keine `M_UNKNOWN_TOKEN` Fehler beim Key Upload
- [ ] Keine `UNABLE_TO_DECRYPT` Fehlermeldungen in der UI

---

### ✅ C-8: Go Appservice Key Backup (NEU)

**Implementiert (25.03.2026):** Megolm-Session-Keys Export/Import in verschlüsselte Datei.
- `ExportKeyBackup()` — alle Sessions via `crypto.ExportKeys()` nach `data/megolm_keys_backup.bin`
- `importKeyBackup()` — beim Start automatisch importiert
- Export nach jedem To-Device-Event (neue Room Keys) + beim Shutdown
- Passphrase via `MATRIX_KEY_BACKUP_PASSWORD` (kein Backup ohne Passphrase)

**Dateien:** `go-appservice/internal/crypto/machine.go`, `go-appservice/internal/handler/server.go`, `go-appservice/internal/config/config.go`

**Verify Gate:**
- [ ] `MATRIX_KEY_BACKUP_PASSWORD` in `.env.development` gesetzt
- [ ] Go Appservice startet → Log: `"E2EE: key backup imported"` (oder `"no key backup file found"` beim ersten Start)
- [ ] Nachricht empfangen (neuer Room Key) → `data/megolm_keys_backup.bin` wird erstellt/aktualisiert
- [ ] Go Appservice stoppen → Log: `"E2EE: key backup exported"`
- [ ] `data/megolm_keys_backup.bin` löschen + Appservice neu starten → alte verschlüsselte Nachrichten können trotzdem gelesen werden (Keys in SQLite), aber Backup wird neu erstellt
- [ ] Neues Deployment (frische SQLite) + vorhandene `megolm_keys_backup.bin` → Keys importiert, alte Nachrichten lesbar

---

### ✅ C-10: MSC4381 — `sender_key`/`device_id` entfernt (NEU)

**Implementiert (25.03.2026):** Deprecated Felder aus `m.room.encrypted` Events entfernt (Privacy).

**Datei:** `go-appservice/internal/handler/server.go`

**Verify Gate:**
- [ ] Go Appservice sendet encrypted Event → DevTools/Tuwunel-Logs prüfen: kein `sender_key`, kein `device_id` im Event-Content
- [ ] Empfänger (Browser + Element X) können trotzdem entschlüsseln

---

## 4. Infrastruktur (NEU — 25.03.2026)

---

### ✅ I-1: `.env.development` / `.env.production` Trennung

**Was:** Saubere Dev/Prod Config. `GO_ENV` steuert welche Datei geladen wird.

**Dateien:** `go-appservice/internal/config/config.go`, `scripts/devstack.ps1`, alle `.env.*`

**Verify Gate:**
- [ ] `GO_ENV=development` → `.env.development` geladen
- [ ] `GO_ENV=production` → `.env.production` geladen
- [ ] Ohne `GO_ENV` → Default `development`
- [ ] `devstack.ps1` prüft `.env.development` (nicht mehr `.env`)

---

### ✅ I-2: Echte Crypto-Keys (kein Platzhalter)

**Was:** `openssl rand -hex 32` für alle Keys.

| Key | Dev | Prod |
|---|---|---|
| `MATRIX_CRYPTO_PICKLE_KEY` | `98efa049...` | `ebc04d8c...` |
| `MATRIX_KEY_BACKUP_PASSWORD` | `ce0061e9...` | `d2aa4156...` |

**Verify Gate:**
- [ ] Keine `changeme` Platzhalter mehr in `.env.development` oder `.env.production`

---

### ✅ I-3: `MATRIX_AGENT_PREFIX` konfigurierbar

**Was:** Hardcoded `"@agent-"` Bot-Prefix als Env-Variable.
- Go: `config.AgentPrefix` → `isAgentUser(userID, serverName, agentPrefix)`
- Next.js: `NEXT_PUBLIC_MATRIX_AGENT_PREFIX` → `isAgentUser(sender)` Helper

**Dateien:** `go-appservice/internal/config/config.go`, `go-appservice/internal/handler/server.go`, `nextjs-chat/src/lib/matrix/types.ts`, alle `.env.*`

**Verify Gate:**
- [ ] `MATRIX_AGENT_PREFIX=agent-` in allen `.env` Dateien
- [ ] `NEXT_PUBLIC_MATRIX_AGENT_PREFIX=agent-` in `.env.local`
- [ ] Bot-Nachrichten zeigen "AI" Avatar + "Agent" Badge
- [ ] Prefix ändern (z.B. `bot-`) → Go + Next.js erkennen neue Bot-IDs

---

## 5. Was ist wirklich noch offen?

### ✅ B-7: Polls (MSC3381) — NEU 25.03.2026

**Implementiert:** Abstimmungen erstellen, abstimmen, Ergebnisse live anzeigen.

**Neue Dateien:**
- `usePoll.ts` — Hook mit Vote-Deduplizierung (last-vote-per-sender, MSC3381 Spec), `PollEvent.Responses` + `PollEvent.End` Subscriptions
- `PollMessage.tsx` — Frage + Antwort-Buttons mit Progress-Bars, Vote-Count, "Abstimmung beendet" State
- `CreatePollDialog.tsx` — Radix Dialog, dynamische Antworten (min 2, max 10), `PollStartEvent.from()` + `serialize()`

**Geänderte Dateien:**
- `types.ts` — `isPoll`, `pollEventId`, `pollQuestion` in ResolvedMessage + Poll-Branch in `resolveMessage` (vor `msgtype === undefined` Guard)
- `Message.tsx` — Poll-Rendering statt Bubble wenn `isPoll === true`
- `MatrixChat.tsx` — BarChart2 Button neben Composer öffnet CreatePollDialog

**Verify Gate:**
- [ ] "Abstimmung erstellen" Button sichtbar neben dem Composer
- [ ] Dialog öffnet: Frage + min. 2 Antworten eingeben
- [ ] Poll wird als Karte in der Timeline gerendert (nicht als Text)
- [ ] Klick auf Antwort → Stimme wird gesendet, Progress-Bar aktualisiert
- [ ] Andere User sehen die Stimme reaktiv (ohne Page-Reload)
- [ ] Element X zeigt die Poll korrekt (Interoperabilität)
- [ ] Eigene Stimme hervorgehoben (Border)
- [ ] Beendete Poll: Buttons disabled, "Abstimmung beendet"

---

### ✅ B-8: Thread-Unterstützung (MSC3440) — Option B Side-Panel — NEU 25.03.2026

**Implementiert:** Thread-Replies in Side-Panel, Thread-Chip auf Root-Nachrichten.

**Neue Dateien:**
- `useThreadTimeline.ts` — Mirror von `useTimeline` für `thread.events`, `ThreadEvent.NewReply` + `ThreadEvent.Update` Subscriptions, Pagination via `paginateEventTimeline`
- `ThreadPanel.tsx` — 380px Side-Panel: Header mit Root-Message Preview, eigene Timeline, eigener Composer mit `threadId`

**Geänderte Dateien:**
- `client.ts` — `threadSupport: true` in createClient (SDK filtert Thread-Replies automatisch aus Main-Timeline)
- `types.ts` — `isThreadRoot`, `threadReplyCount` in ResolvedMessage
- `useTimeline.ts` — Thread-Metadata Stamping (`room.getThreads()` → `threadMap`), `ThreadEvent.Update` Listener
- `Message.tsx` — `ThreadChip` Komponente ("N Antworten" mit MessageSquare Icon), neue Props (`client`, `roomId`, `onThreadOpen`)
- `MessageComposer.tsx` — `threadId` Prop, `sendMessage` 3-Argument-Overload für Thread-Replies
- `Timeline.tsx` — Props durchreichen (`client`, `roomId`, `onThreadOpen`)
- `MatrixChat.tsx` — `activeThreadId` State, `handleThreadOpen` Callback, Flex-Row Layout für Chat + Side-Panel, Reset bei Raumwechsel

**Verify Gate:**
- [ ] Thread starten: Auf eine Nachricht antworten (via Element X) → "N Antworten" Chip erscheint unter der Nachricht
- [ ] Chip klicken → Side-Panel (380px) öffnet rechts mit Root-Message + Replies
- [ ] Reply im Thread-Panel senden → erscheint sofort im Panel
- [ ] Reply-Count auf dem Chip aktualisiert sich reaktiv
- [ ] Thread-Reply erscheint NICHT in der Main-Timeline (SDK filtert)
- [ ] X-Button → Side-Panel schließt
- [ ] Raumwechsel → Thread-Panel schließt automatisch
- [ ] Element X zeigt Thread-Replies korrekt (Interoperabilität)

---

### ✅ HS-1: Homeserver-Config Audit — NEU 25.03.2026

**Tuwunel (`tuwunel.toml`):**
- `default_room_version = "12"` — Project Hydra (State Resolution 2.1 + kryptografische Room-IDs)
- `rocksdb_direct_io = false` — KRITISCH für WSL2+NTFS (9P Filesystem)
- `database_backup_path` + `database_backups_to_keep = 3`
- `encryption_enabled_by_default_for_room_type = "invite"` — neue Invite-Räume automatisch E2EE
- `federate_created_rooms = false` — explizit statt implizit
- TURN/STUN Platzhalter mit Kommentaren (coturn nötig für Voice/Video)

**Dendrite (`dendrite.yaml`):**
- `room_server.default_room_version: "12"`
- `report_stats.enabled: false` — Telemetrie explizit deaktiviert

**Verify Gate:**
- [ ] Tuwunel startet ohne Fehler mit neuem Config
- [ ] Neuer Raum wird mit Room Version 12 erstellt (DevTools → Room State prüfen)
- [ ] `rocksdb_direct_io = false` → keine I/O-Fehler in Logs
- [ ] DB-Backup-Verzeichnis wird erstellt nach erstem Start

---

### Phase 4 — Vorbereitet, noch nicht umgesetzt

---

#### ⏸️ C-4: Encrypted State Events (MSC3414 / MSC4362)

**Status:** matrix-js-sdk v41 hat es **bereits eingebaut** mit `enableEncryptedStateEvents: false` als Default. Null Vorarbeit nötig.

**Aktivierung (wenn Tuwunel ready):**
1. `nextjs-chat/src/lib/matrix/client.ts`: `createClient({ enableEncryptedStateEvents: true })`
2. Bei Raum-Erstellung: `"io.element.msc4362.encrypt_state_events": true` im `m.room.encryption` Event Content

**Homeserver-Status:**
- Tuwunel: in Entwicklung (MSC4362 "Simplified Encrypted State Events")
- Dendrite: kein Support bekannt
- Server-Seite: Raum-Name, Topic, Avatar werden als `m.room.encrypted` Events gesendet — Server sieht nur kryptografisches Rauschen

**Einschränkung:** Nur für neue Räume. Bestehende Räume können nicht nachträglich umgestellt werden.

---

#### 🔄 C-6b: Gruppen-Calls (LiveKit SFU) — Detaillierter Blueprint

**Architektur-Übersicht:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                    Matrix Homeserver (Tuwunel)                       │
│  Leitet nur Signaling-Events weiter (m.rtc.member State Events)     │
└────────────┬──────────────────────────────────┬─────────────────────┘
             │                                  │
    ┌────────▼────────┐              ┌──────────▼──────────┐
    │  Web App Client  │              │    Element X Mobile   │
    │  matrix-js-sdk   │              │    matrix-rust-sdk    │
    │  + livekit-client│              │    + LiveKit native   │
    └────────┬────────┘              └──────────┬──────────┘
             │ WebRTC                           │ WebRTC
             │                                  │
    ┌────────▼──────────────────────────────────▼──────────┐
    │              LiveKit SFU Server                       │
    │  Selective Forwarding Unit — routet Streams            │
    │  E2EE: Media bleibt verschlüsselt (per-participant)   │
    └─────────────────────┬───────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │  JWT Token Service     │
              │  (lk-jwt-service)      │
              │  Matrix OpenID → JWT   │
              └───────────────────────┘
```

**Was deployed werden muss:**

| Komponente | Was | Image/Binary | Port |
|---|---|---|---|
| LiveKit Server | WebRTC SFU | `docker run livekit/livekit-server --dev` | 7880 (HTTP), 7881 (TCP), 7882 (UDP) |
| JWT Token Service | Matrix OpenID → LiveKit JWT Exchange | `element-hq/lk-jwt-service` (Go, ~200 Zeilen) | 8080 |

**Tuwunel-Config:** Keine Änderung nötig! Der Homeserver leitet nur `m.rtc.member` State Events weiter. Die `livekit_service_url` wird vom **Client** in den Events gesetzt, nicht vom Server.

**Client-Code (matrix-js-sdk v41 hat alles):**
```typescript
// MatrixRTC Session beitreten
const rtcSession = client.matrixRTC.getRoomSession(room);
await rtcSession.joinRoomSession([{
    type: "livekit",
    livekit_service_url: "https://your-jwt-service/livekit/jwt"
}]);

// LiveKit Client verbinden (livekit-client npm Package)
import { Room as LKRoom } from "livekit-client";
const lkRoom = new LKRoom();
await lkRoom.connect(livekitServerUrl, jwtToken);
```

**Neue npm Dependency:** `livekit-client`

**Element X Mobile Interop:**
- Element X nutzt `call.element.io` (Element's gehostete Infrastruktur) als Default-SFU
- Mobile User untereinander → Gruppen-Calls funktionieren **jetzt schon** über Element's LiveKit
- Web App + Mobile gemischt → Web App muss zum gleichen SFU verbinden ODER eigenen LiveKit haben
- Empfehlung: Eigener LiveKit. Calls aus der Web App gestartet → alle Teilnehmer verbinden zu unserem LiveKit

**Geschätzter Aufwand: 2-3 Wochen**
- Woche 1: LiveKit + JWT Service deployen, `livekit-client` integrieren, MatrixRTC verdrahten
- Woche 2: Call-UI erweitern (Multi-Party Layout, Teilnehmer-Grid, Speaker-Detection)
- Woche 3: Polish, Element X Interop testen, Edge Cases (Reconnect, Participant Leave/Join)

**Verify Gate (wenn umgesetzt):**
- [ ] LiveKit Docker läuft lokal
- [ ] JWT Service läuft und tauscht Matrix OpenID → LiveKit JWT
- [ ] Web App: Gruppen-Call mit 3+ Teilnehmern starten
- [ ] Video-Grid zeigt alle Teilnehmer
- [ ] Element X User kann Web App Call beitreten
- [ ] E2EE aktiv (per-participant Keys via Matrix To-Device)

---

#### 🔄 C-6c: Bot-Telefonie (TTS/STT) — Detaillierter Blueprint

**Architektur:**
```
User spricht → WebRTC → LiveKit SFU
                              ↓
                    Bot's LiveKit Subscription (livekit-agents Python)
                              ↓
                    VAD (Voice Activity Detection) → Segment erkennen
                              ↓
                    Whisper-Streaming (STT) → Text (~200-500ms)
                              ↓
                    LLM (Claude API) → Antwort-Text (~200-500ms)
                              ↓
                    TTS (edge-tts / Coqui / ElevenLabs) → Audio (~100-300ms)
                              ↓
                    Bot publishes Audio Track → LiveKit SFU → User hört Antwort
```

**Vergleich mit ChatGPT Voice:**

| Aspekt | ChatGPT Voice | Matrix Bot (unser Ansatz) |
|---|---|---|
| Pipeline | Audio → GPT-4o nativ → Audio (ein Schritt) | Audio → Whisper → LLM → TTS (drei Schritte) |
| Latenz | ~300ms | ~800-2000ms |
| Privacy | Audio bei OpenAI | Self-hosted möglich |
| E2EE | Nein | Ja (Bot ist legitimes Raum-Mitglied) |
| Kosten | In ChatGPT Plus inkl. | API-Kosten + Compute |

**Alternative: OpenAI Realtime API** — ersetzt Whisper+TTS durch native Audio-in/Audio-out in GPT-4o. Latenz ~400-600ms, aber teurer (~$0.30/min) und Audio geht zu OpenAI (Privacy-Concern für Trading).

**Empfohlener Stack für Prototyp:**

| Komponente | Empfehlung | Grund |
|---|---|---|
| LiveKit Agent | `livekit-agents` (Python, offizielles SDK) | Handhabt WebRTC, VAD, Audio-Buffering |
| STT | `whisper-streaming` (Python) | Echtzeit-Chunk-basiert, self-hosted |
| LLM | Claude API (Anthropic) | Bereits im Stack |
| TTS | `edge-tts` (Microsoft Neural TTS) | Kostenlos, gute Qualität, niedrige Latenz |

**Matrix-Signaling für den Bot:**
```python
# matrix-nio Client: m.rtc.member Event publizieren
# livekit-agents: Mit LiveKit SFU verbinden, Audio-Tracks subscriben/publishen
# Kein mautrix-go nötig — der Bot ist ein eigenständiger LiveKit-Teilnehmer
```

**Voraussetzung:** C-6b (LiveKit SFU muss laufen)

**Geschätzter Aufwand: 3-5 Wochen**
- Woche 1-2: livekit-agents Setup, Whisper-Streaming Integration, Pipeline-Grundgerüst
- Woche 2-3: Matrix-Signaling (m.rtc.member via matrix-nio), JWT Token Exchange
- Woche 3-4: TTS Integration, Audio-Qualität (Echo Cancellation, Noise)
- Woche 4-5: Polish, Multi-Speaker Handling, Latenz-Optimierung

**Tail Risk:** Audio-Qualität in der Praxis — Echo, Hintergrundgeräusche, mehrere Sprecher gleichzeitig. Das ist wo Voice-Assistenten typischerweise scheitern.

**Verify Gate (wenn umgesetzt):**
- [ ] Bot joined Voice-Call als Teilnehmer (sichtbar in Teilnehmer-Liste)
- [ ] User spricht → Bot transkribiert korrekt (Whisper)
- [ ] Bot-Antwort hörbar innerhalb 2 Sekunden
- [ ] Multi-User: Bot antwortet dem richtigen Sprecher
- [ ] Audio-Qualität akzeptabel (kein Echo, kein Clipping)

---

---

### ✅ Phase 5 — UI-Completeness + Neue Features — ERLEDIGT 25.03.2026

#### ✅ UI-Komponenten (alle implementiert)

**Core UX:**

| ID | Komponente | Dateien |
|---|---|---|
| ✅ **UI-1** | CreateRoomDialog — Name, Topic, E2EE Toggle | `CreateRoomDialog.tsx` (neu), `RoomList.tsx` |
| ✅ **UI-2** | CreateDMDialog — DM starten per User-ID | `CreateDMDialog.tsx` (neu), `RoomList.tsx` |
| ✅ **UI-3** | InviteDialog — User in Raum einladen | `InviteDialog.tsx` (neu), `RoomHeader.tsx` |
| ✅ **UI-4** | ReplyCompose — Antwort mit `m.in_reply_to` | `Message.tsx`, `MessageComposer.tsx`, `MatrixChat.tsx`, `Timeline.tsx` |
| ✅ **UI-5+6** | RoomSettingsPanel + MemberList — Raum-Details, Members, Kick/Ban, Leave | `RoomSettingsPanel.tsx` (neu), `RoomHeader.tsx`, `MatrixChat.tsx` |

**Visual + Moderation:**

| ID | Komponente | Dateien |
|---|---|---|
| ✅ **UI-7** | UserProfileDialog — Displayname + Avatar bearbeiten | `UserProfileDialog.tsx` (neu), `RoomList.tsx` |
| ✅ **UI-8** | SearchPanel — Nachrichten durchsuchen (380px Side-Panel) | `SearchPanel.tsx` (neu), `RoomHeader.tsx`, `MatrixChat.tsx` |
| ✅ **UI-9** | NotificationSettings — Bell/BellOff Mute Toggle pro Raum | `RoomHeader.tsx` |
| ✅ **UI-10** | ModerationActions — Kick/Ban im Member-Panel (Power-Level Check) | `RoomSettingsPanel.tsx` |
| ✅ **UI-11** | Echte Avatare — AvatarImage via Media-Proxy (Room + User) | `types.ts`, `useTimeline.ts`, `Message.tsx`, `RoomList.tsx`, `RoomHeader.tsx` |

**Nice-to-haves:**

| ID | Komponente | Dateien |
|---|---|---|
| ✅ **UI-12** | FullEmojiPicker — 5 Kategorien + Filter statt 8 Quick-Emojis | `Message.tsx` |
| ✅ **UI-13** | MessageForward — Nachricht in anderen Raum weiterleiten | `ForwardDialog.tsx` (neu), `Message.tsx`, `MatrixChat.tsx` |
| ✅ **UI-14** | ReadByDialog — Klick auf Read-Receipts → vollständige Liste | `ReadByDialog.tsx` (neu), `Message.tsx` |

#### ✅ Neue Features (alle implementiert)

| ID | Feature | Dateien |
|---|---|---|
| ✅ **F-1** | Spaces (MSC1772) — SpaceSelector Dropdown + Room-Filtering | `useSpaces.ts` (neu), `SpaceSelector.tsx` (neu), `RoomList.tsx`, `MatrixChat.tsx` |
| **F-2** | `.well-known/matrix/client` — ✅ Config aufgesetzt, 🔄 Verify mit Element X offen | Siehe MOBILE-TEST.md |
| **F-3** | Tuwunel SSO/OIDC — Portierungs-Thema | `identity_provider` Config bei Portierung |
| ✅ **F-4** | Agent-Output für Mobile — Design-Pattern dokumentiert | `specs/agent-output-pattern.md` (neu) |
| ✅ **F-5** | Widget-Vorbereitung — m.widget Placeholder-Rendering | `types.ts`, `Message.tsx` |

**Verify Gates Phase 5:**
- [ ] Raum erstellen → erscheint in RoomList
- [ ] DM starten → User-ID eingeben → DM-Raum erstellt
- [ ] User einladen → InviteDialog → User erscheint im Raum
- [ ] Reply → Banner im Composer, Nachricht mit Reply-Kontext gesendet
- [ ] RoomSettings → Klick auf Raum-Name → Side-Panel mit Details + Members
- [ ] Echte Avatare → Bilder statt nur Initials in RoomList + Messages
- [ ] UserProfile → eigenen Namen/Avatar ändern
- [ ] Suche → Ergebnisse mit Sender + Zeitstempel
- [ ] Mute → Bell-Icon Toggle, Raum stummgeschaltet
- [ ] Kick/Ban → nur für Admins sichtbar, mit Bestätigung
- [ ] Emoji-Picker → 5 Kategorien + Filter
- [ ] Forward → Nachricht an anderen Raum weiterleiten
- [ ] ReadBy → Klick auf Lesebestätigungen → volle Liste
- [ ] Spaces → Dropdown filtert Raumliste nach Space
- [ ] Widget → m.widget Events als Placeholder gerendert

#### Auth-Flow + QR-Codes + Mobile-Onboarding (Referenz)

##### 3 Schichten der Sicherheit

| Schicht | Was | Protokoll | Status |
|---|---|---|---|
| **Authentication** (wer bist du?) | Login, Token | Password / SSO/OIDC | ✅ Password (Dev), SSO bei Portierung |
| **Verification** (vertraue ich deinem Gerät?) | Cross-Signing | Matrix Crypto | ✅ C-3 |
| **Encryption** (E2EE Keys teilen) | Key Exchange | Olm/Megolm | ✅ D-1 |

##### QR-Codes in Matrix

| QR-Code | Zweck | Braucht | Wir haben? |
|---|---|---|---|
| **Login-QR (MSC4108)** | Neues Gerät einloggen (1 Scan) | MAS + Synapse (NUR Synapse!) | ❌ Geht nicht mit Tuwunel |
| **Cross-Signing QR (C-3)** | Geräte-Trust verifizieren (E2EE) | Nur matrix-js-sdk Crypto | ✅ Implementiert |

**MAS (Matrix Authentication Service)** = separater Rust-Service von Element (v1.14.0).
**Funktioniert NUR mit Synapse.** Kein Dendrite, kein Tuwunel. Braucht Synapse Admin-API + MSC3861.
Tuwunel hat MSC3861 nicht implementiert. **MAS ist für uns KEINE Option.**

##### Produktions-Auth-Flow (Tuwunel + NextAuth, OHNE MAS)

```
┌──────────────────────────────────────────────┐
│          Hauptprojekt (tradeview-fusion)       │
│  NextAuth = OIDC Provider                      │
│  User registriert sich → hat Account           │
└──────────────┬───────────────────────────────┘
               │ OIDC (Tuwunel ist Client)
               ▼
┌──────────────────────────────────────────────┐
│  Tuwunel (Homeserver, Legacy SSO seit v1.5.0) │
│  identity_provider Config → zeigt auf NextAuth│
│  User klickt "Login via SSO" in Element X     │
│  → Browser öffnet → NextAuth Login            │
│  → Tuwunel erstellt/verknüpft Matrix-Account  │
│  → Access Token ausgestellt                   │
└──────────────┬───────────────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
 Webapp     Element X   FluffyChat
(matrix-js)  (Mobile)   (Mobile)
```

**Hinweis:** MAS-Login-QR (1-Scan wie WhatsApp) geht nur mit Synapse+MAS.
Für Tuwunel nutzen wir SSO-Button + Cross-Signing QR (2 Schritte, aber kein Password-Tippen).

##### Mobile-Onboarding — 3 Optionen

**Option 1 — .well-known + SSO (Basis) — ✅ Config aufgesetzt, 🔄 Verify offen:**
```
1. User öffnet Element X → tippt Homeserver-Domain ein (einmalig)
2. Element X findet Login-Methoden via .well-known/matrix/client
3. SSO-Button → Browser → NextAuth Login (ggf. schon eingeloggt → automatisch)
4. Tuwunel gibt Access Token → Element X eingeloggt
5. Webapp zeigt Cross-Signing QR → User scannt → E2EE verifiziert
→ 1x Domain tippen + SSO-Klick + QR-Verify
```

**Option 2 — Deep Link QR (kein Domain-Tippen, Erweiterung):**
```
1. Webapp zeigt QR-Code mit Deep Link: element://connect?hs_url=matrix.example.com
2. Element X öffnet sich mit vorausgefülltem Homeserver
3. SSO-Login + Cross-Signing wie bei Option 1
→ Kein manuelles Tippen, aber 2 Schritte (SSO + Verify)
```

**Option 3 — Custom Onboarding Page (bester Kompromiss, spätere Erweiterung):**
```
1. Webapp zeigt QR-Code → öffnet: https://app.example.com/mobile-setup
2. Onboarding-Seite erkennt Plattform (iOS/Android)
3. Link zu Element X im App Store (oder öffnet direkt wenn installiert)
4. Deep Link mit vorausgefülltem Homeserver
5. SSO-Login startet automatisch
6. Cross-Signing QR wird direkt in der Onboarding-Seite angezeigt
→ 1 QR-Scan → geführter Flow durch alles
```

| Option | User-Aufwand | Braucht MAS? | Unser Aufwand |
|---|---|---|---|
| MSC4108 Login-QR | 1 Scan, fertig | Ja (nur Synapse) | **Unmöglich mit Tuwunel** |
| Option 1: .well-known + SSO | Domain tippen + SSO + QR-Verify | Nein | Klein |
| Option 2: Deep Link QR | QR scannen + SSO + QR-Verify | Nein | Mittel |
| Option 3: Onboarding Page | 1 QR → geführt | Nein | Mittel-Groß |

**Plan:** Option 1 zuerst (Basis). Option 3 als Erweiterung wenn Produktion näher rückt.

##### Tuwunel OIDC Config (bei Portierung einrichten)

```toml
# tuwunel.toml — Identity Provider (Produktion)
[global.identity_provider.nextauth]
issuer = "https://app.example.com"         # NextAuth OIDC Discovery URL
client_id = "tuwunel-matrix"
client_secret_file = "/secrets/oidc-secret" # aus Datei lesen, nicht inline
registration = true                         # SSO kann neue Matrix-Accounts erstellen
trusted = true                              # SSO-Accounts automatisch verknüpfen
```

##### Priorität

- **Dev (jetzt):** Password-Login + `.well-known` + Cross-Signing QR
- **Produktion:** NextAuth als OIDC-Provider + Tuwunel `identity_provider` Config
- **Später:** Option 3 Custom Onboarding Page für eleganten Mobile-Flow

---

### Zukunft / Extern blockiert

| ID | Feature | Status | Details |
|---|---|---|---|
| **C-5** | PQXDH / vodozemac | Bei Linux-Portierung | CGO + libvodozemac, automatisch hybrid X25519 + ML-KEM-768 |
| **C-7** | MLS (RFC 9420, MSC4256) | Ecosystem nicht bereit, ~2027 | RFC finalisiert, aber: Tuwunel ❌, matrix-js-sdk ❌, mautrix-go ❌, Element X ❌. Wenn SDK ready → Drop-in, kein Architektur-Change (Megolm und MLS sind auf Protokollebene austauschbar). Relevant für Agent-Swarm (10+ Agents): O(log n) statt O(n) Key-Exchange + Perfect Forward Secrecy pro Agent. |
| **C-9** | Room Version 12 (Project Hydra) | Automatisch | room_id = kryptografischer Hash, kein UI-Change nötig |

### Portierung → tradeview-fusion (wenn bereit)

| Schritt | Was |
|---|---|
| Go Appservice | → `go-backend/internal/matrix/` |
| Python Bridge | → `python-backend/python-agent/agent/matrix_channel.py` |
| React Components | → `src/components/matrix/` (Theme merge) |
| Homeserver | Tuwunel auf Linux (single binary) |
| NATS ersetzen | → bestehende gRPC IPC |
| OIDC Integration | → bestehende NextAuth |

---

## Änderungshistorie

| Datum | Was |
|---|---|
| 24.03.2026 | exec-02 erstellt — 17 Features + Quick-Wins identifiziert |
| 24.03.2026 | Phase 1-3 Features implementiert (QW-1–4, B-1–6, B-9, C-1, C-3, D-1, D-2) |
| 25.03.2026 | exec-03 erstellt — Deep-Dive Code Review aller Features |
| 25.03.2026 | 10 Bugfixes (3 Critical, 7 Important) |
| 25.03.2026 | C-8 Key Backup + C-10 MSC4381 implementiert |
| 25.03.2026 | Infrastruktur: .env Trennung, echte Keys, Agent-Prefix konfigurierbar |
| 25.03.2026 | QW-4 Media-Proxy für Produktion, B-5 Multi-User Token, D-1 IndexedDBStore |
| 25.03.2026 | QW-1 direktes HTML-Parsing (unified), C-2 erledigt via QW-4 |
| 25.03.2026 | Detaillierte Blueprints für C-6b (LiveKit), C-6c (Bot-Voice), C-4 (Encrypted State) |
| 25.03.2026 | B-7 Polls + B-8 Threads (Side-Panel) implementiert |
| 25.03.2026 | Homeserver-Config Audit: Room V12, RocksDB Direct I/O, DB-Backups, E2EE-Default |
| 25.03.2026 | Phase 5 UI-Completeness: 14 fehlende UI-Komponenten + 5 neue Features identifiziert |
| 25.03.2026 | ChatGPT-Forschung abgeglichen: Spaces, .well-known, MAS/OIDC, Agent-Output, Widgets |
| 25.03.2026 | MAS-Korrektur: MAS nur Synapse, Tuwunel hat eigenes Legacy SSO/OIDC |
| 25.03.2026 | .well-known Config + LAN-IP + Firewall für Mobile-Test |
| 25.03.2026 | **Phase 5 komplett implementiert:** 14 UI-Komponenten + Spaces + Agent-Output + Widgets (11 neue Dateien, 10 geänderte) |
