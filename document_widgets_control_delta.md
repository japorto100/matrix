# Document Widgets Control Delta

> **Stand:** 14. Maerz 2026 (Rev. 6)
> **Phase:** 22b - Files Surface (eigenstaendige Route, nicht Control-Subtab)
> **Zweck:** Execution-Owner fuer die Files-Oberflaeche (`/files`) — alle Modalitaeten (PDF, Audio, Video, XLSX, Images, Alt-Data). Abgekoppelt von Control.
> **Aenderungshistorie:**
> - Rev. 1 (13.03.2026): Initialer Slice als Control-Subsurface-Konzept
> - Rev. 2 (14.03.2026): **Entscheid: eigener Header-Button "Files" + Route `/files`** (nicht `/control/documents`); Scope auf alle SOTA-2026-Modalitaeten erweitert; Root-MD `FRONTEND_DOCUMENT.md` erstellt
> - Rev. 3 (14.03.2026): **DW1-DW5 + DW13-DW16 implementiert** — Route-Shell, Tab-Bar, BFF-Contracts, Overview-Widget; pre-existing Control-Route-Konflikt behoben
> - Rev. 4 (14.03.2026): **Shell-Architektur abgeschlossen** — `(shell)` Route Group, `GlobalTopBar` (40px persistent), TradingHeader → reine Chart-Toolbar, Error Pages fuer alle 4 Surfaces; DW1-Scope auf GlobalTopBar aktualisiert
> - Rev. 5 (14.03.2026): **DW6-DW12 implementiert** — alle v1 Viewer-Widgets code-complete; `FilesPage` aus Placeholder-Modus in echte Tab-Komponenten migriert
> - Rev. 6 (14.03.2026): **DW17-DW20 implementiert** — Action-Klassen, `DocumentRecord`+`FileAuditLog` Prisma-Modelle, DELETE+Reindex BFF-Routes mit Audit, `ReindexConfirmDialog`; `dev.db` via `prisma migrate reset --force` neu aufgesetzt (user-konsented, dev-only)

---

## 0. Execution Contract

### Scope In

- **Eigenstaendige Route `/files`** mit Header-Button (analog GeoMap-Link) — kein Control-Subtab
- **Alle Modalitaeten** (SOTA 2026): PDF, DOCX, HTML-Filings, XLSX/CSV, Audio, Video, Images, Parquet, Markdown, Alt-Data
- Tab-Bar: `overview | documents | audio | video | data | images | uploads`
- AI-native Patterns: Transkript-Sync, Chunk-Overlay, Vision-Annotation, Streaming-AI-Sidebar
- BFF-Contracts unter `/api/files/*` (nicht `/api/control/documents/*`)
- klare Action-Klassen (`read-only`, `bounded-write`, `approval-write`) konform zu AGENT_SECURITY.md
- klare UI-Degradation statt silent fallback
- Stack-Regel: v1 ohne neue Kern-Framework-Abhaengigkeit

**Entscheid begruendet (14.03.2026):** `/files` ist Nutzer-facing (viewer/analyst/trader), kein Ops-Tab.
Control bleibt auf Runtime/Memory/Sessions/Security fokussiert.


### Scope Out

- Chat-UI oder Chat-Composer-Funktionen
- 1:1 Port von Onyx als Produkt-UI
- direkter Browserzugriff auf Runtime/Tools/Storage
- Trading-Mutationen aus der Document-Surface
- neuer Frontend-Framework-Stack fuer v1

### Priorisierungsregel (verbindlich)

1. Routing + read-only Observability zuerst
2. BFF-Contracts + Gateway-Boundary erzwingen
3. bounded-/approval-write nur mit Audit + Policy
4. research-nahe Zusatzwidgets nach stabiler v1-Basis

### Mandatory Upstream Sources

