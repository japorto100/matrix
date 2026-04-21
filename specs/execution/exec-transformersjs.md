# exec-transformersjs — Client-Side ML (transformers.js / WebLLM / magika / voicebox)

> ## STATUS: **ENTWURF — NICHT FREIGEGEBEN**
>
> **Dies sind Implementierungs-Vorschläge, kein genehmigter Plan.** Bevor irgendetwas davon umgesetzt wird, muss dieses Dokument **deeper und genauer** besprochen werden:
>
> - Priorisierung gegen andere Execs (`exec-11-memory-evolution.md`, `exec-15-memory-control-ui.md`, `exec-06-agent-chat-integration.md`).
> - Target-Hardware-Budget für Users (welche Geräte müssen funktionieren?).
> - Abhängigkeiten zwischen den Schritten.
> - Lizenz-Review voicebox (AGPL) vs. matrix-Gesamtlizenz.
> - Frontend-Framework-Fit (Next.js 16 App-Router, Web-Worker-Setup, Service-Worker für Model-Cache).
>
> **Die Bewertung und Richtungs-Übersicht liegt in `/transformersjs.md` im Repo-Root — dort auch Modellauswahl, Hardware-Matrix und Links.**

---

## Ziel

Client-seitige ML-Features in matrix einführen, um (a) Server-Kosten zu senken, (b) UX-Latenz für kleine Tasks zu reduzieren, (c) Privacy-First-Pfade zu ermöglichen.

Root-Dokument: [/transformersjs.md](../../transformersjs.md) — dort steht Bewertung, Architektur-Einordnung und Modellauswahl. Dieses Dokument listet **was konkret umgesetzt werden müsste**, falls Phasen freigegeben werden.

---

## Implementierungspunkte (Empfehlung, Reihenfolge = Priorität)

### Punkt 1 — magika in Storage-Upload-Validation (Phase A)

**Was:** ML-basiertes File-Type-Detection vor SeaweedFS/Garage-put in `go-appservice`.

**Warum jetzt:** Kleiner Aufwand, großer Security-Win (MIME-Spoof-Schutz). Keine Client-Side-Arbeit nötig.

