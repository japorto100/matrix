# exec2-03b: Advanced Matrix Options (Server-Auswahl, Onboarding, BYOS)

**Datum:** 10.04.2026
**Status:** Geplant (Backlog)
**Abhaengig von:** exec2-01 (Matrix Chat Core), exec-merge-chat (Hauptprojekt-Integration)
**Kontext:** Matrix ist unsichtbare Infrastruktur fuer Chat + Agents, kein eigenstaendiger Client.

---

## Architektur-Entscheidung: Account-Provisioning

### Default: Auto-Create auf eigenem Server (empfohlen)

```
User registriert sich bei tradeview-fusion
  → App erstellt automatisch Matrix-Account auf unserem Tuwunel
  → User sieht "Matrix" nie — ist unsichtbare Infrastruktur
  → Agents (@agent-*) sind lokal, keine Federation noetig
  → E2EE Keys werden automatisch gemanaged
```

**Warum:**
- Minimale Onboarding-Friction (User will traden, nicht Matrix konfigurieren)
- Agents leben lokal → schnellste Kommunikation, kein Federation-Overhead
- Volle Kontrolle ueber Message Retention, Compliance, Key Management
- Standard-Pattern fuer Apps die Matrix als Infrastruktur nutzen (Beeper, Element Call)

**Implementierung:** OIDC/MAS (Matrix Authentication Service)
- User loggt sich in tradeview-fusion ein (unsere Auth)
- MAS provisioniert Matrix-Session automatisch (delegated auth)
- Kein separater Matrix-Login noetig
- Token-Refresh transparent im Hintergrund

### Advanced Option: BYOS (Bring Your Own Server)

```
User → Settings → Advanced → "Eigenen Matrix-Server verwenden"
  → Homeserver URL eingeben (z.B. matrix.org, eigener Server)
  → Login/Registrierung auf externem Server
  → Federation: User joint Raeume auf unserem Server
  → Agents erreichbar via Federation (mit Einschraenkungen)
```

**Wann relevant:**
- Power-User mit bestehendem Matrix-Account
- Datenschutz-bewusste User die eigenen Server betreiben
- Enterprise mit eigenem Homeserver

**Einschraenkungen bei BYOS:**
- Federation-Latenz (Messages gehen ueber 2 Server)
- E2EE Key-Austausch komplexer (Cross-Server Verification)
- Nicht alle Features garantiert (Live-Location, Voice via LiveKit)
- Agent-Interaktion ueber Federation getestet sein muss

---

## Onboarding UI

### Phase 1: Registrierung/Login (Hauptprojekt)

```
┌─────────────────────────────────────────┐
│  tradeview-fusion                       │
│                                         │
│  [Email]     ___________________        │
│  [Passwort]  ___________________        │
│                                         │
│  [Registrieren]  [Login]                │
│                                         │
│  ─── oder ───                           │
│  [Google]  [GitHub]  [Apple]            │
│                                         │
│  (i) Matrix-Chat wird automatisch       │
│      eingerichtet.                      │
│      Eigenen Server? → Erweitert        │
└─────────────────────────────────────────┘
```

### Phase 2: Post-Login Setup (einmalig)

```
┌─────────────────────────────────────────┐
│  Willkommen! Dein Setup:               │
│                                         │
│  ✅ Account erstellt                    │
│  ✅ Matrix-Chat bereit                  │
│  ✅ Trading-Agent verfuegbar            │
│                                         │
│  Optionen:                              │
│  ○ Standard (empfohlen)                 │
│    Unser Server, alles automatisch      │
│                                         │
│  ○ Eigener Matrix-Server (erweitert)    │
│    Homeserver URL: _______________      │
│    ⚠ Federation noetig, nicht alle     │
│      Features garantiert                │
│                                         │
│  [Weiter]                               │
└─────────────────────────────────────────┘
```

### Phase 3: E2EE Key Setup (bei BYOS oder manuellem Setup)

