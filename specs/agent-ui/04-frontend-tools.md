# Agent Chat UI — Frontend Tool Registry

**Status:** Aktiv
**Stand:** 06.04.2026 — 4 Frontend-Tools aktiv, MCP/WebMCP Bridge laeuft parallel

## Konzept

MCP-style Frontend-Tools die der Agent aufrufen kann um die UI direkt zu steuern.
Kein Backend-Roundtrip — die Ausführung passiert im Browser.

Tools mit `confirmLevel: "confirm"` zeigen eine Approval-Card im Chat bevor sie ausgeführt werden.

---

## Registrierte Tools

### SET_CHART_SYMBOL
Wechselt das aktive Chart-Symbol.

| Feld | Wert |
|------|------|
| Confirm | Ja |
| Args | `{ symbol: string }` |
| Beispiel | Agent: "Ich wechsle zu TSLA" → Approval Card → User bestätigt → Chart wechselt |

### SET_TIMEFRAME
Wechselt den Chart-Timeframe.

| Feld | Wert |
|------|------|
| Confirm | Ja |
| Args | `{ timeframe: string }` |
| Beispiel | `"1D"`, `"4H"`, `"1W"` |

### OPEN_PANEL
Öffnet ein Sidebar-Panel.

| Feld | Wert |
|------|------|
| Confirm | Nein |
| Args | `{ panel: "indicators" \| "news" \| "macro" \| "orders" \| "portfolio" \| "strategy" }` |
| Beispiel | Agent: "Ich öffne die Indikator-Übersicht" → Panel öffnet sofort |

### NAVIGATE_TO
Navigiert zu einer anderen Seite.

| Feld | Wert |
|------|------|
| Confirm | Ja |
| Args | `{ path: string }` |
| Beispiel | Agent: "Ich navigiere zum Portfolio" → Approval → Router navigiert |

---

## Integration

```ts
// lib/frontend-tools.ts
interface FrontendTool {
  name: string;
  description: string;
  confirmLevel: "none" | "confirm";
  execute: (args: Record<string, unknown>, callbacks: ToolCallbacks) => void;
}

interface ToolCallbacks {
  setSymbol?: (symbol: string) => void;
  setTimeframe?: (tf: string) => void;
  openPanel?: (panel: string) => void;
  navigate?: (path: string) => void;
}
```

Die Callbacks werden von der Host-Seite (z.B. `trading/page.tsx`) bereitgestellt und über Props in den AgentChatPanel durchgereicht.

---

## Datei

`agent-chat/src/lib/frontend-tools.ts`

---

## Verwandte Bridges

| Bridge | Datei | Zweck |
|---|---|---|
| MCP Tools | `agent-chat/src/hooks/useMcpTools.ts` | Standard MCP Tool Discovery via `use-mcp` |
| WebMCP Bridge | `agent-chat/src/hooks/useWebMcpBridge.ts` | Browser-Tools → Backend-Agent Bridge |
| WebMCP Tools | `agent-chat/src/hooks/useWebMcpTools.ts` | WebMCP Tool Definitions |
| WebMCP Polyfill | `agent-chat/src/lib/webmcp-polyfill.ts` | `navigator.modelContext` Polyfill |

Frontend-Tools (`frontend-tools.ts`) sind die **lokale, immediate** Variante.
MCP/WebMCP sind die **standardisierte, discovery-basierte** Variante. Beide leben
parallel und decken unterschiedliche Use-Cases ab.
