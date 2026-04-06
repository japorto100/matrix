# Agent Chat UI — Erweiterungen

**Status:** Verschoben → `FUTURE_IDEAS.md`
**Stand:** 06.04.2026

Die ursprueglich hier gesammelten Ideen (Sandpack interaktive Code-Blocks, PPTX/PDF/Excel
Generierung, Spectacle Presentation Mode) sind nicht aktiv im Matrix-Projekt — sie waren
Vorschlaege fuer das Hauptprojekt (tradeview-fusion).

Sie wurden nach `FUTURE_IDEAS.md` (Section "Frontend / UI") umgezogen und werden dort
gesammelt mit anderen nicht-eingeplanten Ideen.

---

## Was im Agent-Chat tatsaechlich umgesetzt ist

Stand 06.04.2026 ist der Agent-Chat (`agent-chat/`) bereits ein vollwertiges Feature-Modul:

| Feature | Status | Details |
|---|---|---|
| Syntax Highlighting | ✅ | `react-shiki` (VS Code Engine) in nextjs-chat + agent-chat |
| Markdown Rendering | ✅ | `react-markdown` + `remark-gfm` + `rehype-sanitize` |
| Streaming SSE | ✅ | AI SDK v6 (`ai`, `@ai-sdk/react`) |
| AssistantUI | ✅ | `@assistant-ui/react` Radix-style Primitives |
| Tambo Generative UI | ✅ | ChartWidget, PortfolioCard, Schema-driven |
| CopilotKit AG-UI | ✅ | Frontend-State Mutations (set_chart_symbol, navigate, ...) |
| MCP + WebMCP | ✅ | `use-mcp`, `@mcp-b/global`, Browser-Tool Discovery |
| tldraw Canvas | ✅ | Infinite Canvas v4.0 mit Novel Editor Shape |
| Novel Editor | ✅ | Tiptap-based Rich Editor + Slash Commands + AI Autocomplete |
| Voice I/O | ✅ | useSpeechInput, useMediaRecorderInput, TTS Button |
| Tool Approval | ✅ | approveToolCall, denyToolCall |
| Multimodal Images | ✅ | Attachments mit base64 + mime_type |
| Reasoning Effort | ✅ | low/medium/high Toggle |

Details: `agent-ui/02-features.md`, `agent-ui/04-frontend-tools.md`.

---

## Verwandte Specs

- `agent-ui/01-architektur.md` — Agent-UI Architektur
- `agent-ui/02-features.md` — Feature-Status
- `FUTURE_IDEAS.md` — Verschobene Ideen