- `docs/FRONTEND_DOCUMENT.md` ← **Root-MD fuer diese Surface (neu, Rev.1 14.03.2026)**
- `docs/storage_layer.md` ← Object-Store, Signed-URLs, Persistenzklassen
- `docs/UNIFIED_INGESTION_LAYER.md` ← UIL-Pipeline (Auto-Ingest)
- `docs/RAG_GRAPHRAG_STRATEGY_2026.md` ← Vector-Store, Chunk-Strategie
- `docs/specs/FRONTEND_ARCHITECTURE.md`
- `docs/specs/SYSTEM_STATE.md`
- `docs/GO_GATEWAY.md`
- `docs/AGENT_SECURITY.md`
- `docs/CONTEXT_ENGINEERING.md`
- `docs/MEMORY_ARCHITECTURE.md`

### Baseline (wichtig)

- Control-Surface ist als Gesamtziel definiert, Document-Subsurface ist bislang nicht als eigener Execution-Slice operationalisiert.
- Bestehender Stack reicht fuer v1:
  - `next`/`react`
  - `@tanstack/react-query`
  - `@tanstack/react-table`
  - `@tanstack/react-virtual`
  - `@dnd-kit/*` (optional)
- Zielkette bleibt verbindlich:
  - `UI -> Next BFF -> Go Gateway -> downstream services`

---

## 1. Offene Deltas

### A. Routing und Surface Shell

- [x] **DW1** "Files" Surface-Button in `GlobalTopBar` (aktiv via `usePathname`, `data-testid="link-files"`, `FolderOpen`-Icon) — 14.03.2026
  - ~~TradingHeader.tsx~~ — obsolet, Files-Button lebt jetzt in GlobalTopBar (Shell-Refactor)
- [x] **DW2** Route `src/app/(shell)/files/[[...tab]]/page.tsx` + `layout.tsx` in `(shell)` Route Group angelegt — 14.03.2026
- [x] **DW3** Tab-Bar `FilesTopNav.tsx` — URL-getrieben via `usePathname`: `overview | documents | audio | video | data | images | uploads`; Overview-Tab aktiv auch auf `/files` root — 14.03.2026
- [x] **DW4** `FilesPlaceholderTab.tsx` — sichtbarer Degradation-State fuer nicht-implementierte Tabs (DW.V8 erfuellt) — 14.03.2026

### A1. Shell-Architektur (Prerequisite, 14.03.2026)

> Cross-cutting — Vollstaendig in `trading_page_refactor_delta.md` Phase L dokumentiert.
> Hier nur Auswirkungen auf die Files-Surface.

- [x] **DW-SH1** `src/app/(shell)/layout.tsx` — Route Group mit `GlobalTopBar` als persistenter 40px Nav; alle 4 Surfaces darin (trading, geopolitical-map, control, files) — 14.03.2026
- [x] **DW-SH2** `GlobalTopBar` (`src/components/GlobalTopBar.tsx`) — Logo + 4 Surface-Buttons (Trading|Map|Control|Files) mit Active-State + Uhr + Account + Theme; kein Doppel-Header — 14.03.2026
- [x] **DW-SH3** `TradingHeader` zu reiner Chart-Toolbar reduziert (`role="toolbar"`) — Logo/Nav/Uhr/Account/Theme entfernt — 14.03.2026
- [x] **DW-SH4** Error Pages fuer alle 4 Surfaces — `(shell)/files/error.tsx` (`FolderX`), `(shell)/control/error.tsx` (`SlidersHorizontal`), `(shell)/trading/error.tsx` (`TrendingDown`), `(shell)/geopolitical-map/error.tsx` (pre-existing `ShieldX`) — 14.03.2026

### B. v1 Read-only Widgets