```
┌─────────────────────────────────────────┐
│  Verschluesselung einrichten            │
│                                         │
│  ○ Automatisch (empfohlen)              │
│    Cross-Signing Keys werden generiert  │
│    Key Backup auf unserem Server        │
│                                         │
│  ○ Bestehende Keys importieren          │
│    Security Key eingeben: ________      │
│    oder Key-Datei hochladen [Browse]    │
│                                         │
│  ○ Neuen Key generieren                 │
│    ⚠ Alte Nachrichten nicht lesbar     │
│                                         │
│  [Einrichten]                           │
└─────────────────────────────────────────┘
```

---

## Settings (nach Onboarding)

### Matrix Settings in control-ui (User Mode)

```
control-ui → Settings Tab:

Matrix Chat
  Server: tuwunel.tradeview.local (Standard)  [Aendern]
  Account: @user123:tuwunel.tradeview.local
  Status: Verbunden ✅

Verschluesselung
  Cross-Signing: Verifiziert ✅
  Key Backup: Aktiv (letzte Sicherung: vor 2h)
  [Security Key anzeigen]  [Key Backup exportieren]
  [Neuen Key generieren]   [Geraet verifizieren]

Erweitert
  Sliding Sync URL: https://tuwunel.tradeview.local/sync
  [Anderen Server verbinden]  ← BYOS Flow
```

---

## Implementierung

### Phase A: Auto-Create (Minimum Viable)

- [ ] **A1:** OIDC/MAS Integration
  - tradeview-fusion Auth → MAS → Tuwunel Account Provisioning
  - Oder: Appservice Admin API fuer Account-Erstellung (einfacher, weniger OIDC-Abhaengigkeit)
  - Token wird im Frontend-Session gespeichert

- [ ] **A2:** Post-Login Matrix Init
  - Nach Login: `initMatrixClient()` mit auto-provisioniertem Token
  - Cross-Signing Bootstrap automatisch (wie in Go Appservice)
  - Key Backup automatisch aktiviert

- [ ] **A3:** Onboarding Wizard (optional)
  - Nur bei Erstanmeldung
  - Zeigt "Chat bereit" Status
  - Skip-Button fuer erfahrene User

### Phase B: BYOS (Advanced)

- [ ] **B1:** Server-Auswahl UI
  - Homeserver URL Input + Well-Known Discovery
  - Server-Capabilities pruefen (Sliding Sync, E2EE, etc.)
  - Warnung bei fehlenden Features

- [ ] **B2:** Federation Verify
  - Externer User joint Raeume auf unserem Server
  - Agent-Interaktion ueber Federation testen
  - E2EE Cross-Server Verification

- [ ] **B3:** E2EE Key Management UI
  - Security Key anzeigen/exportieren
  - Key Backup import/export
  - Cross-Signing Verification Flow (QR + SAS)
  - Neuen Key generieren (mit Warnung)

### Phase C: Multi-Account (spaeter)

- [ ] **C1:** Mehrere Matrix-Accounts gleichzeitig
  - Primaer: eigener Server (Standard)
  - Sekundaer: externer Server (BYOS)
  - Account-Switcher in Matrix Chat UI

---

## Verify-Gates (Phase A/B/C)

> **Ausgelagert nach `exec-blocking.md` (C6).** Phase A/B/C sind grosse Feature-Bloecke
> die eigene Exec-Sessions brauchen. Gates bleiben in `exec2-04-verify-gates.md` (A/B/C)
> aber werden erst aktiv wenn die Abhaengigkeiten (OIDC/MAS, Federation, Merge-Chat) erfuellt sind.
> Hier nur noch als Referenz, nicht als aktive TODO-Liste.

---

## Risiken

| Risiko | Mitigation |
|---|---|
| OIDC/MAS nicht reif genug fuer Tuwunel | Fallback: Appservice Admin API fuer Account-Erstellung |
| Federation-Latenz bei BYOS | Klar kommunizieren: "Standard empfohlen, Federation = langsamere Experience" |
| E2EE Key-Verlust | Automatisches Key Backup, Security Key im Onboarding prominent zeigen |
| Multi-Account Komplexitaet | Phase C nur bei echtem Bedarf, nicht voreilig |

---

## Abhaengigkeiten

