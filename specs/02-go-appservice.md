# Go Matrix Appservice — mautrix-go

**Status:** Aktiv
**Stand:** 06.04.2026 — E2EE + Cross-Signing aktiv, NATS Bridge zu Python Backend, HTTP Proxy fuer Agent Service

## Was ist ein Appservice?

Ein Matrix Application Service (Appservice) ist ein registrierter HTTP-Server, der:
- Einen **Namespace virtueller User-IDs** bei Tuwunel beansprucht (`@agent-*:domain`)
- Matrix-Events fuer diese User via HTTP-Webhook **empfaengt**
- Als diese virtuellen User **sendet** (via `?user_id=` Query-Parameter)
- Ermoeglicht: Orchestrator-Agent + optionale Sub-Agents haben eigene Matrix-Identitaeten

Im Matrix-Projekt uebernimmt der Go Appservice zusaetzlich **drei weitere Rollen**:

1. **E2BE-Endpunkt** — Go ist der einzige Matrix-Endpunkt mit Crypto. Python Bridge sieht
   nur Klartext via NATS. matrix-nio wurde in exec-05 entfernt.
2. **HTTP Proxy** — bridged das Frontend (nextjs-chat / agent-chat) zum Python Backend
   (Agent Service Port 8094, Memory Service Port 8093) inkl. SSE Streaming.
3. **NATS Producer/Consumer** — published Matrix-Messages auf `matrix.message.inbound`,
   subscribed `matrix.message.reply`.

**mautrix-go** abstrahiert Matrix Protocol — Intent API, State Storage, E2EE.

- Repo: https://github.com/mautrix/go
- Package: `maunium.net/go/mautrix`
- Verwendete Version: **v0.22.0**

---

## Stack & Versionen

```go
// go.mod (Auszug)
module matrix/go-appservice

go 1.26

require (
    maunium.net/go/mautrix v0.22.0          // Matrix Client + Crypto
    github.com/nats-io/nats.go v1.49.0      // Message Queue
    modernc.org/sqlite v1.34.4               // Pure-Go SQLite (Crypto Store)
    github.com/rs/zerolog v1.33.0            // Strukturiertes Logging
    gopkg.in/yaml.v3 v3.0.1                  // registration.yaml Parsing
    github.com/joho/godotenv v1.5.1          // .env Loader
    golang.org/x/crypto v0.46.0              // (indirekt via mautrix)
)
```

**Crypto-Variante:** `goolm` Build-Tag → Pure-Go Olm Implementation (kein CGO, kein libolm).

```bash
go run -tags goolm ./cmd/appservice/...
```

---

## Verzeichnisstruktur

```
go-appservice/
├── go.mod / go.sum
├── .env.example / .env.development / .env.production
├── cmd/
│   └── appservice/
│       └── main.go                      # Einstiegspunkt (CLI Flags fuer --generate-registration)
├── internal/
│   ├── config/
│   │   └── config.go                    # ENV Loader, Config Struct
│   ├── handler/
│   │   └── server.go                    # HTTP Server, Event Processing, Intent Coordinator
│   ├── handlers/http/                   # HTTP Proxies (siehe naechste Sektion)
│   │   ├── agent_chat_handler.go        # SSE Proxy zu Python Agent Service (Port 8094)
│   │   ├── agent_tool_proxy_handler.go  # Tool-Calls bridging
│   │   ├── agent_audio_handler.go       # STT/TTS Proxy
│   │   ├── mcp_proxy_handler.go         # MCP Server Proxy
│   │   ├── memory_handler.go            # Knowledge Graph / Episode Store Proxy
│   │   └── helpers.go
│   ├── intent/
│   │   └── agent.go                     # AgentSender API — virtuelle Agent-User-IDs
│   ├── natsbridge/
│   │   └── bridge.go                    # NATS Pub/Sub: matrix.message.inbound / .reply
│   ├── crypto/
│   │   ├── machine.go                   # OlmMachine Wrapper (E2EE, goolm)
│   │   └── statestore.go                # Encryption State + Room Members Cache
│   ├── connectors/
│   │   ├── agentservice/
│   │   │   └── client.go                # HTTP Client zu Agent Service
│   │   └── memory/
│   │       └── client.go                # HTTP Client zu Memory Service
│   └── registration/
│       └── generate.go                  # registration.yaml Generator
└── data/
    ├── crypto.sqlite3                   # SQLite Crypto Store (gitignored)
    ├── cross_signing_seeds.json         # MSK/SSK/USK Seeds (gitignored, 0o600)
    └── megolm_keys_backup.bin           # Megolm Room Key Backup (gitignored)
```

---

## HTTP Endpoints

