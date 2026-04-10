# exec-06: Shared Components + Agent Chat Verify (konsolidiert mit exec-08)

**Datum:** 28.03.2026 (konsolidiert 30.03.2026, restructured 10.04.2026)
**Status:** Phase 5 in Arbeit
**Abhaengig von:** exec-05 (NATS E2EE Pipeline)
**Zusammengefuehrt aus:** exec-06 (Agent Chat UI) + exec-08 offene Items (Verify-Gates)

> **Restructuring 10.04.2026:** Phase 1 (Package Setup) + Phase 6 (Dual-Panel + Layout)
> verschoben nach `exec-merge-chat.md`. Dieser Slice fokussiert auf Shared Components
> und Verify-Gates.

---

## Warum

exec-08 hat den gesamten Backend-Stack + Voice + Frontend SOTA implementiert (Code complete).
exec-06 war fuer die Frontend-Integration geplant. Beide hatten identische offene Punkte:
API Routes kopieren, Shared Components, Verify-Gates. Daher konsolidiert.

### Architektur-Entscheidung: Zwei UIs, ein Panel

**Matrix Chat** (`nextjs-chat/`) = User-zu-User Kommunikation + Agent als Bot-Kontakt
**Agent Chat** (`agent-chat/`) = Produktive Arbeitsoberfläche (Tools, Streaming, Artefakte)

Im Hauptprojekt soll Agent Chat auf jeder Page (ausser `/chat`) als Sidebar/Panel verfuegbar sein,
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

**Was exec-08 erledigt hat (archiviert):**
- Phase 1: Python Backend Konsolidierung (python-backend/)
- Phase 1b: Go Gateway Handler (SSE/Audio/Tool/Memory Proxy)
- Phase 3: Voice AI Pipeline Code (LiveKit VoicePipelineAgent)
- Phase 4: Frontend SOTA (Shiki, motion, zustand, jotai, auto-animate, Novel, assistant-ui)
- Phase 4b: Code Quality Refactoring (God Component Splitting, Type Safety, Bug Fixes)

---

## Phase 1: → verschoben nach `exec-merge-chat.md`

Package Setup + Agent Chat in Hauptprojekt einbinden → siehe [exec-merge-chat.md](exec-merge-chat.md) Phase 1.

---

## Phase 2: API Routes + Backend Verify

### API Routes (aus exec-08 Task 2.5)

- [x] **2.1:** `agent-chat/api/` Routes nach `nextjs-chat/src/app/api/` kopieren ✅
  - `api/agent/chat/route.ts` — SSE Streaming Proxy (BFF → Go Gateway :8090)
  - `api/agent/approve/route.ts` — Tool Approval
  - `api/agent/completion/route.ts` — One-Shot Completion
  - `api/audio/synthesize/route.ts` — TTS (HTTP-Fallback)
  - `api/audio/transcribe/route.ts` — STT (HTTP-Fallback)

### Verify-Gate: Go Gateway (aus exec-08 Phase 1b)
- Siehe: `exec-eval.md` (infra/stack Verify-Gates)

### Verify-Gate: Agent Chat E2E (aus exec-08 Phase 2)
- Siehe: `exec-eval.md` (infra/stack Verify-Gates)

---

## Phase 3: Voice Verify (aus exec-08 Phase 3)

Code ist komplett (LiveKit VoicePipelineAgent, providers.py, useAgentVoice.ts).
Nur Verify-Gates offen.

- [ ] Voice-Button in Agent Chat → LiveKit Room erstellt
- [ ] User spricht → Agent hoert (STT) → Agent denkt (LLM) → Agent antwortet (TTS)
- [ ] Latenz < 500ms (End-of-Speech → Start-of-Response)
- [ ] Provider-Wechsel: STT/TTS/LLM via ENV umschaltbar ohne Code-Aenderung
- [ ] Gleicher LiveKit SFU bedient Matrix Calls UND Agent Voice parallel

---

## Phase 4: Frontend SOTA Verify (aus exec-08 Phase 4)

Code ist komplett. Nur Verify-Gates offen.

- [ ] Shiki: Code-Block in Agent Chat zeigt Syntax Highlighting mit VS Code Theme
- [ ] Shiki: TypeScript/JSX wird korrekt highlighted
- [ ] Agent Chat Markdown ist HTML-sanitized (XSS mit `<script>` gefiltert)
- [ ] Zustand: `useGlobalChat()` funktioniert ohne Provider-Wrapper
- [ ] Zustand: open/close/toggleMode aendern State korrekt
- [ ] Jotai: Tool-Collapse toggelt ohne Re-Render der ganzen Message-Liste
- [ ] Jotai: usageMap zeigt Tokens pro Nachricht korrekt
- [ ] auto-animate: Neue Nachrichten faden sanft ein
- [ ] motion: Paced Turn Groups animieren korrekt
- [ ] AI SDK v6 DevTools: LLM Calls + Token Usage sichtbar im Browser
- [ ] toModelOutput: Grosse Tool-Outputs fuer Model gekuerzt, UI zeigt volles Ergebnis
- [ ] next.config.ts: Agent Chat startet isoliert auf eigenem Port

