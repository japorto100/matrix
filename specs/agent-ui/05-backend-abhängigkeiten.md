# Agent Chat UI — Backend-Abhängigkeiten

> Stand: 29.03.2026

## Übersicht

Die Agent Chat UI ist ein Frontend-Modul das über BFF-Routes mit dem Backend kommuniziert.
Das Backend besteht aus drei Schichten:

```
Next.js BFF (/api/agent/*)
    ↓
Go Gateway (Port 8090)
    ↓
Python Agent Service (Port 8097)
    ↓
LLM Provider (Anthropic / OpenAI)
```

---

## Go Gateway

**Repo:** `D:\matrix\go-appservice` (Matrix Appservice + Agent Gateway)
**Port:** 8090
**Rolle:** Routing, Auth, SSE-Proxy, Tool-Approval Queue

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/v1/agent/chat` | POST | SSE Stream: Message → Python → LLM → Response |
| `/api/v1/agent/approve` | POST | Tool-Call Approve/Deny weiterleiten |
| `/api/v1/agent/audio/synthesize` | POST | TTS Request → Python |
| `/api/v1/agent/audio/transcribe` | POST | STT Request → Python |
| `/_matrix/app/v1/*` | * | Matrix Appservice Protocol (HS ↔ Appservice) |

**UIMessage Stream Protocol:**
- Header: `x-vercel-ai-ui-message-stream: v1`
- Go setzt diesen Header damit das ai SDK v6 den Stream korrekt parsen kann
- Error-Format: `{ errorText: "msg" }` (nicht `{ error: "msg" }`)

---

## Python Agent Service

**Repo:** `D:\matrix\python-agent-bridge`
**Port:** 8097
**Rolle:** Agent-Loop, LLM-Calls, Tool-Execution, Memory

| Feature | Status | Beschreibung |
|---------|--------|-------------|
| Chat Handler | ✅ | `run_agent_loop()` — Streaming Agent Response |
| Tool Execution | ✅ | Python-seitige Tools (Search, Calculation, etc.) |
| TTS | ✅ | Text-to-Speech Synthese |
| STT | ✅ | Speech-to-Text via Whisper |
| Thread-Persistenz | Offen | AgentEpisode — Chat-Verlauf speichern/laden |
| Memory/KG | Offen | Langzeit-Gedächtnis über Sessions hinweg |

---

## LLM Provider

| Model | ID | Max Context | Cost (Input/Output per 1M) |
|-------|----|-------------|---------------------------|
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 200K | $3 / $15 |
| Claude Opus 4.6 | `claude-opus-4-6` | 200K | $15 / $75 |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | 200K | $0.80 / $4 |

Auswahl erfolgt über Model-Selector im AgentChatToolbar.
Haiku wird für One-Shot Completions (Indikator-Tooltips) verwendet.

---

## NATS Pipeline (exec-05)

Für die Integration von Agent Chat mit Matrix Rooms braucht der Agent Zugriff auf
verschlüsselte Matrix-Nachrichten. Dies wird über die NATS E2EE Pipeline gelöst:

```
Matrix Room (E2EE) → Go Appservice (Crypto-Gateway) → NATS → Python Agent
```

Der Go Appservice entschlüsselt Nachrichten (als trusted Appservice) und leitet sie
über NATS an den Python Agent weiter. Antworten gehen den umgekehrten Weg.

**Status:** Geplant (exec-05)

---

## Environment Variables

| Variable | Service | Default |
|----------|---------|---------|
| `NEXT_PUBLIC_GO_GATEWAY_URL` | BFF → Go | `http://127.0.0.1:8090` |
| `ANTHROPIC_API_KEY` | Python → LLM | — |
| `OPENAI_API_KEY` | Python → LLM (optional) | — |
