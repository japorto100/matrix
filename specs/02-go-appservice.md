# Go Matrix Appservice — mautrix-go

> Stand: 24.03.2026 — C-3 implementiert (Cross-Signing Bootstrap aktiv)

## Was ist ein Appservice?

Ein Matrix Application Service (Appservice) ist ein registrierter HTTP-Server, der:
- Einen **Namespace virtueller User-IDs** bei Tuwunel beansprucht (`@agent-*:domain`)
- Matrix-Events für diese User via HTTP-Webhook **empfängt**
- Als diese virtuellen User **sendet** (via `?user_id=` Query-Parameter)
- Ermöglicht: Orchestrator-Agent + optionale Sub-Agents haben eigene Matrix-Identitäten

**mautrix-go** abstrahiert das alles — Intent API, State Storage, E2EE.

- Repo: https://github.com/mautrix/go
- Package: `maunium.net/go/mautrix`
- Letzte Aktivität: März 2026

---

## go.mod (Go Appservice)

```go
module matrix/go-appservice

go 1.26

require (
    maunium.net/go/mautrix v0.22.0
    github.com/nats-io/nats.go v1.49.0
    github.com/redis/go-redis/v9 v9.17.0
    github.com/jackc/pgx/v5 v5.8.0
    github.com/golang-jwt/jwt/v5 v5.3.1
    go.opentelemetry.io/otel v1.41.0
    go.opentelemetry.io/otel/trace v1.41.0
    gopkg.in/yaml.v3 v3.0.1
    golang.org/x/sync v0.20.0
)
```

> Viele Versionen direkt aus dem Haupt-`go.mod` übernommen.
> mautrix-go bringt eigene Crypto-Deps (libolm/vodozemac via CGO oder pure-Go).

---

## Verzeichnisstruktur

```
go-appservice/
├── go.mod
├── go.sum
├── .golangci.yml          # identisch mit Hauptprojekt
├── cmd/
│   └── appservice/
│       └── main.go        # Einstiegspunkt
├── internal/
│   ├── config/
│   │   └── config.go      # Config-Struct + Env-Loading
│   ├── crypto/
│   │   ├── machine.go     # OlmMachine Setup + ensureCrossSigning()
│   │   └── statestore.go  # In-Memory StateStore
│   ├── handler/
│   │   └── events.go      # Matrix Event Handler (Messages, Membership, etc.)
│   ├── intent/
│   │   └── agent.go       # Agent Intent-Wrapper (senden als @agent-*:domain)
│   ├── nats/
│   │   └── bridge.go      # NATS: Matrix Events → Agent-Service weiterleiten
│   └── registration/
│       └── generate.go    # registration.yaml generieren
├── data/
│   ├── crypto.sqlite3          # SQLite Crypto Store (gitignore)
│   └── cross_signing_seeds.json # Cross-Signing Seeds (gitignore, 0o600)
└── registration.yaml.tmpl # Template für Appservice-Registration
```

---

## cmd/appservice/main.go

```go
package main

import (
    "context"
    "log/slog"
    "os"
    "os/signal"
    "syscall"

    "matrix/go-appservice/internal/config"
    "matrix/go-appservice/internal/handler"
    "matrix/go-appservice/internal/nats"
    "maunium.net/go/mautrix"
    "maunium.net/go/mautrix/appservice"
)

func main() {
    cfg := config.Load()

    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))
    slog.SetDefault(logger)

    // Appservice initialisieren
    as, err := appservice.Create()
    if err != nil {
        slog.Error("appservice.Create failed", "error", err)
        os.Exit(1)
    }

    as.HomeserverURL = cfg.HomeserverURL   // http://localhost:8448
    as.HomeserverDomain = cfg.ServerName   // matrix.local
    as.Registration = &appservice.Registration{
        ID:          "trading-agent-appservice",
        URL:         cfg.AppserviceURL,    // http://localhost:29318
        AppToken:    cfg.ASToken,
        ServerToken: cfg.HSToken,
        SenderLocalpart: "appservice-bot",
    }

    // NATS Bridge für Event-Weiterleitung an Python Agents
    natsBridge, err := nats.NewBridge(cfg.NATSUrl)
    if err != nil {
        slog.Error("NATS connect failed", "error", err)
        os.Exit(1)
    }

    // Event Handler registrieren
    h := handler.New(as, natsBridge, cfg)
    as.Router.HandleFunc("/_matrix/app/v1/transactions/{txnID}", h.HandleTransaction)

    // Matrix Client für den Haupt-Bot erstellen
    client, err := as.NewExternalMautrixClient(cfg.BotUserID, "", cfg.HomeserverURL)
    if err != nil {
        slog.Error("matrix client init failed", "error", err)
        os.Exit(1)
    }
    _ = client

    ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
    defer cancel()

    slog.Info("Appservice starting", "url", cfg.AppserviceURL, "server", cfg.ServerName)

    if err := as.Start(ctx); err != nil {
        slog.Error("appservice start failed", "error", err)
        os.Exit(1)
    }

    <-ctx.Done()
    slog.Info("Appservice shutting down")
    as.Stop()
}
```

