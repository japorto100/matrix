# Agent Harness

> **Stand:** 16. April 2026
> **Zweck:** Root-Leitdokument fuer den Harness-Layer um Agenten herum:
> Laufzeitbegrenzung, Verify-/Correct-Schleifen, Guardrails, Sandboxing und
> eval-getriebene Governance.
> **Herkunft:** Matrix-adaptierte Fassung der Runtime-Harness-Leitlinien aus
> `trading-project/docs/AGENT_HARNESS.md`.
> **Abgrenzung:**
> - `AGENT_ARCHITECTURE.md` beschreibt Rollen und Orchestration.
> - `AGENT_SECURITY.md` beschreibt Security- und Policy-Grenzen.
> - `AGENT_RUNTIME_ARCHITECTURE.md` beschreibt verbindliche Runtime-Defaults.

---

## 1. Harness-Prinzipien

Der Harness folgt vier Standardfunktionen:

1. **Constrain**
   - Capability Envelope
   - Budget- und Scope-Grenzen
   - Tool-/Storage-Boundaries
   - Sandbox-Isolation
2. **Inform**
   - kuratierter Kontext statt breitem Prompt-Bloat
   - provenance-markierte Inputs
   - feste Prioritaet `system > policy > intent > data > tool_result`
3. **Verify**
   - Output-Checks
   - Negativtests
   - strukturierte Runtime-Validatoren
   - reproduzierbare Eval-Gates
4. **Correct**
   - Retry-/Repair-/Fallback-Pfade
   - Replan mit Abbruchkriterien
   - Human-Approval fuer High-Risk-Pfade

---

## 2. Minimalismus als Default

Leitregel: weniger Runtime-Komplexitaet, mehr messbare Stabilitaet.

Nicht-Ziele:

- Tool-Flatrates im Prompt
- breite Subagent-Topologien ohne harte Kontextisolation
- Framework-Bloat ohne Reliability-Gewinn

Ziele:

- kleines, klares Toolset pro Agent-Klasse
- stabile Prompt-Struktur
- Artefakte ausserhalb des Promptfensters
- klare Failure-Modes

---

## 3. Guardrails gehoeren in die Laufzeit

Guardrails duerfen nicht nur Prompt-Hoffnungen sein.

Pflichtpunkte:

- Input-Validierung und Injection-Hygiene vor LLM und Tool
- Retrieval-/Execution-Rails zwischen Agent und Action
- Output-Validierung gegen Schema, Policy und Leak-Regeln
- klares Reject-/Repair-Verhalten mit maschinenlesbaren Gruenden

---

## 4. Complete Mediation

Jeder sicherheitsrelevante Zugriff geht durch denselben Entscheidpfad.

Arbeitsregeln:

- kein direkter Shortcut von Agent zu Tool, Storage oder Netz
- kein „trusted fast lane“ ohne Policy-Pruefung
- jeder Tool-Call braucht Envelope plus Context-Integrity-Check
- jeder Retrieval-Pfad bleibt von Write-Pfaden getrennt

---

## 5. Kontextintegritaet

Der Harness erzwingt:

- Kontextquellen sind klassifiziert (`policy`, `intent`, `data`, `tool_result`)
- Prioritaetskette ist fix und nicht promptseitig ueberschreibbar
- Task-Wechsel erzwingt Re-Validation statt stiller Weiterfuehrung
- konflikthafte oder unvollstaendige Evidenz senkt Confidence oder blockiert
  Action-Pfade

Das ist besonders wichtig fuer:

- Memory-Retrieval
- GraphRAG-/Web-Sourcing
- Tool-Entscheidungen
- Approval-Gates

---

## 6. Sandboxing

Matrix-Default fuer agentische Code-/Tool-Execution:

- isolierte Runtime-Grenze
- keine direkte Host-Ausfuehrung von agentisch erzeugtem Code
- Netz-/Filesystem-Rechte task- und envelope-gebunden
- Session-Lifecycle, Audit-Trace und Kill-Switch sind Pflicht

Der Harness behandelt Sandbox-Isolation als Sicherheits- und
Reproduzierbarkeitsbasis, nicht als optionales Komfortfeature.

---

## 7. Observability und Regression-Gates

Produktionsnahe Agent-Qualitaet wird ueber Gates abgesichert, nicht ueber
Einzelprompt-Optimierung.

Pflichtfamilien:

- Injection-/Leakage-/Tool-Misuse-Regressionen
- Eval-Suiten pro Aufgabenklasse
- Traces fuer `input -> retrieval -> tool -> output`
- Drift-Checks bei Modell-, Prompt- oder Tool-Aenderungen

Mindestausgabe:

- Fehlercodes
- Degradation Flags
- Audit-Events
- Telemetrie fuer Kosten, Latenz, Erfolg und Abbruchgruende

---

## 8. Verify-Gates

### Harte technische Gates

- lokale oder CI-nahe reproduzierbare Tests
- negative Tests fuer Missbrauchspfade
- Postgres-/Backend-Smokes fuer kritische Memory-/Policy-Pfade

### Dokumentierte, aber nicht lokal erzwingbare Gates

- echte Full-Stack-E2E gegen laufende Frontends/Gateways
- Browser- oder Session-gebundene Verifikation, wenn `.env` und Runtime fehlen

Solche Gates bleiben dokumentiert, blockieren aber keinen Backend-Slice, wenn
ein gleichwertiger Postgres-/Runtime-Smoke vorhanden ist.

---

## 9. FinOps und Token-Disziplin

Der Harness ist auch Kosten- und Kontext-Disziplin:

- Prefix-/Prompt-Caching nur mit klaren Security-Grenzen
- Tokenbudgets pro Task-Typ
- keine implizite Rechtfertigung fuer groessere Kontextfenster statt besserem
  Retrieval
- Modellwechsel nur mit Eval-/Drift-Nachweis

---

## 10. Verbindung zu Memory

Fuer `exec-memory` bedeutet der Harness konkret:

- `personal_raw` und `personal_derived` brauchen sichtbare Policy-Grenzen
- ungrounded Derived wird nicht still im LLM-Kontext genutzt
- Memory-Operationen brauchen Runtime-Logging
- Verify erfolgt bevorzugt ueber Postgres-Smokes und gezielte Runtime-Tests
- Full-Stack-UI-Gates bleiben offen dokumentiert, wenn die Laufumgebung fehlt

---

## 11. Einfuehrungsreihenfolge

1. Root-Policies und Runtime-Grenzen dokumentieren.
2. Memory-/Context-Runtime auf Policy und Audit ausrichten.
3. Postgres-Smokes als echte Gates etablieren.
4. Danach Retrieval-Rewrite, Self-RAG und komplexere Eval-Suiten ausbauen.

---

## 12. Querverweise

- `AGENT_ARCHITECTURE.md`
- `AGENT_RUNTIME_ARCHITECTURE.md`
- `AGENT_SECURITY.md`
- `AGENT_TOOLS.md`
- `CONTEXT_ENGINEERING.md`
- `MEMORY_ARCHITECTURE.md`
