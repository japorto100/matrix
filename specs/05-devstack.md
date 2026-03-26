# Dev Stack — Lokales Setup ohne Docker

## Übersicht

Da Docker nicht verfügbar ist, läuft der gesamte Stack über PowerShell-Jobs.
`scripts/devstack.ps1` erkennt automatisch welcher Homeserver verfügbar ist.

---

## Voraussetzungen

```powershell
go version           # Go 1.26+
uv --version         # uv (Python Package Manager)
bun --version        # Bun (Next.js Runtime)
# NATS: tools/nats-server.exe (kein PATH-Eintrag nötig)
```

### Tools-Binaries in tools/

Alle Binaries liegen in `D:\matrix\tools\` (nicht im PATH nötig):

| Binary | Zweck | Größe |
|---|---|---|
| `tuwunel` | Linux Homeserver v1.5.1 (via WSL1) | 87 MB |
| `dendrite.exe` | Windows Homeserver v0.13.8 (Fallback) | 77 MB |
| `nats-server.exe` | NATS Message Bus | 16 MB |
| `ngrok.exe` | Tunnel mit Account | 31 MB |
| `cloudflared.exe` | Cloudflare Tunnel (kein Account) | 63 MB |
| `bore.exe` | Open-Source Tunnel (kein Account) | 2 MB |
| `genkey.go` | Dendrite ED25519 Key Generator | - |

**Download:**
```powershell
# nats-server.exe
Invoke-WebRequest 'https://github.com/nats-io/nats-server/releases/download/v2.10.27/nats-server-v2.10.27-windows-amd64.zip' -OutFile tools/nats-server.zip -UseBasicParsing
Expand-Archive tools/nats-server.zip -DestinationPath tools/nats-tmp -Force
Move-Item tools/nats-tmp/nats-server-v2.10.27-windows-amd64/nats-server.exe tools/nats-server.exe
Remove-Item -Recurse tools/nats-tmp, tools/nats-server.zip

# cloudflared.exe (kein Account)
Invoke-WebRequest 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile tools/cloudflared.exe -UseBasicParsing

# bore.exe (kein Account)
Invoke-WebRequest 'https://github.com/ekzhang/bore/releases/download/v0.6.0/bore-v0.6.0-x86_64-pc-windows-msvc.zip' -OutFile tools/bore.zip -UseBasicParsing
Expand-Archive tools/bore.zip -DestinationPath tools/bore-tmp -Force
Move-Item tools/bore-tmp/bore.exe tools/bore.exe
Remove-Item -Recurse tools/bore-tmp, tools/bore.zip

# ngrok.exe (Account nötig: ngrok.com)
Invoke-WebRequest 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile tools/ngrok.zip -UseBasicParsing
Expand-Archive tools/ngrok.zip -DestinationPath tools/ -Force
Remove-Item tools/ngrok.zip
```

### Homeserver-Binary

`devstack.ps1` prüft in dieser Reihenfolge:
1. `tools/tuwunel` → Tuwunel (Linux binary, via WSL1) — **bevorzugt**
2. `tools/dendrite.exe` → Dendrite (Windows native, Fallback)

**Dendrite builden** (einmalig, Go muss installiert sein):
```powershell
cd D:\matrix\tools\dendrite-src
go build -o ../dendrite.exe ./cmd/dendrite/

# Key generieren:
cd D:\matrix\tools && go run genkey.go
```

**Tuwunel herunterladen** (einmalig, WSL1 muss laufen):
```powershell
curl -L "https://github.com/matrix-construct/tuwunel/releases/download/v1.5.1/v1.5.1-release-all-x86_64-v2-linux-gnu-tuwunel.zst" -o tools/tuwunel.zst
zstd -d tools/tuwunel.zst -o tools/tuwunel
rm tools/tuwunel.zst
```

---

## Erster Start (Reihenfolge)

```powershell
# 1. Go Appservice — registration.yaml generieren (einmalig)
cd go-appservice && go run ./cmd/appservice/... --generate-registration

# 2. Homeserver starten (im Hintergrund halten)
# Entweder via devstack.ps1 oder manuell:
D:\matrix\tools\dendrite.exe --config D:\matrix\homeserver\dendrite.yaml -really-enable-open-registration

