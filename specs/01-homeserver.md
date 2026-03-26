# Matrix Homeserver — Tuwunel + Dendrite Setup

## Homeserver-Übersicht

| | Synapse | Tuwunel | Dendrite |
|---|---|---|---|
| RAM idle | ~1 GB | **~50–150 MB** | ~200 MB |
| RAM 100 User | 2–4 GB | **~200–500 MB** | ~400 MB |
| Datenbank | PostgreSQL | **RocksDB** (eingebettet) | SQLite oder PostgreSQL |
| Binary | Nein (Python) | **Ja, Single Binary** | **Ja (Go, Windows-kompatibel)** |
| Windows Native | Nein | Nein (nur Linux) | **Ja (.exe kompilierbar)** |
| OIDC nativ | Nein | **Ja** | Teilweise |
| Entwicklung 2026 | stabil | **aktiv** | verlangsamt |

**Primär:** Tuwunel auf Linux (Production + WSL1 für lokale Dev)
**Fallback:** Dendrite als Windows-native .exe — kein WSL nötig, ideal wenn WSL Probleme macht

---

## Windows Dev — Zwei Optionen

### Option A: Tuwunel via WSL1 (kein Hyper-V nötig)

WSL2 hat VHD-Mount-Probleme auf älteren PCs → WSL1 als Fallback:

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

### Option B: Dendrite Windows Native (.exe)

Dendrite ist in Go geschrieben und läuft nativ unter Windows:

```powershell
# Einmalig builden (aus D:\matrix\tools\dendrite-src\):
go build -o ../dendrite.exe ./cmd/dendrite/

# Key generieren (einmalig):
cd D:\matrix\tools && go run genkey.go

# Starten:
D:\matrix\tools\dendrite.exe `
  --config D:\matrix\homeserver\dendrite.yaml `
  -really-enable-open-registration   # nur für lokales Dev!
```

**devstack.ps1 erkennt automatisch:** Wenn `tools/dendrite.exe` vorhanden → Dendrite,
sonst `tools/tuwunel` via WSL1.

---

## Tuwunel Config (homeserver/tuwunel.toml)

```toml
[global]
server_name = "matrix.local"
database_path = "./homeserver/data/db"   # relativ zum Start-Verzeichnis (D:\matrix\)
address = "127.0.0.1"
port = 8448
log = "warn,tuwunel=info"

[global.tls]
enabled = false

[global.registration]
enable_registration = true
registration_requires_token = true   # kein offenes Signup
allow_guest_access = false

[global.appservices]
registration_files = ["./homeserver/registration.yaml"]

[global.federation]
enabled = false   # lokal deaktiviert
```

---

## Dendrite Config (homeserver/dendrite.yaml)

```yaml
version: 2

global:
  server_name: "matrix.local"
  private_key: D:/matrix/homeserver/dendrite_key.pem   # absolute Pfade!
  disable_federation: true

  database:
    connection_string: "file:D:/matrix/homeserver/data/dendrite.db"

app_service_api:
  database:
    connection_string: "file:D:/matrix/homeserver/data/dendrite_appservice.db"
  config_files:
    - D:/matrix/homeserver/registration.yaml

client_api:
  registration_disabled: false
  registration_requires_token: true   # Token-basierte Registrierung
  guests_disabled: true
```

> **Wichtig:** Dendrite braucht absolute Pfade (Windows-Pfade mit Vorwärtsschrägstrichen).
> Relative Pfade werden vom cwd aufgelöst und können falsch sein.

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

Für lokales Dev: `-really-enable-open-registration` Flag beim Start.

> **Production TODO:** Eigenen Registration-Flow implementieren:
> - User-Registrierung via Go-Backend (existierendes Auth-System)
> - Go-Backend erstellt Matrix-Account per Admin-API mit zufälligem Passwort
> - User bekommt Matrix-Credentials nie direkt zu sehen → transparente Integration
> - `registration_disabled: true` in Production-Config setzen
> - Kein `-really-enable-open-registration` in Production!

---

## Appservice Registration (homeserver/registration.yaml)

Wird vom **Go Appservice** generiert (einmalig):

```powershell
cd go-appservice && go run ./cmd/appservice/... --generate-registration
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
rate_limited: false
```

---

## User-Registrierung (einmalig nach Homeserver-Start)

```powershell
# Automatisch — erstellt Alice + Bot, befüllt alle .env Dateien:
.\scripts\setup-users.ps1

# Manuell (curl):
curl -X POST http://localhost:8448/_matrix/client/v3/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"Alice1234!","auth":{"type":"m.login.registration_token","token":"TOKEN"}}'
```

---

## Port-Übersicht

| Service | Port | Protokoll |
|---|---|---|
| Tuwunel / Dendrite | 8448 | HTTP (Matrix CS API) |
| Go Appservice | 8090 | HTTP (Matrix AS API) |
| Python Agent Bridge | 8097 | HTTP (FastAPI) |
| NATS | 4222 | TCP |
| Next.js | 3000 | HTTP |

---

## Production-Entscheidung

- **Production:** Tuwunel läuft als weiterer Prozess auf dem **bestehenden Server** (kein extra VPS nötig) — single binary, RocksDB eingebettet, ~50-150 MB RAM
- **Windows-Entwicklung:** Dendrite als .exe — kein WSL, kein Docker
- **Gemeinsame Konfiguration:** Appservice-Registration und Tokens identisch für beide — Homeserver ist austauschbar weil das Appservice-API Matrix-standardisiert ist
- **Kein federation-Zwang:** Tuwunel läuft auch ohne öffentliche Domain (nur interne User)
