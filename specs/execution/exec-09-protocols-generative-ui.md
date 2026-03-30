# exec-09: Protokolle + Generative UI + Infinite Canvas + MCP Browser Tools

**Datum:** 30.03.2026
**Status:** Geplant
**Abhaengig von:** exec-08 (Agent Backend + Voice)
**Spec:** `specs/agent-ui/06-protocols-roadmap.md`

---

## Phase 1: MCP Browser Tools

- [ ] **1.1:** `use-mcp` React Hook installieren (`npm i use-mcp`)
- [ ] **1.2:** Agent Chat Composer/Panel mit `useMcp()` Hook verbinden
  - Ersetzt manuelle `fetch("/api/agent/tools/...")` Calls
  - Standardisierte Tool-Discovery + Calling
- [ ] **1.3:** MCP Apps Support evaluieren
  - `@modelcontextprotocol/ext-apps` installieren
  - Sandboxed iframe Rendering fuer Agent-generierte UI-Surfaces
  - Ergaenzt Tambo (eigene Components) mit externen MCP App Surfaces

## Phase 2: Generative UI Frameworks

- [ ] **2.1:** Tambo evaluieren + einbauen
  - `useTamboTool()` — eigene domain-spezifische Components registrieren
  - Chart-Widgets, Portfolio-Karten, Trade-Formulare als Agent-Tools
  - MCP Server Integration
- [ ] **2.2:** CopilotKit AG-UI Protocol evaluieren
  - `useFrontendTool()` — Agent steuert Frontend-State
  - Ersetzt unsere primitive `frontend-tools.ts`
  - Bidirektionaler State zwischen Agent und UI
- [ ] **2.3:** A2UI (Google) evaluieren
  - Agent emittiert JSON → Frontend rendert native Components
  - Via CopilotKit nutzbar
- [ ] **2.4:** Entscheidung: Tambo fuer eigene + CopilotKit fuer dynamische Components
  - Parallel nutzbar — Tambo als Component-Registry, CopilotKit als Protocol-Layer

## Phase 3: Infinite Canvas (tldraw)

- [ ] **3.1:** `@tldraw/tldraw` installieren im Agent Chat
- [ ] **3.2:** Split-View: Chat links, Canvas rechts (oder umschaltbar)
- [ ] **3.3:** Agent kann Shapes/Text/Widgets auf Canvas platzieren
- [ ] **3.4:** Novel Editor als Text-Block innerhalb der Canvas
- [ ] **3.5:** User kann Canvas-Inhalte arrangieren, verbinden, annotieren

## Phase 4: WebMCP (Zukunft)

- [ ] **4.1:** WebMCP Spec beobachten (W3C Draft, Chrome Canary)
- [ ] **4.2:** `@mcp-b/react-webmcp` evaluieren wenn Browser-Support breiter wird
- [ ] **4.3:** Trading-Pages koennen ihre Capabilities via `navigator.modelContext` exposen

---

## Verify-Gates

- [ ] `use-mcp` Hook: Agent ruft Tools via MCP Standard auf (nicht manuelles fetch)
- [ ] MCP App: Agent-generierte UI-Surface rendert in sandboxed iframe
- [ ] Tambo: Eigener Chart-Widget rendert im Chat via Agent-Tool-Call
- [ ] CopilotKit: Agent steuert Frontend-State via AG-UI Protocol
- [ ] tldraw Canvas: Agent platziert Widget auf Infinite Canvas, User kann verschieben
- [ ] Novel Block innerhalb tldraw Canvas editierbar
