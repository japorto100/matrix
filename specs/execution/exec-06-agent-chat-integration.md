# exec-06: Shared Components + Agent Chat Verify (konsolidiert mit exec-08)

**Datum:** 28.03.2026 (konsolidiert 30.03.2026, restructured 10.04.2026)
**Status:** Phase 5 in Arbeit
**Abhaengig von:** exec-05 (NATS E2EE Pipeline)
**Zusammengefuehrt aus:** exec-06 (Agent Chat UI) + exec-08 offene Items (Verify-Gates)

> **Restructuring 10.04.2026:** Phase 1 (Package Setup) + Phase 6 (Dual-Panel + Layout)
> verschoben nach `exec-merge-chat.md` (→ 2026-04-20 nach `archive/exec-merge-chat-SUPERSEDED.md`
> da in branch `claude/merge-frontend-chat-ui-2OqmH` realisiert).
> Dieser Slice fokussiert auf Shared Components und Verify-Gates.

> **Deferred (2026-04-20):** True token-streaming (SSE token-by-token statt batch-mit-SSE) lebt in `exec-blocking.md §C7`. Backend ruft heute `graph.ainvoke()` + sendet 1 × `TextDeltaPacket(final)`; AI-SDK-frontend handelt das als "streaming state" ohne token-stream zu sehen. Phase-D-entscheidung.

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

### Phase 4b: Context Surfacing im Agent-Chat

Owner fuer Merge-/Policy-Regeln bleibt [`exec-context.md`](./exec-context.md).
Dieser Slice haelt die konkreten Agent-Chat-Surfaces fest.

- [x] `agent-chat/src/hooks/useChatSession.ts`: liest jetzt Context-/Layer-Diagnostik aus `message.metadata`, nicht nur `promptTokens` / `completionTokens`
- [x] `agent-chat/src/components/AgentChatEventRail.tsx`: zeigt jetzt sichtbare Flags fuer `NO_WORLD_KG`, `NO_WORLD_EVIDENCE`, `NO_PERSONAL_MEMORY`, `NO_PERSONAL_KB`, `WORLD_CLAIM_CONFLICT`
- [ ] `agent-chat/src/components/AgentChatSources.tsx`: neben Web-Quellen auch Memory-/World-/KB-Provenance darstellen koennen oder separaten Provenance-Block einfuehren
- [~] `agent-chat/src/components/AgentChatMessage.tsx`: Usage-Badge zeigt jetzt auch `cachedTokens`; echte `world`-/`personal memory`-Provenance im Message-Body bleibt offen
- [x] `agent-chat/src/AgentChatPanel.tsx`: EventRail ist jetzt so verdrahtet, dass Context-Degradation und Layer-Herkunft fuer den User sichtbar werden
- [~] `agent-chat/src/app/api/agent/chat/route.ts`: bestehender Stream-Pass-through traegt neue Metadata-/Context-Frames unveraendert weiter; expliziter Verify-Lauf bleibt offen

### Verify-Gate Phase 4b

- [ ] Assistant-Antwort mit `personal memory`-Kontext zeigt sichtbare Herkunft (`source_type` / Layer / Provenance)
- [ ] Assistant-Antwort mit `world`-Kontext zeigt `status` + `provenance` und wird nicht wie gesicherte nackte Wahrheit gerendert
- [x] Fehlende Schichten erzeugen sichtbare Agent-Chat-Flags (`NO_WORLD_KG`, `NO_PERSONAL_KB`, ...)
- [ ] Bestehende Web-Sources (`source-url`, `source-document`) bleiben intakt, waehrend zusaetzliche Context-/Provenance-Surfaces dazukommen
- [x] `contextPressure` bleibt sichtbar, ist aber nicht das einzige Context-Signal im Rail / Message-UI

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

---

## §4c Compression-Health-Indicator UI (Phase-B P6 — backend DONE, frontend TBD)

**Status:** Backend endpoint DONE (2026-04-20); `CompressionIndicator.tsx` frontend PENDING (separate frontend-track ticket).
**Cross-ref:** `exec-hermes.md §0` (context_compressor + manual_compression_feedback rows), `exec-context.md §11`, plan `~/.claude/plans/ja-mach-explore-daf-r-glimmering-gizmo.md §P6`.

User-facing **subtle indicator + expand-on-click** (NOT forced-dialog). Enterprise auditability default on — user must see when/what was summarized.

