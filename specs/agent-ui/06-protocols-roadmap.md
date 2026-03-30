# Agent Chat UI — Protokolle, Frameworks & SOTA Roadmap

> Stand: 30.03.2026
> Scope: Agent Chat UI + Backend im Matrix-Isolationsprojekt (Trading-App Use-Case)

---

## 1. Protokoll-Landschaft

Sechs Protokolle die verschiedene Layer der Agent-Kommunikation abdecken.
Sie sind komplementaer — ein produktives System nutzt mehrere gleichzeitig.

### 1.1 MCP (Model Context Protocol) — Anthropic

**Layer:** Agent → Tools
**Status:** 97M Downloads, de-facto Standard fuer Tool-Integration.

- Agent ruft strukturierte Tools auf (Search, Calculator, API Calls)
- Unser Go Gateway hat bereits MCP-kompatible Tool-Endpoints
- **Browser-Side:** `use-mcp` React Hook (offiziell von Anthropic)
  - `npm i use-mcp`
  - `const { tools, callTool, status } = useMcp({ url: "..." })`
  - OAuth Auth, Connection State, Typed Access

**Fuer uns:** `use-mcp` Hook im Agent Chat Frontend einbauen → standardisierte Tool-Integration
statt manueller `fetch("/api/agent/tools/...")` Calls.

### 1.2 MCP Apps — Anthropic

**Layer:** Agent → UI Surfaces
**Status:** Produktiv seit Januar 2026, ersetzt Artifacts-Pattern.

- MCP Apps ≠ MCP Tools
- Tool referenziert UI-Resource (`ui://...`) in Metadata
- Host rendert UI in **sandboxed iframe** (JSON-RPC via postMessage)
- Anthropic bewegt sich von Artifacts hin zu MCP Apps (standardisiert, erweiterbar)
- SDK: `@modelcontextprotocol/ext-apps`

**Fuer uns:** Agent kann UI-Surfaces generieren die im Chat oder Canvas angezeigt werden.
Ergaenzt Tambo (eigene Components) mit externen MCP App Surfaces.

### 1.3 WebMCP — W3C Draft (Google/Microsoft)

**Layer:** Website → Agent (Browser-nativ)
**Status:** Chrome 146 Canary (Feb 2026), sehr frueh.

- `navigator.modelContext` API
- Websites deklarieren ihre Capabilities als strukturierte Tools
- Agent ruft sie direkt auf — kein DOM-Scraping, keine Screenshots
- `@mcp-b/react-webmcp` fuer React Integration

**Fuer uns:** Zukunftssicher planen. Wenn WebMCP Standard wird, koennen unsere
Trading-Pages ihre Capabilities (Chart-State, Portfolio-Daten) direkt an den Agent exposen.

### 1.4 AG-UI (Agent-User Interaction Protocol) — CopilotKit

**Layer:** Agent ↔ Frontend Runtime (bidirektional)
**Status:** Adoptiert von Google, Oracle, AWS, LangChain, Microsoft.

- Event/State Protocol fuer Echtzeit Agent↔UI Kommunikation
- Agent-State Updates, Tool Progress, User Interactions — alles synchronisiert
- Nicht eine UI-Spezifikation — ein Runtime-Protocol
- CopilotKit ist die Referenz-Implementierung, aber Protocol ist framework-agnostisch

**Fuer uns:** AG-UI als Standard fuer Agent↔Frontend Kommunikation evaluieren.
Unser `useChatSession` Hook ist eine primitive Version davon.

### 1.5 A2UI (Agent-to-UI) — Google

**Layer:** Agent → UI (Declarative Specification)
**Status:** Aktiv, via CopilotKit nutzbar.

- Agent emittiert JSON das UI-Surfaces beschreibt (Cards, Forms, Tables, Multi-Step Flows)
- Frontend rendert native Components aus der JSON-Beschreibung
- Declarative = sicher und portabel (Agent kann keinen beliebigen Code ausfuehren)

**Fuer uns:** Fuer standardisierte Agent-Outputs (Portfolio-Karten, Trade-Summaries, Analyse-Tables).
Agent beschreibt WAS angezeigt werden soll, Frontend entscheidet WIE.

### 1.6 A2A (Agent-to-Agent) — Google

**Layer:** Agent ↔ Agent Koordination
**Status:** v1.0, 50+ Partner, gRPC, signed Agent Cards.

- Agents discovern Capabilities anderer Agents
- Delegieren Tasks an spezialisierte Agents
- Multi-Framework: LangChain Agent kann mit PydanticAI Agent kommunizieren

