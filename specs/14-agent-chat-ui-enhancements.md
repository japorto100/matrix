# Agent Chat UI — Mögliche Erweiterungen

**Datum:** 26.03.2026
**Status:** Ideen / Noch nicht geplant
**Kontext:** Für das Hauptprojekt (tradeview-fusion) Agent Chat UI, nicht für das Matrix-Isolationsprojekt.

---

## Code-Rendering im Agent Chat

### Syntax Highlighting
- `shiki` oder `prism-react-renderer` für statisches Code-Highlighting
- `react-markdown` + `rehype-highlight` bereits im Matrix-Chat vorhanden — kann 1:1 übernommen werden

### Interaktive Code-Blöcke
- **`sandpack`** (CodeSandbox): Interaktive Code-Ausführung direkt im Chat
  - Agent liefert Code → User kann ihn editieren und ausführen
  - Unterstützt React, Vue, Vanilla JS, TypeScript
  - Sandboxed Execution (sicher)

### Markdown-Rendering
- `react-markdown` + `remark-gfm` (GitHub Flavored Markdown) bereits vorhanden
- Tabellen, Checklisten, Footnotes funktionieren

---

## Agent-generierte Dateien

### PowerPoint-Generierung
- **`pptxgenjs`** — Agent kann PowerPoint-Präsentationen generieren
  - Use Case: "Erstelle eine Zusammenfassung als Präsentation"
  - Agent generiert .pptx → sendet als `m.file` im Chat
  - User kann herunterladen und in PowerPoint/Google Slides öffnen

### Excel-Generierung
- **`xlsx` (SheetJS)** — bereits installiert, kann auch zum Erstellen genutzt werden
  - Use Case: "Exportiere die Handelsdaten als Excel"
  - Agent generiert .xlsx → sendet als `m.file`

### PDF-Generierung
- Diverse Libraries (jsPDF, @react-pdf/renderer)
  - Use Case: "Erstelle einen Report als PDF"

---

## Presentation-Mode (Spectacle)

- **`spectacle`** (Formidable Labs) — React Presentation Library
  - Slide-artige Agent-Antworten mit Animationen
  - Use Case: Agent liefert mehrseitige Analyse als navigierbare Slides
  - Overkill für normalen Chat — nur sinnvoll für spezifische Agent-Antwortformate
  - Alternative: Einfache Tabs/Accordion für mehrteilige Antworten

---

## Priorität

| Feature | Nutzen | Aufwand | Empfehlung |
|---------|--------|---------|-----------|
| Syntax Highlighting | Hoch | Niedrig (haben wir schon) | Bei Portierung mitnehmen |
| Sandpack (interaktiv) | Mittel | Mittel | Nice-to-have |
| PptxGenJS | Mittel | Niedrig | Agent-Capability |
| Excel-Export | Hoch | Niedrig (SheetJS da) | Agent-Capability |
| Spectacle | Niedrig | Hoch | Nicht empfohlen |
