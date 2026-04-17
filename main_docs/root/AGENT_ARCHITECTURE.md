# Agent Architecture

> **Stand:** 16. April 2026
> **Zweck:** Root-Leitdokument fuer Agent-Rollen, Orchestration, Guard-Grenzen,
> heterogene Modellpfade und Registry-Regeln in Matrix.
> **Herkunft:** Matrix-adaptierte Fassung der vorhandenen Architekturleitlinien aus
> dem Schwesterprojekt `trading-project/docs/AGENT_ARCHITECTURE.md`.
> **Abgrenzung:**
> - `AGENT_SECURITY.md` definiert Retrieval Broker, Capability Envelope,
>   Agentic-Storage-Grenzen und Security-Gates.
> - `AGENT_HARNESS.md` buendelt Runtime-Haertung, Sandboxing und
>   Verify-/Correct-Schleifen.
> - `AGENT_RUNTIME_ARCHITECTURE.md` ist die kurze Owner-Spec fuer verbindliche
>   Runtime- und Memory-Write-Regeln.
> - `CONTEXT_ENGINEERING.md` definiert Consumer-spezifische Context-Assembly.
> - `MEMORY_ARCHITECTURE.md` definiert die Speicher- und Wissensschichten.

---

## 1. Kernprinzipien

1. Agenten sind **untrusted orchestrators**, keine impliziten Truth-Owner.
2. Deterministische Backends entscheiden ueber Regeln, Freigaben und Mutationen.
3. Search, Replan und Mehrschrittpfade werden explizit modelliert statt still
   dem LLM ueberlassen.
4. Reproduzierbarkeit, Audit und Policy gehen vor maximaler Tool-Autonomie.
5. Multi-Agent-Topologien sind Mittel zum Zweck, kein Selbstzweck.

---

## 2. Verbindliches Vier-Rollen-Pattern

Jeder mehrstufige Agent-Workflow folgt standardmaessig diesem Pattern:

1. **Extractor**
   - LLM-basiert
   - extrahiert Marker, Claims, Kandidaten oder Strukturen
   - darf keine Scores oder Wahrheitsschichten direkt aendern
2. **Verifier**
   - LLM + Regeln
   - prueft Extraktionen auf Kontext, Evidenz und Widersprueche
   - arbeitet konservativ und rejectet im Zweifel
3. **Deterministic Guard**
   - Code-only
   - einzige Instanz, die Schwellen, Klassen und Freigaben deterministisch setzt
4. **Synthesizer**
   - LLM-basiert
   - formuliert den Guard-/Verifier-Output fuer User oder Folgeagenten aus

### Warum der Guard code-only bleibt

- unit-testbar
- auditierbar
- nicht prompt-injectable
- reproduzierbar
- schnell genug fuer produktionsnahe Gates

---

## 3. Orchestration Default

### 3.1 Plan-Execute-Replan

Matrix nutzt fuer agentische Control-Flows standardmaessig:

1. Planner erzeugt oder aktualisiert einen expliziten Planstand.
2. Executor/Orchestrator arbeitet den naechsten Schritt gegen diesen Planstand ab.
3. Replanner bewertet Ergebnisse, Fehler und fehlende Evidenz und passt den Plan
   kontrolliert an.

### 3.2 Laufzeitentscheidung

| Ebene | Default | Wann |
|---|---|---|
| Agent-/Reasoning-Workflows | `LangGraph` | mehrstufige Agent-Laeufe, HITL, Checkpoints, Resume |
| Produkt-/Business-Workflows | `Temporal` spaeter gezielt | langlebige, produktkritische Orchestration |

Arbeitsregel:

- `LangGraph` zuerst im Python-Agent-Layer
- `Temporal` nur bei real belegter Durability-/Operations-Notwendigkeit
- kein frueher Doppelausbau ohne klare Boundary

---

## 4. Erweiterte Rollen

Zusaetzlich zum Vier-Rollen-Pattern sind folgende Rollen erlaubt, wenn ihre
Boundary und Policy explizit beschrieben sind:

- **Router**
  - klassifiziert Task-Typ, Risiko und benoetigte Faehigkeiten
- **Research Agent**
  - sammelt Quellen und Luecken, aber mutiert keine Wahrheitsschichten direkt
