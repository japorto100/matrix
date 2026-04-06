# Matrix Homeserver — Tuwunel + Zendrite Setup

**Status:** Aktiv
**Stand:** 06.04.2026 — Tuwunel v1.5.1 in Produktion, Zendrite als Windows-Fallback

## Homeserver-Übersicht

| | Synapse | Tuwunel | Zendrite | ~~Dendrite~~ |
|---|---|---|---|---|
| RAM idle | ~1 GB | **~50–150 MB** | ~150–200 MB | ~200 MB |
| RAM 100 User | 2–4 GB | **~200–500 MB** | ~300–400 MB | ~400 MB |
| Datenbank | PostgreSQL | **RocksDB** (eingebettet) | SQLite oder PostgreSQL | SQLite oder PostgreSQL |
| Binary | Nein (Python) | **Ja, Single Binary** | **Ja (Go, Windows-kompatibel)** | **Ja (Go)** |
| Windows Native | Nein | Nein (nur Linux) | **Ja (.exe kompilierbar)** | Ja |
| OIDC nativ | Nein | **Ja (main branch)** | Noch nicht | Teilweise |
| Sliding Sync | Ja (nativ ab 1.114) | **Ja (nativ, simplified MSC3575)** | **Ja (nativ, MSC4186)** | Nein |
| MAS | **Ja (vollstaendig)** | In Arbeit | Nein | Nein |
| Entwicklung 2026 | stabil | **aktiv** | **aktiv (Community-Fork)** | ❌ Maintenance-only |

**Aktuell verwendet:**
- **Primaer:** Tuwunel v1.5.1 auf Linux (Docker / podman-compose) und WSL1 fuer lokale Dev
- **Fallback:** Zendrite/Dendrite als Windows-native .exe — kein WSL noetig

> **Dendrite → Zendrite Migration (28.03.2026):**
> Dendrite wird von Element nur noch mit Security-Fixes maintained. Die Matrix Foundation
> hat keine Ressourcen dafuer. Community-Fork **Zendrite** uebernimmt aktive Entwicklung:
> native Sliding Sync, bessere Performance, weniger RAM, nahtlose Migration von Dendrite.
> Repo: CodeFloe (EU, Forgejo-basiert). Migration ist seamless — Config bleibt kompatibel.

---

## Windows Dev — Zwei Optionen

### Option A: Tuwunel via WSL1 (kein Hyper-V noetig)

WSL2 hat VHD-Mount-Probleme auf aelteren PCs → WSL1 als Fallback:

```powershell
# Als Admin (einmalig):
wsl --set-default-version 1
wsl --unregister Ubuntu    # alte/kaputte Distro entfernen
wsl --install -d Ubuntu    # neu als WSL1 installieren

# Tuwunel starten (aus D:\matrix\):
wsl ./tools/tuwunel --config ./homeserver/tuwunel.toml
```

> **Hinweis WSL OOBE-Fehler:** Bei alten PCs kann `LxInitOobeResult / Broken pipe` auftreten.
> Wenn Ubuntu nicht installierbar ist → Option B nutzen.

### Option B: Zendrite Windows Native (.exe)

Zendrite (Community-Fork von Dendrite, Go) laeuft nativ unter Windows:

```powershell
# Einmalig builden (aus D:\matrix\tools\zendrite-src\):
go build -o ../zendrite.exe ./cmd/zendrite/

# Key generieren (einmalig):
cd D:\matrix\tools && go run genkey.go

# Starten:
D:\matrix\tools\zendrite.exe `
  --config D:\matrix\homeserver\dendrite.yaml `
  -really-enable-open-registration   # nur fuer lokales Dev!
```

> **Migration von Dendrite:** Config-Format ist identisch. `dendrite.yaml` funktioniert
> unveraendert mit Zendrite. Einfach Binary austauschen.

**devstack.ps1 erkennt automatisch:** Wenn `tools/zendrite.exe` (oder `dendrite.exe`)
vorhanden → Zendrite/Dendrite, sonst `tools/tuwunel` via WSL1.

### Option C: Tuwunel via podman-compose (empfohlen fuer Dev mit Sandbox)

```bash
# Tuwunel + NATS + Go Appservice + Python Backend + Next.js Chat
podman-compose up

# + LLM Mock fuer Tests ohne API Keys
podman-compose --profile dev up

# + OpenSandbox Server (exec-12)
podman-compose --profile sandbox up
```

Siehe `docker-compose.yml` im Root fuer alle Profile.

---

## Tuwunel Config (homeserver/tuwunel.toml)

Aktive Dev-Config (Auszug — komplette Datei in `homeserver/tuwunel.toml`):

```toml
[global]
server_name = "matrix.local"
database_path = "./homeserver/data/db"   # RocksDB, relativ zum Start-Verzeichnis
address = "0.0.0.0"                       # LAN access (dev)
port = 8448
log = "warn"                              # Minimal aktivitaetslogging

default_room_version = "12"               # Project Hydra
allow_registration = true
registration_token = "matrix-dev-token-2026"
allow_guest_registration = false
auto_join_rooms = ["#general:matrix.local"]

# Federation (default OFF — siehe 09-privacy.md)
allow_federation = false
federate_created_rooms = false

# E2EE: Client entscheidet pro Raum
encryption_enabled_by_default_for_room_type = "off"

# Privacy hardened (B-5 / B-6, siehe 09-privacy.md + 16-security.md)
allow_local_presence = true
allow_incoming_presence = false
allow_outgoing_presence = false
url_preview_domain_contains_allowlist = []   # SSRF-Schutz, kein URL Preview
allow_legacy_media = true                     # Dev mode, fallback fuer alte Clients

# Media
max_request_size = 524288000                  # 500 MB
rocksdb_direct_io = false                     # WSL2 + NTFS safe

# Backup
database_backup_path = "./homeserver/data/db-backups"
database_backups_to_keep = 3

# MatrixRTC + LiveKit (Voice/Video Calls — siehe 04-nextjs-chat.md)
[[global.well_known.rtc_transports]]
type = "livekit"
livekit_service_url = "http://192.168.1.34:8080"

# STUN/TURN
turn_uris = [
    "stun:stun.cloudflare.com:3478",
    "turn:a.relay.metered.ca:443?transport=tcp",
]

# Appservice (Go Appservice)
[global.appservice.trading-agent]
url = "http://127.0.0.1:8090"
as_token = "<generated>"
hs_token = "<generated>"
sender_localpart = "appservice-bot"
[[global.appservice.trading-agent.namespaces.users]]
exclusive = true
regex = "@agent-.*:matrix\\.local"
```

