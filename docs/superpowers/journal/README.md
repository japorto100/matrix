# Session Journal

Tägliches Arbeitsprotokoll. Eine Datei pro Tag (`YYYY-MM-DD.md`) mit:

- **Tasks** — welche open-task IDs oder spec-§ bearbeitet wurden
- **Commits** — Hashes + Kurzbeschreibung, chronologisch
- **Was + Warum** — was gebaut wurde und welches Problem es löst
- **Ref-Projekt-Bezug** — wenn Code aus `_ref/*` portiert/adaptiert: welches Projekt + welche Datei
- **Offene Punkte** — was am Ende der Session blieb, für Handoff
- **Lessons / Surprises** — was überraschend war, Fallen, Entscheidungen mit Begründung

Unterschied zu anderen Doc-Typen:

| Doc | Zweck |
|---|---|
| `journal/` (hier) | Chronologisch: was wann gemacht wurde, als Handoff-Kontext |
| `findings/` | Punktuelle Findings aus Reviews / Audits (ADRs, Contrarian-Outputs, Open-Task-Listen) |
| `plans/` | Multi-step Implementation-Pläne (vor dem Coden geschrieben) |
| `specs/` | Executable specs für Subagents (execution/exec-*.md) |

Das Journal ist **kein** Ersatz für:
- commit messages (die beschreiben WAS der Code tut)
- ADRs (die beschreiben WARUM entschieden wurde)
- specs (die beschreiben das Ziel-Verhalten)

Es ist der **Trail** — was in der Session passiert ist, in welcher Reihenfolge, mit welcher Motivation, und wohin man als nächstes schauen sollte.