- exec2-01: Matrix Chat Core (Basis-Features)
- exec-05: NATS + E2EE Pipeline (Cross-Signing, Key Backup)
- exec-merge-chat: Hauptprojekt-Integration (Onboarding-Flow dort)
- exec-blocking C2: OIDC/MAS (Tuwunel Support noetig)
- Tuwunel: Well-Known Discovery, MAS Support, Federation Config

---

## Infrastruktur-Arbeit: Tunnel + Tuwunel v1.6.0-rc Upgrade

**Datum:** 11.04.2026
**Status:** Umgesetzt, Phase 1+2 Service-Level verifiziert. Client-Level Tests ausstehend.
**Letztes Update:** 11.04.2026 (Abend) — v1.6.0-rc startet sauber, SeaweedFS S3 Storage Provider End-to-End verbunden.
**Kontext:** Mobile-Tests mit Element X brauchen HTTPS (kein bore), v1.6.0-rc bringt MSC2246 (Async Uploads) + Storage Provider (SeaweedFS S3) die direkt zwei offene Pain Points adressieren.

### 1. Cloudflare Tunnel als primaerer Dev-Tunnel

**Problem:** Element X verweigert HTTP, bore liefert nur TCP ohne TLS. Fuer Mobile-Tests brauchten wir HTTPS ohne Domain-Kauf.

**Loesung:** cloudflared Quick Tunnel (`tools/cloudflared.exe tunnel --url http://localhost:8448`) — war bereits als primaerer Fallback in `dev-stack2.ps1` konfiguriert, aber URL lag nur im Log.

**Umgesetzt:**
- `dev-stack2.ps1` Summary zeigt die `https://*.trycloudflare.com` URL jetzt direkt in der Terminal-Ausgabe (gelb, als "Tunnel (Element X)")
- Poll-Schleife ueber `logs/dev-stack/tunnel.stderr.log` bis zu 5 Minuten, Status-Updates alle 15 Sekunden, Fallback zeigt letzte 5 Log-Zeilen bei Timeout

**Cloudflare Free Tier — relevante Limits:**
- Quick Tunnel: 200 in-flight Requests hart (dann HTTP 429), keine SSE (Matrix-Sync-Long-Polling geht trotzdem durch)
- Request-Body-Cap: 100 MB pro Request (Free + Pro; Business 200 MB, Enterprise 500 MB)
- Bandbreite: unbegrenzt im Free Tier
- URL aendert sich bei jedem Neustart (Quick Tunnel ohne Domain)

**Konsequenz fuer Tuwunel-Config:** `max_request_size` auf 100 MB gesetzt in allen 5 Configs (`tuwunel.toml`, `tuwunel.example.toml`, `tuwunel.image.toml`, `tuwunel.image.example.toml`, `tuwunel.prod.toml`). Vorher 500 MB → wuerde bei CF-Tunnel als 413 zurueckgewiesen.

### 2. Tuwunel v1.6.0-rc parallel installiert

**Warum Upgrade:** 138 Commits seit v1.5.1, zwei davon adressieren direkt unsere Pain Points:

- **MSC2246 Async Media Uploads** — entkoppelter Upload-Flow (`POST /_matrix/media/v1/create` reserviert MXC-URI, dann `PUT /_matrix/media/v3/upload/{serverName}/{mediaId}`), Voraussetzung fuer resumable Uploads in Clients die es unterstuetzen (Element X teilweise).

- **Configurable Media Storage Providers** — Tuwunel kann Media direkt in S3-kompatible Stores schreiben. Wir haben SeaweedFS bereits im devstack auf Port 8333 laufen → kein zusaetzlicher Service noetig.

**Weitere Features (verfuegbar, nicht sofort aktiv genutzt):**
- MSC2965/2964/2966/2967 — OIDC-Server (nicht nur -Client) — spaeter als MAS-Ersatz
- MSC2454 — SSO UIA Fix fuer E2EE-Key-Reset
- MSC3706 Federation, MSC4186 Lazy-Loading Rule 2, MSC4143 neuer Endpoint
- Forbid duplicate reactions, Admin Module Load Wait Fix
- Rust 1.94, systemd socket activation

### 3. Parallel-Setup fuer risikoarmes Testing

**Design-Entscheidung:** Shared DB + Pre-flight-Backup (nicht separate DB).