**Was angefasst werden müsste:**
- `go-appservice/internal/storage/service.go` — neuer Validierungsschritt `detectFileType()` vor `Put()`.
- `go-appservice/go.mod` — dependency auf [magika-go-bindings](https://github.com/google/magika) (prüfen ob stabile Go-Library existiert, sonst CGO via Rust oder Shell-out zum magika-binary).
- `go-appservice/internal/storage/types.go` — neues Feld `DetectedMime` in Upload-Response, Audit-Log-Trail.
- Test-Suite: Fuzz-Upload mit bewusst-falsch-benannten Files (`.jpg` der eigentlich `.exe` ist).

**Alternativen:** 
- Ersetzt oder ergänzt `ingestion/detectors/magika.py` auf Python-Seite (separater Task — magika hat auch Python-Library).
- Skip-Flag für Trusted-Upload-Pfade (z.B. matrix-appservice-interner Upload).

**Offene Fragen:**
- Go-Bindings-Stabilität. Alternative: `magika` CLI via `exec.Command` (höhere Latenz, einfacher).
- Wo wird das ONNX-Modell gespeichert — in Container-Image backen oder aus SeaweedFS laden?

---

### Punkt 2 — voicebox als Referenz für control-ui Voice-Input (Phase A)

**Was:** Voice-Input-Komponente in `control-ui` mit sauberer UX (Waveform, Recording-State, Transcript-Preview).

**Warum jetzt:** Ergänzt bestehenden LiveKit-Agent-Voice-Backend. UI-Lücke schließen.

**Was angefasst werden müsste:**
- `control-ui/` — neue Komponente `VoiceInput.tsx`, State-Management für Record/Pause/Stop.
- Lizenz-Check: voicebox ist AGPL — **kritisch**. Entweder: (a) Code inspirieren, selbst schreiben, (b) als separate MIT/Apache-Komponente extrahieren, (c) matrix-Gesamtlizenz akzeptiert AGPL-Komponente.
- Integration mit LiveKit-Agent-Backend: Audio-Stream via WebRTC zum Agent, Transcript retour über WebSocket.
- Fallback: wenn LiveKit-Agent down, lokales Whisper-tiny (→ Punkt 5).

**Offene Fragen:**
- AGPL-Kompatibilität matrix-weit.
- Voice-Activity-Detection (VAD) — lokal oder server-seitig?

---

### Punkt 3 — Client-Side Query-Embedding für Chat / Search (Phase B)

**Was:** User-Query wird im Browser vektorisiert (`Xenova/all-MiniLM-L6-v2` q8, 384-dim), als Vektor direkt an `/search` geschickt.

**Warum jetzt:** Spart 50-150ms Embedding-Latenz server-seitig pro Query. Guter Lackmus-Test für Web-Worker-Infra.

**Was angefasst werden müsste:**
- `control-ui/` — neuer Web-Worker `embedding-worker.ts`, lädt transformers.js + MiniLM lazy beim App-Start.
- `python-backend/retrieval/` — `/search`-Endpoint akzeptiert optional `query_vector: number[]` (base64-encoded oder JSON-array), skipped dann internes `embed()`.
- **Kritisch**: Embedding-Model-Version in Hindsight-Vektor-Rows persistieren, damit Server später Mismatches erkennt (`embedding_model: "all-MiniLM-L6-v2"`).
- Fallback: wenn Frontend-Modell-Load fehlschlägt → normaler Text-Query.

**Offene Fragen:**
- Wie Version-Sync zwischen Frontend und Backend handhaben (env-var? Health-Check-Endpoint `/embedding-info`?).
- Caching-Strategie für das Modell (Service-Worker + Cache-API? IndexedDB?).
- Was passiert bei Model-Update — User muss re-download, wie kommuniziert?

---

### Punkt 4 — UI-Summarization-Worker in control-ui (Phase B)

**Was:** Lokaler Web-Worker mit `Xenova/distilbart-cnn-6-6` (q8) für Agent-Output-Teaser, Thread-Recap, Notification-Digest.

**Warum jetzt:** UX-Gewinn bei Scroll-through vieler Agent-Outputs. Server-Cost-Sparen.

**Was angefasst werden müsste:**
- `control-ui/` — neuer Web-Worker `summarization-worker.ts`.
- UI-Komponenten: Agent-Output-Card, Thread-List-Item, Notification-Dropdown — alle bekommen optionalen `summary`-Slot.
- Server-Fallback-Endpoint `/summarize` in `python-backend/` (LiteLLM-call mit kleinem Modell wie gpt-4o-mini) für WebGPU/WASM-failed-Fälle.
- Hardware-Gating: `deviceMemory < 4GB` → sofort Server-Fallback ohne Modell-Download.

**Offene Fragen:**
- distilbart-cnn ist Englisch-only — Multilingual Summary-Modelle evaluieren (z.B. mT5-tiny).
- Caching von Summaries: IndexedDB pro Agent-Output-ID, damit nicht jedes Scroll re-computed.

---

### Punkt 5 — Client-Side STT (Whisper-tiny) als Voice-Fallback (Phase C)

**Was:** Lokales Whisper-tiny wenn LiveKit-Agent nicht erreichbar.

**Warum später:** Nur relevant für Degraded-Mode-UX. Kann warten bis Core-Voice-Stack steht.

**Was angefasst werden müsste:**
- VoiceInput-Komponente (Punkt 2) bekommt Mode-Switch: `livekit | local-whisper | none`.
- Audio-Recording via MediaRecorder → WAV/OGG → Whisper-Worker → Transcript.
- Integration mit Chat-Input-Feld.

**Offene Fragen:**
- Whisper-tiny ist Englisch-lastig — für DE/Multilingual evtl. `Xenova/whisper-small.de` (~240 MB).
- Latenz vs. Quality — tiny = schnell aber Fehlerquote höher.

---

### Punkt 6 — MemPalace Browser-Side Chat-Mining (Phase C, experimentell)

**Was:** Jede Chat-Message wird beim Tippen / Absenden lokal vektorisiert + gecluster, in IndexedDB gecached, dann zum Backend synchronisiert.

**Warum später:** Löst nur *teilweise* das MemPalace-filesystem-Problem aus `exec-memory.md` "Known Issues". Braucht Design-Runde mit Fusion-Layer-Team.

**Was angefasst werden müsste:**
- `memory_fusion/mempalace/` — neuer Client-Sync-Endpoint.
- `control-ui/chat/` — Vektorisierungs-Worker + IndexedDB-Layer.
- Konflikt-Strategie: was wenn Backend und Frontend unterschiedliche Cluster finden?

**Offene Fragen:**
- Macht das Sinn oder überkomplizieren wir MemPalace damit? Server-side-Fix könnte einfacher sein.
- Wie mit Multi-Device-Sync umgehen (User auf Desktop + Mobile)?

---

### Punkt 7 — WebLLM Offline-Chat-Mode Toggle (Phase C, optional)

**Was:** Separater "Offline-AI"-Toggle in `control-ui`, lädt einmalig Phi-3-mini (~1.8 GB), ermöglicht Chat ohne Backend.

**Warum vielleicht nie:** Hoher Platz-Bedarf, nur Privacy-Power-User. LiteLLM + OpenRouter ist billig und besser.

**Was angefasst werden müsste:**
- `control-ui/settings/` — Toggle + Download-UI + Storage-Permission-Check.
- Chat-Pipeline: Switch zwischen LiteLLM-Call und lokalem WebLLM-Call.
- Model-Storage-Management: wenn User Platz braucht, wie Modell löschen?

**Offene Fragen:**
- Lohnt sich das überhaupt, oder ist es Feature-Creep?

---

## Nicht übernommen

- **EvoMap/evolver** — research-stage, keine stable releases. Nicht jetzt.
- **lsdefine/GenericAgent** — dünne Codebase, geringe Community. Nicht jetzt.

Details siehe [/transformersjs.md Abschnitt 3 — "Nicht empfohlen"](../../transformersjs.md#nicht-empfohlen-jetzt).

---

## Cross-References

- **Root-Bewertung**: [/transformersjs.md](../../transformersjs.md)
- **Memory-Architektur** (Hindsight, MemPalace): `exec-11-memory-evolution.md`, `exec-15-memory-control-ui.md`, `exec-memory.md`
- **Voice-Stack** (LiveKit-Agent-Backend): `python-backend/voice/README.md`
- **Ingestion-Pipeline** (warum Doc-Processing nicht ins Frontend): `python-backend/ingestion/`
- **Storage-Service** (magika-Integration): `go-appservice/internal/storage/`
- **Agent-Integration** (Generative-UI, Output-Cards): `exec-06-agent-chat-integration.md`, `exec-09-protocols-generative-ui.md`

---

## Abnahme-Kriterien (wenn Phasen greenlit werden)

Pro Phase separate Abnahme:
- Phase A (magika + voicebox-UI): Unit-Tests, Security-Fuzz (magika), Lizenz-Review (voicebox).
- Phase B (Query-Embed + Summarization): Benchmarks auf Target-Hardware (i7-2600/8GB als low-end Baseline), Fallback-Tests (WebGPU off, WASM only).
- Phase C (STT, MemPalace-Mining, WebLLM): je nach Design-Runde separat.

Jeder Phase-Start muss ein eigenes detail-Planning durchlaufen.

---

## §3.5 Title-Gen via lokales Small-Model (PRIMARY OWNER)

**Status:** PRIMARY implementation target — transformers.js ownership confirmed 2026-04-20 (user decision).
**Cross-ref:** `exec-hermes.md §0` (title_generator row), `exec-06.md §4d` (legacy remote-LLM fallback — kept as offline-degradation path only).

### Ownership re-scoped

Phase-B P6 shipped `agent/titles/generator.py` as a **remote-LLM** title-gen (LiteLLM via `MATRIX_TITLE_GEN_KEY`). That remains as a **fallback** for environments where WebGPU is unavailable or disabled — but the **primary title-gen path belongs in this spec** (browser-side transformers.js small-model). A remote LLM call per session is a cost-and-latency tax that makes no sense when a 0.5–1B parameter model runs locally in <200ms.

### Why local > remote for title-gen specifically

| Dimension | Remote LLM (agent/titles/generator.py) | Local transformers.js |
|---|---|---|
| Latency | 800ms–2s (network + LiteLLM + model queue) | <200ms on WebGPU, <500ms on WASM |
| Cost | 1 call per session × user-count × turnover | zero |
| Privacy | first 2–3 messages + assistant-reply cross the wire | never leave the user's device |
| Scale | per-session remote call, hits rate-limits | client-side, no server impact |
| Failure mode | silent skip (absent `MATRIX_TITLE_GEN_KEY`) | graceful WebGPU → WASM fallback |

### Implementation targets

**Primary path (this spec):**

- **Model:** Qwen-2.5-0.5B-Instruct quantized (q4_0 or q8_0) via `@huggingface/transformers`. Fallback to Llama-3.2-1B if qwen-0.5B quality is insufficient for 3–7-word title extraction.
- **Host:** `frontend_merger/src/features/agent/lib/titleGen.ts` — new module. Lazy-load the model on first session, reuse across sessions per tab.
- **Trigger:** `useChatSession.ts::onFinish` — after the first assistant reply in a new thread (`threadId` seen for the first time), run `generateTitle(userMsg, assistantReply)` in a Worker or idle-callback.
- **Persist:** `POST /api/v1/agent/sessions/{id}/title` (already exists as a contract in `exec-06.md §4d`) with the generated title. Backend writes to `agent.sessions.title` column (migration 024).
- **Graceful degradation:** if WebGPU and WASM both unavailable, fall through to the backend `/api/v1/agent/titles/generate` endpoint which uses `agent/titles/generator.py` (remote LLM). That endpoint currently doesn't exist but is a ~20 LOC addition to `agent/app.py`.

**Legacy path (backend):**

`agent/titles/generator.py` stays in place as the offline-degradation fallback, NOT the primary. Docstring should note this ownership split — pointing at this spec as the primary. Existing `MATRIX_TITLE_GEN_KEY` env-var logic remains untouched.

### Decision-points still open

- Worker vs main-thread: Worker isolates the model and prevents UI jank, but has model-load latency on every new tab. Main-thread with idle-callback is simpler but can jank scroll.
- When to pre-warm the model: on app-boot (background cost for all users) vs on-first-session (latency on first-ever title).
- Quality floor: a 0.5B model sometimes produces weak titles for niche domains (trading vocabulary, multi-language). We need an empirical quality check before declaring local-only.

### Phase-Start

Prerequisites: transformers.js already a planned dependency in this spec. The only new code is the title-gen module + useChatSession integration + backend fallback endpoint. Estimated ~200 LOC TypeScript + ~20 LOC Python backend (fallback endpoint). Not a large project — the blocker is prior local-model-loading infrastructure landing first (per this spec's main plan).

## Changelog-append (Phase-B)

| Date | Change |
|---|---|
| 2026-04-20 | exec-hermes Phase-B P2 stub added: §3.5 (title-gen local-model upgrade path). Remote-LLM baseline ships P6, local-model upgrade separately. |
| 2026-04-20 | **§3.5 ownership re-scoped (user decision).** transformers.js is now the **primary** title-gen path; `agent/titles/generator.py` (Phase-B P6) demoted to offline-degradation fallback. Rationale: remote-LLM per session is unnecessary cost/latency when a 0.5–1B model runs locally. Concrete implementation targets documented (Qwen-2.5-0.5B via `@huggingface/transformers`, lazy-load, WebGPU→WASM→backend fallback chain). |
