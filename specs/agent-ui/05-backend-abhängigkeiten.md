# Agent Chat UI — Backend-Abhaengigkeiten

**Status:** Aktiv
**Stand:** 06.04.2026 — python-backend konsolidiert (Port 8094), NATS-Bridge aktiv (exec-05 abgeschlossen)

## Uebersicht

Die Agent Chat UI ist ein Frontend-Modul das ueber BFF-Routes mit dem Backend kommuniziert.
Der Stack ist konsolidiert in vier Schichten:

```
Next.js BFF (/api/agent/*)             ← agent-chat/src/app/api/
    ↓
Go Appservice (Port 8090)              ← go-appservice/internal/handlers/http/
    ↓
Python Agent Service (Port 8094)       ← python-backend/agent/app.py
    ↓
LLM Provider (Anthropic / OpenAI / OpenRouter / Ollama / LiteLLM)
```

---

## Go Appservice

**Repo:** `D:\matrix\go-appservice` (Matrix Appservice + Agent Gateway)
**Port:** 8090
**Rolle:** Routing, Auth, SSE-Proxy, Tool-Approval Queue, E2EE

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/v1/agent/chat` | POST | SSE Stream Proxy zu Python Agent |
| `/api/v1/agent/approve` | POST | Tool-Call Approve/Deny weiterleiten |
| `/api/v1/agent/tools/*` | GET/POST | Tool State Queries + Mutations |
| `/api/v1/audio/synthesize` | POST | TTS Request → Python |
| `/api/v1/audio/transcribe` | POST | STT Request → Python |
| `/api/v1/mcp/*` | * | MCP Server Proxy |
| `/api/v1/memory/kg/*` | * | Knowledge Graph Proxy |
| `/api/v1/memory/episode*` | * | Episode Storage Proxy |
| `/_matrix/app/v1/*` | * | Matrix Appservice Protocol |
| `/health` | GET | Health Check |

**UIMessage Stream Protocol:**
- Header: `x-vercel-ai-ui-message-stream: v1`
- Go setzt diesen Header damit das ai SDK v6 den Stream korrekt parsen kann
- Error-Format: `{ errorText: "msg" }` (nicht `{ error: "msg" }`)

Header durchgereicht: `x-user-role`, `x-auth-user`, `x-request-id`.

---

## Python Agent Service

**Repo:** `D:\matrix\python-backend/agent/`
**Port:** 8094
**Rolle:** LangGraph Agent Loop, LLM-Calls, Tool-Execution, Memory, Sandbox

### Aktive Subpackages

| Package | Zweck | Slice |
|---|---|---|
| `agent/graph/` | LangGraph StateGraph (6 Nodes) | exec-10 |
| `agent/tools/` | 15 Tools (chart, portfolio, memory, sandbox, canvas, file_analyze, ...) | exec-09 |
| `agent/sandbox/` | OpenSandbox Manager + Config | exec-12 Phase 1 |
| `agent/audit/` | Audit Logging (PG / JSON Lines) | exec-12 Phase 2.1 |
| `agent/consent/` | Consent Engine + Rate Limiter | exec-12 Phase 2.2-2.3 |
| `agent/middleware/` | Sanitizer, Template Validator, Loop Detection | exec-12 Phase 2.4-2.5 |
| `agent/memory/` | Hindsight Memory (4 Networks) | exec-11 |
| `agent/skills/` | 3-Tier Skills + MetaClaw Evolver | exec-10 Phase 3 |
| `agent/a2a/` | Inter-Agent Delegation | exec-10 Phase 4 |
| `agent/roles.py` | 6 Trading Rollen mit Completion Gates | exec-10 |
| `agent/mcp_server.py` | FastMCP Server (Standalone Port 8095 oder mounted in 8094) | exec-09 |

### Endpoint-Highlights (`agent/app.py`)

| Endpoint | Method | Phase |
|---|---|---|
| `/api/v1/agent/chat` | POST/SSE | 22d/AC7 |
| `/api/v1/agent/context` | POST | 10a.4 |
| `/api/v1/agent/working-memory/*` | GET/POST | 10c (M5 Scratchpad) |
| `/api/v1/agent/tools/*` | GET/POST | 10e |
| `/api/v1/audio/transcribe` | POST | 22f |
| `/api/v1/audio/synthesize` | POST | 22f |
| `/api/v1/skills` | GET/PUT/POST | 10 Ph5 |
| `/mcp/*` | * | exec-09 |

---

## LLM Provider

`AGENT_PROVIDER` schaltet zwischen den Providern um:

| Provider | ENV-Wert | SDK |
|---|---|---|
| Anthropic | `anthropic` (default) | `anthropic>=0.40` |
| OpenAI | `openai` | `openai>=1.50` |
| OpenAI-compatible | `openai-compatible` | `openai>=1.50` + `OPENAI_BASE_URL` (Ollama, vLLM, OpenRouter, Azure) |
| LiteLLM Multi-Provider | `AGENT_USE_LITELLM=true` | `litellm>=1.50` |

### Empfohlene Models

| Model | ID | Use Case |
|-------|----|---|
| Claude Opus 4.6 | `claude-opus-4-6` | Hauptmodell, komplexe Trading-Analyse |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Standard, schnellere Antworten |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | One-Shot Completions, Indikator-Tooltips |

Auswahl erfolgt ueber Model-Selector im `AgentChatToolbar`.

### Structured Output

`instructor>=1.3` als Pydantic-Wrapper fuer Tool-Call Parsing — funktioniert mit allen
Providern.

---

## Memory Engine (Hindsight)

**Package:** `python-backend/memory_engine/` + `agent/memory/`
**SDK:** `hindsight-api-slim>=0.4.17` (BYOE: Bring Your Own Embeddings/Reranker/DB)

| Komponente | Implementation |
|---|---|
| 4 Networks | Retain / Recall / Reflect / Consolidate |
| Vector Store | Chroma (default) / LanceDB / pgvector |
| Knowledge Graph | Kuzu / FalkorDB / SQLite |
| Episodic Store | SQLite (`agent_episodes` table) |
| Embeddings | `sentence-transformers all-MiniLM-L6-v2` (384 dim, CPU-only) |
| Database | PostgreSQL (Hindsight Schema) |

---

## Sandbox (OpenSandbox)

**Package:** `python-backend/agent/sandbox/`
**SDK:** `opensandbox>=0.1.6` + `opensandbox-code-interpreter>=0.1.2`

| Sandbox-Typ | Image | Timeout | Use Case |
|---|---|---|---|
| `CODE_SANDBOX` | `opensandbox/code-interpreter:v1.0.2` | 10 min | Data Analysis, Custom Indicators |
| `BACKTEST_SANDBOX` | `opensandbox/code-interpreter:v1.0.2` | 30 min | Backtesting (Resource-intensive) |
| `BROWSER_SANDBOX` | Custom `Dockerfile.browser` mit Playwright | 10 min | Web Scraping, JS-heavy Sites |

Sprachen: Python, JavaScript, TypeScript, Bash, Go, Java.

---

## Voice AI Pipeline (LiveKit Agents)

**Package:** `python-backend/voice/`

| Komponente | Default | Alternativen |
|---|---|---|
| STT | `faster-whisper` (lokal) | `openai-whisper` (Cloud) |
| TTS | `piper-tts` (lokal, 23 voices) | `openai-tts` / `kokoro` (self-hosted) |
| VAD | Silero VAD (lokal) | — |
| LLM | Geroutet via `AGENT_PROVIDER` | — |

ENV-Switch: `AGENT_STT_PROVIDER`, `AGENT_TTS_PROVIDER`.

---

## NATS Pipeline (exec-05 — abgeschlossen)

```
Matrix Room (E2EE) → Tuwunel → Go Appservice (decrypt) → NATS → Python Bridge → Agent Service
                                                                       ↓
                                Python Bridge ← NATS ← Agent Reply ← Streaming SSE
                                       ↓
                                Tuwunel ← Go Appservice (encrypt) ← Reply Text
```

Subjects:
- `matrix.message.inbound` — decrypted Klartext vom Go Appservice
- `matrix.message.reply` — Antwort vom Python Bridge zurueck zum Go Appservice

Details: `03-python-agent-bridge.md`, `13-e2ee-agent-architecture.md`.

---

## Environment Variables

Vollstaendige Liste in `00-overview.md`. Hier nur Agent-relevant:

```env
# LLM Provider
AGENT_PROVIDER=anthropic|openai|openai-compatible
AGENT_MODEL=claude-sonnet-4-6
AGENT_UTILITY_MODEL=claude-haiku-4-5
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=                    # Ollama: http://localhost:11434/v1
AGENT_USE_LITELLM=false

# Voice
AGENT_STT_PROVIDER=whisper-local
AGENT_TTS_PROVIDER=piper

# Backend Connections
AGENT_SERVICE_URL=http://127.0.0.1:8094
NATS_URL=nats://127.0.0.1:4222

# Database (Hindsight Memory + Audit)
HINDSIGHT_DB_URL=postgresql://user:pass@localhost:5432/hindsight
AUDIT_DB_URL=                       # Falls anders als HINDSIGHT_DB_URL

# Frontend
NEXT_PUBLIC_GO_GATEWAY_URL=http://127.0.0.1:8090

# Agent Behavior
AGENT_MAX_ITERATIONS=10
AGENT_TOOL_TIMEOUT_SEC=30
AGENT_SUMMARIZE_THRESHOLD=0.7
```

---

## Aktivierte vs. vorbereitete Features

### Aktiv
- Streaming SSE Chat (exec-08)
- Multi-Provider LLM (exec-08)
- Voice Pipeline (LiveKit Agents)
- LangGraph + 6 Trading Rollen (exec-10)
- 15 Tools registriert (exec-09)
- Hindsight Memory (exec-11 Phase 1)
- OpenSandbox + Browser Sandbox (exec-12 Phase 1)
- Audit + Consent + Sanitizer + RBAC (exec-12 Phase 2)
- MCP Server (exec-09)

### Scaffold/Vorbereitet (siehe `FUTURE_IDEAS.md`)
- Memory Service Standalone (Port 8093)
- Remote A2A Agents
- RL Trainer (`AGENT_RL_ENABLED=false` default)
- Skill Evolution (`AGENT_SKILL_EVOLUTION=false` default)
