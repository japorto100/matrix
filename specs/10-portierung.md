# Portierung ins Hauptprojekt (tradeview-fusion)

> **Status: Zu evaluieren.** Diese Spec wurde im isolierten Matrix-Testprojekt erstellt,
> zwar bereits mit Bezug auf die tradeview-fusion Fullstack-App, aber die Vorschläge
> sollten bei der tatsächlichen Portierung kritisch hinterfragt werden. Architektur,
> Infrastruktur und Anforderungen des Hauptprojekts können von den Annahmen hier abweichen.

## Ziel

Das Matrix-Isolationsprojekt (`D:\matrix`) wird nach erfolgreichem Test in das
Hauptprojekt (`D:\tradingview-clones\tradeview-fusion`) portiert.

---

## Architektur-Unterschiede: Matrix-Projekt vs. Hauptprojekt

### Go → Python Kommunikation

| | Matrix-Projekt | Hauptprojekt |
|---|---|---|
| Mechanismus | NATS Pub/Sub | gRPC-IPC (HTTP Fallback) |
| Warum | Event-driven, async, entkoppelt | Request-Response mit SSE Streaming |
| Go→Python | Publish auf `matrix.message.*` | `ipc/client.go` ForwardRequest() |
| Python→Go | Subscribe + Reply auf NATS | HTTP Response / gRPC Response |
| gRPC Port | nicht genutzt | HTTP_Port + 1000 (z.B. 8094→9094) |

**Beim Portieren:**
- Go Appservice nutzt statt NATS den bestehenden `ipc/client.go`
- Python Agent Bridge wird NOT portiert — Go ruft direkt den bestehenden `python-agent` Service
- NATS bleibt für Marktdaten (market.*.tick etc.) — nicht für Matrix-Events

### Port-Mapping

| Service | Matrix-Projekt | Hauptprojekt |
|---|---|---|
| Go Gateway | 8090 (Appservice) | 9060 |
| Python Agent | 8097 (Bridge) | 8094 (HTTP) / 9094 (gRPC) |
| NATS | 4222 | 4222 (gleich) |
| Homeserver | 8448 | 8448 (gleich) |

---

## Was direkt übernommen wird

| Komponente | Wo | Änderungen |
|---|---|---|
| `homeserver/tuwunel.toml` | Homeserver-Config bleibt | Production-Anpassungen (TLS, server_name) |
| `go-appservice/` | Appservice-Logik | IPC-Client statt NATS für Agent-Calls |
| Matrix Event-Handling | `handler/events.go` | Bleibt identisch |
| Auto-Join Logik | `handler/events.go` | Bleibt identisch |
| Namespace-Regex | `registration.yaml` | Anpassen auf prod server_name |
| Python mention-only Logik | `matrix_client.py` | Direkt übernehmen |
| `nextjs-chat/` Komponenten | `src/components/matrix/` | 1:1 ins Hauptprojekt |
| Matrix Hooks | `src/lib/matrix/hooks/` | 1:1 ins Hauptprojekt |

---

## Was NICHT portiert wird

| Was | Warum |
|---|---|
| `python-agent-bridge/` (eigenständig) | Hauptprojekt hat bereits `python-agent` Service |
| `scripts/setup-users.ps1` | Hauptprojekt hat eigene User-Verwaltung (DB + Auth) |
| Dendrite | Nur Windows-Dev-Fallback, nicht für Production |
| `tools/dendrite.exe` | Hauptprojekt nutzt Tuwunel direkt |

---

## Portierungs-Schritte

### Schritt 1 — Go Appservice integrieren

```
tradeview-fusion/
└── go-backend/
    └── internal/
        └── matrix/               ← NEU
            ├── appservice.go     ← aus go-appservice/cmd/appservice/main.go
            ├── handler.go        ← aus go-appservice/internal/handler/events.go
            └── agent_bridge.go   ← NATS ersetzen durch ipc/client.go Call
```

`agent_bridge.go` — Anpassung:
```go
// Matrix-Projekt: via NATS
natsPub.Publish("matrix.message.agent", payload)

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