- [x] **DW5** `FilesOverviewTab` — Total Docs / Indexing Pending / Failed Jobs + Recent Uploads; `useQuery` + sichtbarer Error-State mit Fehlercode (`STORAGE_UNAVAILABLE`) — 14.03.2026
- [x] **DW6** `DocumentViewer` + `FilesDocumentsTab` — `@react-pdf-viewer/core` v3.12 + `defaultLayoutPlugin` (Toolbar/Search/Thumbnails); CDN Worker `pdfjs-dist@3.11.174`; `dynamic()` SSR:false; File-List + FileSearch links; Presigned-URL `staleTime` 10min — 14.03.2026
- [x] **DW7** `AudioPlayer` + `useWaveSurfer` Hook + `FilesAudioTab` — `wavesurfer.js` v7 `WaveSurfer.create()`; events: ready/audioprocess/play/pause/finish/error; `formatTime()`; Placeholder "Transcript sync v1.5" — 14.03.2026
- [x] **DW8** `VideoPlayer` + `useHls` Hook + `FilesVideoTab` — `hls.js` v1.6 `Hls.isSupported()` guard; Safari native HLS fallback via `video.src`; `<video controls playsInline aspect-video>` — 14.03.2026
- [x] **DW9** `FilesDataTab` — Placeholder (SheetJS + TanStack Table als v1.5); sichtbarer Degradation-State mit `TableIcon` + `Construction` — 14.03.2026
- [x] **DW10** `ImageViewer` + `FilesImagesTab` — `next/image` fill+`object-contain`; Lightbox-Overlay on click; SVG-Annotation-Layer `preserveAspectRatio="none"` (v1.5 placeholder); `unoptimized` fuer blob-URLs — 14.03.2026
- [x] **DW11** `UploadDropzone` + `FilesUploadsTab` — `react-dropzone` v15 `useDropzone`; `ACCEPTED_TYPES` map; `maxSize` 5MB; zwei-stufig: POST `/api/files/upload-intent` → PUT `upload_url`; per-file Status uploading/done/error — 14.03.2026
- [x] **DW12** `FileSearch` — `fuse.js` v7 `Fuse` instance; `threshold: 0.35`; keys `["name","type"]`; `useMemo` fuer Instanz; X-Button Clear; "No files match" Empty-State — 14.03.2026

### C. BFF / Contract / Boundary

- [x] **DW13** Next.js API-Routes unter `/api/files/*` — 14.03.2026:
  - `GET /api/files` — Liste + Metadaten (`src/app/api/files/route.ts`)
  - `GET /api/files/[id]/url` — frische Presigned-Download-URL TTL 15 min (`src/app/api/files/[id]/url/route.ts`)
  - `POST /api/files/upload-intent` — Presigned-Upload-URL von Go anfordern (`src/app/api/files/upload-intent/route.ts`)
  - `GET /api/files/search` — Proxy zu Meilisearch / fuse.js-Index (`src/app/api/files/search/route.ts`)
- [x] **DW14** `X-Request-ID` in allen 4 BFF-Routes gesetzt (generate via `crypto.randomUUID()` falls nicht vorhanden) — 14.03.2026
- [x] **DW15** `cache: "no-store"` + konsistentes Fehler-Schema (`NO_DOCUMENT_INDEX`, `STORAGE_UNAVAILABLE`) in allen Routes — 14.03.2026
- [x] **DW16** Go-Gateway-Boundary eingehalten: Browser trifft nur `/api/files/*` BFF, niemals direkt Object Store — 14.03.2026

### D. Action-Klassen / Security / Audit

- [x] **DW17** `src/features/files/lib/action-classes.ts` — `ActionClass` + `FileAction` Typen; `FILE_ACTION_CLASSES` Map; `getActionClass()` + `requiresApproval()` Helpers; `FileAuditPayload` Interface — 14.03.2026
- [x] **DW18** Upload als `bounded-write` + Audit: `upload-intent/route.ts` schreibt `FileAuditLog` nach erfolgreichem Intent; `DELETE /api/files/[id]/route.ts` (neu) proxied Go Gateway + schreibt Audit (ok/failed); `src/lib/server/file-audit.ts` shared helper (`writeFileAudit`, niemals request-blockend) — 14.03.2026
- [x] **DW19** `POST /api/files/[id]/reindex/route.ts` — approval-write, `x-confirm-token` Header-Gate (403 ohne Token), Audit mit `expiresAt`; `ReindexConfirmDialog.tsx` — 2-Step (Dateiname eintippen + 30s Countdown), Token via `crypto.randomUUID()`, Error-State mit Code — 14.03.2026
- [x] **DW20** `DocumentRecord` + `FileAuditLog` in `prisma/schema.prisma` (SQLite-konform, alle String statt Enum); `bun run db:generate` + `prisma migrate reset --force` (dev.db, user-konsented 14.03.2026); Indizes auf status/ticker/type/action/actorUserId — 14.03.2026

