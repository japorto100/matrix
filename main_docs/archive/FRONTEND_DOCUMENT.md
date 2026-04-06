# FRONTEND_DOCUMENT — Files & Media Surface

> **Stand:** 14. Maerz 2026 (Rev. 1)
> **Zweck:** Root-MD fuer die "Files"-Oberflaeche in TradeView Fusion.
> Definiert Modalitaeten, UI-Stack, AI-native Patterns, Storage-Contract und Abgrenzung.
> **Aenderungshistorie:**
> - Rev. 1 (14.03.2026): Initiales Root-MD — alle Modalitaeten, SOTA 2026 Stack,
>   AI-native Patterns, Storage-Abgrenzung, Entscheid eigener Header-Button

---

## 1. Positionierung und Entscheid

### 1.1 Eigener Header-Button "Files"

- **Entscheid:** `/files` ist eine eigene Route mit eigenem Header-Button — kein Control-Subtab.
- **Begruendung:**
  - Files ist eine Nutzer-facing Feature-Surface (Research, Uploads, Viewer), kein ops-naher Admin-Tab.
  - Auch `viewer`- und `analyst`-Rollen brauchen Zugang ohne Control-Berechtigung.
  - Kongruent mit GeoMap-Button-Pattern im TradingHeader.
- **Header-Position:** zwischen GeoMap-Link und bestehenden Rechts-Controls.
- **Route:** `src/app/files/page.tsx` (Next.js App Router).
- **Navigation-Tab-Bar in `/files`:**
  - `overview` | `documents` | `audio` | `video` | `data` | `images` | `uploads`

### 1.2 Abgrenzung zu Control und Chat

| Surface | Zweck | Wer greift zu |
|---------|-------|---------------|
| `/files` | Research-Files, Uploads, AI-Viewer | viewer, analyst, trader, admin |
| `/control` | Ops, Runtime, Memory, Sessions, Security | analyst, trader, admin |
| Chat-Composer | Inline-File-Attach fuer Agent-Kontext | alle |

### 1.3 Abgrenzung zu Storage Layer und UIL

- Files-Surface ist nur das **Frontend-Gateway** — kein eigener Persistenz-Stack.
- Binaerdaten liegen in **Object Store** (SeaweedFS / R2) — gemaess `storage_layer.md`.
- Rohingest (YouTube-Transkripte, Reddit) gehoert zu **UIL** (`UNIFIED_INGESTION_LAYER.md`).
- Files-Surface zeigt Artefakte die bereits indexiert und im Object Store sind.
- Zugriffspfade: signierte URLs via Go Gateway, nie direkter Browser-Zugriff.

---

## 2. Modalitaeten — vollstaendige Matrix (SOTA 2026)

### 2.1 Dokumente / Text

| Format | Quellen im Trading-Kontext | Frontend-Pattern |
|--------|---------------------------|-----------------|
| **PDF** | SEC EDGAR (10-K, 10-Q, 8-K), Earnings Releases, Prospekte, Analyst-Reports | `@react-pdf-viewer/core` v3.x + Plugins |
| **XBRL / iXBRL** | EDGAR Inline-XBRL (Pflicht seit 2023), strukturierte Finanztabellen in HTML | Server-Parsing → JSON → TanStack Table |
| **DOCX** | Analyst-Memos, AI-generierte Research-Drafts, interne Reports | Server: Gotenberg → PDF → react-pdf-viewer |
| **HTML / HTM** | EDGAR SGML-Wrappings, 8-K-Filings als plain HTML | sanitized HTML-Render + DOMPurify |
| **XLSX / CSV** | Trade Blotter-Exports, Options Chains, Factor-Daten, Quant-Signals | SheetJS v0.20 → TanStack Table (read-only) |
| **Parquet / Arrow** | Backtester-Archive, Factor Libraries (Riskfolio-Output) | Server-Streaming → Python → JSON; kein Browser-Parquet |
| **JSON / NDJSON** | Bloomberg/Refinitiv Feeds, normalisierte OHLCV-Snapshots | bereits im Stack |
| **Markdown** | LLM-generierte Research-Memos (zunehmend first-class Artefakt) | `react-markdown` + `remark-gfm` |

