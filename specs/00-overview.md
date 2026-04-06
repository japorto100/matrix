# Matrix Integration — Project Overview

**Status:** Aktiv
**Stand:** 06.04.2026

## Ziel

Matrix-Protokoll als Kommunikationsschicht in das Hauptprojekt (tradeview-fusion)
integrieren. Dieses Repo ist das **isolierte Testsetup** — wenn alles funktioniert,
wird es portiert.

### Konkrete Use Cases

1. **User ↔ User Chat** — Matrix-Räume direkt in der Web-App eingebettet
2. **User ↔ Agent Chat** — Python-Agent nimmt an Matrix-Räumen teil, hat eigene Matrix-ID
3. **Gruppen-Chats** — Mehrere User + Agent(s) in einem Raum
4. **Mobile** — User chattet über Element X App mit anderen Usern und mit Agents
5. **E2EE** — Verschlüsselung auch wenn fremde Homeserver in Föderationsumgebung

---

## Architektur-Übersicht

```
┌────────────────────────────────────────────────────────────────────┐
│              Matrix Homeserver (Tuwunel oder Dendrite)             │
│         token-based registration, kein Telefon, OIDC-ready        │
└────────────────────────┬───────────────────────────────────────────┘
                         │ Federation (optional, default OFF)
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
  Go Appservice    Python Backend    Element X (Mobile)
  (mautrix-go)     (FastAPI)         iOS + Android
  port 8090        port 8094 / 8097  ↕ OIDC Login
         │               │
         │  E2BE         │
         │  (Go ist      │
         │   einziger    │
         │   Matrix-     │
         │   Endpunkt)   │
         │               │
         └───────┬───────┘
                 │ NATS (matrix.message.inbound / .reply)
                 ▼
         Python Backend (konsolidiert)
         ├── agent/   — LangGraph Agent + Tools + Memory + Sandbox
         ├── bridge/  — NATS Consumer ↔ Agent
         ├── voice/   — LiveKit Voice AI Pipeline
         └── mock/    — Mock Agent fuer Tests
                 │
                 ▼
         Next.js Frontend (port 3000)
         "use client" MatrixChat + AgentChat Komponenten
         matrix-js-sdk + shadcn/ui + Tailwind v4
```

---

## Stack-Entscheidungen

| Komponente | Technologie | Begründung |
|---|---|---|
| Homeserver (Primär) | **Tuwunel** v1.5.1 (Rust) | ~50–150 MB RAM idle, Single Binary, RocksDB eingebettet, kein PostgreSQL nötig |
| Homeserver (Windows Fallback) | **Dendrite** v0.13 (Go) | Kompiliert nativ für Windows (.exe), kein WSL nötig, SQLite, dev-tauglich |
| Go Matrix-Schicht | **mautrix-go** v0.22.0 | Appservice API, Intent API für virtuelle User-IDs, **goolm** (Pure Go, kein libolm) |
| Python Backend | **FastAPI** + LangGraph | Konsolidierter Service: agent + bridge + voice + mock in `python-backend/` |
| Matrix↔Agent Bridge | **NATS** Pub/Sub | Go ist einziger Matrix-Endpunkt (E2BE-Pattern). matrix-nio entfernt (exec-05). |
| Frontend Chat | **matrix-js-sdk** v41 | Browser-only, WASM Rust crypto (vodozemac), Sliding Sync (MSC3575) |
| Mobile | **Element X, FluffyChat, Syphon, Beeper** | Alle offiziellen Apps + Custom Homeserver URL — Push via Sygnal automatisch |
| E2EE Crypto (Browser) | **vodozemac** (Rust → WASM) | matrix-js-sdk Rust Crypto, MSC4153 Cross-Signing |
| E2EE Crypto (Go) | **goolm** (Pure Go) | Kein CGO, kein libolm — Build via `-tags goolm` |
| Voice/Video Calls | **MatrixRTC + LiveKit** | LiveKit als RTC Transport (well_known.rtc_transports) |
| Voice AI Pipeline | **LiveKit Agents** + Silero VAD | STT: faster-whisper / OpenAI · TTS: piper / OpenAI / Kokoro |
| Multi-Agent Orchestrierung | **LangGraph** + Trading Roles | 6 Trading Rollen, Subgraphs, Approval-Gate, Memory-Recall/Retain |
| Memory Engine | **Hindsight** (4 Networks) | Retain/Recall/Reflect/Consolidate, PostgreSQL+pgvector, BYOE |
| Sandbox Code Execution | **OpenSandbox** (Alibaba) | Apache 2.0, Code-Interpreter Plugin, Docker-Runtime, exec-12 |
| MCP Server | **FastMCP** | exposiert Trading-Tools standardisiert (exec-09) |
| Registration | **Token-basiert** | Go-Backend generiert Tokens, User registriert mit Username+Token |

---

## Verzeichnisstruktur