---

## internal/config/config.go

```go
package config

import (
    "os"
)

type Config struct {
    HomeserverURL  string
    ServerName     string
    AppserviceURL  string
    AppservicePort string
    ASToken        string
    HSToken        string
    BotUserID      string
    NATSUrl        string
    LogLevel       string
}

func Load() *Config {
    return &Config{
        HomeserverURL:  getenv("MATRIX_HOMESERVER_URL", "http://localhost:8448"),
        ServerName:     getenv("MATRIX_SERVER_NAME", "matrix.local"),
        AppserviceURL:  getenv("MATRIX_APPSERVICE_URL", "http://localhost:29318"),
        AppservicePort: getenv("MATRIX_APPSERVICE_PORT", "29318"),
        ASToken:        mustenv("MATRIX_AS_TOKEN"),
        HSToken:        mustenv("MATRIX_HS_TOKEN"),
        BotUserID:      getenv("MATRIX_BOT_USER_ID", "@appservice-bot:matrix.local"),
        NATSUrl:        getenv("NATS_URL", "nats://localhost:4222"),
        LogLevel:       getenv("LOG_LEVEL", "info"),
    }
}

func getenv(key, fallback string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return fallback
}

func mustenv(key string) string {
    v := os.Getenv(key)
    if v == "" {
        panic("required env var not set: " + key)
    }
    return v
}
```

---

## internal/handler/events.go

```go
package handler

import (
    "encoding/json"
    "log/slog"
    "net/http"

    "matrix/go-appservice/internal/nats"
    "maunium.net/go/mautrix/appservice"
    "maunium.net/go/mautrix/event"
)

type Handler struct {
    as          *appservice.AppService
    natsBridge  *nats.Bridge
    cfg         interface{ GetServerName() string }
}

func New(as *appservice.AppService, natsBridge *nats.Bridge, cfg interface{ GetServerName() string }) *Handler {
    return &Handler{as: as, natsBridge: natsBridge, cfg: cfg}
}

// HandleTransaction empfängt Events vom Homeserver
func (h *Handler) HandleTransaction(w http.ResponseWriter, r *http.Request) {
    var txn struct {
        Events []*event.Event `json:"events"`
    }
    if err := json.NewDecoder(r.Body).Decode(&txn); err != nil {
        http.Error(w, "bad request", http.StatusBadRequest)
        return
    }

    for _, ev := range txn.Events {
        h.processEvent(r.Context(), ev)
    }

    w.WriteHeader(http.StatusOK)
    _, _ = w.Write([]byte("{}"))
}

func (h *Handler) processEvent(ctx context.Context, ev *event.Event) {
    switch ev.Type {
    case event.EventMessage:
        h.handleMessage(ctx, ev)
    case event.StateMember:
        h.handleMembership(ctx, ev)
    default:
        slog.Debug("unhandled event type", "type", ev.Type)
    }
}

func (h *Handler) handleMessage(ctx context.Context, ev *event.Event) {
    content, ok := ev.Content.Parsed.(*event.MessageEventContent)
    if !ok {
        return
    }

    // Nur Text-Nachrichten an Agent weiterleiten
    if content.MsgType != event.MsgText {
        return
    }

    // Nicht auf eigene Bot-Nachrichten reagieren
    // (Sender ist eine @agent-* ID → ignorieren)
    if isAgentUser(ev.Sender.String()) {
        return
    }

    slog.Info("message received",
        "room", ev.RoomID,
        "sender", ev.Sender,
        "body", content.Body,
    )

    // Via NATS an Python Agent weiterleiten
    if err := h.natsBridge.PublishMatrixMessage(ctx, ev, content); err != nil {
        slog.Error("NATS publish failed", "error", err, "room", ev.RoomID)
    }
}

func (h *Handler) handleMembership(ctx context.Context, ev *event.Event) {
    // Agent auto-joinт Räume wenn er eingeladen wird
    content, ok := ev.Content.Parsed.(*event.MemberEventContent)
    if !ok {
        return
    }
    if content.Membership == event.MembershipInvite {
        // Agent nimmt Einladung an
        agentIntent := h.as.Intent(ev.GetStateKey())
        if err := agentIntent.JoinRoom(ctx, ev.RoomID.String(), nil); err != nil {
            slog.Error("join room failed", "error", err, "room", ev.RoomID)
        }
    }
}

func isAgentUser(userID string) bool {
    // Prüft ob User-ID aus dem Agent-Namespace kommt
    // Pattern: @agent-*:domain
    return len(userID) > 7 && userID[1:7] == "agent-"
}
```

