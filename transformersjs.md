# transformers.js — Bewertung & Richtungen für matrix

> **Status:** Analyse / Vorschlag — 2026-04-17.
> **Nichts davon ist beschlossen.** Dieses Dokument sammelt Einschätzungen; konkrete Implementierungspunkte stehen in `specs/execution/exec-transformersjs.md` und müssen dort noch **deeper & genauer** besprochen werden.

---

## 0. Kontext

[transformers.js](https://github.com/huggingface/transformers.js) (`@huggingface/transformers` v4) erlaubt, HF-Modelle direkt im Browser (WebGPU / WASM) oder in Node.js auszuführen — gleiche Pipeline-API wie die Python-Version. Für matrix relevant, weil:

- **Compute-Auslagerung**: User-Hardware trägt Last, Server-Kosten sinken.
- **Privacy**: Daten verlassen den Browser nicht.
- **Offline / Low-Latency**: UI-Responsiveness ohne Server-Roundtrip.
- **Fallback-Harness**: WebGPU → WASM → Server bereits etabliertes Muster.

Zweite relevante Library: [WebLLM](https://github.com/mlc-ai/web-llm) — spezialisiert auf große LLMs (Llama-3, Phi-3, Gemma) mit WebGPU-Optimierung.

---

## 1. Bewertung: Wo passt es in matrix

### Gute Fits

| Use-Case | Tool / Modell | matrix-Komponente |
|---|---|---|
| **Sentiment / Classification** | transformers.js `Xenova/distilbert-base-uncased-finetuned-sst-2` (q8) | `control-ui` live-feed preview, `frontend_merger` tweet/news-chip labels |
| **Client-Side Embeddings (Chat-Query)** | transformers.js **`Xenova/all-MiniLM-L6-v2` (q8, 384-dim)** | `retrieval/` — Browser embedded die User-Query vor dem `/search`-Call |
| **MemPalace Inline-Mining** | dasselbe MiniLM-Modell | `memory_fusion/mempalace/` — kurze Chat-Snippets beim Tippen vektorisieren |
| **Summarization kurzer UI-Snippets** | transformers.js `Xenova/distilbart-cnn-6-6` (q8, ~150 MB) | Agent-Output-Teaser in `control-ui`, Thread-Recap-Sidebar, Search-Result-Snippets |
| **STT im Browser** | transformers.js Whisper-tiny (q8) | Voice-Input-Fallback wenn LiveKit-Agent nicht verfügbar |
| **Chat-Generation (offline-mode toggle)** | WebLLM Phi-3-mini oder Gemma-2B | `control-ui` Fallback-Mode wenn Backend nicht erreichbar — **nicht default**, LiteLLM-Gateway bleibt primär |

### Schlechte Fits (bleibt server-seitig)

- **Hindsight Memory** — Persistenz, cross-user-KG-Integration, Konsistenz-Garantien.
- **Agent-Orchestrierung** — Auth, Audit, Rate-Limits, LiteLLM-Gateway.
- **Ingestion-Pipeline für Dokumente** — `python-backend/ingestion/` (8 Phasen, dedup, smart_reindex, multi-sink) lässt sich nicht sinnvoll ins Browser portieren.
- **Schwere LLM-Reasoning-Chains** — LiteLLM + OpenRouter-Credits sind billiger und zuverlässiger.

---

## 2. Kritische Einschränkung: Embedding-Konsistenz

**Wenn Frontend Embeddings für Hindsight / MemPalace erzeugt, MUSS das Modell dimensional und architektonisch identisch zur Server-Pipeline sein.**

Backend heute (`python-backend/ingestion/embedders/sentence_transformer.py:22`):

```python
model_name: str = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dim
```

Frontend-Pendant (ONNX-port, identische Gewichte):

```ts
await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2', { dtype: 'q8' });
```

→ **Drop-in möglich.** Aber: Wechselt das Backend das Embedding-Modell, muss das Frontend synchron mitziehen. Sonst werden Cosine-Scores inkompatibel und der Vektor-Index wird still inkonsistent. **Singular source of truth im Backend, Frontend ist Mirror.**

---

## 3. Mögliche Richtungen (nach Aufwand sortiert)

### Phase A — niedriger Aufwand, hoher Win

1. **[google/magika](https://github.com/google/magika)** — ML-basierte File-Type-Detection (99%+ accuracy, ONNX-Modell ~1 MB).
   - **Einsatz 1 (Go-Side)**: `go-appservice/internal/storage/` — Upload-Validation vor SeaweedFS/Garage-put. Go-Bindings existieren. Schutz gegen MIME-Spoofing.
   - **Einsatz 2 (Agent-Tool)**: File-Analyse-Skill für Agenten (was ist diese Datei wirklich?).
   - **Einsatz 3 (Ingestion Detector)**: ersetzt / ergänzt den bestehenden `ingestion/detectors/magic.py` (libmagic → magika-ONNX).

2. **[jamiepine/voicebox](https://github.com/jamiepine/voicebox)** — saubere Voice-UI-Komponente (Spacedrive-Autor, gute Code-Qualität).
   - **Einsatz**: `control-ui` voice-input-component — visualisiert Audio-Level, Recording-State, Transcript-Preview. Ergänzt LiveKit-Agent-Backend, ersetzt es nicht.

### Phase B — mittlerer Aufwand, gewinnt UX

3. **Client-Side Query-Embedding** für Chat/Search.
   - Endpoint: neuer `/search?vec=<base64>` Pfad in `retrieval/` parallel zum bestehenden `/search?q=<text>`.
   - Frontend: Web-Worker lädt `Xenova/all-MiniLM-L6-v2` beim App-Start (lazy), embedded Query lokal, sendet Vektor.
   - Einspar-Effekt: Server-Embedding-Latenz (~50-150ms pro Query) entfällt.

4. **UI-Summarization-Worker** in `control-ui`.
   - Web-Worker mit `Xenova/distilbart-cnn-6-6` (q8).
   - Targets: Agent-Output-Cards, Thread-Recap, Notification-Digest.
   - Hardware-Fallback: WebGPU → WASM → Server-API (`/summarize`).

### Phase C — höherer Aufwand, experimentell

5. **Client-Side STT für Voice-Input-Fallback** (Whisper-tiny).
   - Nur relevant wenn LiveKit-Stack down oder User in High-Latency-Network.
6. **MemPalace Chat-Mining im Browser** — jede Chat-Message wird direkt beim Tippen vektorisiert und lokal geclustert, bevor sie an den Server geht.
   - Löst das filesystem-basierte MemPalace-Problem (siehe `specs/execution/exec-memory.md`) teilweise — Frontend-Cluster können in IndexedDB cached werden.
7. **WebLLM offline-chat-mode** — separater Toggle "Offline-AI", lädt Phi-3-mini (~1.8 GB) einmalig.
   - Nur sinnvoll wenn User explizit Privacy-First-Modus wählt.

### Nicht empfohlen (jetzt)

- **[EvoMap/evolver](https://github.com/EvoMap/evolver)** — research-stage, kein stabler Release, unklare Roadmap. Wir haben bereits LiteLLM + Agent-Harness.
- **[lsdefine/GenericAgent](https://github.com/lsdefine/GenericAgent)** — dünnes Repo, wenig Community. Unser `python-backend/agent/` ist reifer.

---

## 4. Hardware-Realitäten

Target-Zielgeräte variieren. Entscheidungsmatrix:

| Gerät | RAM | GPU | Transformers.js | WebLLM |
|---|---|---|---|---|
| Desktop Power-User | 16-32 GB | dGPU WebGPU | ✅ alles | ✅ 7B-Modelle |
| Laptop Mid-Range | 8-16 GB | iGPU WebGPU | ✅ q8-Modelle bis 500 MB | ⚠️ nur SLMs (Phi-3-mini, Gemma-2B) |
| Chromebook / Low-End | 4-8 GB | kein WebGPU | ⚠️ nur tiny (Sentiment, MiniLM) | ❌ |
| Mobile | 2-4 GB | WebGPU spotty | ⚠️ nur Sentiment + tiny-Embeds | ❌ |

**Dev-Maschine hier** (i7-2600, 8GB, kein WebGPU): läuft als Low-End-Chromebook-Äquivalent → guter Stresstest.

**Pflicht-Pattern für jede Integration:**
- Web Worker (nie Main-Thread)
- q8-quantisiert als Default
- `try / catch` mit WebGPU → WASM → Server-Fallback
- Hardware-Check: `navigator.gpu`, `navigator.deviceMemory`, `navigator.hardwareConcurrency`
- Ladebalken / "Optimiere für dein Gerät"-UX

---

## 5. Modellauswahl — default-Kandidaten

| Task | Modell | Größe (q8) | Dim |
|---|---|---|---|
| Sentiment | `Xenova/distilbert-base-uncased-finetuned-sst-2-english` | ~65 MB | — |
| Embedding | `Xenova/all-MiniLM-L6-v2` | ~23 MB | 384 |
| Summarization | `Xenova/distilbart-cnn-6-6` | ~150 MB | — |
| STT | `Xenova/whisper-tiny.en` | ~40 MB | — |
| File-Type (ONNX) | google/magika model | ~1 MB | — |
| Chat-LLM (WebLLM) | `Phi-3-mini-4k-instruct-q4f16_1` | ~2.3 GB | — |

---

## 6. Risiken & offene Fragen

- **Model-Drift**: Wenn Backend das Embedding-Modell tauscht, bricht jede Frontend-Cache. Braucht Versionierungs-Strategie (z.B. `embedding_model_version` in Vektor-Row, Frontend prüft Match).
- **Bandwidth**: 100-500 MB Modell-Downloads sind für mobile / getethered Users bitter. Cache-Strategy wichtig (Service-Worker + Cache-API, nicht HTTP-Cache).
- **Browser-Kompatibilität**: WebGPU in Firefox noch experimentell (2026-04). Safari arbeitet dran. Chromium = primary target.
- **IP / Lizenzen**: voicebox ist AGPL — prüfen ob kompatibel mit matrix-Lizenzsituation, bevor Code übernommen wird. Magika ist Apache 2.0 → unproblematisch.
- **Security**: Modelle laden von HF-CDN — wir vertrauen HF. Alternative: self-hosting via SeaweedFS/Garage (neuer `/models/` bucket).

---

## 7. Referenzen & Links

### transformers.js Core
- Repo: https://github.com/huggingface/transformers.js
- Docs: https://huggingface.co/docs/transformers.js
- WebGPU-Guide: https://huggingface.co/docs/transformers.js/guides/webgpu
- v4-Blog: https://huggingface.co/blog/transformersjs-v4

### WebLLM
- Repo: https://github.com/mlc-ai/web-llm
- Model-Catalog: https://github.com/mlc-ai/web-llm#using-built-in-models

### Empfohlene Ergänzungs-Projekte
- **google/magika** — https://github.com/google/magika (Apache 2.0, ML file-type detection)
- **jamiepine/voicebox** — https://github.com/jamiepine/voicebox (Voice-UI-Component, AGPL — Lizenz prüfen)

### Nicht empfohlen (zur Ablage)
- EvoMap/evolver — https://github.com/EvoMap/evolver (research, unreif)
- lsdefine/GenericAgent — https://github.com/lsdefine/GenericAgent (dünn)

---

## 8. Nächste Schritte

Siehe `specs/execution/exec-transformersjs.md` für konkrete Implementierungspunkte. Diese Vorschläge sind **nicht freigegeben** — müssen noch deeper diskutiert werden (Priorisierung, Dependencies zu `exec-15-memory-control-ui.md` / `exec-11-memory-evolution.md`, Resource-Budget, Target-Hardware).
