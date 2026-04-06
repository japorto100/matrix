# E2EE Agent Architecture — Ist-Zustand

**Status:** Aktiv
**Stand:** 06.04.2026 — Phase 3 (Go als einziger E2EE-Endpunkt, NATS aktiv, matrix-nio entfernt)

## Uebersicht

Dieses Dokument beschreibt den aktuellen Zustand der Verschluesselungs- und
Nachrichtenfluss-Architektur zwischen User, Homeserver, Go Appservice, Python Backend
und LLM. Fuer das Trust-Modell siehe `06-e2ee.md`.

---

## Architektur (Ist-Zustand seit exec-05)

```
┌──────────┐  E2EE  ┌──────────┐  E2EE  ┌──────────────────────┐
│ Browser  │───────►│ Tuwunel  │───────►│  Go Appservice       │
│(Next.js) │        │(Homesvr) │        │  (mautrix-go +       │
│ vodozemac│        │ RocksDB  │        │   goolm + Cross-     │
│ Rust WASM│        │          │        │   Signing)           │
└──────────┘        └──────────┘        └──────────┬───────────┘
                                                    │ decrypted
                                                    │ Klartext
                                                    ▼
                                        ┌──────────────────────┐
                                        │  NATS (port 4222)    │
                                        │  matrix.message.     │
                                        │    inbound / reply   │
                                        └──────────┬───────────┘
                                                    │
                                                    ▼
                                        ┌──────────────────────┐
                                        │  Python Bridge       │
                                        │  (NATS Consumer,     │
                                        │   Port 8097)         │
                                        └──────────┬───────────┘
                                                    │ HTTP SSE
                                                    ▼
                                        ┌──────────────────────┐
                                        │  Python Agent (8094) │
                                        │  LangGraph + Tools + │
                                        │  Memory + Sandbox    │
                                        └──────────────────────┘
```

**Encrypted Backend, Bridged Endpoints (E2BE)** — Go Appservice ist die einzige
Komponente mit Crypto. Python sieht nur Klartext via NATS. Browser hat eigene
unabhaengige E2EE-Schicht (vodozemac WASM) fuer User-zu-User Nachrichten.

---

## Komponenten-Status

### Browser (Next.js Chat)
- Eingeloggt mit Device-spezifischem Token
- matrix-js-sdk v41 mit Rust Crypto (vodozemac → WASM)
- `initRustCrypto()` aktiv → IndexedDB Key Store
- Cross-Signing via `useCrossSigning` Hook + `CrossSigningSetup`-Komponente
- QR-Code + SAS-Emoji Verification
- Phase 3 abgeschlossen — Phase 4 Production Hardening in `FUTURE_IDEAS.md`

### Tuwunel (Homeserver)
- `encryption_enabled_by_default_for_room_type = "off"` (Client entscheidet pro Raum)
- Speichert ausschliesslich verschluesselte Events (kann nicht mitlesen)
- TURN/STUN konfiguriert (metered.ca + Cloudflare)
- LiveKit als RTC Transport (well_known.rtc_transports)

### Go Appservice
- Laeuft auf :8090, verbunden mit Tuwunel via Appservice-Protokoll
- `MATRIX_E2EE_ENABLED=true` → kann verschluesselte Events lesen und senden
- OlmMachine + goolm (Pure-Go, kein CGO)
- `ensureCrossSigning()` Bootstrap → Seeds in `data/cross_signing_seeds.json` (0o600)
- Bot-User: `@appservice-bot:matrix.local`
- Agent-Namespace (exklusiv): `@agent-*:matrix.local`
- NATS Producer: `matrix.message.inbound` (decrypted Klartext)
- NATS Subscriber: `matrix.message.reply` → encrypted reply zurueck nach Tuwunel
- HTTP Proxy zu Agent Service (Port 8094) fuer SSE Chat (Frontend Path)

### Python Bridge (`python-backend/bridge/`)
- Laeuft auf :8097
- Reiner NATS Consumer — **keine Matrix Dependency mehr**
- matrix-nio wurde in exec-05 vollstaendig entfernt
- Subscribe `matrix.message.inbound` → HTTP SSE Call zu Agent Service → Publish `matrix.message.reply`
- Stateless, keine Schluesselverwaltung

