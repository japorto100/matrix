# exec-13: Computer Use + Artifacts

**Datum:** 30.03.2026
**Status:** Geplant
**Stand:** 10.04.2026 — Phase 1 (Graphiti/Cognee) nach exec-15 Slice 9 verschoben, Phase 2/3/4 bereits nach exec-15 verschoben
**Abhaengig von:** exec-09 (MCP/Generative UI) ✅, exec-12 Phase 1 (OpenSandbox) ✅
**Referenz-Repos:** `_ref/hindsight`

---

## Kontext

Aus exec-12 verschobene Tool-/UI-Themen:
- **Computer Use:** Playwright MCP, WebMCP, Anthropic Computer Use (Tool-Layer, Phase 5)
- **Artifacts UI:** E2B Fragments / Sandpack / OpenSandbox Artifacts (Phase 6)

> **Playwright MCP** dient doppelt: als MCP Server fuer Claude (AI-Assistent) UND
> als Agent-Tool fuer die Full-Stack-App (Browser-Automation in Sandbox).

> **HINWEIS — Verschoben nach exec-15:**
> - **Phase 2 (Memory Graph Visualisierung)** → exec-15 Phase 3
> - **Phase 3 (Control Panel)** → exec-15 Phasen 1, 2, 4, 6
> - **Phase 4 (Content Ingestion)** → exec-15 Phase 5
>
> Begruendung: Diese Phasen bilden ein eigenstaendiges, groesseres UI-Paket
> ("Memory & Control UI") und nutzen die `D:/matrix/control/` Codex-Extraktion
> als Foundation. Siehe `exec-15-memory-control-ui.md`.

---

## Phase 1: → verschoben nach exec-15 Slice 9

Graphiti/Cognee Backend Integration (GraphRetriever, Cognee, Unified Search API)
verschoben nach `exec-15-memory-control-ui.md` Slice 9 (10.04.2026).
Thematisch passt es besser zu exec-15 (Memory & Control UI) wo die KG-Frontend-Infrastruktur
und Ingestion-Pipeline bereits implementiert sind.

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

### Gate 1: → verschoben nach exec-15 Slice 9

### Gate 5: Computer Use (Phase 5)
- [ ] Playwright MCP Tools registriert und nutzbar
- [ ] Pilot MCP evaluiert (Entscheidung dokumentiert)
- [ ] WebMCP Polyfill in Frontend aktiv

### Gate 6: Artifacts UI (Phase 6)
- [x] Sandpack Browser-Preview im Agent-Chat (SandpackPreview.tsx)
- [x] OpenSandbox Artifacts (Charts, Tables) inline gerendert (SandboxArtifact.tsx)
- [ ] E2B Fragments Evaluation (6.1 — offen)
- [ ] Sandpack: Visual Test im laufenden Agent-Chat (braucht DevStack)
- [ ] SandboxArtifact: E2E Test mit echtem sandbox_execute Output (braucht OpenSandbox)

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
- [x] **6.2:** Sandpack fuer leichtgewichtige Browser-Previews ✅ (10.04.2026)
  - `@codesandbox/sandpack-react` installiert in agent-chat
  - `SandpackPreview.tsx` — Live-Preview mit Code/Preview Toggle
  - Templates: react, react-ts, vanilla, vanilla-ts
  - Files als `Record<string, string>` Props
- [x] **6.3:** OpenSandbox Artifacts inline rendern ✅ (10.04.2026)
  - `SandboxArtifact.tsx` — rendert stdout, stderr, base64 Files (Charts als Bilder, Rest als Downloads)
  - In `ToolOutputRenderer.tsx` registriert fuer `sandbox_execute` + `file_analyze` Tools
  - Execution-Zeit + Sprache als Header
  - Charts (PNG/SVG) als inline `<img>`, andere Files als Download-Links
  - Results als Artifacts im Chat (Charts, Tables, Files)
  - Backend: `SandboxExecuteTool` liefert stdout + files (base64 Charts)

---

## Referenzen

- `_ref/supermemory/packages/memory-graph/` — UI-Referenz fuer Graph Component
- `_ref/graphiti/` — Temporal Knowledge Graph (Zep)
- `_ref/cognee/` — Structured Knowledge Layer
- Hindsight Extension Points: `GraphRetriever(ABC)`, `MemoryEngineInterface(ABC)`
