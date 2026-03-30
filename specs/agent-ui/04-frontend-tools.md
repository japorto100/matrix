# Agent Chat UI — Frontend Tool Registry

> Stand: 29.03.2026

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

`agent-chat/lib/frontend-tools.ts`