```
D:\matrix/
├── specs/                    # Architektur- und Konzeptdokumentation
│   ├── 00-overview.md        # Diese Datei
│   ├── 01-homeserver.md ... 16-security.md
│   ├── agent-ui/             # Agent-Chat UI Specs
│   ├── execution/            # Operative Execution Slices (exec-*.md)
│   ├── FUTURE_IDEAS.md       # Noch nicht umgesetzte Ideen
│   └── archive/ (in execution/)
│
├── tools/                    # Binaries und Hilfstools (gitignored)
│   ├── tuwunel               # Linux Binary v1.5.1
│   ├── dendrite.exe          # Windows Native Binary v0.13 (Fallback)
│   ├── nats-server.exe       # NATS Message Bus v2
│   ├── ngrok.exe / cloudflared.exe / bore.exe  # Tunnel-Optionen
│   └── genkey.go             # ED25519 Key-Generator für Dendrite
│
├── homeserver/               # Homeserver Config + Daten
│   ├── tuwunel.toml          # Aktive Tuwunel Dev-Config (RocksDB, Privacy hardened)
│   ├── tuwunel.prod.toml     # Production-Vorlage
│   ├── tuwunel.example.toml  # Voll dokumentiertes Template
│   ├── dendrite.yaml         # Dendrite Dev-Config (Windows Fallback)
│   ├── registration.yaml     # Appservice-Registration (von Go generiert)
│   └── data/                 # RocksDB / SQLite Daten (gitignored)
│
├── go-appservice/            # Go: mautrix-go Appservice (Port 8090)
│   ├── go.mod (Go 1.26, mautrix-go v0.22.0, modernc.org/sqlite, NATS)
│   ├── cmd/appservice/main.go
│   └── internal/
│       ├── config/           # ENV Loader
│       ├── handler/          # Matrix Event Handler (m.room.message, encrypted, member)
│       ├── handlers/http/    # HTTP Proxies: agent_chat, agent_tool, audio, mcp, memory
│       ├── intent/           # AgentSender API (virtuelle @agent-* User)
│       ├── natsbridge/       # NATS Pub/Sub: matrix.message.inbound / .reply
│       ├── crypto/           # OlmMachine Wrapper (E2EE, goolm)
│       ├── connectors/       # HTTP Clients zu Agent + Memory Service
│       └── registration/     # registration.yaml Generator
│
├── python-backend/           # Konsolidiertes Python Backend (alle Services)
│   ├── pyproject.toml        # uv-managed (Python 3.11+)
│   ├── alembic/              # DB Migrations (agent.audit_events Schema)
│   ├── agent/                # Agent Service (Port 8094) — exec-09/10/11/12
│   │   ├── app.py            # FastAPI: SSE Chat, Tools, Audio, Skills, MCP
│   │   ├── graph/            # LangGraph: 6 Nodes + Subgraphs + Orchestrator
│   │   ├── tools/            # 15 Tools (chart, portfolio, memory, sandbox, canvas, ...)
│   │   ├── memory/           # Hindsight Integration (4 Networks)
│   │   ├── sandbox/          # OpenSandbox Manager + Config
│   │   ├── audit/            # exec-12 Phase 2.1: structured audit logs
│   │   ├── consent/          # exec-12 Phase 2.2: consent + rate limiter
│   │   ├── middleware/       # sanitizer, template_validator, completion_gates, ...
│   │   ├── skills/           # 3-Tier (global/team/personal) + MetaClaw Evolver
│   │   ├── a2a/              # Inter-Agent Delegation (exec-10 Phase 4)
│   │   ├── roles.py          # 6 Trading Rollen (FUNDAMENTALS, TECHNICAL, ...)
│   │   └── mcp_server.py     # FastMCP Server
│   ├── bridge/               # Matrix↔Agent Bridge (Port 8097, NATS Consumer)
│   ├── voice/                # LiveKit Voice AI Worker
│   ├── memory_engine/        # Hindsight Memory Engine (KG/Vector/Episodic)
│   ├── memory/               # Memory Service Scaffold (Port 8093, optional)
│   ├── mock/                 # Mock Agent fuer Tests (Port 8094)
│   ├── context/              # Context Engineering (relevance, token budget)
│   ├── shared/               # app_factory, cache_adapter, config
│   └── scripts/              # smoke_falkordb, smoke_pgvector, register_bot
│
├── nextjs-chat/              # Next.js: Embedded Matrix + Agent Chat UI (Port 3000)
│   ├── package.json          # Next.js 16, React 19, matrix-js-sdk 41, Tailwind 4
│   ├── components.json       # shadcn/ui Config (46 Komponenten)
│   ├── src/
│   │   ├── components/matrix/   # 45+ Matrix-Komponenten (Threads, Spaces, Polls, ...)
│   │   ├── components/ui/       # shadcn/ui Komponenten
│   │   ├── lib/matrix/          # client.ts, types.ts, hooks/ (18 Custom Hooks)
│   │   └── app/
│   │       ├── matrix/page.tsx
│   │       └── api/matrix/      # credentials, media, preview
│   └── ...
│
├── agent-chat/               # Agent Chat UI Feature-Modul (wird in nextjs-chat integriert)
│   ├── src/
│   │   ├── AgentChatPanel.tsx   # Hauptkomponente
│   │   ├── components/          # AssistantUI + Tambo + tldraw Canvas + Novel Editor
│   │   ├── hooks/               # useChatSession, useMcpTools, useWebMcpBridge, ...
│   │   └── app/api/agent/       # /chat, /approve, /completion (BFF zu Go Gateway)
│   └── package.json             # CopilotKit, Tambo, MCP, AssistantUI
│
├── docker-compose.yml        # podman-compose / docker-compose
│                             # Profiles: default | dev | sandbox | prod
│
└── scripts/
    ├── devstack.ps1          # Alle Services starten (auto-erkennt Dendrite vs Tuwunel)
    ├── setup-users.ps1       # Einmalig: Alice + Bot registrieren
    └── harden-env.py         # Default-Credentials in .env ersetzen (exec-12 Ph2.7)
```

