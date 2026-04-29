# Browser-RAG / GraphRAG Modelle: WebGPU first, CPU/WASM fallback

Status: Notiz / Kandidatenliste, 2026-04-29.

Ziel: Modelle sammeln, die direkt im Browser laufen koennen, bevorzugt via `@huggingface/transformers` WebGPU, mit WASM/CPU-Fallback wo sinnvoll. Server-seitige Modelle sind hier nur als Fallback/Referenz genannt.

## Leitlinie

Browser-aktive Modelle muessen anders bewertet werden als normale Backend-Modelle:

| Kriterium | Browser-first Entscheidung |
|---|---|
| Runtime | Web Worker, nie Main Thread |
| Backend | WebGPU bevorzugt, WASM/CPU fallback |
| Download | ideal <100 MB, tolerierbar <500 MB, LLMs nur opt-in |
| Cache | Cache API / IndexedDB / OPFS, nicht jedes Mal neu laden |
| Privacy | Query-, Chat- und Dokument-Embeddings lokal moeglich |
| Consistency | Embedding-Modell muss zur Server-/Index-Version passen |

Pflicht-Fallback:

```ts
const device =
  navigator.gpu ? "webgpu" :
  "wasm";
```

Besser: WebGPU versuchen, bei Fehler auf WASM und danach Server-Fallback gehen.

## Bonsai LLMs

Lokal bereits vorhanden:

| Modell | Zweck | Browser | CPU lokal | Lokaler Pfad |
|---|---|---:|---:|---|
| Bonsai 1.7B GGUF Q1_0 | schneller CPU-Test / Toy Assistant | nein | ja, ca. 15-25 tok/s | `/mnt/cold-storage/models/huggingface/models--prism-ml--Bonsai-1.7B-gguf/snapshots/210a9e99f79cb184909d49595906526eb2b3dd9a/Bonsai-1.7B-Q1_0.gguf` |
| Bonsai 8B GGUF Q1_0 | brauchbarerer lokaler Chat | nein | ja, ca. 5 tok/s | `/mnt/cold-storage/models/huggingface/models--prism-ml--Bonsai-8B-gguf/snapshots/48516770dd04643643e9f9019a2a349cf26c5dbd/Bonsai-8B-Q1_0.gguf` |
| `onnx-community/Bonsai-1.7B-ONNX` q1 | Transformers.js / WebGPU Demo | ja, wenn WebGPU | theoretisch WASM, aber nicht attraktiv | HF cache |
| `onnx-community/Bonsai-8B-ONNX` q1 | WebGPU Experiment | ja, moderne GPU noetig | WASM/CPU praktisch nicht empfohlen | HF cache |

Einschaetzung:

- Auf dieser Maschine: Bonsai via Browser/WebGPU wahrscheinlich nicht sinnvoll, CPU/GGUF dagegen funktioniert.
- In der Webapp: Bonsai nur als opt-in Offline-LLM, nicht als Default.
- CPU-Fallback fuer LLMs im Browser ist kritisch: WASM kann funktionieren, aber blockiert Ressourcen stark und ist UX-riskant. Fuer LLMs besser: WebGPU oder Server-Fallback.
- Fuer RAG reicht ein lokales LLM nicht; wichtiger sind Embeddings + Reranking + gute Retrieval-UX.

llama.cpp Start:

```bash
/home/lipfi2/tools/llama.cpp/build/bin/llama-cli \
  -m /mnt/cold-storage/models/huggingface/models--prism-ml--Bonsai-8B-gguf/snapshots/48516770dd04643643e9f9019a2a349cf26c5dbd/Bonsai-8B-Q1_0.gguf \
  -c 2048 \
  -t 4 \
  -cnv \
  -sys "Du bist ein lockerer deutscher Chat-Assistent. Antworte kurz, natuerlich und direkt."
```

## Embedding-Modelle im Browser

Prioritaet: klein, schnell, solide Qualitaet, Transformers.js-kompatibel.

