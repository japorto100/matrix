# Portierung ins Hauptprojekt (tradeview-fusion)

**Status:** Aktiv (Phase A — Test laeuft)
**Stand:** 06.04.2026 — python-backend konsolidiert, NATS Bridge abgeschlossen

> **Hinweis:** Diese Spec wurde im isolierten Matrix-Testprojekt erstellt, mit Bezug
> auf die tradeview-fusion Fullstack-App. Die Vorschlaege sollten bei der tatsaechlichen
> Portierung kritisch hinterfragt werden — Architektur, Infrastruktur und Anforderungen
> des Hauptprojekts koennen von den Annahmen hier abweichen.

## Ziel

Das Matrix-Isolationsprojekt (`D:\matrix`) wird nach erfolgreichem Test in das
Hauptprojekt (`D:\tradingview-clones\tradeview-fusion`) portiert.

---

## Architektur-Unterschiede: Matrix-Projekt vs. Hauptprojekt

### Go → Python Kommunikation

| | Matrix-Projekt | Hauptprojekt |
|---|---|---|
| Mechanismus | NATS Pub/Sub fuer Matrix-Events + HTTP fuer SSE | gRPC-IPC (HTTP Fallback) |
| Warum | Event-driven, async, entkoppelt | Request-Response mit SSE Streaming |
| Go→Python (NATS) | Publish auf `matrix.message.inbound` | nicht genutzt |
| Go→Python (HTTP SSE) | `/api/v1/agent/chat` direkt | `ipc/client.go` ForwardRequest() |
| Python→Go (NATS) | Publish auf `matrix.message.reply` | nicht genutzt |
| gRPC Port | nicht genutzt | HTTP_Port + 1000 (z.B. 8094→9094) |

**Beim Portieren:**
- Go Appservice nutzt statt NATS den bestehenden `ipc/client.go`
- `python-backend/bridge/` (NATS Consumer) wird NICHT portiert — Go ruft den bestehenden
  `python-agent` Service direkt
- NATS bleibt fuer Marktdaten (market.*.tick etc.) — nicht fuer Matrix-Events

### Port-Mapping

| Service | Matrix-Projekt | Hauptprojekt |
|---|---|---|
| Go Gateway | 8090 (Appservice) | 9060 |
| Python Agent | 8094 (HTTP/SSE) | 8094 (HTTP) / 9094 (gRPC) |
| Python Bridge (NATS) | 8097 | entfaellt |
| NATS | 4222 | 4222 (gleich) |
| Homeserver | 8448 | 8448 (gleich) |

---

## Was direkt uebernommen wird

| Komponente | Wo | Aenderungen |
|---|---|---|
| `homeserver/tuwunel.toml` | Homeserver-Config | Production-Anpassungen (TLS, server_name, OIDC) |
| `go-appservice/internal/crypto/` | E2EE Stack (OlmMachine, Cross-Signing) | direkt uebernehmen |
| `go-appservice/internal/handler/` | Matrix Event-Handling, Auto-Join, Mention-Filter | direkt uebernehmen |
| `go-appservice/internal/intent/` | AgentSender API (virtuelle @agent-* User) | direkt uebernehmen |
| `go-appservice/internal/handlers/http/` | HTTP Proxy zu Agent Service | IPC-Client statt HTTP-Direct |
| Namespace-Regex | `registration.yaml` | Anpassen auf prod server_name |
| `nextjs-chat/src/components/matrix/` | 45+ Matrix-Komponenten | 1:1 ins Hauptprojekt |
| `nextjs-chat/src/lib/matrix/hooks/` | 18 Custom Hooks | 1:1 ins Hauptprojekt |
| `agent-chat/` Feature-Modul | AssistantUI + Tambo + tldraw + Novel | 1:1 als Submodul |

---

## Was NICHT portiert wird

| Was | Warum |
|---|---|
| `python-backend/bridge/` (NATS Consumer) | Hauptprojekt hat IPC-Client direkt zwischen Go ↔ python-agent |
| `python-backend/mock/` | Nur fuer Tests im Isolations-Setup |
| `scripts/setup-users.ps1` | Hauptprojekt hat eigene User-Verwaltung (DB + Auth) |
| Dendrite/Zendrite | Nur Windows-Dev-Fallback, nicht fuer Production |
| `tools/dendrite.exe` / `tools/zendrite.exe` | Hauptprojekt nutzt Tuwunel direkt |

