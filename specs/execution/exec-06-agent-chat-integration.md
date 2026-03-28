# exec-06: Agent Chat UI — Isolierte Entwicklung + Matrix-Integration

**Datum:** 28.03.2026
**Status:** Geplant
**Abhängig von:** exec-05 (NATS E2EE Pipeline) für Matrix-Agent-Verbindung

---

## Warum

### Kontext

Der Agent Chat UI Code wurde 1:1 aus dem Hauptprojekt nach `D:\matrix\agent-chat\` kopiert.
Er ist dort bereits produktiv und umfangreich (Rev. 31, 100+ ACs abgearbeitet).

Das Matrix-Isolationsprojekt bietet die Möglichkeit:
1. Agent Chat UI isoliert zu starten und Verify Gates zu prüfen
2. Go Gateway + Python Agent Service aus dem Hauptprojekt zu übernehmen und auf Richtigkeit zu prüfen
3. Die Integration von Matrix Chat + Agent Chat in einer gemeinsamen UI zu evaluieren

### Architektur-Entscheidung: Zwei UIs, ein Panel

**Matrix Chat** (`nextjs-chat/`) = User-zu-User Kommunikation + Agent als Bot-Kontakt
**Agent Chat** (`agent-chat/`) = Produktive Arbeitsoberfläche (Tools, Streaming, Artefakte)

Im Hauptprojekt soll Agent Chat auf jeder Page (außer `/chat`) als Sidebar/Panel verfügbar sein,
nicht den ganzen Viewport bedecken. Matrix Chat bekommt eine eigene Route (`/chat`).

**Ziel-Layout (Hauptprojekt):**

```
┌─────────────────────────────────────────────────────┐
│  /trading, /dashboard, /settings ...                │
│                                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │                      │  │  Chat Panel (rechts)  │ │
│  │   Page Content       │  │                       │ │
│  │                      │  │  [Matrix] [Agent] Tab │ │
│  │                      │  │                       │ │
│  │                      │  │  Tab wechselt:        │ │
│  │                      │  │  • Matrix RoomList +  │ │
│  │                      │  │    Timeline (kompakt) │ │
│  │                      │  │  • AgentChat Panel    │ │
│  │                      │  │                       │ │
│  └──────────────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  /chat (dedicated route)                            │
│                                                     │
│  Matrix Chat Fullscreen (Space-Rail + RoomList +    │
│  Timeline + InfoPanel — wie aktuell in nextjs-chat) │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Phase 0: Package Setup

### Ziel
`agent-chat/` hat keinen eigenen `package.json`. Abhängigkeiten müssen aus dem Hauptprojekt
(`root package.json`, Kopie vorhanden) extrahiert und als eigenes package.json für den
Agent Chat UI Ordner erstellt werden — oder in `nextjs-chat/package.json` integriert werden.

- [ ] **0.1:** Packages aus Root-`package.json` (Hauptprojekt-Kopie) identifizieren die Agent Chat braucht
  - Vercel AI SDK: `ai`, `@ai-sdk/react`, `@ai-sdk/ui-utils`
  - UI: `framer-motion`, `react-markdown`, `remark-gfm`, `rehype-highlight`, `react-syntax-highlighter`
  - Sonstige: `nuqs` (URL State), `sonner` (Toasts), `lucide-react`
  - Prüfen: welche davon bereits in `nextjs-chat/package.json` vorhanden sind

- [ ] **0.2:** Fehlende Packages in `nextjs-chat/package.json` installieren
  - Agent Chat Komponenten werden in nextjs-chat eingebunden (kein separates Package)
  - `npm install` / `pnpm add` für fehlende Dependencies

- [ ] **0.3:** Agent Chat Dateien nach `nextjs-chat/src/components/agent/` kopieren oder symlinken

---

## Phase 1: Agent Chat UI isoliert starten

### Ziel
Agent Chat aus `agent-chat/` im Next.js Dev-Server lauffähig machen und Verify Gates prüfen.
**Zuerst den exec-Slice aus dem Hauptprojekt (`agent_chat_ui_delta.md`) abarbeiten** — das ist
hier isoliert einfacher als im Hauptprojekt.

- [ ] **1.1:** Fehlende Dateien aus Hauptprojekt identifizieren und kopieren
  - `agent-chat/` enthält: AgentChatPanel, SplitChatShell, components/, context/, hooks/, types.ts
  - Prüfen: shadcn/ui Komponenten, Provider-Wrapper, BFF API-Route (`/api/agent/chat`)
  - Fehlende Abhängigkeiten aus Phase 0 müssen installiert sein

- [ ] **1.2:** Agent Chat in nextjs-chat einbinden (als separate Route oder Panel)
  - Route: `/agent` → rendert AgentChatPanel standalone
  - Oder: als Sheet/Drawer neben MatrixChat testbar

- [ ] **1.3:** `agent_chat_ui_delta.md` Verify Gates abarbeiten (aus Hauptprojekt)
  - Referenz: Rev. 31 AC-Liste + Verify Gates (AC.V1–AC.V86)
  - Fokus auf UI-only Gates (kein Backend nötig): Markdown, Think-Box, Copy, Syntax-Highlighting
  - Backend-abhängige Gates: brauchen Go Gateway + Python Agent Service (→ Phase 2)
  - **Hier isoliert abarbeiten, dann Ergebnisse ins Hauptprojekt zurücktragen**

