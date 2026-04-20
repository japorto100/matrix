# exec-transformers-js: Client-Side AI (WebLLM / transformers.js) [SUPERSEDED]

> **SUPERSEDED 2026-04-20** — This spec (exec-transformers-**js**.md, 13.04.2026) has been replaced by the newer `exec-transformersjs.md` (without the hyphen) which is the active client-side ML spec with broader scope (transformers.js + WebLLM + magika + voicebox). The newer spec also holds the re-scoped title-gen ownership (§3.5, primary path). Content here preserved for historical reference only — do not implement from this file.

**Datum:** 13.04.2026
**Status:** SUPERSEDED (archived 2026-04-20) — see `specs/execution/exec-transformersjs.md`
**Abhaengig von:** exec-19 (Agent-Chat Baseline), exec-a2fm (Routing Konzept)
**Referenzen:**
- [transformers.js v3](https://huggingface.co/docs/transformers.js) — Hugging Face models in browser via ONNX/WebGPU
- [WebLLM](https://webllm.mlc.ai/) — MLC LLM in browser via WebGPU
- [llmware/slim-summary-tiny-onnx](https://huggingface.co/llmware/slim-summary-tiny-onnx) — Tiny ONNX summarizer
- [onnx-community/text_summarization-ONNX](https://huggingface.co/onnx-community/text_summarization-ONNX) — T5-Small summarizer
- [Hindsight Models](https://hindsight.vectorize.io/developer/models) — Built-in llamacpp with Gemma 4 E2B (~3.5GB)

---

## Warum

Mehrere Features brauchen schnelle, guenstige Inference die **nicht** ueber eine Cloud-API laufen muss:

1. **Inline Autocomplete** (agent-chat Composer) — braucht <50ms Latenz, kein Network Roundtrip
2. **Summarization** (Hindsight Memory) — aktuell Overkill: 26B Model via OpenRouter fuer simple Zusammenfassungen
3. **Embedding** (Semantic Search) — laeuft schon lokal (sentence-transformers), koennte auch im Browser
4. **Content Classification** (A2FM Router) — "ist diese Frage einfach/komplex/tool-intensiv?" braucht kein 70B Model

## Moeglichkeiten

### 1. Inline Autocomplete (Browser-seitig)

**Ist-Zustand:** `agent-chat/src/app/api/agent/completion/route.ts` — schickt Prompt an Backend → LiteLLM → Cloud.
**Problem:** Network Latency (~200-500ms) zerstoert das Typing-Erlebnis.

**Ziel:** transformers.js / WebLLM im Browser, Model wird einmalig geladen (~50-200MB), danach instant.

**Kandidaten:**
| Model | Size | Format | Latenz (WebGPU) |
|---|---|---|---|
| `Qwen2.5-0.5B-Instruct` | ~350MB | GGUF/WebLLM | ~20ms/token |
| `Phi-3-mini-4k-instruct` | ~2.3GB | WebLLM | ~15ms/token |
| `SmolLM2-360M-Instruct` | ~250MB | ONNX | ~30ms/token |
| `TinyLlama-1.1B` | ~640MB | ONNX | ~25ms/token |

**Empfehlung:** `SmolLM2-360M` oder `Qwen2.5-0.5B` — klein genug fuer schnellen Download, gross genug fuer brauchbare Completions.

**Implementierung:**
- `agent-chat/src/lib/webllm/` — WebLLM Worker (Web Worker fuer non-blocking)
- Model-Download beim ersten Laden (cached via IndexedDB)
- Fallback auf Server-API wenn WebGPU nicht verfuegbar

### 2. Summarization (Backend, lokal)

**Ist-Zustand:** `AGENT_DEFAULT_UTILITY_MODEL=openrouter/google/gemma-4-26b-a4b-it:free` — 26B Model via Cloud API fuer Summarization.
**Problem:** Overkill, Latenz, API-Abhaengigkeit, Rate Limits.

**Optionen:**
| Option | Size | Wo | Beschreibung |
|---|---|---|---|
| `llmware/slim-summary-tiny-onnx` | ~50MB | Python ONNX | Spezialisiert auf Summarization, winzig |
| `onnx-community/text_summarization-ONNX` | ~250MB | Python ONNX | T5-Small, gut getestet |
| Hindsight built-in `llamacpp` | ~3.5GB | Python | Gemma 4 E2B GGUF, auto-download |
| Ollama `gemma3:1b` | ~800MB | Ollama | Lokale General-Purpose |
| Aktuell via LiteLLM | 0 lokal | Cloud | Funktioniert, aber teuer/langsam |

**Empfehlung:** Hindsight's built-in `llamacpp` (Gemma 4 E2B, 3.5GB) — bereits unterstuetzt, kein extra Setup. Fuer pure Summarization: `slim-summary-tiny-onnx` (50MB) als Fast-Path.

### 3. Content Classification / Routing (Browser oder Backend)

**Fuer exec-a2fm:** "Ist diese Query instant/reasoning/agentic?"
- Browser: transformers.js mit kleinem Classifier (~50MB)
- Backend: Python ONNX oder sentence-transformers + Logistic Regression

### 4. Weitere Moeglichkeiten

- **Speech-to-Text im Browser**: Whisper.cpp via WebAssembly (kein Server noetig)
- **OCR im Browser**: Tesseract.js (bereits Web-Standard)
- **Embedding im Browser**: transformers.js mit `bge-small-en-v1.5` (Hindsight Default)

---

## Betroffene Files

| Datei | Aenderung |
|---|---|
| `agent-chat/src/lib/webllm/` | NEU: WebLLM Worker + Model Loader |
| `agent-chat/src/app/api/agent/completion/route.ts` | Fallback wenn WebLLM nicht verfuegbar |
| `python-backend/.env` | `AGENT_DEFAULT_UTILITY_MODEL` → kleines lokales Model |
| `python-backend/agent/llm_helper.py` | Utility-Call auf lokales Model umstellen |
| `python-backend/agent/memory/engine.py` | Hindsight LLM Config → llamacpp oder ONNX |
| `control-ui/.../ApiModelsTab.tsx` | Utility Models konfigurierbar |

---

## Offene Forschung

- [ ] WebSearch: transformers.js v3 WebGPU Performance Benchmarks 2026
- [ ] WebSearch: WebLLM vs transformers.js Vergleich fuer Autocomplete
- [ ] WebSearch: Whisper.cpp WebAssembly Qualitaet vs Cloud Whisper
- [ ] Test: `slim-summary-tiny-onnx` Qualitaet auf Hindsight Summarization Tasks
- [ ] Test: WebGPU Verfuegbarkeit auf verschiedenen Browsern (Chrome, Firefox, Safari)