---

## internal/intent/agent.go — Als Agent senden

```go
package intent

import (
    "context"

    "maunium.net/go/mautrix/appservice"
    "maunium.net/go/mautrix/event"
    "maunium.net/go/mautrix/id"
)

// AgentSender sendet Nachrichten als virtueller Agent-User
type AgentSender struct {
    as *appservice.AppService
}

func NewAgentSender(as *appservice.AppService) *AgentSender {
    return &AgentSender{as: as}
}

// SendMessage sendet eine Nachricht als spezifischer Agent
func (s *AgentSender) SendMessage(ctx context.Context, agentUserID id.UserID, roomID id.RoomID, text string) error {
    intent := s.as.Intent(agentUserID)

    // Display Name setzen (einmalig pro Agent)
    _ = intent.SetDisplayName(ctx, "Trading Agent 🤖")

    // Nachricht senden
    _, err := intent.SendMessageEvent(ctx, roomID, event.EventMessage, &event.MessageEventContent{
        MsgType: event.MsgText,
        Body:    text,
    })
    return err
}

// SendTyping — Tipp-Indikator während Agent "denkt"
func (s *AgentSender) SendTyping(ctx context.Context, agentUserID id.UserID, roomID id.RoomID, typing bool) error {
    intent := s.as.Intent(agentUserID)
    return intent.UserTyping(ctx, roomID, typing, 30000) // 30s timeout
}
```

---

## internal/nats/bridge.go

```go
package nats

import (
    "context"
    "encoding/json"

    "github.com/nats-io/nats.go"
    "maunium.net/go/mautrix/event"
    "maunium.net/go/mautrix/event"
)

const (
    SubjectMatrixMessage = "matrix.message.inbound"
    SubjectAgentReply    = "matrix.message.reply"
)

type Bridge struct {
    nc *nats.Conn
}

type MatrixMessageEvent struct {
    RoomID   string `json:"room_id"`
    Sender   string `json:"sender"`
    Body     string `json:"body"`
    EventID  string `json:"event_id"`
    ThreadID string `json:"thread_id,omitempty"`
}

type AgentReplyEvent struct {
    RoomID      string `json:"room_id"`
    AgentUserID string `json:"agent_user_id"`
    Text        string `json:"text"`
    IsStreaming bool   `json:"is_streaming"`
}

func NewBridge(natsURL string) (*Bridge, error) {
    nc, err := nats.Connect(natsURL)
    if err != nil {
        return nil, err
    }
    return &Bridge{nc: nc}, nil
}

func (b *Bridge) PublishMatrixMessage(ctx context.Context, ev *event.Event, content *event.MessageEventContent) error {
    msg := MatrixMessageEvent{
        RoomID:  ev.RoomID.String(),
        Sender:  ev.Sender.String(),
        Body:    content.Body,
        EventID: ev.ID.String(),
    }
    data, err := json.Marshal(msg)
    if err != nil {
        return err
    }
    return b.nc.Publish(SubjectMatrixMessage, data)
}

// SubscribeAgentReplies empfängt Antworten vom Python Agent und sendet sie in Matrix
func (b *Bridge) SubscribeAgentReplies(handler func(AgentReplyEvent)) error {
    _, err := b.nc.Subscribe(SubjectAgentReply, func(msg *nats.Msg) {
        var reply AgentReplyEvent
        if err := json.Unmarshal(msg.Data, &reply); err != nil {
            return
        }
        handler(reply)
    })
    return err
}

func (b *Bridge) Close() {
    b.nc.Drain()
}
```

---

## internal/crypto/machine.go — E2EE + Cross-Signing Bootstrap

### OlmMachine Setup

