# Tuwunel v1.5.1 → v1.6.0-rc — Config Comparison

**Stand:** 2026-04-11
**Quelle:** https://github.com/matrix-construct/tuwunel/compare/v1.5.1...v1.6.0-rc (138 commits)
**Aktuelle Config:** `homeserver/tuwunel.toml`
**Referenz:** `_ref/tuwunel-v1.6.0-rc/tuwunel-example.toml`

---

## 1. Was wir bereits nutzen (keine Änderung nötig)

Unsere aktuelle `tuwunel.toml` benutzt 30 der ca. 180 verfügbaren Optionen. Alle diese bleiben in v1.6.0-rc identisch:

| Option | Wert | Bleibt |
|---|---|---|
| `server_name`, `database_path`, `address`, `port`, `log` | dev-local | ✅ |
| `default_room_version = "12"` | Hydra (State Res 2.1) | ✅ |
| `allow_registration`, `registration_token`, `auto_join_rooms` | dev | ✅ |
| `allow_federation = false` | isoliert | ✅ |
| `encryption_enabled_by_default_for_room_type = "off"` | Client entscheidet | ✅ |
| Presence-Tripel (`allow_local/incoming/outgoing_presence`) | dev | ✅ |
| `max_request_size = 104857600` | 100 MB (CF-Cap) | ✅ |
| `allow_legacy_media = true` | MSC3916 Fallback | ✅ |
| TURN/STUN-URIs (Metered.ca) | dev | ✅ |
| `show_all_local_users_in_user_directory = true` | Team-Mode | ✅ |
| `rocksdb_direct_io = false` | WSL+NTFS safe | ✅ |
| `database_backup_path` / `database_backups_to_keep` | dev | ✅ |
| `[global.well_known]` + `[[rtc_transports]]` (LiveKit) | Element X | ✅ |
| `[global.appservice.trading-agent]` | Go Appservice | ✅ |

**Nichts davon bricht.** v1.6.0-rc ist voll rückwärts-kompatibel auf dieser Ebene.

---

## 2. Neue Features die wir AKTIV nutzen sollten

### 2.1 MSC2246 — Asynchronous Media Uploads (automatisch aktiv)

**Was es ist:** Client kann per `POST /_matrix/media/v1/create` erst eine MXC-URI reservieren, dann die eigentlichen Bytes in einem separaten `PUT /_matrix/media/v3/upload/{serverName}/{mediaId}` hochladen. Der Upload ist dadurch **von der ursprünglichen Request-Latenz entkoppelt** und kann theoretisch mit custom Clients auch resumable werden.

**Keine Config-Flag nötig** — läuft automatisch, sobald v1.6.0-rc installiert ist. Aber es gibt 4 neue Rate-Limit-Knobs:

```toml
# Async Media Upload — MSC2246 (neu in v1.6.0)
max_pending_media_uploads = 5           # wie viele MXC-URIs ein User gleichzeitig offen haben kann
media_create_unused_expiration_time = 86400  # 24h — dann wird ungenutzte MXC-URI recycled
media_rc_create_per_second = 10         # Rate-Limit: 10 MXC-URI-Creates pro Sekunde pro User
media_rc_create_burst_count = 50        # Burst-Cap
```

**Empfehlung:** Defaults sind sinnvoll für unsere Nutzung. Für Dev-Environment nur dann anpassen wenn Tests aktiv viele parallele Uploads simulieren.

**Haken:** Client-Unterstützung.
- ✅ Element X (Android/iOS) — implementiert MSC2246
- ⚠️ FluffyChat — unklar, vermutlich nur Legacy-Upload
- ⚠️ Element Web — je nach Version

Bei Clients ohne MSC2246 läuft weiterhin der **alte POST-Upload-Pfad** (Single-Request). Kein Regression-Risiko.

### 2.2 Storage Provider — SeaweedFS S3 Integration

**Was es ist:** Tuwunel-Media (Bilder, Videos, Voice Messages) kann direkt in einen S3-kompatiblen Store geschrieben werden statt in den lokalen RocksDB-Pfad. Wir haben SeaweedFS bereits im devstack laufen (`:8333`).

**Config-Schema (neu in v1.6.0):**