| Endpoint | Method | Zweck |
|---|---|---|
| `/_matrix/app/v1/transactions/{txnID}` | PUT | Receive Room Events vom Homeserver |
| `/_matrix/app/v1/users/{userID}` | GET | User Existence Check (Agent-Namespace) |
| `/health` | GET | Health Check (E2EE Status reported) |
| `/api/v1/agent/chat` | POST | SSE Chat Streaming Proxy zu Python Agent |
| `/api/v1/agent/approve` | POST | Tool Call Approval Proxy |
| `/api/v1/agent/tools/*` | GET/POST | Tool State Queries + Mutations |
| `/api/v1/mcp/*` | * | MCP Server Proxy (exec-09) |
| `/api/v1/audio/transcribe` | POST | STT Proxy (audio → text) |
| `/api/v1/audio/synthesize` | POST | TTS Proxy (text → audio) |
| `/api/v1/memory/kg/*` | * | Knowledge Graph Endpoints |
| `/api/v1/memory/episode*` | * | Episode Storage Endpoints |

**Pattern:** Frontend ruft Go Appservice (Port 8090), Go proxied weiter zu Python Backend
(Port 8094 / 8093). Vorteil: einheitlicher TLS-/Auth-Endpunkt, Frontend braucht keinen
direkten Python-Zugriff. Header durchgereicht: `x-user-role`, `x-auth-user`, `x-request-id`.

---

## Matrix Event Handling

**Behandelte Event-Typen** (in `internal/handler/server.go`):

| Event Type | Handler | Verhalten |
|---|---|---|
| `m.room.message` | `handleMessage()` | Text extrahieren, Mention-Filter, NATS publish |
| `m.room.encrypted` | `handleEncrypted()` | Decrypt via OlmMachine, dann reprocess |
| `m.room.member` | `handleMembership()` | Track room members, auto-join Agents auf Invite |
| `m.room.encryption` | `handleEncryptionState()` | Crypto State Store update |

**Mention-Filter (`MENTION_ONLY_IN_GROUPS=true`):**
- DMs (≤2 Members): Immer forwarden
- Group rooms: Nur wenn `@agent-` Prefix erwaehnt, Reply auf Agent-Message, oder Trigger-Word

---

## Intent API & Virtuelle Agent-User-IDs

**Implementation:** `internal/intent/agent.go`

```go
sender.UserID("trading")          // → @agent-trading:matrix.local
sender.SendText(agentID, roomID, text)
sender.SetTyping(agentID, roomID, true)
sender.JoinRoom(agentID, roomID)
sender.EnsureProfile(agentID, "Trading Agent")
```

**Mechanismus:**
- Alle Requests nutzen `?user_id={agentID}` Query-Parameter (Appservice-Privileg)
- Accounts werden bei erster Message automatisch erstellt (Homeserver-Verhalten)
- Profil-Updates via `EnsureProfile()` setzt displayName

**Namespace-Kontrolle:**
- registration.yaml regex: `@agent-.*:matrix\.local` (exclusive)
- Nur Appservice darf User in diesem Pattern erstellen
- Validation in `isAgentUser()` Helper

---

## NATS Bridge

**Subjects:**

```
matrix.message.inbound  → InboundMessage{room_id, sender, body, event_id, thread_id}
matrix.message.reply    ← ReplyMessage{room_id, agent_user_id, text, is_streaming}
```

**Flow:**

```
Matrix Event (Tuwunel)
    ↓ HTTP /transactions/
Go Appservice handleMessage()
    ↓ NATS publish (matrix.message.inbound)
Python Bridge (Port 8097)  → NATS Consumer
    ↓ HTTP SSE
Python Agent Service (Port 8094)
    ↓ NATS publish (matrix.message.reply)
Go Appservice SubscribeReplies()
    ↓ sendEncryptedReply() oder agent.SendText()
Tuwunel → Matrix Room
```

**Direct Connectivity:**
- Go Appservice ↔ NATS ↔ Python Bridge — kein gRPC, kein direkter HTTP-Call
- Go Appservice → HTTP → Agent Service (Port 8094) fuer SSE Streaming Chat (Frontend Path)
- Go Appservice → HTTP → Memory Service (Port 8093, optional) fuer KG Operations

---

## E2EE Stack — Option C (Go Handles Crypto)

**Trust Model:** Go Appservice ist einziger Matrix-Endpunkt mit Crypto. Python Bridge
sieht nur Klartext via NATS. Vorteile:
- Ein einziger Cross-Signing-Account, eine OlmMachine
- Python kann Stateless bleiben (keine Schluesselverwaltung)
- Keine `matrix-nio` Dependency in Python

**Komponenten:**