**Config-Varianten in `homeserver/`:**
- `tuwunel.toml` — Aktive Dev-Config
- `tuwunel.example.toml` — Voll dokumentiertes Template
- `tuwunel.image.toml` — Docker Image Config
- `tuwunel.prod.toml` — Production hardened Vorlage

---

## Dendrite/Zendrite Config (homeserver/dendrite.yaml)

```yaml
version: 2

global:
  server_name: "matrix.local"
  private_key: D:/matrix/homeserver/dendrite_key.pem   # absolute Pfade!
  disable_federation: true
  log_level: warn

  database:
    connection_string: "file:D:/matrix/homeserver/data/dendrite.db?..."
    max_open_conns: 10
  cache:
    max_size_estimated: 512mb

  presence:
    enable_inbound: false
    enable_outbound: false

  metrics:
    enabled: false
  report_stats:
    enabled: false

app_service_api:
  database:
    connection_string: "file:D:/matrix/homeserver/data/dendrite_appservice.db"
  config_files:
    - D:/matrix/homeserver/registration.yaml

client_api:
  registration_disabled: false
  registration_requires_token: true
  guests_disabled: true
```

> **Wichtig:** Dendrite braucht absolute Pfade (Windows-Pfade mit Vorwaertsschraegstrichen).
> Relative Pfade werden vom cwd aufgeloest und koennen falsch sein.

**Bekannte Dendrite v0.13 Limitierungen:**
- Read Receipts koennen nicht deaktiviert werden (#3284)
- Keine Message Retention Policy (#3330)
- Empfehlung: Tuwunel fuer Production

### Dendrite Key generieren

```powershell
# Einmalig (tools/genkey.go liegt im Repo):
cd D:\matrix\tools && go run genkey.go
# → erstellt homeserver/dendrite_key.pem (MATRIX PRIVATE KEY Format)
```

### Dendrite Registration Warning

```
You have tried to enable open registration without secondary verification...
```

Fuer lokales Dev: `-really-enable-open-registration` Flag beim Start.

> **Production TODO:** Eigenen Registration-Flow implementieren
> (siehe `10-portierung.md`):
> - User-Registrierung via Go-Backend (existierendes Auth-System)
> - Go-Backend erstellt Matrix-Account per Admin-API mit zufaelligem Passwort
> - User bekommt Matrix-Credentials nie direkt zu sehen → transparente Integration
> - `registration_disabled: true` in Production-Config setzen

---

## Appservice Registration (homeserver/registration.yaml)

Wird vom **Go Appservice** generiert (einmalig):

```powershell
cd go-appservice && go run -tags goolm ./cmd/appservice/... --generate-registration
# → schreibt homeserver/registration.yaml mit generierten Tokens
```

Format:
```yaml
id: trading-agent-appservice
url: http://127.0.0.1:8090       # Go Appservice Port
as_token: <generiert>
hs_token: <generiert>
sender_localpart: appservice-bot
namespaces:
  users:
    - exclusive: true
      regex: '@agent-.*:matrix\.local'
  rooms: []
  aliases: []
rate_limited: false
```

Token-Generierung (PowerShell):
```powershell
[System.Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
```

---

## User-Registrierung (einmalig nach Homeserver-Start)

```powershell
# Automatisch — erstellt Alice + Bot, befuellt alle .env Dateien:
.\scripts\setup-users.ps1

# Manuell (curl):
curl -X POST http://localhost:8448/_matrix/client/v3/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"Alice1234!","auth":{"type":"m.login.registration_token","token":"TOKEN"}}'
```

---

## Port-Übersicht

Vollstaendige Port-Liste in `00-overview.md`. Hier nur Homeserver-relevant:

| Service | Port | Protokoll |
|---|---|---|
| Tuwunel / Zendrite / Dendrite | 8448 | HTTP (Matrix CS API) |
| Go Appservice | 8090 | HTTP (Matrix AS API) |
| Python Agent (FastAPI) | 8094 | HTTP (Chat / Tools / Audio) |
| Python Bridge (NATS Consumer) | 8097 | HTTP (Health) |
| NATS | 4222 | TCP (Message Bus) |
| Next.js | 3000 | HTTP |
| LiveKit | 7880 / 8080 | WS / HTTP |

---

## Production-Entscheidung

- **Production:** Tuwunel laeuft als weiterer Prozess auf dem **bestehenden Server**
  (kein extra VPS noetig) — single binary, RocksDB eingebettet, ~50-150 MB RAM
- **Windows-Entwicklung:** Zendrite als .exe — kein WSL, kein Docker
  (Dendrite-Config kompatibel)
- **Gemeinsame Konfiguration:** Appservice-Registration und Tokens identisch fuer
  beide — Homeserver ist austauschbar weil das Appservice-API Matrix-standardisiert ist
- **Kein federation-Zwang:** Tuwunel laeuft auch ohne oeffentliche Domain
  (nur interne User)