```toml
# Welche Provider stehen überhaupt zur Verfügung?
media_storage_providers = ["media", "seaweedfs"]

# Wo sollen NEUE Uploads landen?
# Entry MUSS auch in media_storage_providers stehen.
store_media_on_providers = ["seaweedfs"]

# Provider-Definition: local filesystem (Fallback für alte Media)
[global.storage_provider.media.local]
base_path = "./homeserver/data/media"
create_if_missing = true
delete_empty_directories = true
startup_check = true

# Provider-Definition: SeaweedFS S3
[global.storage_provider.seaweedfs.S3]
url = "s3://matrix-media"
endpoint = "http://192.168.1.34:8333"    # SeaweedFS S3 API aus WSL Sicht
region = "us-east-1"                      # SeaweedFS akzeptiert beliebige Region
key = "seaweedfs"                         # aus tools/seaweedfs/s3.json
secret = "seaweedfs-secret"               # aus tools/seaweedfs/s3.json
base_path = "tuwunel/"                    # Prefix innerhalb des Buckets
use_https = false                         # SeaweedFS läuft unverschlüsselt lokal
use_payload_signatures = true
startup_check = true
```

**Rust-Enum:** `pub enum StorageProvider { local(..), S3(..), None }` aus `src/core/config/mod.rs:2986`. Beide Provider-Typen sind implementiert, Namen **case-sensitive**: `local` klein, `S3` groß.

**Migration bestehender Media:** Tuwunel v1.6.0 hat neue Admin-Kommandos dafür. Siehe Commits:
- `Add inter-provider commands and migration`
- `Support bulk deletion requests to storage provider`

Nach Installation wird's ein `!admin media migrate <src-provider> <dest-provider>` geben (konkrete Syntax muss nach Install geprüft werden).

### 2.3 OIDC Server (MSC2965/2964/2966/2967) — **NICHT JETZT**

Tuwunel wird **OIDC-Server** (nicht nur Client). Heißt: Eigener OIDC-Flow statt externem MAS.

**Status für uns:** Spannend, aber **nicht jetzt**. Wir haben NextAuth bereits als Identity-Provider konfiguriert (Tuwunel als OIDC-Client). Switch auf Tuwunel-als-Server wäre ein Migrationsschritt — eigene Entscheidung, nicht im Rahmen dieses RC-Tests.

### 2.4 MSC2454 — SSO UI-Interactive Authentication

Für E2EE-Key-Reset / Cross-Signing bei SSO-Usern. **Fix** für v1.5.1-Bug wo LDAP/SSO-User keinen Auth-Flow hatten.

**Status für uns:** Wenn ihr SSO/LDAP nutzt → wichtig. Für aktuellen Dev-Stack (Token-Registration) irrelevant.

---

## 3. Neue Features die wir IGNORIEREN können

| Feature | Grund |
|---|---|
| **MSC4143** — neuer Endpoint | Details unklar, keine Client-Auswirkung bekannt |
| **MSC4186** — Lazy-Loading Rule 2 | Sliding Sync Performance — greift automatisch |
| **MSC4277** — Remove report score | Spec-Cleanup, rückwärts-kompatibel |
| **MSC4376** — Remove `/v1/send_join/leave` | Federation-Cleanup, wir haben Federation aus |
| **Forbid duplicate reactions** | Bugfix, automatisch aktiv |
| **LDAP UIA password flow fix** | Wir nutzen kein LDAP |
| **JWT login flow fix** | Wir nutzen keinen JWT-Flow |
| **systemd socket activation** | Nur für systemd-Deployments, wir starten via WSL direkt |
| **Rust 1.94 Bump** | Interne Toolchain |
| **jemalloc profiling** | Debug-Feature |
| **RocksDB event listener callbacks** | Interne Instrumentierung |
| **Duplicate reaction check abstraction** | Refactor |

---

## 4. Bug Fixes die uns betreffen könnten

### 4.1 Media Delete Range Fix (⚠️ Breaking)

v1.5.1 hatte ein Bug im `!admin media delete-range`-Command — Bounds waren invertiert. In v1.6.0:
- Command wurde **umbenannt** (um versehentliche Verwendung zu verhindern)
- Bounds korrigiert
- Deprecated time-of-creation filter entfernt

**Impact für uns:** Keiner, wir haben das Kommando nie manuell benutzt. Aber: wenn ihr Skripte habt die `!admin media delete-range` callen → brechen.

