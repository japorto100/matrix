# Autoresearch — Analyse & Anwendungspotenzial

> Quelle: `_ref/autoresearch` (karpathy/autoresearch)
> Stand: 2026-04-03

## Was ist autoresearch?

Ein Framework von Andrej Karpathy für **vollautonome LLM-Trainingsforschung**. Ein KI-Agent (Claude, Codex) bekommt:

- **Eine einzige editierbare Datei** (`train.py`) — GPT-Modell, Optimizer, Training Loop
- **Ein festes 5-Minuten-Zeitbudget** pro Experiment (Wall-Clock)
- **Eine einzelne Metrik** (`val_bpb` — Validation Bits per Byte, niedriger = besser)

Der Agent läuft in einer Endlosschleife: Hypothese formulieren → `train.py` ändern → trainieren → messen → behalten oder verwerfen. ~12 Experimente/Stunde, ~100 über Nacht. Kein menschliches Eingreifen nötig.

## Kernarchitektur (3 Dateien)

| Datei | Wer kontrolliert | Inhalt |
|-------|-----------------|--------|
| `program.md` | **Mensch** | Forschungsstrategie, Agent-Instruktionen |
| `train.py` | **Agent** | GPT-Modell (~50M Params), MuonAdamW Optimizer, Hyperparameter |
| `prepare.py` | **Niemand** (read-only) | Daten-Download, Tokenizer, Eval-Harness — tamper-proof |

### Design-Prinzipien

1. **Festes Zeitbudget** → Experimente sind vergleichbar unabhängig von Modellgröße/Batch Size
2. **Single-File Mutation** → Agent-Scope ist begrenzt, Diffs sind reviewbar
3. **Keine neuen Packages** → Angriffsflache bleibt konstant
4. **Fast Fail** → Loss NaN oder >100 → sofortiger Exit
5. **Git als Experiment-Tracker** → Branch pro Experiment-Serie, Reset bei Fehlschlag

## Technischer Stack

- **ML**: PyTorch 2.9.1, Flash Attention 3, torch.compile
- **Optimizer**: MuonAdamW — Muon (Newton-Schulz Orthogonalisierung) für 2D-Matrizen, AdamW für Embeddings
- **Daten**: `climbmix-400b-shuffle` (HuggingFace), BPE Tokenizer (vocab=8192)
- **Packaging**: uv (Rust-basiert)
- **Hardware**: Single NVIDIA GPU (H100 getestet)

## Experiment-Loop (aus program.md)

```
LOOP FOREVER:
  1. Hypothese formulieren
  2. train.py hacken (Architektur, Optimizer, Hyperparameter)
  3. git commit
  4. uv run train.py > run.log 2>&1
  5. grep "^val_bpb:|^peak_vram_mb:" run.log
  6. Crash? → tail -50 run.log → Fix oder aufgeben
  7. Ergebnis in results.tsv loggen
  8. val_bpb verbessert → commit behalten (advance)
  9. val_bpb gleich/schlechter → git reset
  10. NIEMALS STOPPEN, NIEMALS FRAGEN
```

Ergebnis: 125 autonome Experimente, val_bpb von ~0.998 auf 0.970 verbessert.

## GPT-Modellarchitektur (Highlights)

- GQA (Grouped Query Attention) + RoPE + QK-Norm
- Sliding Window Pattern (SSSL): 3x halbe Kontextlänge, 1x volle
- Value Embeddings (ResFormer): Alternierend, input-dependent Gate
- Skip Connections: Residual + gelernter Skip vom Input-Embedding
- MLP: 4x Expansion, Squared ReLU, kein Bias
- Softcap Logits bei ±15 (Tanh)

---

## Anwendungspotenzial für Matrix

### 1. Autonomes Prompt/Config-Tuning (hohe Relevanz)

**Pattern übertragen**: Agent optimiert iterativ System-Prompts, Tool-Beschreibungen oder `consent_policy.yaml` gegen ein festes Eval-Set.

- `program.md` → Skill-Datei mit Optimierungsstrategie
- `train.py` → die zu optimierende Config/Prompt-Datei
- `prepare.py` → fester Eval-Harness (z.B. Testfälle für Agent-Responses)
- Metrik: Accuracy, F1, oder benutzerdefinierter Score

### 2. Agent-Skill als Experiment-Runner (hohe Relevanz)

Das `program.md`-Konzept direkt als **Agent-Skill-Pattern** implementieren:

```
skill: autonomous-experiment
inputs:
  - mutable_file: "die Datei die der Agent ändern darf"
  - eval_command: "Befehl der die Metrik ausgibt"
  - metric_name: "Name der Metrik (lower-is-better)"
constraints:
  - time_budget_per_run: 300s
  - max_experiments: 100
  - packages: frozen
```

Anwendbar auf jede Aufgabe mit messbarer Metrik: Hyperparameter-Suche, Config-Tuning, Template-Optimierung.

### 3. Sandbox-Security-Pattern (exec-12)

Die Architektur-Trennung ist ein **Blueprint für sichere Agent-Sandboxes**:

| autoresearch | Matrix exec-12 Äquivalent |
|---|---|
| `prepare.py` (read-only, tamper-proof) | Fester Eval-Harness, System-Invarianten |
| `train.py` (Agent-editierbar) | Agent-Workspace innerhalb Sandbox |
| Keine neuen Packages | Whitelist erlaubter Operationen |
| Git Reset bei Fehlschlag | Sandbox-Rollback |

### 4. PDDL-Planning Integration (exec-14)

Das autoresearch-Loop-Pattern passt zu PDDL-basierter Planung:

- **Hypothese** → PDDL Action
- **Experiment** → Action-Ausführung
- **val_bpb** → State-Evaluation
- **Keep/Discard** → Plan-Revision

### 5. Knowledge-Graph Embedding-Optimierung (mittlere Relevanz)

Falls lokale Embeddings trainiert werden: autoresearch-Pattern für automatische Hyperparameter-Suche (Dimensionalität, Learning Rate, Modellgröße).

### 6. MuonAdamW Optimizer (Referenz)

State-of-the-art Single-GPU Optimizer-Implementierung. Relevant falls Matrix eigene Modelle trainiert:

- Newton-Schulz Orthogonalisierung für stabile Gradients
- Separate LR-Skalierung nach Param-Shape
- torch.compile fused kernels für Performance

---

## Zentrale Erkenntnis

Der eigentliche Wert von autoresearch liegt nicht im ML-Code, sondern im **Meta-Pattern**:

> **Mensch programmiert die Strategie (Markdown), Agent führt Experimente autonom aus, Git trackt alles.**

Dieses Pattern ist generalisierbar auf jede Domäne mit:
1. Einer messbaren Metrik
2. Einer klar abgegrenzten "mutable zone" (was der Agent ändern darf)
3. Einer tamper-proof Evaluation
4. Einem Rollback-Mechanismus (Git)

## Nächste Schritte

- [ ] Generisches `autonomous-experiment` Skill-Template entwerfen
- [ ] Eval-Harness-Pattern aus `prepare.py` für Agent-Tool-Testing adaptieren
- [ ] Sandbox-Architektur (exec-12) um autoresearch-Isolation-Pattern erweitern
- [ ] Prüfen: Windows-Fork (`jsegov/autoresearch-win-rtx`) für lokale Tests
