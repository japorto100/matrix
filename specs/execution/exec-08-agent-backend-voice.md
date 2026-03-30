# exec-08: Agent Backend + Voice AI Pipeline + Frontend SOTA

**Datum:** 30.03.2026
**Status:** Geplant
**Abhaengig von:** exec-06 (Agent Chat UI Integration)

---

## Warum

Das Matrix-Isolationsprojekt hat aktuell:
- `python-agent-bridge/` — Matrix Bot Bridge (matrix-nio, NATS, kein LLM)
- `llm-mock/` — Mock Agent (Port 8094, kein echter LLM-Call)
- Agent Chat UI (`agent-chat/`) — fertiges Frontend, braucht echtes Backend

Es fehlt:
- Echter Agent mit LLM-Calls, Tool-Execution, Memory
- Echtzeit Voice AI (STT/LLM/TTS über WebRTC statt HTTP)
- Provider-agnostisches Setup (nicht an einen LLM/STT/TTS Provider gebunden)

---

## Phase 1: Python Backend Konsolidierung

### Ziel
`python-agent-bridge/` und `python-agent` (Kopie aus Hauptprojekt) zu einem `python-backend/` zusammenlegen.

### Quelle
`D:\tradingview-clones\tradeview-fusion\python-backend\python-agent\` (41 Python-Dateien, pyproject.toml)

### Struktur

```
python-backend/                       ← Konsolidiert
├── pyproject.toml                    ← Unified Dependencies
├── bridge/                           ← Aus python-agent-bridge/
│   ├── matrix_client.py              ← Matrix nio Bot (Rooms lesen/schreiben)
│   ├── agent_client.py               ← HTTP Client → Agent Service
│   └── config.py
├── agent/                            ← Aus Hauptprojekt python-agent/agent/
│   ├── app.py                        ← FastAPI Agent Service (Port 8094)
│   ├── loop.py                       ← run_agent_loop() — Streaming LLM Calls
│   ├── streaming.py                  ← SSE Stream Builder
│   ├── context.py                    ← Conversation Context Management
│   ├── context_assembler.py          ← Context Window Assembly
│   ├── roles.py                      ← System Prompts / Agent Roles
│   ├── guards.py                     ← Safety Guards
│   ├── errors.py                     ← Error Types
│   ├── http_client.py                ← Shared HTTP Client
│   ├── extensions.py                 ← Agent Extensions
│   ├── validators/                   ← Input Validation
│   │   └── trading.py
│   ├── tools/                        ← Tool Registry + Definitionen
│   │   ├── registry.py
│   │   ├── base.py
│   │   ├── chart_state.py
│   │   ├── portfolio.py
│   │   ├── memory_tool.py
│   │   ├── geomap.py
│   │   └── search.py
│   ├── working_memory.py             ← In-Session Memory
│   └── memory_client.py              ← Memory Service Client
├── context/                          ← Aus Hauptprojekt python-agent/context/
│   ├── merge.py                      ← Context Merging
│   ├── relevance.py                  ← Relevance Scoring
│   └── token_budget.py               ← Token Budget Management
├── memory/                           ← Aus Hauptprojekt python-agent/memory/
│   └── app.py                        ← Memory Service (Port 8093)
├── memory_engine/                    ← Aus Hauptprojekt
│   └── episodic_store.py             ← Episodic Memory Storage
├── voice/                            ← NEU: LiveKit VoicePipelineAgent
│   ├── pipeline.py                   ← VoicePipelineAgent Setup
│   ├── worker.py                     ← LiveKit Agent Worker Entry Point
│   └── config.py                     ← Voice Provider Config
├── mock/                             ← Aus llm-mock/
│   └── mock_agent.py                 ← LLM Mock (kein API Key noetig)
├── api/                              ← Bridge FastAPI (Port 8097)
│   └── app.py
├── scripts/
│   └── register_bot.py
└── tests/
```

### Schritte

- [x] **1.1:** `python-agent/` aus Hauptprojekt kopiert nach `D:\matrix\python-backend\`
  - Quelle: `D:\tradingview-clones\tradeview-fusion\python-backend\python-agent\`
  - `agent/`, `context/`, `memory/`, `memory_engine/`, `scripts/`, `tests/`
- [x] **1.2:** `python-agent-bridge/agent_bridge/` → `python-backend/bridge/` verschoben
- [x] **1.3:** `llm-mock/mock_agent.py` → `python-backend/mock/mock_agent.py` verschoben
- [x] **1.4:** Unified `pyproject.toml` erstellt (`uv sync` erfolgreich)
- [x] **1.5:** Imports angepasst (devstack2, setup-scripts)
- [x] **1.6:** `dev-stack2.ps1` angepasst auf `python-backend/`
- [x] **1.7:** Alte Ordner geloescht + `.gitignore` aktualisiert:
  - `python-agent-bridge/` → Inhalt in `python-backend/bridge/`
  - `llm-mock/` → Inhalt in `python-backend/mock/`
  - `devstack.ps1` Referenzen auf alte Pfade entfernen

### Provider-Agnostik (aus Hauptprojekt uebernommen)

Das Hauptprojekt hat bereits ein provider-agnostisches Setup:

```
AGENT_PROVIDER = anthropic | openai | openai-compatible
AGENT_MODEL    = model-id-override (optional)

