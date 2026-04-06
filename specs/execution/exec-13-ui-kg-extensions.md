# exec-13: KG Backend Extensions + Computer Use + Artifacts

**Datum:** 30.03.2026
**Status:** Geplant
**Stand:** 06.04.2026 — Phase 2/3/4 nach exec-15 (Memory & Control UI) verschoben
**Abhaengig von:** exec-11 (Hindsight Memory Engine) ✅, exec-09 (MCP/Generative UI) ✅, exec-12 Phase 1 (OpenSandbox) ✅
**Referenz-Repos:** `_ref/hindsight`, `_ref/graphiti`, `_ref/cognee`

---

## Kontext

Aus exec-11 ausgelagerte Backend-Erweiterungen + aus exec-12 verschobene Tool-/UI-Themen:
- **Graphiti/Cognee:** Knowledge Graph Layer als Hindsight Extension (Backend, Phase 1)
- **Computer Use:** Playwright MCP, WebMCP, Anthropic Computer Use (Tool-Layer, Phase 5)
- **Artifacts UI:** E2B Fragments / Sandpack / OpenSandbox Artifacts (Phase 6)

> **HINWEIS — Verschoben nach exec-15:**
> - **Phase 2 (Memory Graph Visualisierung)** → exec-15 Phase 3
> - **Phase 3 (Control Panel)** → exec-15 Phasen 1, 2, 4, 6
> - **Phase 4 (Content Ingestion)** → exec-15 Phase 5
>
> Begruendung: Diese Phasen bilden ein eigenstaendiges, groesseres UI-Paket
> ("Memory & Control UI") und nutzen die `D:/matrix/control/` Codex-Extraktion
> als Foundation. Siehe `exec-15-memory-control-ui.md`.

---

## Phase 1: Graphiti als Custom GraphRetriever

