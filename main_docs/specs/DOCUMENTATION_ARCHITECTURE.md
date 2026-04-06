# DOCUMENTATION ARCHITECTURE

> **Stand:** 16. Maerz 2026
> **Zweck:** Formale Regel fuer Ebenen, Read Order, Ownership, Split-Regeln,
> Update-Pflichten und Einbezug von Root-/Book-Docs. Dieses Dokument ist die
> normative Authority fuer die Dokumentationsstruktur.
> **Referenz:** [`SPEC_CONVENTIONS.md`](./SPEC_CONVENTIONS.md) fuer Template- und
> Lifecycle-Regeln einzelner Specs.

---

## 1. Ebenen

| Ebene | Ort | Rolle |
|:------|:----|:------|
| **Core Specs** | `docs/specs/*.md` | Normative projektische Wahrheit, Umbrella- und Navigationsdocs pro Thema |
| **Architecture Subspecs** | `docs/specs/architecture/*.md` | Granulare Architektur-Owner-Docs (Baseline, Gateway, Agent, Memory, Orchestrierung, Domain Contracts) |
| **Data Subspecs** | `docs/specs/data/*.md` | Granulare Data-Owner-Docs (Datenfluss, Aggregation, Storage, UIL, Source-Status) |
| **Governance Blueprints** | `docs/specs/governance/*.md` | Future-facing Zielbild-Specs (Rollout-Gates, Plugin-Pilot, Partner-Boundary, Payment-Adapter) |
| **Execution Specs** | `docs/specs/execution/*.md` | Operative Mid-Level-Arbeitsdokumente: Checklisten, Verify Gates, laufende Abarbeitung |
| **Domain Reference Docs** | `docs/*.md` (Root) | Tiefer Fachkontext; ergaenzen Specs, ersetzen sie nicht |
| **Deep Reference** | `docs/books/`, `docs/archive/`, Research-MDs | Nur bei Bedarf; nicht als first-read Quelle |

---

## 2. Read Order fuer Agenten

1. **AGENTS.md** (oder model-spezifisch: CLAUDE.md, GEMINI.md, CODEX.md) — Einstieg, Verweis auf Specs
2. **EXECUTION_PLAN.md** — Highest-Level Working Plan, Phasenstatus, offene Gates
3. **SYSTEM_STATE.md** — kompakter Runtime-IST/SOLL-Snapshot
4. **Spec fuer den Arbeitsbereich** - z.B. API_CONTRACTS, AUTH_SECURITY, `architecture/FRONTEND_ARCHITECTURE` + `architecture/FRONTEND_QUALITY_RULES`, data/DATA_ARCHITECTURE
5. **Execution-Spec bei Bedarf** — z.B. `execution/geomap_closeout.md` fuer GeoMap-Arbeit oder `execution/source_onboarding_and_keys.md` fuer neue Quellen/Keys
6. **Root-Domain-Docs bei Bedarf** — z.B. Deep-Reference zu Geo-Themen; normative Geo-Owner liegen in `docs/geo/*.md`
7. **Books/Research nur bei explizitem Bedarf** — nicht als Standard-Lesepfad

---

## 3. Ownership-Regeln

| Frage | Owner |
|:------|:------|
| Welche Arbeit ist offen? | `EXECUTION_PLAN.md` |
| Welche Verify-Gates gelten? | `EXECUTION_PLAN.md` + `execution/*.md` |
| IST/SOLL pro Schicht? | `SYSTEM_STATE.md` |
| API-/Transport-Contracts? | `docs/specs/api/*.md` |
| Auth / Policy / Secrets? | `docs/specs/security/*.md` |
| Frontend-Regeln? | `docs/specs/architecture/FRONTEND_ARCHITECTURE.md` + `docs/specs/architecture/FRONTEND_QUALITY_RULES.md` |
| Architektur-Leitplanken? | `ARCHITECTURE.md` + `docs/specs/architecture/*.md` |
| Daten-/Aggregationsregeln? | `docs/specs/data/DATA_ARCHITECTURE.md` |
| Tiefer Domain-Kontext? | Root-Docs (Deep-Reference) + `docs/geo/*.md` als normative Geo-Owner |

---

## 4. Single Source of Truth

