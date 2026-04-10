# Dev Stack — Lokales Setup (Native + podman-compose)

**Status:** Aktiv
**Stand:** 10.04.2026 — dev-stack2.ps1, LiteLLM Gateway (exec-16), control-ui, Ingestion Worker

## Zwei Setup-Varianten

| Variante | Fuer wen | Vorteil |
|:---|:---|:---|
| **A) Native PowerShell-Jobs** | Windows-Dev ohne Container | Schnell, kein Docker noetig, Hot-Reload |
| **B) podman-compose / docker-compose** | Linux-Dev oder Sandbox-Tests | Reproduzierbar, OpenSandbox einfacher zu starten |

Beide nutzen dieselben ENV-Dateien.

---

## Voraussetzungen

```powershell
go version           # Go 1.26+
uv --version         # uv (Python Package Manager)
bun --version        # Bun (Next.js Runtime, alternativ pnpm/npm)
# NATS: tools/nats-server.exe (kein PATH-Eintrag noetig)
# Optional: podman/docker fuer Variante B
```

---

## Tools-Binaries in `tools/`

Alle Binaries liegen in `D:\matrix\tools\` (gitignored, nicht im PATH noetig):

| Binary | Zweck | Groesse |
|---|---|---|
| `tuwunel` | Linux Homeserver v1.5.1 (via WSL1 / Docker) | ~87 MB |
| `dendrite.exe` / `zendrite.exe` | Windows Homeserver Fallback | ~77 MB |
| `nats-server.exe` | NATS Message Bus v2.10.27 | ~16 MB |
| `ngrok.exe` | Tunnel mit Account | ~31 MB |
| `cloudflared.exe` | Cloudflare Tunnel (kein Account) | ~63 MB |
| `bore.exe` | Open-Source Tunnel (kein Account) | ~2 MB |
| `genkey.go` | Dendrite ED25519 Key Generator | - |

**Download-Befehle siehe `08-tooling.md`.**

---

## Variante A: Native PowerShell-Jobs

### Service-Liste

| Service | Port | Start |
|---|---|---|
| Homeserver | 8448 | Tuwunel via WSL1 oder Zendrite Native |
| Go Appservice | 8090 | `go run -tags goolm ./cmd/appservice/...` |
| Python Agent Service | 8094 | `uv run uvicorn agent.app:app --port 8094` |
| Python Bridge | 8097 | `uv run uvicorn bridge.app:app --port 8097` |
| LiteLLM Gateway | 4000 | `cd litellm-gateway && uv run litellm --config config.yaml --port 4000` |
| Voice Worker | — | `uv run python -m voice.worker` (optional) |
| Mock Agent | 8094 | `uv run python -m mock.mock_agent` (statt agent) |
| NATS | 4222 | `tools/nats-server.exe` |
| Next.js | 3000 | `cd nextjs-chat && bun run dev` |
| control-ui | 3001 | `cd control-ui && bun run dev` |
| LiveKit | 7880/8080 | externer LiveKit Server (siehe `13-e2ee-agent-architecture.md`) |
| Ingestion Worker | 8098 | `cd ingestion && uv run uvicorn ingestion.worker:app --port 8098` |
| Memory Service | 8093 | `uv run uvicorn memory.app:app --port 8093` (optional) |
| MCP Server (standalone) | 8095 | `uv run python -m agent.mcp_server` (mounted in Agent default) |

### Erster Start (Reihenfolge)

```powershell
# 1. Go Appservice — registration.yaml generieren (einmalig)
cd go-appservice
go run -tags goolm ./cmd/appservice/... --generate-registration

# 2. Homeserver starten (im Hintergrund halten)
# Tuwunel via WSL1:
wsl ./tools/tuwunel --config ./homeserver/tuwunel.toml
# ODER Dendrite native:
D:\matrix\tools\dendrite.exe --config D:\matrix\homeserver\dendrite.yaml -really-enable-open-registration

# 3. Testuser + Bot registrieren (einmalig, Homeserver muss laufen)
.\scripts\setup-users.ps1
# → erstellt @alice:matrix.local + @agent-trading:matrix.local
# → schreibt Access-Tokens in nextjs-chat/.env.local und python-backend/.env

# 4. Python Backend Migrations (einmalig)
cd python-backend
uv run alembic upgrade head

# 5. Stack vollstaendig starten
.\scripts\dev-stack2.ps1
```

### scripts/dev-stack2.ps1

**Flags** (existierende — bitte mit Skript-Stand abgleichen):

| Flag | Beschreibung |
|---|---|
| `-SkipHomeserver` | Homeserver nicht starten (laeuft extern) |
| `-SkipNats` | NATS nicht starten |
| `-SkipGoAppservice` | Go Appservice nicht starten |
| `-SkipLiteLLM` | LiteLLM Gateway nicht starten (direkter Provider-Zugriff) |
| `-SkipControlUi` | control-ui nicht starten |
| `-SkipIngestion` | Ingestion Worker nicht starten |
| `-AgentOnly` | Nur Python Agent + Bridge |
| `-FrontendOnly` | Nur Next.js + control-ui |
| `-UseMock` | Mock Agent statt echtes LLM (kein API Key noetig) |
| `-WithVoice` | Voice Worker starten (LiveKit) |
| `-DevTools` | AI SDK DevTools starten |

**Beispiele:**

```powershell
.\scripts\dev-stack2.ps1                    # Alles starten
.\scripts\dev-stack2.ps1 -NoHomeserver      # Homeserver laeuft bereits
.\scripts\dev-stack2.ps1 -FrontendOnly      # Nur UI entwickeln
.\scripts\dev-stack2.ps1 -MockAgent         # CI / Tests ohne API Keys
```

**Service-Erkennung:**

```
tools/dendrite.exe vorhanden?
  → Ja: Dendrite mit -really-enable-open-registration starten
  → Nein: tools/tuwunel via WSL1 starten
  → Beides fehlt: Warnung ausgeben