| Rang | Modell | Sprache | Dim | Browser-Fit | Einsatz |
|---:|---|---|---:|---|---|
| 1 | `Xenova/all-MiniLM-L6-v2` | EN, brauchbar multilingual aber nicht ideal | 384 | sehr gut, q8 klein | Baseline, Query-Embedding, schnelle Suche |
| 2 | `sentence-transformers/all-MiniLM-L6-v2` via ONNX/Xenova | EN | 384 | sehr gut | Muss zu bestehendem Backend passen |
| 3 | `intfloat/multilingual-e5-small` / ONNX-Port | multilingual, DE gut | 384 | gut, wenn ONNX verfuegbar | Deutscher Chat, Matrix-Messages |
| 4 | `BAAI/bge-small-en-v1.5` / ONNX-Port | EN | 384 | gut | bessere Retrieval-Qualitaet EN |
| 5 | `mixedbread-ai/mxbai-embed-xsmall-v1` | multilingual/modern | typ. klein | sehr interessant fuer WebGPU | moderner Browser-Kandidat |
| 6 | `nomic-ai/nomic-embed-text-v1.5` | EN/multilingual brauchbar | 768 | schwerer | nur wenn Qualitaet wichtiger als Download |
| 7 | `jinaai/jina-embeddings-v2-small-en` | EN | 512 | mittel | Long-context Embedding Experiment |

Empfehlung fuer matrix:

| Phase | Default |
|---|---|
| Sofort | `Xenova/all-MiniLM-L6-v2` wegen bestehender 384-dim Pipeline |
| Deutsch besser | `multilingual-e5-small` ONNX/Transformers.js evaluieren |
| Modern/browser-first | `mxbai-embed-xsmall-v1` mit WebGPU testen |
| Server-Kompatibilitaet | Modellname + Dimension + Quantisierung versionieren |

Wichtig: Frontend-Embeddings duerfen nicht still auf ein anderes Modell wechseln. Vektorindex braucht Felder wie:

```text
embedding_model = "Xenova/all-MiniLM-L6-v2"
embedding_dim = 384
embedding_runtime = "transformersjs-webgpu-q8"
embedding_version = "2026-04-browser-rag-v1"
```

## Reranker / Cross-Encoder im Browser

Reranking ist teurer als Embedding. Im Browser nur Top-K klein halten.

| Modell | Typ | Browser-Fit | Empfehlung |
|---|---|---|---|
| `Xenova/ms-marco-MiniLM-L-6-v2` / Cross-Encoder Port | Cross-Encoder | gut, klein | bester erster Browser-Reranker |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` via ONNX | Cross-Encoder | gut wenn exportiert | top 10-20 reranken |
| `BAAI/bge-reranker-base` | Cross-Encoder | schwer | eher Server, Browser nur Power-User |
| `BAAI/bge-reranker-v2-m3` | multilingual Reranker | schwer | Server-Fallback fuer DE/multilingual |
| `jinaai/jina-reranker-v2-base-multilingual` | multilingual Reranker | eher schwer | Server oder opt-in WebGPU |

Browser-Pattern:

```text
1. Browser embedded Query
2. Server oder local IndexedDB liefert top 50 candidates
3. Browser rerankt nur top 10-20
4. UI zeigt reranked snippets + evidence
```

Nicht versuchen: 500 Dokumente im Browser cross-encoden.

## Sparse / Hybrid Retrieval

Fuer RAG/GraphRAG ist dense-only oft schlechter als hybrid.

| Komponente | Browser-Fit | Notiz |
|---|---|---|
| BM25 in JS | sehr gut | Fuer lokale IndexedDB/OPFS-Dokumente gut |
| MiniSearch / FlexSearch | sehr gut | schnelle lokale Textsuche |
| SPLADE | schlecht | zu schwer fuer Browser default |
| ColBERT late interaction | schwer | spannend, aber Browser default zu komplex |
| Hybrid dense + BM25 | sehr gut | bester Pragmatismus |

Empfohlene lokale Pipeline:

```text
BM25/FlexSearch top 100
+ dense embedding cosine top 100
=> merge/RRF
=> cross-encoder top 10-20
=> answer generation / snippet answer
```

## GraphRAG-spezifische Browser-Modelle

GraphRAG braucht nicht nur Embeddings, sondern Entity/Relation/Claim-Strukturen.

| Task | Browser-Modelltyp | Kandidaten | Fit |
|---|---|---|---|
| Entity Extraction | token-classification NER | DistilBERT/BERT NER ONNX, multilingual NER | gut |
| Relation Extraction | text-classification / zero-shot | kleine DeBERTa/MiniLM Klassifikatoren | mittel |
| Claim Extraction | kleines seq2seq/LLM | Bonsai 1.7B/8B, T5-small, DistilBART | experimentell |
| Topic/Intent | text-classification | MiniLM/DistilBERT classifier | gut |
| Dedup/Entity Linking | embeddings + string similarity | MiniLM/E5 + Fuse.js | sehr gut |
| Clustering | JS algorithmisch | HDBSCAN/Leiden/WASM optional | gut |

Browser-GraphRAG sollte nicht versuchen, den kompletten Knowledge Graph lokal zu bauen. Besser:

```text
Browser:
- lokale Query-Embeddings
- lokales Reranking
- temporaere Entities aus aktueller Seite/Chat
- privacy-sensitive prefiltering