Begruendung: Dev-Historie ist minimal, Element X muss sich nicht neu einloggen, echter Test mit Bestandsdaten. v1.6.0-rc fuehrt Schema-Migration durch → Rollback nur mit Backup moeglich, deshalb Pre-flight-Script.

**Neue Artefakte:**

| Pfad | Zweck |
|---|---|
| `tools/tuwunel-v1.6` | ELF Binary v1.6.0-rc (~87 MB), liegt neben bestehendem `tools/tuwunel` (v1.5.1) |
| `homeserver/tuwunel.v1.6.toml` | Dev-Config fuer RC: shared DB, Storage-Provider definiert (media + seaweedfs), MSC2246 Rate-Limits explizit, `store_media_on_providers = ["media"]` als Start-State |
| `scripts/backup-before-v1.6.ps1` | Pre-flight Backup: prueft Port 8448 ist frei → kopiert `data/db` und `data/media` in `data/db-pre-v1.6` und `data/media-pre-v1.6` → druckt Rollback-Kommandos |
| `scripts/dev-stack2.ps1` | Neuer `-Tuwunel16` Switch: routet auf v1.6-Binary + v1.6-Config, gelbe Terminal-Meldung zur Abgrenzung |
| `_ref/tuwunel-v1.6.0-rc/` | Referenz-Verzeichnis: `tuwunel-example.toml` (upstream default), `configuration.md`, `deploying.md`, `configuration-examples.md`, `storage-provider-schema.rs` (Rust-Quellcode-Snippet fuer StorageProvider-Schema), `COMPARISON.md` (Feature-Diff v1.5.1 → v1.6.0-rc), `TESTING.md` (5-Phasen-Runbook) |

**Tuwunel-Configs (alle 5) — max_request_size auf 100 MB gesetzt:**
`104857600 # 100 MB (Cloudflare Free Plan Limit)` statt vorher `524288000 # 500 MB`. Kommentar erklaert den Zusammenhang mit dem CF-Body-Cap.

### 4. SeaweedFS S3 Storage Provider Config

Aus dem Rust-Quellcode (`src/core/config/mod.rs:2986`) extrahierte Struktur:

```toml
[global.storage_provider.seaweedfs.S3]
endpoint               = "http://192.168.1.34:8333"
bucket                 = "matrix-media"
region                 = "us-east-1"
key                    = "seaweedfs"          # aus tools/seaweedfs/s3.json
secret                 = "seaweedfs-secret"
base_path              = "tuwunel-v1.6/"       # Prefix fuer RC-Uploads im Bucket
use_https              = false
use_payload_signatures = true
startup_check          = true

[global.storage_provider.media.local]
base_path                = "./homeserver/data/media"
create_if_missing        = true
delete_empty_directories = true
startup_check            = true
```

**Wichtig:** Provider-Typnamen sind case-sensitive — `local` klein, `S3` gross (aus dem Rust `#[serde]` Enum).

**Schrittweise Aktivierung** (statt Big-Bang):
1. Phase 1-2 in TESTING.md: `store_media_on_providers = ["media"]` → reiner RC-Smoke-Test ohne S3-Abhaengigkeit
2. Phase 3: auf `["seaweedfs"]` umstellen → neue Uploads landen in SeaweedFS, alte bleiben lesbar via Fallback

### 5. Was explizit NICHT gemacht wurde

- **OIDC Server Migration** — v1.6.0 bringt Tuwunel als OIDC-Server, aber wir haben NextAuth als Identity-Provider (Tuwunel als OIDC-Client). Switch ist separate Entscheidung, nicht im Scope dieses RC-Tests.
- **`max_request_size` erhoeht** — bleibt bei 100 MB solange CF-Tunnel im Einsatz. Phase 4 im Runbook erlaubt testweise 500 MB nur fuer LAN-direkte Verbindungen.
- **Element X Fork** — MSC2246 funktioniert nur mit Clients die es implementieren. Wir testen mit aktuellem Element X, kein Custom-Fork.

---

## 6. Test-Ergebnisse & Folge-Fixes (11.04.2026 Abend)