---

## Portierungs-Schritte

### Schritt 1 — Go Appservice integrieren

```
tradeview-fusion/
└── go-backend/
    └── internal/
        └── matrix/                    ← NEU
            ├── appservice.go          ← aus go-appservice/cmd/appservice/main.go
            ├── handler/server.go      ← aus go-appservice/internal/handler/
            ├── crypto/                ← aus go-appservice/internal/crypto/
            ├── intent/                ← aus go-appservice/internal/intent/
            ├── handlers/http/         ← aus go-appservice/internal/handlers/http/
            │                            (HTTP→IPC anpassen)
            └── matrix_bridge.go       ← NATS ersetzen durch ipc/client.go Call
```

`matrix_bridge.go` — Anpassung:
```go
// Matrix-Projekt: via NATS
natsPub.Publish("matrix.message.inbound", payload)

// Hauptprojekt: via IPC direkt
reply, err := agentServiceClient.Chat(ctx, matrixMessage)
```

### Schritt 2 — Next.js Komponenten integrieren

```
tradeview-fusion/
└── src/
    ├── components/
    │   └── matrix/               ← aus nextjs-chat/src/components/matrix/
    └── lib/
        └── matrix/               ← aus nextjs-chat/src/lib/matrix/
```

Credentials-Source ändern:
```typescript
// Matrix-Projekt: aus .env.local
// Hauptprojekt: aus Session (NextAuth) + Go Backend API
const creds = await fetch("/api/matrix/credentials");  // Go liefert Token
```

Media Proxy:
- `nextjs-chat/src/app/api/matrix/media/route.ts` — 1:1 ins Hauptprojekt kopieren
- Sendet Auth-Header server-seitig an Tuwunel (für `allow_legacy_media = false` in Prod)
- Bilder/Videos/Dateien werden über `/api/matrix/media?mxc=...` geladen
- Kein CORS-Problem weil Server-zu-Server

DM vs Room Erstellung (wichtig!):
- Matrix unterscheidet DMs und Rooms **nur** über `m.direct` Account-Data
- Ein DM ist technisch ein Room mit `is_direct: true` bei Erstellung + `m.direct` Eintrag
- **DM erstellen** (User↔Agent, User↔User):
  ```typescript
  // 1. Room erstellen mit is_direct
  const result = await client.createRoom({
    is_direct: true,
    invite: ["@trading-agent:matrix.local"],
    preset: "trusted_private_chat",
  });
  // 2. m.direct Account-Data updaten (PFLICHT — sonst wird es als Room erkannt!)
  const directMap = client.getAccountData("m.direct")?.getContent() ?? {};
  directMap["@trading-agent:matrix.local"] = [...(directMap["@trading-agent:matrix.local"] ?? []), result.room_id];
  await client.setAccountData("m.direct", directMap);
  ```
- **Ohne `m.direct`** → Frontend zeigt RoomInfoPanel statt DMInfoPanel
- **Go Backend** muss bei Agent-Chat Erstellung beides setzen (createRoom + m.direct)
- Bestehende Rooms beitreten: `client.joinRoom(roomId)` oder `client.joinRoom("#general:matrix.local")`
- Einladung zu bestehendem Room: `client.invite(roomId, userId)` — eingeladener User muss `joinRoom()` aufrufen
- Auto-Accept für DMs: Client-seitig implementiert (`useAutoAcceptInvites` Hook)

Profil-Handling (Option A):
- Display-Name + Avatar aus dem Hauptprojekt synchronisieren, nicht im Chat editierbar
- `src/components/matrix/UserProfileDialog.tsx` — bei Portierung entfernen oder read-only machen
- `SpaceSelector.tsx` Zeile ~104 rendert UserProfileDialog als letztes Element in der Space-Rail → Trigger entfernen
- Matrix-Account wird beim Hauptprojekt-Login erstellt, Display-Name vom Hauptprojekt gesetzt
- Aktuell (Testsetup): Frei editierbar — OK für Entwicklung

### Schritt 2c — Globale Rollen + Power-Levels

Matrix hat **keine** globalen Rollen — nur Server-Admin (Tuwunel Admin API) und Room-Admins (Power-Levels pro Raum).

