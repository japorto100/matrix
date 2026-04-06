# Agent Chat UI — Feature-Katalog

**Status:** Aktiv
**Stand:** 06.04.2026 — Tambo + Canvas + WebMCP zusaetzlich aktiv (exec-09 Phase 3)

## Implementierter Feature-Stand

### Chat Core

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| Streaming | SSE via DefaultChatTransport, live Text-Delta Rendering | ✅ |
| Messages | UIMessage Parts (text, reasoning, tool-call, source) | ✅ |
| Composer | Auto-resize Input, Enter=Send, Shift+Enter=Newline | ✅ |
| Thread-ID | URL-persistent via nuqs (`?t=threadId`) | ✅ |
| Empty State | Suggestion-Chips für Erstinteraktion | ✅ |
| Scroll | Auto-follow bei neuen Nachrichten, Scroll-to-Bottom FAB | ✅ |
| Error Handling | Error-Banner mit Dismiss, Reconnect-Banner | ✅ |
| Abort | Stop-Button während Streaming (useChat abort) | ✅ |

### Markdown & Rich Text

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| GFM | GitHub Flavored Markdown (Tabellen, Listen, Links) | ✅ |
| Syntax Highlighting | Prism via react-syntax-highlighter, oneDark Theme | ✅ |
| Think-Block | `<think>` Tags als collapsible Reasoning-Block | ✅ |
| Citations | Superscript-Nummern verlinken zu Sources-Panel | ✅ |
| Code Copy | Copy-Button pro Code-Block | ✅ |
| JSON Renderer | Strukturierte JSON-Ausgaben als formatierte Tabelle | ✅ |

### Message Actions

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| Copy | Nachrichtentext kopieren | ✅ |
| Regenerate | Letzte Assistant-Nachricht neu generieren (retry) | ✅ |
| Edit & Resend | User-Nachricht editieren, ab dort neu senden | ✅ |
| Feedback | Thumbs Up/Down (lokal, kein Backend) | ✅ |
| Paced Fade-In | Nachrichten erscheinen gestaffelt (framer-motion) | ✅ |

### Speech & Audio

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| Voice Input | Web Speech API + MediaRecorder Fallback | ✅ |
| Mic Selector | Geräteauswahl bei mehreren Mikrofonen | ✅ |
| TTS | Text-to-Speech via BFF → Go → Python, Fallback: Browser SpeechSynthesis | ✅ |
| TTS Autoplay | Toggle in Toolbar — neue Assistant-Nachrichten automatisch vorlesen | ✅ |

### File Attachments

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| File Upload | Paperclip-Button, Multi-File | ✅ |
| Drag & Drop | Dateien auf Composer droppen | ✅ |
| Paste | Bilder aus Zwischenablage einfügen (Ctrl+V) | ✅ |
| Preview Strip | Thumbnail-Leiste mit Remove-Button | ✅ |
| Image Preview | Fullscreen Lightbox mit Zoom | ✅ |
| Multi-Modal | Base64-Encoding, an Agent als Vision-Input gesendet | ✅ |

### Tool Calls

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| Tool Block | Collapsible UI mit 7 States (pending/running/result/error/...) | ✅ |
| Approval Flow | Approve/Deny Buttons für bestätigungspflichtige Tools | ✅ |
| Frontend Tools | MCP-style UI-Mutations (Chart Symbol, Panel öffnen, Navigation) | ✅ |

### Sources & Citations

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| Sources Panel | Cards unter Assistant-Nachrichten mit URL + Titel | ✅ |
| Dialog Overflow | "View N more" öffnet Dialog bei vielen Quellen | ✅ |
| Source Extraction | Aus UIMessage Annotations + Data-Parts extrahiert | ✅ |

### Toolbar & Status

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| Model Selector | Sonnet 4.6 / Opus 4.6 / Haiku 4.5 | ✅ |
| Reasoning Effort | Low / Medium / High Toggle | ✅ |
| Status Badge | idle / live / degraded / reconnecting | ✅ |
| Context Pressure | Fortschrittsbalken (promptTokens / maxContext) | ✅ |
| Token Badge | Tokens ↑↓ + Cost-Schätzung pro Nachricht | ✅ |

### Global Integration

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| Sheet Overlay | Sidebar von rechts (shadcn Sheet, modal=false) | ✅ |
| Split Mode | 420px Panel rechts, pushed Content | ✅ |
| Rail Mode | 240px persistent Sidebar | ✅ |
| Context Chip | Injizierter Kontext als Badge im Header | ✅ |
| Badge Count | Proaktive Notification am Bot-Icon | ✅ |
| Ask AI Menu | Rechtsklick Context Menu "Ask AI about this" | ✅ |

### Generative UI (exec-09 Phase 3)

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| Tambo Components | Component Registry mit Schema-driven Props (ChartWidget, PortfolioCard) | ✅ |
| tldraw Canvas | Infinite Canvas v4.0 mit Agent-platziertem Output | ✅ |
| Novel Editor | Tiptap-based Rich Editor + Slash Commands + AI Autocomplete | ✅ |
| Canvas Tools | Agent kann Shapes/Text/Widgets via Tool-Results platzieren | ✅ |
| MCP Tools | `use-mcp` Hook fuer Standard-Tool Discovery | ✅ |
| WebMCP Bridge | Browser-Tools → Backend-Agent Bridge | ✅ |
| CopilotKit AG-UI | Frontend-State Mutations (set_chart_symbol, navigate_to, ...) | ✅ |

---

## Offene Features (Verschoben → `FUTURE_IDEAS.md` oder Execution Slices)

| Feature | Beschreibung | Status |
|---------|-------------|---|
| Thread-Persistenz | Chat-Verlauf speichern/laden via Hindsight Episodic Store | exec-13 |
| Stop/Resume Policy | Interruption-Semantik bei laufenden Tool-Chains | FUTURE_IDEAS |
| Pause-Loop / Resume-Loop | Agent-Loop pausieren und fortsetzen | FUTURE_IDEAS |
| Memory Graph Visualisierung | Interaktive Graph-UI ueber Hindsight Memories | exec-13 Phase 2 |
| Control Panel | Settings UI fuer Agent-Config, Memory, Skills | exec-13 Phase 3 |
