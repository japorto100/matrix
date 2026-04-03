# MolmoWeb — AI Web Browser Agent

> Analysiert am 02.04.2026 | Repo: https://github.com/allenai/molmoweb | Lizenz: Apache 2.0

## Was ist MolmoWeb?

Ein spezialisierter multimodaler Web-Browser-Agent von Allen Institute for AI (Ai2). KEIN allgemeines Vision-Language-Modell — sondern trainiert um autonom einen Chromium-Browser zu steuern und natuerlichsprachliche Aufgaben auszufuehren.

**Beispiel:** "Finde den guenstigsten Flug von Berlin nach NYC naechsten Dienstag" → Agent oeffnet Browser, navigiert, klickt, tippt, vergleicht, liefert Ergebnis.

## Architektur

| Komponente | Detail |
|---|---|
| Vision Encoder | SigLIP 2 (google/siglip-so400m-patch14-384) |
| Language Backbone | Qwen3-8B (Alibaba) |
| Architektur-Klasse | Molmo2ForConditionalGeneration |
| Input | Screenshot (1280x720) + strukturierter Prompt |
| Output | Chain-of-Thought THOUGHT + strukturierte ACTION |
| Entwickler | Allen Institute for AI (Ai2), Seattle |
| Release | Maerz 2026 |

### Aktionsraum
```
THOUGHT: "Ich muss das Datum aendern. Das Datumsfeld ist oben rechts."
ACTION: click(x=892, y=234)

THOUGHT: "Jetzt das Datum eingeben."
ACTION: type("2026-04-15")

THOUGHT: "Suche starten."
ACTION: click(x=650, y=340)
```

## Verfuegbare Modelle

| Modell | Parameter | VRAM (float32) | Downloads | HuggingFace |
|---|---|---|---|---|
| **MolmoWeb-4B** | 4.85B | ~20 GB | 2.381 | https://huggingface.co/allenai/MolmoWeb-4B |
| **MolmoWeb-8B** | 8.66B | ~35 GB | 1.783 | https://huggingface.co/allenai/MolmoWeb-8B |
| MolmoWeb-4B-Native | 4.85B | ~20 GB | 68 | https://huggingface.co/allenai/MolmoWeb-4B-Native |
| MolmoWeb-8B-Native | 8.66B | ~35 GB | 19 | https://huggingface.co/allenai/MolmoWeb-8B-Native |

**Keine offiziellen Quantisierungen.** float32 empfohlen.

## Benchmarks

| Benchmark | MolmoWeb-8B pass@1 | pass@4 | Vergleich |
|---|---|---|---|
| **WebVoyager** | 78.2% | **94.7%** | Schlaegt GPT-4o (SoM) |
| **Online-Mind2Web** | 35.3% | 60.5% | SotA fuer offene Modelle |

### Test-Time Scaling (pass@4)
4 parallele Agent-Rollouts + Best-of-N Selection:
- WebVoyager: +16.5% absolut (78.2% → 94.7%)
- Online-Mind2Web: +25.2% absolut (35.3% → 60.5%)

## Hardware-Anforderungen

| Variante | Minimum GPU | Empfohlen |
|---|---|---|
| MolmoWeb-4B (float32) | RTX 3090/4090 (24GB) | A6000 (48GB) |
| MolmoWeb-8B (float32) | A100 (80GB) | 2x A40 |
| CPU-only | Nicht praktikabel | — |

## Trainingsdaten (alle oeffentlich)

| Dataset | Typ |
|---|---|
| MolmoWeb-HumanTrajs | Menschliche Web-Browsing-Trajektorien |
| MolmoWeb-HumanSkills | Menschliche Skill-Demonstrationen |
| MolmoWeb-SyntheticTraj | Synthetische Trajektorien |
| MolmoWeb-SyntheticSkills | Synthetische Skill-Demonstrationen |
| MolmoWeb-SyntheticQA | Synthetische QA auf Webseiten |
| MolmoWeb-SyntheticGround | Synthetische Grounding-Daten |

## Setup (Full Agent Stack)

```bash
git clone https://github.com/allenai/molmoweb.git
cd molmoweb
uv venv && uv sync
uv run playwright install chromium

# Weights herunterladen
bash scripts/download_weights.sh allenai/MolmoWeb-4B-Native

# Model Server starten (POST /predict)
bash scripts/start_server.sh ./checkpoints/MolmoWeb-4B-Native

# Agent ausfuehren
uv run python -c "
from inference import MolmoWeb
client = MolmoWeb(endpoint='http://localhost:8001', local=True, headless=True)
traj = client.run(query='Go to arxiv.org and find papers about Molmo', max_steps=10)
traj.save_html(query='my task')
"
```

### Inference Backends
- `native`: molmo2-native Format (schneller)
- `hf`: HuggingFace Transformers
- `fastapi`: Remote HTTP Endpoint
- `modal`: Serverless Modal Deployment
- `vllm`: Coming soon

## Die Molmo-Familie (Kontext)

| Modell | Aufgabe |
|---|---|
| Molmo2-8B | Allgemeines VLM |
| MolmoPoint-8B | Pixel-Level Pointing/Grounding |
| MolmoPoint-Vid-4B | Video Pointing/Tracking |
| MolmoAct-7B | Robot Action Prediction |
| MolmoBot-* | Robotics Manipulation |
| **MolmoWeb-4B/8B** | **Web Browser Agent** |

## Vergleich: MolmoWeb vs Pilot MCP

| Dimension | MolmoWeb | Pilot MCP |
|---|---|---|
| Ansatz | **Autonom** — sieht Screenshot, entscheidet selbst | **Augmentierend** — AI steuert echten Browser |
| Modell | 4B/8B eigenes VLM | Kein eigenes Modell (nutzt Claude/GPT) |
| GPU noetig | Ja (20-35 GB VRAM) | Nein |
| Auth/Login | Muss sich selbst einloggen | Nutzt bestehende Sessions |
| Cloudflare/CAPTCHAs | Kann scheitern (Chromium Fingerprint) | Kein Problem (echter Browser) |
| Staerke | Vollstaendig autonom, keine LLM API-Kosten | Token-effizient, auth-ready |

**Komplementaer einsetzbar:** MolmoWeb fuer autonome Batch-Tasks (z.B. 100 Webseiten systematisch abgrasen), Pilot fuer interaktive Tasks mit Login-Anforderungen.

## Relevanz fuer unser Projekt

### Direkt relevant:
- **Autonome OSINT-Recherche** — Agent durchsucht geopolitische Quellen ohne menschliche Interaktion
- **Batch-Processing** — Systematisches Abgrasen von Nachrichtenquellen, Think-Tanks, Regierungsseiten
- **Test-Time Scaling** — 4 parallele Agents fuer wichtige Recherchen = 94.7% Erfolgsrate

### Einschraenkungen:
- Braucht GPU-Server (Cloud oder eigene Hardware)
- Kein Cookie-Import, muss sich selbst authentifizieren
- Nicht fuer Real-Time geeignet (Latenz: Sekunden pro Schritt)

## Links

- GitHub: https://github.com/allenai/molmoweb
- Tech Report: https://allenai.org/papers/molmoweb
- Blog: https://allenai.org/blog/molmoweb
- Live Demo: https://molmoweb.allen.ai/
- Alle Modelle: https://huggingface.co/collections/allenai/molmoweb
- Alle Datasets: https://huggingface.co/collections/allenai/molmoweb-data