- **Eine Wahrheit pro Thema.** Kein Duplikat zwischen Specs und Agent-Files.
- **AGENTS.md / CLAUDE.md** verweisen auf Specs; sie duplizieren keine Fachtruth.
- **Root-Docs** duplizieren keine Spezifikationen; sie ergaenzen sie fachlich.
- **Historische Fortschritte** gehoeren ins Archiv, nicht in aktive Master-Specs.

---

## 5. Execution-Ebene

- **EXECUTION_PLAN.md** ist der Highest-Level Working Plan.
- **docs/specs/execution/*.md** sind operative Mid-Level-Arbeitsdokumente:
  - Checklisten
  - Verify Gates
  - Offene Punkte pro Domain oder Cross-Cutting
- Execution-Specs leiten sich aus dem EXECUTION_PLAN ab und verweisen auf ihn.
- Domain-spezifische Execution-Specs (z.B. `geomap_closeout.md`, `source_onboarding_and_keys.md`) koennen bei Bedarf angelegt werden.

---

## 6. Root-Docs und Deep Reference

- **Root-Docs** liefern Domain Context und duerfen Specs ergaenzen, nicht ersetzen.
- **Books / Research-MDs** nur bei Bedarf; nicht als first-read Quelle.
- Root-Docs werden in `docs/README.md` nach Rolle klassifiziert (active, reference, bridge, archived).

---

## 7. Split-Regeln

- **Dateien >3.500 Tokens** oder mit mehreren klar getrennten Verantwortlichkeiten werden gesplittet.
- **Boundary-Specs** (API, Security, Architecture, Errors) werden nach Grenzen aufgeteilt:
  - API: Browser→Next, Next→Go, Internal Services, Shared Invariants, UIL Routes
  - Security: Auth Model, Policy Guardrails, Secrets Boundary, ggf. Incident Response
  - Errors: Error Taxonomy + Resilience (`ERRORS.md`) vs. Telemetrie/Logging (`OBSERVABILITY.md`)
- **Sub-Specs** leben in eigenen Ordnern: `docs/specs/api/`, `docs/specs/security/`, `docs/specs/architecture/`, `docs/specs/data/`, `docs/specs/governance/`, `docs/specs/execution/`.

---

## 8. Update-Pflichten

- Specs muessen **laufend aktuell gehalten** werden.
- Bei Code-, Port-, Boundary-, Auth- oder Ownership-Aenderungen: fuehrende Spec aktualisieren.
- Bei Spec-Aenderungen: `Stand`-Datum und ggf. Aenderungshistorie pflegen.
- Querverweise in `docs/README.md`, `EXECUTION_PLAN.md` und betroffenen Specs synchron halten.

---

## 9. Querverweise

| Dokument | Rolle |
|:---------|:------|
| `docs/README.md` | Einstieg, Rollenklassifikation Root-Docs |
| `SPEC_CONVENTIONS.md` | Template, Lifecycle, Naming fuer neue Specs |
| `docs/archive/Master_master_diff_merge_matrix.md` | Archivierte Verteil-/Konsolidierungsmatrix (historische Herleitung) |
| `AGENTS.md` | Agent-Einstieg; verweist auf Specs, dupliziert keine Fachtruth |

---

## 10. Striktes Archivkriterium fuer Bridge-/Master-Docs

Ein Root-Bridge-/Master-Dokument darf erst archiviert werden, wenn alle Punkte
gleichzeitig erfuellt sind:

1. **Normative Regeln transferiert:** Verbindliche Prinzipien und Vertraege sind in
   aktive Owner-Specs uebertragen (`ARCHITECTURE`, `API_CONTRACTS`,
   `AUTH_SECURITY`, `EXECUTION_PLAN`, fachlich passende Root-Docs).
2. **Kontext nicht nur referenziert:** Kerninhalt ist als verwertbare Regel,
   Matrix oder Entscheidungslogik in Ziel-Docs vorhanden, nicht nur als Link.
3. **Owner klar:** Fuer jeden uebertragenen Themenblock gibt es genau einen aktiven
   Owner.
4. **Read Order aktualisiert:** `docs/README.md` und `EXECUTION_PLAN.md`
   klassifizieren das Dokument als `archived`.
5. **Archivheader gesetzt:** Die archivierte Datei enthaelt klaren Header mit
   Archivdatum und "Inhalt verteilt in".

Minimaler Audit-Eintrag vor Archivierung:

- Quelle (Datei)
- Ziel-Dokument(e)
- transferierte Themenbloecke
- verbleibender Rest (falls bewusst historisch)