### 2.2 Audio

| Format | Quellen | Frontend-Pattern |
|--------|---------|-----------------|
| **MP3 / M4A** | Earnings-Call-Recordings (Seeking Alpha, Company IR), Fed-Speeches, FOMC Press Conferences | `wavesurfer.js` v7 + Region-Plugin |
| **WAV** | Hochqualitaets-Podcast-Archive | Transcode zu Opus/WebM on ingest (Python-Backend) |
| **Opus / WebM** | Komprimiertes Streaming-Format (Edge-Delivery) | Nativ via wavesurfer.js |
| **HLS (m3u8)** | Conference-Recordings, Live-Fed-Streams (>30 min) | `hls.js` v1.5 + wavesurfer HLS-Plugin |

**AI-native Audio-Pattern:**
- Ingest: `faster-whisper` v1.x (CTranslate2, Python-Backend) → Transkript als JSON `[{start, end, speaker, text}]`
- Diarisation: `pyannote-audio` → Speaker-Labels im Transkript-JSON
- Frontend: Transcript-Panel synced zu wavesurfer Regions (Timestamp-Klick → Seek)
- Storage: Transkript-JSON in DB (`DocumentRecord`), Audio-Binary in Object Store

### 2.3 Video

| Format | Quellen | Frontend-Pattern |
|--------|---------|-----------------|
| **MP4 (H.264/H.265)** | Analyst Day, Investor Day Webcasts, Conference Replays | `hls.js` v1.5 + custom React Hook |
| **WebM (VP9/AV1)** | YouTube-Analyst-Content, Bloomberg TV Clips | AV1 SOTA quality-per-bit; Safari 17+ |
| **HLS / DASH** | Long-form Conferences (2h+), Live Macro Events | HLS fuer Kompatibilitaet, DASH fuer DRM |
| **YouTube-embed** | IR-Webcasts auf YouTube/Vimeo | `react-player` v2.16 (uniformes Wrapper-Pattern) |

**Pattern fuer lange Recordings:**
- HLS-Streaming + Chapter-Markers (aus Transkript-Timestamps generiert)
- `hls.js` + natives Safari HLS Fallback (kein JS-Overhead auf iOS)
- Thumbnail-Seeking via VTT-Sprite-Sheet (generiert server-seitig)

### 2.4 Bilder / Charts

| Format | Quellen | Frontend-Pattern |
|--------|---------|-----------------|
| **PNG / JPEG** | Annotierte Chart-Screenshots, Trade-Setups, User-Uploads | Next.js `<Image>` + AVIF/WebP auto-convert |
| **SVG** | Exportierte TradingView/D3-Charts | Inline SVG, re-stylable |
| **AVIF / WebP** | Optimierte Delivery via Next.js Image Optimization | automatisch via `next/image` |
| **TIFF** | Gescannte Legacy-Filings, Satelliten-Bilder (Commodity Intelligence) | Server-convert → PNG |

**AI-native Image-Pattern:**
- Upload → Presigned URL → Storage → Trigger Claude Vision / Multimodal-Analyse
- Output: `{pattern_type, key_levels, trend, confidence}` als Annotation gespeichert
- Frontend: semi-transparentes SVG-Annotation-Layer ueber `<img>`

### 2.5 Alternative / Emerging Data (2025-2026)

