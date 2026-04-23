# exec-media-ingestion — Image / Audio / Video / Batch Pipelines

**Status:** Draft → **Ready-to-implement 2026-04-24**. Ownership transferred from archived `exec-19 §3.5 + §3.7`. Open items (§Implementation Status) are impl-work not design-decisions: 4 pipelines (image / audio / video / batch), 4 new routes on ingestion-worker, 1 search endpoint, PipelineKind enum extension. All technology choices fixed (Tesseract/Florence-2 for OCR, Whisper for STT, ffmpeg for key-frames, existing safe-unpack pattern from skills_guard for batch). Impl is multi-day per pipeline; treat this ratification as the go-signal for whoever picks up.
**Erstellt:** 2026-04-18
**Owner der Stufe 3 media-Pipelines vor Archive:** exec-19 (devstack-consolidation)
**Cross-Refs:** exec-15 (Control-UI Files Tabs), exec-18 (agent.traces / audit_events), exec-retrieval (wenn vorhanden — chunk-level search)

## Warum

`python-backend/ingestion/worker.py` verarbeitet heute Text-Dateien (PDF, MD,
TXT, docx → chunks → Hindsight/MemPalace). Media-Dateien (Bilder, Audio,
Video, ZIP-Batches) landen im Artifact-Storage (SeaweedFS via
`go-appservice`) **ohne Pipeline** — keine Transkripte, keine OCR-Texte,
keine Scene-Descriptions. Control-UI Files-Tab kann sie nur als Thumbnails
rendern, nicht durchsuchbar machen.

Diese Spec ist der dedizierte Owner der Media-Pipeline-Erweiterung — raus
aus `exec-19 §3` weil Media-Ingestion ein eigenes Domain ist (OCR-Models,
ffmpeg, Whisper, Vision-APIs), kein devstack-consolidation-Thema.

## Ziel

- Jede Media-Datei die in Artifact-Storage landet bekommt eine
  Pipeline-Pass: OCR-Text (Bilder), Transkript (Audio), Scene-Descriptions
  (Video), oder pro-Entry-Pipelines (Batch).
- Pipeline-Output ist als Chunks in Hindsight/MemPalace searchable und in
  Control-UI Files-Tab durchsuchbar (`GET /search?q=...&user_id=...`).
- `POST /jobs/{job_id}/cancel` ermöglicht best-effort-Abbruch.

## Nicht-Ziel

- Real-time Streaming-Transkription (separate Feature, exec-voice / voice-API).
- Video-Editing / Re-encoding über Transkription hinaus.
- Kommerzielle Cloud-Vision-APIs (OpenAI Vision ok, aber kein Mandatory — local qwen-vl als Default).

## Architektur

```
Upload (Control-UI / Matrix-Chat)
  │
  ▼
go-appservice/storage/  →  SeaweedFS (Artifact-Storage, already works)
  │
  │ POST /ingest/image|audio|video|batch (new routes)
  ▼
python-backend/ingestion/worker.py
  │
  ├── pipelines/image.py    OCR (Tesseract / Florence-2) + Vision-Captioning (qwen-vl / OpenAI)
  ├── pipelines/audio.py    Whisper-Transkription → text chunks
  ├── pipelines/video.py    Key-frame extraction (ffmpeg) + Whisper (audio track) + scene descriptions
  └── pipelines/batch.py    ZIP/TAR fan-out auf per-file pipelines
       │
       ▼
  chunks → embeddings → Hindsight (write_fact) + MemPalace (verbatim) via memory_fusion
       │
       ▼
  Control-UI Files-Tab: searchable via GET /search
```

## Implementation Status

Aus archivierter exec-19 §3.5 + §3.7 übernommen:

### Done (pre-transfer)

- [x] `go-appservice/internal/storage/` — Full-Stack Files-API inkl. pgxpool, Schema-Separation, Signer-Token mit User-Binding (exec-19 §3.0.x, 11-13.04.2026).
- [x] `python-backend/ingestion/core/types.py` — `PipelineKind` Enum (text-only vor Transfer).
- [x] Media-Type Classification in `go-appservice/BuildArtifactService.ClassifyFromContentType` + `ClassifyFromExtension` (exec-19 §3.5).

### Open — Core Pipelines

- [ ] `python-backend/ingestion/pipelines/image.py` — OCR (Tesseract / Florence-2) + Vision-Captioning (OpenAI / local qwen-vl). Output: OCR-text + caption-paragraph als 2 chunks.
- [ ] `python-backend/ingestion/pipelines/audio.py` — Whisper-Transkription → text chunks mit timestamps.
- [ ] `python-backend/ingestion/pipelines/video.py` — Key-frame extraction via ffmpeg + Whisper auf Audio-Track + scene-descriptions pro Key-frame. Output: multi-modal chunks mit timestamp + frame-ref.
- [ ] `python-backend/ingestion/pipelines/batch.py` — ZIP/TAR fan-out: entpacken (safe — path-traversal + symlink-checks aus skills_guard-Pattern), dispatch per-entry an image/audio/video pipeline.

### Open — Routes + Types

- [ ] `python-backend/ingestion/worker.py` — Routes: `POST /ingest/image`, `POST /ingest/audio`, `POST /ingest/video`, `POST /ingest/batch`.
- [ ] `python-backend/ingestion/worker.py` — `POST /jobs/{job_id}/cancel` (best-effort, markiert job als "cancelled" in DB, stoppt running task wenn möglich).
- [ ] `python-backend/ingestion/core/types.py` — `PipelineKind` Enum um `image`, `audio`, `video`, `batch` erweitern.

### Open — Search-Integration (für Control-UI Files-Tab)

- [ ] `python-backend/ingestion/worker.py` — `GET /search?q=...&user_id=...` Route die chunks aus Hindsight/MemPalace per-user surfaced.

## Verify-Gates

- [ ] Upload 1MB JPG via Control-UI → image.py → 2 chunks in Hindsight, beide durchsuchbar via `/search?q=<caption-keyword>`.
- [ ] Upload 5min MP3 → audio.py → Whisper-Transkript als chunks mit timestamps.
- [ ] Upload 30s MP4 → video.py → 3 key-frames + audio-Transkript + captions als chunks.
- [ ] Upload ZIP mit 5 Bildern → batch.py → 5 image-pipeline runs, 10 chunks total.
- [ ] `POST /jobs/{job_id}/cancel` während running job → Job marked "cancelled", partial chunks discarded.

## Abhängigkeiten

- **exec-15 Control-UI Files-Tab** — Viewer-Renderers für die Pipeline-Outputs
  (Waveform für Audio, Transkript-Overlay, Frame-Extracted-Images). Extrahiert
  in `claude-merge-frontend-chat-ui-2OqmH/exec-05-ui-viewers-polish.md`.
- **exec-retrieval** (oder memory_fusion) — Chunk-Persistenz + Search.
- **exec-18 audit_events + agent.traces** — Pipeline-Job-Tracking (status,
  duration, errors).

## Abgrenzung

- **Real-time streaming** (live transcription during Matrix voice call) → exec-voice
- **LLM-vision-tool-calls** (agent sieht uploaded image während Conversation) → exec-10 multi-agent / exec-skills
- **Generative Media** (TTS-Output, Image-Generation) → eigenes Exec
