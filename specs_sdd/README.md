---
title: Matrix Specs SDD Index
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-26
supersedes: []
---

# Matrix Specs SDD

`specs_sdd/` ist die neue Spec-Driven-Development-Struktur fuer dieses Repo.
Sie soll den kompletten alten Stand aus `specs/`, `docs/superpowers/`,
`main_docs/` und relevanten `docs/papers/` uebersetzen, nicht nur neue Arbeit
aufnehmen.

## Authoritative Status

Bis die Migration abgeschlossen ist:

- `specs/`, `docs/superpowers/`, `main_docs/` und `docs/papers/` bleiben
  Legacy-/Reference-Quellen.
- `specs_sdd/` ist die neue kanonische Sicht im Aufbau.
- Neue Planung soll nur noch in `specs_sdd/` entstehen.
- Alte Dateien werden nicht geloescht und nicht umbenannt, bis jede Quelle in
  `MIGRATION_MAP.md` zugeordnet ist.

## Struktur

```text
specs_sdd/
  README.md
  constitution.md
  FEATURE_DETERMINATION.md
  MIGRATION_MAP.md
  DECISION_BACKLOG.md
  features/
    NNN-feature-name/
      spec.md
      plan.md
      tasks.md
      research.md
      live-verify.md
      closeout.md
      evidence/
  adr/
  research/
  journal/
  archive/
  templates/
```

## Lese-Reihenfolge

1. `constitution.md` fuer nicht verhandelbare Projektregeln.
2. `SOURCES.md` fuer Provenance-Regeln: welche Legacy-Dateien, Paper, ADRs,
   Produktdocs und Research-Notizen in SDD weitergetragen werden muessen.
3. `FEATURE_DETERMINATION.md` fuer finale Feature-Anzahl, Subfeatures und
   Superseded-/Already-built-Einschaetzung.
4. `MIGRATION_MAP.md` fuer Legacy-Quelle -> Feature-Ziel.
5. `MAIN_DOCS_COVERAGE.md` fuer Root-/Main-Doc- und Paper-Zuordnung.
6. `LEGACY_COVERAGE.md` fuer Vollstaendigkeitsabgleich gegen alte Dateien.
7. `SEMANTIC_AUDIT.md` fuer den Abgleich, ob `specs_sdd` die alten Inhalte
   bereits wirklich ersetzt.
8. `DECISION_BACKLOG.md` fuer noch nicht akzeptierte Entscheidungen und
   bewusst deferred Fragen.
9. `STATUS_BOARD.md` fuer aktuellen Gate-/Closeout-Status.
10. `features/*/spec.md` fuer Current State, Target State und Scope.
11. `features/*/sources.md` oder `research.md` fuer Feature-spezifische Quellen,
   Paper und externe Kontextbasis.
12. `features/*/tasks.md` fuer konkrete Arbeit.
13. `features/*/live-verify.md` und `closeout.md` fuer Abschlussstatus.

## Status-Modell

| Status | Bedeutung |
|---|---|
| `draft` | noch nicht bindend |
| `review` | fachlich fertig, wartet auf Freigabe |
| `accepted` | bindend; Aenderung nur ueber ADR oder explizite Spec-Revision |
| `implementation_done` | Code/Config gebaut, aber Verify oder Live-Verify offen |
| `baseline` | stabile Grundlage, kein normaler Implementation-Slice |
| `closed_static` | Dokument-/Static-Scope geschlossen; keine Runtime-Live-Verify erforderlich |
| `static_closed_live_pending` | Static-/Buildless-Scope geschlossen; Runtime-/Operator-Live-Verify offen |
| `static_classified_live_pending` | Legacy gates/owners/status sind statisch geklaert; Live-Verify bleibt offen |
| `mostly_built` | grosser Teil gebaut, bekannte Rest-Gaps |
| `frontend_built` | UI steht, Backend-/Live-Integration ist gemischt |
| `in_progress` | aktive Arbeit oder aktive Gates |
| `mixed_active` | mehrere Subfeatures mit unterschiedlichem Reifegrad |
| `decision_pending` | naechster Schritt haengt an ADR/Architekturentscheidung |
| `active_monitoring` | laufende Beobachtung externer/operativer Blocker |
| `verified` | automatisierte Gates gruen |
| `live_verified` | echter End-to-End-/Browser-/CLI-Flow belegt |
| `closed` | `closeout.md` vorhanden, Abweichungen dokumentiert |
| `superseded` | ersetzt, bleibt als Historie lesbar |

## Ist/Soll-Konvention

Jedes Feature trennt sichtbar:

- **Current State / Ist:** was heute existiert, mit Legacy-Quellen.
- **Target State / Soll:** was gelten soll, sobald das Feature fertig ist.
- **Gap:** Differenz zwischen Ist und Soll.
- **Tasks:** konkrete Schritte, um die Gap zu schliessen.
- **Verify:** automatisierte Gates.
- **Live-Verify:** echte Laufzeitpruefung mit Evidence.
- **Closeout:** was tatsaechlich gebaut wurde und was abweicht.

Damit ist Vergangenheit nicht verloren: alter Ist-Stand wird importiert und mit
Provenance versehen, statt nur als Archiv weggeschoben zu werden.

## Journal vs Tasks

Das Journal ersetzt keine Execution-Tasks.

- `tasks.md` ist die Source of Truth fuer Arbeit, Dependencies und Done-Status.
- `journal/` ist ein chronologisches Session-/Bootstrap-Log: was wurde wann
  entdeckt, entschieden, verifiziert oder verschoben.
- Journal-Eintraege muessen auf Feature-Tasks, ADRs oder Research verlinken,
  sobald daraus bindende Arbeit entsteht.

## Checkbox Policy

Unchecked Markdown boxes are reserved for real work queue items:

- active implementation tasks in `tasks.md`,
- true acceptance/verify gates in `gates.md`.

Do not use unchecked boxes for explanatory acceptance prose, live-verify
procedure steps, historical requirements, template placeholders or duplicated
substeps. Those stay as plain bullets. This keeps status counts meaningful and
prevents old execution logs from turning into hundreds of fake tasks.

Decision/defer questions live in `DECISION_BACKLOG.md` until accepted or
explicitly retired. They should not remain as unchecked `tasks.md` items.

## Quellen-Konvention

SDD darf alte Quellen verdichten, aber nicht entkernen. Wenn eine alte Exec-Datei,
ein `main_docs`-Root-Dokument oder ein Paper ein externes Repo, Produktdoc, ADR
oder Superpower-Finding als Begruendung nutzt, muss die neue Feature-Spec diese
Provenance behalten:

- lokale Legacy-Quelle in `migrated_from`;
- paper-/repo-/produktbezogene Entscheidung in `sources.md` oder `research.md`;
- uebernommene Idee als explizite "Adopted into matrix" Notiz;
- offene Research-Frage als Task oder Research-Backlog, nicht als loses TODO.

## Finales Feature-Modell

`specs_sdd` verwendet aktuell 15 Top-Level-Features. Erledigte und
baseline-nahe Themen stehen vorne, aktive/gemischte Themen hinten.
Schema-Historie, Research-Backlog und Journal sind bewusst keine normalen
Feature-IDs.

Wichtig: 15 ist die Capability-Landkarte, nicht die Garantie, dass keine
Subfeatures spaeter zu eigenen Features werden. `SEMANTIC_AUDIT.md` entscheidet
pro Feature, ob die alte Detailtiefe schon importiert ist.

Die aktuelle Liste steht in `features/README.md`.