| Modalitaet | Quelle | Relevanz fuer Trading |
|-----------|--------|----------------------|
| **Satelliten-Bilder** (PNG-Tiles) | Planet Labs, Spire | Parking-Lot-Counts, Tanker-Tracking (Commodity Intelligence) |
| **Web-Scrape-Snapshots** (MHTML/WARC) | Archivierte News zum Signal-Zeitpunkt | Evidenz-Konservierung, Anti-Hindsight |
| **Sensor/IoT-Feeds** (CSV/Arrow) | Agrar, Energie | Rohstoff-Signale |
| **Social-Media-Archive** (JSONL) | Twitter/X API v2, Reddit Pushshift | Sentiment-Archive |
| **PPTX / Keynote** | Analyst-Day-Slides | Server: Docling → Markdown + Images |
| **LLM-Research-Memos** (Markdown + Citations) | Intern generiert | First-class Artefakt-Typ; Inline-Rendering |
| **Earnings-Transcript-JSON** | Refinitiv, Seeking Alpha API | Strukturiert; Speaker + Q&A Tags |
| **Options-Flow-Tape** (NDJSON) | Unusual Whales, Market Chameleon | Streaming-Display; nicht gespeichert |

---

## 3. SOTA 2026 Frontend-Stack

### 3.1 Document Viewer

| Beduerfnis | Library | Version | Begruendung |
|-----------|---------|---------|------------|
| PDF Viewer (Feature-reich) | `@react-pdf-viewer/core` + Plugins | v3.x | Toolbar, Search, Thumbnails, Bookmarks; Plugin-Architektur |
| PDF Viewer (Basis) | `react-pdf` | v9.x | ESM-only, pdfjs-dist Worker; einfacher Use-Case |
| DOCX → Anzeige | Gotenberg (Docker) → PDF → viewer | — | Server-side; kein Browser-DOCX-Rendering |
| XLSX (read-only) | `SheetJS (xlsx)` v0.20 → TanStack Table | 0.20.x | Parse → JSON → bestehende Table-Library |
| HTML-Filings | sanitized `dangerouslySetInnerHTML` + DOMPurify | 3.x | EDGAR HTML-Filings direkt; kein iframe |
| Chunking-Overlay | `react-pdf-viewer` Custom-Plugin | — | Zeigt RAG-Chunk-Grenzen als Annotations im PDF |

### 3.2 Audio

| Beduerfnis | Library | Version |
|-----------|---------|---------|
| Waveform + Regions | `wavesurfer.js` | v7.x |
| HLS-Audio | `hls.js` | v1.5.x |
| Uniform-Embed (YouTube/SoundCloud) | `react-player` | v2.16.x |

### 3.3 Video

| Beduerfnis | Library | Version |
|-----------|---------|---------|
| HLS-Streaming | `hls.js` + custom React Hook `useHls` | v1.5.x |
| Vollstaendiger Player (DRM, DASH) | `video.js` | v8.x |
| Kompositionsfaehig / neu | `@vidstack/react` | evaluieren |
| YouTube / Vimeo Embeds | `react-player` | v2.16.x |

### 3.4 Upload

| Beduerfnis | Library | Version |
|-----------|---------|---------|
| Grosse Files, Resumable (>5MB) | `uppy` v4 + tus-js-client | v4.x |
| Einfacher DnD-Upload (CSV, PNG) | `react-dropzone` | v14.x |
| Protokoll | tus (resumable) oder S3 Multipart | — |
| Presigned URLs | Go Gateway → AWS SDK / R2 SDK | bestehend |

### 3.5 Search

| Beduerfnis | Library |
|-----------|---------|
| In-Dokument (PDF) | `@react-pdf-viewer` Search-Plugin |
| Client-side Fuzzy (Metadaten) | `fuse.js` v7 |
| Offline-capable Hybrid (BM25 + Vector) | `orama` v2 (WASM) |
| Server-side Volltextsuche | Meilisearch + `meilisearch-js` v0.47+ |

### 3.6 AI-native UI

| Pattern | Library |
|---------|---------|
| Streaming AI-Response | `@ai-sdk/react` (`useChat`, `useCompletion`) |
| Markdown-Render | `react-markdown` + `remark-gfm` |
| Rich-Text-Annotation | `tiptap` (optional, v1.5 Schritt) |

---

## 4. Backend-Integration (Python + Go)

### 4.1 Docling — Document-Ingest-Pipeline