openai-compatible deckt ab:
  - OpenRouter (OPENAI_BASE_URL=https://openrouter.ai/api/v1)
  - Ollama (OPENAI_BASE_URL=http://localhost:11434/v1)
  - vLLM, LM Studio, Azure
  - Jeder OpenAI-API-kompatible Endpoint

litellm (optional, AGENT_USE_LITELLM=true):
  - Multi-Provider Router: ein API fuer alle Provider
  - Fallback-Chains, Load Balancing, Caching
```

---

## Phase 1b: Go Gateway — Agent Handler Integration

### Ziel
Go Appservice (`go-appservice/`) um Agent Gateway Funktionalitaet erweitern.
Uebernommen aus Hauptprojekt `go-backend/`, vereinfacht (nur HTTP, kein gRPC/IPC).

### Uebernommene Handler

| Handler | Route | Funktion |
|---------|-------|----------|
| `agent_chat_handler.go` | `/api/v1/agent/chat` | SSE Proxy → Python Agent (Vercel AI Data Stream Protocol) |
| `agent_chat_handler.go` | `/api/v1/agent/approve` | Tool-Call Approve/Deny |
| `agent_audio_handler.go` | `/api/v1/audio/transcribe` | STT Proxy → Python Agent |
| `agent_audio_handler.go` | `/api/v1/audio/synthesize` | TTS Proxy → Python Agent |
| `agent_tool_proxy_handler.go` | `/api/v1/agent/tools/*` | Tool-Call GET/POST Proxy |
| `memory_handler.go` | `/api/v1/memory/*` | KG, Episodes, Vector Search, Health |

### Uebernommene Clients (vereinfacht, nur HTTP)

| Client | Package | Zweck |
|--------|---------|-------|
| `agentservice/client.go` | `internal/connectors/agentservice` | HTTP Client → Python Agent (Port 8094) |
| `memory/client.go` | `internal/connectors/memory` | HTTP Client → Memory Service (Port 8093) |
| `helpers.go` | `internal/handlers/http` | writeJSON, decodeJSONBody, clampInt |

### Nicht uebernommen (vereinfacht)
- IPC/gRPC Dual-Transport (nur HTTP, kein gRPC)
- Capability Registry / RBAC Middleware
- Redis Cache fuer Memory
- OTel/Tracing (spaeter)

### Config-Erweiterung
- `AGENT_SERVICE_URL` (Default: `http://127.0.0.1:8094`)
- `MEMORY_SERVICE_URL` (Default: `http://127.0.0.1:8093`)

### Struktur (neu)

```
go-appservice/
├── cmd/appservice/main.go               ← Bestehendes Entry Point
├── internal/
│   ├── config/config.go                 ← +AgentServiceURL, +MemoryServiceURL
│   ├── handler/server.go                ← +Agent/Audio/Memory Routes im Mux
│   ├── handlers/http/                   ← NEU: Agent Gateway Handler
│   │   ├── helpers.go
│   │   ├── agent_chat_handler.go
│   │   ├── agent_audio_handler.go
│   │   ├── agent_tool_proxy_handler.go
│   │   └── memory_handler.go
│   ├── connectors/                      ← NEU: Service Clients
│   │   ├── agentservice/client.go
│   │   └── memory/client.go
│   ├── crypto/                          ← Bestehend: E2EE (Olm/Megolm)
│   ├── intent/                          ← Bestehend: Agent Sender
│   ├── natsbridge/                      ← Bestehend: NATS Bridge
│   └── registration/                    ← Bestehend: Registration Gen
```

### Schritte
- [x] **1b.1:** Handler + Clients + Helpers erstellt
- [x] **1b.2:** Routes in server.go Mux verdrahtet
- [x] **1b.3:** Config um AgentServiceURL + MemoryServiceURL erweitert
- [x] **1b.4:** Go Build erfolgreich (`go build -tags goolm ./cmd/appservice/`)

### Verify-Gate Phase 1b
- [ ] `GET /health` zeigt Appservice + Agent Service Status
- [ ] `POST /api/v1/agent/chat` proxied SSE Stream korrekt
- [ ] `POST /api/v1/audio/synthesize` liefert audio/mpeg zurueck
- [ ] Matrix E2EE + Agent Gateway laufen im gleichen Prozess

---

## Phase 2: Agent Chat Backend (Text)

### Ziel
Agent Chat UI (`agent-chat/`) mit echtem Backend verbinden.

### Schritte

**Schritte 2.1–2.4 sind Verify-Gates (manuelle Tests nach DevStack-Start):**

### API Routes Integration

- [ ] **2.5:** `agent-chat/api/` Routes nach `nextjs-chat/src/app/api/` kopieren
  - `api/agent/chat/route.ts` → SSE Streaming Proxy
  - `api/agent/approve/route.ts` → Tool Approval
  - `api/agent/completion/route.ts` → One-Shot Completion
  - `api/audio/synthesize/route.ts` → TTS (HTTP-Fallback, bleibt auch nach Phase 3)
  - `api/audio/transcribe/route.ts` → STT (HTTP-Fallback, bleibt auch nach Phase 3)

### Verify-Gate Phase 2
- [ ] Agent Chat UI → BFF → Go Gateway → Python Agent → Claude → SSE Response
- [ ] Tool-Call im Chat → Approval Card → Approve → Tool-Result
- [ ] Mock-Agent: Chat funktioniert ohne API Key
- [ ] HTTP TTS/STT funktioniert als Fallback (unabhaengig von Phase 3 Voice)

---

## Phase 3: Voice AI Pipeline (LiveKit Agents)

### Ziel
Echtzeit Voice Chat ueber WebRTC statt HTTP (200-500ms Latenz statt 3-8s).

### Architektur

```
Browser (LiveKit Room)
    │ WebRTC Audio Stream
    ▼
LiveKit SFU (Port 7880) ← gleicher Server wie Matrix Calls
    │
    ▼
Python VoicePipelineAgent (LiveKit Agent Worker)
    ├── STT: faster-whisper (Open Source, lokal)
    ├── LLM: provider-agnostisch (gleiche Config wie Text-Agent)
    └── TTS: Piper TTS (Open Source, lokal)
    │
    │ WebRTC Audio Stream
    ▼
Browser hoert Agent-Antwort in Echtzeit
```

### Provider-Agnostik fuer Voice

**STT (Speech-to-Text):**

```
AGENT_STT_PROVIDER = whisper-local | openai | google

whisper-local (default, empfohlen):
  - faster-whisper Backend (Open Source, WASM/CUDA)
  - Lokal, kein Cloud-Service
  - 90+ Sprachen, ~200-500ms Latenz

openai:
  - OpenAI Whisper API
  - Cloud, benoetigt OPENAI_API_KEY

google:
  - Google Cloud Speech-to-Text
  - Cloud, benoetigt GOOGLE_API_KEY
```

**TTS (Text-to-Speech):**

```
AGENT_TTS_PROVIDER = piper | openai | kokoro

piper (default, empfohlen):
  - Piper TTS (Open Source, lokal, ~100ms)
  - Sehr leichtgewichtig
  - Community-maintained Voice Models

openai:
  - OpenAI TTS API (alloy, echo, fable, onyx, nova, shimmer)
  - Cloud, hohe Qualitaet

kokoro:
  - Kokoro TTS (Open Source, hohe Qualitaet)
  - Lokal, benoetigt Modell-Download
```

**LLM:**

```
Gleiche Config wie Text-Agent:
AGENT_PROVIDER = anthropic | openai | openai-compatible
AGENT_MODEL    = claude-sonnet-4-6 (default)
```

### LiveKit Agent Worker

```python
# python-backend/voice/pipeline.py
from livekit.agents import AutoSubscribe, WorkerOptions, cli
from livekit.agents.voice import VoicePipelineAgent
from livekit.plugins import silero  # VAD (Voice Activity Detection)

# Provider-agnostische Imports
from voice.providers import get_stt, get_tts, get_llm

async def entrypoint(ctx):
    agent = VoicePipelineAgent(
        vad=silero.VAD.load(),
        stt=get_stt(),     # → faster-whisper / openai / google (je nach ENV)
        llm=get_llm(),     # → anthropic / openai / litellm (je nach ENV)
        tts=get_tts(),     # → piper / openai / kokoro (je nach ENV)
    )
    await agent.start(ctx.room)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        auto_subscribe=AutoSubscribe.AUDIO_ONLY,
    ))
```

### Frontend Integration

```typescript
// Neuer Hook: useAgentVoice.ts
// Verbindet direkt mit LiveKit Room (kein MatrixRTC noetig)
// Agent ist LiveKit-Teilnehmer, kein Matrix-User

const { joinVoice, leaveVoice, isConnected } = useAgentVoice(threadId);
// → Erstellt LiveKit Room "agent-voice-{threadId}"
// → Python Worker subscribed automatisch
// → Browser sendet Audio via WebRTC
// → Agent antwortet via WebRTC Audio
```

### Schritte

- [x] **3.1:** `livekit-agents` + Plugins in pyproject.toml (bereits in Phase 1)
- [x] **3.2:** `voice/providers.py` — Provider-Factory (`get_stt()`, `get_tts()`, `get_llm()`, `get_vad()`)
  - Provider-agnostisch: STT/TTS/LLM via ENV umschaltbar
  - Fallback-Chain: whisper-local → openai, piper → kokoro → openai, anthropic → openai
- [x] **3.3:** `voice/pipeline.py` — `create_voice_agent()` baut VoicePipelineAgent
- [x] **3.4:** `voice/worker.py` — LiveKit Agent Worker Entry Point (`python -m voice.worker`)
- [x] **3.5:** `dev-stack2.ps1` — Voice Worker als optionaler Service (`-WithVoice` Flag)
- [x] **3.6:** `useAgentVoice.ts` — Frontend Hook (LiveKit Room connect, `agent-voice-{threadId}`)
- [x] **3.7:** Agent Chat UI — Voice-Modus Toggle (Text ↔ Voice) in AgentChatToolbar
  - Mic/MicOff Icon + "Voice"/"Text" Label
  - `voiceActive` + `onVoiceToggle` Props
- [x] **3.8:** lk-jwt-service: Unterscheidung Matrix Calls vs Agent Voice
  - Matrix Calls: Auth via Matrix OpenID Token (Tuwunel validiert)
  - Agent Voice: Auth via separatem Mechanismus (Agent Chat Session Token oder API Key)
  - Beide nutzen gleichen LiveKit SFU, aber verschiedene Room-Prefixes:
    - Matrix: `!roomId:server` (MatrixRTC Session)
    - Agent: `agent-voice-{threadId}` (direkter LiveKit Room)
  - lk-jwt-service muss beide Token-Typen akzeptieren oder zweite Instanz
  - Evaluieren: ein lk-jwt-service mit Routing oder zwei Instanzen (Matrix Port 8080, Agent Port 8081)

### Verify-Gate Phase 3
- [ ] Voice-Button in Agent Chat → LiveKit Room erstellt
- [ ] User spricht → Agent hoert (STT) → Agent denkt (LLM) → Agent antwortet (TTS)
- [ ] Latenz < 500ms (End-of-Speech → Start-of-Response)
- [ ] Provider-Wechsel: STT/TTS/LLM via ENV umschaltbar ohne Code-Aenderung
- [ ] Gleicher LiveKit SFU bedient Matrix Calls UND Agent Voice parallel

---

## Phase 4: Agent Chat Frontend Packages (SOTA 2026)

### Package-Upgrades

- [x] **4.1:** `react-syntax-highlighter` → `react-shiki` in `AgentChatMarkdown.tsx`
  - VS Code Engine (oneDark → one-dark-pro Theme), ShikiHighlighter Component
- [x] **4.2:** `framer-motion` → `motion/react` in `AgentChatMessage.tsx`
- [x] **4.3:** `auto-animate` in `AgentChatThread.tsx` Message-Liste eingebaut (useAutoAnimate Hook)
- [x] **4.4:** `zustand` fuer GlobalChatContext (ersetzt React Context, provider-free)
- [x] **4.4b:** `jotai` fuer feingranularen State (`context/atoms.ts`)
  - `collapsedToolsAtom` — per-tool collapse (kein Re-Render der ganzen Liste)
  - `usageMapAtom` — per-message Token/Cost Tracking
  - `toggleToolCollapseAtom` — write-only Atom fuer Toggle
  - `useChatSession.ts` auf Jotai Atome umgestellt
- [x] **4.5:** AI SDK v6 DevTools + next.config.ts
  - `@ai-sdk/devtools` Package installiert
  - `lib/ai-devtools.ts` — `withDevTools()` Middleware Wrapper (lazy, nur Development)
  - DevTools Viewer: `npx @ai-sdk/devtools` → http://localhost:4983
  - In `dev-stack2.ps1` als optionaler Service (`-DevTools` Flag)
  - `next.config.ts` fuer agent-chat erstellt (isoliert, eigener Port)
- [x] **4.6:** `toModelOutput` in Python Backend eingebaut
  - `TradingTool.to_model_output(result)` — Override-Hook in `agent/tools/base.py`
  - Default: gibt volles Result zurueck (keine Aenderung)
  - Override: Tool kann gekuerztes Result ans LLM senden (z.B. 500-char Summary)
  - `agent/loop.py` — UI bekommt volles Result (SSE), LLM bekommt `to_model_output()` (Context)
- [x] **4.7:** `jotai` eingebaut (siehe 4.4b — collapsedTools + usageMap Atome)
  - Zustand: globaler App-State (wenige grosse Stores)
  - Jotai: feingranularer State (per-message collapse, per-tool approval)
  - Beide zusammen nutzbar, kein Konflikt
- [x] **4.8:** ~~`tiptap-ai-autocomplete`~~ → durch Novel abgedeckt (AI Autocomplete inkludiert)
- [x] **4.9:** `assistant-ui` parallel aufgesetzt
  - `@assistant-ui/react@latest` + `@assistant-ui/react-ai-sdk@1.3.16` installiert
  - `AssistantUIThread.tsx` — Prototyp-Component mit Primitives (Thread, Message, Composer, ActionBar, BranchPicker)
  - Nutzt `useVercelUseChatRuntime()` als Adapter fuer ai SDK v6
  - Tailwind-gestyled, parallel zu unserem AgentChatThread nutzbar
  - Evaluationskriterien (offen — beim Live-Test vergleichen):
    - [ ] Kann es AgentChatThread/Message/Composer ersetzen?
    - [ ] Styling-Kontrolle mit shadcn/Tailwind ausreichend?
    - [ ] Tool-Call Rendering + Approval Flow?
    - [ ] Attachment Support?
    - [ ] Performance-Vergleich (Re-Renders, Streaming)
- [x] **4.10:** `Novel` Editor als Agent Output-Editor eingebaut
  - `novel@1.0.2` installiert
  - `AgentOutputEditor.tsx` — Notion-style Block-Editor fuer lange Agent-Outputs
  - Slash-Commands (/table, /code, /heading), AI Autocomplete, Markdown Export
  - Nicht fuer Chat-Composer — nur fuer editierbare Agent-Outputs (Reports, Analysen)

### Agent Chat package.json aktualisieren

- [x] **4.11:** `agent-chat/package.json` mit neuen Packages aktualisiert:
  - `react-shiki` statt `react-syntax-highlighter`
  - `motion` statt `framer-motion`
  - `zustand` hinzufuegen
  - `auto-animate` (`@formkit/auto-animate`) hinzufuegen
  - `tiptap-ai-autocomplete` hinzufuegen (falls Evaluation positiv)
  - `@types/react-syntax-highlighter` entfernen

### Layout-Integration evaluieren (fuer spaetere Zusammenfuehrung)

- [ ] **4.12:** Evaluieren wie Agent Chat in nextjs-chat eingebunden wird
  - GlobalChatProvider + GlobalChatOverlay in (shell)/layout.tsx
  - Sheet/Split/Rail Modes
  - Tab-Wechsel [Matrix] [Agent]
  - **Vorerst isoliert** — Integration erst wenn Matrix + Agent zusammengefuehrt werden

### Shared Components (Matrix Chat ↔ Agent Chat)

- [ ] **4.13:** Markdown-Rendering Core extrahieren → `shared/Markdown.tsx`
  - Gemeinsam: GFM, Sanitize (rehype-sanitize), Code Blocks (Shiki), Linkify
  - Matrix-spezifisch: Matrix Permalinks, Mention Pills
  - Agent-spezifisch: Think-Blocks, Citations, JSON Renderer
- [ ] **4.14:** ImagePreviewModal → `shared/ImagePreviewModal.tsx`
- [x] **4.15:** rehype-sanitize in AgentChatMarkdown.tsx eingebaut (`rehypePlugins={[rehypeSanitize]}`)
- [x] **4.16:** `@livekit/track-processors` → verschoben nach exec-04 (Matrix Calls, nicht Agent UI)

### Verify-Gate Phase 4
- [ ] Shiki: Code-Block in Agent Chat zeigt Syntax Highlighting mit VS Code Theme
- [ ] Shiki: TypeScript/JSX wird korrekt highlighted (nicht nur Keywords)
- [ ] Agent Chat Markdown ist HTML-sanitized (XSS-Versuch mit `<script>` wird gefiltert)
- [ ] Zustand: `useGlobalChat()` funktioniert ohne Provider-Wrapper
- [ ] Zustand: open/close/toggleMode aendern State korrekt
- [ ] Jotai: Tool-Collapse toggelt ohne dass die ganze Message-Liste re-rendert
- [ ] Jotai: usageMap zeigt Tokens pro Nachricht korrekt
- [ ] auto-animate: Neue Nachrichten faden sanft ein
- [ ] motion: Paced Turn Groups animieren korrekt (kein Unterschied zu framer-motion)
- [ ] AI SDK v6 DevTools: LLM Calls + Token Usage sichtbar im Browser
- [ ] toModelOutput: Grosse Tool-Outputs werden fuer Model gekuerzt, UI zeigt volles Ergebnis
- [ ] next.config.ts: Agent Chat startet isoliert auf eigenem Port

### E2EE fuer Agent Voice (spaeter)

Aktuell kein Fokus. Wird evaluiert wenn Matrix Chat + Agent Chat zusammengefuehrt werden:
- Matrix Calls: E2EE via MatrixKeyProvider (bereits implementiert)
- Agent Voice: Erstmals ohne E2EE (Agent ist vertrauenswuerdiger Teilnehmer im lokalen Netz)
- Spaeter: LiveKit E2EE auch fuer Agent Voice Rooms aktivieren wenn oeffentliches Deployment

---

## DevStack Aenderungen

### Port Map (aktualisiert)

```
Port   Service                           Gestartet von
─────  ──────────────────────────────    ─────────────
8448   Tuwunel Homeserver                devstack.ps1
4222   NATS                              devstack.ps1
7880   LiveKit SFU (Calls + Voice)       devstack.ps1
8080   lk-jwt-service                    devstack.ps1 (WSL)
8090   Go Appservice                     devstack.ps1
8093   Memory Service (Python)           devstack.ps1 (optional)
8094   Agent Service (Python)            devstack.ps1
8097   Bridge Service (Python)           devstack.ps1
3000   Next.js Chat UI                   devstack.ps1
```

### Neue devstack.ps1 Flags

```
-MockAgent     # Mock statt echtem Agent (Port 8094, kein API Key)
-WithVoice     # LiveKit Voice Worker starten (Phase 3)
-NoLiveKit     # LiveKit SFU + lk-jwt deaktivieren
```

---

## Hinweis: agent_chat_ui_delta.md

Rein frontend-bezogene Aenderungen (Phase 4: Shiki, motion, zustand, auto-animate, assistant-ui,
tiptap-ai-autocomplete, Novel, shared components, rehype-sanitize, package.json updates) werden
zusaetzlich als **neue ACs und Verify-Gates** in `agent-chat/agent_chat_ui_delta.md` eingetragen.

Das Delta-Dokument (Rev. 31, Kopie aus Hauptprojekt) ist der execution-owner fuer den
Agent Chat UI Layer. Neue Frontend-Features die hier in exec-08 Phase 4 geplant werden,
muessen dort als Checkboxen + Verify-Gates nachgefuehrt werden damit:
- Nichts doppelt oder widersprüchlich dokumentiert ist
- Das Delta-Dokument die Single Source of Truth fuer Agent Chat UI bleibt
- Verify-Gates konsistent an einer Stelle geprueft werden koennen

**Vorgehen:** exec-08 Phase 4 definiert WAS gemacht wird. agent_chat_ui_delta.md trackt
die Umsetzung mit ACs (z.B. AC110+) und Verify-Gates (z.B. AC.V87+).

---

## Hinweis: Memory Service

Memory Service (Port 8093, KuzuDB/ChromaDB/LanceDB) ist in der Struktur enthalten
aber wird in einem **spaeteren Slice** separat behandelt. Nicht Teil von exec-08.
Die Dependencies (kuzu, chromadb, sentence-transformers, lancedb) bleiben in pyproject.toml
fuer spaetere Aktivierung.

---

## Abhaengigkeitsgraph

```
exec-04 (UI Rework) ✅
    └── LiveKit SFU + lk-jwt-service installiert
        └── exec-08 Phase 3 (Voice) nutzt gleichen SFU

exec-05 (NATS E2EE Pipeline)
    └── exec-08 Phase 1 (bridge/ Modul in python-backend)

exec-06 (Agent Chat UI Integration)
    └── exec-08 Phase 2 (Backend fuer Agent Chat)
    └── exec-08 Phase 4 (Frontend Packages)

exec-08 Phase 1 → Phase 2 → Phase 3 → Phase 4
(Backend Setup → Text Chat → Voice AI → Frontend Polish)
```