**Backend (DONE):** `GET /api/v1/agent/context/compression-status?thread_id=X&model=Y` → `{thread_id, model, window, thresholds: {pre_save, compaction, emergency}, stage, engine}`. Stateless and cheap — computes from the LiteLLM context-window and the canonical 80/85/95 thresholds. The client enriches with per-turn token counts from its own SSE stream or span-queries.

**Frontend (P6a):** `frontend_merger/src/features/agent/CompressionIndicator.tsx` — status-dot in chat-header:
- Green: `normal`
- Yellow: `compaction` active
- Red: `emergency` + badge with `compressed_turn_count`

**Expand-on-click** panel shows `{stage, usage_pct%, "12 earlier turns summarized"}` + link "show raw (from mempalace)" for reversibility via MemPalace verbatim-archive.

**Inline indicator** in chat-body at the compression-point: `📎 32 earlier turns summarized → click to expand`.

Design-rationale: enterprise contexts (trading/research/legal) need auditable compression. ChatGPT-seamless is good for casual; we're trust-by-audit.

## §4d Title-Gen display + API (Phase-B P6 — backend DONE, UI TBD)

**Status:** Backend generator + migration DONE (2026-04-20); frontend display + async dispatch from runner PENDING.
**Cross-ref:** `exec-hermes.md §0` (title_generator row), `exec-transformersjs.md §3.5` (local-model upgrade path), plan §P6.

Hermes-port: `_ref/hermes-agent/agent/title_generator.py` (~50 LOC).

**Backend (DONE):**
- Migration 024 — `ALTER TABLE agent.sessions ADD COLUMN title TEXT` + index `(user_id, title)` for Control-UI search (Contrarian BLOCKER-2 fix).
- `agent/titles/generator.py` — `generate_title(user_message, assistant_reply, max_words=7)` returns a 3–7 word title via `litellm.acompletion`, with strict sanitisation (first line only, trailing punctuation stripped iteratively, word cap). Fails closed on any error → returns `None`, UI falls back to truncated-first-message label.
- `persist_session_title(session_id, title)` — direct UPDATE on `agent.sessions`, fail-soft on DB error.

**Credential isolation (Contrarian-2 MAJOR-5, enforced):** Title-gen reads `MATRIX_TITLE_GEN_KEY` and `MATRIX_TITLE_GEN_MODEL` (default `claude-haiku-4-5-20251001`) **only**. No CredentialPool call. No user-quota consumption. Absent env-var → title-gen returns `None` and the caller skips gracefully. Title-gen spans are NOT scoped to a user-id, so they never show up in `InsightsEngine.generate(user_id, days)` billing.

**Frontend (P6a):** async trigger after first assistant-response, SSE-push title when ready. Chat-list UI (when it lands) displays titles in session-list.

**Transformers.js upgrade path** (separately in `exec-transformersjs.md §3.5`): swap remote-LLM call for local WebGPU small-model, <200ms, no remote cost, no service-key needed. Phase-C likely.

## §4c.b Manual Compression Feedback UX (Phase-B P6b stub, nice-to-have)

**Status:** STUB — Phase-2 nice-to-have, not default-visible.
**Cross-ref:** `exec-hermes.md §0` (manual_compression_feedback row).

`frontend_merger/src/features/agent/CompressionFeedback.tsx` — opt-in button "improve this summary" in the compression-indicator expand-panel. Modal with textarea for user-correction; POST `/api/v1/agent/compression/{compression_id}/feedback`.

NICHT default-visible (no forced feedback-dialog after every compression). Ingested as fine-tuning-dataset signal in exec-harness backlog.

## Changelog-append (Phase-B)

| Date | Change |
|---|---|
| 2026-04-20 | exec-hermes Phase-B P2 stubs added: §4c (compression-health indicator UI), §4d (title-gen), §4c.b (manual-compression-feedback, Phase-2 nice-to-have). All filled during P6. Title-gen credential-isolation via `MATRIX_TITLE_GEN_KEY` per Contrarian-2 MAJOR-5 fix. |
| 2026-04-20 | Phase-B P6 backend DONE — migration 024 sessions.title, `agent/titles/generator.py`, `GET /api/v1/agent/context/compression-status` endpoint. Frontend components (CompressionIndicator.tsx, CompressionFeedback.tsx) + runner-side async title-gen dispatch remain in the frontend/backend follow-up ticket. |
