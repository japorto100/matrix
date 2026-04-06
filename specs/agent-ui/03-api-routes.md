# Agent Chat UI — API Routes (BFF Layer)

**Status:** Aktiv
**Stand:** 06.04.2026

## Uebersicht

Next.js API Routes als BFF (Backend-for-Frontend) Proxy zwischen Browser und Go Gateway.
Browser spricht nie direkt mit Go/Python — alle Requests laufen über `/api/agent/*` und `/api/audio/*`.

```
Browser → Next.js BFF (/api/agent/chat) → Go Gateway (/api/v1/agent/chat) → Python Agent → LLM
```

---

## Endpoints

### POST /api/agent/chat — SSE Streaming

Haupt-Endpoint für Agent-Interaktion. Proxy zum Go Gateway mit SSE Stream.

**Request:**
```json
{
  "message": "Analysiere AAPL",
  "threadId": "optional-thread-id",
  "agentId": "optional-agent-id",
  "model": "claude-opus-4-6",
  "attachments": [{ "base64": "...", "mime_type": "image/png", "name": "chart.png" }],
  "reasoningEffort": "high"
}
```

**Response:** SSE Stream
- Header: `x-vercel-ai-ui-message-stream: v1` (damit DefaultChatTransport den Stream parst)
- Frames: `text-delta`, `tool-call`, `message-metadata`, `error`
- Error-Rewrite: Python `{ error: "msg" }` → `{ errorText: "msg" }` (ai v6 Kompatibilität)

**Go Gateway:** `NEXT_PUBLIC_GO_GATEWAY_URL` / Default `http://127.0.0.1:8090`

---

### POST /api/agent/approve — Tool Approval

Bestätigung oder Ablehnung von Tool-Calls die `confirmLevel: "confirm"` haben.

**Request:**
```json
{
  "toolCallId": "tc_abc123",
  "decision": "approve",
  "threadId": "optional"
}
```

**Response:** 204 No Content

---

### POST /api/agent/completion — Single-Shot

One-Shot Completion ohne Thread (z.B. Indikator-Erklärungen via Tooltip).

**Request:**
```json
{ "prompt": "Was bedeutet RSI 72.3 für AAPL?" }
```

**Verhalten:**
- Prepend System-Prompt: "You are a concise trading analyst..."
- Hardcoded Model: `claude-haiku-4-5-20251001`
- Kein threadId, kein Streaming-UI — nur Plain-Text Stream
- Max 500 Zeichen Prompt

---

### POST /api/audio/synthesize — Text-to-Speech

TTS Proxy zum Go Gateway → Python Agent.

**Request:**
```json
{
  "text": "Die RSI-Analyse zeigt...",
  "voice": "alloy",
  "model": "optional"
}
```

**Response:** `audio/mpeg` Binary (MP3)
- Max 4096 Zeichen Text
- Voices: alloy, echo, fable, onyx, nova, shimmer

---

### POST /api/audio/transcribe — Speech-to-Text

STT Proxy zum Go Gateway → Python Agent (Whisper).

**Request:**
```json
{
  "audio_base64": "base64-encoded-audio",
  "mime_type": "audio/webm",
  "language": "de"
}
```

**Response:**
```json
{ "ok": true, "text": "Transkribierter Text" }
```

---

## Environment

| Variable | Default | Beschreibung |
|----------|---------|-------------|
| `NEXT_PUBLIC_GO_GATEWAY_URL` | `http://127.0.0.1:8090` | Go Gateway Base-URL |

## Dateien

```
agent-chat/src/app/api/
├── agent/
│   ├── chat/route.ts         ← SSE Streaming Proxy
│   ├── approve/route.ts      ← Tool Approval
│   └── completion/route.ts   ← One-Shot Completion
└── audio/
    ├── synthesize/route.ts   ← TTS
    └── transcribe/route.ts   ← STT
```

Bei Integration in nextjs-chat werden diese nach `nextjs-chat/src/app/api/agent/`
und `nextjs-chat/src/app/api/audio/` kopiert (exec-06).

---

## Backend Endpoints (Go Appservice + Python Agent)

Vollstaendige Endpoint-Liste:

| Frontend BFF | Go Appservice (Proxy) | Python Agent (Backend) |
|---|---|---|
| `/api/agent/chat` | `:8090/api/v1/agent/chat` | `:8094/api/v1/agent/chat` |
| `/api/agent/approve` | `:8090/api/v1/agent/approve` | `:8094/api/v1/agent/approve` |
| `/api/agent/completion` | `:8090/api/v1/agent/completion` | `:8094/api/v1/agent/completion` |
| `/api/audio/synthesize` | `:8090/api/v1/audio/synthesize` | `:8094/api/v1/audio/synthesize` |
| `/api/audio/transcribe` | `:8090/api/v1/audio/transcribe` | `:8094/api/v1/audio/transcribe` |
| — | `:8090/api/v1/agent/tools/*` | `:8094/api/v1/agent/tools/*` |
| — | `:8090/api/v1/mcp/*` | `:8094/mcp/*` (mounted sub-app) |
| — | `:8090/api/v1/memory/kg/*` | `:8093/api/v1/memory/kg/*` |
| — | `:8090/api/v1/memory/episode*` | `:8093/api/v1/memory/episode*` |

Header durchgereicht: `x-user-role`, `x-auth-user`, `x-request-id`.
