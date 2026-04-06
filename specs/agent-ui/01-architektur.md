# Agent Chat UI — Architektur

**Status:** Aktiv
**Stand:** 06.04.2026 — Feature-Modul `agent-chat/` aktiv, Integration in nextjs-chat via exec-06

## Konzept

Produktive Agent-Chat-Oberflaeche fuer LLM-gestuetzte Interaktion (Trading-Analyse,
Tool-Ausfuehrung, Recherche). Gebaut als Feature-Modul (`agent-chat/`), wird in
`nextjs-chat` integriert (exec-06).

Ursprung: `tradeview-fusion/src/features/agent-chat/` (Rev. 31, 100+ ACs abgearbeitet).

---

## Stack

| Schicht | Technologie | Version |
|---------|-------------|---------|
| Chat SDK | Vercel AI SDK v6 (`ai` + `@ai-sdk/react`) | 6.0.134 / 3.0.136 |
| Transport | `DefaultChatTransport` → BFF SSE Proxy | — |
| Markdown | `react-markdown` + `remark-gfm` + `react-syntax-highlighter` | 10.1.0 / 4.0.1 / 16.1.1 |
| Animation | `framer-motion` (paced message fade-in) | 12.38.0 |
| URL-State | `nuqs` (Thread-ID in URL) | 2.8.9 |
| UI | shadcn/ui (Button, Badge, Dialog, Sheet, ContextMenu) | — |
| Icons | `lucide-react` | 0.525.0 |

---

## Komponentenbaum

```
AgentChatPanel (Orchestrator)
├── useChatSession()                    ← ai SDK v6 useChat Wrapper
│   └── DefaultChatTransport → /api/agent/chat (BFF SSE)
│       └── Go Gateway → Python Agent → Anthropic/OpenAI
│
├── AgentChatHeader                     ← Titel + Context-Chip + Close
├── AgentChatToolbar                    ← Model-Selector, Reasoning-Effort, TTS, Mode-Toggle
├── AgentChatEventRail                  ← Status-Badge (idle/live/degraded) + Context-Pressure-Bar
├── AgentChatThread                     ← Message-Liste + Scroll-to-Bottom + Empty-State
│   └── AgentChatMessage (pro Nachricht, memo'd)
│       ├── AgentChatMarkdown           ← GFM, Syntax-Highlighting, Think-Block, Citations
│       ├── AgentChatToolBlock          ← 7-State Tool-Call UI + Approval-Card
│       ├── AgentChatTtsButton          ← Text-to-Speech per Nachricht
│       ├── AgentChatSources            ← Citations-Panel mit Cards + Dialog
│       ├── CopyButton, ReasoningBlock
│       └── ImagePreviewModal           ← Lightbox für Attachments
├── AgentChatReconnectBanner            ← Reconnect-Status (auto-dismiss)
├── AgentChatErrorBanner                ← Fehler-Banner mit Dismiss
└── AgentChatComposer (forwardRef)      ← Input + Mic + Attachments + Drag-Drop
    ├── useSpeechInput                  ← Web Speech API
    ├── useMediaRecorderInput           ← MediaRecorder Fallback
    ├── useAttachments                  ← File-Staging + Base64 Konvertierung
    └── AttachmentPreviewStrip          ← Thumbnail-Strip + Remove-Button
```

---

## Globale Integration

```
(shell)/layout.tsx
├── GlobalChatProvider                  ← State: open, mode, badge, chatContext
├── GlobalChatOverlay                   ← Sheet-Overlay (side=right, modal=false)
│   └── AgentChatPanel (sheet mode)
└── SplitChatShell                      ← Inline-Panel (split/rail modes)
    ├── Page Children
    └── AgentChatPanel (split: 420px / rail: 240px)
```

### Display-Modes

| Mode | Darstellung | Wann |
|------|-------------|------|
| `sheet` | Overlay von rechts (shadcn Sheet) | Default, blockiert nicht |
| `split` | 420px Panel rechts, pushed Content | Toggle in Toolbar |
| `rail` | 240px persistent Sidebar | Toggle in Toolbar |

### Context-Injection

Seiten können Kontext in den Chat injizieren:
```ts
const { setChatContext } = useGlobalChat();
setChatContext(`Symbol: AAPL, Timeframe: 1D, RSI: 72.3`);
// → Erscheint als Chip im Header, wird an Agent gesendet
```

---

## Datenfluss

```
User tippt → AgentChatComposer
  → useChatSession.send(text, attachments)
    → DefaultChatTransport.prepareSendMessagesRequest()
      → POST /api/agent/chat (Next.js BFF)
        → Go Appservice (Port 8090) /api/v1/agent/chat (SSE Proxy)
          → Python Agent Service (Port 8094) /api/v1/agent/chat
            → LangGraph run_agent_loop() (memory_recall → llm_call → approval → tool_execute)
              → Anthropic/OpenAI/OpenRouter/Ollama API
          ← SSE Frames: text-delta, tool-call, message-metadata, error
        ← UIMessage Stream (x-vercel-ai-ui-message-stream: v1)
      ← useChat() aktualisiert messages[]
    ← AgentChatThread rendert neue Nachricht
  ← AgentChatMessage zeigt Text/Tools/Sources
```

---

## State-Management

| State | Wo | Persistenz |
|-------|-----|-----------|
| Chat open/mode/badge | `GlobalChatContext` | In-Memory (React Context) |
| Thread-ID | `nuqs` URL Query (`?t=xxx`) | URL |
| Messages | `useChat()` (ai SDK) | In-Memory (Session) |
| Usage/Cost Map | `useChatSession` (Map) | In-Memory |
| Tool Collapse | `useChatSession` (Set) | In-Memory |
| Attachments | `useAttachments` Hook | In-Memory + ObjectURL |
| Model/Reasoning | `useChatSession` State | In-Memory |
| Thread-Persistenz | — | **Offen** (braucht AgentEpisode Backend) |
