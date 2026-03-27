# Dokument-Preview — Evaluation

**Datum:** 26.03.2026
**Status:** Zu evaluieren

---

## Aktueller Stand

| Dateityp | Preview | Library |
|----------|---------|---------|
| PDF | iframe Dialog | Browser-nativ |
| Word (.docx) | HTML-Render Dialog | `docx-preview` |
| Excel (.xlsx/.csv) | Tabellen-Dialog | `xlsx` (SheetJS) |
| PowerPoint (.pptx) | HTML/CSS/SVG Render | `pptxjs` / `react-pptx-preview` (einzurichten) |
| Andere | Download-Link | — |

---

## PowerPoint Preview

### Aktuell: pptxjs / react-pptx-preview (Client-seitig)
- Parse .pptx (ZIP/XML) → HTML/CSS/SVG im Browser
- Offline-fähig, keine Daten verlassen den Client
- ~80% originalgetreu (komplexe Animationen/3D-Effekte können abweichen)
- **Status:** Einzurichten

### Zu evaluieren: Backend PDF-Konvertierung
- **Gotenberg** (Docker-Container) oder **LibreOffice** als Konvertierungs-Backend
- Go-Backend ruft Gotenberg auf → .pptx → PDF → an Client → `react-pdf` zeigt an
- ~95% originalgetreu
- Braucht zusätzlichen Service (Docker)
- **Vorteil:** Funktioniert für ALLE Office-Formate (Word, Excel, PPT) mit einem Ansatz
- **Nachteil:** Nicht offline, zusätzliche Infrastruktur
- **Relevanz:** Erst bei Prod-Deployment evaluieren

### Entscheidungsmatrix

| Kriterium | pptxjs (Client) | Gotenberg (Backend) |
|-----------|----------------|-------------------|
| Qualität | 80% | 95% |
| Offline | Ja | Nein |
| Infrastruktur | Keine | Docker-Container |
| Alle Formate | Nur PPT | Word, Excel, PPT, alles |
| Aufwand | Niedrig | Mittel (Go-Integration) |
| Latenz | Sofort | ~1-3s Konvertierung |

### Empfehlung
- **Dev/MVP:** pptxjs client-seitig (aktueller Ansatz)
- **Prod:** Gotenberg evaluieren — ein Backend-Service für alle Office-Formate
  - Würde `docx-preview` und `xlsx` Viewer ersetzen können
  - Einheitliche Qualität für alle Dokumenttypen
  - Go-Backend Route: `POST /api/convert` → Gotenberg → PDF → Response
