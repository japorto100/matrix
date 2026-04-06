# Dokument-Preview — Evaluation

**Status:** Aktiv (Client-seitig umgesetzt, Backend-Konvertierung in `FUTURE_IDEAS.md`)
**Stand:** 06.04.2026

---

## Aktueller Stand (Ist)

| Dateityp | Preview | Library | Status |
|----------|---------|---------|---|
| PDF | iframe / `react-pdf` | `react-pdf` 10.4 | ✅ in nextjs-chat |
| Word (.docx) | HTML-Render Dialog | `docx-preview` 0.3.7 | ✅ in nextjs-chat |
| Excel (.xlsx/.csv) | Tabellen-Dialog / Export | `xlsx` (SheetJS) | ✅ in nextjs-chat |
| Markdown / Text | inline | `react-markdown` + `rehype-sanitize` | ✅ |
| Code | Syntax Highlighting | `react-shiki` (VS Code Engine) | ✅ |
| PowerPoint (.pptx) | — | `pptxjs` / `react-pptx-preview` | ❌ siehe FUTURE_IDEAS |
| Andere | Download-Link | — | ✅ Fallback |

---

## Backend-Konvertierung (Optional, FUTURE_IDEAS)

Statt Client-seitiger Parsing-Libraries koennte ein Backend-Service wie **Gotenberg**
(Docker, LibreOffice basiert) alle Office-Formate auf PDF konvertieren und der Browser
nutzt nur einen einzigen `react-pdf` Viewer. Vor- und Nachteile:

| Kriterium | Client (aktuell) | Backend (Gotenberg) |
|-----------|----------------|-------------------|
| Qualitaet | ~80% | ~95% |
| Offline | Ja | Nein |
| Infrastruktur | Keine | Docker-Container |
| Alle Formate | Pro Format eine Library | Eine Pipeline fuer alles |
| Aufwand | Niedrig | Mittel (Go-Integration) |
| Latenz | Sofort | ~1-3s Konvertierung |

**Status:** Verschoben nach `FUTURE_IDEAS.md` — sinnvoll erst bei Prod-Deployment.
PowerPoint Preview hat aktuell keine Prioritaet, da der Use-Case (Trading-Dokumente)
ueberwiegend PDF + Excel ist.

---

## Verwandte Specs

- `04-nextjs-chat.md` — Document Preview Komponenten
- `FUTURE_IDEAS.md` — Backend-Konvertierung via Gotenberg