### E. AI-native Widgets (v1.5)

- [ ] **DW21** Transkript-Sync: Audio/Video-Player + scrollbares Transcript-Panel (Speaker-Farben, Timestamp-Seek)
- [ ] **DW22** Chunking-Overlay im PDF-Viewer (Custom-Plugin — zeigt RAG-Chunk-Grenzen + Token-Count)
- [ ] **DW23** AI-Sidebar-Stream: `@ai-sdk/react` `useCompletion` — Selected-Text → Streaming-Summary
- [ ] **DW24** Image-AI-Annotation: Upload → Claude Vision → SVG-Overlay (pattern_type, key_levels, confidence)
- [ ] **DW25** Kontext-Degradation sichtbar (`NO_DOCUMENT_INDEX`, `TRANSCRIPT_PENDING`, `CHUNK_STALE`)

### F. Stack-Additions (mit Begruendung)

| Library | Version | Begruendung | Phase |
|---------|---------|------------|-------|
| `@react-pdf-viewer/core` | v3.x | PDF Toolbar/Search/Thumbnails; react-pdf alleine zu basic | v1 |
| `wavesurfer.js` | v7 | Waveform + Region-Sync; kein Ersatz im Stack | v1 |
| `hls.js` | v1.5 | HLS-Streaming; Safari native fallback | v1 |
| `react-dropzone` | v14 | DnD-Upload; minimal, kein tus-Overhead fuer <5MB | v1 |
| `uppy` + tus | v4 | Resumable fuer grosse Files (Earnings-Calls, Videos) | v1.5 |
| `fuse.js` | v7 | Client-side Fuzzy auf Metadaten; schon fast im Stack | v1 |
| `SheetJS (xlsx)` | 0.20 | XLSX-Parse → TanStack Table; kein neuer Renderer | v1.5 |
| `meilisearch-js` | 0.47+ | Server-Fulltext; self-hosted Meilisearch | v1.5 |

---

## 2. Verify-Gates

### Shell / Navigation (Live-Verify noetig)

- [x] **DW.V1** `/files` ist ueber `GlobalTopBar`-Button erreichbar, reload-stabil, Tab-Bar URL-getrieben (14.03.2026)
- [ ] **DW.V10** `GlobalTopBar` sichtbar auf allen 4 Surfaces (`/trading`, `/geopolitical-map`, `/control`, `/files`) — Live-Verify
- [ ] **DW.V11** Active-State im GlobalTopBar korrekt: jeweils nur der aktive Surface-Button highlighted — Live-Verify
- [ ] **DW.V12** `TradingHeader` zeigt kein Logo / keine Nav-Links mehr — reine Chart-Toolbar — Live-Verify
- [ ] **DW.V13** Error Pages ausloesbar (throw in Surface-Component → framer-motion Error-Card erscheint mit Reset-Button) — Live-Verify je Surface
- [ ] **DW.V14** Surface-Wechsel via GlobalTopBar ist instant (kein Full-Page-Reload, App-Router Link-Prefetch) — Live-Verify

### Files Surface / BFF (Live-Verify noetig)

- [ ] **DW.V2** Alle v1 Widgets laufen read-only stabil inkl. Empty/Error/Loading — `FilesOverviewTab` zeigt Fehlercode wenn Gateway unavailable (DW5)
- [ ] **DW.V3** `FilesTopNav`-Tabs switchen deterministisch; URL entspricht aktivem Tab; Reload bleibt auf Tab — Live-Verify
- [ ] **DW.V4** Overview-Tab: Total/Pending/Failed-Zahlen + Recent-Uploads-Liste laden via `GET /api/files` — Live-Verify (Stack noetig)
- [x] **DW.V5** keine Browser-Direktpfade zu Object Store — BFF-Boundary erzwungen (DW16, 14.03.2026)