**Fuer uns:** Wenn Multi-Agent Setup steht (Trading + Research + Risk Manager).
Agents koennen Tasks delegieren ohne manuelles Routing.

### 1.7 ACP (Agent Communication Protocol) — IBM/Linux Foundation

**Layer:** Agent ↔ Agent + Memory Sharing
**Status:** Wachsend, BeeAI Platform.

- Wie A2A, aber mit **Built-in Memory Sharing** zwischen Agents
- Agent A kann Erkenntnisse an Agent B weitergeben ohne Context Window Overhead
- Discovery-Mechanismus fuer Agent-Capabilities

**Fuer uns:** Trading-Agent teilt Analyse-Ergebnisse mit Research-Agent ohne
alles nochmal im Context Window zu wiederholen.

---

## 2. Generative UI Frameworks

### 2.1 Tambo

**Was:** Generative React UI Framework — Agent registriert Components, Tambo rendert im Chat.
**Status:** Im Hauptprojekt geplant, aktives Produkttempo, MCP Apps Support.

- `useTamboTool()` — Agent registriert React Components als Tools
- MCP Server Integration (Tools, Resources, Prompts)
- Per-Tool Begrenzungen (`maxCalls`), Sampling/Sub-Thread Support
- Interactable-Pattern fuer Tool-Lifecycle Management

**Use-Case:** Eigene domain-spezifische Components (Chart-Widgets, Portfolio-Karten,
Trade-Formulare) die der Agent im Chat rendern kann.

### 2.2 CopilotKit

**Was:** AG-UI Protocol Framework — Generative UI + Frontend Tool Binding.
**Status:** Open Source, Google/Oracle/AWS adoptiert.

- `useFrontendTool()` — Agent ruft vordefinierte React Components auf
- AG-UI Protocol — bidirektionaler State zwischen Agent und Frontend
- A2UI Integration — Agent emittiert JSON, Frontend rendert native Components
- React, Next.js, Angular, Vue

**Use-Case:** Dynamische/standardisierte Agent-UI. Agent steuert Frontend-State
(Chart wechseln, Panel oeffnen) ueber standardisiertes Protocol.

### 2.3 Empfehlung: Parallel nutzen

- **Tambo** fuer eigene, domain-spezifische Components
- **CopilotKit** fuer AG-UI Protocol und standardisierte Agent↔Frontend Kommunikation
- Beide koennen koexistieren — Tambo als Component-Registry, CopilotKit als Protocol-Layer

---

## 3. Infinite Canvas & Workspace

### 3.1 tldraw

**Was:** Open Source Infinite Canvas SDK fuer React.
**Status:** Aktiv, Collaboration-ready, von mehreren AI-Projekten genutzt.

- 2D Spatial Canvas mit Shapes, Text, Connections, Embeds
- React SDK: `<Tldraw />`
- Echtzeit-Collaboration Support
- Wird u.a. von Nordeck's matrix-neoboard (MatrixRTC) genutzt

**Use-Case:** Split-View im Agent Chat — statt linearer Chat ein Spatial Workspace.
Agent platziert Widgets, Charts, Analyse-Blocks auf einer 2D-Flaeche.
User kann arrangieren, verbinden, annotieren.

### 3.2 Novel (bereits eingebaut)

**Was:** Tiptap + AI Autocomplete + Slash-Commands.
**Status:** In `AgentOutputEditor.tsx` eingebaut.

**Abgrenzung zu tldraw:**
- Novel = **linearer Dokument-Editor** (Headings, Lists, Code, Tables)
- tldraw = **2D Spatial Canvas** (Freiform, Widgets, Connections)
- Novel kann als **Text-Block innerhalb der Canvas** genutzt werden

---

## 4. Memory & Self-Evolution

### 4.1 Supermemory

**Was:** Memory API fuer AI — Storage, Retrieval, Auto-Extraction, Profile Building.
**Status:** 100B+ Tokens/Monat, <300ms Retrieval, MCP Server.

- `supermemory-mcp` — Agent greift auf Memory zu via MCP
- Auto-Extraction aus Conversations (Deduplication, Profile Building)
- TypeScript + Python + REST SDKs
- Graph-Visualisierung der Memory-Daten

**Fuer uns:** Ergaenzt oder ersetzt unseren Memory-Service (KuzuDB/ChromaDB).
Backend-Integration in `python-backend/memory/`.