### Fehlende Dateien (zu prüfen)
- [ ] shadcn/ui Komponenten die AgentChat nutzt aber in nextjs-chat fehlen
- [ ] BFF API-Route: `app/api/agent/chat/route.ts`
- [ ] GlobalChatProvider, GlobalKeyboardProvider (aus Hauptprojekt `(shell)/layout.tsx`)
- [ ] CommandPalette, AskAiContextMenu (falls relevant)

---

## Phase 2: Go Gateway + Python Agent Service übernehmen

### Ziel
Backend-Stack aus Hauptprojekt übernehmen, auf Richtigkeit prüfen, und isoliert lauffähig machen.

- [ ] **2.1:** Go Gateway Code aus Hauptprojekt kopieren
  - `/api/v1/agent/chat` SSE-Endpoint (AC6, code-complete im Hauptprojekt)
  - Model-Override, Reasoning-Effort, Multimodal Durchreichung
  - Prüfen: Kompatibilität mit NATS-Pipeline aus exec-05

- [ ] **2.2:** Python Agent Service aus Hauptprojekt kopieren
  - `run_agent_loop()` — Chat-Handler + Streaming (AC7, code-complete)
  - LLM-Anbindung (Anthropic/OpenAI via LiteLLM)
  - Prüfen: Passt der bestehende `python-agent-bridge/` oder braucht es separaten Service?

- [ ] **2.3:** End-to-End Test
  - User tippt im Agent Chat → BFF → Go Gateway → Python → LLM → SSE Stream zurück
  - Tool-Calls sichtbar im UI
  - Verify Gates die Backend brauchen durchgehen

---

## Phase 3: Dual-Panel Evaluation

### Ziel
Prüfen ob Matrix Chat + Agent Chat als Tabs in einem gemeinsamen Panel funktionieren.

- [ ] **3.1:** ChatPanel-Wrapper Prototyp
  - Wrapper-Komponente mit Tab-Toggle: [Matrix] [Agent]
  - Matrix-Tab: MatrixChat in kompakter Breite (~380px, responsive)
  - Agent-Tab: AgentChatPanel (hat bereits SplitChatShell Rail-Mode 240px)

- [ ] **3.2:** MatrixChat responsive testen
  - Space-Rail + RoomList + Timeline bei ~380px Breite
  - Möglicherweise: Space-Rail als Overlay/Drawer bei schmaler Breite
  - RoomList und Timeline als gestackte Views (nicht nebeneinander)

- [ ] **3.3:** Gemeinsamer Notification-Badge
  - Matrix: Unread-Count aus Sliding Sync
  - Agent: Badge-Count aus GlobalChatContext (`incrementBadge`/`clearBadge` existiert)
  - Kombinierter Badge am Panel-Toggle-Button

- [ ] **3.4:** Kontextwechsel evaluieren
  - Agent Chat sendet Zusammenfassung in Matrix-Raum nach Session-Ende (Muster C aus Recherche)
  - Matrix-Nachricht an Agent → öffnet Agent-Tab automatisch
  - Deep-Link zwischen beiden UIs

---

## Phase 4: Weitere Integrationen

- [ ] **4.1:** Agent-Antworten als Matrix-Nachricht relayed
  - Nach Agent-Chat-Session: Zusammenfassung als `m.text` + Chart als `m.image` in Matrix-Raum
  - Mobile User sehen Agent-Ergebnisse in Element X

- [ ] **4.2:** Matrix-Mention → Agent-Chat Trigger
  - User schreibt `@trading-agent analyze AAPL` in Matrix
  - Bot antwortet kurz in Matrix: "Analyse läuft..."
  - Vollständige Analyse im Agent Chat (mit Link)

---

## Risiken

| Risiko | Mitigation |
|---|---|
| Fehlende Hauptprojekt-Abhängigkeiten | Phase 1.1 — systematisch identifizieren |
| MatrixChat nicht responsive genug | Phase 3.2 — ggf. separate Mobile-optimierte Variante |
| Zwei Chat-Engines = doppelter State | Tabs sind lazy-loaded, nur aktiver Tab hält Verbindung |
| Vercel AI SDK Abhängigkeit | Agent Chat nutzt `useChat` + `DefaultChatTransport` — bereits stabil |

---

## Abhängigkeiten

- exec-05 Phase A (NATS) für Agent ↔ Matrix Verbindung
- Go Gateway Code aus Hauptprojekt
- Python Agent Service aus Hauptprojekt
- Hauptprojekt `agent_chat_ui_delta.md` als Referenz-Spec (Rev. 31)

---

## Cross-Signing Hinweis (aus exec-05 Diskussion)

Der Web-Client hat bereits einen "Verify"-Button der einen QR-Code öffnet.
Element X Mobile kann diesen QR-Code scannen → Cross-Signing Device Verification.
Das ist **nicht** QR-Login (braucht MAS), sondern Device-Verification (funktioniert ohne MAS).
Tuwunel unterstützt das — kein Blocker für Mobile-Testing.