# 3. Testuser + Bot registrieren (einmalig, Homeserver muss laufen)
.\scripts\setup-users.ps1
# → erstellt @alice:matrix.local + @trading-agent:matrix.local
# → schreibt Access-Tokens direkt in nextjs-chat/.env.local und python-agent-bridge/.env

# 4. Stack vollständig starten
.\scripts\devstack.ps1
```

---

## scripts/devstack.ps1

### Flags

| Flag | Beschreibung |
|---|---|
| `-NoHomeserver` | Homeserver nicht starten (läuft extern) |
| `-NoNATS` | NATS nicht starten |
| `-SkipGoAppservice` | Go Appservice nicht starten |
| `-AgentOnly` | Nur Python Agent Bridge |
| `-FrontendOnly` | Nur Next.js |

### Beispiele

```powershell
.\scripts\devstack.ps1                    # Alles starten
.\scripts\devstack.ps1 -NoHomeserver      # Homeserver läuft bereits
.\scripts\devstack.ps1 -FrontendOnly      # Nur UI entwickeln
.\scripts\devstack.ps1 -AgentOnly         # Nur Bot testen
```

### Service-Erkennung

```
tools/dendrite.exe vorhanden?
  → Ja: Dendrite mit -really-enable-open-registration starten
  → Nein: tools/tuwunel via WSL1 starten (wsl bash -c "cd ... && ./tools/tuwunel ...")
  → Beides fehlt: Warnung ausgeben
```

---

## scripts/setup-users.ps1

Einmalig nach erstem Homeserver-Start ausführen:

```powershell
.\scripts\setup-users.ps1
```

**Was es macht:**
1. Admin-Login (fragt nach Credentials)
2. Registration-Token erstellen
3. `@alice:matrix.local` registrieren + einloggen
4. `@trading-agent:matrix.local` registrieren + einloggen
5. Test-Raum `#general:matrix.local` erstellen
6. Access-Tokens automatisch in .env Dateien schreiben:
   - `nextjs-chat/.env.local` → MATRIX_ACCESS_TOKEN, MATRIX_DEVICE_ID
   - `python-agent-bridge/.env` → MATRIX_BOT_ACCESS_TOKEN, MATRIX_BOT_PASSWORD

---

## Port-Map

| Service | Port | Binary/Framework |
|---|---|---|
| Homeserver | 8448 | Dendrite.exe oder Tuwunel (WSL1) |
| Go Appservice | 8090 | go run ./cmd/appservice/... |
| Python Agent Bridge | 8097 | uv run uvicorn agent_bridge.app:app |
| NATS | 4222 | nats-server |
| Next.js | 3000 | bun run dev |

---

## .env Übersicht

| Datei | Wann befüllen |
|---|---|
| `go-appservice/.env` | Bereits befüllt (Tokens auto-generiert) |
| `python-agent-bridge/.env` | Nach `setup-users.ps1` (Bot-Token) |
| `nextjs-chat/.env.local` | Nach `setup-users.ps1` (Alice-Token) |

---

## Verifizierung

```powershell
# Homeserver erreichbar?
curl http://localhost:8448/_matrix/client/versions

# Go Appservice?
curl http://localhost:8090/health

# Python Bridge?
curl http://localhost:8097/health

# Next.js?
curl http://localhost:3000/matrix
```

---

## Bekannte Probleme

| Problem | Lösung |
|---|---|
| WSL2 VHD-Mount-Fehler (`ERROR_PATH_NOT_FOUND`) | WSL1 nutzen: `wsl --set-default-version 1` |
| WSL OOBE Fehler (`LxInitOobeResult / Broken pipe`) | Ubuntu deinstallieren + neu installieren, oder Dendrite als Fallback |
| Dendrite: "open registration" Warning | `-really-enable-open-registration` Flag (nur Dev!) |
| Dendrite: `keyBlock is nil` | `go run tools/genkey.go` ausführen (MATRIX PRIVATE KEY Format) |
| NATS nicht im PATH | Manuell herunterladen: https://nats.io/download/ |
| Go Appservice: `missing go.sum` | `cd go-appservice && go mod tidy` |