### 4.2 MetaClaw (SkillRL Pattern)

**Was:** Self-Evolving Agent Framework — Agent lernt aus Fehlern ohne GPU.
**Status:** Open Source, March 2026.

**Pattern das wir uebernehmen (ohne MetaClaw direkt einzubauen):**

1. **Failure-to-Skill Synthesis:**
   - Agent schlaegt fehl → LLM analysiert Failure-Trajectory
   - Destilliert zu kompaktem Skill (z.B. "Pruefe Dateipfade vor dem Lesen")
   - Skill wird in Skill-Library gespeichert

2. **Embedding-basiertes Retrieval:**
   - Pro Task: relevanteste Skills per Similarity-Search finden
   - Skills werden als System-Prompt-Addon injiziert
   - Sofort wirksam, kein Fine-Tuning

3. **Temporal Context (last30days Pattern):**
   - Zeitbasierten Kontext automatisch injizieren
   - Letzte Trades, Portfolio-Aenderungen, Market Events
   - Kombinierbar mit Skill-Retrieval

**Fuer uns:** `python-backend/agent/` um Skills-Library erweitern.
Agent wird besser ueber Zeit ohne manuelles Prompt-Engineering.

### 4.3 ACP Agent Memory

**Was:** IBM Protocol fuer shared Memory zwischen Agents.
**Status:** Linux Foundation backed.

**Fuer uns:** Wenn Multi-Agent (Trading + Research + Risk):
- Trading-Agent findet RSI-Anomalie → teilt via ACP mit Research-Agent
- Research-Agent hat Kontext ohne eigene Analyse wiederholen zu muessen
- Spart Tokens + reduziert Latenz

---

## 5. Multi-Agent Orchestrierung

### 5.1 LangGraph

**Was:** Graph-basierte Agent-Orchestrierung (de-facto Standard 2026).
**Status:** LangChain Ecosystem, von TradingAgents + deer-flow genutzt.

- Graph-basierte Workflows: Agent A → Agent B → Agent C
- Built-in State Management zwischen Agents
- Checkpointing (Agent kann pausieren/resumieren)
- Sub-Agent Spawning mit scoped Context

**Fuer uns:** `python-backend/agent/loop.py` (manueller Loop) → LangGraph.
Erster Schritt: einzelner Agent als LangGraph Graph.
Zweiter Schritt: Multi-Agent Workflows.

### 5.2 TradingAgents (TauricResearch)

**Was:** Multi-Agent Framework mit 7 Trading-spezialisierten Rollen.
**Status:** v0.2.3, multi-provider (OpenAI, Anthropic, Google, Ollama).

**Rollen:**
1. Fundamentals Analyst
2. Sentiment Analyst
3. News Analyst
4. Technical Analyst
5. Researcher
6. Trader
7. Risk Manager

**Fuer uns:** Architektur-Inspiration fuer unser Multi-Agent Setup.
Nicht 1:1 uebernehmen, aber Rollen-Pattern und LangGraph-Workflows studieren.

### 5.3 deer-flow (ByteDance)

**Was:** SuperAgent Harness — 45K Stars, LangGraph + Docker Sandbox.
**Status:** v2.0, Open Source, aktiv entwickelt.

**Features die uns interessieren:**
- **Skills System:** Markdown-basierte Skill-Definitionen (Workflow + Best Practices + Referenzen)
- **Task Decomposition:** Lead Agent zerlegt Tasks, spawnt Sub-Agents
- **Scoped Context:** Jeder Sub-Agent bekommt eigenes Filesystem + Bash Terminal
- **Docker Sandbox:** Isolierte Execution pro Sub-Agent

**Fuer uns:** deer-flow als Referenz/Basis fuer unser Agent-Harness Design.
Skills-System (Markdown .md Files) in `python-backend/agent/skills/` uebernehmen.

---

## 6. Sandbox & Code Execution

### 6.1 OpenSandbox (Alibaba)

**Was:** Sandbox Platform fuer AI — Docker-basiert, Multi-Language SDKs.
**Status:** Apache 2.0, Open Source.

- Python/TS/Go SDKs
- Docker Container pro Execution
- Built-in: Code Interpreter, Browser Automation (Chrome/Playwright), Desktop (VNC)
- Lifecycle Management (Start/Stop/Timeout)

**Fuer uns:** Standard-Sandbox fuer Agent Code-Execution.
`pip install opensandbox-sdk`, Docker Container pro Tool-Execution.
Kein Vendor Lock-in, kein Firecracker noetig.

