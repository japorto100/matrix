# FUTURE_IDEAS — Noch nicht umgesetzte Ideen

**Datum:** 06.04.2026
**Zweck:** Sammelbecken für Ideen, Vorschlaege und Konzepte aus den Spec-Files,
die nicht den Ist-Zustand abbilden, aber spaeter relevant werden koennten.
Quellen werden pro Eintrag vermerkt.

> **Hinweis:** Konkrete operative Plaene gehoeren in `specs/execution/exec-*.md`.
> Diese Datei ist fuer Brainstorming, Optionen und nicht-eingeplante Features.

---

## Inhaltsverzeichnis

- [Frontend / UI](#frontend--ui)
- [Backend / Agent](#backend--agent)
- [Matrix / Protokoll](#matrix--protokoll)
- [Mobile](#mobile)
- [Privacy / Security](#privacy--security)
- [Infrastruktur / Deployment](#infrastruktur--deployment)
- [Entwickler-Tools](#entwickler-tools)

---

## Frontend / UI

### Agent Chat — Interaktive Code-Blocks (Sandpack)
**Aus:** `14-agent-chat-ui-enhancements.md` (vorher Ideen-Liste)
**Was:** `sandpack` (CodeSandbox) im Agent-Chat einbauen — Agent liefert Code, User kann
ihn editieren und ausfuehren. Unterstuetzt React, Vue, Vanilla JS, TypeScript. Sandboxed.
**Warum verschoben:** Bestehender Sandbox-Stack (OpenSandbox in `agent/sandbox/`) deckt
serverseitige Code-Execution ab. Sandpack waere clientseitig fuer interaktive Code-Demos.
Nice-to-have, kein bloecker.

### Agent Chat — Datei-Generierung (PPTX, PDF, Excel)
**Aus:** `14-agent-chat-ui-enhancements.md`
**Was:**
- `pptxgenjs` — Agent generiert PowerPoint-Praesentationen
- `@react-pdf/renderer` oder `jsPDF` — PDF-Reports
- `xlsx` (SheetJS) — Excel-Export (Library bereits in nextjs-chat installiert)
**Warum verschoben:** Macht erst Sinn wenn Agent regelmaessig strukturierte Reports
liefert. Aktuell deckt Markdown + Code-Highlighting den Bedarf.

### Document Preview — Backend-Konvertierung (Gotenberg)
**Aus:** `15-document-preview-evaluation.md`
**Was:** Statt Client-seitiger Parsing-Libraries (`docx-preview`, `xlsx`) koennte ein
Backend-Service wie **Gotenberg** (Docker, LibreOffice basiert) alle Office-Formate auf
PDF konvertieren. Browser braucht dann nur einen `react-pdf` Viewer fuer alles.
**Warum verschoben:** Aktuelle Client-Libraries reichen aus (~80% Qualitaet). Backend-
Konvertierung waere ~95%, braucht aber Docker-Service und ist nicht offline. Erst bei
Prod-Deployment relevant. Insbesondere PowerPoint Preview hat aktuell keine Prioritaet.

### PowerPoint (.pptx) Client Preview
**Aus:** `15-document-preview-evaluation.md`
**Was:** `pptxjs` / `react-pptx-preview` einbauen — parse .pptx (ZIP/XML) → HTML/CSS/SVG
im Browser. Offline-faehig.
**Warum verschoben:** Use-Case (Trading-Dokumente) ist ueberwiegend PDF + Excel,
PPT spielt kaum eine Rolle.

### Agent Chat — Spectacle Presentation Mode
**Aus:** `14-agent-chat-ui-enhancements.md`
**Was:** `spectacle` Library fuer slide-artige Agent-Antworten mit Animationen.
**Warum verschoben:** Niedrige Prioritaet, hoher Aufwand. Tabs/Accordion sind einfacher
und decken den Use-Case ab.

### Next.js: Authenticated Media (MSC3916) Migration
**Aus:** `04-nextjs-chat.md`, `06-e2ee.md`
**Was:** Aktuell wird via `allow_legacy_media = true` in `tuwunel.toml` das alte
unauthenticated Media-Schema unterstuetzt. Production sollte auf MSC3916 umgestellt
werden — Media-Requests mit `Authorization: Bearer <access_token>` und neuem URL-Schema
`/_matrix/client/v1/media/download/`.
**Warum verschoben:** Workaround funktioniert, kein Zwang in Dev. Erfordert Anpassung
von `mxcToHttp()` und allen Komponenten die Media laden.

---

## Backend / Agent

### Remote A2A Agents (exec-10 Phase 4)
**Aus:** Codebase-Erkundung — `agent/graph/nodes/a2a_node.py` Scaffold vorhanden
**Was:** Inter-Agent Delegation an *externe* Agents (HTTP+JSON), nicht nur lokale
Trading-Rollen. Scaffold ist da, aber nicht getestet/aktiviert.
**Warum verschoben:** Lokale Trading-Rollen reichen aktuell. Externe A2A wird interessant
wenn andere Teams ihre Agents anbieten.

### Agent Loop Stop/Resume Policy
**Aus:** `agent-ui/02-features.md`
**Was:** Interruption-Semantik bei laufenden Tool-Chains. User soll laufende
Agent-Iteration stoppen und spaeter fortsetzen koennen (statt komplett neu zu starten).
**Warum verschoben:** Braucht Backend-Design — Tool-State persistieren, Interrupt-Token
weitergeben, Recovery-Pfad definieren. Aktueller Stop-Button bricht hart ab.

### Agent Loop Pause/Resume
**Aus:** `agent-ui/02-features.md`
**Was:** Agent-Loop pausieren ohne abzubrechen, spaeter fortsetzen. Z.B. Tool-Approval
braucht 5 Min User-Reaktion, Loop sollte solange "schlafen" statt timeouten.
**Warum verschoben:** Braucht Architektur-Eval — wie verhaelt sich das mit
LangGraph Checkpointing, Rate Limiter, Audit Logging? Konzeptionelle Frage.

### Memory Service Standalone (Port 8093)
**Aus:** Codebase-Erkundung — `memory_engine/` Package + `memory/app.py` Scaffold
**Was:** Hindsight Memory Engine als eigenstaendiger HTTP-Service auf Port 8093
herausziehen, statt im Agent-Prozess zu leben. Vorteil: mehrere Agents/Bridges koennen
auf eine Memory-Instanz zugreifen.
**Warum verschoben:** Aktuell laeuft Hindsight in-process im Agent. Standalone macht erst
Sinn wenn Multi-Process Setup oder Cross-Service Memory benoetigt wird.

### RL Trainer aktivieren (`AGENT_RL_ENABLED=true`)
**Aus:** Codebase-Erkundung — `agent/skills/rl_trainer.py` Infrastructure vorhanden
**Was:** Process Reward Model (LLM-as-Judge) + LoRA Fine-Tuning fuer personalisierte
Skills. Trajectories werden in `.trajectories/training/` gesammelt.
**Warum verschoben:** Default `AGENT_RL_ENABLED=false`. Braucht trainierten PRM und
genug Trajectory-Daten. Sinnvoll erst nach Produktivnutzung mit echten Usern.

---

## Matrix / Protokoll

### E2EE Production Hardening
**Aus:** `06-e2ee.md` (Phase 4 Items)
**Was:**
1. **D-1:** `globalBlacklistUnverifiedDevices = true` im Browser setzen, sobald alle
   Geraete verifiziert sind.
2. **C-8:** Megolm Key Backup implementieren — neue Geraete koennen aktuell keine
   alten verschluesselten Nachrichten lesen.
3. **PQXDH (Post-Quantum):** vodozemac im Go Appservice nutzen (CGO-Build), goolm hat
   noch kein PQXDH. Erst bei Portierung auf Production Linux relevant.
**Warum verschoben:** Dev-Setup laeuft mit relaxten Security-Defaults. Production
Hardening kommt im Portierungs-Slice.

---

## Mobile

<!-- Mobile-spezifische Ideen. -->

---

## Privacy / Security

<!-- Privacy/Security Optionen die nicht aktiv sind. -->

---

## Infrastruktur / Deployment

<!-- Production/Deployment Optionen die noch evaluiert werden. -->

---

## Entwickler-Tools

<!-- Tooling Ideen die nicht in 08-tooling.md stehen. -->

---

## Verworfene Ideen

<!-- Ideen die wir aktiv verworfen haben, mit Begruendung — dient als Lessons Learned. -->
