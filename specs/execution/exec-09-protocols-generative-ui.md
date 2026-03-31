# exec-09: Protokolle + Generative UI + Infinite Canvas + MCP Browser Tools

**Datum:** 30.03.2026
**Status:** Phase 1-3 implementiert — Verify-Gates ausstehend
**Abhaengig von:** exec-08 (Agent Backend + Voice) ✅ archiviert

---

## Phase 1: MCP Integration (Backend + Frontend)

- [x] **1.1:** Python MCP Server erstellt ✅ (30.03.2026)
  - `mcp>=1.26.0` in pyproject.toml, `uv sync` erfolgreich
  - `agent/mcp_server.py` — FastMCP Server mit Streamable HTTP Transport
  - Alle 10 TradingTools automatisch als MCP Tools registriert (6 Trading + 4 Canvas)
  - `shared/config.py` + `shared/__init__.py` vom Hauptprojekt uebernommen (GO_GATEWAY_URL)
  - Start: `uv run python -m agent.mcp_server` (Port 8095)

- [x] **1.2:** Go Gateway MCP Proxy ✅ (30.03.2026)
  - `handlers/http/mcp_proxy_handler.go` — Reverse-Proxy fuer MCP Streamable HTTP
  - Route: `/api/v1/mcp/` → Python MCP Server :8095
  - `MCP_SERVICE_URL` Config in `config.go` (Default: http://127.0.0.1:8095)
  - golangci-lint: 0 Issues

- [x] **1.3:** Frontend use-mcp Hook ✅ (30.03.2026)
  - `use-mcp@0.0.21` in agent-chat/package.json
  - `hooks/useMcpTools.ts` — React Hook connected zu MCP Server via Go Gateway
  - In AgentChatPanel verdrahtet — MCP Status in Footer sichtbar
  - Standardisierte Tool-Discovery + Calling

## Phase 2: Generative UI (Tambo + CopilotKit)

- [x] **2.1:** Tambo Generative UI Components ✅ (30.03.2026)
  - `@tambo-ai/react@1.2.4` installiert
  - `components/tambo/ChartWidget.tsx` — Chart mit Symbol, Timeframe, Preis, Indikatoren
  - `components/tambo/PortfolioCard.tsx` — Portfolio-Uebersicht mit Positionen + P&L
  - `components/tambo/registry.ts` — JSON Schema Component Registry
  - `providers/AgentProviders.tsx` — TamboProvider + CopilotKit Wrapper
  - TamboProvider in AgentChatPanel integriert (via AgentProviders)

- [x] **2.2:** CopilotKit AG-UI Protocol ✅ (30.03.2026)
  - `@copilotkit/react-core@1.54.1` installiert
  - `hooks/useFrontendTools.ts` — 4 Frontend-Tools via `useCopilotAction()`
    - SET_CHART_SYMBOL, SET_TIMEFRAME, OPEN_PANEL, NAVIGATE_TO
  - CopilotKit Provider in AgentChatPanel integriert (via AgentProviders)
  - useFrontendTools() Hook in AgentChatPanelInner aufgerufen
  - Agent steuert Frontend-State via standardisiertem AG-UI Protocol

- [ ] **2.3:** CopilotKit AG-UI evaluieren
  - [ ] Kann es AgentChatThread/Message/Composer ersetzen?
  - [ ] Tool-Call Rendering + Approval Flow?
  - [ ] A2UI (Google) evaluieren

- [ ] **2.4:** Entscheidung dokumentieren: Tambo + CopilotKit parallel vs. eines davon

## Phase 3: Infinite Canvas (tldraw 4.0)

- [x] **3.1:** tldraw eingebaut ✅ (30.03.2026)
  - `tldraw@4.5.4` installiert (SDK 4.0+)
  - `components/AgentCanvas.tsx` — Infinite Canvas mit Editor-Ref + State-Callback
  - `canvasToContext()` Helper fuer AI Context Extraktion
  - Split-View in AgentChatPanel: Chat links (50%), Canvas rechts (50%)
  - Toggle-Button in Status Bar: "Open Canvas" / "Close Canvas"
  - Canvas-Shapes werden als AI Context an Agent-Messages angehaengt

- [x] **3.2:** Canvas-Tools im Python Backend ✅ (30.03.2026)
  - `agent/tools/canvas.py` — 4 neue Tools:
    - `canvas_create_shape` — Erstellt Shapes (text, geo, arrow, note)
    - `canvas_create_novel_block` — Erstellt editierbaren Novel Editor Block
    - `canvas_update_shape` — Aktualisiert Text/Position
    - `canvas_delete_shape` — Loescht Shape
  - In ToolRegistry registriert (10 Tools gesamt)
  - Automatisch als MCP Tools exponiert

- [x] **3.3:** Canvas + Agent + Novel Integration ✅ (30.03.2026)
  - `canvas/NovelCanvasShape.tsx` — tldraw Custom Shape mit Novel Editor eingebettet
  - NovelShapeUtil in AgentCanvas registriert (`shapeUtils`)
  - `canvas_create_novel_block` Python Tool (10 Tools gesamt)
  - AgentCanvas.applyToolResult() handelt "novel" Shape-Typ
  - User kann Novel-Block auf Canvas inline editieren (Slash-Commands, Formatting)

- [ ] **3.4:** Lizenz evaluieren
  - tldraw 4.0: Kostenlos fuer Development + Hobby
  - Commercial License fuer Prod noetig

## Phase 4: WebMCP (Browser-Tools → Backend-Agent Bridge)

- [x] **4.1:** WebMCP Packages installiert ✅ (30.03.2026)
  - `@mcp-b/global@2.2.0` — Polyfill fuer navigator.modelContext (alle Browser)
  - `@mcp-b/react-webmcp@2.2.0` — React Hooks (useWebMCPTool)
  - Chrome 146 hat es nativ (Feb 2026), Edge bald, Firefox 8-12 Wochen

- [x] **4.2:** WebMCP Tool-Registration ✅ (30.03.2026)
  - `lib/webmcp-polyfill.ts` — Polyfill Import
  - `hooks/useWebMcpTools.ts` — 3 Trading-Tools via navigator.modelContext
  - Zod Schemas fuer Input-Validierung

- [x] **4.3:** WebMCP Bridge (Browser → Backend → Browser Roundtrip) ✅ (30.03.2026)
  - `hooks/useWebMcpBridge.ts` — Sammelt alle Browser-Tools, macht sie dem Backend verfuegbar
  - Bridge pollt `navigator.modelContext.listTools()` alle 5s (dynamisch bei Page-Wechsel)
  - Browser-Tool-Definitionen werden im Chat-Request als `browserTools` mitgeschickt
  - Go `agent_chat_handler.go` — `BrowserTools` Feld durchgereicht
  - Python `app.py` — `browserTools` in `AgentChatRequest`, dynamisch in ToolRegistry injiziert
  - `agent/tools/browser_tool.py` — `BrowserToolProxy` Wrapper (TradingTool fuer Browser-Tools)
  - Agent sieht Browser-Tools als "[Browser Tool]" mit prefix in Tool-Choice
  - Tool-Result `action: "browser_execute"` → Frontend erkennt → `navigator.modelContext.callTool()`
  - `ToolOutputRenderer.tsx` zeigt "Executing in browser via WebMCP..." Spinner
  - AgentChatPanel useEffect faengt `browser_execute` Results ab → ruft Bridge auf

- [ ] **4.4:** WebMCP in Layout integrieren + testen
  - Polyfill in layout.tsx importieren
  - useWebMcpTools() in Trading-Pages aufrufen
  - Chrome DevTools → navigator.modelContext.listTools() zeigt registrierte Tools
  - Agent erkennt Browser-Tools und kann sie aufrufen

---

## Verify-Gates

### Gate 1: MCP
- [ ] Python MCP Server startet und listet 10 Tools (`uv run python -m agent.mcp_server`)
- [ ] Go Proxy `/api/v1/mcp/` leitet korrekt an Python MCP Server weiter
- [ ] `use-mcp` Hook im Frontend connected zum MCP Server via Go Proxy
- [ ] Agent ruft Tools via MCP Standard auf (nicht manuelles fetch)
- [ ] MCP Status im AgentChatPanel Footer sichtbar ("connected", "X tools")

### Gate 2: Generative UI in Chat
- [ ] `get_chart_state` Tool-Result rendert als ChartWidget (nicht JSON)
- [ ] `get_portfolio_summary` Tool-Result rendert als PortfolioCard (nicht JSON)
- [ ] Tambo: ChartWidget zeigt Symbol, Timeframe, Preis, Indikatoren
- [ ] Tambo: PortfolioCard zeigt Positionen + P&L
- [ ] CopilotKit: Agent aendert Chart-Symbol via AG-UI Protocol
- [ ] CopilotKit + Tambo Provider laden ohne Fehler
- [ ] Unbekannte Tools fallen zurueck auf JSON-Anzeige

### Gate 3: Infinite Canvas
- [ ] tldraw Canvas rendert rechts neben Agent Chat (Split-View 50/50)
- [ ] "Open Canvas" / "Close Canvas" Toggle funktioniert
- [ ] Agent platziert Shape auf Canvas via `canvas_create_shape` Tool
- [ ] Agent erstellt Novel-Block auf Canvas via `canvas_create_novel_block` Tool
- [ ] Novel-Block ist inline editierbar (Slash-Commands, Formatting)
- [ ] User kann Shapes verschieben/annotieren (tldraw nativ)
- [ ] Canvas-State wird als AI Context an Agent-Messages angehaengt
- [ ] Canvas + Chat gleichzeitig nutzbar (kein Blocking)

---

## Neue/Geaenderte Dateien (exec-09)

```
python-backend/
  agent/mcp_server.py              — NEU: FastMCP Server (Port 8095)
  agent/tools/canvas.py            — NEU: Canvas Tools (create/update/delete shape)
  agent/tools/registry.py          — GEAENDERT: +4 Canvas Tools (10 gesamt)
  shared/__init__.py               — NEU: GO_GATEWAY_URL Export
  shared/config.py                 — NEU: Service URL Config
  pyproject.toml                   — GEAENDERT: +mcp>=1.26.0

go-appservice/
  internal/handlers/http/mcp_proxy_handler.go  — NEU: MCP Reverse-Proxy
  internal/config/config.go                    — GEAENDERT: +MCPServiceURL
  internal/handler/server.go                   — GEAENDERT: +/api/v1/mcp/ Route

agent-chat/
  AgentChatPanel.tsx               — GEAENDERT: +Providers, +MCP, +Canvas Split-View, +AG-UI
  providers/AgentProviders.tsx      — NEU: CopilotKit + Tambo Provider Wrapper
  hooks/useMcpTools.ts             — NEU: MCP React Hook (use-mcp)
  hooks/useFrontendTools.ts        — NEU: CopilotKit AG-UI Hook (ersetzt frontend-tools.ts)
  components/tambo/ChartWidget.tsx  — NEU: Generative UI: Chart
  components/tambo/PortfolioCard.tsx — NEU: Generative UI: Portfolio
  components/tambo/registry.ts     — NEU: Tambo Component Registry (JSON Schema)
  components/AgentCanvas.tsx       — NEU: tldraw Infinite Canvas mit Canvas-Ref + Novel Shape
  components/canvas/NovelCanvasShape.tsx — NEU: tldraw Custom Shape mit Novel Editor
  components/ToolOutputRenderer.tsx — NEU: Tool-Result → Rich UI Component Mapping
  components/AgentChatToolBlock.tsx — GEAENDERT: +ToolOutputRenderer fuer Rich UI statt JSON
  lib/webmcp-polyfill.ts           — NEU: WebMCP Polyfill Import (@mcp-b/global)
  hooks/useWebMcpTools.ts          — NEU: WebMCP Tool-Registration (navigator.modelContext)
  hooks/useWebMcpBridge.ts         — NEU: WebMCP Bridge (Browser-Tools → Backend-Agent Roundtrip)
  package.json                     — GEAENDERT: +use-mcp, +@copilotkit/react-core, +@tambo-ai/react, +tldraw, +@mcp-b/global, +@mcp-b/react-webmcp

python-backend/
  agent/tools/browser_tool.py      — NEU: BrowserToolProxy (TradingTool Wrapper fuer WebMCP)
  agent/app.py                     — GEAENDERT: +BrowserToolDef, +browserTools in Request + Registry

go-appservice/
  internal/handlers/http/agent_chat_handler.go — GEAENDERT: +browserToolDef Struct + BrowserTools Feld
```

### Deprecated (ersetzt durch exec-09 Protokolle)
- `lib/frontend-tools.ts` — Eigenes FrontendTool Interface, ersetzt durch `hooks/useFrontendTools.ts` (CopilotKit AG-UI)
- `lib/fusion-symbols.ts` — Stub, nur fuer deprecated frontend-tools.ts
- `lib/providers/types.ts` — Stub (TimeframeValue), nur fuer deprecated frontend-tools.ts
- Root `api/` Ordner — verschoben nach `src/app/api/` fuer Next.js App Router

### Gate 4: WebMCP
- [ ] Polyfill geladen: `navigator.modelContext` verfuegbar in Chrome/Firefox
- [ ] `navigator.modelContext.listTools()` zeigt trading_get_chart_state, trading_set_symbol, trading_set_timeframe
- [ ] Externer AI-Agent kann `navigator.modelContext.callTool("trading_get_chart_state")` aufrufen
