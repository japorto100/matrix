# exec-merge-chat: Chat UI Merge + Dual-Panel Layout

**Datum:** 10.04.2026
**Status:** Geplant
**Abhaengig von:** exec-06 Phase 5 (Shared Components) ✅, exec-15 (control-ui) ✅, Devstack E2E
**Herkunft:** Extrahiert aus exec-06 Phase 1 + Phase 6 (10.04.2026)

---

## Warum

Agent Chat, Matrix Chat und Control UI sind aktuell isolierte Next.js Apps.
Fuer das Hauptprojekt (tradeview-fusion) muessen sie in ein einheitliches Layout
zusammengefuehrt werden. Dieser Slice ist erst dran wenn alle drei UIs
isoliert funktionieren (Devstack E2E verifiziert).

### Ziel-Layout (tradeview-fusion)

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
│  Matrix Chat Fullscreen                             │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  /control (dedicated route)                         │
│  Control UI (Memory, Agents, System, Files)         │
└─────────────────────────────────────────────────────┘
```

---

## Phase 1: Agent Chat in Hauptprojekt einbinden

> Verschoben aus exec-06 Phase 1 (10.04.2026)

- [ ] **1.1:** Fehlende Deps in Hauptprojekt package.json installieren
  - Fehlend: `ai`, `@ai-sdk/react`, `@ai-sdk/ui-utils`
  - Vorhanden: framer-motion, react-markdown, remark-gfm, sonner, lucide-react, nuqs
  - agent-chat hat eigenes package.json als Referenz

- [ ] **1.2:** Agent Chat Dateien nach Hauptprojekt kopieren/symlinken
  - 19 Komponenten aus `agent-chat/components/`
  - Hooks aus `agent-chat/hooks/`
  - Context/Stores aus `agent-chat/context/` + `agent-chat/stores/`
  - Types aus `agent-chat/types.ts`

- [ ] **1.3:** Jotai Provider in Hauptprojekt Providers.tsx hinzufuegen

- [ ] **1.4:** `/agent` Route erstellen
  - Rendert AgentChatPanel standalone

---

## Phase 2: Dual-Panel Layout

> Verschoben aus exec-06 Phase 6 (10.04.2026)

### Dual-Panel
- [ ] ChatPanel-Wrapper Prototyp mit Tab-Toggle: [Matrix] [Agent]
- [ ] MatrixChat responsive bei ~380px Breite
- [ ] Gemeinsamer Notification-Badge
- [ ] Kontextwechsel: Agent → Matrix Summary, Matrix Mention → Agent-Tab

### Layout-Integration
- [ ] GlobalChatProvider + GlobalChatOverlay in (shell)/layout.tsx
- [ ] Sheet/Split/Rail Modes evaluieren

### Cross-UI Integrationen
- [ ] Agent-Antworten als Matrix-Nachricht relayed
- [ ] Matrix-Mention → Agent-Chat Trigger (`@trading-agent analyze AAPL`)

---

## Phase 3: control-ui Integration

> Querverweis: exec-15 Slice 8

- [ ] Komponenten-Migration von control-ui in Hauptprojekt
- [ ] GlobalTopBar mit 4 Surfaces (Agent · Memory · Control · Files)
- [ ] BFF-Routes integration
- [ ] control-ui/ archivieren oder eigenstaendig lassen

---

## Verify-Gates

### Gate 1: Agent Chat integriert
- [ ] Agent Chat UI rendert im Hauptprojekt ohne Fehler
- [ ] SSE Streaming via BFF → Go Gateway → Python Agent funktioniert
- [ ] Tool-Call + Approval Flow funktioniert

### Gate 2: Dual-Panel
- [ ] Tab-Toggle zwischen Matrix und Agent Chat
- [ ] Matrix Chat responsive in Panel-Breite (~380px)
- [ ] Beide Tabs lazy-loaded (nur aktiver Tab haelt Verbindung)

### Gate 3: control-ui integriert
- [ ] Control-Tabs erreichbar im Hauptprojekt
- [ ] Memory Dashboard zeigt Daten

---

## Risiken

| Risiko | Mitigation |
|---|---|
| Fehlende Hauptprojekt-Abhaengigkeiten | Phase 1.1 — systematisch identifizieren |
| MatrixChat nicht responsive genug | Phase 2 — ggf. separate Mobile-Variante |
| Zwei Chat-Engines = doppelter State | Tabs lazy-loaded, nur aktiver Tab haelt Verbindung |

---

## Abhaengigkeiten

- exec-06 Phase 5: Shared Components (Markdown, ImagePreview, Location) ✅
  - `D:\matrix\shared\` (`@matrix/shared`) geloescht am 13.04.2026 — alle Components superseded:
    - `geo/` + `location/` → lebt in `nextjs-chat/src/lib/matrix/geo.ts` + `components/matrix/message/content/Location*.tsx`
    - `markdown/CodeBlock.tsx` (58 Z.) → superseded durch `agent-chat/src/components/AgentChatMarkdown.tsx` (366 Z., Mermaid, Sandpack, Syntax-HL)
    - `media/ImagePreviewModal.tsx` → superseded durch `agent-chat/src/components/ImagePreviewModal.tsx`
  - Beim UI-Merge: Components aus den jeweiligen Apps nehmen, nicht aus archiviertem shared/
- exec-15: control-ui isoliert funktioniert
- Devstack E2E: alle drei UIs laufen einzeln
- tradeview-fusion: Hauptprojekt-Shell bereit

---

## Shared Component Integration: Location in Agent-Chat

> Verschoben aus exec2-03 (13.04.2026). Location-Components existieren in
> nextjs-chat (`LocationEmbed.tsx` + `geo.ts`), aber sind nicht in agent-chat
> integriert. Gehoert zum Merge weil es um Shared-Component-Nutzung zwischen
> den Chat-UIs geht.

**Was existiert (nextjs-chat):**
- `geo.ts` — `parseGeoUri()`, `osmUrl()`, `osmEmbedUrl()` (reine Utilities, 0 Dependencies)
- `LocationEmbed.tsx` — iframe-basierter OSM-Embed, Props: `{lat, lon, label?, zoom?, height?}` (0 Dependencies, SSR-safe)
- `LocationMapInner.tsx` — interaktive Leaflet-Karte (heavy, braucht leaflet + react-leaflet) — fuer Agent-Chat nicht noetig

**Was fehlt (agent-chat):**
- [ ] `geo.ts` + `LocationEmbed.tsx` nach agent-chat kopieren (oder als Shared Package)
- [ ] In `ToolOutputRenderer.tsx` oder `AgentChatMessage.tsx` einbinden: wenn Agent Location-Daten liefert (`{lat, lon, label}`) → `<LocationEmbed />` rendern
- [ ] Entscheidung: Agent liefert Location als Tool-Result JSON oder als `geo:` URI in Markdown?