- **Evaluator**
  - prueft Ergebnisqualitaet, Evidenzdichte und Widersprueche
- **Monitor**
  - aggregiert Telemetrie, Drift und Runtime-Schwachstellen

---

## 5. Agent Registry und Tool-System

Jede Agent-Klasse wird ueber eine explizite Registry beschrieben:

- `agent_class`
- erlaubte Tool-Gruppen
- Context-/Memory-Zugriff
- Policy-Tier (`read-only`, `bounded-write`, `approval-write`)
- Modell-/Budgetprofil
- Verify-/Approval-Anforderungen

Die Registry ist keine Komfortschicht, sondern der Ort fuer:

- Tool-Allowlisting
- MemoryAccessPolicy
- Risk-Tier-Zuordnung
- Runtime-Defaults

---

## 6. Memory- und Context-Regeln

### 6.1 MemoryAccessPolicy ist Pflicht

Nicht jeder Agent darf jede Memory-Schicht gleich lesen oder schreiben.

Mindestens zu regeln:

- wer `personal_raw` lesen darf
- wer `personal_derived` schreiben darf
- wer `personal_kb` aendern darf
- wer `bridge_world` oder `world_kg` nur lesen darf

### 6.2 Keine direkte Truth-Mutation

Agenten duerfen:

- Claims vorschlagen
- Evidence verknuepfen
- Derived-Kandidaten erzeugen

Agenten duerfen nicht:

- kanonische globale Wahrheit direkt mutieren
- still aus User-Aussagen Weltwissen machen
- unmarkierte Derived-Objekte in den Default-LLM-Kontext einschmuggeln

### 6.3 Retrieval ist Policy-getrieben

Retrieval ist nicht nur Relevance, sondern immer auch:

- Scope
- Sensitivity
- Provenance
- Consumer-/Role-Policy
- Evidence-Gates

Die operative Ausgestaltung liegt in:

- `AGENT_SECURITY.md`
- `CONTEXT_ENGINEERING.md`
- `MEMORY_ARCHITECTURE.md`

---

## 7. Heterogene Modellarchitektur

Modellmischung ist erlaubt, wenn sie explizit nach Rolle begruendet ist.

Beispiele:

- kleineres, guenstiges Modell fuer Router/Classifier
- staerkeres Modell fuer Synthese oder schwierige Verifier-Faelle
- kein Modell darf fehlende Policy- oder Security-Schichten kompensieren sollen

Entscheidungsregel:

- erst Rollen- und Boundary-Klarheit
- dann Modellwahl
- nie andersherum

---

## 8. Verbindung zu Memory, Security und Harness

### Security

`AGENT_SECURITY.md` ist verbindlich fuer:

- Retrieval Broker
- Capability Envelope
- Agentic Storage Write Path
- Evidence-Completeness Gates
- Security-Evals

### Harness

`AGENT_HARNESS.md` ist verbindlich fuer:

- Constrain / Inform / Verify / Correct
- Guardrails als Runtime-Layer
- OpenSandbox-Default
- Observability und Regression-Gates

### Runtime

`AGENT_RUNTIME_ARCHITECTURE.md` ist die kurze Owner-Spec fuer:

- Plan-Execute-Replan Defaults
- Policy Tiers
- Memory-Write-Regeln
- Provenance / Idempotency / Audit

---

## 9. Priorisierte Einfuehrungsreihenfolge

1. Root-Policies und Registry-Grenzen dokumentieren.
2. Retrieval Broker / Tool Proxy / Agentic-Storage-Grenzen verbindlich machen.
3. Context- und Memory-Policies pro Consumer ausrollen.
4. Runtime- und Eval-Gates verdichten.
5. Erst danach komplexere Multi-Agent-Topologien verbreitern.

---

## 10. Querverweise

- `AGENT_SECURITY.md`
- `AGENT_HARNESS.md`
- `AGENT_RUNTIME_ARCHITECTURE.md`
- `AGENT_TOOLS.md`
- `CONTEXT_ENGINEERING.md`
- `MEMORY_ARCHITECTURE.md`
- `RAG_GRAPHRAG_STRATEGY_2026.md`
- `../specs/EXECUTION_PLAN.md`