### assistant-ui Evaluation (aus exec-08 Task 4.9)
- [ ] Kann es AgentChatThread/Message/Composer ersetzen?
- [ ] Styling-Kontrolle mit shadcn/Tailwind ausreichend?
- [ ] Tool-Call Rendering + Approval Flow?
- [ ] Attachment Support?
- [ ] Performance-Vergleich (Re-Renders, Streaming)

---

## Phase 5: Shared Components (`D:/matrix/shared/`)

> Stand 10.04.2026: shared/ Package erstellt, Location + CodeBlock + ImagePreview implementiert.

- [x] **5.0:** `shared/` Package erstellt (package.json, tsconfig.json, barrel exports)
  - tsconfig path alias `@shared/*` in nextjs-chat + agent-chat konfiguriert
  - `bun install` + `tsc --noEmit` → 0 Errors

- [x] **5.1:** CodeBlock (Shiki + Copy-to-Clipboard) → `shared/src/markdown/CodeBlock.tsx`
  - ShikiHighlighter mit one-dark-pro Theme
  - Copy-Button mit 1.5s Feedback
  - Identisch in beiden Apps — jetzt einmal in shared/

- [x] **5.2:** ImagePreviewModal → `shared/src/media/ImagePreviewModal.tsx`
  - Generische Props: `{src, alt?, onClose}` (kein App-spezifischer Type)
  - Zoom In/Out, Escape-Close, Backdrop-Blur

- [x] **5.3:** Location Components → `shared/src/location/` + `shared/src/geo/`
  - `parseGeoUri()` — geo: URI → {lat, lon, uncertainty}
  - `LocationEmbed.tsx` — iframe OSM embed (0 deps, SSR-safe)
  - `LocationMapInner.tsx` — react-leaflet interaktive Karte (dynamic import)
  - `LocationContent.tsx` in nextjs-chat refactored auf shared/ imports
  - **SDK-Version:** matrix-js-sdk 41.2.0 hat M_LOCATION types, makeLocationContent(), parseLocationEvent()
  - **Agent-Version:** Nur {lat, lon, label} Props, kein matrix-js-sdk

- [ ] **5.4:** SharedMarkdown — vollstaendige Markdown-Abstraktion (zurueckgestellt)
  - Matrix rendert HTML-first (formatted_body), Agent rendert Markdown-first
  - Zu divergent fuer sinnvolle Abstraktion — CodeBlock als Baustein reicht vorerst
  - Evaluieren wenn beide Apps in tradeview-fusion zusammengefuehrt werden

### Verify-Gate Phase 5
- [x] `@shared/*` Imports aufloesbar in nextjs-chat + agent-chat (tsc --noEmit)
- [x] CodeBlock: Shiki Syntax Highlighting mit Copy-Button
- [x] ImagePreview: Fullscreen Zoom in beiden Apps nutzbar
- [x] LocationEmbed: OSM iframe mit korrekten Koordinaten
- [ ] LocationMap: Leaflet-Karte rendert (nur Client-Side, braucht Visual Test)
- [ ] SharedMarkdown: zurueckgestellt (siehe 5.4)

---

## Phase 6: → verschoben nach `exec-merge-chat.md`

Dual-Panel Layout, Cross-UI Integrationen, Layout-Integration → siehe [exec-merge-chat.md](exec-merge-chat.md) Phase 2.

### E2EE fuer Agent Voice (spaeter)
- Aktuell kein Fokus
- Matrix Calls: E2EE via MatrixKeyProvider (bereits implementiert)
- Agent Voice: Erstmals ohne E2EE (lokales Netz)

---

## Risiken

| Risiko | Mitigation |
|---|---|
| Fehlende Hauptprojekt-Abhaengigkeiten | Phase 1.1 — systematisch identifizieren |
| MatrixChat nicht responsive genug | Phase 6 — ggf. separate Mobile-Variante |
| Zwei Chat-Engines = doppelter State | Tabs lazy-loaded, nur aktiver Tab haelt Verbindung |
| Vercel AI SDK Abhaengigkeit | `useChat` + `DefaultChatTransport` — stabil |

---

## Abhaengigkeiten

- exec-05 Phase A+B (NATS + E2EE) — erledigt
- Go Gateway Handler — erledigt (exec-08 Phase 1b)
- Python Agent Service — erledigt (exec-08 Phase 1)
- Voice Pipeline Code — erledigt (exec-08 Phase 3)
- Frontend SOTA Code — erledigt (exec-08 Phase 4)

---

## Abhaengigkeitsgraph

```
exec-04 (UI Rework) ✅
    └── LiveKit SFU + lk-jwt-service installiert
        └── exec-06 Phase 3 (Voice Verify) nutzt gleichen SFU

exec-05 (NATS E2EE Pipeline) ✅ (A4 Verify offen)
    └── exec-06 Phase 2 (Backend Verify braucht NATS-Pfad)

exec-08 (Agent Backend + Voice + SOTA) ✅ archiviert (Code complete)
    └── Alle offenen Verify-Gates → exec-06 Phase 2-4
    └── Shared Components → exec-06 Phase 5
    └── Layout/Panel → exec-06 Phase 6

exec-06 Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
(Package Setup → Backend Verify → Voice Verify → Frontend Verify → Shared Components)
Phase 6 (Dual-Panel) optional, unabhaengig
```