| Komponente | Implementation |
|---|---|
| **OlmMachine** | `crypto.NewOlmMachine` (goolm via mautrix-go) |
| **Crypto Store** | `SQLCryptoStore` (modernc.org/sqlite, Pure Go) |
| **State Store** | Custom `StateStore` (in-memory cache + Homeserver Fallback) |
| **Device Keys** | Upload bei Init via `ShareKeys()` |
| **Cross-Signing** | MSC4153 Bootstrap (MSK/SSK/USK), persistiert in `seeds.json` |
| **Room Keys** | `ExportKeyBackup()` bei Megolm Session Creation |
| **Decryption** | `crypto.Decrypt()` auf `m.room.encrypted` Events |
| **Encryption** | `crypto.Encrypt()` fuer `sendEncryptedReply()` |

**Key Management:**
- Cross-Signing Seeds: `./data/cross_signing_seeds.json` (persistent, 0o600)
- Room Key Backups: `./data/megolm_keys_backup.bin` (passphrase-encrypted)
- Device ID: statisch `"APPSERVICE"` (fuer Olm State erforderlich)

**Privacy Feature (C-10 / MSC4381):**
- `sender_key` und `device_id` werden NICHT mitgesendet (deprecated, Privacy)
- Empfaenger identifiziert Sender via Megolm Session

**Cross-Signing Bootstrap (`ensureCrossSigning()`):**
- **Erster Start:** `GenerateAndUploadCrossSigningKeys()` → `SignOwnDevice()` →
  `SignOwnMasterKey()` → Seeds in `seeds.json` schreiben (0o600)
- **Neustart:** `seeds.json` lesen → `ImportCrossSigningKeys()` → Signaturen erneuern (idempotent)
- Verlust der Seeds = Verlust der Identitaet (alle Verifikationen muessen neu durchgefuehrt werden)

---

## Configuration (ENV)

**Critical:**
```env
MATRIX_HOMESERVER_URL=http://127.0.0.1:8448
MATRIX_SERVER_NAME=matrix.local
MATRIX_APPSERVICE_URL=http://127.0.0.1:8090
MATRIX_APPSERVICE_PORT=8090
MATRIX_AS_TOKEN=<32-byte hex>
MATRIX_HS_TOKEN=<32-byte hex>
NATS_URL=nats://127.0.0.1:4222
```

**Optional:**
```env
MATRIX_BOT_USER_ID=@appservice-bot:matrix.local
MATRIX_AGENT_PREFIX=agent-
LOG_LEVEL=info
REGISTRATION_PATH=../homeserver/registration.yaml
MENTION_ONLY_IN_GROUPS=true
AGENT_SERVICE_URL=http://127.0.0.1:8094
MEMORY_SERVICE_URL=http://127.0.0.1:8093
MCP_SERVICE_URL=http://127.0.0.1:8094
```

**E2EE:**
```env
MATRIX_E2EE_ENABLED=true
MATRIX_CRYPTO_DB_PATH=./data/crypto.sqlite3
MATRIX_CRYPTO_PICKLE_KEY=<32-byte hex>
MATRIX_KEY_BACKUP_PASSWORD=<passphrase>
```

**ENV Files:**
- `.env.example` — Template mit allen Defaults
- `.env.development` — Aktive Dev-Config (Tokens, E2EE enabled)
- `.env.production` — Production Template

---

## Token-Generierung

```bash
# Zufaellige Tokens fuer AS/HS
openssl rand -hex 32
```

```powershell
# PowerShell Variante
[System.Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
```

---

## Registration generieren

```bash
go run -tags goolm ./cmd/appservice/... --generate-registration
# → schreibt ../homeserver/registration.yaml mit generierten Tokens
```

Format siehe `01-homeserver.md`.

---

## Portierung ins Hauptprojekt

Im Hauptprojekt nutzt Go → Python **gRPC-IPC** (nicht NATS) fuer direkte Agent-Aufrufe:

```
Matrix-Projekt:    Go Appservice → NATS → Python Bridge → Agent Service
Hauptprojekt:      Go Appservice → ipc/client.go → Python Agent Service (gRPC 9094 / HTTP 8094)
```

**Warum unterschiedlich:**
- Matrix: Event-driven, async — NATS Pub/Sub passt
- Hauptprojekt: SSE-Streaming fuers Frontend — gRPC/HTTP direkt besser

**Beim Portieren:**
1. `natsbridge/` durch IPC-Client aus `go-backend/internal/connectors/ipc/client.go` ersetzen
2. Python Bridge entfaellt — Go ruft bestehenden Python Agent Service direkt
3. NATS Subjects isoliert halten: `matrix.event.*` (kein Konflikt mit `market.*`)
4. `internal/crypto/machine.go` + `ensureCrossSigning()` direkt uebernehmen

Siehe `specs/10-portierung.md` fuer vollstaendigen Portierungsplan.
