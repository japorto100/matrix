# exec-05 — Control-UI Viewer Packages + Files/Models Polish

**Status:** Extracted from archived `exec-19 §3.9 + §5b.6-§5b.10 + §5c.6` (2026-04-18)
**Branch:** `claude/merge-frontend-chat-ui-2OqmH`
**Owner der extracted sections:** exec-19 (devstack-consolidation) vor Archive
**Cross-refs:** exec-15 (Memory Control-UI), exec-16 (LLM Provider Gateway — Reasoning-Composer-Pfad), exec-media-ingestion (viewer payloads)

## Warum

Drei verschiedene UI-Polish-Bündel lagen in exec-19, die logisch weder zu
devstack-consolidation noch zu einem der anderen fachlichen Specs gehören:

1. **Viewer-Packages** für Files-Tab (Wave-Form, Spreadsheet, Document-Preview) — Dependencies-Adds + neue Components.
2. **Model-Discovery Polish** (Dynamic-Model-Filtering) — URL-State via `nuqs`, Postgres-Cache, Stale-while-revalidate, Filter/Sort-Kontrolle.
3. **Reasoning-Cycle-Button** in agent-chat + control-ui Composer — exec-19 §5c.6 Frontend-Seite (Backend-Portion wurde nach exec-16 Phase 4.5 gezogen).

Diese Spec macht den Frontend-Merge-Slice zum Owner dieser drei Bündel
damit exec-19 archiviert werden kann ohne Content-Loss.

## Bündel 1 — Viewer Packages (aus exec-19 §3.9)

Control-UI Files-Tab braucht Renderer für Media-Pipeline-Outputs (exec-media-ingestion):

- [ ] `bun add wavesurfer.js @wavesurfer/react` — Waveform + Playhead für Audio-Files
- [ ] `bun add exifr` — EXIF-Metadaten-Extraction für Bild-Preview (Kamera, GPS, Datum)
- [ ] `bun add xlsx` — XLSX-Sheet-Preview (read-only grid)
- [ ] `bun add docx-preview` — .docx Inline-Preview (Original-Formatting)
- [ ] `bun add react-markdown rehype-raw rehype-sanitize remark-gfm` — Enhanced Markdown-Renderer (safe HTML + GFM + Tables)

### Viewer-Components (after bun-add)

- [ ] `control-ui/src/features/files/viewers/AudioWaveformViewer.tsx`
- [ ] `control-ui/src/features/files/viewers/ImageWithExifViewer.tsx`
- [ ] `control-ui/src/features/files/viewers/SheetViewer.tsx`
- [ ] `control-ui/src/features/files/viewers/DocxViewer.tsx`
- [ ] `control-ui/src/features/files/viewers/MarkdownViewer.tsx` (enhanced, ersetzt rohen `<pre>`)

### Viewer-Dispatch

- [ ] `control-ui/src/features/files/FileViewer.tsx` — Dispatch-Logik basierend auf `contentType` / `mediaClass`:
  - `audio/*` → AudioWaveformViewer
  - `image/*` → ImageWithExifViewer
  - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` → SheetViewer
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document` → DocxViewer
  - `text/markdown` → MarkdownViewer
  - fallback → existing text/hex-viewer

## Bündel 2 — Model-Discovery Polish (aus exec-19 §5b.6-§5b.10)

### URL-State

- [ ] URL-State mit `nuqs` — Filter-Auswahl (provider, reasoning-capable,
  price-tier, Sort-by) wird in Query-Params persistiert damit Refresh/Back
  den State erhält und Links-zum-Share-"Filtered-View" funktionieren.

### Cache-Strategie

- [ ] Persistenter Cache in Postgres: Tabelle `agent.llm_models_cache`
  (Model-Metadata von OpenRouter / Anthropic / OpenAI; refreshed per
  Background-Worker alle 6h). Heute: Page-Load ruft Live-API → Latenz
  + Rate-Limit-Risiko.
- [ ] Stale-While-Revalidate: alte Cache-Daten sofort anzeigen während
  im Background neu geholt wird.

### Filter/Sort

- [ ] Neuer Filter **"Auto-Mode Capable"** — flagt Modelle die
  `reasoning_effort`-Parameter akzeptieren. **Gate:** Backend-Check in
  exec-16 Phase 4.5.1 muss sagen "diese Model-ID kann reasoning_effort".
- [ ] Sortierung nach `reasoning_quality_score` (Langfuse-basiert,
  post-Live-Gates von exec-16 Phase 4.5) — optional.

## Bündel 3 — Reasoning-Cycle-Button (aus exec-19 §5c.6)

Frontend-Seite des exec-16-Phase-4.5-Features. Backend (LiteLLM
pass-through + SSE streaming) ist pre-transfer landed; hier nur die UX.

- [ ] Reasoning-Cycle-Button im Composer hinzufuegen (analog zu
  agent-chat's existierendem Cycle — Low/Medium/High/Auto).
- [ ] State in Room-Timeline persistent per Room (wie Model-Selection).
  Key: `localStorage.reasoning_effort_{roomId}` oder Postgres-backed
  User-Pref.
- [ ] Body-Forward im `/api/agent/chat` Route — Frontend sendet
  `{ reasoning_effort: "high" }` → Go-Gateway → Python-Agent state.

## Verify-Gates

### Viewer-Gates

- [ ] Upload 1MB MP3 → Files-Tab zeigt Waveform mit Play-Controls.
- [ ] Upload 5MB JPG mit EXIF → Files-Tab zeigt Bild + Kamera/GPS/Datum.
- [ ] Upload XLSX → Files-Tab zeigt Sheet-Preview (erste 100 Rows).
- [ ] Upload DOCX → Files-Tab zeigt formatierten Text.
- [ ] Upload MD → Files-Tab rendert GFM (Tables + Checkbox-Lists).

### Model-Discovery-Gates

- [ ] Page-Load → Models aus Postgres-Cache (< 50ms), Background-Refresh läuft.
- [ ] Filter "reasoning-capable" + "openrouter" → URL hat `?providers=openrouter&caps=reasoning`, Refresh erhält State.
- [ ] Sort by `reasoning_quality_score` → Top-5 sind Models mit höchstem Score (post-Langfuse-integration).

### Reasoning-Composer-Gates

- [ ] Cycle-Button 4 Werte (low/medium/high/auto) sichtbar.
- [ ] User setzt "high", sendet Nachricht → Agent bekommt `reasoning_effort: "high"` in state, Thinking-Delta Stream sichtbar.
- [ ] Room-Wechsel → Reasoning-State persistent pro Room.

## Abhängigkeiten

- **exec-media-ingestion** — Payloads die die Viewer rendern (Waveform-Data, EXIF-JSON, Pipeline-Outputs).
- **exec-16 Phase 4.5.1** — Backend `_compute_auto_effort` + Model-Capability-Flag für "Auto-Mode Capable" Filter.
- **Control-UI Slice** (existing `frontend_merger/src/features/control/`) — Viewers + Model-Discovery-Page live here.
- **agent-chat Slice** (existing `frontend_merger/src/features/agent-chat/`) — Reasoning-Cycle-Composer.