```
Upload (uppy/tus) → Go Presigned URL → R2/SeaweedFS
  → Storage-Event → Go Webhook → Python indicator/memory-service
  → Docling (PDF/DOCX/PPTX → Markdown + Tables + Images)
  → Chunks → ChromaDB (Vector) + Meilisearch (Fulltext)
  → Metadata → SQLite/Postgres (DocumentRecord)
```

- **Docling** (IBM, 2024): ersetzt PyMuPDF + pdfplumber als SOTA; integriert mit LangChain/LlamaIndex.
- **faster-whisper** v1.x: Audio → Transkript JSON; auf Python-Backend, kein Cloud-API.
- **pyannote-audio**: Speaker-Diarisation; optional, aktivierbar per Flag.

### 4.2 Go Gateway — Signed URL Flow

```
Browser → POST /api/files/upload-intent (Go) → Presigned URL (R2/S3)
Browser → PUT <presigned-url> (direkt zu R2, kein Go-Proxy)
R2 → Webhook → Go → Python-Ingest-Trigger
Browser → GET /api/files/{id}/url (Go) → frische Presigned-Download-URL (TTL 15 min)
```

Regeln (aus `storage_layer.md`):
- Kein direkter Browser-Root-Access.
- Go ist Policy-Owner fuer ACL, Retention, Audit.
- Presigned-URLs nie serverseitig cachen (zeitgebunden).

### 4.3 Prisma DocumentRecord (Erweiterung)

```typescript
model DocumentRecord {
  id          String   @id @default(cuid())
  type        String   // "pdf" | "docx" | "xlsx" | "audio" | "video" | "image" | "parquet" | "markdown"
  subtype     String?  // "10-K" | "earnings-call" | "analyst-report" | "trade-screenshot" | "satellite"
  ticker      String?
  title       String
  sourceUrl   String?
  storageKey  String   // Object-Store-Key (R2/SeaweedFS)
  mimeType    String
  sizeBytes   Int
  status      String   // "pending" | "indexing" | "indexed" | "error"
  chunkCount  Int      @default(0)
  durationSec Int?     // Audio/Video
  transcriptId String? // FK zu Transkript-Record
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  profileKey  String?  // User-Scope
}
```

---

## 5. UI-Architektur

### 5.1 Route-Struktur

```
src/app/files/
  page.tsx               ← Tab-Container (overview default)
  layout.tsx             ← Header-Inject + Auth-Gate
  [tab]/
    page.tsx             ← Dynamic segment: overview|documents|audio|video|data|images|uploads
src/features/files/
  components/
    FileTabBar.tsx
    DocumentViewer.tsx   ← @react-pdf-viewer wrapper
    AudioPlayer.tsx      ← wavesurfer.js + Transcript-Sync
    VideoPlayer.tsx      ← hls.js Hook + <video>
    ImageViewer.tsx      ← next/image + SVG-Annotation-Layer
    DataViewer.tsx       ← SheetJS → TanStack Table
    UploadDropzone.tsx   ← uppy Dashboard oder react-dropzone
    FileSearch.tsx       ← orama / meilisearch-js
    ChunkOverlay.tsx     ← PDF-Viewer Custom-Plugin
  hooks/
    useHls.ts
    useWavesurfer.ts
    useFileUpload.ts
    useDocumentSearch.ts
  types/
    files.ts
src/app/api/files/
  route.ts               ← List + Metadata
  [id]/
    route.ts             ← Single-Document-Metadata
    url/route.ts         ← Frische Presigned-Download-URL
  upload-intent/route.ts ← Presigned-Upload-URL generieren
  search/route.ts        ← Proxy zu Meilisearch / orama-Index
```

### 5.2 Header-Integration

```tsx
// src/components/TradingHeader.tsx (bestehend)
// Analog zu GeoMap-Link hinzufuegen:
<Link href="/files" data-testid="link-files">
  Files
</Link>
```

### 5.3 Action-Klassen (AGENT_SECURITY.md Konformitaet)

