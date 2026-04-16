# Exec Updates 2026-04-16

Kurze Uebergabe fuer andere Instanzen: Diese Execs wurden heute neu erstellt
oder gegen `memory_kg.md` nachgezogen.

## Neu angelegt

### `specs/execution/exec-world-model.md`

- Neuer Owner fuer `Global World Evidence`, `Claim Layer`, `Global World KG`
  und Adjudication.
- Trennt die globale Wissensseite sauber von `exec-memory`.
- Enthaelt erste Checklisten fuer Claims, Konflikte, Provenance,
  Degradation-Flags und World-Query-Pipeline.

### `specs/execution/exec-personal-kb.md`

- Neuer Owner fuer `Personal Knowledgebase`.
- Trennt kuratierte User-Artefakte sauber von `Personal Memory`.
- Deckt Capture/Import, Inbox/Library/Notes, KB-Retrieval und UI-/UX-Referenzen
  (`Recall`, `TriliumNext`) ab.

## Bestehende Execs erweitert

### `specs/execution/exec-memory.md`

- Jetzt explizit auf `Personal Raw Evidence` und `Personal Derived Memory`
  zugeschnitten.
- Neue Leitregeln: User-Input = Evidenzquelle, nicht automatisch `truth` oder
  `belief`; Agent-Output = sekundaeres Artefakt.
- Neuer Block fuer Default-Routing:
  - `chat/tool/scratch -> personal raw`
  - `observation/preference -> personal derived`
  - `pdf/webclip/transcript -> personal KB`
  - `news/claims -> world`
- Neue Checkboxen fuer:
  - `source_type`
  - Promotion-Gates `raw -> derived`
  - Evidence-/Source-Backlinks
  - Guardrails gegen stilles Mischen mit KB / World
  - Query-Typen fuer Memory-Evals (`verbatim`, `derived`, `cross-session`,
    `forgetting`)

### `specs/execution/exec-context.md`

- Neue Runtime-Checkboxen fuer Consumer-/Layer-Policies aus `memory_kg.md`.
- `Personal Knowledgebase` jetzt explizit als eigene Retrieval-Schicht.
- Neue Degradation-/Policy-Flags:
  - `NO_WORLD_KG`
  - `NO_WORLD_EVIDENCE`
  - `NO_PERSONAL_MEMORY`
  - `NO_PERSONAL_KB`
  - `WORLD_CLAIM_CONFLICT`
- Verify-Gates erweitert: kein Merge ohne sichtbare Layer-/Status-Signale.

### `specs/execution/exec-harness.md`

- Von generischem Trace-/Pareto-Harness auf `layer-aware` /
  `consumer-aware` Harness erweitert.
- Neue Arbeitspunkte fuer:
  - `world` / `personal_memory` / `personal_kb` / `mixed` Query-Typen
  - consumer-spezifische Harness-Configs
  - Policy-/Grounding-aware Scoring
  - Degradation-Flags als Eval-Signal

### `specs/execution/exec-18-unified-agent-schema.md`

- Abhaengigkeiten um `exec-world-model`, `exec-personal-kb`, `exec-context`
  erweitert.
- Bounded-Context-Richtung ergaenzt:
  - optionales Schema `personal_kb`
  - optionales Schema `world`
- Neue optionale Sektionen:
  - `019 personal_kb.*`
  - `020 world.*`
- Wichtig: als Richtung / Schema-Vorschlag, nicht als sofortige Umsetzung.

### `specs/execution/exec-15-memory-control-ui.md`

- Neue UI-Trennung vorbereitet:
  - `Memory Browser`
  - `Personal Knowledgebase`
  - `Global World Model`
- Upload-Target-Logik erweitert:
  - `Personal Memory`
  - `Personal Knowledgebase`
  - `Global World Evidence`
- Neue Phase `6b` fuer KB-/World-Surfaces, Layer-Badges und
  Degradation-Signale.

### `specs/execution/README.md`

- Exec-Landkarte aktualisiert.
- Neue Reihenfolge:
  - `exec-memory`
  - `exec-world-model`
  - `exec-personal-kb`
  - `exec-context`
  - `exec-harness`
  - `exec-skills`
- Neue Execs in der Tabelle aufgenommen.

## Wichtig fuer Folgearbeit

- `memory_kg.md` ist jetzt die begriffliche Leitplanke.
- `exec-memory` = persoenliche Memory-Seite
- `exec-world-model` = globale Wissensseite
- `exec-personal-kb` = kuratierte User-Artefakte
- `exec-context` = Runtime-Assembly / Degradation / Merge
- `exec-harness` = Tuning ueber diese Schichten hinweg

## Noch nicht umgesetzt im Code

Diese Aenderungen sind bisher **Exec-/Doku-Arbeit**, keine tiefe Runtime-
Implementierung.

Offene produktive Folgepunkte liegen jetzt vor allem in:

- `memory_fusion/`
- `agent/memory/`
- `experiments/memory_eval/`
- spaeter `exec-18` / API-Routen / UI-Surfaces