Beim ersten Devstack-Start mit `-Tuwunel16` wurden mehrere Probleme gefunden und gefixt. Die Sections 1-5 oben haben an manchen Stellen veraltete / vor-Test Annahmen; dieser Abschnitt ist die aktuelle Ground Truth.

### 6.1 Korrekturen an den Annahmen aus Sections 1-5

**Media-Provider `base_path`** — Section 4 zeigt `./homeserver/data/media`. **Korrekt ist `./homeserver/data/db/media`**, weil Tuwunel v1.5 den Default-Media-Pfad als `<database_path>/media` anlegt. Die alten Bilder (100 MB, aus Dev-Tests) liegen dort, nicht im separaten `media/` Ordner. Wenn der Provider-Pfad nicht matcht, findet v1.6 alte Thumbnails nicht.

**Storage Provider `endpoint`** — Section 4 zeigt `http://192.168.1.34:8333`. **Korrekt ist `http://127.0.0.1:8333`**. Grund: Ubuntu ist WSL1 (nicht WSL2), teilt sich Windows' Netzwerk-Stack, Tuwunel in WSL1 erreicht `127.0.0.1` identisch wie Windows. SeaweedFS wird im devstack explizit an `-ip.bind=127.0.0.1` gebunden.

**SeaweedFS Bucket-Init** — Section 5 behauptet `startup_check = true` erzeugt den Bucket on-the-fly. **Das ist falsch.** Tuwunel macht einen S3 LIST-Request auf den Bucket und schlaegt fehl wenn der nicht existiert. Der Bucket `matrix-media` muss **manuell** erstellt werden (via AWS CLI oder SeaweedFS Filer UI).

### 6.2 Zusaetzlich gefundene v1.6 Breaking Changes

**Appservice `id` Feld ist jetzt required.** In v1.5 wurde der TOML-Section-Key (`[global.appservice.trading-agent]`) implizit als appservice id uebernommen. In v1.6 muss die id **explizit im Body** stehen und **mit dem Section-Key matchen**:

```toml
[global.appservice.trading-agent]
id = "trading-agent"   # NEU in v1.6
url = "http://127.0.0.1:8090"
```

Ohne diese Zeile startet zwar Tuwunel, aber der Appservice-Manager crasht mit `service "appservice" aborted: Invalid id in config appservice: does not match trading-agent`. Fix wurde in **alle 6 Tuwunel-Configs** eingetragen (auch v1.5-Configs, als Forward-Compat-Vorbereitung).

### 6.3 SOTA Config-Improvements fuer alle Configs

Nach Review des v1.6-Default-Templates (`_ref/tuwunel-v1.6.0-rc/tuwunel-example.toml`) wurden 4 Optionen in alle 6 Configs eingetragen:

| Option | Wert | Begruendung |
|---|---|---|
| `error_on_unknown_config_opts` | `true` | Safety-Net: falscher/veralteter Key → Fail-fast beim Start statt stiller Ignore |
| `zstd_compression` | `true` (Dev) / `false` (Prod) | HTTP Response-Compression spart Bandbreite ueber CF Tunnel. In Prod mit TLS direkt auf Tuwunel: **BREACH-Attack Risiko** — explizit `false` mit Kommentar |
| `prune_missing_media` | `false` | Explizit: verwaiste DB-Eintraege nicht automatisch loeschen wenn Media-File fehlt (Migrations-Safety) |
| `encryption_enabled_by_default_for_room_type` | `"none"` (vorher `"off"`) | Canonical v1.6 Wert. Vorher war `"off"` ein "fiel auf Default zurueck"-Wert, jetzt canonical |

### 6.4 Devstack Startup-Order Bug

Im ersten Test-Lauf schlug der Storage-Provider `seaweedfs` startup_check fehl mit 10 retries, obwohl Connectivity (via curl verifiziert) funktionierte. Root-Cause:

**Tuwunel war in `dev-stack2.ps1` vor SeaweedFS registriert** (ab Zeile ~274) → Phase-C iteriert in Registration-Order → Tuwunel startet zuerst → versucht `127.0.0.1:8333` zu erreichen → SeaweedFS noch nicht gestartet → 10 retries in ~3s → Abort. **Dann** startet SeaweedFS (zu spaet).