| Action | Klasse | Anforderung |
|--------|--------|------------|
| Dokument ansehen / herunterladen | `read-only` | Auth + Role-Gate (viewer+) |
| Datei hochladen | `bounded-write` | Auth + Role-Gate (analyst+), Audit-Log |
| Datei loeschen | `bounded-write` | Auth + Role-Gate (trader+), Confirm-Dialog |
| Chunk-Reindex erzwingen | `approval-write` | Admin, Confirm + Second-Check |
| Storage-Key manuell aendern | `forbidden` | Kein UI-Pfad |

---

## 6. Degradation und Error-States

Konform zu `CONTEXT_ENGINEERING.md`:

| Signal | UI-Anzeige |
|--------|-----------|
| `NO_DOCUMENT_INDEX` | Banner: "Suche nicht verfuegbar — Index wird aufgebaut" |
| `TRANSCRIPT_PENDING` | Audio-Player ohne Transcript-Panel + Spinner |
| `STORAGE_UNAVAILABLE` | Viewer: "Datei aktuell nicht erreichbar" + Retry-Button |
| `INGEST_FAILED` | Upload-Status: "Verarbeitung fehlgeschlagen" + Fehlerdetail |
| `CHUNK_STALE` | Chunking-Overlay: gelber Rand + "Veraltete Chunks" |

---

## 7. v1 vs. v1.5 Scope

### v1 (implementierbar ohne neue Kern-Framework-Abhaengigkeit)

- Header-Button + Route `/files`
- DocumentsOverview + Liste mit Status
- PDF-Viewer (`@react-pdf-viewer/core`)
- Einfacher Upload (`react-dropzone` + Presigned URL)
- Basis-Search (fuse.js auf Metadaten)
- Audio-Player (wavesurfer.js, kein Transkript)

### v1.5

- Transkript-Sync (Audio + Video mit Speaker-Labels)
- DOCX → Gotenberg-Pipeline
- XLSX read-only via SheetJS + TanStack Table
- Chunking-Overlay im PDF-Viewer
- Meilisearch-Integration (Server-Fulltext)
- Image AI-Annotation (Claude Vision)

### v2 (Phase 22+)

- orama WASM Hybrid-Search (offline-capable)
- Satellite-Image-Tiles-Viewer
- Live-Transcript (Whisper Streaming, Echtzeit-FOMC)
- XBRL Inline-Tabellen-Viewer
- Options-Flow-Tape Streaming-Display

---

## 8. Stack-Regel (verbindlich)

- v1 **ohne neuen Kern-UI-Framework-Stack** (bestehende `package.json` nutzen).
- Neue Abhaengigkeiten nur mit nachgewiesenem Gap und Begruendung in `Aenderungshistorie`.
- `@react-pdf-viewer/core` + `wavesurfer.js` + `hls.js` + `uppy` + `react-dropzone` sind die v1-Additions — je nach Scope-Entscheid.
- `SheetJS`, `react-markdown`, `fuse.js` sind bereits im Stack oder kleinstmoeglich.

---

## 9. Querverweise

| Dokument | Relevanz |
|---------|---------|
| `docs/storage_layer.md` | Object-Store-Architektur, Signierte URLs, Persistenzklassen |
| `docs/UNIFIED_INGESTION_LAYER.md` | UIL-Pipeline fuer automatisches Ingest (YouTube, Reddit) |
| `docs/RAG_GRAPHRAG_STRATEGY_2026.md` | Vector-Store, Chunk-Strategie |
| `docs/AGENT_SECURITY.md` | Action-Klassen, Policy-Gates |
| `docs/CONTEXT_ENGINEERING.md` | Degradation-Flags, NO_*_CONTEXT-Pattern |
| `docs/GO_GATEWAY.md` | Signed-URL-Flow, Gateway-Boundary |
| `docs/MEMORY_ARCHITECTURE.md` | Episodic Store, Dokument-as-Kontext |
| `docs/specs/execution/document_widgets_control_delta.md` | Execution-Owner fuer Implementierung |
| `docs/specs/execution/storage_layer_delta.md` | Storage-Implementierungsplan |