Server:
- persistenter KG
- globale Entity Resolution
- cross-user/cross-room Memory
- Audit, Auth, Versionierung
```

## Sonstige nuetzliche Browser-Modelle fuer RAG-UX

| Task | Kandidat | Browser-Fit | Nutzen |
|---|---|---|---|
| Language Detection | `Xenova/fasttext-language-identification` oder kleines classifier model | gut | Modellroute DE/EN |
| Sentiment/Tone | DistilBERT SST-2 / multilingual sentiment | gut | Chat/Feed Labels |
| Summarization | `Xenova/distilbart-cnn-6-6` | mittel | kurze Snippets, nicht lange Docs |
| STT | Whisper tiny/base ONNX | mittel | Voice fallback |
| File-Type Detection | Magika ONNX | sehr gut | Upload/Ingestion precheck |
| PII Detection | NER + regex | gut | Browser-side privacy guard |

## Webapp Runtime-Architektur

Empfohlene Worker-Aufteilung:

```text
main thread
  -> rag-worker
      - embedding model
      - BM25/FlexSearch
      - vector scoring
  -> rerank-worker
      - cross-encoder, lazy loaded
  -> llm-worker
      - Bonsai/WebLLM only opt-in
```

Fallback-Kette:

```text
WebGPU Transformers.js
  -> WASM Transformers.js
  -> server endpoint
```

Fuer LLMs:

```text
WebGPU/WebLLM/Bonsai
  -> server LLM
```

Kein automatischer Browser-CPU-LLM-Fallback fuer normale User. Das kann alte Maschinen hart blockieren.

## Konkrete Matrix-Defaults

| Use Case | Default | Fallback |
|---|---|---|
| Query embedding | `Xenova/all-MiniLM-L6-v2` q8 | Server embedding |
| Deutsches Retrieval | `multilingual-e5-small` evaluieren | Server embedding |
| Browser reranking | MiniLM cross-encoder top 10 | Server reranker |
| Local lexical search | FlexSearch/MiniSearch | Server search |
| Offline answer | Bonsai 8B WebGPU nur opt-in | Server LLM |
| Old hardware | Embeddings ja, LLM nein | Server LLM |

## Offene Checks

- Welche der Kandidaten haben saubere ONNX/Transformers.js Artefakte mit WebGPU?
- Welche Modelle laufen in Chromium mit `dtype: "q8"` bzw. `dtype: "q4"` stabil?
- Kann `mxbai-embed-xsmall-v1` die bestehende MiniLM-Pipeline ersetzen, ohne Index-Migration zu teuer zu machen?
- Braucht Matrix fuer Deutsch zwingend multilingual-e5-small als neuen Standard?
- Reranker: MiniLM im Browser vs. bge-reranker serverseitig A/B testen.

## Lokaler Testbestand

HF cache:

```text
/mnt/cold-storage/models/huggingface/
```

Bonsai 1.7B:

```text
models--prism-ml--Bonsai-1.7B-gguf
models--onnx-community--Bonsai-1.7B-ONNX
```

Bonsai 8B:

```text
models--prism-ml--Bonsai-8B-gguf
models--onnx-community--Bonsai-8B-ONNX
```

llama.cpp:

```text
/home/lipfi2/tools/llama.cpp/build/bin/llama-cli
```

## Kurzfazit

Fuer matrix ist der groesste Hebel nicht Browser-LLM, sondern Browser-RAG:

```text
Embeddings lokal
+ Hybrid Search
+ kleines Reranking
+ Server/KG als persistente Wahrheit
+ LLM nur opt-in/offline
```

Bonsai ist als Offline-LLM spannend. Fuer produktiven Browser-RAG sind MiniLM/E5/mxbai + kleiner Cross-Encoder wichtiger.
