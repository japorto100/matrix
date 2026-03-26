# Matrix Integration — Project Overview

## Ziel

Matrix-Protokoll als Kommunikationsschicht in das Hauptprojekt (tradeview-fusion) integrieren.
Dieses Repo ist das **isolierte Testsetup** — wenn alles funktioniert, wird es portiert.

### Konkrete Use Cases

1. **User ↔ User Chat** — Matrix-Räume direkt in der Web-App eingebettet
2. **User ↔ Agent Chat** — Python-Agent nimmt an Matrix-Räumen teil, hat eigene Matrix-ID
3. **Gruppen-Chats** — Mehrere User + Agent(s) in einem Raum
4. **Mobile** — User chattet über Element X App mit anderen Usern und mit Agents
5. **E2EE** — Verschlüsselung auch wenn fremde Homeserver in Föderationsumgebung

---

## Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│              Matrix Homeserver (Tuwunel oder Dendrite)          │
│         token-based registration, kein Telefon, OIDC-ready      │
└────────────────────────┬────────────────────────────────────────┘
                         │ Federation (optional)
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
  Go Appservice    Python Agent     Element X (Mobile)
  (mautrix-go)     (matrix-nio)     iOS + Android
  port 8090         port 8097        ↕ OIDC Login
         │               │
         └───────┬───────┘
                 │ NATS / HTTP
                 ▼
         Go Gateway (bestehend)
         NATS · Redis · PostgreSQL · WebSocket
                 │
                 ▼
         Python Agent Loop (bestehend)
         FastAPI · Anthropic/Claude · LiteLLM
                 │
                 ▼
         Next.js Frontend (port 3000)
         "use client" MatrixChat Komponente
         matrix-js-sdk + shadcn/ui + Tailwind v4