### 4.2 Admin Module Load Wait (Fix #320)

In v1.5.1 konnte bei Startup ein Race zwischen Admin-Modul und HTTP-Listener auftreten → erstes Admin-Kommando schlug fehl. v1.6.0 wartet explizit.

**Impact:** Bei schnellem `!admin`-Aufruf direkt nach Startup stabiler.

### 4.3 Double-Deserialize Fix bei incoming PDU

Performance-Fix bei Federation-Traffic.

**Impact:** Irrelevant (Federation aus).

---

## 5. Empfohlener Test-Plan

### Phase 1 — RC Binary parallel einrichten
1. Download `tuwunel.rc.exe` → `tools/tuwunel-rc` (separates Binary neben bestehendem)
2. Neue Config `homeserver/tuwunel.rc.toml` (basierend auf `tuwunel.toml` + neue Optionen)
3. **Separate DB** (`./homeserver/data/db-rc`) — niemals gegen Dev-DB testen, v1.6.0-rc könnte Schema-Upgrades durchführen die rückwärts-inkompatibel sind
4. **Separate Media** (`./homeserver/data/media-rc`) + neuen S3-Prefix `tuwunel-rc/` auf SeaweedFS

### Phase 2 — Smoke Test ohne S3
- `tools/tuwunel-rc --config homeserver/tuwunel.rc.toml`
- Element X login → Raum erstellen → Text + Bild posten
- Prüfen: Log-Output, Admin-Panel, Media-Download funktioniert

### Phase 3 — S3 Provider aktivieren
- `store_media_on_providers = ["seaweedfs"]` setzen
- Neues Bild posten → über SeaweedFS-Admin (`http://localhost:8888`) prüfen ob es im Bucket `matrix-media` unter `tuwunel-rc/` liegt
- Download vom Client erneut testen

### Phase 4 — Async Upload (MSC2246)
- Mit Element X (neueste Version) großes Bild/Video posten
- Im Tuwunel-Log nach `media/v1/create` und `media/v3/upload/{id}` Requests suchen
- Prüfen: getrennter Upload-Step sichtbar

### Phase 5 — `max_request_size` erhöhen
- Wenn alle obigen Stufen funktionieren: `max_request_size = 524288000` (500 MB) **nur im RC-Config**
- **Haken:** Bringt nur was wenn wir den Cloudflare-Tunnel umgehen oder auf Business-Plan gehen. Im Dev mit lokalem Zugriff geht's.

### Phase 6 — Merge-Entscheidung
- Wenn v1.6.0 stable raus ist (vermutlich Ende April/Anfang Mai 2026):
- RC-Config wird zur Haupt-Config
- Stable-Binary ersetzt Alt-Binary
- Alte Media-Migration via `!admin media migrate media seaweedfs`

---

## 6. Risiken & Mitigationen

| Risiko | Mitigation |
|---|---|
| v1.6.0-rc crasht oder korrumpiert DB | Separate DB in `data/db-rc`, niemals Prod-DB anfassen |
| SeaweedFS S3-API verhält sich anders als AWS S3 | Storage-Provider `startup_check = true` lassen — Tuwunel prüft beim Start ob Bucket erreichbar |
| MSC2246 bricht Element X Sync | RC-Stack komplett eigenständig, Prod-Dev bleibt auf v1.5.1 |
| Neue Defaults ändern Verhalten | Explizit in RC-Config alle alten Werte setzen (auch wo sie default sind) |
| Migration-Kommandos haben Bugs | Erste Tests mit Dummy-Media im RC-Stack, Prod-Media nie anfassen |

---

## 7. Nächste Schritte (Reihenfolge)

1. ✅ `_ref/tuwunel-v1.6.0-rc/` — Referenz-Docs liegen vor
2. ⏳ `tuwunel-rc` Binary runterladen (Download aus GitHub Release Assets)
3. ⏳ `homeserver/tuwunel.rc.toml` schreiben
4. ⏳ `dev-stack2.ps1` um `-RC` Flag erweitern (optional, sonst manuell starten)
5. ⏳ Smoke-Test durchführen
6. ⏳ S3-Provider aktivieren und verifizieren
7. ⏳ Bei Erfolg: Entscheidung "stable warten" vs. "direkt produktiv nutzen"
