# Cohere Transcribe — ASR Model

> Analysiert am 02.04.2026 | HuggingFace: https://huggingface.co/CohereLabs/cohere-transcribe-03-2026

## Was ist es?

Production-Grade multilinguales Automatic Speech Recognition (ASR) Modell von Cohere. Released Ende Maerz 2026. Apache 2.0 lizenziert.

## Modell-Details

| Detail | Wert |
|---|---|
| Modell-ID | `CohereLabs/cohere-transcribe-03-2026` |
| Groesse | ~2B Parameter |
| Architektur | `CohereAsrForConditionalGeneration` (Whisper-Style Seq2Seq) |
| Interface | `AutoModelForSpeechSeq2Seq` / `pipeline("automatic-speech-recognition")` |
| Lizenz | Apache 2.0 |
| Zugang | Gated (auto-approval, HF Account + Agreement noetig) |
| Downloads | 71.028 (in ~1 Woche) |
| Likes | 714 |
| Modified | 2026-04-01 |

## Unterstuetzte Sprachen (14)

Arabisch, **Deutsch**, Griechisch, **Englisch**, Spanisch, Franzoesisch, Italienisch, Japanisch, Koreanisch, Niederlaendisch, Polnisch, Portugiesisch, Vietnamesisch, Chinesisch

## Community-Varianten (bereits verfuegbar)

| Variante | Repo | Format | Use Case |
|---|---|---|---|
| **ONNX** | onnx-community/cohere-transcribe-03-2026-ONNX | ONNX | Browser/Runtime |
| **ONNX INT8** | vigneshlabs/cohere-transcribe-03-2026-int8-onnx | ONNX INT8 | Leichteres ONNX |
| **GGUF** | cstr/cohere-transcribe-03-2026-GGUF | GGUF | llama.cpp/Ollama |
| **INT8 Safetensors** | smcleod/cohere-transcribe-03-2026-int8 | Safetensors | CPU Inference |
| MLX 8-bit | mlx-community/cohere-transcribe-03-2026-mlx-8bit | MLX | Apple Silicon |
| MLX fp16 | beshkenadze/cohere-transcribe-03-2026-mlx-fp16 | MLX | Apple Silicon |
| MLX 4/6-bit | beshkenadze/cohere-transcribe-03-2026-mlx-{4,6}bit | MLX | Apple Silicon quantized |
| CoreML fp16 | BarathwajAnandan/cohere-transcribe-03-2026-CoreML-fp16 | CoreML | iOS/macOS |
| Sherpa ONNX | csukuangfj2/sherpa-onnx-cohere-transcribe-* | Sherpa | Mobile/Embedded |
| Polish LoRA | AleksanderObuchowski/...-med-pl-lora-decoder-only | LoRA | Polnisch Medizin |

## Hardware-Anforderungen

| Praezision | Modellgroesse | RAM (CPU) | VRAM (GPU) | Machbar auf i7-2600 (8GB)? |
|---|---|---|---|---|
| FP32 | ~8 GB | ~10-12 GB | ~10 GB | Nein |
| FP16 | ~4 GB | ~6-8 GB | ~5 GB | Knapp (Swap) |
| **INT8** | **~2 GB** | **~4-5 GB** | **~3 GB** | **Ja, langsam** |
| **INT4 (GGUF Q4)** | **~1.2 GB** | **~3-4 GB** | **~2 GB** | **Ja, beste Option** |

### Empfohlene Varianten fuer CPU-only (kein GPU):
1. **GGUF Q4** (`cstr/cohere-transcribe-03-2026-GGUF`) — kleinste, schnellste
2. **INT8 Safetensors** (`smcleod/cohere-transcribe-03-2026-int8`) — besser Qualitaet

Erwartete CPU-Performance (i7-2600): ~0.3-0.5x Realtime (INT8), ~0.5-1x Realtime (Q4)

## Download-Voraussetzungen

1. HuggingFace Account erstellen (falls nicht vorhanden)
2. Lizenz akzeptieren auf: https://huggingface.co/CohereLabs/cohere-transcribe-03-2026
3. HF Token erstellen: https://huggingface.co/settings/tokens
4. Token konfigurieren:
   ```bash
   # Option A: Environment Variable
   export HF_TOKEN=hf_xxx

   # Option B: CLI Login
   huggingface-cli login
   ```

## Technische Details

- Tokenizer: `<|startoftranscript|>` / `<|endoftext|>` (Whisper-Style)
- Custom Code: `trust_remote_code=True` erforderlich
- Custom Classes: CohereAsrConfig, CohereAsrFeatureExtractor, CohereAsrProcessor, CohereAsrTokenizer
- Cloud: Azure Deployment verfuegbar (`deploy:azure` Tag)
- Benchmark: Gelistet auf hf-asr-leaderboard

## Quick Start (nach Token-Setup)

```python
from transformers import pipeline

pipe = pipeline(
    "automatic-speech-recognition",
    model="CohereLabs/cohere-transcribe-03-2026",
    trust_remote_code=True,
)

result = pipe("audio.wav")
print(result["text"])
```

## Vergleich mit Whisper

| Dimension | Cohere Transcribe | OpenAI Whisper Large-v3 |
|---|---|---|
| Parameter | ~2B | 1.55B |
| Sprachen | 14 | 99 |
| Lizenz | Apache 2.0 | MIT |
| Qualitaet (EN) | ASR Leaderboard (top) | Etablierter Standard |
| Community Forks | Sehr viele nach 1 Woche | Riesiges Oekosystem |
| Spezialitaet | Produktionsqualitaet, wenige Sprachen | Breite Sprachabdeckung |

## Relevanz fuer unser Projekt

### Direkt relevant:
- **Voice-AI Pipeline** — Transkription von Sprachnachrichten im Matrix-Chat
- **Multilingual** — Deutsch + Englisch + weitere europaeische Sprachen
- **On-Premise** — Apache 2.0, kein API-Call noetig

### Einschraenkungen:
- 2B Parameter = schwer auf unserem i7-2600 (INT8/Q4 noetig)
- 14 Sprachen vs. Whisper's 99 — reicht fuer EU-Sprachen, nicht fuer Global
- Gated Access — HF Token noetig

## Links

- HuggingFace: https://huggingface.co/CohereLabs/cohere-transcribe-03-2026
- GGUF Variante: https://huggingface.co/cstr/cohere-transcribe-03-2026-GGUF
- INT8 Variante: https://huggingface.co/smcleod/cohere-transcribe-03-2026-int8
- ONNX Variante: https://huggingface.co/onnx-community/cohere-transcribe-03-2026-ONNX