---

## Agent-Identitäten Strategie

**Orchestrator-Agent** hat eine Matrix-User-ID:
```
@agent-trading:matrix.local
```

Sub-Agents (Trading Rollen: fundamentals, technical, sentiment, researcher, trader,
risk_manager) arbeiten intern via LangGraph + A2A — fuer den User unsichtbar.
Der Orchestrator koordiniert und antwortet unter seiner Matrix-Identität.

**Namespace:** `@agent-.*:matrix.local` (exklusiv via registration.yaml)
Nur der Go Appservice kann User in diesem Namespace anlegen.

**Optionale Erweiterung:** 2-3 spezialisierte Agents mit eigener Matrix-ID,
wenn User-seitig relevant (z.B. `@agent-risk-monitor:domain` der proaktiv warnt).

---

## Service-Ports (Default)

| Service | Port | Zweck |
|:---|:---|:---|
| Tuwunel Homeserver | 8448 | Matrix Client-Server + Federation API |
| Go Appservice | 8090 | Matrix Appservice + HTTP Proxy zum Backend |
| Python Agent | 8094 | LangGraph Agent + SSE Chat + Tools + Audio |
| Python Bridge | 8097 | NATS Consumer (matrix.message.inbound) |
| Memory Service | 8093 | Optional, Scaffold (Hindsight Memory Engine) |
| MCP Server | 8095 | Standalone MCP Server (oder mounted in 8094) |
| NATS | 4222 | Message Bus (Go ↔ Python) |
| Next.js Chat | 3000 | Frontend |
| LiveKit | 7880 (WS) / 8080 (HTTP) | Voice/Video SFU |
| OpenSandbox Server | 8080 / 8100 | Code Execution Backend (profile: sandbox) |

---

## Abgrenzung zu bestehendem Agent-Chat

**Strategie: Option B — Matrix parallel zum bestehenden Agent-Chat**

- Bestehender SSE/WebSocket Agent-Chat in der Web-App bleibt unveraendert
- Matrix wird als separater Kommunikationskanal eingefuehrt
- Gleicher Agent, zwei Kanaele: Web-Chat-Widget (`agent-chat/`) + Matrix (`nextjs-chat/`)
- Schrittweiser Rollout, kein Breaking Change
- Beide UIs teilen sich das gleiche Python Backend (Port 8094)

---

## Portierungs-Checkliste (später → Hauptprojekt tradeview-fusion)

Siehe `10-portierung.md` fuer Details.

- [ ] Go Appservice → `go-backend/internal/matrix/`
- [ ] Python Backend → `python-backend/agent/matrix_channel.py` (oder als separater Service)
- [ ] Next.js Chat Komponenten → `src/components/matrix/` + `src/components/agent/`
- [ ] Homeserver-Entscheidung: Tuwunel auf Linux-Server (Production), Dendrite fuer Windows-Dev
- [ ] OIDC Integration mit bestehendem NextAuth
- [ ] Production Registration: Eigener Flow statt offener Registrierung

---

## Status der Execution Slices

Vollstaendige Liste mit Status: `specs/execution/README.md`

| Slice | Inhalt | Status |
|---|---|---|
| exec-05 | NATS E2EE Pipeline (Go↔Python) | ✅ |
| exec-06 | Agent Chat Integration | ✅ |
| exec-09 | MCP / Generative UI / A2A | ✅ |
| exec-10 | Multi-Agent (Trading Roles) | ✅ |
| exec-11 | Hindsight Memory Engine | ✅ Phase 1 |
| exec-12 | OpenSandbox + Security Hardening | ✅ Phase 1+2 |
| exec-13 | UI + Knowledge Graph Extensions | Geplant |
| exec-14 | PDDL Formale Plan-Validierung | Geplant |