Mapping NextAuth → Matrix:
```
NextAuth Rolle     → Matrix Power-Level in neuen Räumen
─────────────────────────────────────────────────────────
App-Admin          → 100 (Room-Admin in allen erstellten Räumen)
Normaler User      → 0 (Member)
Agent-Bot          → 0 (Member, kann nur senden/reagieren)
```

Go Backend setzt Power-Levels bei Raum-Erstellung:
- User erstellt Raum → Go prüft NextAuth-Rolle → setzt Power-Level
- App-Admin tritt bestehendem Raum bei → Go setzt Power-Level via Admin API
- Server-Admin Rechte (User erstellen/löschen) bleiben in Go Backend (Admin API)
- **Matrix hat keine "Super-Admin der alles sehen kann"** — ein Server-Admin kann DB lesen, aber in E2EE Räumen nicht entschlüsseln

### Schritt 3 — Homeserver Production-Config

```toml
# homeserver/tuwunel.prod.toml
[global]
server_name = "matrix.yourdomain.com"  # echte Domain
address = "127.0.0.1"                  # nur lokaler Zugriff (Nginx/Caddy davor)
port = 8448

# TLS: Nginx/Caddy übernimmt TLS-Terminierung
# OIDC: NextAuth als OIDC Provider (optional)
[global.oidc]
issuer = "https://yourdomain.com"
client_id = "matrix-element-x"
```

### Schritt 4 — User-Provisioning (NextAuth → Matrix)

In Prod wird `registration_token` **NICHT** verwendet. Stattdessen:

```
User → NextAuth Login → Session → Go Backend: POST /api/matrix/provision
                                         ↓
                                   Go → Tuwunel Admin API: User erstellen
```

```toml
# Prod: Keine öffentliche Registrierung
allow_registration = false
# registration_token nicht nötig — Go erstellt User via Admin API
```

Go Backend erstellt Matrix-User programmtisch:
- Bei erstem Login: `POST /_synapse/admin/v1/register` (Tuwunel Admin API)
- Display-Name + Avatar aus NextAuth Session synchronisieren
- Matrix Access-Token in Session speichern → an Next.js Client weiterreichen
- **Kein registration_token nötig** — Admin API nutzt `shared_secret` oder Admin-Credentials

### Schritt 4b — Token-Sicherheit

- `tuwunel.toml` enthält Secrets (as_token, hs_token) → **NICHT committen** (gitignore)
- `tuwunel.example.toml` mit Platzhaltern committen
- Prod: Secrets aus Secrets-Manager (Docker Secrets, Vault, etc.)
- Tuwunel unterstützt Env-Vars: `TUWUNEL_AS_TOKEN=...`, `TUWUNEL_HS_TOKEN=...`

### Schritt 5 — NATS Subjects isolieren

Im Hauptprojekt gibt es bereits NATS Subjects:
- `market.*.tick` — Marktdaten
- `market.*.ohlcv.*` — Candlestick-Daten
- `geo.event.new` — Geopolitische Events

Matrix-spezifische Subjects müssen isoliert bleiben:
```go
// Eigene Namespace-Präfixe für Matrix
const SubjectMatrixMessage = "matrix.event.message"
const SubjectMatrixReply   = "matrix.event.reply"
// NICHT in Konflikt mit market.* oder geo.* Subjects
```

---

## Zeitplan (grob)

| Phase | Was | Voraussetzung |
|---|---|---|
| Phase A | Matrix-Projekt vollständig testen | ← aktuell |
| Phase B | Go Appservice in go-backend integrieren | Phase A abgeschlossen |
| Phase C | Next.js Komponenten portieren | Phase A abgeschlossen |
| Phase D | Homeserver Production-Config | VPS/Server verfügbar |
| Phase E | OIDC Integration (Element X Login via App-Account) | NextAuth konfiguriert |

---

## Quellen

- `D:\tradingview-clones\tradeview-fusion\go-backend\internal\connectors\ipc\client.go`
- `D:\tradingview-clones\tradeview-fusion\go-backend\internal\connectors\agentservice\client.go`
- `D:\tradingview-clones\tradeview-fusion\go-backend\internal\proto\ipc\ipc.proto`
- `D:\tradingview-clones\tradeview-fusion\go-backend\internal\messaging\topics.go`