**Fix:** Register-Service Block von SeaweedFS an den Anfang der infra-Tier-Registration verschoben (vor Tuwunel). `$script:services = [ordered]@{}` garantiert dass Iteration == Insertion-Order.

Nach dem Fix zeigt der devstack-Output:
```
Registered: seaweedfs, tuwunel      # vorher: tuwunel, seaweedfs
[seaweedfs] Ready on :8333           # startet zuerst
[tuwunel] Ready on :8448             # startet danach, findet S3 ready
```

Und im Tuwunel-Log:
```
INFO Connected to storage provider name=media
INFO Listening on ["tcp:0.0.0.0:8448"]
INFO Connected to storage provider name=seaweedfs     ← erfolgreich!
```

Kein ERROR, keine Retry-Loops mehr.

### 6.5 Housekeeping

- **616 MB RocksDB WAL-Archive geloescht** (`homeserver/data/db/archive/*.log`, Files vom 27.03.2026). Alte Write-Ahead-Logs aus einer frueheren Test-Session, nicht Teil der Live-DB. Auch im Backup-Verzeichnis (`db-pre-v1.6/archive/`) entfernt. DB ging von 720 MB auf 105 MB zurueck (davon 100 MB Media in `db/media/`, 5 MB echte Matrix-Metadaten).
- **SeaweedFS Bucket `matrix-media` manuell angelegt** via `aws --endpoint-url http://127.0.0.1:8333 s3 mb s3://matrix-media`. Noetig weil Tuwunel den Bucket nicht on-the-fly erzeugt.

### 6.6 Dokumentierte WSL1-Quirks

Tuwunel zeigt beim Startup einen Warning:
```
WARN tcp set_tcp_user_timeout error: Protocol not available (os error 92)
```

Das ist **harmlos**: WSL1 implementiert die `TCP_USER_TIMEOUT` Socket-Option nicht, Rust `hyper` setzt sie als Best-Effort und loggt die Warning. Verbindung funktioniert trotzdem (siehe erfolgreiches `Connected to storage provider name=seaweedfs` direkt danach). Bei WSL2-Migration oder Prod-Linux-Deployment verschwindet die Warning automatisch.

### 6.7 Bisher verifiziert (Service-Level)

| | Status |
|---|---|
| Tuwunel v1.6.0-rc Binary laeuft in WSL1 | ✅ `tuwunel 1.6.0` aus `--version` |
| Schema-Migration v1.5.1 → v1.6.0 | ✅ `Loaded RocksDB database with schema version 17` |
| Config-Parsing (alle Keys v1.6-kompatibel) | ✅ implizit durch `error_on_unknown_config_opts = true` + kein Abort |
| Media Storage Provider (local) | ✅ `Connected to storage provider name=media` |
| Media Storage Provider (SeaweedFS S3) | ✅ `Connected to storage provider name=seaweedfs` |
| HTTP Listener | ✅ `Listening on ["tcp:0.0.0.0:8448"]` |
| Appservice Config Parsing | ✅ kein Abort mehr (nach `id = "trading-agent"` Fix) |
| devstack `-Tuwunel16` Flag | ✅ gelbe Summary-Meldung + korrekte Binary-/Config-Wahl |
| Devstack Clean-Shutdown | ✅ `finally{}` Cleanup killt sowohl WSL als auch weed.exe |

### 6.8 Was noch aussteht (Client/Runtime-Level)

- **Element X Login + Chat-History-Check** (Gate J1 Client-Teil) — braucht Mobile-Geraet im LAN
- **Tatsaechlicher Media-Upload via Client** (Gate J3 Client-Teil) — Bild/Video posten, in SeaweedFS-Bucket via Filer UI verifizieren
- **MSC2246 Async Upload Detection** (Gate J4) — Log nach `POST /media/v1/create` + `PUT /media/v3/upload/{serverName}/{mediaId}` pruefen
- **max_request_size > 100 MB LAN-Test** (Gate J5) — optional, nur wenn grosse Datei-Uploads gebraucht werden
- **Go Appservice Integration** — andere Claude-Session arbeitet aktuell daran, Test sobald verfuegbar
- **Merge-Entscheidung v1.6.0 stable** (Gate J6) — sobald upstream stable released