```

---

## Stack-Entscheidungen

| Komponente | Technologie | Begründung |
|---|---|---|
| Homeserver (Primär) | **Tuwunel** (Rust) | ~50–150 MB RAM idle, Single Binary, RocksDB eingebettet, kein PostgreSQL nötig |
| Homeserver (Windows Fallback) | **Dendrite** (Go) | Kompiliert nativ für Windows (.exe), kein WSL nötig, SQLite, dev-tauglich |
| Go Matrix-Schicht | **mautrix-go** | Appservice API, Intent API für virtuelle User-IDs, aktiv März 2026 |
| Python Matrix-Bot | **matrix-nio** | Async, sans-I/O, E2EE, passt zu FastAPI/asyncio Pattern aus Hauptprojekt |
| Frontend Chat | **matrix-js-sdk** | Browser-only, WASM Rust crypto (vodozemac), Sliding Sync |
| Mobile | **Element X, FluffyChat, Syphon, Beeper** | Alle offiziellen Apps + Custom Homeserver URL — Push via Elements Sygnal automatisch |
| E2EE Crypto | **vodozemac** (Rust) | WASM im Browser, native Node.js binding für OpenClaw-Pattern |
| Registration | **Token-basiert** | Go-Backend generiert Tokens, User registriert mit Username+Token |

---

## Verzeichnisstruktur

```
D:\matrix/
├── specs/                    # Diese Docs
│   ├── 00-overview.md
│   ├── 01-homeserver.md
│   ├── 02-go-appservice.md
│   ├── 03-python-agent-bridge.md
│   ├── 04-nextjs-chat.md
│   ├── 05-devstack.md
│   ├── 06-e2ee.md
│   ├── 07-mobile.md          # Element X, FluffyChat, Syphon, Beeper + Tunnel-Optionen
│   ├── 08-tooling.md
│   ├── 09-privacy.md         # Privacy-Konfiguration Tuwunel + Dendrite
│   ├── 10-portierung.md      # Portierungsstrategie → tradeview-fusion
│   ├── 11-bore-tunnel.md     # bore Tunnel, eigener Relay, Production-Optionen ohne VPS
│   └── 12-connectivity.md    # Tunnel, VPS, IPv6, DynDNS, Entscheidungsbaum Production
│
├── tools/                    # Binaries und Hilfstools (nicht committed)
│   ├── tuwunel               # Linux Binary v1.5.1 (via WSL1 starten)
│   ├── dendrite.exe          # Windows Native Binary v0.13.8 (Fallback)
│   ├── nats-server.exe       # NATS Message Bus v2.10.27
│   ├── ngrok.exe             # Tunnel (Account nötig)
│   ├── cloudflared.exe       # Cloudflare Tunnel (kein Account)
│   ├── bore.exe              # Open-Source Tunnel bore.pub (kein Account)
│   ├── genkey.go             # ED25519 Key-Generator für Dendrite
│   └── dendrite-src/         # Go Source (für Rebuild)
│
├── homeserver/               # Homeserver Config + Daten
│   ├── tuwunel.toml          # Tuwunel Dev-Config
│   ├── tuwunel.prod.toml     # Tuwunel Production-Vorlage
│   ├── dendrite.yaml         # Dendrite Dev-Config (Windows Fallback)
│   ├── dendrite_key.pem      # ED25519 Private Key für Dendrite (generiert)
│   ├── registration.yaml     # Appservice-Registration (von Go generiert)
│   └── data/                 # Datenbankdateien (gitignored)
│
├── go-appservice/            # Go: mautrix-go Appservice
│   ├── go.mod + go.sum
│   ├── .golangci.yml
│   ├── .env + .env.example
│   ├── cmd/appservice/main.go
│   └── internal/
│       ├── config/
│       ├── handler/          # Matrix Event Handler
│       ├── intent/           # Agent Intent-Wrapper
│       ├── natsbridge/       # NATS Bridge
│       └── registration/     # registration.yaml Generator
│
├── python-agent-bridge/      # Python: matrix-nio Bot
│   ├── pyproject.toml
│   ├── .env + .env.example
│   ├── agent_bridge/
│   │   ├── app.py            # FastAPI Einstieg
│   │   ├── matrix_client.py  # matrix-nio Client
│   │   ├── agent_client.py   # HTTP → Agent-Service (SSE parsing)
│   │   ├── config.py
│   │   └── models.py
│   ├── scripts/
│   │   └── register_bot.py   # Einmalig: Bot-Account registrieren
│   └── tests/
│
├── nextjs-chat/              # Next.js: Embedded Chat UI
│   ├── package.json
│   ├── biome.json + tsconfig.json
│   ├── .env.local + .env.local.example
│   ├── src/
│   │   ├── components/matrix/ # MatrixProvider, MatrixChat, RoomList, Timeline,
│   │   │                      # Message, MessageComposer, RoomHeader, TypingIndicator
│   │   ├── lib/matrix/
│   │   │   ├── client.ts      # matrix-js-sdk Singleton
│   │   │   ├── types.ts       # ResolvedMessage, RoomInfo
│   │   │   └── hooks/         # useMatrixClient, useRooms, useTimeline, useTyping
│   │   └── app/
│   │       ├── matrix/page.tsx           # dynamic(ssr:false)
│   │       └── api/matrix/credentials/   # Credentials API Route
│   └── ...
│
└── scripts/
    ├── devstack.ps1          # Alle 5 Services starten (auto-erkennt Dendrite vs Tuwunel)
    └── setup-users.ps1       # Einmalig: Alice + Bot registrieren, .env Dateien befüllen
```

---

## Agent-Identitäten Strategie

**Orchestrator-Agent** hat eine Matrix-User-ID:
```
@trading-agent:matrix.local
```

Sub-Agents arbeiten intern via NATS/Python — für den User unsichtbar.
Der Orchestrator koordiniert und antwortet unter seiner Matrix-Identität.

**Optionale Erweiterung:** 2-3 spezialisierte Agents mit eigener ID, wenn User-seitig relevant (z.B. `@risk-monitor:domain` der proaktiv warnt).

---

## Abgrenzung zu bestehendem Agent-Chat

**Strategie: Option B — Matrix parallel zum bestehenden Agent-Chat**

- Bestehender SSE/WebSocket Agent-Chat in der Web-App bleibt unverändert
- Matrix wird als separater Kommunikationskanal eingeführt
- Gleicher Agent, zwei Kanäle: Web-Chat-Widget + Matrix (→ Mobile)
- Schrittweiser Rollout, kein Breaking Change
- Phase 2: ggf. Web-Agent-Chat auf Matrix migrieren

---

## Portierungs-Checkliste (später → Hauptprojekt)

- [ ] Go Appservice → `go-backend/internal/matrix/`
- [ ] Python Agent Bridge → `python-backend/python-agent/agent/matrix_channel.py`
- [ ] Next.js Chat Komponenten → `src/components/matrix/`
- [ ] Homeserver-Entscheidung: Tuwunel auf Linux-Server (Production), Dendrite für Windows-Dev
- [ ] OIDC Integration mit bestehendem NextAuth
- [ ] Production Registration: Eigener Flow statt `-really-enable-open-registration` (siehe spec/01)