### Action-Klassen / Security (Live-Verify noetig)

- [ ] **DW.V6** Upload-Action als `bounded-write` — `FileAuditLog` Eintrag in SQLite nach Upload-Intent nachweisbar (DW17+DW18) — Stack noetig
- [x] **DW.V7** `ReindexConfirmDialog`: 30s-Countdown, Confirm-Button erst bei korrektem Dateinamen aktiv, BFF liefert 403 ohne `x-confirm-token` — code-complete 14.03.2026
- [ ] **DW.V7-LV** `ReindexConfirmDialog` UX end-to-end: Dateiname eingeben, Countdown sichtbar, 403 ohne Token verifiziert, `FileAuditLog` Eintrag (actionClass=approval-write, expiresAt gesetzt) in dev.db nachweisbar — Stack noetig
- [ ] **DW.V22** DELETE `204` via BFF + `FileAuditLog` Eintrag (status=ok) in dev.db nachweisbar (DW18) — Stack noetig
- [x] **DW.V23** `DocumentRecord` + `FileAuditLog` Tabellen in dev.db vorhanden — `prisma migrate reset --force` durchgefuehrt (14.03.2026, user-konsented), Prisma Client regeneriert ✓

### Degradation / Stack-Regel

- [x] **DW.V8** Degradation-Flags sichtbar gerendert — `FilesPlaceholderTab` + Error-States in Overview mit Fehlercode (DW4, 14.03.2026)
- [x] **DW.V9** Kein neuer Kern-UI-Framework eingefuehrt — viewer-spezifische Libs (wavesurfer.js, hls.js, react-dropzone, fuse.js, @react-pdf-viewer, pdfjs-dist) waren alle in Section F vorab geplant und genehmigt; kein neues State-Management / Router / Component-System (14.03.2026)

### Viewer-Widgets (Live-Verify noetig — Stack + Storage Gateway)

- [ ] **DW.V15** `DocumentViewer` rendert PDF, Search-Plugin und Thumbnail-Sidebar funktional (DW6) — Stack noetig
- [ ] **DW.V16** `AudioPlayer` Waveform sichtbar, Play/Pause/Seek, Loader-State vor `ready` (DW7) — Stack noetig
- [ ] **DW.V17** `VideoPlayer` ladet HLS-Stream, Safari native fallback aktiv (DW8) — Stack noetig
- [x] **DW.V18** `FilesDataTab` zeigt Degradation-Placeholder korrekt — `TableIcon` + `Construction` + "DW9 — SheetJS v1.5" Text sichtbar, code-complete 14.03.2026
- [ ] **DW.V19** `ImageViewer` zeigt Bild + Lightbox-Toggle + SVG-Layer leer (v1) (DW10) — Stack noetig
- [ ] **DW.V20** `UploadDropzone` akzeptiert Drag+Drop, POST `/api/files/upload-intent` liefert Presigned-URL, per-file Status korrekt (DW11) — Stack noetig
- [ ] **DW.V21** `FileSearch` fuzzy-sucht Metadaten-Index deterministisch, kein stiller Fallback (DW12) — Stack noetig

---

## 3. Evidence Requirements

- Screenshots/Recording fuer alle v1 Widgets (happy path + empty + error)
- API Contract Samples fuer `/api/files/*` (happy + degraded + error)
- Request-Trace fuer Gateway-Boundary-Nachweis (`UI -> BFF -> Gateway`)
- Rollen-/Action-Matrix Nachweis fuer `bounded-write` und `approval-write`
- Audit-Beispiele mit Pflichtfeldern fuer mutierende Aktionen
- kurzer Dependency-Nachweis: vorhandener Stack genutzt, keine v1-Framework-Ausweitung

---

## 4. Propagation Targets

- `docs/specs/EXECUTION_PLAN.md`
- `docs/specs/FRONTEND_ARCHITECTURE.md`
- `docs/specs/execution/control_surface_delta.md`
- `docs/specs/execution/frontend_enhancement_delta.md`
- `../../../../FRONTEND_DOCUMENT.md`