```go
// goolm Build-Tag aktiviert Pure-Go Crypto
olmMachine := crypto.NewOlmMachine(client, &zlog, cryptoStore, stateStore)
olmMachine.SendKeysMinTrust = id.TrustStateUnset  // sendet Megolm-Keys an alle Geräte
olmMachine.Load(ctx)
olmMachine.ShareKeys(ctx, -1)

// Cross-Signing Bootstrap (C-3)
if err := ensureCrossSigning(ctx, olmMachine, dbDir); err != nil {
    slog.Error("cross-signing bootstrap failed", "error", err)
}
```

**`SendKeysMinTrust = TrustStateUnset`:** Standardmäßig sendet OlmMachine Megolm-Keys
nur an Geräte mit mindestens einem bestimmten Trust-Level. `TrustStateUnset` deaktiviert
diese Einschränkung — der Go Appservice sendet Keys an alle Geräte im Raum.
Nötig, weil der Appservice nicht aktiv alle Peer-Geräte verifiziert.

### ensureCrossSigning()

Wird einmalig nach `olmMachine.Load()` aufgerufen. Persistiert Cross-Signing-Seeds
damit die Identität über Neustarts erhalten bleibt.

**Erster Start (Seeds-Datei fehlt):**
```go
// 1. Keys generieren und auf den Homeserver hochladen
err := olmMachine.GenerateAndUploadCrossSigningKeys(ctx, nil, "")

// 2. Eigenes Gerät (Appservice Device) mit Self-Signing Key signieren
err = olmMachine.SignOwnDevice(ctx)

// 3. Master Key mit User-Signing Key signieren
err = olmMachine.SignOwnMasterKey(ctx)

// 4. Seeds für Persistenz sichern (0o600)
seeds := extractSeeds(olmMachine)
writeJSONFile(seedsPath, seeds, 0o600)
```

**Neustart (Seeds-Datei vorhanden):**
```go
// 1. Seeds laden
seeds := readJSONFile(seedsPath)

// 2. Cross-Signing-Keys aus Seeds importieren (keine neuen Keys → gleiche Identität)
err := olmMachine.ImportCrossSigningKeys(seeds)

// 3. Signaturen erneuern (idempotent)
err = olmMachine.SignOwnDevice(ctx)
err = olmMachine.SignOwnMasterKey(ctx)
```

### Seeds-Datei

```
Pfad:         <dbDir>/cross_signing_seeds.json
Rechte:       0o600 (nur Owner lesbar, nie committen)
Inhalt:       { "master_key": "<base64>", "self_signing_key": "<base64>", "user_signing_key": "<base64>" }
```

Die Seeds sind die privaten Anteile der drei Cross-Signing-Schlüssel (Master, Self-Signing, User-Signing).
Verlust der Seeds bedeutet Verlust der Cross-Signing-Identität — alle Verifikationen müssen neu durchgeführt werden.

---

## .env (Go Appservice)

```env
MATRIX_HOMESERVER_URL=http://localhost:8448
MATRIX_SERVER_NAME=matrix.local
MATRIX_APPSERVICE_URL=http://localhost:29318
MATRIX_APPSERVICE_PORT=29318
MATRIX_AS_TOKEN=<zufälliger_hex_token>
MATRIX_HS_TOKEN=<zufälliger_hex_token>
MATRIX_BOT_USER_ID=@appservice-bot:matrix.local
NATS_URL=nats://localhost:4222
LOG_LEVEL=info
```

---

## Token generieren

```bash
# Zufällige Tokens für AS/HS
openssl rand -hex 32
# oder in PowerShell:
[System.Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
```

---

## Portierung ins Hauptprojekt

Im Hauptprojekt nutzt Go → Python **gRPC-IPC** (nicht NATS) für direkte Agent-Aufrufe:

```
Matrix-Projekt:    Go Appservice → NATS → Python Bridge → Agent Service
Hauptprojekt:      Go Appservice → ipc/client.go → Python Agent Service (gRPC 9094 / HTTP 8094)
```

**Warum unterschiedlich:**
- Matrix: Event-driven, async — NATS Pub/Sub passt
- Hauptprojekt: SSE-Streaming für Frontend — gRPC/HTTP direkt besser

**Beim Portieren:**
1. `natsbridge/` durch IPC-Client aus `go-backend/internal/connectors/ipc/client.go` ersetzen
2. Python Agent Bridge entfällt — Go ruft bestehenden `python-agent` Service direkt
3. NATS Subjects isoliert halten: `matrix.event.*` (kein Konflikt mit `market.*`)
4. `internal/crypto/machine.go` + `ensureCrossSigning()` direkt übernehmen — keine Anpassungen nötig

Siehe `specs/10-portierung.md` für vollständigen Portierungsplan.