### 6.2 E2B

**Was:** Firecracker microVMs, Cloud oder Self-Hosted.
**Status:** 100h/Monat Free Tier.

**Fuer uns:** Referenz-Implementierung, nicht primaere Wahl (Vendor Lock-in Risiko).
E2B Fragments als UI-Inspiration fuer Artifacts-Style Code-Previews.

### 6.3 Sandpack (CodeSandbox)

**Was:** Browser-basierter Sandbox, kein Server noetig.
**Status:** Aktiv, leichtgewichtig.

**Fuer uns:** Fuer interaktive Code-Previews im Chat ohne Backend-Roundtrip.
Agent generiert React-Code → Sandpack rendert live im Browser.

---

## 7. Computer Use & Browser Automation

### 7.1 Playwright MCP

**Was:** 33+ Browser-Tools via MCP (Navigate, Click, Type, Screenshot, Accessibility Tree).
**Status:** Microsoft, aktiv, im Hauptprojekt MCP Stack.

- Agent kann Websites bedienen
- Microsoft empfiehlt neuerdings **CLI ueber MCP** (4x weniger Tokens)
- MCP fuer explorative Tasks, CLI fuer wiederholbare Flows

### 7.2 WebMCP (Browser-nativ)

**Was:** `navigator.modelContext` — Websites deklarieren Tools nativ.
**Status:** W3C Draft, Chrome 146 Canary (Feb 2026).

- Kein DOM-Scraping, keine Screenshots
- Website sagt Agent direkt was sie kann
- Zukunft: Standard-Weg fuer Agent↔Website Interaktion

### 7.3 Anthropic Computer Use

**Was:** Claude sieht Screen + klickt (Cloud-side).
**Status:** Verfuegbar, aber Cloud-only.

**Fuer uns:** Evaluieren wenn Desktop-Agent Use-Case kommt.
Aktuell nicht prioritaer.

---

## 8. Security & Hardening

### 8.1 pentagi (vxcontrol)

**Was:** Security-focused AI Agent — Audit-Logging, Consent Flows, Sandbox Execution.
**Status:** Open Source, aktiv.

**Patterns zum Uebernehmen:**
- Structured Audit Logs fuer alle Agent-Actions
- Consent Flows bevor Agent sensitive Tools ausfuehrt
- Rate-Limiting pro Tool/Agent/Session

### 8.2 OpenSandbox als Security Boundary

- Jeder Agent-Code-Execution in isoliertem Docker Container
- Kein Zugriff auf Host-Filesystem oder Netzwerk (ausser explizit erlaubt)
- Timeout-Enforcement verhindert Endlos-Loops

### 8.3 deer-flow Isolation Pattern

- Jeder Sub-Agent bekommt eigenes Filesystem
- Docker Container pro Agent-Execution
- Scoped Permissions (Agent A kann nicht Agent B's Daten lesen)

---

## 9. Design Trends 2026

| Trend | Beschreibung | Relevanz |
|-------|-------------|----------|
| **Generative UI** | Agent rendert interaktive Components statt Text | Hoch — Tambo + CopilotKit |
| **Dark Glass / Frosted Panels** | Transluzente Panels auf dunklem Hintergrund | Styling-Richtung |
| **Canvas/Workspace** | Spatial statt linear (Microsoft/OpenAI Canvas) | tldraw als Split-View |
| **Voice-first Multimodal** | Text + Voice + Images + Video in einem Interface | Haben wir (LiveKit) |
| **Beyond Chat** | Chat ist nur ein Kanal, Agent steuert gesamte App | AG-UI + Frontend Tools |
| **Transparency** | Tool-Calls, Reasoning Traces, Cost Badges sichtbar | Haben wir (AgentChatToolBlock) |

---

## 10. Zukunft (6-12 Monate)

| Richtung | Zeithorizont | Impact |
|----------|-------------|--------|
| AG-UI als Standard Protocol | 3-6 Monate | Hoch |
| MCP Apps uberall | 3-6 Monate | Hoch |
| WebMCP nativ in Browsern | 6-12 Monate | Mittel |
| Self-Evolving Agents (MetaClaw-Pattern) | 3-6 Monate | Hoch |
| Canvas > Chat fuer komplexe Tasks | 6 Monate | Hoch |
| Multi-Agent Teams als Standard | 6-12 Monate | Hoch |
| 40% Enterprise Apps mit Agents (Gartner) | 12 Monate | Validierung |
