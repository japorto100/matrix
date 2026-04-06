# Agent Tools & Capabilities -- Werkzeugkasten fuer autonome Agenten

> **Stand:** 22. Februar 2026
> **Zweck:** Definiert alle Tools, Protokolle und Capabilities die unseren Agenten zur Verfuegung stehen: Browser-Steuerung, Vision, MCP-Server, Agentic Search, Kommunikationskanaele, Frontend-Observation, und Agent-to-Agent Collaboration. Das Ziel: Ein Orchestrator-Agent der 100% Kontext hat -- Frontend-State, Portfolio, Nachrichten, User-Verhalten, Karte, Indikatoren -- und autonom den richtigen Kontext zieht.
> **Abgrenzung:** `CONTEXT_ENGINEERING.md` definiert WAS der Agent braucht. Dieses Dokument definiert WIE er es bekommt (Werkzeuge).
> **Abgrenzung:** `AGENT_ARCHITECTURE.md` definiert Rollen und Workflows. Dieses Dokument definiert die Toolbox die jede Rolle nutzt.
> **Abgrenzung:** `MEMORY_ARCHITECTURE.md` definiert Speicher-Schichten. Dieses Dokument definiert die Read/Write-Interfaces zu diesen Schichten.
> **Ergaenzung Security-Layer:** [`AGENT_SECURITY.md`](./AGENT_SECURITY.md) definiert Capability Envelope, Retrieval Broker, Tool Proxy und Agentic-Storage-Write-Grenzen.
> **Ergaenzung Harness-Layer:** [`AGENT_HARNESS.md`](./AGENT_HARNESS.md) buendelt Runtime-Harness-Prinzipien, OpenSandbox-Execution-Boundary und Guardrail-Governance.
> **Ergaenzung Tuning-Layer:** [`AGENT_MODEL_TOKEN_TUNING.md`](./AGENT_MODEL_TOKEN_TUNING.md) definiert Token-/KV-/Prefix-Caching-, Flash- und Langkontext-Tuningpfade mit Go/No-Go-Gates.
> **Referenz-Dokumente:** [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md), [`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md), [`MEMORY_ARCHITECTURE.md`](./MEMORY_ARCHITECTURE.md), [`GAME_THEORY.md`](./GAME_THEORY.md), [`GEOMAP_OVERVIEW.md`](./specs/geo/GEOMAP_OVERVIEW.md)
> **Externe Referenzen:**
> - [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) -- Browser-Debugging und Automation
> - [WebMCP](https://webmcp.dev/) -- Website-to-Agent Bridge
> - [WebMCP W3C Community Draft](https://webmachinelearning.github.io/webmcp/) -- Offizielle Spezifikation
> - [Music Composer WebMCP Demo](https://github.com/Leanmcp-Community/music-composer-webmcp) -- Referenz-Implementierung (100+ Tool Calls, 0% Error)
> - [Agentic File Search](https://github.com/PromtEngineer/agentic-file-search) -- Dokumenten-Navigation statt RAG
> - [OpenClaw](https://github.com/openclaw/openclaw) -- Multi-Channel Personal AI Assistant
> - [TinyClaw / TinyAGI](https://github.com/PromtEngineer/tinyAGI) -- Multi-Agent Collaboration
> - [A2A Protocol](https://google.github.io/A2A/) -- Google Agent-to-Agent Standard
> - [Emergent Mind API](https://www.emergentmind.com/docs/api) -- Research Paper Search
> - [Context Engineering 2.0](https://arxiv.org/abs/2510.26493) -- CE Research Paper
> **Primaer betroffen:** Python-Backend (Agent-Runtime), Go Gateway (Tool-Routing), Frontend (State Exposure)

---

## Inhaltsverzeichnis

1. [Vision: Der 100%-Kontext-Agent](#1-vision-der-100-kontext-agent)
2. [Tool-Taxonomie](#2-tool-taxonomie)
3. [MCP-Server: Architektur-Entscheidung](#3-mcp-server-architektur-entscheidung)
4. [Browser Control Tools](#4-browser-control-tools)
5. [Frontend State Observation](#5-frontend-state-observation)
6. [Agentic Search Tools](#6-agentic-search-tools)
7. [Research & Intelligence Sources](#7-research--intelligence-sources)
8. [Communication Channels](#8-communication-channels)
9. [Agent-to-Agent (A2A) Collaboration](#9-agent-to-agent-a2a-collaboration)
10. [GeoMap Game Theory Simulation Mode](#10-geomap-game-theory-simulation-mode)
11. [Tool-Access-Matrix pro Agent-Rolle](#11-tool-access-matrix-pro-agent-rolle)
12. [Ist-Zustand vs. Soll-Zustand](#12-ist-zustand-vs-soll-zustand)
13. [Stufenplan](#13-stufenplan)
14. [Querverweise](#14-querverweise)
15. [Formale Planungssprachen -- PDDL / ADL (Phase 22+)](#15-formale-planungssprachen--pddl--adl-phase-22)
16. [Konsolidierungs-Addendum -- Merge/Claim/Simulation Tools](#16-konsolidierungs-addendum----mergeclaimsimulation-tools)

---

## 1. Vision: Der 100%-Kontext-Agent

> **Realitaet heute:** Du benutzt 5+ Tools: Google Search, Gemini (Nano Banana), ChatGPT, NotebookLM (isolierter Kontext, Indexing), Cursor (Code). Jedes Tool hat seine eigene Staerke, aber keines hat das Gesamtbild.
>
> **Ziel:** Ein Orchestrator-Agent der autonom:
> - **Sieht** was du siehst (Frontend-State: welche Aktie, welches Timeframe, welche Indikatoren)
> - **Weiss** was du weisst (Portfolio, Watchlist, Favoriten, Alert-History)
> - **Liest** was relevant ist (Nachrichten, Events, Research Papers)
> - **Navigiert** die GeoMap (Marker anklicken, Regionen zoomen, Game Theory Map)
> - **Debuggt** wenn noetig (Chrome DevTools, Netzwerk-Requests, Console)
> - **Kommuniziert** ueber deine Kanaele (WhatsApp, Telegram, Discord)
> - **Kollaboriert** mit spezialisierten Sub-Agenten (BTE-Extractor, Game Theory Scorer, Research Agent)

### Was "100% Kontext" konkret bedeutet

```
┌──────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                             │
│                                                                  │
│  "Was soll ich jetzt beachten?"                                  │
│                                                                  │
│  ┌──── Frontend State ────┐  ┌──── Memory ────────────┐         │
│  │ Aktive Seite: /chart   │  │ KG: Strategeme, BTE    │         │
│  │ Symbol: AAPL           │  │ Episodic: Letzte 5     │         │
│  │ Timeframe: 4H          │  │           Analysen     │         │
│  │ Indikatoren: RSI, MACD │  │ Vector: Aehnliche News │         │
│  │ GeoMap: MENA fokussiert │  │ Redis: Letzte Scores   │         │
│  │ Portfolio: 5 Positionen │  │                        │         │
│  │ Alerts: 2 aktiv         │  │                        │         │
│  └─────────────────────────┘  └────────────────────────┘         │
│                                                                  │
│  ┌──── Live Data ─────────┐  ┌──── Research ──────────┐         │
│  │ News: Top 3 relevant   │  │ Emergent Mind: Papers  │         │
│  │ Events: ACLED/GDELT    │  │ Agentic Search: Docs   │         │
│  │ Market: Preis, Vol     │  │ Web Search: Context    │         │
│  └─────────────────────────┘  └────────────────────────┘         │
│                                                                  │
│  ┌──── Tools ─────────────┐  ┌──── Channels ─────────┐         │
│  │ Browser: Navigate, SS  │  │ WhatsApp: Alerts       │         │
│  │ WebMCP: Interact       │  │ Telegram: Commands     │         │
│  │ DevTools: Debug        │  │ Discord: Dashboard     │         │
│  │ Vision: Screenshots    │  │                        │         │
│  └─────────────────────────┘  └────────────────────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Tool-Taxonomie

| Kategorie | Tool | Protokoll | Zweck | Stufe |
|---|---|---|---|---|
| **Browser Control** | Chrome DevTools MCP | MCP Server | Debugging, Performance, Network Inspection | T2 |
| **Browser Interaction** | WebMCP | W3C Draft / `navigator.modelContext` | UI-Interaktion via direkte Tool Calls (98% Accuracy, kein Playwright noetig) | T2 |
| **Browser Automation** | Puppeteer (via DevTools MCP) | MCP Tool | Screenshots, Click, Fill, Navigate | T2 |
| **Vision** | Screenshot + VLM | Tool (intern) | "Was sieht der User gerade?" | T3 |
| **Frontend State** | State Exposure API | REST / WebSocket | Symbol, Timeframe, Indikatoren, Portfolio | T1 |
| **Memory Read** | KG Query, Vector Search, Episodic | Tool (intern) | Context Assembly (`CONTEXT_ENGINEERING.md`) | T1 |
| **Memory Write** | Analysis Logger, Feedback | Tool (intern) | Episodic Memory schreiben | T2 |
| **Agentic Search** | File Navigator (Docling-based) | Tool (intern) | Dokumente durchsuchen wie ein Mensch | T3 |
| **Web Search** | Google/Brave Search API | Tool (extern) | Aktuelle Informationen | T2 |
| **Research** | Emergent Mind API | Tool (extern) | Trending Papers, Research | T3 |
| **Communication** | WhatsApp/Telegram/Discord | Channel (extern) | User-Benachrichtigung, Befehle | T2 |
| **A2A** | Google A2A Protocol | Protocol | Agent-zu-Agent Collaboration | T4 |
| **Code Search** | Agentic File Search on Repo | Tool (intern) | Codebase-Navigation | T3 |
| **Tool Discovery** | Tool Search / Lazy Loading | Runtime-Pattern | grosse Tool-Inventare ohne Context-Bloat nutzbar halten | T2 |
| **Plan Surface** | Markdown-/JSON-Planartefakt | Datei / UI / Store | Planner-Status sichtbar und editierbar machen | T2 |

---

## 3. MCP-Server: Architektur-Entscheidung

> **Deine Frage:** "Koennen wir MCP abstrahieren und als Skill extrahieren? Oder muss es ein MCP-Server sein?"

### Antwort: MCP-Server MUESSEN MCP-Server bleiben. Aber sie KOENNEN als Skills gewrapped werden.

**Warum MCP-Server nicht wegabstrahiert werden koennen:**

MCP (Model Context Protocol) ist ein **Transport-Standard** -- wie HTTP fuer APIs. Chrome DevTools MCP startet eine Chrome-Instanz und exponiert Tools (click, navigate, screenshot, evaluate_script, etc.) ueber das MCP-Protokoll. Der Chrome-Browser selbst IST der Server.

**WebMCP ist ein separater, aber komplementaerer Standard:** Ein [W3C Community Draft](https://webmachinelearning.github.io/webmcp/) (Co-authored von Google/Microsoft-Engineers), der in Chrome 146 (Canary) als `navigator.modelContext` API shipped. Der fundamentale Unterschied: WebMCP braucht KEINEN externen MCP-Server. Die Website selbst deklariert Tools (deklarativ via HTML-Attribute ODER imperativ via `navigator.modelContext.registerTool()`), und der Agent ruft diese direkt auf -- im JS-Context der Seite, mit User-Session/Auth. Das eliminiert Screenshot-basierte Interaktion komplett.

```
AGENT ──[MCP Protocol]──> Chrome DevTools MCP Server ──[CDP]──> Chrome Browser
AGENT ──[MCP Protocol]──> WebMCP Server ──[DOM API]──> Webseite
```

**Was abstrahiert werden KANN:** Ein **Skill-Wrapper** der:
1. Den MCP-Server automatisch startet/verbindet
2. High-Level-Operationen definiert ("Navigiere zur GeoMap und klicke auf Iran-Marker")
3. Error-Handling und Retry-Logik kapselt
4. Tool-Auswahl vereinfacht (26 Tools bei DevTools MCP → 5-8 haeufigste als Skill-Actions)

### MCP-Server fuer unser System

| MCP Server | Funktion | Config | Nutzen fuer uns |
|---|---|---|---|
| **Chrome DevTools MCP** | 26 Tools: click, fill, navigate, screenshot, network, console, performance trace | `npx chrome-devtools-mcp@latest` | GeoMap-Interaktion, Debugging, Performance-Analyse, Visual Regression |
| **WebMCP** | Website-eigene Tools via JS Widget | `<script src="webmcp.js">` + `registerTool()` | Custom Tools pro Seite: GeoMap-Marker-Info, Indikator-Werte, Portfolio-State |
| **Filesystem MCP** | Datei-Operationen | Bereits konfiguriert | Codebase-Zugriff, Config-Aenderungen |

### WebMCP: W3C-Proposal, Chrome 146, und warum das alles aendert

> **Stand Feb 2026:** WebMCP ist ein [W3C Community Draft](https://webmachinelearning.github.io/webmcp/) und shipped in Chrome 146 (Canary, hinter `chrome://flags`). Google- und Microsoft-Engineers sind Co-Autoren. Die native Browser-API heisst `navigator.modelContext`.
>
> **Benchmark:** ~67% weniger Computational Overhead, ~98% Task Accuracy vs. Screenshot-basierte Agenten. Ein [Music Composer Demo](https://github.com/Leanmcp-Community/music-composer-webmcp) machte 100+ Tool Calls mit 0% Error Rate -- der Agent wusste nicht mal, dass er eine Website steuert.

**Warum WebMCP Screenshot-Agenten ersetzt:**

| Ansatz | Wie es funktioniert | Probleme |
|---|---|---|
| Screenshot + Vision | Agent nimmt Screenshot, VLM erkennt UI-Elemente, klickt auf Koordinaten | Token-ineffizient, unreliable, langsam, bricht bei Layout-Aenderungen |
| DOM Parsing | Agent parst HTML/DOM, sucht Elemente | DOM zu komplex (tausende Nodes), fragil, Token-teuer |
| **WebMCP** | Website deklariert Tools → Agent macht direkte Tool Calls | Zuverlaessig, effizient, Agent braucht kein Playwright/Browser-Use |

**Zwei Implementierungswege:**

**A) Deklarativ (HTML-Attribute -- fuer einfache Forms):**
```html
<form toolname="set_chart_symbol" tooldescription="Change the active chart symbol">
  <input name="symbol" type="text" placeholder="AAPL" />
  <button type="submit">Apply</button>
</form>
```
Browser generiert automatisch das JSON Schema. Zero JavaScript.

**B) Imperativ (JS API -- fuer komplexe Interaktionen):**
```typescript
navigator.modelContext.registerTool(
  'get_chart_state',
  'Current chart configuration including symbol, timeframe, and active indicators',
  { type: 'object', properties: {} },
  () => ({
    content: [{ type: 'text', text: JSON.stringify({
      symbol: chartStore.getState().symbol,
      timeframe: chartStore.getState().timeframe,
      indicators: chartStore.getState().activeIndicators,
      visibleRange: chartStore.getState().visibleTimeRange,
    })}]
  })
);

navigator.modelContext.registerTool(
  'get_portfolio_summary',
  'Current portfolio positions, total value, and active alerts',
  { type: 'object', properties: {} },
  () => ({
    content: [{ type: 'text', text: JSON.stringify({
      positions: portfolioStore.getState().positions,
      totalValue: portfolioStore.getState().totalValue,
      activeAlerts: alertStore.getState().activeAlerts,
    })}]
  })
);

navigator.modelContext.registerTool(
  'get_geomap_focus',
  'Current GeoMap view: center, zoom, filters, selected event, game theory mode',
  { type: 'object', properties: {} },
  () => ({
    content: [{ type: 'text', text: JSON.stringify({
      center: geoMapStore.getState().center,
      zoom: geoMapStore.getState().zoom,
      activeFilters: geoMapStore.getState().filters,
      selectedEvent: geoMapStore.getState().selectedEvent,
      gameTheoryMode: geoMapStore.getState().isGameTheoryMode,
      visibleMarkers: geoMapStore.getState().visibleMarkerCount,
    })}]
  })
);

navigator.modelContext.registerTool(
  'click_geomap_marker',
  'Select a specific event marker on the GeoMap by event ID',
  { type: 'object', properties: { eventId: { type: 'string', description: 'The event ID to select' } }, required: ['eventId'] },
  (args) => {
    geoMapStore.getState().selectEvent(args.eventId);
    return { content: [{ type: 'text', text: `Marker ${args.eventId} selected` }] };
  }
);

navigator.modelContext.registerTool(
  'run_game_theory_simulation',
  'Trigger game theory simulation for the currently selected event with specified scenario count',
  { type: 'object', properties: { scenarios: { type: 'number', description: 'Number of Monte Carlo paths (default 100)' } } },
  async (args) => {
    const result = await gameTheoryService.simulate(args.scenarios || 100);
    return { content: [{ type: 'text', text: JSON.stringify(result) }] };
  }
);
```

**Security-Modell (aus Reddit-Diskussion bestaetigt):**
- Tools laufen im JS-Context der Seite → erben User-Session, Cookies, CORS automatisch
- Same-Origin-Policy gilt -- Agent kann keine Cross-Origin-Daten abgreifen
- Bei Logout verlieren Tools sofort den Zugriff (Session-gebunden)
- **Audit Trail:** Tool Calls koennen vor Ausfuehrung intercepted und geloggt werden (fuer Observability, `CONTEXT_ENGINEERING.md` Sek. 9)

**Fallback fuer Browser ohne WebMCP-Support:**
- Polyfill existiert (Music Composer Demo nutzt einen)
- Alternativ: klassisches `WebMCP` JS-Library (`<script src="webmcp.js">`) fuer aeltere Browser
- Langfristig: Native Browser API wird Standard (W3C Draft)

**Das loest dein Kernproblem:** Der Agent kann den Frontend-State deterministisch lesen (kein Screenshot + Vision noetig fuer strukturierte Daten) UND mit der UI interagieren (GeoMap Marker anklicken, Simulation starten, Chart-Symbol wechseln). Und das mit 98% Accuracy statt der ~60-70% von Screenshot-Agenten.

### 3.1 Tool Discovery und Lazy Loading

Sobald viele MCP-Server und interne Tool-Familien parallel existieren, braucht die
Agent-Runtime einen Discovery-Layer statt "alle Tool-Deskriptoren immer im
Prompt".

**Arbeitsregel fuer `tradeview-fusion`:**

- Tool-Discovery ist ein **Runtime-Pattern**, kein eigenes Root-Architekturzentrum.
- Grosse Tool-Inventare werden ueber Suche + selektives Nachladen erschlossen.
- Die Default-Suche sollte zwei Modi haben:
  - **regex/exakt** fuer bekannte Tool-Namen und Familien
  - **BM25/semantisch** fuer Aufgabenbeschreibungen und unscharfe Queries

**Warum das wichtig ist:**

- weniger Context Pollution bei vielen MCP- und internen Tools
- bessere Tool-Auswahl statt "blindes" Halluzinieren von Tool-Namen
- saubere Skalierung, wenn spaeter Memory-, Research-, Broker- und Admin-Tools
  parallel verfuegbar sind

**Benennungsregeln fuer Tools:**

- Verben + Objekte klar halten: `search_papers`, `read_paper`, `market_data_fetch`
- verwandte Tool-Familien konsistent gruppieren
- Beschreibungen so schreiben, dass semantische Suche sie gut matchen kann

Das Tool-Search-Muster bleibt damit in der Heimat von Runtime-/Tooling-Entscheiden
und muss nicht als eigene Root-Verfassung weiterleben.

### 3.2 Optionales Code-Mode-Muster (evaluate-only)

Bei MCP-Tools mit grossen JSON-/API-Antworten kann ein optionaler "code mode"
evaluiert werden: Der Agent schreibt ein kleines Auswertungsskript, die
Sandbox fuehrt es auf dem Rohpayload aus, und nur der kompakte Output geht in
den Kontext.

Arbeitsregeln fuer `tradeview-fusion`:

- **evaluate-only**: kein Default-Switch ohne Evidence in den Harness-Gates
- nur fuer High-Volume-Responses (z. B. grosse Listen, Telemetrie, Bulk-Snapshots)
- kein Ersatz fuer normale Tool-Responses bei kleinen Payloads
- Ausfuehrung nur in isolierter Runtime-Boundary (keine Host-Ausfuehrung)
- Ergebnisformat muss klein, deterministisch und auditierbar sein

Kandidaten-Referenz (evaluate-only):

- [chenhunghan/code-mode-skill](https://github.com/chenhunghan/code-mode-skill)

### 3.3 MCP Apps Extension (UI aus MCP-Servern) -- evaluate-first

Neben klassischen MCP-Tools (text-/json-basierte Tool-Responses) soll auch
MCP Apps als optionales UI-Layer eingeplant werden:

- Tool deklariert `ui://...` Ressource (`_meta.ui.resourceUri`)
- Host rendert UI in sandboxed iframe
- UI-Kommunikation via JSON-RPC over `postMessage`

Arbeitsregel fuer `tradeview-fusion`:

- **MCP Apps als additive Surface**, nicht als Ersatz fuer klassische Tool-Pfade
- **evaluate-first** hinter Feature-Flag; kein globaler Default ohne Evidence
- **text-only Fallback bleibt Pflicht** fuer alle UI-faehigen Tools

Security-/Trust-Policy (verbindlich):

1. Nur **pre-declared templates** (`ui://`) und hostseitige Vorpruefung
2. UI-initiierte Tool-Calls standardmaessig mit **explizitem User-Consent**
3. Vollstaendige Auditierbarkeit aller UI-Nachrichten/Tool-Calls
4. Start mit **curated external** Quellen (z. B. Mail/Calendar) und enger Allowlist
5. Keine Trading-kritischen Mutationen aus App-UI ohne Human-Approval

Initialer Rollout (empfohlen):

- Phase A: interne read-only Dashboards/Analysen
- Phase B: kuratierte Produktivitaets-Apps (z. B. Gmail/Outlook Kalender/Mail)
- Phase C: breitere externe App-Klassen erst nach Security-/Eval-Nachweisen

---

## 4. Browser Control Tools

### 4.1 Chrome DevTools MCP (Debugging + Performance)

**26 Tools**, kategorisiert nach Nutzen fuer uns:

| Kategorie | Tools | Unser Use-Case |
|---|---|---|
| **Input** | click, fill, hover, drag, press_key | GeoMap-Navigation, Formular-Eingaben |
| **Navigation** | navigate_page, new_page, list_pages, close_page, wait_for | Multi-Tab-Analyse (Chart + GeoMap + News) |
| **Debugging** | evaluate_script, list_console_messages, take_screenshot, take_snapshot | Frontend-Debugging, State-Inspection |
| **Network** | list_network_requests, get_network_request | API-Call-Debugging, Latenz-Analyse |
| **Performance** | performance_start_trace, performance_stop_trace, performance_analyze_insight | Bottleneck-Erkennung, Optimierung |

### 4.2 Entscheidungsmatrix: WebMCP vs. Chrome DevTools MCP

> **Faustregel:** WebMCP ist der Default fuer alles was mit dem Frontend-State und UI-Interaktion zu tun hat. Chrome DevTools MCP ist fuer alles "unter der Haube" (JS-Engine, Network, Performance). Beides gleichzeitig aktiv -- WebMCP first.

| Use Case | Tool | Begruendung |
|---|---|---|
| Frontend-State lesen (Chart, Portfolio, GeoMap) | **WebMCP** | Direkte, typsichere Tool Calls. 98% Accuracy. Kein DOM-Parsing. |
| UI-Interaktion (Marker klicken, Symbol wechseln, Filter setzen) | **WebMCP** | Deterministisch via `registerTool()`. Keine Koordinaten-Raterei. |
| Simulation starten, Game Theory Mode triggern | **WebMCP** | Direkter Funktionsaufruf mit strukturiertem Return. |
| JavaScript-Debugging (Errors, Exceptions, Stack Traces) | **Chrome DevTools MCP** | `list_console_messages`, `evaluate_script` -- Low-Level V8 Zugriff. |
| Network Inspection (welche API-Calls, Latenzen, Fehler?) | **Chrome DevTools MCP** | `list_network_requests`, `get_network_request` -- WebMCP hat keinen Netzwerk-Zugriff. |
| Performance Profiling (CPU, Memory, Rendering) | **Chrome DevTools MCP** | `performance_start_trace`, `performance_analyze_insight` -- Bottleneck-Erkennung. |
| CSS/Layout-Debugging | **Chrome DevTools MCP** | DOM-Inspektion, Computed Styles via `evaluate_script`. |
| Screenshot fuer Visual Verification | **Chrome DevTools MCP** | `take_screenshot` -- WebMCP macht keine Screenshots. |
| "Warum rendert die GeoMap langsam?" | **Beide** | WebMCP: State pruefen (wie viele Marker sichtbar?). DevTools: CPU Profile starten. |
| "Zeige mir was der User sieht und klicke den Iran-Marker" | **Beide** | DevTools: Screenshot. WebMCP: `click_geomap_marker("iran-sanctions-2026")`. |
| Formular-Eingabe (einfache Forms) | **WebMCP (deklarativ)** | HTML-Attribute `toolname`/`tooldescription` -- Zero JavaScript noetig. |

**Warum beides aktiv:**
- WebMCP kann nicht ins Network-Tab schauen. Chrome DevTools MCP kann nicht sauber mit Custom-Tools interagieren.
- Der Orchestrator-Agent waehlt pro Aufgabe das richtige Tool (oder beide). Das Tool-Routing ist Teil der Agent-Logik (`AGENT_ARCHITECTURE.md`).
- Bei Produktion: WebMCP allein reicht fuer 90% der Agent-Interaktionen. DevTools MCP wird on-demand fuer Debugging/Monitoring aktiviert.

### 4.3 Vision (Screenshot + VLM Analysis)

Fuer Situationen wo strukturierte Daten nicht reichen:
- "Wie sieht der Chart gerade aus?" → Screenshot + Vision Language Model
- "Ist die GeoMap-Visualisierung korrekt?" → Visual Regression Testing
- "Was steht in diesem PDF?" → Document Vision

**Technologie:** `take_screenshot` (DevTools MCP) + GPT-4o / Claude Vision API

---

## 5. Frontend State Observation

> **Ziel:** Der Agent weiss jederzeit was der User gerade sieht und tut.

### 5.1 State Exposure API (Soll)

Neuer Next.js API Endpoint der den gesamten Frontend-State exponiert:

```
GET /api/agent/state
→ {
    page: "/chart/AAPL",
    chart: { symbol: "AAPL", timeframe: "4H", indicators: ["RSI", "MACD", "BB"] },
    geomap: { center: [33.5, 48.2], zoom: 5, mode: "game-theory", filters: { severity: "S3+" } },
    portfolio: { positions: 5, totalValue: 12450.00, unrealizedPnL: +340.00 },
    alerts: { active: 2, triggered_last_24h: 1 },
    watchlist: ["AAPL", "GLD", "CL", "BTC-USD"],
    tradingPanel: { activeTab: "orders", favorites: ["market", "limit"] },
    lastUserAction: { type: "click", target: "geomap-marker-iran-sanctions", timestamp: "..." }
  }
```

### 5.2 WebSocket State Stream (Soll)

Fuer Real-Time Awareness: SSE/WebSocket der State-Changes pusht:

```
WS /api/agent/state-stream
→ { type: "chart_symbol_change", data: { from: "AAPL", to: "GLD" } }
→ { type: "geomap_marker_click", data: { eventId: "evt_iran_sanc_20260222" } }
→ { type: "alert_triggered", data: { alertId: "...", symbol: "GLD", condition: "price > 2100" } }
```

**Warum beides:** REST fuer On-Demand Context Assembly. WebSocket fuer proaktive Reaktion ("User hat gerade auf Iran-Sanktions-Event geklickt → ich bereite Game Theory Analyse vor").

### 5.3 Human-editierbare Planflaeche

Fuer komplexe Agent-Laeufe braucht der Planner neben strukturiertem State auch eine
menschlich lesbare Projektion des aktuellen Plans.

**Pattern:**

- **Planner** schreibt einen strukturierten Plan und optional eine Markdown-/
  Checklist-Projektion.
- **Executor** arbeitet immer nur den naechsten freigegebenen Schritt ab.
- **Replanner** bewertet nach jedem wichtigen Schritt, ob der Plan noch stimmt.
- **Human-in-the-loop** kann Schritte markieren, umpriorisieren, pausieren oder
  mit Kommentaren versehen.

**Architekturregel:**

- Die **strukturierte Runtime-Representation** bleibt die Source of Truth.
- Die Markdown-/UI-Ansicht ist die editierbare Oberflaeche fuer Mensch und Agent.
- Diese Planflaeche gehoert zu Agent-Workbench/Mission-Control-Surfaces, nicht in
  Trading-Kern-Widgets.

### 5.4 Read-only Agent-UI-Surfaces

Tambo oder aehnliche Frameworks sind fuer uns vor allem als Laufzeitmuster fuer
agentische Output-Surfaces relevant:

- Analyse-Karten
- Tool-Result-Renderings
- Playground-/Monitor-Komponenten
- statusnahe SSE-/Streaming-Widgets

**Harte Grenze:** Solche AI-getriebenen UI-Surfaces bleiben read-only oder
assistiv. Keine Orders, keine Kontomutationen, keine stillen Side Effects.

---

## 6. Agentic Search Tools

### 6.1 Agentic File Search (Dokument-Navigation)

Inspiriert von [PromtEngineer/agentic-file-search](https://github.com/PromtEngineer/agentic-file-search):

**Warum besser als RAG fuer bestimmte Use-Cases:**
- RAG zerschneidet Dokumente in Chunks → Beziehungen zwischen Sektionen gehen verloren
- Cross-Referenzen ("Siehe Sek. 5.2") sind fuer Embeddings unsichtbar
- Agentic Search navigiert wie ein Mensch: Scan → Preview → Deep Dive → Backtrack

**Drei-Phasen-Strategie:**
1. **Parallel Scan:** Alle Dokumente im Ordner vorab scannen
2. **Deep Dive:** Nur relevante Dokumente vollstaendig parsen
3. **Backtrack:** Cross-Referenzen zu uebersprungenen Dokumenten folgen

**Use-Cases fuer uns:**

| Use-Case | Ordner/Quelle | Warum Agentic statt RAG |
|---|---|---|
| Buch-Recherche | `docs/books/` | Buecher referenzieren sich gegenseitig (Keen → Minsky, Rieck → Strategeme) |
| Architektur-Verstaendnis | `docs/*.md` | Dokumente referenzieren Sektionen in anderen Docs |
| Code-Navigation | `src/`, `python-backend/`, `go-backend/` | Code folgt Import-Ketten und Function Calls |
| Legal/Policy-Recherche | PDFs, Reports | Cross-References zu Exhibits, Appendices |

**Technologie:** Docling (lokal, open-source) fuer Document Parsing + Gemini Flash fuer Reasoning. Kosten: ~$0.001 pro Query.

### 6.2 Codebase Search (GitHub/Lokal)

Fuer die eigene Codebase -- sowohl lokal als auch auf GitHub (Produktion):
- Lokal: Agentic File Search auf `d:\tradingview-clones\tradeview-fusion`
- GitHub: GitHub Search API oder Code Search fuer Produktions-Repository
- Nutzen: "Wo wird `game_theory.py` aufgerufen?", "Welche Tests decken den CrisisWatch-Connector ab?"

---

## 7. Research & Intelligence Sources

### 7.1 Emergent Mind (Paper Search)

**API:** `https://api.emergentmind.com/v1/papers/search`
- Authentifizierung via API Key
- 25 Requests/Tag, 2500/Billing-Cycle
- Natural Language Search, Date-Filtering, 1-50 Ergebnisse

**Use-Cases:**
- Research Agent sucht nach "game theory market microstructure 2025"
- Trend-Monitoring: "Was sind die trending Papers diese Woche zu agent architecture?"
- Validierung: "Gibt es neuere Forschung zu Mean Field Games in Finance?"

**Funktionen die wir uebernehmen koennen (inspiriert von Emergent Mind UI):**
- Paper Prompts (strukturierte Fragen an Papers)
- Knowledge Gaps (was fehlt in der Forschung?)
- Practical Applications (wie anwendbar ist das Paper?)
- Related Papers (Vernetzung)

**Integration:** Python-Backend, Research Agent (`AGENT_ARCHITECTURE.md` Sek. 12) bekommt `search_papers` Tool.

### 7.2 arXiv API (Ergaenzung)

Direkte arXiv API fuer Full-Text-Zugriff (Emergent Mind hat nur Metadaten).
- Kostenlos, keine Rate-Limits (hoefliche Nutzung)
- PDF-Download + Docling-Parsing fuer Deep Dives

### 7.3 NotebookLM-Analogie: Isolierter Kontext

> **Deine Beobachtung:** NotebookLM indexiert 2 PDFs und merkt woertlich an wenn etwas nicht aus dem gegebenen Kontext stammt.

**Wie machen die das:**
- Strikte Grounding: LLM bekommt System Prompt "Antworte NUR basierend auf den folgenden Dokumenten. Wenn die Information nicht in den Dokumenten steht, sage das explizit."
- Retrieval-Augmented Generation mit expliziter Source-Attribution
- Kein externes Wissen, kein Web Search -- nur die hochgeladenen Docs

**Unser Equivalent:** Der Verifier Agent (`AGENT_ARCHITECTURE.md` Sek. 2) macht genau das -- er prueft ob Extraktionen durch den Kontext gedeckt sind. Wir koennen dasselbe Pattern fuer Research-Agenten nutzen: "Analysiere NUR basierend auf diesen 3 Papers + KG-Kontext."

### 7.4 claude-scientific-skills (Skill-Templates für Trading)

**Quelle:** [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills)

Skill-Templates für Trading-relevante Daten: `alpha-vantage`, `fred-economic-data`, `exploratory-data-analysis`, `market-research-reports`, `hedgefundmonitor`. Als Referenz für eigene Tool-Skills nutzbar.

### 7.5 Evaluation-Kandidaten: OSINT Agent Tools (noch nicht final)

> **Status:** Evaluation / nicht final freigegeben
>
> Die folgenden Tools sind als **moegliche Agent-Tools** aufgenommen, nicht als
> verbindlicher Scope. Vor Produktivnutzung sind Legal-, Security-, Rate-Limit-,
> und Qualitaetspruefung verpflichtend.

#### Candidate A: user-scanner (Identity/Presence Enrichment)

- **Quelle:** [kaifcodec/user-scanner](https://github.com/kaifcodec/user-scanner)
- **Was es ist:** CLI/Python-Toolkit fuer Username- und Email-Presence-Checks ueber viele Plattformen.
- **Primärer Modus bei uns:** Agent-Tool (nicht primär User-UI).
- **Geeigneter Use-Case:**
  - Entitaets-Anreicherung: `username/email -> Plattform-Presence-Signal`
  - Recherche-Unterstuetzung fuer Social/Entity Correlation
  - Input fuer Risiko-/Vertrauens-Scoring (als schwaches Signal, nie allein)
- **Wichtige Klarstellung:** Kein vollwertiger Bot-Detektor. Nur Presence-Signal.
- **Tool-Skizze (intern):**
  - `identity_presence_scan(query: {username?, email?}, scope, timeout)`
  - Output: strukturierte Trefferliste + Fehlergruende + Confidence-Flags

#### Candidate B: quevidkit (Video Tamper Forensics)

- **Quelle:** [thumpersecure/quevidkit](https://github.com/thumpersecure/quevidkit)
- **Was es ist:** Forensik-Toolkit zur Analyse moeglicher Video-Manipulation (CLI/REST/Web).
- **Primärer Modus bei uns:** Agent-Tool fuer Analysten-Assistenz (nicht primär Enduser-Bedienung).
- **Geeigneter Use-Case:**
  - Verifikation von OSINT/UGC-Videoevidence
  - "Suspicious vs. likely authentic" als Hilfssignal im Event-Workflow
  - Evidenz-Report fuer Analyst-Review (Begruendung + Confidence)
- **Wichtige Klarstellung:** Liefert Wahrscheinlichkeiten/Indizien, keine juristische Gewissheit.
- **Tool-Skizze (intern):**
  - `video_tamper_check(input: {file|url}, preset, sensitivity)`
  - Output: Label, Wahrscheinlichkeit, Segment-Hinweise, Erklaerung, Report-Link

#### Candidate C: Spin (Investigation Browser / Workflow-Referenz)

- **Quelle:** [thumpersecure/Spin](https://github.com/thumpersecure/Spin)
- **Was es ist:** OSINT-Desktop-Browser mit Fokus auf Investigation-Workflows (Identity-Profile, Correlation-Graph, Research-Flows, OPSEC-orientierte Nutzung).
- **Primärer Modus bei uns:** Architektur-/UX-Referenz (nicht als direkte Datenquelle, nicht als Core-Abhaengigkeit).
- **Geeigneter Use-Case:**
  - Inspiration fuer Investigation-Workspace (Entity-Graph + Timeline + Pivot-Flows)
  - Inspiration fuer Agent-Rollen im Recherche-Kontext
  - Inspiration fuer "multi-profile research session" Muster
- **Wichtige Klarstellung:** Spin ist kein klassischer Feed-Provider. Relevanz liegt in Workflow-Ideen, nicht in direkten Marktdaten.
- **Tool-Skizze (intern, abgeleitet):**
  - Kein direkter Wrapper geplant in Phase 1
  - Stattdessen selektive Feature-Uebernahme als eigene interne Tools/UI-Surfaces

#### Entscheidungsregel fuer alle Kandidaten

- Start als **optionaler Agent-Adapter** hinter Feature-Flag.
- Keine harten Trading-Entscheidungen nur auf Basis dieser Tools.
- Erst nach erfolgreicher Evaluation in den Standard-Toolring uebernehmen.

### 7.6 Optionale Websearch-Quelle: Ahmia

- **Quelle:** [Ahmia](https://ahmia.fi/)
- **Rolle bei uns:** Optionale Search-Quelle fuer den Agent im Websearch-Kontext (Darkweb-/Onion-nahe Discovery, nur wenn explizit aktiviert).
- **Einordnung:** Kein primaerer Finanz-/Makro-Feed; nur Zusatzsignal fuer Research/Threat-Context.
- **Implementationshinweis:** Zunaechst als URL-basierte optionale Query-Quelle fuehren (kein harter Runtime-Contract).
- **Guardrails:**
  - strikt optional per Feature-Flag
  - keine autonomen Handelsableitungen
  - Ergebnis immer als "unverified external context" labeln

### 7.7 Optionale Websearch-/Verifizierungsquelle: Wayback (Internet Archive)

- **Quelle:** [Wayback Machine](https://web.archive.org/)
- **Rolle bei uns:** Optionale Verifikationsquelle fuer historische Webseitenstaende
  ("was stand wann online?").
- **Einordnung:** Kein Live-Market-Feed; hoher Nutzen fuer Research, Provenance,
  Narrativ-Checks und Ruecktests von Headlines/Statements.
- **Implementationshinweis:** Zunaechst als on-demand Recherche-Quelle fuer den
  Agent fuehren, nicht als permanenter Polling-Core.
- **Guardrails:**
  - fair-use/rate-limit respektieren
  - Ergebnisse mit Timestamp/Capture-Quelle ausgeben
  - keine direkte Handelsableitung ohne weitere Bestaetigung

---

## 8. Communication Channels

### 8.1 Multi-Channel Architecture (Inspiriert von OpenClaw + TinyClaw)

> **OpenClaw Status (Stand 22. Feb 2026):**
> - v2026.2.21 (gestern released): SHA-256 Hashing, iOS Wake/Reconnect, Model Fallback Visibility
> - v2026.2.22 (unreleased): Korean Language Support, iOS TTS Prefetching, Unified Streaming Config
> - Frueher im Feb: xAI (Grok) Provider, Voyage AI Embeddings, Anthropic Opus 4.6, Token Usage Dashboard
> - 218K GitHub Stars, 748 Contributors, MIT License
> - Unterstuetzt: WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Teams, Google Chat, WebChat

**Was wir von OpenClaw lernen:**

| OpenClaw Feature | Unser Equivalent | Adaptions-Aufwand |
|---|---|---|
| Gateway (WS Control Plane) | Unser Go Gateway (Port 8080) | Erweiterung um Agent-Sessions |
| Multi-Channel Inbox | Noch nicht vorhanden | Channel-Adapter pro Plattform |
| Agent Routing (@agent_id) | Agent-Rollen (`AGENT_ARCHITECTURE.md` Sek. 12) | Routing-Layer im Gateway |
| DM Pairing (Security) | Noch nicht relevant (Single-User) | Spaeter bei Multi-User |
| Canvas (A2UI) | Unsere Frontend-Panels | Konzeptionell aehnlich |
| Skills Registry | Unser KG-basiertes Wissen | Strukturell anders (KG statt Skill-Files) |

### 8.2 Channel-Abstraktion (TinyClaw-Pattern)

TinyClaw zeigt: Message Queue + Channel Adapters = saubere Trennung.

```
WhatsApp / Telegram / Discord / WebChat
           │
           ▼
    ┌──────────────────┐
    │  Message Queue    │  (File-based oder Redis)
    │  incoming/        │
    │  processing/      │
    │  outgoing/        │
    └────────┬─────────┘
             │
    ┌────────▼─────────┐
    │  Agent Router     │  → @game_theory, @research, @trade
    │  (Go Gateway)     │
    └────────┬─────────┘
             │
    ┌────────▼─────────┐
    │  Agent Runtime    │  (Python, mit Tool Access)
    └──────────────────┘
```

**Konkreter Nutzen:**
- "GLD Alert getriggert" → WhatsApp-Nachricht an dich + Game Theory Kontext
- Du antwortest "@analyze" → Agent analysiert Event + Chart + Portfolio-Impact
- Ergebnis kommt zurueck via WhatsApp mit Zusammenfassung

---

## 9. Agent-to-Agent (A2A) Collaboration

### 9.1 Google A2A Protocol

**Status:** v0.3.0 (Juli 2025), 22K+ GitHub Stars, aktive Entwicklung. Spezifikation: [google.github.io/A2A](https://google.github.io/A2A/)

**Kernkonzepte:**
- **Agent Cards:** JSON-Metadaten (`/.well-known/agent.json`) beschreiben Capabilities, Skills, Auth
- **JSON-RPC 2.0 ueber HTTP(S):** Synchron, Streaming (SSE), Async Push
- **Task Lifecycle:** Stateful Tasks mit Status-Tracking
- **Opaque Execution:** Agenten teilen Ergebnisse, nicht interne State/Memory/Tools

**Relevanz fuer uns (2026-2027):**

| Szenario | Wie A2A hilft |
|---|---|
| Externer Research Agent | Ein spezialisierter Paper-Analyse-Agent (extern) analysiert Papers und liefert Zusammenfassungen via A2A |
| Cross-Platform Composite | Unser Game Theory Agent + ein externer Macro-Agent tauschen Regime-Einschaetzungen aus |
| Crowd Intelligence | Mehrere User-Agents tauschen (anonymisiert) Regime-Signals aus → Mean Field Approximation |
| Tool Marketplace | Spezialisierte Agenten bieten Tools an (z.B. "Ich kann COT-Daten analysieren") |

### 9.2 Interne Agent Collaboration (vor A2A)

Bevor A2A produktionsreif ist, brauchen wir interne Collaboration. Pattern aus TinyClaw:

```
Orchestrator
  ├── @game_theory  "Analysiere Iran-Sanktionen"
  │     └── Ergebnis: { impact: 0.7, bias: "risk_off", strategem: "strat_28" }
  │
  ├── @research     "Papers zu Sanctions → Oil Price seit 2020"
  │     └── Ergebnis: { papers: 3, key_finding: "avg +2.1% in 48h" }
  │
  ├── @behavioral   "BTE-Analyse der letzten Fed-Rede"
  │     └── Ergebnis: { drs: 8, state: "guarded", markers: ["117_Am", "118_Pol"] }
  │
  └── Synthese: "Iran-Sanktionen + historisches Pattern + Fed ist vorsichtig = risk_off, GLD Long Signal"
```

---

## 10. GeoMap Game Theory Simulation Mode

> **Dein Geistesblitz:** Die GeoMap bekommt einen Game-Theory-Modus mit Verzweigungen, Pfaden, einer Simulationsseite.

### 10.1 Konzept: Interactive Scenario Tree auf der Karte

```
┌─────────────────────────────────────────────────────────────────┐
│  GEOMAP -- GAME THEORY SIMULATION MODE                          │
│                                                                  │
│  ┌─ d3-geo Karte (geoOrthographic) ─────────────────────────┐  │
│  │                                                            │  │
│  │    ╔══════════════╗                                        │  │
│  │    ║ Iran         ║ ←── Aktuelles Event (pulsierend)      │  │
│  │    ║ Sanctions    ║                                        │  │
│  │    ╚══════╤═══════╝                                        │  │
│  │           │                                                │  │
│  │     ┌─────┼─────┐                                         │  │
│  │     │     │     │                                         │  │
│  │     ▼     ▼     ▼                                         │  │
│  │   ┌───┐ ┌───┐ ┌───┐                                      │  │
│  │   │ESC│ │STA│ │DEE│  ←── 3 Szenarien (klickbar)          │  │
│  │   │ↂ  │ │ↂ  │ │ↂ  │     Escalation / Status Quo / De-esc│  │
│  │   └─┬─┘ └─┬─┘ └─┬─┘                                      │  │
│  │     │     │     │                                         │  │
│  │    ...   ...   ...     ←── Weitere Verzweigungen          │  │
│  │                                                            │  │
│  │  ── Animierte Pfade auf der Karte ──                      │  │
│  │  Iran ═══> Strait of Hormuz ═══> Oil Price Impact         │  │
│  │  Iran ═══> Europe ═══> Gas Price Impact                   │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ Scenario Panel (rechts) ─────────────────────────────────┐  │
│  │                                                            │  │
│  │  SCENARIO: Escalation (60% Probability)                   │  │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │  │
│  │  Spieler:                                                  │  │
│  │  🏛 USA: Weitere Sanktionen (+0.15 Impact)               │  │
│  │  🏛 Iran: Vergeltung → Strait Blockade (+0.35 Impact)    │  │
│  │  📈 Institutional: Risk-Off → GLD, Oil Long              │  │
│  │  📉 Retail: Panik-Verkauf → Equity Short                 │  │
│  │                                                            │  │
│  │  Nash-Gleichgewicht: (Sanctions, Retaliate)               │  │
│  │  → Bias: STRONG RISK_OFF                                  │  │
│  │  → Betroffene Assets: GLD (+2.3%), CL (+5.1%), SPY (-1%) │  │
│  │                                                            │  │
│  │  Strategem Match: #28 "Auf das Dach locken"              │  │
│  │  Phase: Akute Krise → Kipppunkt-Naehe                     │  │
│  │                                                            │  │
│  │  [▶ Simulate]  [📊 Backtest]  [🔀 Alternative]           │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Interaktive Elemente

**Auf der Karte:**
- **Pulsierender Event-Marker:** Zeigt das aktuelle Kern-Event
- **Animated Transmission Paths:** Farbige Linien von Event → betroffene Regionen/Assets (z.B. Iran → Strait of Hormuz → Oil)
- **Szenario-Knoten:** Klickbare Verzweigungen die Spielbaeume auf der Karte visualisieren
- **Heatmap-Overlay:** Wahrscheinlichkeitsverteilung der Szenarien faerbt Regionen ein
- **Timeline-Slider:** "Was waere passiert vor 1 Woche / 1 Monat?" → Historischer Vergleich

**Im Szenario-Panel:**
- **Spieler-Karten:** Jeder Akteur mit Strategie, Payoff, historischem Verhalten
- **Nash-GG-Indikator:** Zeigt das berechnete Gleichgewicht + wie stabil es ist
- **Strategem-Match:** Welches der 36 Strategeme passt? (KG-Query)
- **Asset-Impact-Tabelle:** Betroffene Symbole mit geschaetzter Preisbewegung
- **Simulate-Button:** Monte-Carlo-artige Simulation ueber 100 Pfade → Verteilung der Outcomes
- **Backtest-Link:** "Wie haben aehnliche Events historisch performed?" (Episodic Memory)

### 10.3 Simulation Page (Advanced)

Separate Route `/simulation` oder `/geomap/simulation`:

```
┌──────────────────────────────────────────────────────────────┐
│  GAME THEORY SIMULATION ENGINE                               │
│                                                              │
│  Event: Iran Sanctions Escalation (Feb 2026)                │
│                                                              │
│  ┌─── Spielbaum (D3.js) ────────────────────────────────┐   │
│  │                                                       │   │
│  │        [ROOT: Sanctions Announced]                    │   │
│  │              /        |         \                     │   │
│  │         [ESC]      [STATUS]    [DE-ESC]              │   │
│  │        60% 🔴     25% 🟡     15% 🟢               │   │
│  │        /    \        |          |                    │   │
│  │   [BLOCK] [CYBER] [NEGOTIATE] [CONCEDE]             │   │
│  │    45%     15%      20%        5%                    │   │
│  │     |       |        |         |                     │   │
│  │   [...    [...      [...      [...                   │   │
│  │                                                       │   │
│  │  ● Klick = Zoom in + Szenario-Detail                 │   │
│  │  ■ Farbintensitaet = Wahrscheinlichkeit              │   │
│  │  ━ Pfadbreite = Erwarteter Impact                     │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─── Payoff-Matrix (Live) ─────────────────────────────┐   │
│  │  Spieler × Strategien → Payoffs (aus Nash-Berechnung) │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─── Monte-Carlo-Ergebnis ─────────────────────────────┐   │
│  │  1000 Simulationen | Avg Impact: 0.62 | Std: 0.18    │   │
│  │  ████████████████████░░░░ Risk_Off: 72%              │   │
│  │  ████░░░░░░░░░░░░░░░░░░░ Risk_On: 13%               │   │
│  │  ███░░░░░░░░░░░░░░░░░░░░ Neutral: 15%               │   │
│  │                                                       │   │
│  │  [Histogram: Impact Score Distribution]               │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─── Historischer Vergleich ───────────────────────────┐   │
│  │  Aehnliche Events (Episodic Memory):                  │   │
│  │  2025-11: Iran Sanctions → GLD +2.3% (24h)           │   │
│  │  2024-03: Russia Sanctions → Oil +8.1% (48h)         │   │
│  │  2023-10: China Tariffs → SPY -1.8% (24h)            │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 10.4 Wie die Karte sich dynamisch aendert

**Real-Time Updates wenn ein Event reinkommt:**

1. **Neues ACLED-Event:** Marker erscheint auf der Karte (animiert, pulsierend)
2. **Game Theory Scorer laeuft:** Waehrend der Berechnung zeigt der Marker einen Lade-Indikator
3. **Score berechnet:** 
   - Marker-Farbe aendert sich (gruen/gelb/rot je nach Impact)
   - Transmission Paths erscheinen (animierte Linien zu betroffenen Assets)
   - Szenario-Baum klappt sich aus wenn der User den Marker anklickt
4. **Regime-Wechsel erkannt:** Gesamte Karten-Hintergrundfarbe shiftet (subtil) -- risk_off = roetlich, risk_on = gruenlich
5. **Agent meldet sich proaktiv:** Toast/Notification: "Neues High-Impact Event: Iran Sanctions. Betroffene Positionen in deinem Portfolio: GLD (+), CL (+)"

**Kreativ-Idee: "Zeitreise-Modus"**
- Slider unten an der Karte: Ziehe durch die Zeit (letzte 30 Tage)
- Karte zeigt Events + Szenarien + tatsaechliche Marktreaktion
- Vergleich: "Was hat der Game Theory Scorer vorhergesagt vs. was ist passiert?"
- Ground Truth fuer Backtesting (Game Theory v2)

---

## 11. Tool-Access-Matrix pro Agent-Rolle

Welche Rolle bekommt welche Tools? Principle of Least Privilege.

| Rolle | Browser | WebMCP | Vision | Memory R | Memory W | Search | Channels | A2A |
|---|---|---|---|---|---|---|---|---|
| **Orchestrator** | Ja | Ja | Ja | Alle | Nein (delegiert) | Ja | Ja | Ja |
| **Extractor** | Nein | Nein | Nein | KG only | Nein | Nein | Nein | Nein |
| **Verifier** | Nein | Nein | Nein | KG + Episodic | Nein | Nein | Nein | Nein |
| **Guard** | Nein | Nein | Nein | Redis (Thresholds) | Nein | Nein | Nein | Nein |
| **Synthesizer** | Nein | Nein | Nein | Alle | Episodic (Write) | Nein | Ja (Output) | Nein |
| **Research Agent** | Nein | Nein | Nein | KG + Vector | Episodic (Write) | Ja (Emergent Mind, arXiv, Web) | Nein | Ja |
| **Monitor Agent** | Ja (DevTools) | Ja | Ja (Screenshots) | Redis + Episodic | Episodic (Alerts) | Nein | Ja (Alerts) | Nein |

### 11.1 Security Contract fuer jede Tool-Familie (verbindlich)

Jede neue Tool-Familie muss vor Aktivierung einen maschinenlesbaren
Security-Contract mitbringen.

Pflichtfelder:

- `trust_class` (`internal`, `curated_external`, `untrusted_external`)
- `data_class_in` / `data_class_out` (`public`, `internal`, `sensitive`)
- `allowed_identities` (`user`, `agent`, `task`)
- `capability_scope` (`read`, `write`, `delete`, `execute`, `network`)
- `requires_human_approval` (bool + trigger conditions)
- `egress_policy` (erlaubte Domains/targets)
- `credential_mode` (`vault_ref`, `jit_token`, `none`)
- `audit_schema` (Pflichtfelder fuer Trace)

Hard Stops:

- kein Tool ohne Security-Contract in produktiven Tool-Ring
- kein Tool mit `untrusted_external` input ohne Guardrail + taint propagation
- kein write-/execute-Tool ohne envelope + policy decision id

---

## 12. Ist-Zustand vs. Soll-Zustand

| Capability | Ist-Zustand | Soll-Zustand |
|---|---|---|
| **Browser Control** | Chrome DevTools MCP konfiguriert (Cursor-intern) | Agent kann GeoMap navigieren, Marker klicken, Charts screenshotten |
| **WebMCP** | Nicht implementiert | Custom Tools pro Frontend-Seite (Chart State, Portfolio, GeoMap) |
| **Vision** | Nicht implementiert | Screenshot + VLM fuer UI-Verstaendnis |
| **Frontend State** | Kein API-Endpoint | State Exposure REST + WebSocket Stream |
| **Agentic Search** | Nicht implementiert | Docling-basierter File Navigator fuer Docs + Code |
| **Research Sources** | Keine | Emergent Mind API + arXiv API |
| **Channels** | Keine | WhatsApp + Telegram (via Adapter, inspiriert von OpenClaw/TinyClaw) |
| **A2A Protocol** | Nicht vorhanden | Agent Cards + JSON-RPC (2027+) |
| **GeoMap Simulation** | Game Theory Impact Panel (statisch) | Interaktiver Szenario-Baum + Monte Carlo + Zeitreise |
| **Internal Agent Collab** | Nicht vorhanden | Orchestrator → Sub-Agents (Message Passing) |

---

## 13. Stufenplan

| Stufe | Was | Abhaengigkeit | Aufwand |
|---|---|---|---|
| **T1: Frontend State API** | `/api/agent/state` + WebSocket Stream | Zustand-Stores existieren bereits | Klein (1-2 Tage) |
| **T1: WebMCP Integration** | `registerTool()` fuer Chart, Portfolio, GeoMap | Frontend Stores | Klein (1 Tag) |
| **T2: Channel Adapter** | WhatsApp + Telegram via Queue + Go Gateway | Go Gateway Erweiterung | Mittel (1 Woche) |
| **T2: Agentic Search** | Docling + LLM File Navigator fuer `docs/` | Python Service | Mittel (3-5 Tage) |
| **T2: Emergent Mind** | API-Integration als Research Tool | API Key, Python | Klein (1 Tag) |
| **T3: GeoMap GT Mode** | Szenario-Baum auf Karte + Simulation Page | Game Theory v3+ | Gross (2-4 Wochen) |
| **T3: Vision** | Screenshot → VLM Pipeline | DevTools MCP + API | Mittel (3 Tage) |
| **T3: Internal Collab** | Orchestrator → Sub-Agent Message Passing | Agent Runtime | Mittel (1 Woche) |
| **T4: A2A Protocol** | Agent Cards + External Collaboration | A2A Spec v1.0 (2027?) | Gross (TBD) |

---

## 15. Formale Planungssprachen — PDDL / ADL (Phase 22+)

> **Stand:** 16. Maerz 2026 | **Phase-Slot:** 22b (PLANNED)

### Ueberblick

| Sprache | Was es ist | Solver noetig | Wann relevant |
|:--------|:-----------|:-------------|:--------------|
| **JSON Tool Schemas** | Informelle Funktionsbeschreibung fuer LLM Tool-Use | Nein | **Primaer — jetzt** |
| **PDDL** | Planning Domain Definition Language (STRIPS-Basis). Formale Beschreibung von Aktionen, Zustaenden, Zielen | Ja (FastDownward, FF-Planner) | Phase 22+ wenn formaler Plan-Validator benoetigt |
| **ADL** | Action Description Language — PDDL-Erweiterung mit konditionalen Effekten und Quantoren. Expressiver als PDDL | Ja (FastDownward unterstuetzt ADL) | Phase 22+ gleichzeitig mit PDDL |
| **OpenAPI / JSON Schema** | Maschinen-lesbare API-Beschreibung | Nein | Tool-Definitionen, MCP-Server-Specs |

### Strategische Einordnung

Heute nutzen wir JSON Tool Schemas fuer alle Agent-Tool-Definitionen — das ist
das, was Claude / OpenAI-kompatible Modelle erwarten. PDDL/ADL wuerde einen
zusaetzlichen formalen Plan-Validator ermöglichen:

```
Agent generiert Plan (JSON-Steps)
  └── PDDL-Validator prüft: Ist der Plan konsistent mit Domain-Constraints?
        ├── Valide → Ausfuehren
        └── Invalid → Replanning-Loop
```

**Vorteil:** Formale Verifizierung von Agent-Plans bevor Ausfuehrung. Besonders
relevant fuer: Order-Execution-Chains (kein Doppelkauf), GeoMap Scenario-Baum
(konsistente Spielzuege), Multi-Step-Tool-Use mit Constraints.

### Semantik und Scope (Phase 22b)

- Ziel ist **nicht** "alles in PDDL", sondern ein formales Constraint-Layer fuer
  komplexe Agent-Ablaufplanung.
- Besonders relevant sind temporale/numerische Constraints: Dauer, Deadlines,
  Ressourcenbudgets, erlaubte Parallelitaet und Replan-Trigger.
- Der technische Zielpfad ist kompatibel mit einem Compile-Ansatz
  `PDDL 2.1 (durative/numeric) -> diskretes PDDL+` fuer Solver-Backends.
- Fuer den ersten Pilot gilt die Modellierungsannahme
  **non-self-overlapping actions** (konservativer Start, geringeres Risiko).

### Fachliche Basis (Research-Delta, arXiv 2603.12188)

Die aktuelle Fachbasis fuer Phase 22b ist die Arbeit
`Compiling Temporal Numeric Planning into Discrete PDDL+` (Micheli/Scala/Valentini, 2026):

- Die Kompilierung von `PDDL 2.1 Level 3` nach diskretem `PDDL+` wird formal als
  **sound + complete** beschrieben.
- Der Compile-Pfad ist **polynomial in der Problemgroesse**, mit maximal
  konstantem Planlaengen-Overhead.
- Die Semantik deckt heikle Punkte explizit ab:
  `overall conditions`, `no-moving-target`, `mutex/non-interference`.
- Der Lock-Mechanismus in der Zielkodierung (`read/assign/increment`-Locks) ist
  relevant fuer korrekte Parallelitaet in Multi-Step-Workflows.
- Die Publikation arbeitet mit der Annahme **non-self-overlapping actions**.
- Die Compiler-Implementierung laeuft in `unified_planning`; delayed effects und
  timed initial literals werden ueber Events modelliert.

### Operative Implikation fuer TradeView Fusion

- PDDL/ADL wird als **Plan-Validierungsschicht** genutzt, nicht als Ersatz fuer
  JSON Tool Schemas, OpenAPI oder Runtime-Policy-Checks.
- Bester Pilot-Fit bleibt der "Morning Research Run" mit Deadline-, Ressourcen-
  und Fallback-Constraints.
- Nicht-Zielfaelle bleiben unveraendert: low-latency execution, triviale CRUD/UI,
  rein heuristische Ranking-Entscheide.
- Evidence-first Einfuehrung: ohne reproduzierbare Metrikverbesserung keine
  breitere Adoption.

### Nicht-Ziele

- Kein Ersatz fuer Low-Latency-Order-Execution.
- Kein Ersatz fuer normale REST-/CRUD-Workflow-Validierung.
- Keine Modellierung weicher, rein heuristischer Ranking-Entscheide in PDDL.

### Adoption-Bedingung

PDDL/ADL einplanen **wenn:**
- Agent-Plans komplex genug sind dass JSON-Validierung nicht ausreicht
- Formale Constraint-Checks noetig sind (finanzielle Limits, geopolitische Regeln)
- Team hat Kapazitaet fuer Solver-Integration (FastDownward in Python via subprocess)

**Heute:** JSON Tool Schemas + Pydantic-Validierung reichen. PDDL ist Zukunftsoption.

### Naechste Schritte (Phase 22b)

- [ ] **PDL.V1** Pilot-Domain "Morning Research Run" modellieren
      (API-Limits, Datenfrische, CPU-Budget, Fallback-Provider, Deadline)
- [ ] **PDL.V2** Solver-Pfad lokal testen (FastDownward per Python subprocess;
      optional zweiter Pfad via unified_planning fuer Vergleich)
- [ ] **PDL.V3** Semantik-Checkliste formalisieren
      (`overall`, `no-moving-target`, `mutex`, non-self-overlap)
- [ ] **PDL.V4** Research-Evidence in Pilot-Metriken mappen
      (valid/invalid blocking, p95 Zeit, Deadline-Adherence, Replan-Rate)
- [ ] **PDL.V5** Go/No-Go mit Messwerten entscheiden (Adopt/Defer)

### Referenz

- arXiv: `https://arxiv.org/html/2603.12188v1`

---

## 14. Querverweise

| Dieses Dokument | Referenziertes Dokument | Verbindung |
|---|---|---|
| Sek. 3 (MCP) | [`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 12-15 | Erweiterte Rollen nutzen Tools aus diesem Dokument |
| Sek. 4 (Browser) | [`GEOMAP_OVERVIEW.md`](./specs/geo/GEOMAP_OVERVIEW.md) | GeoMap-Navigation via Browser Tools |
| Sek. 5 (Frontend State) | [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md) Sek. 2-3 | Consumer "Frontend UI" bekommt State via diese API |
| Sek. 6 (Agentic Search) | [`MEMORY_ARCHITECTURE.md`](./MEMORY_ARCHITECTURE.md) Sek. 5.4 | Ergaenzt Vector Store (M4) fuer strukturierte Dokumente |
| Sek. 7 (Research) | [`docs/references/README.md`](./references/README.md) | Externer Referenzindex fuer Research-Quellen |
| Sek. 8 (Channels) | [`AGENT_ARCHITECTURE.md`](./AGENT_ARCHITECTURE.md) Sek. 13 | Orchestrator + Router nutzen Channels fuer Output |
| Sek. 9 (A2A) | [`GAME_THEORY.md`](./GAME_THEORY.md) Sek. 5.6 | Mean Field Games brauchen Multi-Agent Collaboration |
| Sek. 10 (GeoMap Simulation) | [`GAME_THEORY.md`](./GAME_THEORY.md) Sek. 5.3-5.4 | Spielbaeume + Evolutionary GT visualisiert |
| Sek. 10 (GeoMap Simulation) | [`GEOMAP_OVERVIEW.md`](./specs/geo/GEOMAP_OVERVIEW.md) Sek. 35 | Entity Graph + Transmission Paths |
| Sek. 11 (Tool Access) | [`CONTEXT_ENGINEERING.md`](./CONTEXT_ENGINEERING.md) Sek. 8 | MemoryAccessPolicy erweitert um ToolAccessPolicy |
| Sek. 15 (PDDL/ADL) | [`AGENT_SECURITY.md`](./AGENT_SECURITY.md) Sek. 2-7 | Formale Planpruefung bleibt unter Security-Grenzen fuer Tooling/Storage |
| Sek. 6/7/11 (Retrieval/Tools) | [`RAG_GRAPHRAG_STRATEGY_2026.md`](./RAG_GRAPHRAG_STRATEGY_2026.md) | Hybrid Retrieval, Query-Modi, Rerank/UQ-Anforderungen fuer Tooling-Pfade |

---

## 16. Konsolidierungs-Addendum -- Merge/Claim/Simulation Tools

Ergaenzende Tool-Familie fuer den Overlay-/Claim-/Branch-Vertrag:

| Tool-ID | Zweck | Scope |
|---|---|---|
| `get_overlay_context` | Lokalen User-Overlay-Kontext fuer Merge-Queries lesen | read-only |
| `evaluate_claim` | Claim gegen Evidence, Widerspruch und Staleness bewerten | read-mostly |
| `create_simulation_branch` | Branch aus Event/Claim/Snapshot erzeugen | bounded-write |
| `attach_evidence` | Evidence an Claim/Branch verknuepfen | bounded-write |

### 16.1 Capability-Scoping (verbindlich)

- `get_overlay_context`: `viewer+` (nur fuer eigenen user scope)
- `evaluate_claim`: `analyst+` oder policy-freigegebener Agent
- `create_simulation_branch`: `analyst+` mit Branch-Quota/Rate-Limit
- `attach_evidence`: `analyst+`, audit-pflichtig

Harte Regeln:

- Kein Tool in dieser Familie darf canonical facts direkt mutieren.
- Alle write-nahen Aufrufe muessen provenance + idempotency_key + audit_event_id tragen.
- Simulation-Tools schreiben nur in Branch-/Claim-Layer, nicht in den globalen Truth-Layer.