### Python Agent Service (`python-backend/agent/`)
- Laeuft auf :8094
- LangGraph StateGraph mit 6 Nodes (memory_recall → llm_call → approval → tool_execute → loop → memory_retain)
- 15 Tools registriert (chart, portfolio, memory, sandbox, canvas, file_analyze, ...)
- 6 Trading Rollen (FUNDAMENTALS, TECHNICAL, SENTIMENT, RESEARCHER, TRADER, RISK_MANAGER)
- Hindsight Memory Engine (4 Networks: Retain/Recall/Reflect/Consolidate)
- exec-12 Phase 2: Audit, Consent, Sanitizer, Template Validator, Rate Limiter

### NATS (port 4222)
- Aktiv genutzt fuer Matrix-Bridge
- Subjects: `matrix.message.inbound`, `matrix.message.reply`
- Spaeter erweiterbar fuer Multi-Source Bridges (exec-05b)

---

## E2EE-Status pro Raum

| Raum-Typ | Verschluesselt | Grund |
|---|---|---|
| DM (`is_direct: true`) | ✅ Client kann aktivieren | Default in Element X |
| Private Group | ✅ Client kann aktivieren | Default-Empfehlung |
| Public Room (`#general`) | ❌ | Nicht sinnvoll fuer offene Raeume |
| Admin Room | ❌ | Server-Admin Operationen |

---

## Konfiguration

### Go Appservice (`go-appservice/.env.development`)
```env
MATRIX_E2EE_ENABLED=true
MATRIX_CRYPTO_DB_PATH=./data/crypto.sqlite3
MATRIX_CRYPTO_PICKLE_KEY=<32-byte hex>
MATRIX_KEY_BACKUP_PASSWORD=<passphrase>
MATRIX_BOT_USER_ID=@appservice-bot:matrix.local
MATRIX_AGENT_PREFIX=agent-
MATRIX_AGENT_USER_ID=@agent-trading:matrix.local
NATS_URL=nats://127.0.0.1:4222
MENTION_ONLY_IN_GROUPS=true
```

### Python Backend (`python-backend/.env`)
```env
NATS_URL=nats://127.0.0.1:4222
AGENT_SERVICE_URL=http://127.0.0.1:8094
AGENT_TIMEOUT_SEC=120
AGENT_USER_ID=@agent-trading:matrix.local
BRIDGE_HOST=127.0.0.1
BRIDGE_PORT=8097
```

### Tuwunel (`homeserver/tuwunel.toml`)
```toml
[global]
default_room_version = "12"
encryption_enabled_by_default_for_room_type = "off"  # Client entscheidet
allow_federation = false

# MatrixRTC + LiveKit
[[global.well_known.rtc_transports]]
type = "livekit"
livekit_service_url = "http://192.168.1.34:8080"

# TURN
turn_uris = [
    "stun:stun.cloudflare.com:3478",
    "turn:a.relay.metered.ca:443?transport=tcp",
]
```

---

## Vergleich: Vorher (exec-04) vs. Jetzt (exec-05+)

| Aspekt | Vorher | Jetzt |
|---|---|---|
| Matrix Endpunkte | 2 (Go + Python matrix-nio) | 1 (Go only) |
| Crypto Stores | 2 (Go + matrix-nio[e2e]) | 1 (Go SQLite) |
| Cross-Signing | Keine | Aktiv (`ensureCrossSigning`) |
| NATS | Tot (kein Subscriber) | Aktiv (Bridge subscribed) |
| Python Dependencies | matrix-nio[e2e], libolm | nats-py (pure Python) |
| Code-Komplexitaet Bridge | ~300 LoC | ~80 LoC |

---

## Trust-Modell

Siehe `06-e2ee.md` fuer Details. Kurz:
- Go Appservice ist **die** vertrauenswuerdige Identitaet (Master/Self-Signing/User-Signing Keys)
- Browser-Geraete vertrauen Go via Cross-Signing Verifikation (QR + SAS)
- Python Bridge braucht **keine** Crypto-Identitaet — Klartext via NATS
- Andere User-Geraete verifizieren mit Go-Identitaet via Standard Matrix Verification Flow