### 1.1 Graphiti Integration
Hindsight bietet `GraphRetriever(ABC)` als Extension Point:
- [ ] `GraphitiRetriever` implementieren (nutzt Graphiti's Temporal Knowledge Graph)
- [ ] Graphiti installieren (`pip install graphiti-core`)
- [ ] Neo4j oder FalkorDB als Graph-Backend evaluieren
- [ ] Temporal Edges: Fakten haben Zeitstempel, alte werden invalidiert
- [ ] Entity Resolution: Graphiti's eigene Entity-Merging-Pipeline

### 1.2 Cognee als Structured Knowledge Layer
- [ ] Cognee installieren (`pip install cognee`)
- [ ] Document → Knowledge Graph Pipeline (PDF, Markdown, Code)
- [ ] Cognee's LLM-basierte Triplet Extraction
- [ ] Integration mit Hindsight: Cognee Facts als `world` Memories retainen

### 1.3 Unified Search API
- [ ] RRF Fusion ueber alle Backends (Hindsight + Graphiti + Cognee)
- [ ] Fallback-Kette: Hindsight (immer) → Graphiti (wenn Neo4j) → Cognee (wenn konfiguriert)
- [ ] Search API Endpoint: `/api/memory/search?q=...&backends=all`

---

## Phase 2 — VERSCHOBEN nach exec-15

Memory Graph Visualisierung → siehe `exec-15-memory-control-ui.md` Phase 3
(Knowledge Graph Visualization).

## Phase 3 — VERSCHOBEN nach exec-15

Control Panel (Agent Config UI, Memory Dashboard, Project Settings) → siehe
`exec-15-memory-control-ui.md` Phasen 1, 2, 4, 6.

## Phase 4 — VERSCHOBEN nach exec-15

Content Ingestion (File Upload Pipeline, Document → Memory, NATS Bridge UI) → siehe
`exec-15-memory-control-ui.md` Phase 5.

---

## Verify-Gates (verbleibend)

### Gate 1: Graphiti/Cognee (Phase 1)
- [ ] GraphitiRetriever registriert und liefert Ergebnisse
- [ ] Cognee Document-Pipeline: PDF → Facts in Hindsight
- [ ] Unified Search: Query liefert Ergebnisse aus allen Backends

### Gate 5: Computer Use (Phase 5)
- [ ] Playwright MCP Tools registriert und nutzbar
- [ ] Pilot MCP evaluiert (Entscheidung dokumentiert)
- [ ] WebMCP Polyfill in Frontend aktiv

### Gate 6: Artifacts UI (Phase 6)
- [ ] Sandpack Browser-Preview im Agent-Chat
- [ ] OpenSandbox Artifacts (Charts, Tables) inline gerendert

---

## Phase 5: Computer Use (verschoben aus exec-12, 01.04.2026)

> **Voraussetzung:** exec-12 Phase 1 (OpenSandbox) ✅ — SandboxBrowserTool + Dockerfile.browser implementiert (03.04.2026)

### 5.1 Playwright MCP (Browser Automation)

- [ ] **5.1.1:** Playwright MCP Server im Agent-Stack
  - 33+ Tools (Navigate, Click, Type, Screenshot, Accessibility Tree)
  - Agent kann Websites bedienen
- [ ] **5.1.2:** Playwright CLI als Alternative (4x weniger Tokens)
  - Fuer wiederholbare Flows (CI/CD, Testing)
  - MCP fuer explorative Tasks
- [x] **5.1.3:** Integration in Sandbox (exec-12 Phase 1) ✅ (03.04.2026)
  - `SandboxBrowserTool` in `agent/tools/sandbox_browser_tool.py`
  - Playwright laeuft innerhalb OpenSandbox Container (`Dockerfile.browser`)
  - Isoliert vom Host-Browser, allowed_domains fuer Egress-Kontrolle

### 5.1b Pilot MCP (Alternative zu @playwright/mcp) — Evaluation

> Siehe `PILOT_MCP_ANALYSIS.md` im Root fuer vollstaendige Analyse.

- [ ] **5.1b.1:** Evaluieren als Alternative/Ergaenzung zu Playwright MCP
  - Repo: https://github.com/TacosyHorchata/Pilot (MIT, npm: `pilot-mcp`)
  - **Kernvorteil:** Agent steuert echten Chrome-Tab (bereits eingeloggt, kein Bot-Fingerprint)
  - **69x weniger Token-Verbrauch** als @playwright/mcp pro Navigation
  - 61 Tools vs 22 bei @playwright/mcp
  - CAPTCHA-Handoff: Agent pausiert → Mensch loest → Agent weiter
  - Broker/Client Multiplexer fuer parallele Agent-Sessions
- [ ] **5.1b.2:** Use-Case-Abgrenzung
  - **Pilot:** Authentifizierte Webseiten, OSINT-Recherche, Cloudflare-geschuetzte Seiten
  - **@playwright/mcp:** CI/CD, headless Testing, Multi-Browser (Firefox/WebKit)
  - **MolmoWeb (4B/8B):** Vollautonome Web-Agents ohne LLM-API-Kosten (GPU noetig)
    - Siehe `MOLMOWEB_ANALYSIS.md` im Root
- [ ] **5.1b.3:** Risikobewertung
  - Projekt ist 8 Tage alt (v0.4.x), ein Hauptentwickler
  - Cookie-Decryption = maechtig aber Security-Surface
  - Kein Windows Cookie-Import (nur macOS/Linux)
  - Nur stdio Transport (kein HTTP/SSE)

### 5.2 WebMCP

- [ ] **5.2.1:** WebMCP Spec beobachten
- [ ] **5.2.2:** Trading-Pages exposen Capabilities via `navigator.modelContext`
  - Chart-State, Portfolio-Daten, Indikator-Werte als Tools
  - Agent ruft sie nativ auf (kein DOM-Scraping)

### 5.3 Anthropic Computer Use (Evaluation)

- [ ] **5.3.1:** Evaluieren fuer Desktop-Agent Use-Cases
  - Claude sieht Screen + klickt (Cloud-side)
  - Aktuell nicht prioritaer

## Phase 6: Artifacts UI (verschoben aus exec-12, 01.04.2026)

> **Voraussetzung:** exec-12 Phase 1 (OpenSandbox) ✅ — SandboxExecuteTool implementiert (03.04.2026)

- [ ] **6.1:** E2B Fragments als UI-Inspiration
  - Artifacts-Style: Agent generiert Code → Preview im Chat
  - Split-View: Code links, Output rechts
- [ ] **6.2:** Sandpack fuer leichtgewichtige Browser-Previews
  - Kein Server noetig, laeuft komplett im Browser
  - React/JS Code-Previews direkt im Chat
- [ ] **6.3:** OpenSandbox fuer schwere Execution ← nutzt `sandbox_execute` Tool
  - Python Data-Analysis, File-Processing, API Calls
  - Results als Artifacts im Chat (Charts, Tables, Files)
  - Backend: `SandboxExecuteTool` liefert stdout + files (base64 Charts)

---

## Referenzen

- `_ref/supermemory/packages/memory-graph/` — UI-Referenz fuer Graph Component
- `_ref/graphiti/` — Temporal Knowledge Graph (Zep)
- `_ref/cognee/` — Structured Knowledge Layer
- Hindsight Extension Points: `GraphRetriever(ABC)`, `MemoryEngineInterface(ABC)`