```

---

## Variante B: podman-compose / docker-compose

`docker-compose.yml` im Repo-Root definiert alle Services in **Profilen**:

| Profile | Services |
|---|---|
| **default** | tuwunel, nats, go-appservice, python-bridge, nextjs-chat |
| **dev** | + llm-mock (Mock Agent statt echtes LLM) |
| **sandbox** | + opensandbox-server (exec-12 Code Execution) |
| **prod** | + coturn (TURN Relay) |

**Beispiele:**

```bash
# Default Stack (Tuwunel + Bridge + Frontend, kein Sandbox)
podman-compose up

# + Mock Agent (kein API Key noetig)
podman-compose --profile dev up

# + OpenSandbox Server (Code Execution Tests)
podman-compose --profile sandbox up

# + Coturn TURN Relay (Production-aehnlich)
podman-compose --profile prod up
```

**OpenSandbox Setup auf Windows:** Siehe Hinweis im docker-compose.yml Header
und in `specs/execution/exec-12-sandbox-security.md`. Podman braucht
`/run/podman/podman.sock` statt `/var/run/docker.sock`.

---

## scripts/setup-users.ps1

Einmalig nach erstem Homeserver-Start ausfuehren:

```powershell
.\scripts\setup-users.ps1
```

**Was es macht:**
1. Admin-Login (fragt nach Credentials)
2. Registration-Token erstellen
3. `@alice:matrix.local` registrieren + einloggen
4. `@agent-trading:matrix.local` registrieren + einloggen
5. Test-Raum `#general:matrix.local` erstellen
6. Access-Tokens automatisch in .env Dateien schreiben:
   - `nextjs-chat/.env.local` → `MATRIX_ACCESS_TOKEN`, `MATRIX_DEVICE_ID`
   - `python-backend/.env` → `MATRIX_BOT_ACCESS_TOKEN`, `MATRIX_BOT_PASSWORD`

---

## scripts/harden-env.py (exec-12 Phase 2.7)

Ersetzt Default-Credentials in den `.env`-Dateien durch zufaellige Tokens:

```bash
# Dry-Run (zeigt Aenderungen ohne zu schreiben)
uv run python scripts/harden-env.py --dry-run

# Aktiv (Backup nach .env.bak, dann ersetzen)
uv run python scripts/harden-env.py
```

Idempotent — nur bekannte Defaults (`devkey`, `changeme` etc.) werden ersetzt.
Betrifft: `LIVEKIT_API_KEY/SECRET`, `MATRIX_BOT_PASSWORD`, etc.

---

## .env Uebersicht

| Datei | Wann befuellen |
|---|---|
| `go-appservice/.env.development` | Vor erstem Start (Tokens generieren) |
| `python-backend/.env` | Nach `setup-users.ps1` (Bot-Tokens) + manuell (LLM API Keys) |
| `nextjs-chat/.env.local` | Nach `setup-users.ps1` (Alice-Token) |

Vollstaendige Schema-Referenz in `00-overview.md` und `agent-ui/05-backend-abhaengigkeiten.md`.

---

## Verifizierung

```powershell
# Homeserver erreichbar?
curl http://localhost:8448/_matrix/client/versions

# Go Appservice?
curl http://localhost:8090/health

# Python Agent Service?
curl http://localhost:8094/health

# Python Bridge?
curl http://localhost:8097/health

# LiteLLM Gateway (exec-16)?
curl http://localhost:4000/health

# Memory Service (optional)?
curl http://localhost:8093/health

# Next.js?
curl http://localhost:3000/matrix
```

---

## Bekannte Probleme

| Problem | Loesung |
|---|---|
| WSL2 VHD-Mount-Fehler (`ERROR_PATH_NOT_FOUND`) | WSL1 nutzen: `wsl --set-default-version 1` |
| WSL OOBE Fehler (`LxInitOobeResult / Broken pipe`) | Ubuntu deinstallieren + neu installieren, oder Dendrite als Fallback |
| Dendrite: "open registration" Warning | `-really-enable-open-registration` Flag (nur Dev!) |
| Dendrite: `keyBlock is nil` | `go run tools/genkey.go` ausfuehren (MATRIX PRIVATE KEY Format) |
| NATS nicht im PATH | Manuell herunterladen: https://nats.io/download/ |
| Go Appservice: `missing go.sum` | `cd go-appservice && go mod tidy` |
| Go Appservice: `cgo errors` | Build mit `-tags goolm` (kein libolm-Build) |
| Turbopack: `Assertion failed: !(handle->flags & UV_HANDLE_CLOSING)` | Webpack-Build ohne Turbopack-Config nutzen |
| Podman Sandbox: `/var/run/docker.sock not found` | Symlink `sudo ln -sf /run/user/$(id -u)/podman/podman.sock /var/run/docker.sock` |
| Python: `No module named 'opensandbox'` | `cd python-backend && uv sync` |
| Alembic: `Target database is not up to date` | `cd python-backend && uv run alembic upgrade head` |
